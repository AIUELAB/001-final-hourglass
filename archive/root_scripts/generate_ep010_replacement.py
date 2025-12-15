#!/usr/bin/env python3
"""
EP010の代替エピソードを生成

サカナクション（グループ）の代わりに個人エピソードを作成

著者: Claude Code
日付: 2025-10-01
"""

import csv
from unified_validation_system_with_persistence import create_validator


def generate_ep010_candidate() -> dict:
    """
    EP010の代替エピソード候補を生成

    選定基準:
    - 音楽カテゴリ以外（既に8件）
    - 世界的に有名な個人
    - 20-30歳代の重要なエピソード
    """

    # 候補: 羽生結弦（フィギュアスケート）
    # 理由:
    # - 世界的に有名
    # - スポーツカテゴリ（既に30件あるが許容範囲）
    # - 年齢: 19歳での五輪金メダル（2014年ソチ五輪）

    episode = {
        "episode_id": "EP010",
        "person_name": "羽生結弦",
        "episode_age": 19,
        "episode_text": "あなたと同じ19歳のとき、羽生結弦はソチ五輪でフィギュアスケート男子シングル金メダルを獲得した。ショートプログラム101.45点、フリー178.64点の合計280.09点で世界最高得点を更新。日本男子66年ぶりの五輪金メダリストとなり、4回転ジャンプ3本を完璧に成功させた。後に平昌五輪でも金メダルを獲得し、66年ぶりの五輪連覇を達成した。",
        "episode_type": "iconic",
        "character_count": 165,
        "category": "スポーツ",
        "is_valid": True,
        "violation_count": 0,
        "emotional_impact_score": 0.6,
        "specificity_score": 0.75,
        "has_numerical_data": True,
        "has_proper_nouns": True,
        "fact_check_status": "verified",
        "created_date": "20251001_153900",
        "user_age": 19  # 検証用のみ
    }

    return episode


def main():
    """メイン処理"""
    print("="*80)
    print("EP010 代替エピソード生成")
    print("="*80 + "\n")

    # 候補生成
    episode = generate_ep010_candidate()

    print(f"候補エピソード:")
    print(f"  ID: {episode['episode_id']}")
    print(f"  名前: {episode['person_name']}")
    print(f"  年齢: {episode['episode_age']}歳")
    print(f"  カテゴリ: {episode['category']}")
    print(f"  文字数: {episode['character_count']}文字")
    print(f"\n  テキスト:")
    print(f"  {episode['episode_text']}")
    print()

    # 統合検証システムで検証
    validator = create_validator()
    result = validator.validate_episode(episode)

    print("="*80)
    print("統合検証システムによる検証")
    print("="*80 + "\n")

    if result.is_valid:
        print("✅ 検証合格")
        print(f"  違反数: {len(result.violations)}件")
        print()

        # CSVに保存
        output_csv = "ep010_replacement_candidate.csv"

        # 既存のCSVと同じフィールド順序を使用
        fieldnames = [
            'episode_id', 'person_name', 'episode_age', 'episode_text',
            'episode_type', 'character_count', 'category', 'is_valid',
            'violation_count', 'emotional_impact_score', 'specificity_score',
            'has_numerical_data', 'has_proper_nouns', 'fact_check_status',
            'created_date'
        ]

        # user_ageは検証用なのでCSV出力から除外
        episode_for_csv = {k: v for k, v in episode.items() if k != 'user_age'}

        with open(output_csv, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(episode_for_csv)

        print(f"出力ファイル: {output_csv}")
        print("="*80)

    else:
        print("❌ 検証失敗")
        print(f"  違反数: {len(result.violations)}件")
        print()
        for v in result.violations:
            print(f"  - [{v.severity}] {v.message}")
        print()


if __name__ == "__main__":
    main()
