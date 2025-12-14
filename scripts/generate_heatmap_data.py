#!/usr/bin/env python3
"""
ヒートマップデータ生成スクリプト
ダッシュボードv6用の年齢×日ヒートマップデータを生成

使用方法:
    python scripts/generate_heatmap_data.py
    python scripts/generate_heatmap_data.py --output preserved/heatmap_data.json
    python scripts/generate_heatmap_data.py --embed  # HTMLに埋め込み
"""

import argparse
import json
import re
from pathlib import Path

import pandas as pd


def load_csv(csv_path: Path | None = None) -> pd.DataFrame:
    """最新のMASTER CSVを読み込み"""
    if csv_path and csv_path.exists():
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        print(f"📂 読み込み: {csv_path}")
    else:
        # 複数の候補パスを探索（preserved/data/を最優先）
        candidates = [
            Path("preserved/data/MASTER_EPISODES_CURRENT.csv"),
            Path("data/MASTER_EPISODES_CURRENT.csv"),  # シンボリックリンク経由
            Path("preserved/MASTER_EPISODES_CURRENT.csv"),
            Path("MASTER_EPISODES_CURRENT.csv"),
        ]

        for path in candidates:
            if path.exists():
                df = pd.read_csv(path, encoding="utf-8-sig")
                print(f"📂 読み込み: {path}")
                break
        else:
            # パターンマッチで探索
            csv_files = list(Path(".").glob("**/MASTER_EPISODES*.csv"))
            if not csv_files:
                raise FileNotFoundError("MASTER_EPISODES*.csv が見つかりません")
            latest = max(csv_files, key=lambda f: f.stat().st_mtime)
            df = pd.read_csv(latest, encoding="utf-8-sig")
            print(f"📂 読み込み: {latest}")

    print(f"📊 エピソード数: {len(df)}")
    return df


def generate_heatmap_data(df: pd.DataFrame, min_age: int = 0, max_age: int = 90) -> dict:
    """年齢×日(1-365)のヒートマップデータを生成

    Args:
        df: エピソードDataFrame
        min_age: 最小年齢（デフォルト: 0）
        max_age: 最大年齢（デフォルト: 90）
    """

    # 年齢範囲（引数から取得）
    ages = list(range(min_age, max_age + 1))  # 62歳分
    days = list(range(1, 366))  # 365日

    # 年齢と日(slot)でカウント
    # slotが1-365の範囲であることを確認
    df_valid = df[
        (df["age"] >= min_age) & (df["age"] <= max_age) & (df["slot"].notna()) & (df["slot"] >= 1) & (df["slot"] <= 365)
    ].copy()

    df_valid["age"] = df_valid["age"].astype(int)
    df_valid["slot"] = df_valid["slot"].astype(int)

    # グループカウント
    counts = df_valid.groupby(["age", "slot"]).size().reset_index(name="count")

    # 2Dマトリクス作成 (ages × days)
    z_matrix = []
    for age in ages:
        row = []
        for day in days:
            count = counts[(counts["age"] == age) & (counts["slot"] == day)]["count"].sum()
            row.append(int(count))
        z_matrix.append(row)

    # カテゴリ別統計
    category_stats = {}
    if "category" in df.columns:
        for cat in df["category"].dropna().unique():
            cat_df = df_valid[df_valid["category"] == cat]
            category_stats[cat] = {
                "count": len(cat_df),
                "ages": sorted(cat_df["age"].unique().tolist()) if len(cat_df) > 0 else [],
            }

    # 全体統計
    target_total = (max_age - min_age + 1) * 365  # 22,630
    in_range_count = len(df_valid)
    total_count = len(df)
    bonus_count = total_count - in_range_count

    # 実在/架空カウント
    real_count = 0
    fictional_count = 0
    if "person_type" in df_valid.columns:
        real_count = len(df_valid[df_valid["person_type"].str.upper().str.contains("REAL", na=False)])
        fictional_count = len(df_valid[df_valid["person_type"].str.upper().str.contains("FICTIONAL", na=False)])

    # 年齢別充足率（14歳〜75歳をダッシュボードで使用）
    age_coverage = {}
    age_counts = df_valid.groupby("age").size()
    for age in ages:
        current = int(age_counts.get(age, 0))
        target = 365  # 各年齢で365日分
        age_coverage[age] = {
            "current": current,
            "target": target,
            "coverage_percent": round((current / target) * 100, 2) if target > 0 else 0,
        }

    coverage_stats = {
        "total_current": in_range_count,
        "total_target": target_total,
        "gap": target_total - in_range_count,
        "overall_coverage_percent": round((in_range_count / target_total) * 100, 2),
        "real_count": real_count,
        "fictional_count": fictional_count,
        "bonus_count": bonus_count,
        "total_all": total_count,
        "age_range": {"min": min_age, "max": max_age},
        "days_range": {"min": 1, "max": 365},
        "age_coverage": age_coverage,
    }

    # カテゴリ別充足率
    category_coverage = []
    if "category" in df_valid.columns:
        for cat, stats in sorted(category_stats.items(), key=lambda x: x[1]["count"], reverse=True):
            category_coverage.append(
                {
                    "name": cat,
                    "count": stats["count"],
                    "percent": round((stats["count"] / in_range_count) * 100, 2) if in_range_count > 0 else 0,
                }
            )

    return {
        "heatmap": {
            "x": [f"{d}日" for d in days],
            "y": [f"{a}歳" for a in ages],
            "z": z_matrix,
            "ages": ages,
            "days": days,
        },
        "coverage_stats": coverage_stats,
        "category_coverage": category_coverage,
        "generated_at": pd.Timestamp.now().isoformat(),
    }


def save_json(data: dict, output_path: Path):
    """JSONファイルに保存"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON保存: {output_path}")


def embed_in_html(data: dict, html_path: Path):
    """HTMLファイルにEMBEDDED_HEATMAP_DATAとして埋め込み"""
    if not html_path.exists():
        raise FileNotFoundError(f"{html_path} が見つかりません")

    content = html_path.read_text(encoding="utf-8")

    # JSON文字列を生成（圧縮形式）
    json_data = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    # 埋め込みパターン
    embed_pattern = r"const EMBEDDED_HEATMAP_DATA = .*?;"
    embed_replacement = f"const EMBEDDED_HEATMAP_DATA = {json_data};"

    # 既存の埋め込みがあれば置換
    if re.search(embed_pattern, content, flags=re.DOTALL):
        new_content = re.sub(embed_pattern, embed_replacement, content, flags=re.DOTALL)
    else:
        # <script>タグの直後に追加
        script_pattern = r"(<script>)"
        new_content = re.sub(
            script_pattern,
            f'\\1\n        // 自動生成: {data["generated_at"]}\n        {embed_replacement}\n',
            content,
            count=1,
        )

    html_path.write_text(new_content, encoding="utf-8")
    print(f"✅ HTML埋め込み完了: {html_path}")


def main():
    parser = argparse.ArgumentParser(description="ヒートマップデータ生成")
    parser.add_argument("--csv", type=Path, help="入力CSVファイル")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("preserved/heatmap_data.json"),
        help="出力JSONファイル（デフォルト: preserved/heatmap_data.json）",
    )
    parser.add_argument("--embed", action="store_true", help="HTMLに埋め込み")
    parser.add_argument(
        "--html", type=Path, default=Path("preserved/episode_database_dashboard_v6.html"), help="埋め込み先HTMLファイル"
    )
    args = parser.parse_args()

    print("=" * 50)
    print("🔄 ヒートマップデータ生成")
    print("=" * 50)

    # CSV読み込み
    df = load_csv(args.csv)

    # ヒートマップデータ生成
    data = generate_heatmap_data(df)

    # 統計表示
    stats = data["coverage_stats"]
    print("\n📈 統計:")
    print(f"  範囲内エピソード: {stats['total_current']:,}")
    print(f"  目標: {stats['total_target']:,}")
    print(f"  達成率: {stats['overall_coverage_percent']}%")
    print(f"  不足数: {stats['gap']:,}")
    print(f"  実在: {stats['real_count']:,}")
    print(f"  架空: {stats['fictional_count']:,}")
    print(f"  ボーナス（範囲外）: {stats['bonus_count']:,}")

    # JSON保存
    save_json(data, args.output)

    # HTML埋め込み
    if args.embed:
        embed_in_html(data, args.html)

    print("\n🎉 完了!")
    return data


if __name__ == "__main__":
    main()
