#!/usr/bin/env python3
"""
人物名正規化の回帰テスト

Phase 8で追加された職業接頭辞除去機能のテスト
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.data.normalize_person_names import PersonNameNormalizer


def test_profession_prefix_normalization():
    """職業接頭辞「XX・」形式の正規化テスト"""
    normalizer = PersonNameNormalizer(min_confidence=0.85)

    # Phase 8で実際に修正した3件のテスト
    test_cases = [
        ("浮世絵師・歌川国芳", "歌川国芳", "浮世絵師"),
        ("人間国宝・金重陶陽", "金重陶陽", "人間国宝"),
        ("歌舞伎俳優・中村勘九郎", "中村勘九郎", "歌舞伎俳優"),
    ]

    for before, expected_name, expected_title in test_cases:
        result = normalizer._match_profession_prefix(before)
        assert result is not None, f"正規化失敗: {before}"
        assert (
            result.normalized_name == expected_name
        ), f"名前が一致しません: {before} → {result.normalized_name} (期待値: {expected_name})"
        assert result.title == expected_title, f"肩書きが一致しません: {result.title} (期待値: {expected_title})"
        assert result.confidence >= 0.85, f"信頼度が低すぎます: {result.confidence}"
        assert result.pattern_type == "PROFESSION_PREFIX", f"パターンタイプが一致しません: {result.pattern_type}"

    print("✅ test_profession_prefix_normalization: PASSED")


def test_no_false_positives():
    """誤検出がないことを確認（中黒を含む正常な名前）"""
    normalizer = PersonNameNormalizer(min_confidence=0.85)

    # 姓・名の中黒は検出されないべき
    normal_names = [
        "歌川国芳",  # 職業なし
        "金重陶陽",  # 職業なし
        "中村勘九郎",  # 職業なし
    ]

    for name in normal_names:
        result = normalizer.normalize(name)
        if result is not None:
            # 職業接頭辞パターンでは検出されないはず
            assert result.pattern_type != "PROFESSION_PREFIX", f"誤検出: {name} がPROFESSION_PREFIXとして検出されました"

    print("✅ test_no_false_positives: PASSED")


def test_all_new_professions_registered():
    """新しく追加した3職業がPROFESSION_KEYWORDSに登録されているか"""
    from scripts.data.normalize_person_names import PROFESSION_KEYWORDS

    required_professions = ["浮世絵師", "人間国宝", "歌舞伎俳優"]

    for prof in required_professions:
        assert prof in PROFESSION_KEYWORDS, f"職業「{prof}」がPROFESSION_KEYWORDSに登録されていません"

    print("✅ test_all_new_professions_registered: PASSED")


if __name__ == "__main__":
    # 全テストを実行
    test_all_new_professions_registered()
    test_profession_prefix_normalization()
    test_no_false_positives()
    print("\n✅ すべてのテストが成功しました")
