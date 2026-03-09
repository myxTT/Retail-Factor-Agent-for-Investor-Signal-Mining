# Retail Factor Agent for Investor Signal Mining

一个面向“散户讨论文本 -> 因子结构化 -> 可解释建模”的端到端 Agent 项目。  
目标是把复杂的研究流程产品化为可复现流水线，用于实习/项目展示与后续研究迭代。

## 这个 Agent 在做什么

`Retail Factor Agent` 自动完成以下任务：

1. 按用户选择的时间范围获取/筛选帖子数据
2. 在抽样前做文本清洗（字数、非 AI 生成、非公告、包含逻辑）
3. 调用大模型提取“因子名称-数值-方向”，并强制落在全因子白名单
4. 先基于同时间段“总因子表”重训模型
5. 再对用户帖子因子做预测与解释（贡献度 Top 因子）
6. 生成指标、因子权重、相关性和可视化图

## 核心能力

- **Pipeline 化**：爬取/清洗、LLM 抽取、训练、解释、可视化串成统一命令
- **强约束抽取**：只允许全因子表中的因子名，避免 LLM 自造特征
- **时间段重训**：每次按用户所选日期重新过滤总表训练，保证分析一致性
- **可解释输出**：输出权重、相关性、用户帖子因子贡献
- **可交互运行**：提供 `bat` 菜单界面，非代码用户也可直接操作

## 项目结构

- `retail_factor_agent/`：Agent 主代码
- `retail_factor_agent/steps/`：流程步骤模块
- `retail_factor_agent/workspace/`：运行产物（数据、模型、图表）
- `.cursor/skills/retail-factor-agent/`：Cursor Skill 定义
- `run_retail_factor_agent.bat`：Windows 菜单入口

## 快速开始

### 1) 安装依赖

```bash
pip install -r retail_factor_agent/requirements.txt
```

### 2) 设置大模型密钥

- `LLM_API_KEY`（或 `OPENAI_API_KEY`）

### 3) 一键运行（推荐）

```bash
python -m retail_factor_agent.pipeline --all
```

### 4) Windows 菜单模式

双击：

- `run_retail_factor_agent.bat`

## 常用命令

```bash
# Wind 数据处理（process + merge）
python -m retail_factor_agent.pipeline --wind

# 按时间段执行全分析
python -m retail_factor_agent.pipeline --start-date 2021-01-01 --end-date 2023-12-31 --sample-size 5000 --min-chars 120 --crawl --llm --train --analyze --viz
```

## 关键产物

- `retail_factor_agent/workspace/outputs/llm_factor_table.csv`
- `retail_factor_agent/workspace/outputs/training_master_table_filtered.csv`
- `retail_factor_agent/workspace/outputs/ml_metrics.csv`
- `retail_factor_agent/workspace/outputs/factor_weights.csv`
- `retail_factor_agent/workspace/outputs/factor_correlation.csv`
- `retail_factor_agent/workspace/outputs/user_factor_analysis.csv`
- `retail_factor_agent/workspace/outputs/viz_*.png`

## 说明

- 本仓库默认不包含敏感密钥与大体量中间数据。
- 若用于公开展示，建议仅上传 Agent 代码与示例产物，不上传原始全量数据。
