#!/usr/bin/env python3
"""
最終データ検証スクリプト
すべての修正後のデータ品質を包括的に検証
"""

import pandas as pd
import json
from datetime import datetime
from pathlib import Path

def validate_final_data():
    """最終データの包括的検証"""
    print("="*60)
    print("📊 最終データ品質検証")
    print("="*60)

    # データ読み込み
    csv_file = "ultra_think_EPISODE_FINAL_20250901_020106_fixed.csv"
    df = pd.read_csv(csv_file)
    print(f"📂 データ読み込み: {len(df)}件")

    validation_results = {
        "timestamp": datetime.now().isoformat(),
        "total_records": len(df),
        "tests": [],
        "issues": [],
        "quality_score": 100.0
    }

    # 1. entity_type検証
    print("\n1️⃣ entity_type検証:")
    entity_null_count = df['entity_type'].isna().sum()
    entity_fill_rate = (len(df) - entity_null_count) / len(df) * 100
    print(f"  充填率: {entity_fill_rate:.1f}%")
    print(f"  NULL数: {entity_null_count}件")

    entity_dist = df['entity_type'].value_counts()
    print("  分布:")
    for entity_type, count in entity_dist.items():
        print(f"    {entity_type}: {count}件 ({count/len(df)*100:.1f}%)")

    validation_results["tests"].append({
        "name": "entity_type充填率",
        "result": "PASS" if entity_fill_rate == 100 else "FAIL",
        "value": float(entity_fill_rate),
        "expected": 100
    })

    if entity_fill_rate < 100:
        validation_results["issues"].append(f"entity_typeに{entity_null_count}件のNULLが存在")
        validation_results["quality_score"] -= 20

    # 2. 組織レコードチェック
    print("\n2️⃣ 組織レコードチェック:")
    org_count = (df['entity_type'] == 'organization').sum()
    print(f"  組織レコード数: {org_count}件")

    validation_results["tests"].append({
        "name": "組織レコード除外",
        "result": "PASS" if org_count == 0 else "FAIL",
        "value": int(org_count),
        "expected": 0
    })

    if org_count > 0:
        validation_results["issues"].append(f"組織レコードが{org_count}件残存")
        validation_results["quality_score"] -= 10

    # 3. グループ分類検証
    print("\n3️⃣ グループ分類検証:")
    groups = df[df['entity_type'] == 'group']
    print(f"  グループ数: {len(groups)}件")

    expected_groups = ['嵐', 'ニュージーンズ', 'ビッグバン']
    for group_name in expected_groups:
        group_record = df[df['person_name_ja'] == group_name]
        if not group_record.empty:
            entity_type = group_record.iloc[0]['entity_type']
            status = "✅" if entity_type == 'group' else "❌"
            print(f"    {status} {group_name}: {entity_type}")

            if entity_type != 'group':
                validation_results["issues"].append(f"{group_name}が{entity_type}として誤分類")
                validation_results["quality_score"] -= 5

    # 4. person_name_display検証
    print("\n4️⃣ person_name_display検証:")
    display_null_count = df['person_name_display'].isna().sum()
    display_fill_rate = (len(df) - display_null_count) / len(df) * 100
    print(f"  充填率: {display_fill_rate:.1f}%")

    # 特定のチェック
    check_cases = [
        ('P003266', '常田大希', 'King Gnu'),  # バンドメンバー
        ('P002276', '千原ジュニア', '千原兄弟'),  # お笑いコンビ
        ('P001381', 'ヨンジュン', None),  # 韓国アーティスト
        ('P001159', 'ヘチャン', None),  # 韓国アーティスト
        ('P000783', 'スングァン', None),  # 韓国アーティスト
    ]

    print("\n  個別検証:")
    for person_id, expected_name, expected_group in check_cases:
        record = df[df['person_id'] == person_id]
        if not record.empty:
            display_name = record.iloc[0]['person_name_display']
            if expected_group:
                expected_display = f"{expected_name} ({expected_group})"
                status = "✅" if display_name == expected_display else "⚠️"
            else:
                # 韓国アーティストは日本語名が含まれていればOK
                status = "✅" if expected_name in str(display_name) else "⚠️"
            print(f"    {status} {person_id}: {display_name}")

            if status == "⚠️":
                validation_results["issues"].append(f"{person_id}のdisplay名が不適切: {display_name}")
                validation_results["quality_score"] -= 2

    # 5. 必須フィールド検証
    print("\n5️⃣ 必須フィールド検証:")
    required_fields = ['person_id', 'person_name_ja', 'entity_type']
    for field in required_fields:
        null_count = df[field].isna().sum()
        fill_rate = (len(df) - null_count) / len(df) * 100
        status = "✅" if fill_rate == 100 else "❌"
        print(f"  {status} {field}: {fill_rate:.1f}%")

        validation_results["tests"].append({
            "name": f"{field}充填率",
            "result": "PASS" if fill_rate == 100 else "FAIL",
            "value": float(fill_rate),
            "expected": 100
        })

        if fill_rate < 100:
            validation_results["issues"].append(f"{field}に{null_count}件のNULLが存在")
            validation_results["quality_score"] -= 10

    # 6. 韓国アーティスト名検証
    print("\n6️⃣ 韓国アーティスト名検証:")
    korean_artists = df[df['nationality'] == '韓国']
    english_display = korean_artists[korean_artists['person_name_display'].str.match('^[A-Za-z]+$', na=False)]
    print(f"  韓国アーティスト総数: {len(korean_artists)}件")
    print(f"  英語表記のまま: {len(english_display)}件")

    if len(english_display) > 0:
        print("  英語表記の例:")
        for idx, row in english_display.head(5).iterrows():
            print(f"    - {row['person_id']}: {row['person_name_display']}")
        validation_results["issues"].append(f"韓国アーティスト{len(english_display)}件が英語表記のまま")
        validation_results["quality_score"] -= min(len(english_display) * 0.5, 10)

    # 7. 特定問題IDの最終確認
    print("\n7️⃣ 報告された問題の最終確認:")
    problem_ids = {
        'P015953': 'マルクス・アウレリウス',  # IUではない
        'P015898': 'ニュージーンズ',  # グループ
        'P015901': 'ビッグバン',  # グループ
        'P003218': '嵐',  # グループ
        'P015757': '世界食糧計画'  # 削除済み
    }

    for pid, expected in problem_ids.items():
        record = df[df['person_id'] == pid]
        if pid == 'P015757':  # 削除されているべき
            if record.empty:
                print(f"  ✅ {pid}: 正しく削除済み")
            else:
                print(f"  ❌ {pid}: まだ存在（削除されていない）")
                validation_results["issues"].append(f"{pid}（組織）が削除されていない")
                validation_results["quality_score"] -= 5
        else:
            if not record.empty:
                row = record.iloc[0]
                display_name = row['person_name_display']
                entity_type = row['entity_type']

                # 期待される条件のチェック
                issues = []
                if pid in ['P015898', 'P015901', 'P003218'] and entity_type != 'group':
                    issues.append(f"entity_type={entity_type}（groupであるべき）")
                if pid == 'P015953' and display_name == 'IU':
                    issues.append(f"display名がIU（{expected}であるべき）")

                if issues:
                    print(f"  ❌ {pid}: {', '.join(issues)}")
                    for issue in issues:
                        validation_results["issues"].append(f"{pid}: {issue}")
                        validation_results["quality_score"] -= 3
                else:
                    print(f"  ✅ {pid}: OK ({display_name}, {entity_type})")

    # 最終スコア計算
    validation_results["quality_score"] = max(0, validation_results["quality_score"])

    # 結果サマリー
    print("\n" + "="*60)
    print("📊 検証結果サマリー")
    print("="*60)

    passed_tests = sum(1 for t in validation_results["tests"] if t["result"] == "PASS")
    total_tests = len(validation_results["tests"])
    print(f"✅ 合格テスト: {passed_tests}/{total_tests}")
    print(f"❌ 検出された問題: {len(validation_results['issues'])}件")
    print(f"📈 品質スコア: {validation_results['quality_score']:.1f}/100")

    if validation_results["issues"]:
        print("\n⚠️ 主な問題:")
        for issue in validation_results["issues"][:10]:
            print(f"  - {issue}")

    # 結果を保存
    with open('final_validation_report.json', 'w', encoding='utf-8') as f:
        json.dump(validation_results, f, ensure_ascii=False, indent=2)
    print(f"\n📝 検証レポート保存: final_validation_report.json")

    return validation_results

if __name__ == "__main__":
    results = validate_final_data()

    if results["quality_score"] >= 90:
        print("\n🎉 データ品質検証合格！")
    elif results["quality_score"] >= 70:
        print("\n⚠️ データ品質は改善されましたが、まだ問題があります")
    else:
        print("\n❌ データ品質に重大な問題があります")
