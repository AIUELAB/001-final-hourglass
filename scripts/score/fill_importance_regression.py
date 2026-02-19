#!/usr/bin/env python3
"""
episode_importance_score / impressiveness_score の NaN値を
回帰モデル（GradientBoosting）で予測補完するスクリプト

既存の非NaN行から学習し、NaN行に対して予測値を適用する。

使用方法:
    # ドライラン（予測のみ、CSVは更新しない）
    python scripts/score/fill_importance_regression.py --dry-run

    # 実行（CSVを上書き更新）
    python scripts/score/fill_importance_regression.py --execute
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.model_selection import cross_val_score

# プロジェクトルート（scripts/score/ から2階層上）
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# パス設定
CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORTS_DIR = PROJECT_ROOT / "src" / "reports"

# 特徴量カラム
FEATURE_COLUMNS = [
    "episode_fame_v6",
    "composite_score",
    "memorability_score",
    "empathy_score",
    "surprise_score",
    "generation_quality_score",
    "educational_value",
    "storytelling_quality",
    "factual_density",
    "celebrity_score_v2",
    "fame_score_v3",
    "iconic_score",
]

# ターゲットごとの設定
TARGET_CONFIGS = {
    "episode_importance_score": {
        "clip_min": 5.0,
        "clip_max": 98.0,
    },
    "impressiveness_score": {
        "clip_min": 5.0,
        "clip_max": 80.0,
    },
}


def load_csv() -> pd.DataFrame:
    """マスターCSVを読み込む"""
    print(f"CSVを読み込み中: {CSV_PATH.name}")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig", low_memory=False)
    print(f"  総レコード数: {len(df):,}")
    return df


def print_nan_stats(df: pd.DataFrame) -> dict:
    """NaN統計を表示し、統計情報を返す"""
    print("\n=== Phase E: episode_importance_score NaN修復 ===\n")
    print("NaN統計:")

    stats = {}
    for target in TARGET_CONFIGS:
        nan_count = df[target].isna().sum()
        total = len(df)
        pct = nan_count / total * 100
        print(f"  {target}: {nan_count:,} / {total:,} ({pct:.1f}%) NaN")
        stats[target] = {"nan_count": nan_count, "total": total, "pct": pct}

    return stats


def train_and_predict(
    df: pd.DataFrame,
    target_col: str,
    clip_min: float,
    clip_max: float,
) -> tuple[np.ndarray, dict, pd.Series]:
    """
    指定ターゲットの回帰モデルを訓練し、NaN行に対して予測値を返す。

    Returns:
        predictions: NaN行に対する予測値
        metrics: CV精度指標
        nan_mask: NaN行のブールマスク
    """
    # NaN / 非NaN の分離
    nan_mask: pd.Series = df[target_col].isna()  # type: ignore[assignment]
    train_df = df[~nan_mask]
    predict_df = df[nan_mask]

    print(f"\n{target_col} 回帰モデル:")
    print(f"  訓練データ: {len(train_df):,} 件")
    print(f"  特徴量数: {len(FEATURE_COLUMNS)}")

    # 特徴量とターゲットの準備
    X_train: np.ndarray = train_df[FEATURE_COLUMNS].to_numpy()  # type: ignore[union-attr]
    y_train: np.ndarray = train_df[target_col].to_numpy()  # type: ignore[union-attr]
    X_predict: np.ndarray = predict_df[FEATURE_COLUMNS].to_numpy()  # type: ignore[union-attr]

    # NaN特徴量を中央値で補完
    imputer = SimpleImputer(strategy="median")
    X_train = imputer.fit_transform(X_train)
    X_predict = imputer.transform(X_predict)  # type: ignore[assignment]

    # モデル定義
    model = GradientBoostingRegressor(
        n_estimators=200,
        max_depth=5,
        random_state=42,
    )

    # 5-fold CV で精度評価
    print("  5-fold CV:")

    cv_r2 = cross_val_score(model, X_train, y_train, cv=5, scoring="r2")
    cv_neg_mae = cross_val_score(model, X_train, y_train, cv=5, scoring="neg_mean_absolute_error")
    cv_neg_mse = cross_val_score(model, X_train, y_train, cv=5, scoring="neg_mean_squared_error")

    cv_mae = -cv_neg_mae
    cv_rmse = np.sqrt(-cv_neg_mse)

    print(f"    R²: {cv_r2.mean():.4f} +/- {cv_r2.std():.4f}")
    print(f"    MAE: {cv_mae.mean():.2f} +/- {cv_mae.std():.2f}")
    print(f"    RMSE: {cv_rmse.mean():.2f} +/- {cv_rmse.std():.2f}")

    metrics = {
        "cv_r2_mean": round(float(cv_r2.mean()), 4),
        "cv_r2_std": round(float(cv_r2.std()), 4),
        "cv_mae_mean": round(float(cv_mae.mean()), 2),
        "cv_mae_std": round(float(cv_mae.std()), 2),
        "cv_rmse_mean": round(float(cv_rmse.mean()), 2),
        "cv_rmse_std": round(float(cv_rmse.std()), 2),
    }

    # 全訓練データでモデルを再訓練
    model.fit(X_train, y_train)

    # NaN行に対して予測
    if len(X_predict) > 0:
        predictions = model.predict(X_predict)
        predictions = np.clip(predictions, clip_min, clip_max)
    else:
        predictions = np.array([])

    return predictions, metrics, nan_mask


def print_distribution(
    df: pd.DataFrame,
    target_col: str,
    predictions: np.ndarray,
    nan_mask: pd.Series,
) -> dict:
    """予測値分布を表示し、統計情報を返す"""
    existing_values = df.loc[~nan_mask, target_col]
    existing_median = float(existing_values.median())

    dist_stats = {
        "existing_median": round(existing_median, 2),
    }

    if len(predictions) > 0:
        predicted_median = float(np.median(predictions))
        predicted_mean = float(np.mean(predictions))
        predicted_min = float(np.min(predictions))
        predicted_max = float(np.max(predictions))
        diff = predicted_median - existing_median

        print(f"  {target_col}:")
        print(f"    既存値中央値: {existing_median:.2f}")
        print(f"    予測値中央値: {predicted_median:.2f}")
        print(f"    差: {diff:.2f}")

        dist_stats.update(
            {
                "predicted_median": round(predicted_median, 2),
                "predicted_mean": round(predicted_mean, 2),
                "predicted_min": round(predicted_min, 2),
                "predicted_max": round(predicted_max, 2),
            }
        )
    else:
        print(f"  {target_col}: NaN行なし（補完不要）")

    return dist_stats


def save_report(report: dict) -> Path:
    """レポートJSONを保存する"""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d")
    report_path = REPORTS_DIR / f"importance_fill_regression_{timestamp}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nレポートを保存しました: {report_path.relative_to(PROJECT_ROOT)}")
    return report_path


def main():
    parser = argparse.ArgumentParser(
        description="episode_importance_score / impressiveness_score のNaN値を回帰モデルで補完"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="予測のみ（CSVは更新しない）",
    )
    group.add_argument(
        "--execute",
        action="store_true",
        help="CSVを上書き更新",
    )
    args = parser.parse_args()

    mode = "dry-run" if args.dry_run else "execute"

    # CSV読み込み
    if not CSV_PATH.exists():
        print(f"ファイルが見つかりません: {CSV_PATH}")
        sys.exit(1)

    df = load_csv()

    # NaN統計の表示
    nan_stats = print_nan_stats(df)

    # レポート初期化
    report: dict = {
        "timestamp": datetime.now().isoformat(),
        "mode": mode,
    }

    # 各ターゲットに対してモデルを訓練・予測
    results = {}
    for target_col, config in TARGET_CONFIGS.items():
        predictions, metrics, nan_mask = train_and_predict(
            df,
            target_col,
            config["clip_min"],
            config["clip_max"],
        )
        results[target_col] = {
            "predictions": predictions,
            "metrics": metrics,
            "nan_mask": nan_mask,
        }

    # 予測値分布の表示
    print("\n予測値分布:")
    for target_col in TARGET_CONFIGS:
        r = results[target_col]
        dist_stats = print_distribution(df, target_col, r["predictions"], r["nan_mask"])

        nan_before = int(nan_stats[target_col]["nan_count"])
        nan_after = nan_before - len(r["predictions"])

        report[target_col] = {
            "total_rows": len(df),
            "nan_before": nan_before,
            "nan_after": max(nan_after, 0),
            **r["metrics"],
            **dist_stats,
        }

    # CSVの更新（--execute時のみ）
    if args.execute:
        print()
        for target_col in TARGET_CONFIGS:
            r = results[target_col]
            if len(r["predictions"]) > 0:
                df.loc[r["nan_mask"], target_col] = r["predictions"]

        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

        print(f"CSVを更新しました: {CSV_PATH.relative_to(PROJECT_ROOT)}")
        for target_col in TARGET_CONFIGS:
            filled = int(nan_stats[target_col]["nan_count"])
            remaining = int(df[target_col].isna().sum())
            print(f"  {target_col}: {filled:,}件を補完（残りNaN: {remaining:,}件）")

        # レポートのnan_afterを実際の残NaN数で更新
        for target_col in TARGET_CONFIGS:
            report[target_col]["nan_after"] = int(df[target_col].isna().sum())
    else:
        print("\n[dry-run] CSVは更新されていません")

    # レポート保存
    save_report(report)


if __name__ == "__main__":
    main()
