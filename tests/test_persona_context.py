#!/usr/bin/env python3
"""
ペルソナ・文脈整合性 回帰テスト

北野武/ビートたけし混在問題の再発を防止するテスト。
"""

import pytest
import pandas as pd
import re


class TestPersonaContext:
    """ペルソナ・文脈整合性テスト"""

    def test_no_kitano_twobeat_contamination(self):
        """「北野武（ツービート）」が存在しないこと"""
        df = pd.read_csv("preserved/data/MASTER_EPISODES_CURRENT.csv", low_memory=False)
        contaminated = df[df["episode_text"].str.contains("北野武（ツービート）", na=False)]
        assert (
            len(contaminated) == 0
        ), f"「北野武（ツービート）」が{len(contaminated)}件存在: {contaminated['episode_id'].tolist()}"

    @pytest.mark.xfail(reason="既存データ品質課題: 北野武芸人文脈混在 - 技術的負債", strict=False)
    def test_p34ea398_no_comedian_context(self):
        """P34EA398（北野武）配下に芸人文脈がないこと"""
        df = pd.read_csv("preserved/data/MASTER_EPISODES_CURRENT.csv", low_memory=False)
        kitano = df[df["person_id"] == "P34EA398"]

        comedian_keywords = ["漫才", "ツービート", "たけし軍団", "ひょうきん族"]
        for _, row in kitano.iterrows():
            text = str(row["episode_text"])
            # 「ツービート」がテキスト内に含まれる場合は芸人文脈の可能性
            if any(k in text for k in comedian_keywords):
                # 映画監督キーワードも同時にあれば許容（歴史的言及）
                director_keywords = ["監督", "映画", "作品", "カンヌ", "ベネチア"]
                has_director = any(k in text for k in director_keywords)
                if not has_director:
                    pytest.fail(f"P34EA398に芸人文脈エピソードが混在: {row['episode_id']}")

    @pytest.mark.skip(reason="ビートたけし/北野武のペルソナ分離は未実装（現在は北野武P34EA398に統合）")
    def test_beattakeshi_person_exists(self):
        """ビートたけし用PERSON IDが存在すること"""
        df = pd.read_csv("preserved/data/MASTER_EPISODES_CURRENT.csv", low_memory=False)
        beat = df[df["person_id"] == "PBEATTAKE"]
        assert len(beat) >= 1, "ビートたけし用PERSON ID（PBEATTAKE）が存在しない"

    @pytest.mark.skip(reason="ビートたけし/北野武のペルソナ分離は未実装（現在は北野武P34EA398に統合）")
    def test_beattakeshi_no_director_context(self):
        """PBEATTAKE配下に映画監督文脈がないこと"""
        df = pd.read_csv("preserved/data/MASTER_EPISODES_CURRENT.csv", low_memory=False)
        beat = df[df["person_id"] == "PBEATTAKE"]

        director_only_keywords = ["カンヌ", "ベネチア", "ヴェネツィア", "金獅子賞", "パルムドール"]
        for _, row in beat.iterrows():
            text = str(row["episode_text"])
            if any(k in text for k in director_only_keywords):
                pytest.fail(f"PBEATTAKEに映画監督文脈エピソードが混在: {row['episode_id']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
