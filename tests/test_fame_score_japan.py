#!/usr/bin/env python3
"""
日本向けFame Score計算のテスト。

テストケース:
1. 非日本人のスコアが変わらないこと
2. 日本人のスコアが正しく上乗せされること
3. カテゴリ重みが正しく適用されること
4. PV比率ボーナスが正しく計算されること
5. 大谷翔平がJapan Top 10に入ること
"""

import csv
from pathlib import Path

import pytest

from scripts.fame_score_v3.scorer_japan import (
    JapanBoostConfig,
    calculate_boost_breakdown,
    calculate_japan_score,
    load_config,
)


# テスト用の固定設定
@pytest.fixture
def test_config():
    """テスト用の設定（本番と同じ値）"""
    return JapanBoostConfig(
        enabled=True,
        base_alpha=0.10,
        category_weights={
            "スポーツ": 0.40,
            "音楽": 0.20,
            "エンターテイメント": 0.20,
            "アニメ": 0.25,
            "漫画": 0.25,
            "ゲーム": 0.20,
            "芸術・文化": 0.15,
            "文学": 0.15,
            "科学・技術": 0.15,
            "映画・演劇": 0.10,
            "政治・社会": 0.05,
            "歴史": 0.05,
            "default": 0.05,
        },
        pv_ratio_max_bonus=0.15,
        pv_ratio_scale=0.50,
    )


class TestNonJapaneseScore:
    """非日本人のスコアが変わらないことをテスト"""

    def test_non_japanese_score_unchanged(self, test_config):
        """非日本人のスコアはグローバルスコアと同じ"""
        global_score = 789.06
        japan_score = calculate_japan_score(
            global_score=global_score,
            is_japanese=False,
            category="政治・社会",
            wikipedia_pv_ja=50000,
            multi_lang_pv=10000000,
            config=test_config,
        )
        assert japan_score == global_score

    def test_non_japanese_breakdown(self, test_config):
        """非日本人のブレークダウンは全てゼロ"""
        breakdown = calculate_boost_breakdown(
            is_japanese=False,
            category="スポーツ",
            wikipedia_pv_ja=100000,
            multi_lang_pv=1000000,
            config=test_config,
        )
        assert breakdown["is_japanese"] is False
        assert breakdown["base_alpha"] == 0.0
        assert breakdown["category_weight"] == 0.0
        assert breakdown["pv_ratio_bonus"] == 0.0
        assert breakdown["total_boost"] == 0.0
        assert breakdown["multiplier"] == 1.0


class TestJapaneseScoreBoost:
    """日本人のスコア上乗せをテスト"""

    def test_base_alpha_applied(self, test_config):
        """基本上乗せ（10%）が適用される"""
        global_score = 100.0
        # カテゴリをdefaultにしてPVボーナスなしで計算
        japan_score = calculate_japan_score(
            global_score=global_score,
            is_japanese=True,
            category="その他",  # default: 5%
            wikipedia_pv_ja=0,
            multi_lang_pv=0,
            config=test_config,
        )
        # 100 * (1 + 0.10 + 0.05) = 115
        assert japan_score == 115.0

    def test_sports_category_weight(self, test_config):
        """スポーツカテゴリの重み（+40%）が正しく適用される"""
        global_score = 100.0
        japan_score = calculate_japan_score(
            global_score=global_score,
            is_japanese=True,
            category="スポーツ",
            wikipedia_pv_ja=0,
            multi_lang_pv=0,
            config=test_config,
        )
        # 100 * (1 + 0.10 + 0.40) = 150
        assert japan_score == 150.0

    def test_music_category_weight(self, test_config):
        """音楽カテゴリの重み（+20%）が正しく適用される"""
        global_score = 100.0
        japan_score = calculate_japan_score(
            global_score=global_score,
            is_japanese=True,
            category="音楽",
            wikipedia_pv_ja=0,
            multi_lang_pv=0,
            config=test_config,
        )
        # 100 * (1 + 0.10 + 0.20) = 130
        assert japan_score == 130.0

    def test_anime_category_weight(self, test_config):
        """アニメカテゴリの重み（+25%）が正しく適用される"""
        global_score = 100.0
        japan_score = calculate_japan_score(
            global_score=global_score,
            is_japanese=True,
            category="アニメ",
            wikipedia_pv_ja=0,
            multi_lang_pv=0,
            config=test_config,
        )
        # 100 * (1 + 0.10 + 0.25) = 135
        assert japan_score == 135.0


class TestPVRatioBonus:
    """PV比率ボーナスのテスト"""

    def test_pv_ratio_bonus_calculation(self, test_config):
        """PV比率ボーナスが正しく計算される"""
        breakdown = calculate_boost_breakdown(
            is_japanese=True,
            category="スポーツ",
            wikipedia_pv_ja=100000,  # 10%
            multi_lang_pv=1000000,
            config=test_config,
        )
        # ja_pv_ratio = 0.1, bonus = 0.1 * 0.5 = 0.05
        assert breakdown["pv_ratio_bonus"] == 0.05

    def test_pv_ratio_bonus_max_cap(self, test_config):
        """PV比率ボーナスが最大値（15%）でキャップされる"""
        breakdown = calculate_boost_breakdown(
            is_japanese=True,
            category="スポーツ",
            wikipedia_pv_ja=500000,  # 50%
            multi_lang_pv=1000000,
            config=test_config,
        )
        # ja_pv_ratio = 0.5, bonus = 0.5 * 0.5 = 0.25 -> capped to 0.15
        assert breakdown["pv_ratio_bonus"] == 0.15

    def test_pv_ratio_bonus_zero_when_no_pv(self, test_config):
        """PVデータがない場合はボーナスゼロ"""
        breakdown = calculate_boost_breakdown(
            is_japanese=True,
            category="スポーツ",
            wikipedia_pv_ja=0,
            multi_lang_pv=0,
            config=test_config,
        )
        assert breakdown["pv_ratio_bonus"] == 0.0


class TestOhtaniShohei:
    """大谷翔平の実データでのテスト"""

    def test_ohtani_score_calculation(self, test_config):
        """大谷翔平のスコアが正しく計算される"""
        # 実データ: global_score=536.85, category=スポーツ
        # ja_pv=261588, multi_pv=5452838
        global_score = 536.85
        japan_score = calculate_japan_score(
            global_score=global_score,
            is_japanese=True,
            category="スポーツ",
            wikipedia_pv_ja=261588,
            multi_lang_pv=5452838,
            config=test_config,
        )

        # 内訳計算
        # base_alpha = 0.10
        # category_weight = 0.40 (スポーツ)
        # ja_pv_ratio = 261588 / 5452838 = 0.048
        # pv_bonus = min(0.048 * 0.5, 0.15) = 0.024
        # total_boost = 0.10 + 0.40 + 0.024 = 0.524
        # japan_score = 536.85 * 1.524 = 818.16

        # 許容誤差0.5以内
        assert 817.5 <= japan_score <= 818.5

    def test_ohtani_breakdown(self, test_config):
        """大谷翔平のブレークダウンが正しい"""
        breakdown = calculate_boost_breakdown(
            is_japanese=True,
            category="スポーツ",
            wikipedia_pv_ja=261588,
            multi_lang_pv=5452838,
            config=test_config,
        )
        assert breakdown["base_alpha"] == 0.10
        assert breakdown["category_weight"] == 0.40
        # PV ratio bonus ≈ 0.024
        assert 0.02 <= breakdown["pv_ratio_bonus"] <= 0.03
        # Total boost ≈ 0.524
        assert 0.52 <= breakdown["total_boost"] <= 0.53
        # Multiplier ≈ 1.524
        assert 1.52 <= breakdown["multiplier"] <= 1.53


class TestOhtaniTop10:
    """大谷翔平がJapan Top 10に入ることを検証"""

    def test_ohtani_in_japan_top10(self):
        """大谷翔平がJapan Top 10に入る"""
        csv_path = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
        if not csv_path.exists():
            pytest.skip("CSV file not found")

        # CSVから全人物のJapan Scoreを取得
        persons = {}
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pid = row.get("person_id", "")
                if pid and pid not in persons:
                    japan_score = float(row.get("fame_score_japan", 0) or 0)
                    persons[pid] = {
                        "person_id": pid,
                        "person_name": row.get("person_name", ""),
                        "fame_score_japan": japan_score,
                    }

        # Japan Scoreでソート
        sorted_persons = sorted(persons.values(), key=lambda x: x["fame_score_japan"], reverse=True)
        top10 = sorted_persons[:10]
        top10_names = [p["person_name"] for p in top10]

        # 大谷翔平がTop 10に含まれることを確認
        assert "大谷翔平" in top10_names, f"大谷翔平 not in Top 10: {top10_names}"

    def test_ohtani_japan_score_higher_than_global(self):
        """大谷翔平のJapan ScoreがGlobal Scoreより高い"""
        csv_path = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
        if not csv_path.exists():
            pytest.skip("CSV file not found")

        ohtani_found = False
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("person_name") == "大谷翔平":
                    global_score = float(row.get("fame_score_v3", 0) or 0)
                    japan_score = float(row.get("fame_score_japan", 0) or 0)
                    ohtani_found = True

                    # Japan Score > Global Score
                    assert japan_score > global_score
                    # 約52%の上乗せ
                    boost_ratio = (japan_score / global_score - 1) * 100
                    assert 50 <= boost_ratio <= 55, f"Boost ratio: {boost_ratio}%"
                    break

        assert ohtani_found, "大谷翔平 not found in CSV"


class TestConfigLoading:
    """設定ファイル読み込みのテスト"""

    def test_load_config_from_file(self):
        """設定ファイルが正しく読み込まれる"""
        config = load_config()
        assert config.enabled is True
        assert config.base_alpha == 0.10
        assert "スポーツ" in config.category_weights
        assert config.category_weights["スポーツ"] == 0.40

    def test_config_disabled(self):
        """設定無効時はグローバルスコアがそのまま返る"""
        disabled_config = JapanBoostConfig(enabled=False)
        japan_score = calculate_japan_score(
            global_score=100.0,
            is_japanese=True,
            category="スポーツ",
            config=disabled_config,
        )
        assert japan_score == 100.0


class TestJapaneseCount:
    """日本人数のテスト"""

    def test_japanese_count_reasonable(self):
        """日本人の数が妥当な範囲内"""
        csv_path = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
        if not csv_path.exists():
            pytest.skip("CSV file not found")

        japanese_count = 0
        total_count = 0
        seen_pids = set()

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pid = row.get("person_id", "")
                if pid and pid not in seen_pids:
                    seen_pids.add(pid)
                    total_count += 1
                    if row.get("is_japanese") == "True":
                        japanese_count += 1

        # 日本人は全体の40-70%程度（日本向けDBなので多め）
        ratio = japanese_count / total_count if total_count > 0 else 0
        assert 0.40 <= ratio <= 0.70, f"Japanese ratio: {ratio:.1%}"
        # 3000人以上の日本人がいること
        assert japanese_count >= 3000, f"Japanese count: {japanese_count}"
