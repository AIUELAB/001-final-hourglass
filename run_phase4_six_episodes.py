#!/usr/bin/env python3
"""
Phase 4評価 - 問題の6エピソードのみ
EP011, EP033, EP035, EP061, EP077, EP079
"""

import csv
from typing import List, Dict
from integrated_episode_evaluator import IntegratedEpisodeEvaluator


# ユーザーが指摘した6つの問題エピソード
PROBLEM_EPISODE_IDS = ['EP011', 'EP033', 'EP035', 'EP061', 'EP077', 'EP079']


def load_problem_episodes(csv_path: str) -> List[Dict]:
    """問題エピソードのみ読み込み"""
    episodes = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['episode_id'] in PROBLEM_EPISODE_IDS:
                episodes.append({
                    'episode_id': row['episode_id'],
                    'person_name': row['person_name'],
                    'episode_age': int(row['episode_age']),
                    'episode_text': row['episode_text'],
                    'category': row.get('category', '')
                })
    return episodes


def main():
    """メイン処理"""

    print("=" * 80)
    print("Phase 4評価 - 問題の6エピソード")
    print("=" * 80)

    input_csv = "episodes_validated_100_20251001.csv"

    print(f"\n入力: {input_csv}")
    print(f"対象: {', '.join(PROBLEM_EPISODE_IDS)}")
    print()

    # 問題エピソードを読み込み
    print("問題エピソードを読み込み中...")
    episodes = load_problem_episodes(input_csv)
    print(f"✅ {len(episodes)}件のエピソードを読み込み\n")

    # NOTE: この処理はClaude Code環境でBrave Search MCPを使って実行されます
    # 各エピソードについて、Brave Searchで定番度を測定します

    print("=" * 80)
    print("Phase 4評価実行")
    print("=" * 80)
    print()

    # 各エピソードを表示して、Claude Codeが処理する準備
    for episode in episodes:
        print(f"エピソードID: {episode['episode_id']}")
        print(f"  人物名: {episode['person_name']}")
        print(f"  年齢: {episode['episode_age']}歳")
        print(f"  エピソード: {episode['episode_text'][:100]}...")
        print()

    print("=" * 80)
    print("次のステップ:")
    print("=" * 80)
    print("このスクリプトは情報表示用です。")
    print("実際のPhase 4評価は、Claude Codeが各エピソードについて")
    print("Brave Search MCPを使用して実行します。")
    print()
    print("Claude Codeに以下を依頼してください:")
    print("「これらの6エピソードについて、Brave Search MCPを使って")
    print(" 定番度判定を実行してください」")
    print("=" * 80)


if __name__ == '__main__':
    main()
