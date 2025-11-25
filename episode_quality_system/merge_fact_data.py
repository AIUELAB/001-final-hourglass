#!/usr/bin/env python3
"""
事実データを統合してexpanded_person_facts_v2.jsonを作成
"""

import json
from pathlib import Path

def merge_fact_data():
    """既存データと新規データを統合"""

    # 既存データを読み込み
    existing_file = Path("expanded_person_facts.json")
    if existing_file.exists():
        with open(existing_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
    else:
        existing_data = {"persons": {}}

    # 新規データファイルを読み込み
    batch_files = [
        "manual_fact_data_batch1.json",
        "manual_fact_data_batch2.json",
        "manual_fact_data_batch3.json"
    ]

    merged_persons = existing_data.get("persons", {}).copy()

    for batch_file in batch_files:
        if Path(batch_file).exists():
            with open(batch_file, 'r', encoding='utf-8') as f:
                batch_data = json.load(f)
                # 新規データを追加（既存データは上書きしない）
                for person_name, person_data in batch_data.items():
                    if person_name not in merged_persons:
                        merged_persons[person_name] = person_data
                        print(f"✅ 追加: {person_name}")
                    else:
                        print(f"⏭️ スキップ（既存）: {person_name}")

    # 統合データを保存
    output_data = {"persons": merged_persons}
    output_file = "expanded_person_facts_v2.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    # 統計を表示
    print("\n" + "=" * 60)
    print("📊 事実データ統合完了")
    print("=" * 60)
    print(f"既存データ: {len(existing_data.get('persons', {}))}人")
    print(f"統合後データ: {len(merged_persons)}人")
    print(f"新規追加: {len(merged_persons) - len(existing_data.get('persons', {}))}人")
    print(f"\n保存先: {output_file}")

    # カテゴリ別統計
    categories = {}
    for person_name, person_data in merged_persons.items():
        # カテゴリ情報はないので、作品の有無で判定
        if person_data.get("facts", {}).get("works"):
            category = "entertainment/literature"
        elif any(word in str(person_data.get("facts", {}).get("achievements", []))
                for word in ["メダル", "優勝", "記録", "MVP"]):
            category = "sports"
        elif any(word in str(person_data.get("facts", {}).get("achievements", []))
                for word in ["創業", "CEO", "経営"]):
            category = "business"
        elif any(word in str(person_data.get("facts", {}).get("achievements", []))
                for word in ["ノーベル", "理論", "研究"]):
            category = "science"
        else:
            category = "other"

        categories[category] = categories.get(category, 0) + 1

    print("\nカテゴリ別人数:")
    for category, count in sorted(categories.items()):
        print(f"  {category}: {count}人")

if __name__ == "__main__":
    merge_fact_data()
