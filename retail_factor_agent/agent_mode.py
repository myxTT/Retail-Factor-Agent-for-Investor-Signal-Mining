from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ParsedIntent:
    requirement: str
    start_date: str
    end_date: str
    sample_size: int
    stock_scope: str
    custom_symbols: list[str]
    run_wind: bool
    run_crawl: bool
    run_llm: bool
    run_train: bool
    run_analyze: bool
    run_viz: bool


def _extract_date_range(text: str) -> tuple[str, str]:
    date_matches = re.findall(r"(20\d{2}[-/\.](?:0[1-9]|1[0-2])[-/\.](?:0[1-9]|[12]\d|3[01]))", text)
    if len(date_matches) >= 2:
        s = date_matches[0].replace("/", "-").replace(".", "-")
        e = date_matches[1].replace("/", "-").replace(".", "-")
        return s, e

    year_matches = re.findall(r"(20\d{2})", text)
    if len(year_matches) >= 2:
        y1, y2 = sorted([int(year_matches[0]), int(year_matches[1])])
        return f"{y1}-01-01", f"{y2}-12-31"
    if len(year_matches) == 1:
        y = int(year_matches[0])
        return f"{y}-01-01", f"{y}-12-31"
    return "2020-01-01", "2024-12-31"


def _extract_sample_size(text: str) -> int:
    m = re.search(r"(\d{3,6})\s*条", text)
    if m:
        return int(m.group(1))
    m = re.search(r"sample\s*[:=]?\s*(\d{3,6})", text, flags=re.I)
    if m:
        return int(m.group(1))
    return 5000


def _extract_stock_scope(text: str) -> tuple[str, list[str]]:
    t = text.lower()
    if "创业板" in text or "gem" in t:
        return "gem", []
    if "科创板" in text or "star" in t:
        return "star", []
    if "主板" in text:
        return "main_board", []
    if "沪深300" in text or "hs300" in t:
        return "hs300", []
    if "上证50" in text or "sz50" in t:
        return "sz50", []

    # custom code list
    codes = re.findall(r"\b\d{6}\b", text)
    if codes:
        uniq = []
        seen = set()
        for c in codes:
            if c not in seen:
                seen.add(c)
                uniq.append(c)
        return "custom", uniq

    if "a股" in text.lower() or "全市场" in text:
        return "a_all", []
    return "a_all", []


def _extract_stages(text: str) -> tuple[bool, bool, bool, bool, bool, bool]:
    t = text.lower()
    has_only = "仅" in text or "只" in text

    run_wind = ("wind" in t) or ("万得" in text)
    run_crawl = ("爬取" in text) or ("抓取" in text) or ("样本" in text) or ("帖子" in text)
    run_llm = ("llm" in t) or ("大模型" in text) or ("抽取" in text) or ("因子提取" in text)
    run_train = ("训练" in text) or ("建模" in text) or ("模型" in text)
    run_analyze = ("分析" in text) or ("相关性" in text) or ("解释" in text)
    run_viz = ("可视化" in text) or ("画图" in text) or ("图表" in text)

    if not any([run_wind, run_crawl, run_llm, run_train, run_analyze, run_viz]):
        return False, True, True, True, True, True
    if has_only:
        return run_wind, run_crawl, run_llm, run_train, run_analyze, run_viz

    # 不是only语义时，若提到了后续环节则默认补齐中间依赖
    if run_train or run_analyze or run_viz:
        run_crawl = True
        run_llm = True
        run_train = True
        run_analyze = True
        run_viz = True
    return run_wind, run_crawl, run_llm, run_train, run_analyze, run_viz


def parse_requirement(requirement: str) -> ParsedIntent:
    req = (requirement or "").strip()
    start_date, end_date = _extract_date_range(req)
    sample_size = _extract_sample_size(req)
    stock_scope, custom_symbols = _extract_stock_scope(req)
    run_wind, run_crawl, run_llm, run_train, run_analyze, run_viz = _extract_stages(req)
    return ParsedIntent(
        requirement=req,
        start_date=start_date,
        end_date=end_date,
        sample_size=sample_size,
        stock_scope=stock_scope,
        custom_symbols=custom_symbols,
        run_wind=run_wind,
        run_crawl=run_crawl,
        run_llm=run_llm,
        run_train=run_train,
        run_analyze=run_analyze,
        run_viz=run_viz,
    )


def print_intent_summary(intent: ParsedIntent) -> None:
    print("[AGENT] 已解析用户需求：")
    print(f"  - 时间区间: {intent.start_date} ~ {intent.end_date}")
    print(f"  - 抽样条数: {intent.sample_size}")
    print(f"  - 股票范围: {intent.stock_scope}")
    if intent.custom_symbols:
        print(f"  - 自定义股票: {','.join(intent.custom_symbols)}")
    stages = []
    if intent.run_wind:
        stages.append("wind")
    if intent.run_crawl:
        stages.append("crawl")
    if intent.run_llm:
        stages.append("llm")
    if intent.run_train:
        stages.append("train")
    if intent.run_analyze:
        stages.append("analyze")
    if intent.run_viz:
        stages.append("viz")
    print(f"  - 执行步骤: {', '.join(stages) if stages else '(无)'}")

