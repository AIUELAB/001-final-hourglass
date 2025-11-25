#!/usr/bin/env python3
"""
バッチ4エピソードを既存のマスターファイルと統合
74件 + 26件 = 100件の完成版を作成
"""

import csv
from datetime import datetime
from collections import OrderedDict

def merge_episodes():
    """エピソードファイルを統合"""

    print("=" * 60)
    print("エピソードマスターファイル統合処理")
    print("=" * 60)

    # 既存のマスターファイルを読み込み
    master_file = 'episodes_master_20250923_101033.csv'
    batch4_file = 'episodes_batch4_final_20250923_133557.csv'

    all_episodes = []
    person_names = set()

    # 既存エピソードを読み込み
    print(f"\n既存マスター読み込み: {master_file}")
    with open(master_file, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_episodes.append(row)
            person_names.add(row['person_name'])

    existing_count = len(all_episodes)
    print(f"  既存エピソード数: {existing_count}件")

    # 新規エピソードを読み込み
    print(f"\n新規バッチ読み込み: {batch4_file}")
    new_count = 0
    with open(batch4_file, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 重複チェック
            if row['person_name'] not in person_names:
                all_episodes.append(row)
                person_names.add(row['person_name'])
                new_count += 1

    print(f"  新規エピソード数: {new_count}件")

    # 人名順でソート（日本語配慮）
    all_episodes.sort(key=lambda x: x['person_name'])

    # 統合ファイルを保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'episodes_master_100_complete_{timestamp}.csv'

    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        fieldnames = [
            'person_name', 'user_age', 'episode_age', 'episode_text',
            'character_count', 'category', 'weighted_score', 'is_valid',
            'record_score', 'memory_score', 'empathy_score',
            'fact_check_status', 'created_date'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_episodes)

    print(f"\n✅ 統合完了: {output_file}")
    print(f"   総エピソード数: {len(all_episodes)}件")

    # 統計情報
    print("\n📊 統合後の統計:")

    # カテゴリ別集計
    categories = {}
    for ep in all_episodes:
        cat = ep.get('category', 'general')
        categories[cat] = categories.get(cat, 0) + 1

    print("\nカテゴリ別分布:")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f"  {cat}: {count}件 ({count/len(all_episodes)*100:.1f}%)")

    # スコア統計
    scores = []
    for ep in all_episodes:
        try:
            score = float(ep.get('weighted_score', 8.0))
            scores.append(score)
        except:
            scores.append(8.0)

    if scores:
        print(f"\nスコア統計:")
        print(f"  平均: {sum(scores)/len(scores):.2f}")
        print(f"  最高: {max(scores):.2f}")
        print(f"  最低: {min(scores):.2f}")

    # 文字数統計
    char_counts = []
    for ep in all_episodes:
        try:
            count = int(ep.get('character_count', 150))
            char_counts.append(count)
        except:
            char_counts.append(150)

    if char_counts:
        print(f"\n文字数統計:")
        print(f"  平均: {sum(char_counts)/len(char_counts):.1f}文字")
        print(f"  最小: {min(char_counts)}文字")
        print(f"  最大: {max(char_counts)}文字")

        valid_count = sum(1 for c in char_counts if 132 <= c <= 250)
        print(f"  基準適合: {valid_count}/{len(char_counts)}件 ({valid_count/len(char_counts)*100:.1f}%)")

    return output_file, len(all_episodes)

if __name__ == "__main__":
    try:
        output_file, total_count = merge_episodes()

        print("\n" + "=" * 60)
        if total_count == 100:
            print("🎊 祝！100件のエピソード作成完了！")
            print("=" * 60)
            print("\n✅ プロジェクト目標達成")
        elif total_count > 100:
            print(f"✅ 目標超過達成！{total_count}件のエピソード作成完了")
        else:
            print(f"⚠️ あと{100 - total_count}件で目標達成")

        exit(0)
    except Exception as e:
        print(f"\n❌ エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
