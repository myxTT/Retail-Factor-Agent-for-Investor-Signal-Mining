---
name: retail-factor-agent
description: Builds and runs a retail investor factor agent workflow with crawl/sampling, LLM factor extraction constrained by a whitelist, ML training, factor correlation/weight analysis, and visualization. Use when the user asks to run or extend the retail factor pipeline, generate factor tables from posts, or produce interpretable model outputs for investing research.
---

# Retail Factor Agent

## 适用场景

- 用户要把“散户帖子分析”做成一条可复现 agent 流水线
- 用户要求：爬取帖子、LLM 抽因子、模型训练、因子解释、可视化
- 用户要求抽取因子必须来自历史全因子表

## 工作目录

- 代码目录：`retail_factor_agent/`
- 产物目录：`retail_factor_agent/workspace/`

## 执行步骤

1. 可选执行 Wind 处理（process + merge，必要时再下载）
2. 按用户时间段爬取/读取帖子并清洗（字数、非AI、非公告、含逻辑）
3. 随机抽样（默认5000）
4. 运行 LLM 抽取（只允许白名单因子）
5. 先按同一时间段训练“总表”模型，再分析用户因子
6. 输出相关性、权重、用户因子解释和可视化

默认全流程命令：

```bash
python -m retail_factor_agent.pipeline --all
```

## 关键规则

- 因子白名单必须来自 `analysis_results/matched_data_2024.csv` 的 `factor_*_effect`。
- 若 LLM 返回白名单外因子，必须丢弃。
- 输出宽表需包含 `factor_{name}_effect` + `factor_{name}_value`。
- 每次训练前必须按用户选择时间段重建训练集（总表优先）。
- 不要覆盖原论文主线脚本，只在 `retail_factor_agent/` 内扩展。

## 常用命令

```bash
python -m retail_factor_agent.pipeline --crawl
python -m retail_factor_agent.pipeline --llm
python -m retail_factor_agent.pipeline --train --analyze --viz
python -m retail_factor_agent.pipeline --wind
```

## 依赖与环境

- LLM 环境变量：`LLM_API_KEY`（或 `OPENAI_API_KEY`）
- 可选参数：`--llm-model`、`--llm-base-url`

更多参数与结构见 [reference.md](reference.md)。
