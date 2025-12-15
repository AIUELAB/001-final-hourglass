#!/usr/bin/env python3
"""
FactChecker統合テスト
PDCAガーディアンとFactCheckerの連携を検証
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pdca_guardian import PDCAGuardian
from src.fact_checker import FactChecker


def test_fact_checker_integration():
    """FactCheckerとPDCAガーディアンの統合テスト"""
    print("=" * 60)
    print("FactChecker統合テスト開始")
    print("=" * 60)

    # PDCAガーディアンの初期化
    guardian = PDCAGuardian()

    # テストケース1: 正常なエピソード
    print("\n[テストケース1] 正常なエピソード")
    print("-" * 40)

    episode1 = """
    2004年、31歳のイチローはMLBでシーズン262安打の新記録を樹立。
    この記録は84年ぶりの更新となり、世界中の野球ファンを驚かせた。
    """

    person_data1 = {
        "person_id": "P001",
        "person_name_ja": "イチロー",
        "birth_year_int": 1973,
        "wikipedia_verified": True,
    }

    violations1 = guardian.check_factual_accuracy(episode1, person_data1)

    if violations1:
        print("検出された違反:")
        for v in violations1:
            print(f"  - [{v['severity']}] {v['message']}")
    else:
        print("✅ 違反なし - エピソードは事実的に正確です")

    # テストケース2: ハルシネーションを含むエピソード
    print("\n[テストケース2] ハルシネーションを含むエピソード")
    print("-" * 40)

    episode2 = """
    世界で初めてYouTubeで10億人の登録者を獲得したHIKAKINは、
    2025年にノーベル平和賞を受賞。史上初の快挙を達成した。
    """

    person_data2 = {
        "person_id": "P002",
        "person_name_ja": "HIKAKIN",
        "birth_year_int": 1989,
        "wikipedia_verified": False,
    }

    violations2 = guardian.check_factual_accuracy(episode2, person_data2)

    if violations2:
        print("検出された違反:")
        for v in violations2:
            print(f"  - [{v['severity']}] {v['message']}")
            if "suggestion" in v:
                print(f"    → 提案: {v['suggestion']}")
    else:
        print("❌ 違反が検出されませんでした（予期しない結果）")

    # テストケース3: 時代錯誤を含むエピソード
    print("\n[テストケース3] 時代錯誤を含むエピソード")
    print("-" * 40)

    episode3 = """
    江戸時代、インターネットで情報発信を始めた侍は、
    SNSで100万人のフォロワーを獲得した。
    """

    person_data3 = {
        "person_id": "P003",
        "person_name_ja": "架空の侍",
        "birth_year_int": 1800,
        "wikipedia_verified": False,
    }

    violations3 = guardian.check_factual_accuracy(episode3, person_data3)

    if violations3:
        print("検出された違反:")
        for v in violations3:
            print(f"  - [{v['severity']}] {v['message']}")
            if "confidence" in v:
                print(f"    確信度: {v['confidence']}")
    else:
        print("❌ 違反が検出されませんでした（予期しない結果）")

    # テストケース4: 年代不整合を含むエピソード
    print("\n[テストケース4] 年代不整合を含むエピソード")
    print("-" * 40)

    episode4 = """
    1954年生まれの安倍晋三は、2006年に50歳で第90代内閣総理大臣に就任。
    その後、2012年に60歳で再び総理大臣となった。
    """

    person_data4 = {
        "person_id": "P004",
        "person_name_ja": "安倍晋三",
        "birth_year_int": 1954,
        "wikipedia_verified": True,
    }

    violations4 = guardian.check_factual_accuracy(episode4, person_data4)

    if violations4:
        print("検出された違反:")
        for v in violations4:
            print(f"  - [{v['severity']}] {v['message']}")
    else:
        print("✅ 違反なし")

    # 結果サマリー
    print("\n" + "=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)

    total_cases = 4
    cases_with_violations = sum(
        [len(violations1) > 0, len(violations2) > 0, len(violations3) > 0, len(violations4) > 0]
    )

    print(f"実行されたテストケース: {total_cases}")
    print(f"違反が検出されたケース: {cases_with_violations}")
    print(f"成功率: {(cases_with_violations/total_cases)*100:.1f}%")

    # FactCheckerが利用可能か確認
    if FactChecker is not None:
        print("\n✅ FactCheckerモジュールが正常にロードされています")
    else:
        print("\n⚠️ FactCheckerモジュールがロードされていません")

    print("\n統合テスト完了")


def test_fact_checker_direct():
    """FactCheckerの直接テスト"""
    print("\n" + "=" * 60)
    print("FactChecker直接テスト")
    print("=" * 60)

    if FactChecker is None:
        print("❌ FactCheckerが利用できません")
        return

    checker = FactChecker()

    # テストエピソード
    episode = """
    30歳の時、世界で初めて1000億円の売上を達成。
    150%の成長率を記録し、ノーベル経済学賞を受賞した。
    """

    report = checker.check_episode(person_id="TEST001", person_name="テスト人物", episode_text=episode, birth_year=1990)

    print(checker.generate_summary(report))


if __name__ == "__main__":
    # 統合テスト実行
    test_fact_checker_integration()

    # FactChecker直接テスト
    test_fact_checker_direct()
