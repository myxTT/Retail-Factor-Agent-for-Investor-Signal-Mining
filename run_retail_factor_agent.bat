@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ==========================================
echo Retail Factor Agent 可视化运行菜单
echo ==========================================
echo.
set /p START_DATE=请输入开始日期(YYYY-MM-DD, 默认2020-01-01): 
if "%START_DATE%"=="" set START_DATE=2020-01-01
set /p END_DATE=请输入结束日期(YYYY-MM-DD, 默认2024-12-31): 
if "%END_DATE%"=="" set END_DATE=2024-12-31
set /p SAMPLE_SIZE=请输入抽样数量(默认5000): 
if "%SAMPLE_SIZE%"=="" set SAMPLE_SIZE=5000
set /p MIN_CHARS=请输入最小文本字数(默认100): 
if "%MIN_CHARS%"=="" set MIN_CHARS=100

echo.
echo 选择执行模式:
echo [1] 全流程(推荐): Wind处理+清洗抽样+LLM+训练+分析+可视化
echo [2] 不跑Wind: 清洗抽样+LLM+训练+分析+可视化
echo [3] 仅清洗抽样
echo [4] 仅LLM抽取
echo [5] 仅训练+分析+可视化
set /p MODE=请输入编号(默认2): 
if "%MODE%"=="" set MODE=2

set CMD=python -m retail_factor_agent.pipeline --start-date %START_DATE% --end-date %END_DATE% --sample-size %SAMPLE_SIZE% --min-chars %MIN_CHARS%

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
