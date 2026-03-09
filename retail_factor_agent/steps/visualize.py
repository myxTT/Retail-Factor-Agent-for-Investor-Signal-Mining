from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from retail_factor_agent.config import AgentConfig


def run_visualization(cfg: AgentConfig) -> list[Path]:
    cfg.ensure_dirs()
    fig_paths: list[Path] = []

    metrics_path = cfg.output_dir / "ml_metrics.csv"
    if metrics_path.exists():
        m = pd.read_csv(metrics_path, encoding="utf-8-sig")
        plot_cols = [c for c in ["accuracy", "f1", "precision", "recall", "auc"] if c in m.columns]
        if plot_cols:
            ax = m.set_index("model")[plot_cols].plot(kind="bar", figsize=(10, 5))
            ax.set_title("Model Performance")
            ax.set_ylabel("Score")
            ax.grid(axis="y", alpha=0.3)
            p = cfg.output_dir / "viz_model_metrics.png"
            plt.tight_layout()
            plt.savefig(p, dpi=220)
            plt.close()
            fig_paths.append(p)

    weight_path = cfg.output_dir / "factor_weights.csv"
    if weight_path.exists():
        w = pd.read_csv(weight_path, encoding="utf-8-sig").head(20)
        if not w.empty:
            vals = w["weight"].values
            order = np.argsort(np.abs(vals))[::-1]
            w = w.iloc[order]
            plt.figure(figsize=(10, 6))
            plt.barh(w["feature"], w["weight"])
            plt.gca().invert_yaxis()
            plt.title("Top Factor Weights")
            plt.grid(axis="x", alpha=0.3)
            p = cfg.output_dir / "viz_factor_weights_top20.png"
            plt.tight_layout()
            plt.savefig(p, dpi=220)
            plt.close()
            fig_paths.append(p)

    corr_path = cfg.output_dir / "factor_correlation.csv"
    if corr_path.exists():
        c = pd.read_csv(corr_path, encoding="utf-8-sig").head(20)
        if not c.empty:
            c = c.sort_values("abs_corr_return", ascending=False)
            plt.figure(figsize=(10, 6))
            plt.barh(c["factor_feature"], c["corr_actual_return"])
            plt.gca().invert_yaxis()
            plt.title("Top Factor Correlation with Actual Return")
            plt.grid(axis="x", alpha=0.3)
            p = cfg.output_dir / "viz_factor_corr_top20.png"
            plt.tight_layout()
            plt.savefig(p, dpi=220)
            plt.close()
            fig_paths.append(p)

    user_path = cfg.output_dir / "user_factor_analysis.csv"
    if user_path.exists():
        u = pd.read_csv(user_path, encoding="utf-8-sig")
        if not u.empty and "pred_direction" in u.columns:
            cnt = u["pred_direction"].value_counts()
            plt.figure(figsize=(6, 4))
            cnt.plot(kind="bar")
            plt.title("User Posts Predicted Direction")
            plt.ylabel("Count")
            plt.grid(axis="y", alpha=0.3)
            p = cfg.output_dir / "viz_user_prediction_distribution.png"
            plt.tight_layout()
            plt.savefig(p, dpi=220)
            plt.close()
            fig_paths.append(p)

    return fig_paths
