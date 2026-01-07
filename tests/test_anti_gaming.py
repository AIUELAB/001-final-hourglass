"""
AntiGamingMonitor Tests - アンチゲーミングのテスト

SAGE vNext Phase 3: AntiGamingMonitorの単体テスト
"""

import sys
from pathlib import Path

import pytest

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.sage.gates.anti_gaming import (
    AntiGamingMonitor,
    AntiGamingResult,
    get_gaming_violations,
    quick_anti_gaming_check,
)


class TestAntiGamingResult:
    """AntiGamingResult のテスト"""

    def test_to_dict(self):
        """辞書変換"""
        result = AntiGamingResult(
            passed=True,
            violations=[],
            keyword_density=0.05,
            abstract_ratio=0.10,
            ngram_repetition=0.15,
            specifics_count=3,
        )
        d = result.to_dict()
        assert d["passed"] is True
        assert d["violations"] == []
        assert d["keyword_density"] == 0.05
        assert d["abstract_ratio"] == 0.1
        assert d["specifics_count"] == 3

    def test_failed_result(self):
        """失敗結果"""
        result = AntiGamingResult(
            passed=False,
            violations=["keyword_stuffing", "missing_specifics"],
            keyword_density=0.20,
            specifics_count=0,
        )
        assert not result.passed
        assert len(result.violations) == 2


class TestAntiGamingMonitor:
    """AntiGamingMonitor のテスト"""

    @pytest.fixture
    def monitor(self):
        """テスト用モニター"""
        return AntiGamingMonitor()

    def test_init_default(self, monitor):
        """デフォルト初期化"""
        assert monitor.max_keyword_density == 0.15
        assert monitor.max_abstract_ratio == 0.30
        assert monitor.max_ngram_repetition == 0.20
        assert monitor.min_specifics == 1

    def test_init_custom(self):
        """カスタム初期化"""
        monitor = AntiGamingMonitor(
            max_keyword_density=0.10,
            min_specifics=2,
        )
        assert monitor.max_keyword_density == 0.10
        assert monitor.min_specifics == 2

    def test_good_episode_pass(self, monitor):
        """良質なエピソードはパス"""
        text = """
        1995年、田中太郎は「革新的アルゴリズム」を発表した。
        この論文は東京大学の研究グループと共同で執筆され、
        コンピュータサイエンス学会で第1位を獲得した。
        当時25歳だった田中は、この成果により若手研究者賞を受賞した。
        """
        result = monitor.check(text, "田中太郎")
        assert result.passed
        assert result.specifics_count >= 1

    def test_keyword_stuffing_detected(self, monitor):
        """キーワード詰め込み検出"""
        text = """
        彼は革命的な天才であり、伝説的な偉大な巨匠だった。
        その衝撃的で画期的な奇跡は歴史的な最高記録を樹立。
        レジェンドとして永遠に不朽の金字塔として讃えられる。
        """
        result = monitor.check(text)
        assert result.keyword_density > 0.15
        assert "keyword_stuffing" in result.violations

    def test_missing_specifics_detected(self, monitor):
        """具体性不足検出"""
        text = """
        ある日、彼は素晴らしいことを成し遂げた。
        多くの人々が感動し、様々な評価を受けた。
        それは本当に素晴らしい出来事だった。
        """
        result = monitor.check(text)
        assert result.specifics_count < 1
        assert "missing_specifics" in result.violations

    def test_too_abstract_detected(self):
        """抽象語過多検出"""
        monitor = AntiGamingMonitor(max_abstract_ratio=0.05)  # 厳格な閾値
        text = """
        ある日、おそらくきっと何かが起きた。
        もしかしたらたぶんそれなりに様々なことがあった。
        いろいろとにかく基本的に一般的に良かった。
        """
        result = monitor.check(text)
        assert result.abstract_ratio > 0.05
        assert "too_abstract" in result.violations

    def test_template_smell_detected(self):
        """テンプレート臭検出"""
        monitor = AntiGamingMonitor(max_ngram_repetition=0.10)  # 厳格な閾値
        text = "彼は彼は彼は彼は彼は彼は彼は彼は彼は彼は素晴らしかった。"
        result = monitor.check(text)
        # 繰り返しが多いとngram_repetitionが高くなる
        assert result.ngram_repetition > 0.10

    def test_person_name_excluded(self, monitor):
        """人物名は除外される"""
        text = """
        2000年、山田花子は山田花子賞を受賞した。
        山田花子の功績は「山田花子記念財団」に記録されている。
        """
        result_with_name = monitor.check(text, "山田花子")
        result_without_name = monitor.check(text, None)
        # 人物名を除外した場合、キーワード密度が変わる可能性
        assert result_with_name.specifics_count >= 1

    def test_proper_nouns_detected(self, monitor):
        """固有名詞検出"""
        text = """
        1985年に「情熱大陸」という番組で紹介された。
        東京大学で研究を続け、第3回日本学術賞を受賞。
        著書『人生の選択』は100万部を突破した。
        """
        result = monitor.check(text)
        assert result.specifics_count >= 3  # 年号、作品名、組織名
        assert result.passed

    def test_edge_case_empty_text(self, monitor):
        """空テキスト"""
        result = monitor.check("")
        assert result.keyword_density == 0.0
        assert result.abstract_ratio == 0.0
        assert result.specifics_count == 0

    def test_edge_case_short_text(self, monitor):
        """短いテキスト"""
        result = monitor.check("こんにちは")
        assert result.specifics_count == 0

    def test_year_detection(self, monitor):
        """年号検出"""
        text = "1990年と2020年に重要な出来事があった。"
        result = monitor.check(text)
        assert result.specifics_count >= 2

    def test_organization_detection(self, monitor):
        """組織名検出"""
        text = "東京大学と京都大学の研究チームが協力した。"
        result = monitor.check(text)
        assert result.specifics_count >= 2


class TestQuickFunctions:
    """便利関数のテスト"""

    def test_quick_anti_gaming_check_pass(self):
        """クイックチェック - パス"""
        text = "2000年、「成功の秘訣」という著書を出版した。"
        assert quick_anti_gaming_check(text) is True

    def test_quick_anti_gaming_check_fail(self):
        """クイックチェック - 失敗"""
        text = "ある日、様々なことがあった。"
        # 具体性不足で失敗
        assert quick_anti_gaming_check(text) is False

    def test_get_gaming_violations_empty(self):
        """違反なし"""
        text = "1995年に「新型エンジン」の特許を取得した。"
        violations = get_gaming_violations(text)
        assert violations == []

    def test_get_gaming_violations_multiple(self):
        """複数違反"""
        text = "ある日、様々なことがあった。とにかく基本的に良かった。"
        violations = get_gaming_violations(text)
        assert "missing_specifics" in violations


class TestRealWorldCases:
    """実際のエピソードに近いケース"""

    @pytest.fixture
    def monitor(self):
        return AntiGamingMonitor()

    def test_historical_episode(self, monitor):
        """歴史的エピソード"""
        text = """
        1969年7月20日、アポロ11号は月面着陸に成功した。
        ニール・アームストロングは「これは一人の人間にとっては小さな一歩だが、
        人類にとっては大きな飛躍である」と述べた。
        この歴史的瞬間は世界中で6億人が視聴したと言われている。
        """
        result = monitor.check(text, "ニール・アームストロング")
        assert result.passed
        assert result.specifics_count >= 2

    def test_sports_episode(self, monitor):
        """スポーツエピソード"""
        text = """
        2023年、大谷翔平はメジャーリーグで44本塁打を記録した。
        「ロサンゼルス・エンゼルス」から「ドジャース」へ移籍し、
        史上最高額の10年7億ドル契約を締結。
        日本人選手として初のホームラン王に輝いた。
        """
        result = monitor.check(text, "大谷翔平")
        assert result.passed
        assert result.specifics_count >= 3

    def test_fictional_episode_should_fail_without_specifics(self, monitor):
        """架空エピソード（具体性なし）"""
        text = """
        ある日、彼は何か大切なことに気づいた。
        それは彼の人生を変える出来事だった。
        多くの人が彼の変化に気づいた。
        """
        result = monitor.check(text)
        assert not result.passed
        assert "missing_specifics" in result.violations


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
