#!/usr/bin/env python3
"""
拡充エピソードの再検証スクリプト

定型文禁止ルールを含む統合検証システムで再検証

Author: Claude Code
Date: 2025-10-01
"""

import csv
from datetime import datetime
from unified_validation_system_with_persistence import create_validator


def validate_csv(input_csv: str):
    """CSVファイルの全エピソードを検証"""
    validator = create_validator()

    # CSVを読み込み
    with open(input_csv, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    stats = {
        "total": len(rows),
        "valid": 0,
        "invalid": 0,
        "template_violations": 0,
        "char_count_violations": 0,
        "specificity_violations": 0
    }

    invalid_episodes = []

    print(f"\n{'='*80}")
    print("拡充エピソードの再検証")
    print(f"{'='*80}\n")
    print(f"総エピソード数: {stats['total']}件\n")

    for i, row in enumerate(rows, start=1):
        person_name = row['person_name']
        episode_age = int(row['episode_age'])
        episode_text = row['episode_text']

        # 検証実行
        episode_dict = {
            "episode_id": f"E{i:03d}",
            "person_id": f"P{i:03d}",
            "person_name": person_name,
            "display_name": person_name,
            "episode_text": episode_text,
            "episode_age": episode_age,
            "user_age": episode_age,
            "occupation": row.get('category', '不明'),
            "category": row.get('category', '不明')
        }

        result = validator.validate_episode(episode_dict)

        if result.is_valid:
            stats["valid"] += 1
            row['is_valid'] = True
            row['violation_count'] = 0
        else:
            stats["invalid"] += 1
            row['is_valid'] = False
            row['violation_count'] = len(result.violations)

            # 違反詳細を記録
            violation_types = []
            for v in result.violations:
                if v.rule_name == "template_prohibition":
                    stats["template_violations"] += 1
                    violation_types.append("定型文")
                elif v.rule_name == "character_count":
                    stats["char_count_violations"] += 1
                    violation_types.append("文字数")
                elif v.rule_name == "specificity":
                    stats["specificity_violations"] += 1
                    violation_types.append("具体性")

            invalid_episodes.append({
                "row": i,
                "person_name": person_name,
                "violations": violation_types,
                "text": episode_text[:100]
            })

        # 更新
        row['emotional_impact_score'] = result.emotional_impact_score
        row['specificity_score'] = result.specificity_score

    # 結果表示
    print(f"{'='*80}")
    print("検証結果")
    print(f"{'='*80}\n")
    print(f"✅ 合格: {stats['valid']}件 ({stats['valid']/stats['total']*100:.1f}%)")
    print(f"❌ 不合格: {stats['invalid']}件 ({stats['invalid']/stats['total']*100:.1f}%)")
    print(f"\n【違反内訳】")
    print(f"  定型文違反: {stats['template_violations']}件")
    print(f"  文字数違反: {stats['char_count_violations']}件")
    print(f"  具体性違反: {stats['specificity_violations']}件")

    if invalid_episodes:
        print(f"\n{'='*80}")
        print("不合格エピソード詳細")
        print(f"{'='*80}\n")
        for ep in invalid_episodes:
            print(f"行{ep['row']}: {ep['person_name']}")
            print(f"  違反: {', '.join(ep['violations'])}")
            print(f"  テキスト: {ep['text']}...")
            print()

    # 結果を書き込み
    output_csv = input_csv.replace('.csv', '_validated.csv')
    with open(output_csv, 'w', encoding='utf-8-sig', newline='') as f:
        fieldnames = list(rows[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"{'='*80}")
    print(f"出力ファイル: {output_csv}")
    print(f"{'='*80}\n")

    return stats


def main():
    """メイン処理"""
    input_csv = "episodes_enriched_20251001_144345.csv"

    print("="*80)
    print("拡充エピソードの再検証スクリプト")
    print("="*80)
    print(f"\n入力: {input_csv}")
    print("\n【検証ルール】")
    print("1. 定型文禁止（CRITICAL）")
    print("2. 文字数制限: 130-250文字（CRITICAL）")
    print("3. 具体性: 数値データ・固有名詞必須（CRITICAL）")
    print("4. 年号・日付禁止（CRITICAL）")
    print("5. 主観表現禁止（IMPORTANT）")
    print("="*80)

    stats = validate_csv(input_csv)

    if stats["valid"] == stats["total"]:
        print("🎉 全エピソードが検証に合格しました！")
    else:
        print(f"⚠️  {stats['invalid']}件のエピソードが不合格です。")


if __name__ == "__main__":
    main()
