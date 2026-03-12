@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ==========================================
echo Retail Factor Agent 交互式 Agent 菜单
echo ==========================================
echo.
echo 请选择运行方式:
echo [1] Agent模式(推荐): 输入自然语言需求，自动拆解执行
echo [2] 手动模式: 自己逐项配置参数
set /p ENTRY_MODE=请输入编号(默认1): 
if "%ENTRY_MODE%"=="" set ENTRY_MODE=1

if "%ENTRY_MODE%"=="1" (
  echo.
  set /p REQUIREMENT=请输入你的需求描述(例如: 我想分析2022-2023创业板散户观点并完成训练与可视化): 
  if "%REQUIREMENT%"=="" (
    echo [ERROR] 需求不能为空，退出。
    pause
    exit /b 1
  )
  set /p LLM_BASE_URL=请输入LLM BASE URL(默认https://api.deepseek.com/v1): 
  if "%LLM_BASE_URL%"=="" set LLM_BASE_URL=https://api.deepseek.com/v1
  set /p LLM_MODEL=请输入LLM模型名(默认deepseek-chat): 
  if "%LLM_MODEL%"=="" set LLM_MODEL=deepseek-chat
  set /p LLM_API_KEY=请输入LLM API KEY(可留空, 将使用系统环境变量): 

  set CMD=python -m retail_factor_agent.pipeline --agent --requirement "%REQUIREMENT%" --llm-base-url "%LLM_BASE_URL%" --llm-model "%LLM_MODEL%"
  if not "%LLM_API_KEY%"=="" set CMD=%CMD% --llm-api-key "%LLM_API_KEY%"

  echo.
  echo 即将执行(Agent模式):
  echo %CMD%
  echo.
  %CMD%
  echo.
  echo 运行完成。输出目录:
  echo retail_factor_agent\workspace\outputs
  pause
  exit /b 0
)

echo.
set /p START_DATE=请输入开始日期(YYYY-MM-DD, 默认2020-01-01): 
if "%START_DATE%"=="" set START_DATE=2020-01-01
set /p END_DATE=请输入结束日期(YYYY-MM-DD, 默认2024-12-31): 
if "%END_DATE%"=="" set END_DATE=2024-12-31
set /p SAMPLE_SIZE=请输入抽样数量(默认5000): 
if "%SAMPLE_SIZE%"=="" set SAMPLE_SIZE=5000
set /p MIN_CHARS=请输入最小文本字数(默认100): 
if "%MIN_CHARS%"=="" set MIN_CHARS=100
set /p SOURCE_CSV=请输入帖子源CSV路径(留空走默认本地文件): 
set /p FACTOR_TABLE=请输入用户股票/因子总表CSV路径(留空用默认总表): 

echo.
echo 股票范围:
echo [1] A股全市场(默认)
echo [2] 创业板
echo [3] 科创板
echo [4] 主板
echo [5] 自定义股票代码
set /p STOCK_SCOPE_SEL=请输入编号(默认1): 
if "%STOCK_SCOPE_SEL%"=="" set STOCK_SCOPE_SEL=1
set STOCK_SCOPE=a_all
set CUSTOM_SYMBOLS=
if "%STOCK_SCOPE_SEL%"=="2" set STOCK_SCOPE=gem
if "%STOCK_SCOPE_SEL%"=="3" set STOCK_SCOPE=star
if "%STOCK_SCOPE_SEL%"=="4" set STOCK_SCOPE=main_board
if "%STOCK_SCOPE_SEL%"=="5" (
  set STOCK_SCOPE=custom
  set /p CUSTOM_SYMBOLS=请输入股票代码列表(逗号分隔, 如300750,688981): 
)

echo.
echo 爬取来源:
echo [1] 东方财富(默认, akshare, 无需key)
echo [2] 自定义爬虫API(URL+KEY)
set /p CRAWL_SRC=请输入编号(默认1): 
if "%CRAWL_SRC%"=="" set CRAWL_SRC=1
set CRAWL_PROVIDER=eastmoney
set CRAWLER_API_URL=
set CRAWLER_API_KEY=
if "%CRAWL_SRC%"=="2" (
  set CRAWL_PROVIDER=api
  set /p CRAWLER_API_URL=请输入爬虫API URL: 
  set /p CRAWLER_API_KEY=请输入爬虫API KEY(可留空): 
)

echo.
set /p LLM_BASE_URL=请输入LLM BASE URL(默认https://api.deepseek.com/v1): 
if "%LLM_BASE_URL%"=="" set LLM_BASE_URL=https://api.deepseek.com/v1
set /p LLM_MODEL=请输入LLM模型名(默认deepseek-chat): 
if "%LLM_MODEL%"=="" set LLM_MODEL=deepseek-chat
set /p LLM_API_KEY=请输入LLM API KEY(可留空, 将使用系统环境变量): 

echo.
echo 选择执行模式:
echo [1] 全流程(推荐): Wind处理+清洗抽样+LLM+训练+分析+可视化
echo [2] 不跑Wind: 清洗抽样+LLM+训练+分析+可视化
echo [3] 仅清洗抽样
echo [4] 仅LLM抽取
echo [5] 仅训练+分析+可视化
set /p MODE=请输入编号(默认2): 
if "%MODE%"=="" set MODE=2

set CMD=python -m retail_factor_agent.pipeline --start-date %START_DATE% --end-date %END_DATE% --sample-size %SAMPLE_SIZE% --min-chars %MIN_CHARS% --stock-scope %STOCK_SCOPE% --crawl-provider %CRAWL_PROVIDER% --llm-base-url "%LLM_BASE_URL%" --llm-model "%LLM_MODEL%"

if not "%SOURCE_CSV%"=="" set CMD=%CMD% --source-csv "%SOURCE_CSV%"
if not "%FACTOR_TABLE%"=="" set CMD=%CMD% --factor-table-csv "%FACTOR_TABLE%"
if not "%CUSTOM_SYMBOLS%"=="" set CMD=%CMD% --custom-symbols "%CUSTOM_SYMBOLS%"
if not "%CRAWLER_API_URL%"=="" set CMD=%CMD% --crawler-api-url "%CRAWLER_API_URL%"
if not "%CRAWLER_API_KEY%"=="" set CMD=%CMD% --crawler-api-key "%CRAWLER_API_KEY%"
if not "%LLM_API_KEY%"=="" set CMD=%CMD% --llm-api-key "%LLM_API_KEY%"

if "%MODE%"=="1" set CMD=%CMD% --all
if "%MODE%"=="2" set CMD=%CMD% --crawl --llm --train --analyze --viz
if "%MODE%"=="3" set CMD=%CMD% --crawl
if "%MODE%"=="4" set CMD=%CMD% --llm
if "%MODE%"=="5" set CMD=%CMD% --train --analyze --viz

echo.
echo 即将执行:
echo %CMD%
echo.
%CMD%

echo.
echo 运行完成。输出目录:
echo retail_factor_agent\workspace\outputs
pause
