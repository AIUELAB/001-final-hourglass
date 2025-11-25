#!/usr/bin/env python3
"""
ハイライトエピソード選定スクリプト

各人物の最も重要なエピソードをハイライトとして選定
"""

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
CSV_PATH = PROJECT_ROOT / "MASTER_EPISODES_CURRENT.csv"
BACKUP_PATH = PROJECT_ROOT / "MASTER_EPISODES_CURRENT_backup_before_highlight_assignment.csv"
REPORT_PATH = PROJECT_ROOT / "reports" / f"highlight_assignment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"


def calculate_importance_fallback(row: pd.Series) -> float:
    """
    episode_importance_scoreが欠損している場合の代替重要度スコア計算

    Args:
        row: エピソードの行データ

    Returns:
        代替重要度スコア
    """
    score = 0.0

    # 品質スコア（40%）
    if "composite_score" in row and not pd.isna(row["composite_score"]):
        score += float(row["composite_score"]) * 0.4

    # エピソードタイプ（30%）
    type_weights = {
        "ACHIEVEMENT": 30,
        "TURNING_POINT": 25,
        "CHALLENGE": 20,
        "INNOVATION": 20,
        "FOUNDING": 18,
        "FAMILY": 15,
        "GROWTH": 15,
        "成長": 15,
        "FAILURE": 10,
        "COMEBACK": 10,
    }
    episode_type = str(row.get("episode_type", "")).strip()
    score += type_weights.get(episode_type, 10)

    # 記憶性・共感性・意外性（30%）
    if "記憶性スコア" in row and not pd.isna(row["記憶性スコア"]):
        score += float(row["記憶性スコア"]) * 0.1
    if "共感性スコア" in row and not pd.isna(row["共感性スコア"]):
        score += float(row["共感性スコア"]) * 0.1
    if "意外性スコア" in row and not pd.isna(row["意外性スコア"]):
        score += float(row["意外性スコア"]) * 0.1

    return score


def assign_highlights():
    """ハイライト選定のメイン処理"""

    print("=" * 80)
    print("📋 ハイライトエピソード選定スクリプト")
    print("=" * 80)
    print()

    # Step 1: CSVファイル読み込み
    print("Step 1: CSVファイル読み込み中...")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"  ✅ 読み込み完了: {len(df):,}件")
    print()

    # Step 2: バックアップ作成
    print("Step 2: バックアップ作成中...")
    df.to_csv(BACKUP_PATH, index=False, encoding="utf-8-sig")
    print(f"  ✅ バックアップ作成: {BACKUP_PATH}")
    print()

    # Step 3: 新規フィールド追加
    print("Step 3: 新規フィールド追加中...")
    if "is_highlight" not in df.columns:
        df["is_highlight"] = False
        print("  ✅ 'is_highlight'フィールド追加")
    else:
        print("  ℹ️  'is_highlight'フィールドは既に存在")

    if "highlight_rank" not in df.columns:
        df["highlight_rank"] = None
        print("  ✅ 'highlight_rank'フィールド追加")
    else:
        print("  ℹ️  'highlight_rank'フィールドは既に存在")

    if "highlight_selection_method" not in df.columns:
        df["highlight_selection_method"] = None
        print("  ✅ 'highlight_selection_method'フィールド追加")
    else:
        print("  ℹ️  'highlight_selection_method'フィールドは既に存在")
    print()

    # Step 4: 人物ごとのエピソード数を確認
    print("Step 4: 人物ごとのエピソード数を確認中...")
    episode_counts = df.groupby("person_id").size()
    unique_persons = len(episode_counts)
    print(f"  ユニーク人物数: {unique_persons:,}人")
    print("  エピソード数分布:")
    print(f"    - 1件: {(episode_counts == 1).sum():,}人")
    print(f"    - 2-3件: {((episode_counts >= 2) & (episode_counts <= 3)).sum():,}人")
    print(f"    - 4-5件: {((episode_counts >= 4) & (episode_counts <= 5)).sum():,}人")
    print(f"    - 6件以上: {(episode_counts >= 6).sum():,}人")
    print()

    # Step 5: episode_importance_scoreの確認と補完
    print("Step 5: episode_importance_scoreの確認と補完中...")

    # episode_importance_scoreが欠損しているエピソードを確認
    missing_importance = df["episode_importance_score"].isna().sum()
    print(f"  episode_importance_score欠損数: {missing_importance:,}件")

    if missing_importance > 0:
        print("  代替重要度スコアを計算中...")
        # 代替スコアを計算して一時カラムに格納
        df["importance_score_temp"] = df.apply(
            lambda row: row["episode_importance_score"]
            if not pd.isna(row["episode_importance_score"])
            else calculate_importance_fallback(row),
            axis=1,
        )
        print("  ✅ 代替重要度スコア計算完了")
    else:
        df["importance_score_temp"] = df["episode_importance_score"]
    print()

    # Step 6: ハイライト選定
    print("Step 6: ハイライト選定中...")

    single_episode_count = 0
    multi_episode_count = 0
    total_highlights = 0

    for person_id in df["person_id"].unique():
        person_episodes = df[df["person_id"] == person_id]
        episode_count = len(person_episodes)

        if episode_count == 1:
            # 単一エピソード: 自動的にハイライト
            idx = person_episodes.index[0]
            df.at[idx, "is_highlight"] = True
            df.at[idx, "highlight_rank"] = 1
            df.at[idx, "highlight_selection_method"] = "auto_single"
            single_episode_count += 1
            total_highlights += 1

        else:
            # 複数エピソード: 重要度スコアでソート
            sorted_episodes = person_episodes.sort_values("importance_score_temp", ascending=False)

            # TOP3を選定（エピソード数が3未満の場合は全て）
            top_n = min(3, len(sorted_episodes))

            for rank, (idx, episode) in enumerate(sorted_episodes.head(top_n).iterrows(), 1):
                df.at[idx, "is_highlight"] = True
                df.at[idx, "highlight_rank"] = rank
                df.at[idx, "highlight_selection_method"] = "importance_based"
                total_highlights += 1

            multi_episode_count += 1

    # 一時カラムを削除
    df.drop(columns=["importance_score_temp"], inplace=True)

    print("  ✅ ハイライト選定完了")
    print(f"    - 単一エピソード人物: {single_episode_count:,}人")
    print(f"    - 複数エピソード人物: {multi_episode_count:,}人")
    print(f"    - 総ハイライト数: {total_highlights:,}件")
    print()

    # Step 7: 検証
    print("Step 7: ハイライト選定の検証")
    validation = {
        "total_episodes": int(len(df)),
        "total_persons": int(unique_persons),
        "highlights_assigned": int(df["is_highlight"].sum()),
        "single_episode_persons": int(single_episode_count),
        "multi_episode_persons": int(multi_episode_count),
        "selection_method_distribution": df["highlight_selection_method"].value_counts().to_dict(),
        "highlight_rank_distribution": df["highlight_rank"].value_counts().to_dict(),
    }

    print(f"  総エピソード数: {validation['total_episodes']:,}件")
    print(f"  総人物数: {validation['total_persons']:,}人")
    print(
        f"  ハイライト選定数: {validation['highlights_assigned']:,}件 ({validation['highlights_assigned'] / validation['total_episodes'] * 100:.1f}%)"
    )
    print()

    print("  選定方法別分布:")
    for method, count in validation["selection_method_distribution"].items():
        if method:  # None以外
            pct = count / validation["total_episodes"] * 100
            print(f"    - {method}: {count:,}件 ({pct:.1f}%)")
    print()

    print("  ハイライトランク分布:")
    for rank, count in sorted(validation["highlight_rank_distribution"].items()):
        if rank and not pd.isna(rank):  # None以外
            pct = count / validation["highlights_assigned"] * 100 if validation["highlights_assigned"] > 0 else 0
            print(f"    - Rank {int(rank)}: {count:,}件 ({pct:.1f}%)")
    print()

    # Step 8: CSVファイル保存
    print("Step 8: CSVファイル保存中...")
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"  ✅ 保存完了: {CSV_PATH}")
    print()

    # Step 9: レポート保存
    print("Step 9: レポート保存中...")
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "timestamp": datetime.now().isoformat(),
        "csv_path": str(CSV_PATH),
        "backup_path": str(BACKUP_PATH),
        "validation": validation,
        "highlight_definition": {
            "single_episode_method": "auto_single",
            "multi_episode_method": "importance_based",
            "max_highlights_per_person": 3,
            "version": "1.0",
        },
    }

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"  ✅ レポート保存: {REPORT_PATH}")
    print()

    # サマリー
    print("=" * 80)
    print("✅ ハイライトエピソード選定が完了しました！")
    print("=" * 80)
    print()
    print("📊 サマリー:")
    print(f"  - 総エピソード数: {validation['total_episodes']:,}件")
    print(f"  - 総人物数: {validation['total_persons']:,}人")
    print(f"  - ハイライト選定数: {validation['highlights_assigned']:,}件")
    print(f"  - 選定率: {validation['highlights_assigned'] / validation['total_episodes'] * 100:.1f}%")
    print(f"  - バックアップ: {BACKUP_PATH}")
    print(f"  - レポート: {REPORT_PATH}")
    print()


def show_sample_highlights(n: int = 10):
    """サンプルのハイライト選定を表示"""
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    print("=" * 80)
    print("📋 サンプルハイライト選定")
    print("=" * 80)
    print()

    # 複数エピソードを持つ人物のサンプル
    multi_episode_persons = df.groupby("person_id").filter(lambda x: len(x) > 1)
    sample_persons = multi_episode_persons["person_id"].unique()[:5]

    for person_id in sample_persons:
        person_episodes = df[df["person_id"] == person_id].sort_values("highlight_rank")
        person_name = person_episodes.iloc[0]["person_name"]

        print(f"【{person_name}】({len(person_episodes)}件のエピソード)")
        for _, episode in person_episodes.iterrows():
            is_highlight = "★" if episode["is_highlight"] else "  "
            rank = f"Rank {int(episode['highlight_rank'])}" if not pd.isna(episode["highlight_rank"]) else "---"
            method = str(episode["highlight_selection_method"]) if episode["highlight_selection_method"] else "---"
            age = episode["age"]
            slot = int(episode["slot"]) if not pd.isna(episode["slot"]) else "---"
            slot_str = str(slot)
            print(
                f"  {is_highlight} {rank:7s} | {method:20s} | {age:.0f}歳 (slot {slot_str}) | {episode['episode_text'][:60]}..."
            )
        print()


if __name__ == "__main__":
    assign_highlights()
    print()
    show_sample_highlights()
