from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
import re
import requests

from retail_factor_agent.config import AgentConfig


def _normalize_post_columns(df: pd.DataFrame) -> pd.DataFrame:
    col_map = {
        "post_id": ["post_id", "帖子id", "帖子ID", "id", "ID"],
        "post_publish_time": ["post_publish_time", "发布时间", "发帖时间", "time", "date"],
        "post_title": ["post_title", "标题", "帖子标题", "title"],
        "content": ["content", "帖子内容", "内容", "text", "body"],
        "stock_code": ["stockbar_code", "stock_code", "代码", "symbol"],
    }
    out = pd.DataFrame()
    for target, candidates in col_map.items():
        found = next((c for c in candidates if c in df.columns), None)
        out[target] = df[found] if found else ""
    return out


def _load_with_fallback_encoding(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False)
        except Exception:
            continue
    return pd.read_csv(path, low_memory=False)


def _crawl_from_akshare(symbols: list[str], per_symbol_limit: int = 500) -> pd.DataFrame:
    import akshare as ak  # optional dependency

    all_rows: list[pd.DataFrame] = []
    for symbol in symbols:
        try:
            raw = ak.stock_guba_em(symbol=symbol)
            if raw is None or raw.empty:
                continue
            raw = raw.head(per_symbol_limit).copy()
            raw["stock_code"] = symbol
            all_rows.append(raw)
        except Exception:
            continue
    if not all_rows:
        return pd.DataFrame()
    merged = pd.concat(all_rows, ignore_index=True)
    return _normalize_post_columns(merged)


def _extract_6digit_code(x: str) -> str:
    s = str(x or "")
    m = re.search(r"(\d{6})", s)
    return m.group(1) if m else ""


def _scope_filter_code(code: str, scope: str) -> bool:
    if not code:
        return False
    if scope == "a_all":
        return True
    if scope == "gem":
        return code.startswith(("300", "301"))
    if scope == "star":
        return code.startswith("688")
    if scope == "main_board":
        return code.startswith(("600", "601", "603", "605", "000", "001", "002"))
    # indices buckets fallback: still use A-share universe
    if scope in {"hs300", "sz50"}:
        return True
    return True


def _filter_posts_by_stock_scope(df: pd.DataFrame, scope: str) -> pd.DataFrame:
    if scope in {"", "a_all"}:
        return df
    df2 = df.copy()
    code_col = "stock_code" if "stock_code" in df2.columns else None
    if code_col is None:
        return df2
    codes = df2[code_col].astype(str).map(_extract_6digit_code)
    mask = codes.map(lambda c: _scope_filter_code(c, scope))
    return df2[mask]


def _resolve_symbols_for_scope(scope: str, custom_symbols: list[str] | None, max_symbols: int) -> list[str]:
    if custom_symbols:
        return custom_symbols[:max_symbols]
    # Try auto universe via akshare spot list
    try:
        import akshare as ak

        spot = ak.stock_zh_a_spot_em()
        if spot is None or spot.empty:
            raise RuntimeError("empty spot list")
        code_col = "代码" if "代码" in spot.columns else ("代码" if "code" not in spot.columns else "code")
        if code_col not in spot.columns:
            # fallback guess
            code_col = spot.columns[1]
        codes = spot[code_col].astype(str).map(_extract_6digit_code).tolist()
        filt = [c for c in codes if _scope_filter_code(c, scope)]
        uniq = []
        seen = set()
        for c in filt:
            if c and c not in seen:
                seen.add(c)
                uniq.append(c)
        return uniq[:max_symbols]
    except Exception:
        # fallback small list
        base = ["600519", "000001", "601318", "600036", "000858", "300750", "688981"]
        return [c for c in base if _scope_filter_code(c, scope)][:max_symbols]


def _crawl_from_custom_api(
    api_url: str,
    api_key: str,
    symbols: list[str],
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    if not api_url:
        return pd.DataFrame()
    params = {
        "symbols": ",".join(symbols),
        "start_date": start_date,
        "end_date": end_date,
    }
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        headers["X-API-Key"] = api_key
    resp = requests.get(api_url, params=params, headers=headers, timeout=60)
    resp.raise_for_status()
    payload = resp.json()
    rows = payload.get("data", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list) or not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    return _normalize_post_columns(df)


def _is_ai_generated_text(title: str, content: str) -> bool:
    text = f"{title} {content}".lower()
    patterns = [
        r"chatgpt",
        r"deepseek",
        r"claude",
        r"由ai生成",
        r"ai生成",
        r"大模型生成",
        r"仅供参考.*(ai|模型)",
    ]
    return any(re.search(p, text) for p in patterns)


def _is_announcement_text(title: str, content: str) -> bool:
    text = f"{title} {content}"
    keywords = [
        "公告",
        "临时公告",
        "董事会决议",
        "监事会决议",
        "提示性公告",
        "关于公司",
        "年度报告",
        "半年度报告",
        "一季度报告",
        "三季度报告",
        "年报",
        "季报",
    ]
    return any(k in text for k in keywords)


def _contains_logic_text(content: str) -> bool:
    logic_kw = ["因为", "因此", "所以", "逻辑", "预计", "判断", "看好", "看空", "理由", "驱动", "导致", "若", "则"]
    signal_kw = ["上涨", "下跌", "突破", "跌破", "反弹", "回调", "%", "同比", "环比", "增速"]
    has_logic = any(k in content for k in logic_kw)
    has_signal = any(k in content for k in signal_kw) or any(ch.isdigit() for ch in content)
    return has_logic and has_signal


def run_crawl_and_sample(
    cfg: AgentConfig,
    source_csv: Optional[Path] = None,
    stock_symbols: Optional[list[str]] = None,
) -> Path:
    cfg.ensure_dirs()

    if source_csv is None:
        source_csv = cfg.existing_posts_path

    if source_csv.exists():
        df = _load_with_fallback_encoding(source_csv)
        df = _normalize_post_columns(df)
    else:
        symbols = _resolve_symbols_for_scope(
            scope=cfg.stock_scope,
            custom_symbols=stock_symbols,
            max_symbols=cfg.max_crawl_symbols,
        )
        if cfg.crawl_provider == "api":
            df = _crawl_from_custom_api(
                api_url=cfg.crawler_api_url,
                api_key=cfg.crawler_api_key,
                symbols=symbols,
                start_date=cfg.start_date,
                end_date=cfg.end_date,
            )
        else:
            df = _crawl_from_akshare(symbols=symbols)
        if df.empty:
            raise RuntimeError("爬虫未获取到数据，且未找到本地帖子源文件。请检查爬虫URL/KEY或本地输入路径。")

    df["content"] = df["content"].fillna("").astype(str).str.strip()
    df["post_title"] = df["post_title"].fillna("").astype(str).str.strip()
    df["post_publish_time"] = pd.to_datetime(df["post_publish_time"], errors="coerce")
    df = _filter_posts_by_stock_scope(df, cfg.stock_scope)

    start = pd.to_datetime(cfg.start_date)
    end = pd.to_datetime(cfg.end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    df = df[df["post_publish_time"].between(start, end, inclusive="both")]
    df = df[df["content"].str.len() >= cfg.min_chars]
    full_text = (df["post_title"] + " " + df["content"]).fillna("")

    if cfg.exclude_ai_generated:
        ai_pattern = r"chatgpt|deepseek|claude|由ai生成|ai生成|大模型生成|仅供参考.*(?:ai|模型)"
        df = df[~full_text.str.lower().str.contains(ai_pattern, regex=True, na=False)]
        full_text = (df["post_title"] + " " + df["content"]).fillna("")
    if cfg.exclude_announcements:
        ann_pattern = r"公告|临时公告|董事会决议|监事会决议|提示性公告|关于公司|年度报告|半年度报告|一季度报告|三季度报告|年报|季报"
        df = df[~full_text.str.contains(ann_pattern, regex=True, na=False)]
    if cfg.require_logic:
        logic_pattern = r"因为|因此|所以|逻辑|预计|判断|看好|看空|理由|驱动|导致|若|则"
        signal_pattern = r"上涨|下跌|突破|跌破|反弹|回调|%|同比|环比|增速|\d"
        has_logic = df["content"].str.contains(logic_pattern, regex=True, na=False)
        has_signal = df["content"].str.contains(signal_pattern, regex=True, na=False)
        df = df[has_logic & has_signal]

    if "post_id" in df.columns:
        df = df.drop_duplicates(subset=["post_id"])
    else:
        df = df.drop_duplicates(subset=["content"])

    if len(df) > cfg.sample_size:
        df = df.sample(n=cfg.sample_size, random_state=cfg.random_seed)

    df = df.sort_values("post_publish_time").copy()
    df["post_publish_time"] = df["post_publish_time"].dt.strftime("%Y-%m-%d %H:%M:%S")

    out_path = cfg.data_dir / f"posts_sample_{cfg.start_date}_{cfg.end_date}_{cfg.sample_size}.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    return out_path
