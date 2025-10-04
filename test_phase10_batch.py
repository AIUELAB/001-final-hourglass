#!/usr/bin/env python3
"""
Phase 10.4: テスト実行（5エピソード）

ギャップ最小の5エピソードで微調整改善をテストする。
"""

import csv
from batch_micro_adjustment_improver import MicroAdjustmentBatchImprover


def create_test_targets():
    """テスト用ターゲット作成（TOP5）"""
    test_targets = []

    # Phase 10ターゲットからTOP5を読み込み
    with open("episodes_phase10_targets.csv", 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i < 5:  # TOP5のみ
                test_targets.append(row)
            else:
                break

    # テスト用CSV保存
    with open("episodes_phase10_test_targets.csv", 'w', encoding='utf-8-sig', newline='') as f:
        if test_targets:
            fieldnames = list(test_targets[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(test_targets)

    return test_targets


def main():
    """メイン実行"""
    print("=" * 80)
    print("Phase 10.4: テスト実行（5エピソード）")
    print("=" * 80)

    # テストターゲット作成
    print("\n📋 テストターゲット作成中...")
    test_targets = create_test_targets()
    print(f"✅ {len(test_targets)}件のテストターゲット作成完了")

    print(f"\nテスト対象:")
    for i, t in enumerate(test_targets, 1):
        print(f"  {i}. {t['episode_id']}: {t['person_name']} "
              f"(社会的影響: {t['social_impact_score']}点, ギャップ: {t['gap_to_pass']}点)")

    # バッチ改善システム初期化（改訂版: RULE_184使用）
    improver = MicroAdjustmentBatchImprover(
        provider="openai",
        checkpoint_interval=5,  # テストなので5件ごと
        acceptance_threshold=5.0  # Phase 9と同じ
    )

    # テスト実行
    print("\n🚀 テスト実行を開始...")
    results = improver.process_batch(
        targets=test_targets,
        episodes_csv_path="episodes_phase9_complete.csv",
        output_csv_path="episodes_phase10_test.csv"
    )

    # テスト結果サマリー
    print("\n" + "=" * 80)
    print("📊 テスト結果サマリー")
    print("=" * 80)

    print(f"\n処理統計:")
    print(f"  総処理数: {improver.stats['total_processed']}件")
    print(f"  改善採用: {improver.stats['improved']}件 "
          f"({improver.stats['improved']/improver.stats['total_processed']*100:.1f}%)")
    print(f"  改善失敗: {improver.stats['failed']}件")
    print(f"  スキップ: {improver.stats['skipped']}件")

    print(f"\n改善効果:")
    print(f"  社会的影響向上: {improver.stats['social_impact_increased']}件")
    print(f"  総合スコア向上: {improver.stats['total_score_increased']}件")

    # 個別結果表示
    print(f"\n" + "=" * 80)
    print(f"📋 個別結果詳細")
    print(f"=" * 80)

    for result in results:
        print(f"\n{result['episode_id']}: {result['person_name']}")
        print(f"  改善前: 総合 {result['before_total_score']:.1f}点, "
              f"社会的影響 {result['before_social_impact']:.1f}点")
        print(f"  改善後: 総合 {result['after_total_score']:.1f}点, "
              f"社会的影響 {result['after_social_impact']:.1f}点")
        print(f"  変化: 社会的影響 {result['social_impact_gain']:+.1f}点")
        print(f"  採用: {'✅ 採用' if result['adopted'] else '🔄 ロールバック'}")

    # 判定
    print(f"\n" + "=" * 80)
    print(f"🎯 テスト判定")
    print(f"=" * 80)

    success_rate = (improver.stats['improved'] / improver.stats['total_processed'] * 100)

    if success_rate >= 60.0:
        print(f"✅ テスト成功！（成功率 {success_rate:.1f}% >= 60%）")
        print(f"本番実行（53エピソード）に進んでください。")
        test_passed = True
    else:
        print(f"⚠️ テスト要検討（成功率 {success_rate:.1f}% < 60%）")
        print(f"受入閾値の調整を検討してください。")
        test_passed = False

    print(f"\n" + "=" * 80)
    print(f"✅ Phase 10.4完了")
    print(f"=" * 80)

    return test_passed


if __name__ == "__main__":
    main()
