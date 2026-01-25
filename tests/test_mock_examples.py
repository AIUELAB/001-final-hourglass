#!/usr/bin/env python3
"""
Phase 3: モックフィクスチャ使用例テスト

このファイルは、conftest.pyで定義されたモックフィクスチャの
使用方法を示すサンプルテストです。

CI環境で実行可能なunitテストとして設計されています。
"""

import pytest


@pytest.mark.unit
class TestMockMasterEpisodes:
    """mock_master_episodes_df フィクスチャの使用例"""

    def test_episode_structure(self, mock_master_episodes_df):
        """エピソードデータの構造が正しいことを確認"""
        df = mock_master_episodes_df

        # 必須カラムの存在確認
        required_columns = [
            "episode_id",
            "person_id",
            "person_name",
            "age",
            "episode_text",
            "person_type",
            "composite_score",
        ]
        for col in required_columns:
            assert col in df.columns, f"必須カラム {col} が存在しない"

    def test_person_types(self, mock_master_episodes_df):
        """person_type が正しい値を持つことを確認"""
        df = mock_master_episodes_df

        valid_types = {"REAL", "FICTIONAL"}
        actual_types = set(df["person_type"].unique())

        assert actual_types.issubset(valid_types), f"不正なperson_type: {actual_types - valid_types}"

    def test_fictional_has_work_title(self, mock_master_episodes_df):
        """FICTIONALキャラにはwork_titleが設定されている"""
        df = mock_master_episodes_df

        fictional = df[df["person_type"] == "FICTIONAL"]
        for _, row in fictional.iterrows():
            assert row["work_title"], f"FICTIONALキャラ {row['person_name']} にwork_titleがない"

    def test_score_ranges(self, mock_master_episodes_df):
        """スコアが妥当な範囲内にあることを確認"""
        df = mock_master_episodes_df

        assert df["composite_score"].min() >= 0, "composite_scoreが負の値"
        assert df["episode_importance_score"].max() <= 10, "episode_importance_scoreが10を超過"

    def test_age_values(self, mock_master_episodes_df):
        """年齢が妥当な範囲内にあることを確認"""
        df = mock_master_episodes_df

        assert df["age"].min() >= 0, "年齢が負の値"
        assert df["age"].max() <= 120, "年齢が120を超過"


@pytest.mark.unit
class TestMockCsvPath:
    """mock_csv_path フィクスチャの使用例"""

    def test_csv_file_exists(self, mock_csv_path):
        """CSVファイルが作成されていることを確認"""
        assert mock_csv_path.exists(), "CSVファイルが存在しない"
        assert mock_csv_path.suffix == ".csv", "拡張子が.csvでない"

    def test_csv_readable(self, mock_csv_path):
        """CSVファイルが読み込み可能なことを確認"""
        import pandas as pd

        df = pd.read_csv(mock_csv_path, encoding="utf-8-sig")
        assert len(df) > 0, "CSVが空"
        assert "person_name" in df.columns, "person_nameカラムがない"


@pytest.mark.unit
class TestMockFactChecker:
    """mock_fact_checker フィクスチャの使用例"""

    def test_check_fact_returns_verified(self, mock_fact_checker):
        """check_factがverified結果を返すことを確認"""
        result = mock_fact_checker.check_fact("織田信長は桶狭間で勝利した")

        assert result["is_verified"] is True
        assert result["confidence"] >= 0.9
        assert len(result["sources"]) > 0

    def test_batch_check_returns_list(self, mock_fact_checker):
        """batch_checkがリストを返すことを確認"""
        result = mock_fact_checker.batch_check(["EP-001", "EP-002"])

        assert isinstance(result, list)
        assert len(result) == 2
        assert all("is_verified" in item for item in result)


@pytest.mark.unit
class TestMockExternalApi:
    """mock_external_api フィクスチャの使用例"""

    def test_wikipedia_pv(self, mock_external_api):
        """Wikipedia PV取得のモックが動作することを確認"""
        pv = mock_external_api.get_wikipedia_pv("織田信長")
        assert pv > 0, "Wikipedia PVが0以下"

    def test_wikidata_info(self, mock_external_api):
        """Wikidata情報取得のモックが動作することを確認"""
        info = mock_external_api.get_wikidata_info("織田信長")

        assert "sitelinks_count" in info
        assert "multi_lang_pv" in info
        assert info["sitelinks_count"] > 0


@pytest.mark.unit
class TestEpisodeValidation:
    """エピソード検証ロジックのモックテスト"""

    def test_episode_text_starts_with_age_phrase(self, mock_master_episodes_df):
        """エピソードテキストが「あなたと同じX歳のとき」で始まることを確認"""
        df = mock_master_episodes_df

        for _, row in df.iterrows():
            text = row["episode_text"]
            age = row["age"]
            expected_prefix = f"あなたと同じ{age}歳のとき"
            assert text.startswith(expected_prefix), f"エピソードが正しい形式で始まっていない: {text[:50]}..."

    def test_no_duplicate_episode_ids(self, mock_master_episodes_df):
        """episode_idに重複がないことを確認"""
        df = mock_master_episodes_df

        duplicates = df[df.duplicated(subset=["episode_id"], keep=False)]
        assert len(duplicates) == 0, f"重複episode_id: {duplicates['episode_id'].tolist()}"

    def test_birth_death_year_consistency(self, mock_master_episodes_df):
        """birth_year < death_year であることを確認（REALのみ）"""
        df = mock_master_episodes_df

        real_persons = df[df["person_type"] == "REAL"]
        for _, row in real_persons.iterrows():
            birth = row.get("birth_year")
            death = row.get("death_year")

            if birth and death:
                assert birth < death, f"{row['person_name']}: birth_year({birth}) >= death_year({death})"
