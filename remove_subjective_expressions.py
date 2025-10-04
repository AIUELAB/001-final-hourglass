#!/usr/bin/env python3
"""
主観的表現を客観的表現に修正
NGワードを検出して事実ベースの表現に置き換える
"""

import csv
import re
from datetime import datetime

# 主観的表現と客観的な置き換え
SUBJECTIVE_TO_OBJECTIVE = {
    # 評価的表現
    "偉大な": "",
    "素晴らしい": "",
    "驚異的な": "",
    "圧倒的な": "",
    "伝説の": "",
    "神様": "第一人者",
    "英雄": "選手",
    "カリスマ": "",
    "天才": "",
    "鬼才": "",
    "最高の": "",
    "究極の": "",
    "完璧な": "",
    "奇跡の": "",
    "感動の": "",

    # 受動的評価
    "愛される": "",
    "尊敬される": "",
    "憧れの": "",
    "国民的": "",

    # 伝聞表現
    "と言われる": "である",
    "とされる": "である",
    "と呼ばれる": "となる",

    # その他の主観的表現
    "歴史的": "",
    "画期的な": "",
    "革新的な": "新しい",
    "衝撃的な": "",
    "センセーショナルな": "",
    "類を見ない": "",
    "前代未聞の": "",
    "空前の": "",
    "唯一無二の": "",
    "不朽の": "",
    "永遠の": "",
    "輝かしい": "",
    "華麗な": "",
    "見事な": "",
    "圧巻の": "",
    "劇的な": "",
}

def remove_subjective_expressions(text: str) -> tuple[str, list]:
    """
    主観的表現を除去して客観的な文章にする

    Returns:
        (修正後のテキスト, 修正箇所のリスト)
    """
    modified_text = text
    changes = []

    # 主観的表現を順番に置換
    for subjective, objective in SUBJECTIVE_TO_OBJECTIVE.items():
        if subjective in modified_text:
            # 置換前後を記録
            before = modified_text
            modified_text = modified_text.replace(subjective, objective)

            # 変更があった場合は記録
            if before != modified_text:
                changes.append(f"{subjective} → {objective if objective else '(削除)'}")

    # 連続するスペースや句点の重複を修正
    modified_text = re.sub(r'\s+', '', modified_text)
    modified_text = re.sub(r'。+', '。', modified_text)
    modified_text = re.sub(r'、+', '、', modified_text)

    # 文頭の接続詞や余分な助詞を削除
    modified_text = re.sub(r'^(また|さらに|そして|しかも)', '', modified_text)

    return modified_text, changes

def check_remaining_subjective(text: str) -> list:
    """
    残っている主観的表現をチェック
    """
    remaining = []

    # パターンベースのチェック
    patterns = [
        r'史上\s*(最高|最強|最大|最小|初|唯一)',
        r'世界\s*(初|最高|最強|一)',
        r'日本\s*(初|最高|最強|一)',
        r'(最も|もっとも)',
        r'極めて',
        r'非常に',
        r'とても',
        r'大変',
        r'すごく',
        r'ものすごく',
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            remaining.append(f"パターン: {pattern}")

    return remaining

def fix_subjective_expressions():
    """主観的表現を修正"""

    print("=" * 60)
    print("主観的表現修正処理")
    print("=" * 60)

    # 最新の修正済みファイルを読み込み
    csv_file = 'episodes_final_no_years_20250923_141000.csv'

    episodes = []
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        episodes = list(reader)

    fixed_count = 0
    fix_log = []

    # 各エピソードを処理
    for episode in episodes:
        person_name = episode['person_name']
        original_text = episode['episode_text']

        # 主観的表現を除去
        fixed_text, changes = remove_subjective_expressions(original_text)

        if changes:
            episode['episode_text'] = fixed_text
            episode['character_count'] = str(len(fixed_text))
            episode['created_date'] = datetime.now().strftime('%Y%m%d_%H%M%S')

            fixed_count += 1
            fix_log.append({
                'person_name': person_name,
                'changes': changes,
                'original_length': len(original_text),
                'fixed_length': len(fixed_text)
            })

            print(f"✅ 修正: {person_name}")
            for change in changes[:3]:  # 最初の3つの変更を表示
                print(f"    - {change}")

    # 修正されたCSVを保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'episodes_objective_only_{timestamp}.csv'

    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        fieldnames = list(episodes[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(episodes)

    print(f"\n修正完了: {fixed_count}件")
    print(f"出力ファイル: {output_file}")

    # 残存する主観的表現のチェック
    print("\n" + "=" * 60)
    print("残存チェック")
    print("=" * 60)

    remaining_count = 0
    for episode in episodes:
        remaining = check_remaining_subjective(episode['episode_text'])
        if remaining:
            remaining_count += 1
            print(f"⚠️ {episode['person_name']}: {', '.join(remaining[:2])}")

    if remaining_count == 0:
        print("✅ すべての主観的表現が除去されました")
    else:
        print(f"⚠️ {remaining_count}件にまだ主観的表現が残っています")

    return output_file, fixed_count

if __name__ == "__main__":
    output_file, count = fix_subjective_expressions()

    if count > 0:
        print(f"\n✅ {count}件のエピソードから主観的表現を除去しました")