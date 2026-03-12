from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from retail_factor_agent.config import AgentConfig


def _load_allowed_factors(factor_table_path: Path) -> list[str]:
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            df = pd.read_csv(factor_table_path, nrows=1, encoding=enc)
            cols = [c for c in df.columns if c.startswith("factor_") and c.endswith("_effect")]
            names = [c[len("factor_") : -len("_effect")] for c in cols]
            names = [n for n in names if isinstance(n, str) and n.strip()]
            if names:
                return names
        except Exception:
            continue
    raise RuntimeError(f"无法从全因子表读取因子白名单: {factor_table_path}")


def _compact_text(title: str, content: str, max_chars: int) -> str:
    text = f"标题：{title}\n正文：{content}".strip()
    if len(text) <= max_chars:
        return text
    head = max_chars // 2
    tail = max_chars - head - 20
    return text[:head] + "\n...[截断]...\n" + text[-tail:]


def _build_prompts(allowed_factors: list[str], post_text: str) -> tuple[str, str]:
    system_prompt = (
        "你是金融文本结构化抽取器。只输出一个JSON对象，不要Markdown。\n"
        "字段必须为 prediction_object,prediction_stock_code,prediction_score,prediction_duration,logic_chains。\n"
        "prediction_score: 看多=1,看空=-1,中性=0。\n"
        "logic_chains 为数组，每条包含 chain_summary,factors。\n"
        "factors 每项仅含 name,value,effect；name必须在给定因子库中；value为纯数字或null；effect为1/-1/0。\n"
        "若文本无有效逻辑链，返回空数组 logic_chains。"
    )
    user_prompt = (
        "因子库（name只能从中选择）：" + "、".join(allowed_factors) + "\n"
        "若文本因子不在库内，忽略，不要自造。\n"
        "请抽取下面帖子：\n"
        + post_text
    )
    return system_prompt, user_prompt


def _call_llm(
    base_url: str,
    api_key: str,
    model: str,
    timeout: int,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    resp = requests.post(
        base_url.rstrip("/") + "/chat/completions",
        headers=headers,
        json=payload,
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    start = content.find("{")
    end = content.rfind("}")
    if start >= 0 and end > start:
        content = content[start : end + 1]
    return json.loads(content)


def _to_wide_row(result: dict[str, Any], allowed_factors: list[str], meta: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "row_id": meta.get("row_id", ""),
        "post_id": meta.get("post_id", ""),
        "post_publish_time": meta.get("post_publish_time", ""),
        "prediction_object": result.get("prediction_object"),
        "prediction_stock_code": result.get("prediction_stock_code"),
        "prediction_score": result.get("prediction_score"),
        "prediction_duration": result.get("prediction_duration"),
    }
    for f in allowed_factors:
        row[f"factor_{f}_effect"] = 0
        row[f"factor_{f}_value"] = ""
    chains = result.get("logic_chains", [])
    if not isinstance(chains, list):
        chains = []
    allowed = set(allowed_factors)
    for chain in chains:
        if not isinstance(chain, dict):
            continue
        factors = chain.get("factors", [])
        if not isinstance(factors, list):
            continue
        for f in factors:
            if not isinstance(f, dict):
                continue
            name = str(f.get("name", "")).strip()
            if name not in allowed:
                continue
            row[f"factor_{name}_effect"] = f.get("effect", 0)
            val = f.get("value", None)
            row[f"factor_{name}_value"] = "" if val is None else str(val)
    return row


def run_llm_extraction(cfg: AgentConfig, posts_csv: Path) -> tuple[Path, Path]:
    cfg.ensure_dirs()
    api_key = cfg.llm_api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("缺少 LLM_API_KEY/OPENAI_API_KEY 环境变量。")

    posts = pd.read_csv(posts_csv, encoding="utf-8-sig")
    allowed_factors = _load_allowed_factors(cfg.factor_table_path)

    jsonl_path = cfg.output_dir / "llm_extracted.jsonl"
    table_path = cfg.output_dir / "llm_factor_table.csv"

    rows: list[dict[str, Any]] = []
    lock_rows: list[dict[str, Any]] = []

    def _process(i: int, r: pd.Series) -> None:
        title = str(r.get("post_title", ""))
        content = str(r.get("content", ""))
        text = _compact_text(title, content, cfg.llm_max_input_chars)
        system_prompt, user_prompt = _build_prompts(allowed_factors, text)
        parsed = _call_llm(
            base_url=cfg.llm_base_url,
            api_key=api_key,
            model=cfg.llm_model,
            timeout=cfg.llm_timeout,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=cfg.llm_max_output_tokens,
        )
        meta = {
            "row_id": i,
            "post_id": r.get("post_id", ""),
            "post_publish_time": r.get("post_publish_time", ""),
        }
        lock_rows.append({"meta": meta, "analysis": parsed})
        rows.append(_to_wide_row(parsed, allowed_factors, meta))

    with ThreadPoolExecutor(max_workers=max(1, cfg.llm_workers)) as ex:
        futures = [ex.submit(_process, i, row) for i, row in posts.iterrows()]
        for f in as_completed(futures):
            _ = f.result()

    with open(jsonl_path, "w", encoding="utf-8") as f:
        for rec in lock_rows:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    pd.DataFrame(rows).to_csv(table_path, index=False, encoding="utf-8-sig")
    return jsonl_path, table_path
