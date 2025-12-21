#!/usr/bin/env python3
"""
PERSON ID 重複検出スクリプト

機能:
1. 英字表記とカタカナ表記の同一人物候補を検出
2. 同一年齢・同一イベントの重複を特定
3. 統合候補リストをJSON形式で出力

使用方法:
    python scripts/detect_person_id_duplicates.py

出力:
    src/reports/logs/duplicate_candidates_YYYYMMDD.json
"""

import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.csv_path_resolver import get_master_csv_path, get_reports_dir


def is_english_name(name: str) -> bool:
    """人物名が英字のみかどうかを判定"""
    # 英字、数字、スペース、特殊記号のみで構成
    english_pattern = r'^[A-Za-z0-9\s\'".,\-()]+$'
    return bool(re.match(english_pattern, name))


def is_katakana_name(name: str) -> bool:
    """人物名にカタカナが含まれるかどうかを判定"""
    katakana_pattern = r"[\u30A0-\u30FF]"
    return bool(re.search(katakana_pattern, name))


def get_name_category(name: str) -> str:
    """人物名のカテゴリを判定"""
    if is_english_name(name):
        return "ENGLISH"
    elif is_katakana_name(name):
        return "KATAKANA"
    else:
        return "OTHER"


def find_duplicate_candidates(df: pd.DataFrame) -> list:
    """
    同一人物の重複候補を検出

    検出ロジック:
    1. 同一年齢で類似カテゴリのエピソードを検出
    2. 英字名とカタカナ名のペアを候補として抽出
    """
    candidates = []

    # ユニークなperson_idとperson_nameの組み合わせを取得
    person_data = (
        df.groupby(["person_id", "person_name"])
        .agg({"age": list, "category": list, "episode_id": "count"})
        .reset_index()
    )
    person_data.columns = ["person_id", "person_name", "ages", "categories", "episode_count"]

    # 人物名カテゴリを付与
    person_data["name_category"] = person_data["person_name"].apply(get_name_category)

    # 英字名のリスト
    english_names = person_data[person_data["name_category"] == "ENGLISH"]
    # カタカナ/日本語名のリスト
    japanese_names = person_data[person_data["name_category"].isin(["KATAKANA", "OTHER"])]

    # 各英字名について、同一年齢のカタカナ名を検索
    for _, en_row in english_names.iterrows():
        en_ages = set(en_row["ages"])

        for _, jp_row in japanese_names.iterrows():
            jp_ages = set(jp_row["ages"])

            # 年齢が重複するか確認
            common_ages = en_ages & jp_ages
            if common_ages:
                # 類似度スコア計算
                similarity_score = len(common_ages) / min(len(en_ages), len(jp_ages))

                if similarity_score >= 0.5:  # 50%以上の年齢一致
                    candidate = {
                        "english_name": en_row["person_name"],
                        "english_id": en_row["person_id"],
                        "english_episodes": int(en_row["episode_count"]),
                        "english_ages": sorted([int(a) for a in en_ages]),
                        "japanese_name": jp_row["person_name"],
                        "japanese_id": jp_row["person_id"],
                        "japanese_episodes": int(jp_row["episode_count"]),
                        "japanese_ages": sorted([int(a) for a in jp_ages]),
                        "common_ages": sorted([int(a) for a in common_ages]),
                        "similarity_score": round(similarity_score, 2),
                        "recommended_canonical": jp_row["person_name"],
                        "recommended_id": jp_row["person_id"],
                        "risk": "HIGH" if similarity_score >= 0.8 else "MEDIUM" if similarity_score >= 0.5 else "LOW",
                    }
                    candidates.append(candidate)

    # スコア順にソート
    candidates.sort(key=lambda x: (-x["similarity_score"], -x["english_episodes"]))

    return candidates


def find_exact_duplicates(df: pd.DataFrame) -> list:
    """
    同一person_nameに複数person_idが存在するケースを検出
    """
    duplicates = []

    # person_nameごとにperson_idをグループ化
    name_groups = df.groupby("person_name")["person_id"].apply(set).reset_index()

    for _, row in name_groups.iterrows():
        ids = row["person_id"]
        if len(ids) > 1:
            duplicates.append(
                {"person_name": row["person_name"], "person_ids": list(ids), "count": len(ids), "risk": "HIGH"}
            )

    return duplicates


def main():
    """メイン処理"""
    print("=" * 60)
    print("PERSON ID 重複検出スクリプト")
    print("=" * 60)

    # CSVを読み込み
    csv_path = get_master_csv_path()
    print(f"\n読み込み中: {csv_path}")

    df = pd.read_csv(csv_path)
    print(f"総レコード数: {len(df):,}")

    # ユニークperson_id数
    unique_persons = df["person_id"].nunique()
    print(f"ユニークPERSON ID数: {unique_persons:,}")

    # 重複候補を検出
    print("\n英字/カタカナ表記の重複候補を検出中...")
    candidates = find_duplicate_candidates(df)

    print(f"検出された候補数: {len(candidates)}")

    # 完全重複を検出
    print("\n同一person_nameの複数ID検出中...")
    exact_duplicates = find_exact_duplicates(df)
    print(f"検出された完全重複: {len(exact_duplicates)}")

    # 結果をまとめる
    result = {
        "timestamp": datetime.now().isoformat(),
        "total_records": len(df),
        "unique_person_ids": unique_persons,
        "duplicate_candidates": candidates,
        "exact_duplicates": exact_duplicates,
        "summary": {
            "english_japanese_pairs": len(candidates),
            "exact_duplicates": len(exact_duplicates),
            "high_risk": len([c for c in candidates if c.get("risk") == "HIGH"]),
            "medium_risk": len([c for c in candidates if c.get("risk") == "MEDIUM"]),
        },
    }

    # レポート出力
    reports_dir = get_reports_dir()
    logs_dir = reports_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = logs_dir / f"duplicate_candidates_{timestamp}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\nレポート出力: {output_path}")

    # サマリ表示
    print("\n" + "=" * 60)
    print("検出結果サマリ")
    print("=" * 60)

    if candidates:
        print("\n■ 英字/カタカナ表記の重複候補（上位10件）:")
        for i, c in enumerate(candidates[:10], 1):
            print(f"  {i}. {c['english_name']} ({c['english_id']}) ≡ {c['japanese_name']} ({c['japanese_id']})")
            print(f"     共通年齢: {c['common_ages']}, リスク: {c['risk']}")

    if exact_duplicates:
        print("\n■ 同一person_nameの複数ID:")
        for d in exact_duplicates:
            print(f"  - {d['person_name']}: {d['person_ids']}")

    print("\n完了")
    return result


if __name__ == "__main__":
    main()
