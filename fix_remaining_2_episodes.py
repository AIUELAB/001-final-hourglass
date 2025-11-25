#!/usr/bin/env python3
"""
残り2件のエピソードを修正

EP010: 年号削除
EP031: 主観表現削除

著者: Claude Code
日付: 2025-10-01
"""

import csv
from unified_validation_system_with_persistence import create_validator


def fix_ep010_no_year() -> str:
    """EP010: サカナクション - 年号を削除"""
    return """あなたがバンドを始めるとき、サカナクションは結成5年目でメジャーブレイクを果たした。シングル『アルクアラウンド』がオリコン2位を獲得し、配信100万ダウンロードを突破。全国ツアー20公演で10万人を動員し、日本のロックシーンに新たな可能性を示した。インディーズから這い上がった5人組の躍進が始まった。"""


def fix_ep031_no_subjective() -> str:
    """EP031: 吉田秀彦 - 主観表現を削除"""
    return """あなたと同じ23歳のとき、吉田秀彦はバルセロナ五輪で柔道78kg級金メダルを獲得した。決勝でハンガリーのコバーチ・ヨジェフを背負投で破り、全5試合を一本勝ちで制覇。試合時間の合計はわずか11分38秒という記録を達成した。世界選手権3連覇と合わせて、柔道界の頂点に立った。"""


def main():
    """メイン処理"""
    input_csv = "episodes_final_fixed_20251001.csv"
    output_csv = "episodes_final_perfect_20251001.csv"

    print("="*80)
    print("残り2件のエピソードを修正")
    print("="*80 + "\n")

    # CSVを読み込み
    with open(input_csv, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # 修正対象
    fixes = {
        'EP010': ('サカナクション', fix_ep010_no_year()),
        'EP031': ('吉田秀彦', fix_ep031_no_subjective())
    }

    validator = create_validator()
    fixed_count = 0

    for episode_id, (name, new_text) in fixes.items():
        # 該当行を見つける
        for row in rows:
            if row['episode_id'] == episode_id:
                print(f"修正中: {episode_id} ({name})")
                print(f"  元: {row['episode_text'][:60]}...")
                print(f"  新: {new_text[:60]}...")

                # 検証
                episode_dict = {
                    "episode_id": episode_id,
                    "person_name": name,
                    "episode_text": new_text,
                    "episode_age": int(row['episode_age']),
                    "user_age": int(row['episode_age']),
                    "category": row.get('category', '不明')
                }

                result = validator.validate_episode(episode_dict)

                if result.is_valid:
                    row['episode_text'] = new_text
                    row['character_count'] = len(new_text)
                    row['is_valid'] = True
                    row['violation_count'] = 0
                    fixed_count += 1
                    print(f"  ✅ 修正成功 ({len(new_text)}文字)\n")
                else:
                    print(f"  ❌ 修正失敗")
                    for v in result.violations:
                        print(f"    - {v.message}")
                    print()

                break

    # 出力
    with open(output_csv, 'w', encoding='utf-8-sig', newline='') as f:
        fieldnames = list(rows[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # 最終検証
    valid_count = sum(1 for row in rows if row['is_valid'] == 'True' or row['is_valid'] is True)

    print("="*80)
    print("修正完了")
    print("="*80)
    print(f"\n修正件数: {fixed_count}/2")
    print(f"最終合格率: {valid_count}/100 ({valid_count}%)")

    if valid_count == 100:
        print("\n🎉 全100件のエピソードが完璧になりました！")
    else:
        print(f"\n⚠️ まだ{100-valid_count}件のエピソードに問題があります")

    print(f"\n出力ファイル: {output_csv}")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
