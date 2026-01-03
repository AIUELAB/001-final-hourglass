#!/usr/bin/env python3
"""7軸スコア相関分析スクリプト

7軸スコア間の相関を分析し、冗長性を特定する。

使用方法:
    python scripts/analyze_seven_axis_correlation.py
    python scripts/analyze_seven_axis_correlation.py --output-image  # ヒートマップ画像出力
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 7軸のカラム名
SEVEN_AXIS_COLUMNS = [
    "記憶性スコア",
    "共感性スコア",
    "意外性スコア",
    "生成品質スコア",
    "教育的価値",
    "ストーリー品質",
    "事実密度",
]

# 短縮名（表示用）
AXIS_SHORT_NAMES = {
    "記憶性スコア": "記憶性",
    "共感性スコア": "共感性",
    "意外性スコア": "意外性",
    "生成品質スコア": "生成品質",
    "教育的価値": "教育的",
    "ストーリー品質": "ストーリー",
    "事実密度": "事実密度",
}


def load_data(csv_path: Path) -> pd.DataFrame:
    """マスターCSVを読み込む"""
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    return df


def calculate_correlation_matrix(df: pd.DataFrame, method: str = "spearman") -> pd.DataFrame:
    """7軸の相関行列を算出

    Args:
        df: データフレーム
        method: 相関係数の種類（spearman / pearson）

    Returns:
        相関行列
    """
    # 7軸のカラムを抽出
    axis_df = df[SEVEN_AXIS_COLUMNS].copy()

    # 数値変換（文字列の場合）
    for col in SEVEN_AXIS_COLUMNS:
        axis_df[col] = pd.to_numeric(axis_df[col], errors="coerce")

    # 欠損値を除外
    axis_df = axis_df.dropna()

    # 相関行列を算出
    corr_matrix = axis_df.corr(method=method)

    return corr_matrix


def find_high_correlation_pairs(corr_matrix: pd.DataFrame, threshold: float = 0.7) -> list:
    """高相関ペアを特定

    Args:
        corr_matrix: 相関行列
        threshold: 高相関とみなす閾値

    Returns:
        高相関ペアのリスト [(軸1, 軸2, 相関係数), ...]
    """
    pairs = []
    columns = corr_matrix.columns.tolist()

    for i in range(len(columns)):
        for j in range(i + 1, len(columns)):
            r = corr_matrix.iloc[i, j]
            if abs(r) >= threshold:
                pairs.append((columns[i], columns[j], r))

    # 相関係数の絶対値で降順ソート
    pairs.sort(key=lambda x: abs(x[2]), reverse=True)
    return pairs


def print_correlation_matrix(corr_matrix: pd.DataFrame):
    """相関行列をコンソールに出力（短縮名で表示）"""
    # 短縮名に変換
    renamed = corr_matrix.rename(index=AXIS_SHORT_NAMES, columns=AXIS_SHORT_NAMES)

    print("\n" + "=" * 60)
    print("7軸スコア相関行列（Spearman）")
    print("=" * 60)

    # ヘッダー
    header = "         " + " ".join(f"{name:>8}" for name in renamed.columns)
    print(header)
    print("-" * len(header))

    # 各行
    for row_name in renamed.index:
        row_values = " ".join(f"{renamed.loc[row_name, col]:>8.3f}" for col in renamed.columns)
        print(f"{row_name:>8} {row_values}")

    print("=" * 60)


def print_statistics(df: pd.DataFrame):
    """7軸の基本統計量を出力"""
    print("\n" + "=" * 60)
    print("7軸スコア基本統計量")
    print("=" * 60)

    # 7軸のカラムを抽出
    axis_df = df[SEVEN_AXIS_COLUMNS].copy()
    for col in SEVEN_AXIS_COLUMNS:
        axis_df[col] = pd.to_numeric(axis_df[col], errors="coerce")

    stats = axis_df.describe()

    for col in SEVEN_AXIS_COLUMNS:
        short_name = AXIS_SHORT_NAMES[col]
        print(f"\n{short_name}:")
        print(f"  件数: {stats.loc['count', col]:.0f}")
        print(f"  平均: {stats.loc['mean', col]:.2f}")
        print(f"  標準偏差: {stats.loc['std', col]:.2f}")
        print(f"  最小: {stats.loc['min', col]:.1f}")
        print(f"  最大: {stats.loc['max', col]:.1f}")


def save_heatmap(corr_matrix: pd.DataFrame, output_path: Path):
    """ヒートマップ画像を保存"""
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns

        # 日本語フォント設定
        plt.rcParams["font.family"] = "Hiragino Sans"

        # 短縮名に変換
        renamed = corr_matrix.rename(index=AXIS_SHORT_NAMES, columns=AXIS_SHORT_NAMES)

        # ヒートマップ作成
        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(
            renamed,
            annot=True,
            fmt=".3f",
            cmap="RdYlBu_r",
            center=0,
            vmin=-1,
            vmax=1,
            square=True,
            ax=ax,
        )
        ax.set_title("7軸スコア相関行列（Spearman）", fontsize=14)

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close()

        print(f"\nヒートマップを保存しました: {output_path}")

    except ImportError:
        print("\n警告: matplotlib/seaborn がインストールされていないため、ヒートマップを出力できません。")
        print("pip install matplotlib seaborn でインストールしてください。")


def main():
    parser = argparse.ArgumentParser(description="7軸スコア相関分析")
    parser.add_argument(
        "--csv",
        type=Path,
        default=PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv",
        help="マスターCSVのパス",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.7,
        help="高相関とみなす閾値（デフォルト: 0.7）",
    )
    parser.add_argument(
        "--output-image",
        action="store_true",
        help="ヒートマップ画像を出力",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "reports",
        help="出力ディレクトリ（デフォルト: reports/）",
    )

    args = parser.parse_args()

    # データ読み込み
    print(f"データを読み込んでいます: {args.csv}")
    df = load_data(args.csv)
    print(f"総エピソード数: {len(df):,}")

    # 基本統計量
    print_statistics(df)

    # 相関行列算出
    corr_matrix = calculate_correlation_matrix(df, method="spearman")

    # 相関行列出力
    print_correlation_matrix(corr_matrix)

    # 高相関ペア特定
    high_corr_pairs = find_high_correlation_pairs(corr_matrix, threshold=args.threshold)

    print("\n" + "=" * 60)
    print(f"高相関ペア（|r| >= {args.threshold}）")
    print("=" * 60)

    if high_corr_pairs:
        for axis1, axis2, r in high_corr_pairs:
            short1 = AXIS_SHORT_NAMES[axis1]
            short2 = AXIS_SHORT_NAMES[axis2]
            print(f"  {short1} <-> {short2}: r = {r:.3f}")

        print(f"\n警告: {len(high_corr_pairs)}組の高相関ペアが見つかりました。")
        print("これらの軸は同じ特徴を測定している可能性があります。")
    else:
        print("  高相関ペアは見つかりませんでした。")
        print("  7軸は比較的独立しています。")

    # 中程度相関ペア（参考）
    mid_corr_pairs = find_high_correlation_pairs(corr_matrix, threshold=0.5)
    mid_corr_pairs = [p for p in mid_corr_pairs if abs(p[2]) < args.threshold]

    if mid_corr_pairs:
        print("\n" + "-" * 60)
        print(f"参考: 中程度相関ペア（0.5 <= |r| < {args.threshold}）")
        print("-" * 60)
        for axis1, axis2, r in mid_corr_pairs:
            short1 = AXIS_SHORT_NAMES[axis1]
            short2 = AXIS_SHORT_NAMES[axis2]
            print(f"  {short1} <-> {short2}: r = {r:.3f}")

    # ヒートマップ出力
    if args.output_image:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = args.output_dir / "seven_axis_correlation_heatmap.png"
        save_heatmap(corr_matrix, output_path)

    # CSVエクスポート
    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_output = args.output_dir / "seven_axis_correlation_matrix.csv"
    corr_matrix.to_csv(csv_output, encoding="utf-8-sig")
    print(f"\n相関行列をCSVに保存しました: {csv_output}")

    print("\n分析完了")


if __name__ == "__main__":
    main()
