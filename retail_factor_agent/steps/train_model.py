from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from retail_factor_agent.config import AgentConfig


def _read_labeled_data(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False)
        except Exception:
            continue
    return pd.read_csv(path, low_memory=False)


def _filter_by_date_range(df: pd.DataFrame, start_date: str, end_date: str) -> pd.DataFrame:
    date_col = None
    for c in ("post_publish_time", "post_date", "date", "日期"):
        if c in df.columns:
            date_col = c
            break
    if date_col is None:
        return df
    t = pd.to_datetime(df[date_col], errors="coerce")
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    out = df[t.between(start, end, inclusive="both")].copy()
    return out if not out.empty else df


def _prepare_xy(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    effect_cols = [c for c in df.columns if c.startswith("factor_") and c.endswith("_effect")]
    value_cols = [c for c in df.columns if c.startswith("factor_") and c.endswith("_value")]
    feature_cols = sorted(set(effect_cols + value_cols))
    X = df[feature_cols].copy()
    for c in X.columns:
        X[c] = pd.to_numeric(X[c], errors="coerce")
    X = X.replace([np.inf, -np.inf], np.nan).fillna(0.0)

    if "actual_direction" not in df.columns:
        raise KeyError("训练数据缺少 actual_direction 列。")
    y = (pd.to_numeric(df["actual_direction"], errors="coerce").fillna(0) > 0).astype(int)
    return X, y, feature_cols


def _time_split(df: pd.DataFrame, ratio: float = 0.8) -> tuple[np.ndarray, np.ndarray]:
    if "post_publish_time" in df.columns:
        t = pd.to_datetime(df["post_publish_time"], errors="coerce")
        idx = np.argsort(t.fillna(pd.Timestamp("1900-01-01")).values)
    else:
        idx = np.arange(len(df))
    split = int(len(idx) * ratio)
    return idx[:split], idx[split:]


def _metric_dict(y_true: pd.Series, y_pred: np.ndarray, y_prob: np.ndarray, model_name: str) -> dict[str, Any]:
    return {
        "model": model_name,
        "accuracy": accuracy_score(y_true, y_pred),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "auc": roc_auc_score(y_true, y_prob) if len(np.unique(y_true)) > 1 else np.nan,
    }


def run_training(cfg: AgentConfig, infer_table_path: Path | None = None) -> tuple[Path, Path, Path]:
    cfg.ensure_dirs()
    df_all = _read_labeled_data(cfg.factor_table_path)
    df = _filter_by_date_range(df_all, cfg.start_date, cfg.end_date)
    train_base_path = cfg.output_dir / "training_master_table_filtered.csv"
    df.to_csv(train_base_path, index=False, encoding="utf-8-sig")
    X, y, feature_cols = _prepare_xy(df)
    tr_idx, te_idx = _time_split(df, ratio=0.8)

    X_tr, X_te = X.iloc[tr_idx], X.iloc[te_idx]
    y_tr, y_te = y.iloc[tr_idx], y.iloc[te_idx]

    lr = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=2000, class_weight="balanced")),
        ]
    )
    rf = RandomForestClassifier(
        n_estimators=500,
        max_depth=12,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced_subsample",
    )

    models = {"logistic": lr, "random_forest": rf}
    metrics: list[dict[str, Any]] = []
    best_name = ""
    best_model = None
    best_f1 = -1.0

    for name, model in models.items():
        model.fit(X_tr, y_tr)
        pred = model.predict(X_te)
        prob = model.predict_proba(X_te)[:, 1]
        m = _metric_dict(y_te, pred, prob, name)
        metrics.append(m)
        if m["f1"] > best_f1:
            best_f1 = m["f1"]
            best_name = name
            best_model = model

    metrics_path = cfg.output_dir / "ml_metrics.csv"
    pd.DataFrame(metrics).sort_values("f1", ascending=False).to_csv(metrics_path, index=False, encoding="utf-8-sig")

    assert best_model is not None
    model_path = cfg.model_dir / "best_model.joblib"
    joblib.dump({"model_name": best_name, "model": best_model, "features": feature_cols}, model_path)

    # Save factor weights/importances for interpretation
    if best_name == "logistic":
        clf = best_model.named_steps["clf"]
        weights = clf.coef_[0]
    else:
        weights = best_model.feature_importances_
    weight_df = pd.DataFrame({"feature": feature_cols, "weight": weights}).sort_values("weight", key=np.abs, ascending=False)
    weight_path = cfg.output_dir / "factor_weights.csv"
    weight_df.to_csv(weight_path, index=False, encoding="utf-8-sig")

    # Optional inference on newly extracted post factors
    if infer_table_path is not None and infer_table_path.exists():
        infer_df = pd.read_csv(infer_table_path, encoding="utf-8-sig")
        X_inf = infer_df.reindex(columns=feature_cols, fill_value=0).copy()
        for c in X_inf.columns:
            X_inf[c] = pd.to_numeric(X_inf[c], errors="coerce")
        X_inf = X_inf.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        inf_prob = best_model.predict_proba(X_inf)[:, 1]
        inf_pred = (inf_prob >= 0.5).astype(int)
        infer_df["pred_up_prob"] = inf_prob
        infer_df["pred_direction"] = np.where(inf_pred == 1, "上涨", "下跌")
        infer_df.to_csv(cfg.output_dir / "llm_factor_table_with_prediction.csv", index=False, encoding="utf-8-sig")

        # 基于训练出的权重，对用户因子做解释性分析
        weight_map = {r["feature"]: float(r["weight"]) for _, r in weight_df.iterrows()}
        records: list[dict[str, Any]] = []
        for _, row in infer_df.iterrows():
            post_id = row.get("post_id", "")
            contribs: list[tuple[str, float]] = []
            for feat in feature_cols:
                val = pd.to_numeric(row.get(feat, 0), errors="coerce")
                val = 0.0 if pd.isna(val) else float(val)
                w = weight_map.get(feat, 0.0)
                s = val * w
                if abs(s) > 1e-12:
                    contribs.append((feat, s))
            contribs.sort(key=lambda x: abs(x[1]), reverse=True)
            top3 = contribs[:3]
            records.append(
                {
                    "post_id": post_id,
                    "pred_direction": row.get("pred_direction", ""),
                    "pred_up_prob": row.get("pred_up_prob", np.nan),
                    "top_factor_1": top3[0][0] if len(top3) > 0 else "",
                    "top_factor_1_contrib": top3[0][1] if len(top3) > 0 else 0.0,
                    "top_factor_2": top3[1][0] if len(top3) > 1 else "",
                    "top_factor_2_contrib": top3[1][1] if len(top3) > 1 else 0.0,
                    "top_factor_3": top3[2][0] if len(top3) > 2 else "",
                    "top_factor_3_contrib": top3[2][1] if len(top3) > 2 else 0.0,
                }
            )
        pd.DataFrame(records).to_csv(
            cfg.output_dir / "user_factor_analysis.csv",
            index=False,
            encoding="utf-8-sig",
        )

    return metrics_path, model_path, weight_path
