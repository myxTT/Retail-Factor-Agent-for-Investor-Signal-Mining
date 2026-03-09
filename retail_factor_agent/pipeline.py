from __future__ import annotations

import argparse
from pathlib import Path

from retail_factor_agent.config import AgentConfig
from retail_factor_agent.steps.crawl_posts import run_crawl_and_sample
from retail_factor_agent.steps.factor_analysis import run_factor_analysis
from retail_factor_agent.steps.llm_extract import run_llm_extraction
from retail_factor_agent.steps.train_model import run_training
from retail_factor_agent.steps.visualize import run_visualization
from retail_factor_agent.steps.wind_sync import run_wind_sync


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Retail factor agent pipeline")
    p.add_argument("--crawl", action="store_true", help="执行爬取/抽样步骤")
    p.add_argument("--llm", action="store_true", help="执行 LLM 因子抽取")
    p.add_argument("--train", action="store_true", help="执行 ML 训练")
    p.add_argument("--analyze", action="store_true", help="执行因子相关性分析")
    p.add_argument("--viz", action="store_true", help="执行可视化")
    p.add_argument("--all", action="store_true", help="执行全流程")
    p.add_argument("--wind", action="store_true", help="执行Wind处理与因子合并")
    p.add_argument("--wind-fetch", action="store_true", help="执行Wind重新下载（需要Wind可用）")
    p.add_argument("--sample-size", type=int, default=5000)
    p.add_argument("--start-date", type=str, default="2020-01-01")
    p.add_argument("--end-date", type=str, default="2024-12-31")
    p.add_argument("--llm-model", type=str, default="deepseek-chat")
    p.add_argument("--llm-base-url", type=str, default="https://api.deepseek.com/v1")
    p.add_argument("--llm-workers", type=int, default=8)
    p.add_argument("--min-chars", type=int, default=100)
    p.add_argument("--symbols", type=str, default="", help="逗号分隔股票代码，用于在线爬取兜底")
    p.add_argument("--allow-ai", action="store_true", help="不剔除AI生成文本")
    p.add_argument("--allow-announcement", action="store_true", help="不剔除公告文本")
    p.add_argument("--no-logic-filter", action="store_true", help="不要求文本包含逻辑信号")
    p.add_argument("--source-csv", type=str, help="指定帖子源CSV")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = AgentConfig()
    cfg.sample_size = args.sample_size
    cfg.start_date = args.start_date
    cfg.end_date = args.end_date
    cfg.llm_model = args.llm_model
    cfg.llm_base_url = args.llm_base_url
    cfg.llm_workers = args.llm_workers
    cfg.min_chars = args.min_chars
    cfg.exclude_ai_generated = not args.allow_ai
    cfg.exclude_announcements = not args.allow_announcement
    cfg.require_logic = not args.no_logic_filter
    cfg.ensure_dirs()

    run_all = args.all or not any([args.wind, args.crawl, args.llm, args.train, args.analyze, args.viz])

    posts_csv = cfg.data_dir / f"posts_sample_{cfg.start_date}_{cfg.end_date}_{cfg.sample_size}.csv"
    factor_table = cfg.output_dir / "llm_factor_table.csv"

    if run_all or args.wind:
        run_wind_sync(cfg, fetch_fresh=args.wind_fetch)
        print("[OK] wind sync -> done")

    if run_all or args.crawl:
        source = Path(args.source_csv) if args.source_csv else None
        symbols = [s.strip() for s in args.symbols.split(",") if s.strip()] if args.symbols else None
        posts_csv = run_crawl_and_sample(cfg, source_csv=source, stock_symbols=symbols)
        print(f"[OK] crawl/sample -> {posts_csv}")

    if run_all or args.llm:
        if not posts_csv.exists():
            raise FileNotFoundError(f"缺少帖子样本文件: {posts_csv}")
        jsonl_path, factor_table = run_llm_extraction(cfg, posts_csv)
        print(f"[OK] llm extract -> {jsonl_path}")
        print(f"[OK] factor table -> {factor_table}")

    if run_all or args.train:
        infer_path = factor_table if factor_table.exists() else None
        metrics, model, weights = run_training(cfg, infer_table_path=infer_path)
        print(f"[OK] train metrics -> {metrics}")
        print(f"[OK] model -> {model}")
        print(f"[OK] factor weights -> {weights}")
        print(f"[OK] user factor analysis -> {cfg.output_dir / 'user_factor_analysis.csv'}")

    if run_all or args.analyze:
        corr = run_factor_analysis(cfg)
        print(f"[OK] factor analysis -> {corr}")

    if run_all or args.viz:
        figs = run_visualization(cfg)
        for fig in figs:
            print(f"[OK] visualization -> {fig}")


if __name__ == "__main__":
    main()
