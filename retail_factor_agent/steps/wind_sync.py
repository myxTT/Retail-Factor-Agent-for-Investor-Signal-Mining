from __future__ import annotations

import subprocess

from retail_factor_agent.config import AgentConfig


def run_wind_sync(cfg: AgentConfig, fetch_fresh: bool = False) -> None:
    """
    与 Wind 数据流程对齐：
    - 默认：仅处理已有数据 + 合并因子，不强制重新下载
    - fetch_fresh=True 时才触发 Wind 拉取
    """
    if not cfg.wind_script_path.exists():
        raise FileNotFoundError(f"Wind脚本不存在: {cfg.wind_script_path}")

    if fetch_fresh:
        subprocess.run(["python", str(cfg.wind_script_path)], check=True)

    subprocess.run(["python", str(cfg.wind_script_path), "--process-only"], check=True)
    subprocess.run(["python", str(cfg.wind_script_path), "--merge-factors"], check=True)
