#!/usr/bin/env python3
"""
EpisodeGuardianによる最終検証

100件の完成データベースをEpisodeGuardianで再検証

著者: Claude Code
日付: 2025-10-01
バージョン: 1.0.0
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from episode_guardian import create_episode_guardian, Severity


def load_episodes_from_csv(csv_path: str) -> List[Dict]:
    """CSVファイルからエピソードを読み込み"""
    episodes = []

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row in reader:
            episode = {
                'episode_id': row['episode_id'],
                'person_name': row['person_name'],
                'episode_age': int(row['episode_age']),
                'episode_text': row['episode_text'],
                'category': row['category'],
                'episode_type': row.get('episode_type', 'iconic'),
                'user_age': int(row['episode_age'])  # 検証用
            }
            episodes.append(episode)

    return episodes


def verify_all_episodes(csv_path: str) -> Dict:
    """すべてのエピソードを検証"""
    print("=" * 80)
    print("EpisodeGuardianによる最終検証")
    print("=" * 80)
    print()

    # CSVファイルを読み込み
    print(f"📄 CSVファイル読み込み: {csv_path}")
    episodes = load_episodes_from_csv(csv_path)
    print(f"   総エピソード数: {len(episodes)}件\n")

    # EpisodeGuardianを初期化
    print("🛡️ EpisodeGuardian初期化...")
    guardian = create_episode_guardian()
    print(f"   バージョン: {guardian.VERSION}")
    print(f"   既知のグループ: {len(guardian.known_groups)}件\n")

    # 検証実行
    print("🔍 検証開始...\n")

    results = {
        'total': len(episodes),
        'passed': 0,
        'failed': 0,
        'failures': []
    }

    for episode in episodes:
        result = guardian.validate_episode(episode)

        if result.is_valid:
            results['passed'] += 1
            print(f"✅ {episode['episode_id']}: {episode['person_name']} - 合格")
        else:
            results['failed'] += 1
            results['failures'].append({
                'episode_id': episode['episode_id'],
                'person_name': episode['person_name'],
                'severity': result.severity.value,
                'message': result.message,
                'failed_rules': result.failed_rules
            })

            severity_icon = "🚨" if result.severity == Severity.CRITICAL else "⚠️"
            print(f"{severity_icon} {episode['episode_id']}: {episode['person_name']} - 失格")
            print(f"   理由: {result.message}")
            print(f"   違反ルール: {', '.join(result.failed_rules)}")

    print()
    print("=" * 80)
    print("検証結果サマリー")
    print("=" * 80)
    print(f"総エピソード数: {results['total']}件")
    print(f"合格: {results['passed']}件 ({results['passed']/results['total']*100:.1f}%)")
    print(f"失格: {results['failed']}件 ({results['failed']/results['total']*100:.1f}%)")
    print()

    # メトリクス
    metrics = guardian.get_metrics()
    print("=" * 80)
    print("EpisodeGuardianメトリクス")
    print("=" * 80)
    print(f"総検証数: {metrics['total_validations']}")
    print(f"失敗数: {metrics['failed_validations']}")
    print(f"Entity Type失敗: {metrics['entity_type_failures']}")
    print(f"グループ検出数: {len(metrics['group_detections'])}")

    if metrics['group_detections']:
        print("\n検出されたグループ:")
        for detection in metrics['group_detections']:
            print(f"  - {detection['name']} ({detection['timestamp']})")

    print()

    # 失格の詳細
    if results['failures']:
        print("=" * 80)
        print("失格エピソード詳細")
        print("=" * 80)

        for failure in results['failures']:
            print(f"\n{failure['episode_id']}: {failure['person_name']}")
            print(f"  重要度: {failure['severity']}")
            print(f"  メッセージ: {failure['message']}")
            print(f"  違反ルール: {', '.join(failure['failed_rules'])}")

    return results


def save_verification_report(results: Dict, output_path: str):
    """検証レポートをJSON形式で保存"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'guardian_version': '1.0.0',
        'results': results
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"📄 検証レポート保存: {output_path}")


def main():
    """メイン処理"""
    # 最終データベースのパス
    csv_path = "episodes_complete_100_20251001.csv"

    if not Path(csv_path).exists():
        print(f"❌ エラー: {csv_path} が見つかりません")
        return

    # 検証実行
    results = verify_all_episodes(csv_path)

    # レポート保存
    report_path = "episode_guardian_verification_report_20251001.json"
    save_verification_report(results, report_path)

    # 最終判定
    print()
    print("=" * 80)
    print("最終判定")
    print("=" * 80)

    if results['failed'] == 0:
        print("🎉 すべてのエピソードが合格しました！")
        print("✅ データベースは本番環境にデプロイ可能です。")
    else:
        print("⚠️ 一部のエピソードが失格しました。")
        print(f"   失格数: {results['failed']}件")
        print("❌ 修正が必要です。")

    print()


if __name__ == '__main__':
    main()
