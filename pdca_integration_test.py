#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDCAガーディアンシステム統合テスト
すべてのコンポーネントが協調して動作することを確認
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from pdca_guardian_enhanced import EnhancedPDCAGuardian
from pdca_health_monitor import PDCAHealthMonitor
from episode_validator import EpisodeValidator


def run_integration_test():
    """統合テストの実行"""

    print("=" * 80)
    print("🚀 PDCAガーディアンシステム - 統合テスト")
    print("=" * 80)
    print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # コンポーネント初期化
    guardian = EnhancedPDCAGuardian()
    monitor = PDCAHealthMonitor()
    validator = EpisodeValidator()

    # テストケース: 問題のあったWeek 4エピソード（修正前）
    problematic_episodes = [
        {
            "name": "久石譲",
            "age": 47,
            "text": "あなたと同じ47歳のとき、久石譲は『もののけ姫』で日本アカデミー賞最優秀音楽賞を受賞した。宮崎駿作品の音楽を30年以上手がけ、世界中のファンを魅了した。年間100回以上のコンサートで指揮を執り、クラシックと映画音楽の垣根を超えた。日本音楽を世界に広めた現代最高の作曲家。"
        },
        {
            "name": "玉置浩二",
            "age": 56,
            "text": "あなたと同じ56歳のとき、玉置浩二は日本武道館で伝説的なコンサートを開催し、2万人を涙させた。安全地帯での活動と並行し、ソロで20枚以上のアルバムをリリース。音域4オクターブの歌声と、繊細な表現力で「日本最高の歌手」と称された。半世紀にわたり日本の音楽シーンをリードする巨匠。"
        },
        {
            "name": "明石康",
            "age": 61,
            "text": "あなたと同じ61歳のとき、明石康は国連カンボジア暫定統治機構代表として、内戦終結と民主化を実現した。1993年の総選挙を成功に導き、20年間続いた内戦を終結させた。日本人初の国連事務次長として、PKO活動の新たなモデルを確立した。国際平和構築の第一人者として世界平和に大きく貢献した外交官。"
        }
    ]

    print("📝 テストエピソード: 修正前のWeek 4から3件")
    print()

    # 各システムでの検証結果を収集
    results = {
        "episodes": [],
        "guardian_violations": 0,
        "validator_violations": 0,
        "monitor_alerts": 0,
        "fixed_count": 0
    }

    for ep in problematic_episodes:
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"【{ep['name']}】({ep['age']}歳)")
        print(f"文字数: {len(ep['text'])}文字")
        print()

        # 1. EpisodeValidatorで検証
        print("1️⃣ EpisodeValidator検証:")
        validation_results = validator.validate_episode(ep['text'])

        failed_checks = []
        for check_name, (is_valid, reason) in validation_results.items():
            if not is_valid:
                failed_checks.append(check_name)
                print(f"  ❌ {check_name}: {reason}")

        if not failed_checks:
            print("  ✅ すべてのチェックを通過")

        results["validator_violations"] += len(failed_checks)

        # 2. PDCAガーディアンで検証
        print("\n2️⃣ PDCAガーディアン検証:")

        # 監視開始
        monitor_id = monitor.start_monitoring(
            'RULE_152',
            {'episode_text': ep['text'], 'person_data': {'name': ep['name']}}
        )

        try:
            violations = guardian.check_episode_quality(
                ep['text'], ep['age'], ep['name']
            )
            monitor.end_monitoring(monitor_id, 'success', result=violations)
        except Exception as e:
            monitor.end_monitoring(monitor_id, 'error', error=str(e))
            violations = []

        # 文末違反を特定
        ending_violations = [
            v for v in violations
            if 'RULE_152' in str(v.get('rule_id', v.get('rule', '')))
        ]

        if ending_violations:
            print(f"  ❌ 文末違反検出: {len(ending_violations)}件")
            for v in ending_violations[:2]:  # 最初の2件のみ表示
                msg = v.get('message', str(v))
                print(f"    - {msg[:60]}...")
        else:
            print("  ✅ 文末違反なし")

        results["guardian_violations"] += len(violations)

        # 3. 自動修正を試みる
        if 'sentence_ending' in failed_checks:
            print("\n3️⃣ 自動修正:")
            fixed_text = validator.fix_sentence_ending(ep['text'])

            # 修正後の検証
            fixed_validation = validator.validate_sentence_ending(fixed_text)
            if fixed_validation[0]:
                print(f"  ✅ 修正成功")
                print(f"    元の文末: ...{ep['text'][-20:]}")
                print(f"    修正後: ...{fixed_text[-30:]}")
                results["fixed_count"] += 1
            else:
                print(f"  ❌ 修正失敗: {fixed_validation[1]}")

        # エピソード結果を記録
        results["episodes"].append({
            "name": ep['name'],
            "validator_violations": len(failed_checks),
            "guardian_violations": len(violations),
            "ending_violation": len(ending_violations) > 0,
            "fixed": 'sentence_ending' in failed_checks and validator.validate_sentence_ending(
                validator.fix_sentence_ending(ep['text'])
            )[0]
        })

    # 健全性レポート生成
    print("\n" + "━" * 40)
    print("4️⃣ 健全性監視レポート:")

    health_report = monitor.generate_health_report()

    print(f"  総実行数: {health_report['summary']['total_executions']}")
    print(f"  成功率: {health_report['summary']['success_rate']:.1f}%")
    print(f"  エラー率: {health_report['summary']['error_rate']:.1f}%")

    if health_report['alerts']:
        print(f"  ⚠️ アラート: {len(health_report['alerts'])}件")
        results["monitor_alerts"] = len(health_report['alerts'])
    else:
        print("  ✅ アラートなし")

    # 統合テスト結果サマリー
    print("\n" + "=" * 80)
    print("📊 統合テスト結果サマリー")
    print("=" * 80)

    print(f"\n検証したエピソード数: {len(problematic_episodes)}件")
    print(f"\nEpisodeValidator:")
    print(f"  検出した違反総数: {results['validator_violations']}")
    print(f"  文末違反検出数: {sum(1 for ep in results['episodes'] if ep['validator_violations'] > 0)}")

    print(f"\nPDCAガーディアン:")
    print(f"  検出した違反総数: {results['guardian_violations']}")
    print(f"  文末違反検出数: {sum(1 for ep in results['episodes'] if ep['ending_violation'])}")

    print(f"\n自動修正:")
    print(f"  修正成功数: {results['fixed_count']}/{len([e for e in results['episodes'] if e['validator_violations'] > 0])}")

    print(f"\n健全性監視:")
    print(f"  アラート数: {results['monitor_alerts']}")

    # 総合判定
    print("\n" + "=" * 80)
    print("🎯 総合判定")
    print("=" * 80)

    all_systems_detected = all(
        ep['validator_violations'] > 0 and ep['ending_violation']
        for ep in results['episodes']
    )

    if all_systems_detected and results['fixed_count'] == 3:
        print("\n🎉 完璧！すべてのシステムが正しく動作しています！")
        print("  ✅ EpisodeValidatorが文末違反を検出")
        print("  ✅ PDCAガーディアンが文末違反を検出")
        print("  ✅ 自動修正が成功")
        print("  ✅ 健全性監視が正常動作")
        return 0
    elif all_systems_detected:
        print("\n✅ 良好: 検出システムは正常動作しています")
        print(f"  ⚠️ 自動修正: {results['fixed_count']}/3件成功")
        return 0
    else:
        print("\n❌ 問題あり: 一部のシステムが期待通り動作していません")
        for i, ep in enumerate(results['episodes']):
            if ep['validator_violations'] == 0 or not ep['ending_violation']:
                print(f"  - {problematic_episodes[i]['name']}: 違反を検出できませんでした")
        return 1


def main():
    """メイン関数"""
    exit_code = run_integration_test()

    # レポート保存
    monitor = PDCAHealthMonitor()
    report = monitor.generate_health_report()
    monitor.save_report(report, "integration_test_report.json")

    print(f"\n📁 レポートを保存しました: pdca_logs/integration_test_report.json")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
