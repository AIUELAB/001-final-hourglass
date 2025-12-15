#!/usr/bin/env python3
"""
EpisodeGuardian統合検証スクリプト

単一または複数のエピソードをEpisodeGuardianで検証

著者: Claude Code
日付: 2025-10-01
バージョン: 1.0.0

使用例:
    # 単一エピソード検証
    python validate_episode_with_guardian.py --name "羽生結弦" --age 19 --text "..."

    # CSVファイル検証
    python validate_episode_with_guardian.py --csv episodes.csv

    # JSONファイル検証
    python validate_episode_with_guardian.py --json episode.json
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List

from episode_guardian import create_episode_guardian, Severity


def validate_single_episode(guardian, episode: Dict) -> bool:
    """単一エピソードを検証"""
    result = guardian.validate_episode(episode)

    if result.is_valid:
        print(f"✅ 合格: {episode['person_name']}")
        return True
    else:
        severity_icon = "🚨" if result.severity == Severity.CRITICAL else "⚠️"
        print(f"{severity_icon} 失格: {episode['person_name']}")
        print(f"   理由: {result.message}")
        print(f"   違反ルール: {', '.join(result.failed_rules)}")

        if result.suggestions:
            print(f"   改善提案:")
            for suggestion in result.suggestions:
                print(f"     - {suggestion}")

        return False


def validate_from_csv(guardian, csv_path: str) -> Dict:
    """CSVファイルから検証"""
    print(f"📄 CSVファイル読み込み: {csv_path}")

    episodes = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            episode = {
                'episode_id': row.get('episode_id', 'N/A'),
                'person_name': row['person_name'],
                'episode_age': int(row['episode_age']),
                'episode_text': row['episode_text'],
                'category': row.get('category', 'その他'),
                'user_age': int(row['episode_age'])
            }
            episodes.append(episode)

    print(f"   総エピソード数: {len(episodes)}件\n")

    results = {'total': len(episodes), 'passed': 0, 'failed': 0}

    for episode in episodes:
        if validate_single_episode(guardian, episode):
            results['passed'] += 1
        else:
            results['failed'] += 1
        print()

    return results


def validate_from_json(guardian, json_path: str) -> Dict:
    """JSONファイルから検証"""
    print(f"📄 JSONファイル読み込み: {json_path}")

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 単一エピソードまたは配列
    if isinstance(data, list):
        episodes = data
    else:
        episodes = [data]

    print(f"   総エピソード数: {len(episodes)}件\n")

    results = {'total': len(episodes), 'passed': 0, 'failed': 0}

    for episode in episodes:
        # user_ageがない場合はepisode_ageを使用
        if 'user_age' not in episode:
            episode['user_age'] = episode['episode_age']

        if validate_single_episode(guardian, episode):
            results['passed'] += 1
        else:
            results['failed'] += 1
        print()

    return results


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description='EpisodeGuardian統合検証スクリプト',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 単一エピソード検証
  python validate_episode_with_guardian.py \\
    --name "羽生結弦" \\
    --age 19 \\
    --text "あなたと同じ19歳のとき、羽生結弦はソチ五輪で金メダルを獲得した。..." \\
    --category "スポーツ"

  # CSVファイル検証
  python validate_episode_with_guardian.py --csv episodes_complete_100_20251001.csv

  # JSONファイル検証
  python validate_episode_with_guardian.py --json episode.json
        """
    )

    # 単一エピソード引数
    parser.add_argument('--name', help='人物名')
    parser.add_argument('--age', type=int, help='年齢')
    parser.add_argument('--text', help='エピソードテキスト')
    parser.add_argument('--category', default='その他', help='カテゴリ')

    # ファイル引数
    parser.add_argument('--csv', help='CSVファイルパス')
    parser.add_argument('--json', help='JSONファイルパス')

    # 設定
    parser.add_argument('--config', help='EpisodeGuardian設定ファイルパス')
    parser.add_argument('--verbose', action='store_true', help='詳細出力')

    args = parser.parse_args()

    # EpisodeGuardian初期化
    print("=" * 80)
    print("EpisodeGuardian統合検証")
    print("=" * 80)
    print()

    guardian = create_episode_guardian(args.config)
    print(f"🛡️ EpisodeGuardian v{guardian.VERSION}")
    print(f"   既知のグループ: {len(guardian.known_groups)}件")
    print()

    # 検証実行
    if args.csv:
        # CSVファイル検証
        results = validate_from_csv(guardian, args.csv)

    elif args.json:
        # JSONファイル検証
        results = validate_from_json(guardian, args.json)

    elif args.name and args.text:
        # 単一エピソード検証
        episode = {
            'person_name': args.name,
            'episode_age': args.age,
            'episode_text': args.text,
            'category': args.category,
            'user_age': args.age
        }

        print("🔍 単一エピソード検証\n")
        success = validate_single_episode(guardian, episode)

        results = {
            'total': 1,
            'passed': 1 if success else 0,
            'failed': 0 if success else 1
        }

    else:
        print("❌ エラー: --csv, --json, または (--name, --text) を指定してください")
        parser.print_help()
        sys.exit(1)

    # サマリー
    print("=" * 80)
    print("検証結果サマリー")
    print("=" * 80)
    print(f"総エピソード数: {results['total']}件")
    print(f"合格: {results['passed']}件 ({results['passed']/results['total']*100:.1f}%)")
    print(f"失格: {results['failed']}件 ({results['failed']/results['total']*100:.1f}%)")

    # メトリクス
    if args.verbose:
        print()
        print("=" * 80)
        print("EpisodeGuardianメトリクス")
        print("=" * 80)

        metrics = guardian.get_metrics()
        print(f"総検証数: {metrics['total_validations']}")
        print(f"失敗数: {metrics['failed_validations']}")
        print(f"Entity Type失敗: {metrics['entity_type_failures']}")
        print(f"グループ検出数: {len(metrics['group_detections'])}")

        if metrics['group_detections']:
            print("\n検出されたグループ:")
            for detection in metrics['group_detections']:
                print(f"  - {detection['name']}")

    # 終了コード
    sys.exit(0 if results['failed'] == 0 else 1)


if __name__ == '__main__':
    main()
