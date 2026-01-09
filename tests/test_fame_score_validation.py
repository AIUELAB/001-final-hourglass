"""
スコア検証テスト

異常値（NaN, inf, 負数, 上限超過）の検出と
スケール変換のバグ防止テスト
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from validate_fame_score import validate_fame_scores, FAME_SCORE_MAX
from validate_all_scores import validate_all_scores, SCORE_SPECS


class TestFameScoreValidation:
    """有名人度スコア検証テスト"""

    def test_all_scores_within_range(self):
        """全スコアが0-1000の範囲内であること"""
        result = validate_fame_scores()

        # 範囲外エラーがないこと
        assert result["valid"], f"検証エラー: {result['errors'][:5]}"

        # 統計値が正常範囲
        stats = result["stats"]
        assert (
            stats["fame_score_v3_max"] <= FAME_SCORE_MAX
        ), f"fame_score_v3の最大値が上限超過: {stats['fame_score_v3_max']}"
        assert stats["fame_score_v3_min"] >= 0, f"fame_score_v3の最小値が負数: {stats['fame_score_v3_min']}"

    def test_no_nan_or_inf(self):
        """NaN/infが含まれていないこと"""
        result = validate_fame_scores()
        stats = result["stats"]

        assert len(stats["nan_inf"]) == 0, f"NaN/infが検出されました: {stats['nan_inf'][:5]}"

    def test_no_negative_scores(self):
        """負のスコアが含まれていないこと"""
        result = validate_fame_scores()
        stats = result["stats"]

        assert len(stats["negative"]) == 0, f"負のスコアが検出されました: {stats['negative'][:5]}"

    def test_specific_person_ken(self):
        """PF632FA6 (ken) のスコアが正常範囲であること（回帰テスト）"""
        import csv

        csv_path = Path(__file__).parent.parent / "preserved/data/MASTER_EPISODES_CURRENT.csv"

        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("person_id") == "PF632FA6":
                    fs_v3 = float(row.get("fame_score_v3", "0"))

                    # 正常範囲チェック（713.34 付近を想定）
                    assert 0 <= fs_v3 <= 1000, f"ken (PF632FA6) のfame_score_v3が範囲外: {fs_v3}"

                    # 10倍バグの回帰チェック
                    assert fs_v3 < 1000, f"ken (PF632FA6) のスコアが異常に高い（10倍バグ?）: {fs_v3}"

                    break


class TestScaleConversionBugPrevention:
    """スケール変換バグ防止テスト"""

    def test_fame_score_v3_is_already_1000_scale(self):
        """fame_score_v3は既に0-1000スケールであること（10倍不要）"""
        result = validate_fame_scores()
        stats = result["stats"]

        # 最大値が1000以下であれば0-1000スケール
        assert stats["fame_score_v3_max"] <= 1000, (
            f"fame_score_v3が1000を超えています: {stats['fame_score_v3_max']}"
            "（10倍変換が不要なのに適用された可能性）"
        )

        # 最大値が100未満だと0-100スケールの可能性
        if stats["fame_score_v3_max"] < 100:
            pytest.skip("fame_score_v3の最大値が100未満（スケール要確認）")

    def test_episode_fame_score_scale(self):
        """episode_fame_scoreのスケールが正常であること"""
        result = validate_fame_scores()
        stats = result["stats"]

        # episode_fame_scoreは通常0-500程度
        # 1000を超えていたら10倍バグの可能性
        assert (
            stats["episode_fame_score_max"] <= 1000
        ), f"episode_fame_scoreが1000を超えています: {stats['episode_fame_score_max']}"


class TestAllScoresValidation:
    """全スコアフィールド検証テスト"""

    def test_all_scores_within_defined_ranges(self):
        """全スコアが定義されたスケール範囲内であること"""
        result = validate_all_scores()

        # エラーがないこと
        assert result["valid"], f"検証エラー: {result['errors'][:5]}"

    def test_score_specs_cover_major_fields(self):
        """主要スコアフィールドが定義されていること"""
        spec_names = {spec.name for spec in SCORE_SPECS}

        required_fields = [
            "fame_score_v3",
            "episode_fame_score",
            "composite_score",
            "fame_tier",
        ]

        for field in required_fields:
            assert field in spec_names, f"必須フィールド未定義: {field}"

    def test_no_scale_mixing_errors(self):
        """スケール混在エラーがないこと（0-10と0-1000の混同など）"""
        result = validate_all_scores()
        stats = result["stats"]

        # 0-10スケールのフィールドが100を超えていないこと
        # Note: composite_scoreは0-1000スケール（8軸合計×重み）なので除外
        scale_10_fields = [
            # "composite_score",  # 0-1000スケール
            # "composite_score_5axis",  # 0-1000スケール
            "llm_memorability_score",
            "llm_empathy_score",
        ]

        for field in scale_10_fields:
            if stats[field]["count"] > 0:
                max_val = stats[field]["max"]
                assert max_val <= 15, f"{field}が0-10スケールを大きく超過: {max_val}" "（10倍バグの可能性）"


class TestDashboardScaleConsistency:
    """ダッシュボードスケール整合性テスト"""

    def test_dashboard_no_incorrect_multipliers(self):
        """ダッシュボードに不正な乗算がないこと（v11）"""
        # Phase 27: v10 → v11 移行
        dashboard_path = Path(__file__).parent.parent / "preserved/episode_database_dashboard_v11.html"

        with open(dashboard_path, "r", encoding="utf-8") as f:
            content = f.read()

        # fame_score * 10 パターンが存在しないこと
        assert "fame_score * 10" not in content, "fame_score * 10 パターンが残存"
        assert "fame_score *10" not in content, "fame_score *10 パターンが残存"

        # episode_fame_score * 10 パターンが存在しないこと
        assert "episode_fame_score * 10" not in content, "episode_fame_score * 10 パターンが残存"


class TestWikidataDisambiguation:
    """Wikidata同名曖昧性テスト"""

    @pytest.mark.xfail(reason="データ品質課題: Eve等の高リスク短名が存在")
    def test_no_high_risk_short_names(self):
        """高リスク短名（ラテン文字≤5文字 + sitelinks≥100）がないこと"""
        from validate_wikidata_disambiguation import detect_suspicious_persons

        suspicious = detect_suspicious_persons()
        high_risk = [s for s in suspicious if s.risk_level == "high"]

        assert len(high_risk) == 0, (
            f"高リスク短名が検出されました: "
            f"{[(s.person_id, s.person_name, s.sitelinks_count) for s in high_risk[:5]]}"
        )

    def test_ken_not_using_kenya_entity(self):
        """ken (PF632FA6) がケニア(sitelinks=331)を使用していないこと（回帰テスト）"""
        import csv

        csv_path = Path(__file__).parent.parent / "preserved/data/MASTER_EPISODES_CURRENT.csv"

        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("person_id") == "PF632FA6":
                    sitelinks = float(row.get("sitelinks_count", "0") or "0")
                    # ケニアのsitelinks(331)ではないこと
                    assert sitelinks < 50, (
                        f"ken (PF632FA6) のsitelinkが異常に高い: {sitelinks} "
                        "(ケニアのエンティティを使用している可能性)"
                    )
                    break

    def test_one_not_using_number_entity(self):
        """ONE (PBC21E64) が数字1(sitelinks≈214)を使用していないこと（回帰テスト）"""
        import csv

        csv_path = Path(__file__).parent.parent / "preserved/data/MASTER_EPISODES_CURRENT.csv"

        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("person_id") == "PBC21E64":
                    sitelinks = float(row.get("sitelinks_count", "0") or "0")
                    # 数字1のsitelinks(214)ではないこと
                    assert sitelinks < 50, (
                        f"ONE (PBC21E64) のsitelinkが異常に高い: {sitelinks} "
                        "(数字1のエンティティを使用している可能性)"
                    )
                    break

    def test_ken_score_below_justin_bieber(self):
        """ken (PF632FA6) のスコアがジャスティン・ビーバーより低いこと"""
        import csv

        csv_path = Path(__file__).parent.parent / "preserved/data/MASTER_EPISODES_CURRENT.csv"

        ken_score = None
        jb_score = None

        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pid = row.get("person_id", "")
                name = row.get("person_name", "")
                score = float(row.get("fame_score_v3", "0") or "0")

                if pid == "PF632FA6":
                    ken_score = score
                elif "ジャスティン" in name and "ビーバー" in name:
                    jb_score = score

                if ken_score is not None and jb_score is not None:
                    break

        assert ken_score is not None, "ken (PF632FA6) が見つかりません"
        assert jb_score is not None, "ジャスティン・ビーバーが見つかりません"
        assert ken_score < jb_score, f"ken ({ken_score}) がジャスティン・ビーバー ({jb_score}) より高い"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
