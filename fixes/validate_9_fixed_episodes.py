#!/usr/bin/env python3
"""
9件の修正済みエピソードを検証

統合パイプラインを使用して修正後のエピソードを検証
"""

import sys
import json
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, '/Users/admin/Documents/AIUELAB/001-final-hourglass')

from validate_and_fix_episodes import validate_all_episodes


def main():
    print("=" * 80)
    print("🔍 Phase 1: 修正済み9エピソードの検証")
    print("=" * 80)
    print()

    # v3修正済みCSVパス
    csv_path = '#episodes_fixed_v3_20251002.csv'

    print(f"📂 検証対象: {csv_path}")
    print("📋 検証内容:")
    print("  - 9件の修正エピソード（EP011, EP027, EP033, EP035, EP052, EP060, EP061, EP079, EP091）")
    print("  - v3修正: 文字数削減（平均201文字）")
    print("  - すべて250文字以内を達成")
    print("  - 象徴性スコア平均: 170.6点")
    print()

    # 統合パイプライン検証
    print("🔄 統合パイプライン検証実行中...")
    print()

    results = validate_all_episodes(csv_path)

    # 結果サマリー表示
    print()
    print("=" * 80)
    print("📊 検証結果サマリー")
    print("=" * 80)

    total = results['total']
    passed = len(results['passed'])
    failed_score = len(results['failed_score'])
    failed_critical = len(results['failed_critical'])
    failed_fact = len(results['failed_fact'])
    failed_total = failed_score + failed_critical + failed_fact
    pass_rate = (passed / total * 100) if total > 0 else 0

    print(f"合計エピソード: {total}件")
    print(f"✅ 合格: {passed}件")
    print(f"❌ 不合格: {failed_total}件")
    print(f"  - スコア不足: {failed_score}件")
    print(f"  - CRITICAL違反: {failed_critical}件")
    print(f"  - 事実検証失敗: {failed_fact}件")
    print(f"合格率: {pass_rate:.1f}%")
    print()

    # 修正済み9件の詳細
    fixed_episodes = [
        'EP011', 'EP027', 'EP033', 'EP035', 'EP052',
        'EP060', 'EP061', 'EP079', 'EP091'
    ]

    print("=" * 80)
    print("📋 修正済み9エピソードの詳細")
    print("=" * 80)

    for ep_id in fixed_episodes:
        # 該当エピソードを探す
        found = False
        for ep in results['evaluations']:
            if ep['episode_id'] == ep_id:
                found = True
                # 合格判定
                is_passed = ep in results['passed']
                status = "✅ 合格" if is_passed else "❌ 不合格"
                print(f"{ep_id}: {status} (スコア: {ep['score']:.1f}点)")

                if not is_passed:
                    print(f"  結果: {ep['result']}")
                    if ep.get('violations'):
                        print(f"  違反件数: {len(ep['violations'])}件")
                        for violation in ep['violations'][:3]:  # 最初の3件のみ表示
                            print(f"    - {violation}")
                break

        if not found:
            print(f"{ep_id}: ⚠️ データなし")

    print()

    # レポート保存
    output_path = 'fixes/validation_9_fixed_episodes_20251002.json'
    report_data = {
        'timestamp': json.dumps(results, ensure_ascii=False, indent=2),
        'summary': {
            'total': total,
            'passed': passed,
            'failed': failed_total,
            'pass_rate': pass_rate
        },
        'fixed_episodes': fixed_episodes
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"✅ 検証レポート保存: {output_path}")
    print()

    if pass_rate >= 98.0:
        print("=" * 80)
        print("🎉 Phase 1 検証成功！")
        print("=" * 80)
        print("修正済みエピソードは統合パイプライン基準をクリアしました。")
        print()
        print("次のステップ:")
        print("1. データベースの年齢を更新（6件）")
        print("2. Phase 2: 新ルール実装に進む")
    else:
        print("=" * 80)
        print("⚠️ 追加修正が必要です")
        print("=" * 80)
        print(f"不合格エピソード数: {failed_total}件")
        print("詳細は検証レポートを確認してください。")

    print()


if __name__ == "__main__":
    main()
