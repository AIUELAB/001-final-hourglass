#!/usr/bin/env python3
"""
統合マッピングを生成するスクリプト。
分析結果のJSONを元に、正式名を確定版に更新した統合マッピングを作成。
"""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

# パス設定
ANALYSIS_JSON = Path("src/reports/person_duplicate_clusters.json")
OUTPUT_JSON = Path("src/reports/person_merge_mapping.json")
MASTER_CSV = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")

# 例外（分離維持）
EXCEPTIONS = {
    "P777A8A2",  # 森田一義
    "P1A40E23",  # タモリ
}

# 正式名の上書き（ユーザー承認済み）
NAME_OVERRIDES = {
    # キング牧師系 → キング牧師
    "マルティン・ルター・キング・ジュニア": "キング牧師",
    "マルティン・ルター・キング": "キング牧師",
    "マーティン・ルーサー・キング": "キング牧師",
    "マーティン・ルーサー・キング・ジュニア": "キング牧師",
    # チャップリン系 → チャーリー・チャップリン
    "チャップリン": "チャーリー・チャップリン",
    "チャールズ・チャップリン": "チャーリー・チャップリン",
    # HIKAKIN/ヒカキン → HIKAKIN
    "ヒカキン": "HIKAKIN",
    # 千原浩史/千原ジュニア → 千原ジュニア
    "千原浩史": "千原ジュニア",
}

# 特定クラスターの正ID上書き（一般的な表記を持つIDを優先）
ID_OVERRIDES = {
    # キング牧師系 → キング牧師のIDを正に
    63: "PDE1EBEB",  # キング牧師
    # チャップリン系 → チャーリー・チャップリンのIDを正に
    30: "P5172E80",  # チャーリー・チャップリン
    # HIKAKIN系 → HIKAKINのIDを正に
    3: "P710BB63",  # HIKAKIN
}


def load_analysis_data():
    """分析結果を読み込み"""
    with open(ANALYSIS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def get_official_name(name: str, cluster_entries: list) -> str:
    """正式名を決定"""
    # 上書きルールがあれば適用
    if name in NAME_OVERRIDES:
        return NAME_OVERRIDES[name]

    # クラスター内の他の名前も確認
    for entry in cluster_entries:
        if entry["name_input"] in NAME_OVERRIDES:
            return NAME_OVERRIDES[entry["name_input"]]

    return name


def generate_merge_mapping():
    """統合マッピングを生成"""
    data = load_analysis_data()
    df = pd.read_csv(MASTER_CSV, low_memory=False)

    # person_id -> episode_count
    episode_counts = df.groupby("person_id").size().to_dict()

    merge_list = []
    skipped = []

    for cluster in data["clusters"]:
        cluster_id = cluster["cluster_id"]
        entries = cluster["entries"]

        # 例外チェック
        cluster_ids = {e["person_id"] for e in entries}
        if cluster_ids & EXCEPTIONS:
            skipped.append(
                {
                    "cluster_id": cluster_id,
                    "reason": "例外（分離維持）",
                    "entries": entries,
                }
            )
            continue

        # CSV存在確認（どちらか一方でも存在すれば統合対象）
        existing_entries = [e for e in entries if e["exists_in_csv"]]
        if len(existing_entries) < 2:
            # 統合不要（片方しか存在しない）
            skipped.append(
                {
                    "cluster_id": cluster_id,
                    "reason": "片方のみ存在",
                    "entries": entries,
                }
            )
            continue

        # 正IDを決定
        if cluster_id in ID_OVERRIDES:
            primary_id = ID_OVERRIDES[cluster_id]
            primary_entry = next((e for e in entries if e["person_id"] == primary_id), None)
            if not primary_entry:
                # 上書きIDがクラスターに存在しない場合はデフォルトロジック
                primary_entry = max(existing_entries, key=lambda e: (e["episode_count"], e["fame_score"]))
                primary_id = primary_entry["person_id"]
        else:
            # デフォルト: エピソード数優先
            primary_entry = max(existing_entries, key=lambda e: (e["episode_count"], e["fame_score"]))
            primary_id = primary_entry["person_id"]

        # 正式名を決定
        official_name = get_official_name(primary_entry["name_csv"] or primary_entry["name_input"], entries)

        # 統合元IDを抽出
        merge_from = [e["person_id"] for e in existing_entries if e["person_id"] != primary_id]

        if merge_from:
            merge_list.append(
                {
                    "cluster_id": cluster_id,
                    "primary_id": primary_id,
                    "official_name": official_name,
                    "merge_from": merge_from,
                    "merge_from_names": [
                        e["name_csv"] or e["name_input"] for e in entries if e["person_id"] in merge_from
                    ],
                    "total_episodes": sum(episode_counts.get(e["person_id"], 0) for e in entries),
                }
            )

    # 千原浩史/千原ジュニアを追加（例外から統合対象に変更）
    chihara_cluster = next(
        (c for c in data["clusters"] if any(e["name_input"] == "千原ジュニア" for e in c["entries"])), None
    )
    if chihara_cluster:
        junior_entry = next(e for e in chihara_cluster["entries"] if e["name_input"] == "千原ジュニア")
        hiroshi_entry = next(e for e in chihara_cluster["entries"] if e["name_input"] == "千原浩史")
        if junior_entry["exists_in_csv"] and hiroshi_entry["exists_in_csv"]:
            merge_list.append(
                {
                    "cluster_id": chihara_cluster["cluster_id"],
                    "primary_id": junior_entry["person_id"],
                    "official_name": "千原ジュニア",
                    "merge_from": [hiroshi_entry["person_id"]],
                    "merge_from_names": ["千原浩史"],
                    "total_episodes": junior_entry["episode_count"] + hiroshi_entry["episode_count"],
                }
            )

    # 出力
    output = {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_merges": len(merge_list),
            "total_skipped": len(skipped),
        },
        "merges": merge_list,
        "skipped": skipped,
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"統合マッピング生成完了: {OUTPUT_JSON}")
    print(f"- 統合対象: {len(merge_list)} クラスター")
    print(f"- スキップ: {len(skipped)} クラスター")

    # 上位10件を表示
    print("\n=== 統合対象 上位10件 ===")
    for m in sorted(merge_list, key=lambda x: x["total_episodes"], reverse=True)[:10]:
        print(f"  #{m['cluster_id']}: {m['official_name']} ← {m['merge_from_names']}")

    return output


if __name__ == "__main__":
    generate_merge_mapping()
