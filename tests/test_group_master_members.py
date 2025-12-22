#!/usr/bin/env python3
"""
tests/test_group_master_members.py - group_master/members.py ユニットテスト
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from group_master.members import (
    GROUP_MEMBER_MAP,
    get_group_info,
    get_group_members,
    is_solo_artist,
    is_group_entity,
    get_statistics,
)


class TestGroupMemberMap:
    """GROUP_MEMBER_MAPデータ構造テスト"""

    def test_group_member_map_exists(self):
        """GROUP_MEMBER_MAPが存在する"""
        assert isinstance(GROUP_MEMBER_MAP, dict)
        assert len(GROUP_MEMBER_MAP) > 0

    def test_mrchildren_members(self):
        """Mr.Childrenメンバー登録確認"""
        assert GROUP_MEMBER_MAP.get("桜井和寿") == "Mr.Children"
        assert GROUP_MEMBER_MAP.get("田原健一") == "Mr.Children"
        assert GROUP_MEMBER_MAP.get("中川敬輔") == "Mr.Children"
        assert GROUP_MEMBER_MAP.get("鈴木英哉") == "Mr.Children"

    def test_bz_members(self):
        """B'zメンバー登録確認"""
        assert GROUP_MEMBER_MAP.get("稲葉浩志") == "B'z"
        assert GROUP_MEMBER_MAP.get("松本孝弘") == "B'z"

    def test_downtown_members(self):
        """ダウンタウンメンバー登録確認"""
        assert GROUP_MEMBER_MAP.get("松本人志") == "ダウンタウン"
        assert GROUP_MEMBER_MAP.get("浜田雅功") == "ダウンタウン"

    def test_arashi_members(self):
        """嵐メンバー登録確認"""
        assert GROUP_MEMBER_MAP.get("大野智") == "嵐"
        assert GROUP_MEMBER_MAP.get("櫻井翔") == "嵐"
        assert GROUP_MEMBER_MAP.get("相葉雅紀") == "嵐"
        assert GROUP_MEMBER_MAP.get("二宮和也") == "嵐"
        assert GROUP_MEMBER_MAP.get("松本潤") == "嵐"

    def test_smap_members(self):
        """SMAPメンバー登録確認"""
        assert GROUP_MEMBER_MAP.get("中居正広") == "SMAP"
        assert GROUP_MEMBER_MAP.get("木村拓哉") == "SMAP"

    def test_bts_members(self):
        """BTSメンバー登録確認"""
        assert GROUP_MEMBER_MAP.get("RM") == "BTS"
        assert GROUP_MEMBER_MAP.get("Jin") == "BTS"
        assert GROUP_MEMBER_MAP.get("ジョングク") == "BTS"

    def test_hololive_members(self):
        """ホロライブメンバー登録確認"""
        assert GROUP_MEMBER_MAP.get("星街すいせい") == "ホロライブ"
        assert GROUP_MEMBER_MAP.get("兎田ぺこら") == "ホロライブ"

    def test_unregistered_person(self):
        """未登録人物はNone"""
        assert GROUP_MEMBER_MAP.get("未登録の人物") is None


class TestGetGroupInfo:
    """get_group_info関数テスト"""

    def test_registered_member(self):
        """登録済みメンバー"""
        group, is_member = get_group_info("桜井和寿")
        assert group == "Mr.Children"
        assert is_member is True

    def test_fictional_character(self):
        """架空キャラクターは対象外"""
        group, is_member = get_group_info("アニメキャラ", person_type="FICTIONAL")
        assert group is None
        assert is_member is False

    def test_fictional_uppercase(self):
        """FICTIONAL（大文字）"""
        group, is_member = get_group_info("テスト", person_type="fictional")
        assert group is None
        assert is_member is False

    def test_unknown_person(self):
        """未知の人物"""
        group, is_member = get_group_info("未知の人物")
        assert group is None
        assert is_member is None

    def test_solo_artist(self):
        """ソロアーティスト"""
        group, is_member = get_group_info("宇多田ヒカル")
        assert group is None
        assert is_member is False

    def test_group_entity(self):
        """グループ本体"""
        group, is_member = get_group_info("嵐")
        assert group is None
        assert is_member is None

    def test_comedy_duo_member(self):
        """お笑いコンビメンバー"""
        group, is_member = get_group_info("岡村隆史")
        assert group == "ナインティナイン"
        assert is_member is True

    def test_youtube_group_member(self):
        """YouTubeグループメンバー"""
        group, is_member = get_group_info("伊沢拓司")
        assert group == "QuizKnock"
        assert is_member is True


class TestGetGroupMembers:
    """get_group_members関数テスト"""

    def test_mrchildren_members(self):
        """Mr.Childrenメンバー取得"""
        members = get_group_members("Mr.Children")
        assert "桜井和寿" in members
        assert "田原健一" in members
        assert "中川敬輔" in members
        assert "鈴木英哉" in members
        assert len(members) == 4

    def test_bz_members(self):
        """B'zメンバー取得"""
        members = get_group_members("B'z")
        assert "稲葉浩志" in members
        assert "松本孝弘" in members
        assert len(members) == 2

    def test_downtown_members(self):
        """ダウンタウンメンバー取得"""
        members = get_group_members("ダウンタウン")
        assert "松本人志" in members
        assert "浜田雅功" in members
        assert len(members) == 2

    def test_arashi_members(self):
        """嵐メンバー取得"""
        members = get_group_members("嵐")
        assert len(members) == 5
        assert "大野智" in members

    def test_nonexistent_group(self):
        """存在しないグループ"""
        members = get_group_members("存在しないグループ")
        assert members == []

    def test_yoasobi_members(self):
        """YOASOBIメンバー取得（本名含む）"""
        members = get_group_members("YOASOBI")
        assert "Ayase" in members
        assert "ikura" in members
        assert "幾田りら" in members  # ikuraの本名
        assert len(members) == 3

    def test_snowman_members(self):
        """Snow Manメンバー取得"""
        members = get_group_members("Snow Man")
        assert len(members) == 9
        assert "目黒蓮" in members
        assert "ラウール" in members


class TestIsSoloArtist:
    """is_solo_artist関数テスト"""

    def test_utada_hikaru(self):
        """宇多田ヒカルはソロ"""
        assert is_solo_artist("宇多田ヒカル") is True

    def test_yonezu_kenshi(self):
        """米津玄師はソロ"""
        assert is_solo_artist("米津玄師") is True

    def test_ado(self):
        """Adoはソロ"""
        assert is_solo_artist("Ado") is True

    def test_akashiya_sanma(self):
        """明石家さんまはソロ"""
        assert is_solo_artist("明石家さんま") is True

    def test_tamori(self):
        """タモリはソロ"""
        assert is_solo_artist("タモリ") is True

    def test_beat_takeshi(self):
        """ビートたけしはソロ"""
        assert is_solo_artist("ビートたけし") is True

    def test_misora_hibari(self):
        """美空ひばりはソロ"""
        assert is_solo_artist("美空ひばり") is True

    def test_group_member_is_not_solo(self):
        """グループメンバーはソロではない"""
        assert is_solo_artist("桜井和寿") is False

    def test_unknown_person_is_not_solo(self):
        """未知の人物はソロではない"""
        assert is_solo_artist("未知の人物") is False


class TestIsGroupEntity:
    """is_group_entity関数テスト"""

    def test_arashi_is_group(self):
        """嵐はグループ本体"""
        assert is_group_entity("嵐") is True

    def test_smap_is_group(self):
        """SMAPはグループ本体"""
        assert is_group_entity("SMAP") is True

    def test_downtown_is_group(self):
        """ダウンタウンはグループ本体"""
        assert is_group_entity("ダウンタウン") is True

    def test_bts_is_group(self):
        """BTSはグループ本体"""
        assert is_group_entity("BTS") is True

    def test_hololive_is_group(self):
        """ホロライブはグループ本体"""
        assert is_group_entity("ホロライブ") is True

    def test_nijisanji_is_group(self):
        """にじさんじはグループ本体"""
        assert is_group_entity("にじさんじ") is True

    def test_beatles_is_group(self):
        """ビートルズはグループ本体"""
        assert is_group_entity("ビートルズ") is True

    def test_member_is_not_group_entity(self):
        """メンバーはグループ本体ではない"""
        assert is_group_entity("桜井和寿") is False

    def test_solo_artist_is_not_group_entity(self):
        """ソロアーティストはグループ本体ではない"""
        assert is_group_entity("宇多田ヒカル") is False


class TestGetStatistics:
    """get_statistics関数テスト"""

    def test_statistics_structure(self):
        """統計情報の構造"""
        stats = get_statistics()
        assert isinstance(stats, dict)
        assert "total_members" in stats
        assert "unique_groups" in stats
        assert "group_entities" in stats
        assert "solo_artists" in stats

    def test_total_members_positive(self):
        """総メンバー数は正の値"""
        stats = get_statistics()
        assert stats["total_members"] > 0
        assert stats["total_members"] == len(GROUP_MEMBER_MAP)

    def test_unique_groups_positive(self):
        """ユニークグループ数は正の値"""
        stats = get_statistics()
        assert stats["unique_groups"] > 0
        assert stats["unique_groups"] <= stats["total_members"]

    def test_group_entities_positive(self):
        """グループエンティティ数は正の値"""
        stats = get_statistics()
        assert stats["group_entities"] > 0

    def test_solo_artists_positive(self):
        """ソロアーティスト数は正の値"""
        stats = get_statistics()
        assert stats["solo_artists"] > 0


class TestEdgeCases:
    """エッジケーステスト"""

    def test_empty_string(self):
        """空文字列"""
        group, is_member = get_group_info("")
        assert group is None
        assert is_member is None

    def test_variant_names(self):
        """表記ゆれ対応"""
        # L'Arc~en~Cielの表記ゆれ
        assert GROUP_MEMBER_MAP.get("hyde") == "L'Arc~en~Ciel"
        assert GROUP_MEMBER_MAP.get("HYDE") == "L'Arc~en~Ciel"

    def test_alias_names(self):
        """別名対応"""
        # ikuraと幾田りら
        assert GROUP_MEMBER_MAP.get("ikura") == "YOASOBI"
        assert GROUP_MEMBER_MAP.get("幾田りら") == "YOASOBI"

    def test_english_names(self):
        """英語名対応"""
        assert GROUP_MEMBER_MAP.get("John Lennon") == "The Beatles"
        assert GROUP_MEMBER_MAP.get("Paul McCartney") == "The Beatles"

    def test_japanese_translated_names(self):
        """日本語訳名対応"""
        assert GROUP_MEMBER_MAP.get("ジョン・レノン") == "ビートルズ"
        assert GROUP_MEMBER_MAP.get("ポール・マッカートニー") == "ビートルズ"


class TestKpopMembers:
    """K-POPメンバーテスト"""

    def test_blackpink_members(self):
        """BLACKPINKメンバー"""
        members = get_group_members("BLACKPINK")
        assert "Jisoo" in members or "ジス" in members
        assert "Jennie" in members or "ジェニー" in members
        assert "Rosé" in members or "ロゼ" in members
        assert "Lisa" in members or "リサ" in members

    def test_twice_members(self):
        """TWICEメンバー"""
        members = get_group_members("TWICE")
        assert "サナ" in members
        assert "モモ" in members


class TestVTuberMembers:
    """VTuberメンバーテスト"""

    def test_nijisanji_members(self):
        """にじさんじメンバー"""
        members = get_group_members("にじさんじ")
        assert "葛葉" in members
        assert "月ノ美兎" in members

    def test_hololive_members(self):
        """ホロライブメンバー"""
        members = get_group_members("ホロライブ")
        assert "星街すいせい" in members
        assert "宝鐘マリン" in members


class TestYouTubeGroupMembers:
    """YouTubeグループメンバーテスト"""

    def test_tokaiair_members(self):
        """東海オンエアメンバー"""
        members = get_group_members("東海オンエア")
        assert "てつや" in members
        assert "しばゆー" in members

    def test_quizknock_members(self):
        """QuizKnockメンバー"""
        members = get_group_members("QuizKnock")
        assert "伊沢拓司" in members
        assert "ふくらP" in members
