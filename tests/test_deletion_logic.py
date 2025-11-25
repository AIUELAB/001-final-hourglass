#!/usr/bin/env python3
"""
削除ロジックの自動テスト

世界的偉人の誤削除を防止するためのユニットテスト

Author: Final Hourglass Project
Date: 2025-10-08
Version: 1.0.0
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

    def test_no_nationality_based_deletion(self):
        """
        国籍による削除が行われていないことを確認
        """
        # Week 1-6復元版CSV（最新）
        csv_path = Path("final_hourglass_week1_6_final_20251008_075039.csv")

        if not csv_path.exists():
            pytest.skip("Week 1-6 CSV not found")

        df = pd.read_csv(csv_path, encoding="utf-8-sig")

        # 削除理由に「日本の偉人ではない」が含まれていないことを確認
        deleted = df[df["ステータス"] == "削除済み"]

        for _, row in deleted.iterrows():
            reason = str(row.get("削除理由", ""))
            assert "日本の偉人ではない" not in reason, f"国籍による削除が検出されました: {row['人物名']} - {reason}"

    def test_protected_persons_not_deleted(self):
        """
        世界的偉人が削除されていないことを確認
        """
        csv_path = Path("final_hourglass_week1_6_final_20251008_075039.csv")

        if not csv_path.exists():
            pytest.skip("Week 1-6 CSV not found")

        df = pd.read_csv(csv_path, encoding="utf-8-sig")

        # 保護対象の人物が削除されていないことを確認
        for person_name in self.PROTECTED_PERSONS:
            person_records = df[df["人物名"] == person_name]

            if len(person_records) > 0:
                # レコードが存在する場合、削除されていないことを確認
                assert (
                    person_records.iloc[0]["ステータス"] != "削除済み"
                ), f"世界的偉人が削除されています: {person_name}"

    def test_deletion_reason_validity(self):
        """
        削除理由が妥当であることを確認
        """
        csv_path = Path("final_hourglass_week1_6_final_20251008_075039.csv")

        if not csv_path.exists():
            pytest.skip("Week 1-6 CSV not found")

        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        deleted = df[df["ステータス"] == "削除済み"]

        # REQUIREMENTS.mdに基づく妥当な削除理由
        valid_reasons = [
            "架空キャラクター",
            "検証不可能",
            "歴史的実在性不明",
            "信頼できる情報源なし",
            "倫理的問題",
            "品質基準未達",
        ]

        # 不当な削除理由（国籍、分野、時代による排除）
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

            # 不当な削除理由が含まれていないことを確認
            for invalid in invalid_reasons:
                assert invalid not in reason, f"不当な削除理由が検出されました: {row['人物名']} - {reason}"

    def test_deletion_approval_process(self):
        """
        削除理由が必ず記録されていることを確認
        """
        csv_path = Path("final_hourglass_week1_6_final_20251008_075039.csv")

        if not csv_path.exists():
            pytest.skip("Week 1-6 CSV not found")

        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        deleted = df[df["ステータス"] == "削除済み"]

        # 削除レコードには必ず削除理由が記載されていること
        for _, row in deleted.iterrows():
            reason = row.get("削除理由", "")
            assert pd.notna(reason) and reason.strip() != "", f"削除理由が記載されていません: {row['人物名']}"

    def test_no_field_based_deletion(self):
        """
        分野による削除が行われていないことを確認
        """
        csv_path = Path("final_hourglass_week1_6_final_20251008_075039.csv")

        if not csv_path.exists():
            pytest.skip("Week 1-6 CSV not found")

        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        deleted = df[df["ステータス"] == "削除済み"]

        # 分野による削除が行われていないことを確認
        field_based_reasons = ["スポーツ選手", "芸能人", "実業家", "政治家", "音楽家"]

        for _, row in deleted.iterrows():
            reason = str(row.get("削除理由", ""))
            for field_reason in field_based_reasons:
                assert field_reason not in reason, f"分野による削除が検出されました: {row['人物名']} - {reason}"


def test_requirements_compliance():
    """
    REQUIREMENTS.mdの存在確認
    """
    requirements_path = Path("REQUIREMENTS.md")
    assert requirements_path.exists(), "REQUIREMENTS.mdが存在しません - 要件定義が明確化されていません"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
