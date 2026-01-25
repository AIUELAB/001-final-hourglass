#!/usr/bin/env python3
"""
削除ロジックの自動テスト

世界的偉人の誤削除を防止するためのユニットテスト

Author: Final Hourglass Project
Date: 2025-10-08
Version: 2.0.0
"""

from pathlib import Path

import pandas as pd
import pytest


class TestDeletionLogic:
    """
    削除ロジックの妥当性テスト
    """

    # 絶対に削除してはならない世界的偉人
    PROTECTED_PERSONS = [
        "アルベルト・アインシュタイン",
        "マリー・キュリー",
        "スティーブ・ジョブズ",
        "イーロン・マスク",
        "ジェフ・ベゾス",
        "ビル・ゲイツ",
        "マーク・ザッカーバーグ",
        "レオナルド・ダ・ヴィンチ",
        "アイザック・ニュートン",
        "ガリレオ・ガリレイ",
        "マーティン・ルーサー・キング・ジュニア",
        "ネルソン・マンデラ",
        "マハトマ・ガンジー",
    ]

    # ============================================
    # モック版テスト（CI実行可能）
    # ============================================

    @pytest.mark.unit
    def test_protected_persons_not_deleted_mock(self, mock_deletion_df):
        """
        [モック版] 世界的偉人が削除されていないことを確認
        """
        df = mock_deletion_df

        # 保護対象の人物が削除されていないことを確認
        for person_name in self.PROTECTED_PERSONS:
            person_records = df[df["人物名"] == person_name]

            if len(person_records) > 0:
                assert (
                    person_records.iloc[0]["ステータス"] != "削除済み"
                ), f"世界的偉人が削除されています: {person_name}"

    @pytest.mark.unit
    def test_deletion_reason_exists_mock(self, mock_deletion_df):
        """
        [モック版] 削除レコードには必ず削除理由が記載されていることを確認
        """
        df = mock_deletion_df
        deleted = df[df["ステータス"] == "削除済み"]

        for _, row in deleted.iterrows():
            reason = row.get("削除理由", "")
            assert pd.notna(reason) and reason.strip() != "", f"削除理由が記載されていません: {row['人物名']}"

    @pytest.mark.unit
    def test_no_invalid_deletion_reasons_mock(self, mock_deletion_df):
        """
        [モック版] 不当な削除理由が使用されていないことを確認
        """
        df = mock_deletion_df
        deleted = df[df["ステータス"] == "削除済み"]

        invalid_reasons = [
            "日本の偉人ではない",
            "外国人",
            "日本人ではない",
            "スポーツ選手",
            "芸能人",
            "現代人",
            "古すぎる",
        ]

        for _, row in deleted.iterrows():
            reason = str(row.get("削除理由", ""))
            for invalid in invalid_reasons:
                assert invalid not in reason, f"不当な削除理由が検出されました: {row['人物名']} - {reason}"

    # ============================================
    # 統合版テスト（ローカル実行のみ）
    # ============================================

    @pytest.mark.integration
    def test_no_nationality_based_deletion(self):
        """
        [統合版] 国籍による削除が行われていないことを確認
        """
        csv_path = Path("final_hourglass_week1_6_final_20251008_075039.csv")

        if not csv_path.exists():
            pytest.skip("Week 1-6 CSV not found")

        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        deleted = df[df["ステータス"] == "削除済み"]

        for _, row in deleted.iterrows():
            reason = str(row.get("削除理由", ""))
            assert "日本の偉人ではない" not in reason, f"国籍による削除が検出されました: {row['人物名']} - {reason}"

    @pytest.mark.integration
    def test_protected_persons_not_deleted(self):
        """
        [統合版] 世界的偉人が削除されていないことを確認
        """
        csv_path = Path("final_hourglass_week1_6_final_20251008_075039.csv")

        if not csv_path.exists():
            pytest.skip("Week 1-6 CSV not found")

        df = pd.read_csv(csv_path, encoding="utf-8-sig")

        for person_name in self.PROTECTED_PERSONS:
            person_records = df[df["人物名"] == person_name]

            if len(person_records) > 0:
                assert (
                    person_records.iloc[0]["ステータス"] != "削除済み"
                ), f"世界的偉人が削除されています: {person_name}"

    @pytest.mark.integration
    def test_deletion_reason_validity(self):
        """
        [統合版] 削除理由が妥当であることを確認
        """
        csv_path = Path("final_hourglass_week1_6_final_20251008_075039.csv")

        if not csv_path.exists():
            pytest.skip("Week 1-6 CSV not found")

        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        deleted = df[df["ステータス"] == "削除済み"]

        invalid_reasons = [
            "日本の偉人ではない",
            "外国人",
            "日本人ではない",
            "スポーツ選手",
            "芸能人",
            "現代人",
            "古すぎる",
        ]

        for _, row in deleted.iterrows():
            reason = str(row.get("削除理由", ""))
            for invalid in invalid_reasons:
                assert invalid not in reason, f"不当な削除理由が検出されました: {row['人物名']} - {reason}"

    @pytest.mark.integration
    def test_deletion_approval_process(self):
        """
        [統合版] 削除理由が必ず記録されていることを確認
        """
        csv_path = Path("final_hourglass_week1_6_final_20251008_075039.csv")

        if not csv_path.exists():
            pytest.skip("Week 1-6 CSV not found")

        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        deleted = df[df["ステータス"] == "削除済み"]

        for _, row in deleted.iterrows():
            reason = row.get("削除理由", "")
            assert pd.notna(reason) and reason.strip() != "", f"削除理由が記載されていません: {row['人物名']}"

    @pytest.mark.integration
    def test_no_field_based_deletion(self):
        """
        [統合版] 分野による削除が行われていないことを確認
        """
        csv_path = Path("final_hourglass_week1_6_final_20251008_075039.csv")

        if not csv_path.exists():
            pytest.skip("Week 1-6 CSV not found")

        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        deleted = df[df["ステータス"] == "削除済み"]

        field_based_reasons = ["スポーツ選手", "芸能人", "実業家", "政治家", "音楽家"]

        for _, row in deleted.iterrows():
            reason = str(row.get("削除理由", ""))
            for field_reason in field_based_reasons:
                assert field_reason not in reason, f"分野による削除が検出されました: {row['人物名']} - {reason}"


@pytest.mark.integration
def test_requirements_compliance():
    """
    [統合版] REQUIREMENTS.mdの存在確認
    """
    requirements_path = Path("REQUIREMENTS.md")
    assert requirements_path.exists(), "REQUIREMENTS.mdが存在しません - 要件定義が明確化されていません"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
