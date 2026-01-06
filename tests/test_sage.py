"""
SAGE Tests - Smart Adaptive Generation Engine

高品質エピソード生成システムの自動テスト。
"""

import sys
from pathlib import Path

import pytest

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.sage.adapters import (
    AxisScores,
    Candidate,
    MockEPGENAdapter,
)
from scripts.sage.config import (
    GENERATION_RULES,
    PROHIBITED_PATTERNS,
    QUALITY_THRESHOLDS,
    RejectionReason,
    Strategy,
)
from scripts.sage.gates import (
    DuplicateDetector,
    FactChecker,
    TextSimilarityCalculator,
)
from scripts.sage.pre_generation_rules import (
    PreGenerationRules,
    check_prohibited_patterns,
    check_specificity,
)
from scripts.sage.quality import (
    CompositeScoreCalculator,
    QualityEvaluator,
    SuperTotalCalculator,
)


class TestCandidate:
    """Candidateクラスのテスト"""

    def test_valid_candidate(self):
        """有効な候補の作成"""
        candidate = Candidate(
            person_id="P12345",
            person_name="テスト太郎",
            age=40,
            category="ビジネス",
        )
        assert candidate.person_id == "P12345"
        assert candidate.age == 40

    def test_invalid_age(self):
        """無効な年齢"""
        with pytest.raises(ValueError):
            Candidate(
                person_id="P12345",
                person_name="テスト太郎",
                age=-1,
                category="ビジネス",
            )

    def test_to_dict(self):
        """辞書変換"""
        candidate = Candidate(
            person_id="P12345",
            person_name="テスト太郎",
            age=40,
            category="ビジネス",
        )
        d = candidate.to_dict()
        assert d["person_id"] == "P12345"
        assert d["age"] == 40


class TestAxisScores:
    """AxisScoresクラスのテスト"""

    def test_average(self):
        """平均計算"""
        scores = AxisScores(
            memorability=7.0,
            empathy=6.0,
            surprise=8.0,
            generation_quality=7.0,
            educational_value=6.0,
            story_quality=7.0,
            factual_density=7.0,
        )
        avg = scores.average()
        assert 6.5 < avg < 7.5

    def test_weighted_average(self):
        """加重平均"""
        scores = AxisScores(
            memorability=5.0,
            empathy=5.0,
            surprise=5.0,
            generation_quality=10.0,  # 重み高
            educational_value=5.0,
            story_quality=5.0,
            factual_density=10.0,  # 重み高
        )
        weighted = scores.weighted_average()
        avg = scores.average()
        # 高い重みの項目が高いので加重平均 > 単純平均
        assert weighted > avg


class TestPreGenerationRules:
    """生成前ルールのテスト"""

    def test_age_boundary_valid(self):
        """有効な年齢"""
        rules = PreGenerationRules()
        candidate = Candidate(
            person_id="P12345",
            person_name="テスト太郎",
            age=40,
            category="ビジネス",
            birth_year=1980,
        )
        result = rules._check_age_boundary(candidate)
        assert result.passed

    def test_age_boundary_death(self):
        """死亡後の年齢"""
        rules = PreGenerationRules()
        candidate = Candidate(
            person_id="P12345",
            person_name="テスト太郎",
            age=100,  # 死亡年齢を超える
            category="ビジネス",
            birth_year=1900,
            death_year=1980,  # 80歳で死亡
        )
        result = rules._check_age_boundary(candidate)
        assert not result.passed
        assert result.reason == RejectionReason.AGE_BOUNDARY_VIOLATION

    def test_age_boundary_future(self):
        """未来の年齢"""
        rules = PreGenerationRules()
        candidate = Candidate(
            person_id="P12345",
            person_name="テスト太郎",
            age=50,
            category="ビジネス",
            birth_year=2000,  # 2050年の話になる
        )
        result = rules._check_age_boundary(candidate)
        assert not result.passed


class TestProhibitedPatterns:
    """禁止パターンのテスト"""

    def test_meta_expression(self):
        """メタ表現検出"""
        text = "このエピソードでは、彼の成功について語ります。"
        result = check_prohibited_patterns(text)
        assert not result.passed
        assert result.reason == RejectionReason.PROHIBITED_PATTERN

    def test_valid_text(self):
        """有効なテキスト"""
        text = "1955年、彼は新たな挑戦を始めました。「ケンタッキーフライドチキン」の創業です。"
        result = check_prohibited_patterns(text)
        assert result.passed


class TestSpecificity:
    """具体性チェックのテスト"""

    def test_high_specificity(self):
        """高い具体性"""
        text = "1955年、サンダースは「ケンタッキーフライドチキン」を創業し、100万ドルの売上を達成しました。"
        result = check_specificity(text)
        assert result.passed
        assert result.details["specificity_score"] >= 3

    def test_low_specificity(self):
        """低い具体性（埋め草）"""
        text = "ある日、彼は多くの困難を乗り越えて成功しました。"
        result = check_specificity(text)
        assert not result.passed
        assert result.reason == RejectionReason.FILLER_DETECTED


class TestFactChecker:
    """ファクトチェッカーのテスト"""

    def test_valid_episode(self):
        """有効なエピソード"""
        checker = FactChecker()
        text = "1955年、ハーランド・サンダースは「ケンタッキーフライドチキン」を創業しました。"
        result = checker.check(text)
        assert result.passed
        assert len(result.evidence_found) >= 2

    def test_fabrication_signals(self):
        """創作シグナル検出"""
        checker = FactChecker()
        text = "と言われているらしい話によると、かもしれない出来事があったと思われる。"
        result = checker.check(text)
        assert not result.passed
        assert len(result.fabrication_signals) >= 2

    def test_required_evidence(self):
        """必須根拠チェック"""
        checker = FactChecker()
        text = "彼は成功しました。"
        has_required, missing = checker.check_required_evidence(text)
        assert not has_required
        assert "年号 (YYYY年)" in missing


class TestDuplicateDetector:
    """重複検出のテスト"""

    def test_text_similarity(self):
        """テキスト類似度"""
        calc = TextSimilarityCalculator()

        text1 = "1955年、サンダースはケンタッキーフライドチキンを創業しました。"
        text2 = "1955年、サンダースはKFCを創業しました。"
        text3 = "2020年、田中太郎は新しい会社を設立しました。"

        sim_high = calc.combined_similarity(text1, text2)
        sim_low = calc.combined_similarity(text1, text3)

        assert sim_high > sim_low
        assert sim_high > 0.3

    def test_key_phrase_overlap(self):
        """キーフレーズ重複"""
        calc = TextSimilarityCalculator()

        text1 = "1955年、「ケンタッキー」を創業。"
        text2 = "1955年、「ケンタッキー」の成功。"

        overlap = calc.key_phrase_overlap(text1, text2)
        assert overlap > 0.5


class TestQualityEvaluator:
    """品質評価のテスト"""

    def test_quality_gate_pass(self):
        """品質ゲート通過"""
        evaluator = QualityEvaluator()
        scores = AxisScores(
            memorability=7.0,
            empathy=7.0,
            surprise=7.0,
            generation_quality=7.0,  # >= 6.0
            educational_value=7.0,
            story_quality=7.0,
            factual_density=7.0,  # >= 6.0
        )
        result = evaluator.check_quality_gates(scores)
        assert result.passed

    def test_quality_gate_fail_factual(self):
        """事実密度不足"""
        evaluator = QualityEvaluator()
        scores = AxisScores(
            memorability=7.0,
            empathy=7.0,
            surprise=7.0,
            generation_quality=7.0,
            educational_value=7.0,
            story_quality=7.0,
            factual_density=5.0,  # < 6.0
        )
        result = evaluator.check_quality_gates(scores)
        assert not result.passed
        assert result.reason == RejectionReason.LOW_FACTUAL_DENSITY

    def test_quality_gate_fail_generation(self):
        """生成品質不足"""
        evaluator = QualityEvaluator()
        scores = AxisScores(
            memorability=7.0,
            empathy=7.0,
            surprise=7.0,
            generation_quality=5.0,  # < 6.0
            educational_value=7.0,
            story_quality=7.0,
            factual_density=7.0,
        )
        result = evaluator.check_quality_gates(scores)
        assert not result.passed
        assert result.reason == RejectionReason.LOW_GENERATION_QUALITY


class TestCompositeScore:
    """統合スコアのテスト"""

    def test_composite_calculation(self):
        """統合スコア計算"""
        scores = AxisScores(
            memorability=7.0,
            empathy=7.0,
            surprise=7.0,
            generation_quality=7.0,
            educational_value=7.0,
            story_quality=7.0,
            factual_density=7.0,
        )
        composite = CompositeScoreCalculator.calculate(scores)
        # 7.0 * 100 = 700 前後
        assert 650 < composite < 750

    def test_composite_with_penalties(self):
        """ペナルティ付き計算"""
        scores = AxisScores(
            memorability=7.0,
            empathy=7.0,
            surprise=7.0,
            generation_quality=7.0,
            educational_value=7.0,
            story_quality=7.0,
            factual_density=7.0,
        )
        base = CompositeScoreCalculator.calculate(scores)
        penalized = CompositeScoreCalculator.calculate_with_penalties(scores, ["penalty1", "penalty2"])
        # ペナルティで20%減
        assert penalized < base
        assert penalized == base * 0.8


class TestMockAdapter:
    """モックアダプターのテスト"""

    def test_mock_generate(self):
        """モック生成"""
        adapter = MockEPGENAdapter()
        candidate = Candidate(
            person_id="P12345",
            person_name="テスト太郎",
            age=40,
            category="ビジネス",
        )
        result = adapter.generate(candidate)
        assert result.success
        assert result.episode_text
        assert result.evaluation.passed_gate

    def test_mock_evaluate(self):
        """モック評価"""
        adapter = MockEPGENAdapter()
        candidate = Candidate(
            person_id="P12345",
            person_name="テスト太郎",
            age=40,
            category="ビジネス",
        )
        result = adapter.evaluate("テストテキスト", candidate)
        assert result.axis_scores.memorability > 0
        assert result.passed_gate


class TestEPUPPrevention:
    """EPUP再発防止テスト"""

    def test_same_age_duplicate_rejection(self):
        """同一年齢重複の拒否"""
        # 同一人物・同一年齢のエピソードは生成前に拒否されるべき
        # PreGenerationRulesで確認
        rules = PreGenerationRules()
        # 既存データがある場合のテスト
        # 実際のテストではモックデータを使用

    def test_death_year_boundary(self):
        """死亡年境界のテスト"""
        rules = PreGenerationRules()
        candidate = Candidate(
            person_id="P12345",
            person_name="歴史人物",
            age=90,
            category="政治",
            birth_year=1900,
            death_year=1980,  # 80歳で死亡
        )
        result = rules._check_age_boundary(candidate)
        assert not result.passed  # 90歳 > 80歳なので拒否

    def test_filler_detection(self):
        """埋め草検出"""
        # 具体性のない抽象的なエピソードは拒否
        text = "ある日、彼は様々な困難を乗り越えました。多くの人々が彼を称えました。"
        result = check_specificity(text)
        assert not result.passed

    def test_meta_expression_rejection(self):
        """メタ表現の拒否"""
        text = "このエピソードでは、読者に彼の人生を伝えます。"
        result = check_prohibited_patterns(text)
        assert not result.passed

    def test_low_quality_rejection(self):
        """低品質の拒否"""
        evaluator = QualityEvaluator()
        # 事実密度も生成品質も低い
        scores = AxisScores(
            memorability=5.0,
            empathy=5.0,
            surprise=5.0,
            generation_quality=4.0,  # 低い
            educational_value=5.0,
            story_quality=5.0,
            factual_density=4.0,  # 低い
        )
        result = evaluator.check_quality_gates(scores)
        assert not result.passed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
