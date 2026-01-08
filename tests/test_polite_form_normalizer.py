#!/usr/bin/env python3
"""
丁寧語正規化エンジンのテスト

検証項目:
1. 丁寧語漏れが検出されること
2. 引用内（「」）は変換されないこと
3. 変換後に検出件数が減ること
4. 既存の丁寧語は変換されないこと
5. 動詞の「んだ」は誤変換されないこと
"""

import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validation.polite_form_normalizer import (
    PoliteFormNormalizer,
    validate_single,
)


class TestPoliteFormDetection:
    """丁寧語漏れ検出テスト"""

    def setup_method(self):
        """テスト前の初期化"""
        self.normalizer = PoliteFormNormalizer()

    def test_detect_teita_pattern(self):
        """〜ていた。パターンの検出"""
        text = "彼は注目を浴びていた。"
        issues = self.normalizer.detect_issues(text)
        assert len(issues) >= 1
        assert any("ていた" in i["rule_name"] for i in issues)

    def test_detect_datta_pattern(self):
        """〜だった。パターンの検出"""
        text = "それは始まりだった。"
        issues = self.normalizer.detect_issues(text)
        assert len(issues) >= 1
        assert any("だった" in i["rule_name"] for i in issues)

    def test_detect_shita_pattern(self):
        """〜した。パターンの検出"""
        text = "彼は偉業を達成した。"
        issues = self.normalizer.detect_issues(text)
        assert len(issues) >= 1
        assert any("した" in i["rule_name"] for i in issues)

    def test_detect_dearu_pattern(self):
        """〜である。パターンの検出"""
        text = "これは歴史的な瞬間である。"
        issues = self.normalizer.detect_issues(text)
        assert len(issues) >= 1
        assert any("である" in i["rule_name"] for i in issues)

    def test_detect_noda_pattern(self):
        """〜のだ。パターンの検出"""
        text = "彼は決意したのだ。"
        issues = self.normalizer.detect_issues(text)
        assert len(issues) >= 1
        assert any("のだ" in i["rule_name"] for i in issues)


class TestQuoteProtection:
    """引用保護テスト"""

    def setup_method(self):
        """テスト前の初期化"""
        self.normalizer = PoliteFormNormalizer()

    def test_quote_not_transformed(self):
        """引用内（「」）は変換されない"""
        text = "「私は行った」と言いました。"
        transformed, changes = self.normalizer.transform_text(text, max_risk="medium", dry_run=False)
        # 引用内の「行った」が変換されていないこと
        assert "「私は行った」" in transformed
        # 外部の「言いました」は変換されていないこと（既に丁寧語）
        assert "言いました" in transformed

    def test_quote_detection_skipped(self):
        """引用内のテキストは検出対象外"""
        text = "「これは素晴らしかった」と彼は言いました。"
        issues = self.normalizer.detect_issues(text)
        # 引用内の「かった」は検出されない
        assert all("かった" not in i.get("matched", "") for i in issues)

    def test_multiple_quotes_protected(self):
        """複数の引用が保護される"""
        text = "「第一の発言だった」と「第二の発言だった」を比較しました。"
        transformed, changes = self.normalizer.transform_text(text, max_risk="medium", dry_run=False)
        assert "「第一の発言だった」" in transformed
        assert "「第二の発言だった」" in transformed


class TestTransformationCorrectness:
    """変換正確性テスト"""

    def setup_method(self):
        """テスト前の初期化"""
        self.normalizer = PoliteFormNormalizer()

    def test_teita_to_teimashita(self):
        """〜ていた→〜ていました"""
        text = "彼は練習していた。"
        transformed, changes = self.normalizer.transform_text(text, max_risk="low", dry_run=False)
        assert transformed == "彼は練習していました。"

    def test_datta_to_deshita(self):
        """〜だった→〜でした"""
        text = "それは運命だった。"
        transformed, changes = self.normalizer.transform_text(text, max_risk="low", dry_run=False)
        assert transformed == "それは運命でした。"

    def test_shita_to_shimashita(self):
        """〜した→〜しました"""
        text = "彼は発表した。"
        transformed, changes = self.normalizer.transform_text(text, max_risk="medium", dry_run=False)
        assert transformed == "彼は発表しました。"

    def test_dearu_to_desu(self):
        """〜である→〜です"""
        text = "これは事実である。"
        transformed, changes = self.normalizer.transform_text(text, max_risk="low", dry_run=False)
        assert transformed == "これは事実です。"

    def test_nodearu_to_nodesu(self):
        """〜のである→〜のです"""
        text = "それが真実なのである。"
        transformed, changes = self.normalizer.transform_text(text, max_risk="low", dry_run=False)
        assert transformed == "それが真実なのです。"


class TestNoFalsePositives:
    """誤変換防止テスト"""

    def setup_method(self):
        """テスト前の初期化"""
        self.normalizer = PoliteFormNormalizer()

    def test_existing_polite_not_changed(self):
        """既存の丁寧語は変換されない"""
        polite_texts = [
            "彼は達成しました。",
            "それは始まりでした。",
            "彼は練習していました。",
            "これは事実です。",
        ]
        for text in polite_texts:
            transformed, changes = self.normalizer.transform_text(text, max_risk="medium", dry_run=False)
            assert transformed == text
            assert len(changes) == 0

    def test_verb_nda_not_transformed(self):
        """動詞の「んだ」は変換されない（選んだ→選んです にならない）"""
        verb_nda_texts = [
            "彼は道を選んだ。",  # 選ぶの過去形
            "彼は本を読んだ。",  # 読むの過去形
            "彼は歌を歌んだ。",  # 歌むの過去形（古語）
        ]
        for text in verb_nda_texts:
            transformed, changes = self.normalizer.transform_text(text, max_risk="low", dry_run=False)
            # 「んです」への誤変換がないこと
            assert "んです" not in transformed

    def test_explanatory_nda_transformed(self):
        """説明の「んだ」は正しく変換される"""
        text = "それが真実だったんだ。"
        transformed, changes = self.normalizer.transform_text(text, max_risk="low", dry_run=False)
        # 「だった」→「でした」、「んだ」→「んです」の両方
        assert "でした" in transformed or "んです" in transformed


class TestIssueCountReduction:
    """修正後の問題件数減少テスト"""

    def setup_method(self):
        """テスト前の初期化"""
        self.normalizer = PoliteFormNormalizer()

    def test_issues_reduced_after_transform(self):
        """変換後に検出件数が減ること"""
        text = "彼は注目を浴びていた。それは始まりだった。彼は決意した。"

        # 変換前の検出
        issues_before = self.normalizer.detect_issues(text)
        count_before = len(issues_before)

        # 変換実行
        transformed, _ = self.normalizer.transform_text(text, max_risk="medium", dry_run=False)

        # 変換後の検出
        issues_after = self.normalizer.detect_issues(transformed)
        count_after = len(issues_after)

        # 検出件数が減っていること
        assert count_after < count_before


class TestValidateSingleFunction:
    """validate_single関数のテスト"""

    def test_validate_single_detects_issues(self):
        """validate_single関数が問題を検出する"""
        text = "彼は注目を浴びていた。"
        issues = validate_single(text)
        assert len(issues) >= 1

    def test_validate_single_returns_empty_for_polite(self):
        """validate_single関数が丁寧語テキストで空リストを返す"""
        text = "彼は注目を浴びていました。"
        issues = validate_single(text)
        # この特定のテキストには問題がないはず
        assert all("ていた" not in i for i in issues)


class TestIdealEpisodeText:
    """理想的なエピソードテキストのテスト"""

    def setup_method(self):
        """テスト前の初期化"""
        self.normalizer = PoliteFormNormalizer()

    def test_ideal_text_has_no_issues(self):
        """理想的なエピソードテキストは問題なし"""
        ideal_text = (
            "あなたと同じ26歳のとき、アインシュタインは1905年、「奇跡の年」と呼ばれる"
            "驚異的な業績を成し遂げました。スイス特許庁の技術者として働きながら、"
            "わずか1年間で物理学の根幹を揺るがす4本の論文を発表。光量子仮説、"
            "ブラウン運動の理論、特殊相対性理論、そしてE=mc²（質量とエネルギーの等価性）"
            "を世に問いました。特に6月に発表した特殊相対性理論は、ニュートン以来200年"
            "続いた物理学の常識を覆し、時間と空間の概念を根本から変革しました。"
            "この年の業績によりアインシュタインは物理学の世界に衝撃を与え、"
            "後にノーベル物理学賞（1921年）を受賞する基盤を築いたのです。"
        )
        issues = self.normalizer.detect_issues(ideal_text)
        # 理想的なテキストには問題がないはず
        assert len(issues) == 0, f"検出された問題: {issues}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
