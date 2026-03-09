# Retail Factor Agent

一个可复现的散户因子挖掘 Agent：  
从帖子文本中抽取结构化因子，联动历史总表训练模型，并输出可解释分析结果。

## Pipeline（按时间段重训）

1. **Wind 同步（可选）**：处理已有市场数据并合并因子表  
2. **数据获取**：按时间范围读取/爬取帖子  
3. **抽样前清洗**：字数过滤、剔除 AI 生成、剔除公告、要求文本含逻辑  
4. **LLM 抽取**：输出 `因子名称-数值-方向`，仅允许白名单因子  
5. **总表重训**：按同一时间段过滤总因子表并重新训练模型  
6. **用户因子分析**：对帖子级因子做预测与贡献解释  
7. **可视化输出**：指标图、权重图、相关性图、用户预测分布图

## 目录与职责

- `config.py`: 路径和参数配置
- `pipeline.py`: 主入口
- `steps/crawl_posts.py`: 爬虫/清洗/抽样
- `steps/llm_extract.py`: LLM 因子抽取（白名单约束）
- `steps/train_model.py`: 总表训练 + 用户因子解释
- `steps/factor_analysis.py`: 因子相关性分析
- `steps/visualize.py`: 可视化
- `steps/wind_sync.py`: Wind 数据流程衔接
- `workspace/`: 产物目录（自动创建）

## 快速运行

```bash
python -m retail_factor_agent.pipeline --all
```

分步运行示例：

```bash
python -m retail_factor_agent.pipeline --crawl
python -m retail_factor_agent.pipeline --llm
python -m retail_factor_agent.pipeline --train --analyze --viz
```

按时间段与清洗规则运行：

```bash
python -m retail_factor_agent.pipeline --start-date 2021-01-01 --end-date 2023-12-31 --sample-size 5000 --min-chars 120 --crawl --llm --train --analyze --viz
```

仅做 Wind 处理（不重新下载）：

```bash
python -m retail_factor_agent.pipeline --wind
```

## Windows 菜单界面

双击运行：

- `run_retail_factor_agent.bat`

可交互输入时间段、样本量、清洗字数并选择执行模式。

## 环境变量

LLM 抽取步骤需要：

- `LLM_API_KEY`（或 `OPENAI_API_KEY`）
- 可选：`--llm-model`、`--llm-base-url`

## 关键约束

- 因子白名单来自 `analysis_results/matched_data_2024.csv` 的 `factor_*_effect` 列。
- 抽取后还会做二次过滤，确保输出因子只来自白名单。
- 宽表输出包含 `factor_{因子}_effect` 和 `factor_{因子}_value`，用于后续训练与解释分析。
- 每次训练都按用户选择时间段重新过滤总表，先训练总表，再对用户因子做解释分析（`user_factor_analysis.csv`）。

## 关键产物

- `workspace/data/posts_sample_<start>_<end>_<n>.csv`
- `workspace/outputs/llm_factor_table.csv`
- `workspace/outputs/training_master_table_filtered.csv`
- `workspace/outputs/ml_metrics.csv`
- `workspace/outputs/factor_weights.csv`
- `workspace/outputs/factor_correlation.csv`
- `workspace/outputs/user_factor_analysis.csv`
- `workspace/outputs/viz_*.png`
