from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from retail_factor_agent.config import AgentConfig


def run_factor_analysis(cfg: AgentConfig) -> Path:
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            df = pd.read_csv(cfg.factor_table_path, encoding=enc, low_memory=False)
            break
        except Exception:
            continue
    else:
        df = pd.read_csv(cfg.factor_table_path, low_memory=False)

    if "actual_return" not in df.columns or "actual_direction" not in df.columns:
        raise KeyError("因子分析需要 actual_return 与 actual_direction 列。")

    factors = [c for c in df.columns if c.startswith("factor_") and (c.endswith("_effect") or c.endswith("_value"))]
    out_rows: list[dict[str, float | str]] = []

    y_ret = pd.to_numeric(df["actual_return"], errors="coerce")
    y_dir = (pd.to_numeric(df["actual_direction"], errors="coerce").fillna(0) > 0).astype(float)

    for f in factors:
        x = pd.to_numeric(df[f], errors="coerce")
        v = x.replace([np.inf, -np.inf], np.nan)
        if v.notna().sum() < 20:
            continue
        corr_ret = v.corr(y_ret)
        corr_dir = v.corr(y_dir)
        out_rows.append(
            {
                "factor_feature": f,
                "corr_actual_return": corr_ret,
                "corr_actual_direction": corr_dir,
                "abs_corr_return": abs(corr_ret) if pd.notna(corr_ret) else np.nan,
                "abs_corr_direction": abs(corr_dir) if pd.notna(corr_dir) else np.nan,
            }
        )

    out = pd.DataFrame(out_rows).sort_values("abs_corr_return", ascending=False)
    out_path = cfg.output_dir / "factor_correlation.csv"
    out.to_csv(out_path, index=False, encoding="utf-8-sig")
    return out_path
