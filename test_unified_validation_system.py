#!/usr/bin/env python3
"""
統合検証システム実運用テスト
Test Unified Validation System in Production

5件のテストエピソードで自動検証・自動修正をテスト
"""

import json
from datetime import datetime
from typing import List, Dict, Any

from episode_generator_with_unified_validation import ValidatedEpisodeGenerator


# テストデータ: 意図的に違反を含む5件のエピソード
TEST_EPISODES = [
    {
        "person_id": "TEST001",
        "person_name": "テスト太郎",
        "user_age": 30,
        "episode_age": 30,
        "category": "スポーツ",
        "episode_text": "2013年にオリンピックで金メダルを獲得。日本人初の快挙として世界中から注目を集めた。北京オリンピックでの活躍は記録更新となり、陸上競技の歴史に新たな1ページを刻んだ。国際オリンピック委員会からも高い評価を受け、スポーツ界に大きな影響を与えた。",
        "expected_violation": "年号あり（2013年）",
        "auto_correctable": True
    },
    {
        "person_id": "TEST002",
        "person_name": "山田花子",
        "user_age": 25,
        "episode_age": 25,
        "category": "音楽",
        "episode_text": "史上最年少でグラミー賞を受賞。驚異的な才能で世界中の音楽ファンを魅了し、素晴らしいパフォーマンスで圧倒的な人気を獲得した。感動的なステージは多くの人々の心に残り、音楽業界に革新をもたらした。全世界でアルバム売上500万枚を記録し、ビルボードチャート1位を獲得した。",
        "expected_violation": "主観表現あり（驚異的、素晴らしい、圧倒的、感動的）",
        "auto_correctable": True
    },
    {
        "person_id": "TEST003",
        "person_name": "佐藤次郎",
        "user_age": 35,
        "episode_age": 35,
        "category": "科学",
        "episode_text": "ノーベル物理学賞を受賞。量子力学の研究で世界的な評価を受けた。",
        "expected_violation": "文字数不足（35文字、最低130文字必要）",
        "auto_correctable": False
    },
    {
        "person_id": "TEST004",
        "person_name": "田中三郎",
        "user_age": 28,
        "episode_age": 28,
        "category": "ビジネス",
        "episode_text": "自社を東京証券取引所に上場させ、史上最年少での株式公開を達成。ベンチャーキャピタルから総額100億円の資金調達に成功し、テクノロジー業界に革新をもたらした。28歳という若さで日本経済新聞の1面を飾り、起業家の新時代を切り開いた。従業員300人を抱える企業へと成長させた。",
        "expected_violation": "年齢重複（28歳が2回）",
        "auto_correctable": True
    },
    {
        "person_id": "TEST005",
        "person_name": "鈴木一郎",
        "user_age": 40,
        "episode_age": 40,
        "category": "スポーツ",
        "episode_text": "メジャーリーグで通算3000本安打を達成。日本人初の偉業として世界中から称賛され、野球殿堂入りを果たした。シアトル・マリナーズでの17年間の活躍は、アメリカ野球界に大きな足跡を残した。史上最年少記録を塗り替え、200本安打を10シーズン連続で記録する快挙を成し遂げた。",
        "expected_violation": "なし（完全準拠）",
        "auto_correctable": True  # 修正不要
    }
]


def print_section(title: str):
    """セクションタイトルを表示"""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def print_episode_summary(episode: Dict[str, Any], index: int):
    """エピソード概要を表示"""
    print(f"\n【エピソード {index + 1}】")
    print(f"人名: {episode['person_name']}")
    print(f"年齢: {episode['episode_age']}歳")
    print(f"カテゴリ: {episode['category']}")
    print(f"期待される違反: {episode['expected_violation']}")
    print(f"自動修正可能: {'はい' if episode['auto_correctable'] else 'いいえ'}")
    print(f"\n本文:\n{episode['episode_text']}")


def print_validation_result(episode: Dict[str, Any], result: Dict[str, Any], generated_episode: Any):
    """検証結果を表示"""
    print(f"\n--- 検証結果 ---")

    if generated_episode is None:
        print("❌ エピソード生成失敗（検証不合格、修正不可）")
        return

    validation = result
    print(f"有効: {'✅ 合格' if validation['is_valid'] else '❌ 不合格'}")
    print(f"違反数: {validation['violations']}")
    print(f"クリティカル違反: {validation['critical_violations']}")
    print(f"感銘スコア: {validation['emotional_score']:.2f}")
    print(f"具体性スコア: {validation['specificity_score']:.2f}")

    if 'corrections_applied' in generated_episode:
        print(f"\n自動修正適用: {', '.join(generated_episode['corrections_applied'])}")
        print(f"\n修正後の本文:\n{generated_episode['episode_text']}")


def run_test():
    """テスト実行"""
    print_section("統合検証システム 実運用テスト開始")

    print("テスト設定:")
    print(f"- テストエピソード数: {len(TEST_EPISODES)}件")
    print(f"- 設定ファイル: unified_validation_config.json")
    print(f"- 自動修正: 有効")
    print(f"- 検証失敗時: 拒否")

    # ジェネレータを初期化
    print_section("Step 1: ValidatedEpisodeGenerator の初期化")
    generator = ValidatedEpisodeGenerator("unified_validation_config.json")
    print("✅ ジェネレータ初期化完了")

    # 各エピソードをテスト
    print_section("Step 2: エピソード生成と検証")
    results = []

    for idx, test_episode in enumerate(TEST_EPISODES):
        print_episode_summary(test_episode, idx)

        # エピソード生成（自動検証付き）
        generated_episode = generator.generate_episode(test_episode)

        # 結果を記録
        if generated_episode:
            validation_result = generated_episode.get('validation_result', {})
            results.append({
                "test_case": idx + 1,
                "person_name": test_episode['person_name'],
                "expected_violation": test_episode['expected_violation'],
                "auto_correctable": test_episode['auto_correctable'],
                "generated": True,
                "is_valid": validation_result.get('is_valid', False),
                "violations": validation_result.get('violations', 0),
                "emotional_score": validation_result.get('emotional_score', 0.0),
                "specificity_score": validation_result.get('specificity_score', 0.0)
            })
            print_validation_result(test_episode, validation_result, generated_episode)
        else:
            results.append({
                "test_case": idx + 1,
                "person_name": test_episode['person_name'],
                "expected_violation": test_episode['expected_violation'],
                "auto_correctable": test_episode['auto_correctable'],
                "generated": False,
                "is_valid": False,
                "violations": -1,
                "emotional_score": 0.0,
                "specificity_score": 0.0
            })
            print(f"\n❌ エピソード生成失敗")

    # 統計情報
    print_section("Step 3: 統計情報の確認")
    stats = generator.validator.get_statistics()

    print(f"総検証数: {stats['total_validations']}")
    print(f"合格エピソード: {stats['valid_episodes']}")
    print(f"不合格エピソード: {stats['invalid_episodes']}")
    print(f"準拠率: {stats['compliance_rate']:.1f}%")
    print(f"平均感銘スコア: {stats['avg_emotional_score']:.2f}")
    print(f"平均具体性スコア: {stats['avg_specificity_score']:.2f}")
    print(f"クリティカル違反総数: {stats['critical_violations_total']}")

    # 検証履歴を保存
    print_section("Step 4: 検証履歴の保存")
    generator.validator.save_validation_history()
    print(f"✅ 検証履歴を {generator.validator.history_path} に保存しました")

    # テスト結果のサマリー
    print_section("テスト結果サマリー")

    print("\n【テストケース別結果】")
    print(f"{'#':<4} {'人名':<12} {'期待違反':<25} {'生成':<6} {'合格':<6} {'違反数':<8}")
    print("-" * 70)

    for r in results:
        print(f"{r['test_case']:<4} "
              f"{r['person_name']:<12} "
              f"{r['expected_violation']:<25} "
              f"{'○' if r['generated'] else '×':<6} "
              f"{'○' if r['is_valid'] else '×':<6} "
              f"{r['violations']:<8}")

    # 成功率計算
    generated_count = sum(1 for r in results if r['generated'])
    valid_count = sum(1 for r in results if r['is_valid'])

    print(f"\n【総合結果】")
    print(f"生成成功率: {generated_count}/{len(results)} ({generated_count/len(results)*100:.0f}%)")
    print(f"最終合格率: {valid_count}/{len(results)} ({valid_count/len(results)*100:.0f}%)")

    # 期待される結果との比較
    print(f"\n【期待値との比較】")
    expected_valid = 4  # TEST001, TEST002, TEST004, TEST005 は自動修正可能
    expected_failed = 1  # TEST003 は文字数不足で修正不可

    print(f"期待合格数: {expected_valid}件")
    print(f"実際の合格数: {valid_count}件")
    print(f"期待失敗数: {expected_failed}件")
    print(f"実際の失敗数: {len(results) - valid_count}件")

    if valid_count == expected_valid:
        print("\n✅ テスト成功: 期待通りの結果が得られました")
    else:
        print(f"\n⚠️ テスト結果が期待と異なります（期待: {expected_valid}件、実際: {valid_count}件）")

    # 結果をJSONファイルに保存
    test_result_file = f"test_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(test_result_file, 'w', encoding='utf-8') as f:
        json.dump({
            "test_date": datetime.now().isoformat(),
            "test_episodes": len(TEST_EPISODES),
            "results": results,
            "statistics": stats,
            "expected_valid": expected_valid,
            "actual_valid": valid_count
        }, f, ensure_ascii=False, indent=2)

    print(f"\n✅ テスト結果を {test_result_file} に保存しました")

    print_section("テスト完了")

    return results, stats


if __name__ == "__main__":
    results, stats = run_test()
