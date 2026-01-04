#!/usr/bin/env python3
"""
寄せ集めエピソード品質ゲートのテスト
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.validation.hodgepodge_quality_gate import check_episode_quality


class TestHodgepodgeQualityGate:
    """品質ゲートのテスト"""

    def test_good_episode_passes(self):
        """正常なエピソードは合格する"""
        text = """あなたと同じ60歳のとき、黒澤明は映画界から「終わった」と見なされていました。
1970年、ハリウッド映画『トラ・トラ・トラ!』の監督を途中降板させられ、
その後の企画も次々と頓挫。失意の中、自宅で自殺未遂を図るという痛ましい出来事まで起こしました。
しかし彼は諦めませんでした。病室で目覚めた黒澤は、すぐにソ連との合作映画の構想を練り始めたのです。"""

        result = check_episode_quality(text, 60)
        assert result["passed"] is True
        assert result["score"] < 10

    def test_hodgepodge_episode_fails(self):
        """寄せ集めエピソードは不合格になる"""
        # 15年スパン + 3作品 + 時系列ジャンプ = 確実に不合格
        text = """あなたと同じ60歳のとき、黒澤明は映画界から「終わった」と見なされていました。
1970年、ハリウッド映画を途中降板させられ、失意の中、自殺未遂を図りました。
しかし1975年に『デルス・ウザーラ』でアカデミー賞を受賞。見事に復活を遂げたのです。
その後も1980年に『影武者』、1985年に『乱』など傑作を生み出し続けました。
やがて世界的巨匠として評価され、後に多くの映画監督に影響を与えました。"""

        result = check_episode_quality(text, 60)
        assert result["passed"] is False, f"score={result['score']}, reason={result['reason']}"
        assert result["score"] >= 10

    def test_multiple_ages_detected(self):
        """複数年齢の言及を検出する"""
        text = """あなたと同じ65歳のとき、益川敏英は京大を定年退職しました。
彼の理論は1973年、33歳のときに発表されました。"""

        result = check_episode_quality(text, 65)
        assert 33 in result["details"]["other_ages"]
        assert result["score"] >= 3  # 他年齢言及でスコア加算

    def test_multiple_works_detected(self):
        """複数作品の列挙を検出する"""
        text = """あなたと同じ50歳のとき、彼は『作品A』『作品B』『作品C』『作品D』を発表しました。"""

        result = check_episode_quality(text, 50)
        assert result["details"]["works_count"] >= 4
        assert result["score"] >= 4  # 3作品以上でスコア加算

    def test_time_jumps_detected(self):
        """時系列ジャンプ語の多用を検出する"""
        text = """あなたと同じ40歳のとき、彼は活動を開始しました。
その後、翌年には成功を収め、数年後にはさらに発展しました。
後には国際的な評価を得て、やがて歴史に名を残しました。"""

        result = check_episode_quality(text, 40)
        assert result["details"]["time_jumps"] >= 4

    def test_year_range_detected(self):
        """年号の広がりを検出する"""
        text = """あなたと同じ50歳のとき、1990年に活動開始。2020年には大成功を収めました。"""

        result = check_episode_quality(text, 50)
        years = result["details"]["years"]
        assert 1990 in years
        assert 2020 in years

    def test_extract_ages(self):
        """年齢抽出のテスト"""
        from scripts.validation.hodgepodge_quality_gate import extract_ages

        text = "30歳で始め、45歳で成功、60歳で引退"
        ages = extract_ages(text)
        assert ages == [30, 45, 60]

    def test_extract_years(self):
        """年号抽出のテスト"""
        from scripts.validation.hodgepodge_quality_gate import extract_years

        text = "1990年に開始、2000年に発展、2020年に完成"
        years = extract_years(text)
        assert 1990 in years
        assert 2000 in years
        assert 2020 in years

    def test_fictional_ages_ignored(self):
        """架空キャラの極端な年齢は別処理"""
        text = """あなたと同じ2000歳のとき、ガンダルフは中つ国で活動していました。
1000年前から旅を続け、2000年の時を経て知恵を得ました。"""

        result = check_episode_quality(text, 2000)
        # 架空キャラの場合、年号1000-2000は検出されるが
        # 年齢差は大きくないので他年齢問題は発生しない
        assert len(result["details"]["other_ages"]) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
