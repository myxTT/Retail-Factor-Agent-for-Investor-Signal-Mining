# Retail Factor Agent Reference

## 参数

`python -m retail_factor_agent.pipeline [options]`

- `--all`: 跑全流程（默认）
- `--wind`: 执行 Wind process/merge
- `--wind-fetch`: 执行 Wind 重新下载（需Wind可用）
- `--crawl`: 仅爬取/抽样
- `--llm`: 仅LLM抽取
- `--train`: 仅模型训练
- `--analyze`: 仅相关性分析
- `--viz`: 仅可视化
- `--sample-size`: 抽样条数，默认 5000
- `--start-date`: 起始日期，默认 `2020-01-01`
- `--end-date`: 结束日期，默认 `2024-12-31`
- `--min-chars`: 最小文本字数过滤
- `--allow-ai`: 不剔除AI生成文本
- `--allow-announcement`: 不剔除公告文本
- `--no-logic-filter`: 不要求文本含逻辑
- `--symbols`: 在线爬取兜底股票代码（逗号分隔）
- `--source-csv`: 指定帖子源文件
- `--llm-model`: 模型名
- `--llm-base-url`: OpenAI兼容接口地址
- `--llm-workers`: 并发数

## 产物

- `workspace/data/posts_sample_<start>_<end>_<n>.csv`
- `workspace/outputs/llm_extracted.jsonl`
- `workspace/outputs/llm_factor_table.csv`
- `workspace/outputs/training_master_table_filtered.csv`
- `workspace/outputs/ml_metrics.csv`
- `workspace/outputs/factor_weights.csv`
- `workspace/outputs/factor_correlation.csv`
- `workspace/outputs/user_factor_analysis.csv`
- `workspace/outputs/viz_model_metrics.png`
- `workspace/outputs/viz_factor_weights_top20.png`
- `workspace/outputs/viz_factor_corr_top20.png`
- `workspace/outputs/viz_user_prediction_distribution.png`
- `workspace/models/best_model.joblib`

## 白名单机制

- 白名单字段：`analysis_results/matched_data_2024.csv` 中 `factor_*_effect`
- LLM Prompt 限制 + 后处理过滤双保险

