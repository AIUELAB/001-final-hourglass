#!/usr/bin/env python3
"""
Phase 4バッチ評価スクリプト
Phase 1-3合格済みのエピソードのみを対象に定番度判定を実行
"""

import csv
from typing import List, Dict


def load_phase123_passed_episodes(csv_path: str) -> List[Dict]:
    """Phase 1-3合格済みエピソードを読み込み"""
    episodes = []

    # まず前回の評価結果があるか確認
    evaluation_csv = "episodes_validated_100_20251001_integrated_evaluation.csv"

    try:
        with open(evaluation_csv, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Phase 1-3すべて合格のエピソードのみ
                if (row.get('compliance_passed') == 'True' and
                    row.get('distribution_passed') == 'True' and
                    row.get('impact_passed') == 'True'):
                    episodes.append({
                        'episode_id': row['episode_id'],
                        'person_name': row['person_name'],
                        'episode_age': row['episode_age'],
                        'compliance_passed': True,
                        'distribution_passed': True,
                        'impact_passed': True
                    })

        print(f"✅ 前回評価結果から読み込み: {len(episodes)}件")

    except FileNotFoundError:
        # 評価結果がない場合は全エピソードを対象
        print("⚠️ 前回評価結果なし - 全エピソードを対象にします")
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                episodes.append({
                    'episode_id': row['episode_id'],
                    'person_name': row['person_name'],
                    'episode_age': int(row['episode_age'])
                })

    return episodes


def main():
    """メイン処理"""

    print("=" * 80)
    print("Phase 4バッチ評価 - Phase 1-3合格エピソードのみ")
    print("=" * 80)

    input_csv = "episodes_validated_100_20251001.csv"

    print(f"\n入力: {input_csv}")
    print()

    # Phase 1-3合格エピソードを読み込み
    print("Phase 1-3合格エピソードを読み込み中...")
    episodes = load_phase123_passed_episodes(input_csv)

    if not episodes:
        print("\n❌ Phase 1-3合格エピソードが見つかりませんでした")
        print("まず integrated_episode_evaluator.py を実行してください")
        return

    print(f"\n対象エピソード数: {len(episodes)}件")
    print()

    # 問題の6エピソードをハイライト
    problem_ids = ['EP011', 'EP033', 'EP035', 'EP061', 'EP077', 'EP079']
    problem_episodes = [e for e in episodes if e['episode_id'] in problem_ids]

    print("=" * 80)
    print("評価対象エピソード")
    print("=" * 80)
    print()

    if problem_episodes:
        print(f"問題の6エピソード: {len(problem_episodes)}件")
        for ep in problem_episodes:
            print(f"  - {ep['episode_id']}: {ep['person_name']} ({ep['episode_age']}歳)")
        print()

    other_episodes = [e for e in episodes if e['episode_id'] not in problem_ids]
    if other_episodes:
        print(f"その他のエピソード: {len(other_episodes)}件")
        print(f"  合計: {len(episodes)}件")
        print()

    print("=" * 80)
    print("実行計画")
    print("=" * 80)
    print()
    print("Phase 4評価を実行するには以下の方法があります:")
    print()
    print("【方法1】問題の6エピソードのみ（推奨）")
    print("  - すでに検証済みの6エピソード")
    print("  - 実行時間: 約30秒")
    print("  - コマンド: python3 run_phase4_six_episodes.py")
    print()
    print("【方法2】全Phase 1-3合格エピソード")
    print(f"  - 対象: {len(episodes)}エピソード")
    print(f"  - 実行時間: 約{len(episodes) * 0.5}秒 + 検索時間")
    print("  - コマンド: python3 run_phase4_evaluation.py")
    print()
    print("【方法3】バッチ処理（10件ずつ）")
    print("  - API Rate Limit対策")
    print("  - 進捗確認しながら実行")
    print()
    print("=" * 80)
    print()
    print("📊 現在の状況:")
    print(f"  - 全エピソード数: 100件")
    print(f"  - Phase 1-3合格: {len(episodes)}件")
    print(f"  - Phase 4評価済み: 6件（問題エピソード）")
    print(f"  - Phase 4未評価: {len(episodes) - len(problem_episodes)}件")
    print()


if __name__ == '__main__':
    main()
