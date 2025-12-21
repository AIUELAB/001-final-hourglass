"""
Unit tests for pipeline_verify_sources.py

このテストスイートは、Stage 2: verify-sources パイプラインの
品質判定・重複除外・センシティブフィルタリングをテストします。
"""

import sys
from pathlib import Path

# PYTHONPATH設定
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
import pandas as pd
from scripts.pipeline.pipeline_verify_sources import (
    generate_source_id,
    is_duplicate_source,
    judge_evidence_quality,
    is_blacklisted,
)


class TestSourceIDGeneration:
    """source_id生成のテスト"""

    def test_generate_source_id_basic(self):
        """基本的なsource_id生成"""
        source_id = generate_source_id("イチロー", "https://example.com")
        assert source_id.startswith("SRC-")
        assert len(source_id) == 20  # "SRC-" + 16桁のMD5ハッシュ

    def test_generate_source_id_deterministic(self):
        """同じ入力に対して同じIDを生成"""
        id1 = generate_source_id("イチロー", "https://example.com")
        id2 = generate_source_id("イチロー", "https://example.com")
        assert id1 == id2

    def test_generate_source_id_different_person(self):
        """異なる人物名で異なるIDを生成"""
        id1 = generate_source_id("イチロー", "https://example.com")
        id2 = generate_source_id("山中伸弥", "https://example.com")
        assert id1 != id2

    def test_generate_source_id_different_url(self):
        """異なるURLで異なるIDを生成"""
        id1 = generate_source_id("イチロー", "https://example.com/1")
        id2 = generate_source_id("イチロー", "https://example.com/2")
        assert id1 != id2


class TestDuplicateDetection:
    """重複検出のテスト"""

    def test_is_duplicate_source_empty_df(self):
        """空のDataFrameでは重複なし"""
        empty_df = pd.DataFrame(columns=["source_id"])
        assert is_duplicate_source("SRC-test123", empty_df) is False

    def test_is_duplicate_source_none_df(self):
        """NoneのDataFrameでは重複なし"""
        assert is_duplicate_source("SRC-test123", None) is False

    def test_is_duplicate_source_found(self):
        """既存IDが存在する場合は重複"""
        existing_df = pd.DataFrame({"source_id": ["SRC-abc123", "SRC-def456"]})
        assert is_duplicate_source("SRC-abc123", existing_df) is True

    def test_is_duplicate_source_not_found(self):
        """既存IDが存在しない場合は新規"""
        existing_df = pd.DataFrame({"source_id": ["SRC-abc123", "SRC-def456"]})
        assert is_duplicate_source("SRC-xyz789", existing_df) is False


class TestEvidenceQualityJudgment:
    """根拠品質判定のテスト"""

    def test_quality_A_government_domain(self):
        """政府ドメインはA品質"""
        quality = judge_evidence_quality(
            source_url="https://www.kantei.go.jp/jp/article.html", raw_text="首相官邸の記録", context=""
        )
        assert quality == "A"

    def test_quality_A_academic_domain(self):
        """学術ドメインはA品質"""
        quality = judge_evidence_quality(
            source_url="https://www.kyoto-u.ac.jp/research", raw_text="京都大学の研究", context=""
        )
        assert quality == "A"

    def test_quality_A_ndl_domain(self):
        """国会図書館ドメインはA品質"""
        quality = judge_evidence_quality(
            source_url="https://ndl.go.jp/japan/entry", raw_text="国会図書館の記録", context=""
        )
        assert quality == "A"

    def test_quality_A_keyword_autobiography(self):
        """「自伝」キーワードはA品質"""
        quality = judge_evidence_quality(
            source_url="https://example.com", raw_text="", context="自伝『生き方』より抜粋"
        )
        assert quality == "A"

    def test_quality_A_keyword_official_interview(self):
        """「公式インタビュー」キーワードはA品質"""
        quality = judge_evidence_quality(
            source_url="https://example.com", raw_text="公式インタビューで語った内容", context=""
        )
        assert quality == "A"

    def test_quality_B_wikipedia_with_reference(self):
        """Wikipedia + 参照文献はB品質"""
        # Note: 「出典」「参照」キーワードのみでA_QUALITY_KEYWORDSに該当しない
        quality = judge_evidence_quality(
            source_url="https://ja.wikipedia.org/wiki/イチロー",
            raw_text="2004年シーズン262安打記録を達成。出典: メジャーリーグ記録",
            context="",
        )
        # Wikipediaは.orgなのでA_QUALITY_DOMAINSには該当しない
        # 「出典」キーワードがあるのでB品質
        assert quality == "B"

    def test_quality_C_wikipedia_without_reference(self):
        """Wikipedia（参照文献なし）はC品質"""
        quality = judge_evidence_quality(
            source_url="https://ja.wikipedia.org/wiki/イチロー", raw_text="2004年シーズン記録。", context=""
        )
        assert quality == "C"

    def test_quality_C_unknown_source(self):
        """不明なソースはC品質"""
        quality = judge_evidence_quality(source_url="https://example.com/blog", raw_text="ブログ記事", context="")
        assert quality == "C"


class TestBlacklistMatching:
    """ブラックリスト照合のテスト"""

    def test_blacklist_exact_match(self):
        """名前の完全一致"""
        blacklist_names = ["大リーグ養成ギプス", "タイムマシン"]
        blacklist_patterns = []
        is_bl, reason = is_blacklisted("大リーグ養成ギプス", blacklist_names, blacklist_patterns)
        assert is_bl is True
        assert "blacklist_match" in reason

    def test_blacklist_pattern_match(self):
        """パターンマッチ（正規表現）"""
        blacklist_names = []
        blacklist_patterns = [r"テスト.*", r"ダミー.*"]
        is_bl, reason = is_blacklisted("テスト太郎", blacklist_names, blacklist_patterns)
        assert is_bl is True
        assert "blacklist_pattern" in reason

    def test_blacklist_no_match(self):
        """ブラックリストに該当しない"""
        blacklist_names = ["大リーグ養成ギプス"]
        blacklist_patterns = [r"テスト.*"]
        is_bl, reason = is_blacklisted("イチロー", blacklist_names, blacklist_patterns)
        assert is_bl is False
        assert reason == ""

    def test_blacklist_empty_lists(self):
        """空のブラックリスト"""
        is_bl, reason = is_blacklisted("イチロー", [], [])
        assert is_bl is False
        assert reason == ""


class TestIntegration:
    """統合テスト"""

    def test_full_workflow_verified_source(self):
        """検証済みソースのワークフロー"""
        # A品質のソース
        person_name = "山中伸弥"
        source_url = "https://www.kyoto-u.ac.jp/research"

        # 1. source_id生成
        source_id = generate_source_id(person_name, source_url)
        assert source_id.startswith("SRC-")

        # 2. 重複チェック（初回）
        existing_df = pd.DataFrame(columns=["source_id"])
        assert is_duplicate_source(source_id, existing_df) is False

        # 3. 品質判定
        quality = judge_evidence_quality(source_url, "iPS細胞研究", "")
        assert quality == "A"

        # 4. ブラックリストチェック
        is_bl, _ = is_blacklisted(person_name, [], [])
        assert is_bl is False

    def test_full_workflow_rejected_source(self):
        """却下ソースのワークフロー"""
        # ブラックリスト該当のソース
        person_name = "テスト太郎"
        source_url = "https://example.com/test"

        # 1. source_id生成
        source_id = generate_source_id(person_name, source_url)

        # 2. ブラックリストチェック
        is_bl, reason = is_blacklisted(person_name, [], [r"テスト.*"])
        assert is_bl is True
        assert "blacklist_pattern" in reason

    def test_full_workflow_duplicate_source(self):
        """重複ソースのワークフロー"""
        person_name = "イチロー"
        source_url = "https://example.com"

        # 1. source_id生成
        source_id = generate_source_id(person_name, source_url)

        # 2. 既存DataFrameを作成
        existing_df = pd.DataFrame({"source_id": [source_id]})

        # 3. 重複チェック
        assert is_duplicate_source(source_id, existing_df) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
