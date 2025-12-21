#!/usr/bin/env python3
"""
人物名正規化スクリプト

機能:
1. 肩書/所属/関係性の混入パターンを検出
2. 高信頼度のものは自動修正
3. 低信頼度のものは保留してレビュー用レポート出力

使用方法:
    # ドライラン（検出のみ）
    python scripts/normalize_person_names.py --dry-run

    # 自動修正実行（信頼度≥0.85）
    python scripts/normalize_person_names.py --execute

    # LLM検証付き
    python scripts/normalize_person_names.py --use-llm --execute

    # 特定パターンのみ処理
    python scripts/normalize_person_names.py --pattern TITLE_ROLE --dry-run

環境変数:
    ANTHROPIC_API_KEY: LLM検証を使用する場合に必要
"""

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.csv_path_resolver import get_master_csv_path, get_reports_dir

# Anthropic API（オプション）
try:
    import anthropic

    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

# ========================================
# 定数定義（統一パス解決を使用）
# ========================================

CSV_PATH = get_master_csv_path()
REPORTS_DIR = get_reports_dir()

# 西洋人名のファーストネーム（誤分割防止）
WESTERN_FIRST_NAMES = {
    # アルファベット順（一般的なカタカナ表記）
    "アーサー",
    "アイザック",
    "アガサ",
    "アダム",
    "アドルフ",
    "アラン",
    "アルバート",
    "アルフレッド",
    "アレクサンダー",
    "アンソニー",
    "アンディ",
    "アンドリュー",
    "イーロン",
    "ウィリアム",
    "エディ",
    "エドガー",
    "エドワード",
    "エマ",
    "エミリー",
    "エリザベス",
    "エリック",
    "エルトン",
    "オードリー",
    "オスカー",
    "カール",
    "キース",
    "クリス",
    "クリストファー",
    "グレン",
    "ケビン",
    "ジェームズ",
    "ジェーン",
    "ジェフ",
    "ジミー",
    "ジャック",
    "ジャン",
    "ジョージ",
    "ジョセフ",
    "ジョナサン",
    "ジョン",
    "スティーブ",
    "スティーブン",
    "ダニエル",
    "チャールズ",
    "チャック",
    "ティム",
    "デイビッド",
    "デイヴ",
    "トーマス",
    "トム",
    "ナタリー",
    "ニール",
    "ニコラス",
    "ニック",
    "ハリー",
    "バート",
    "パトリック",
    "ビル",
    "フィリップ",
    "フランク",
    "フレディ",
    "フレデリック",
    "ブライアン",
    "ブルース",
    "ヘンリー",
    "ベン",
    "ベンジャミン",
    "ボブ",
    "ポール",
    "マーク",
    "マーティン",
    "マイク",
    "マイケル",
    "マシュー",
    "マックス",
    "マリー",
    "ミック",
    "レイ",
    "リチャード",
    "リンダ",
    "ルイ",
    "レオナルド",
    "ロジャー",
    "ロバート",
    "ロン",
    "ロナルド",
    # イニシャル
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
    "K",
    "L",
    "M",
    "N",
    "O",
    "P",
    "Q",
    "R",
    "S",
    "T",
    "U",
    "V",
    "W",
    "X",
    "Y",
    "Z",
    # 藤子・F・不二雄対策
    "藤子",
}

# 肩書/役職パターン
TITLE_KEYWORDS = [
    "創業者",
    "設立者",
    "創始者",
    "会長",
    "社長",
    "CEO",
    "副社長",
    "元CEO",
    "元会長",
    "元社長",
    "現会長",
    "共同開発者",
    "共同創業者",
    "名誉教授",
    "教授",
    "研究者",
]

# 別名・通称キーワード（追加: 2025-12-15）
ALIAS_KEYWORDS = {
    "山中教授": "山中伸弥",
    "マンデラ": "ネルソン・マンデラ",
    "ホリエモン": "堀江貴文",
    "Mackenyu": "新田真剣佑",  # 俳優の英字別名（追加: 2025-12-16）
    "サンダース上院議員": "バーニー・サンダース上院議員",  # 役職語混入（修正: 2025-12-16）
    "岸田文雄夫人": "岸田裕子",  # 関係語混入（修正: 2025-12-16）
    "竹中工務店創業者": "竹中藤右衛門",  # 組織名・役職混入（追加: 2025-12-16）
    "石川島播磨重工創業者": "久保田権四郎",  # 組織名・役職混入（追加: 2025-12-16）
    "ルイ・ヴィトン創業者ルイ・ヴィトン": "ルイ・ヴィトン",  # 組織名・重複（追加: 2025-12-16）
    # 英字芸名→カタカナ正規化（追加: 2025-12-21）
    "Madonna": "マドンナ",
    "Prince": "プリンス",
    "Beyoncé": "ビヨンセ",
    "Hergé": "エルジェ",
    "Rintaro": "りんたろう",
    "Francis Fukuyama": "フランシス・フクヤマ",
    "Marcin Iwiński": "マルチン・イヴィンスキ",
    # 企業＋人物混在パターン（追加: 2025-12-21）
    "Activision・Bobby Kotick": "ボビー・コティック",
    "Bethesda・Todd Howard": "トッド・ハワード",
    # FIN.K.L メンバー正規化（追加: 2025-12-21）
    "Shelly": "イ・ジン",  # 韓国 FIN.K.L メンバー（※日本のタレントSHELLYとは別人）
    # 今後発見された別名をここに追加
}

# 職業修飾子（新規）
PROFESSION_MODIFIERS = [
    "秋葉原系",
    "平成の",
    "令和の",
    "伝説の",
    "天才",
    "カリスマ",
    "ベテラン",
    "新進気鋭の",
    "人気",
    "有名",
    "お笑い",
    "アニメ",
    "高所順応",
]

# 役名キーワード（新規）
ROLE_KEYWORDS = [
    "役",
    "CV",
    "声の出演",
    "主演",
]

# 職業パターン
PROFESSION_KEYWORDS = [
    # 既存
    "落語家",
    "声優",
    "作詞家",
    "作曲家",
    "漫画家",
    "陶芸家",
    "書道家",
    "華道家",
    "俳人",
    "能楽師",
    "漆芸家",
    "版画家",
    "日本画家",
    "現代美術家",
    "作庭家",
    "音楽家",
    "オペラ歌手",
    "コメディアン",
    # 追加（Phase 2で修正した職業）
    "建築家",  # EP-000006250等で検出
    "画家",  # EP-000006256で検出
    "映画監督",  # EP-000006254で検出
    # 追加（関連職業）
    "彫刻家",
    "写真家",
    "詩人",
    "小説家",
    "劇作家",
    "脚本家",
    "演出家",
    "指揮者",
    "ピアニスト",
    "バイオリニスト",
    "デザイナー",
    "イラストレーター",
    "アニメーター",
    # Phase 8 追加（肩書き接頭辞除去）
    "浮世絵師",  # 歌川国芳
    "人間国宝",  # 金重陶陽
    "歌舞伎俳優",  # 中村勘九郎
]

# スポーツカテゴリ
SPORT_KEYWORDS = [
    "野球",
    "サッカー",
    "柔道",
    "競泳",
    "体操",
    "陸上",
    "テニス",
    "ゴルフ",
    "フィギュア",
    "スノーボード",
    "スケート",
    "卓球",
    "相撲",
    "バスケ",
    "ラグビー",
    "バレーボール",
    "マラソン",
    "水泳飛込み",
    "女子レスリング",
    "アイスホッケー",
]

# 力士四股名キーワード（著名力士のリスト）
RIKISHI_SHIKONA = [
    # 横綱（大横綱）
    "千代の富士",
    "大鵬",
    "貴乃花",
    "朝青龍",
    "白鵬",
    "北の湖",
    "輪島",
    "若乃花",
    "貴ノ花",
    "隆の里",
    "双羽黒",
    "旭富士",
    "曙",
    "武蔵丸",
    "栃東",
    "琴欧洲",
    "日馬富士",
    "鶴竜",
    "稀勢の里",
    "照ノ富士",
    # 大関級
    "千代大海",
    "琴光喜",
    "魁皇",
    "琴奨菊",
    "豪栄道",
    "高安",
    "貴景勝",
    "正代",
    "御嶽海",
    "霧馬山",
    # 🆕 追加（2025-12-16）: Phase 1で確認した力士
    "舞の海",  # 舞の海秀平（P5420FBE）
    "土佐ノ海",  # 土佐ノ海敏生（P887D990）
]

# リーグ/組織
LEAGUE_KEYWORDS = [
    "NBA",
    "NFL",
    "F1",
    "UFC",
    "NHL",
    "MLB",
]

# 関係性パターン
RELATIONSHIP_KEYWORDS = [
    "の息子",
    "の娘",
    "の弟子",
    "の後継者",
    "の兄弟",
    "の孫",
    "の妻",
    "の夫",
    "の同僚",
]

# 企業/組織名（所属パターン）
COMPANY_KEYWORDS = [
    "CD Projekt",
    "Epic Games",
    "Rockstar",
    "Ubisoft",
    "Electronic Arts",
    "アリババ",
    "テスラ",
    "スペースX",
    "フェイスブック",
    "フェデックス",
    "バークシャー・ハサウェイ",
    "ソフトバンク",
    "ファーストリテイリング",
    "セブンイレブン",
    "キーエンス",
    "ソニー",
    "パナソニック",
    "任天堂",
    "カプコン",
    "スクウェア・エニックス",
    "バンダイナムコ",
    "理化学研究所",
    "島津製作所",
    "青山学院大学",
    "前田建設工業",
    "楽天",
    "福岡ソフトバンクホークス",
    "レアル・マドリード",
    "マンチェスター・シティ",
    "バルセロナ",
    "辻調",  # 新規: 「辻調 辻芳樹」対応
    "維新",  # 新規: 「維新松井一郎」対応（党名）
    "聖路加国際病院",  # 新規: 「聖路加国際病院 日野原重明」対応
]

# チーム名（スポーツチーム）
TEAM_KEYWORDS = [
    "レアル・マドリリード",
    "レアル・マドリード",
    "マンチェスター・シティ",
    "バルセロナ",
]

# アイドルグループ（新規）
IDOL_GROUP_KEYWORDS = [
    "AKB48",
    "SKE48",
    "NMB48",
    "HKT48",
    "乃木坂46",
    "櫻坂46",
    "日向坂46",
    "欅坂46",
    "嵐",
    "SMAP",
    "TOKIO",
    "V6",
    "KinKi Kids",
    "関ジャニ∞",
    "Hey! Say! JUMP",
    "King & Prince",
    "SixTONES",
    "Snow Man",
    "モーニング娘。",
]

# 音楽グループ（新規）
MUSIC_GROUP_KEYWORDS = [
    "RADWIMPS",
    "チューリップ",
    "サザンオールスターズ",
    "Mr.Children",
    "BUMP OF CHICKEN",
    "スピッツ",
    "L'Arc〜en〜Ciel",
    "GLAY",
    "X JAPAN",
    "B'z",
    "スキマスイッチ",
    "ゆず",
    "コブクロ",
    "いきものがかり",
    "Perfume",
    "SEKAI NO OWARI",
    "Official髭男dism",
    "King Gnu",
    "U2",
    "Coldplay",
    "Queen",
    "The Beatles",
    "ONE OK ROCK",
    "UVERworld",
    "レペゼン地球",  # 新規: 「レペゼン地球 DJ社長」対応
]

# お笑いグループ（新規）
COMEDY_GROUP_KEYWORDS = [
    "野性爆弾",
    "トレンディエンジェル",
    "ガンバレルーヤ",
    "ダウンタウン",
    "ウッチャンナンチャン",
    "とんねるず",
    "爆笑問題",
    "くりぃむしちゅー",
    "ナインティナイン",
    "雨上がり決死隊",
    "バナナマン",
    "サンドウィッチマン",
    "千鳥",
    "霜降り明星",
    "オードリー",
    "アンジャッシュ",
    "おぎやはぎ",
    "品川庄司",
    "さまぁ〜ず",
    "ロンドンブーツ1号2号",
    "オリエンタルラジオ",
    "チョコレートプラネット",
    "かまいたち",
    "ミルクボーイ",
    "ぺこぱ",
    "EXIT",
    "宮下草薙",
    "錦鯉",
]

# 代数表記パターン（新規）
GENERATION_PREFIXES = [
    "初代",
    "二代目",
    "2代目",
    "三代目",
    "3代目",
    "四代目",
    "4代目",
    "五代目",
    "5代目",
    "六代目",
    "6代目",
    "七代目",
    "7代目",
    "八代目",
    "8代目",
    "九代目",
    "9代目",
    "十代目",
    "10代目",
    "十一代目",
    "11代目",
    "十二代目",
    "12代目",
    "十三代目",
    "13代目",
    "十四代目",
    "14代目",
    "十五代目",
    "15代目",
    # 「代」なし形式（陶芸家など） - 「八代」は苗字として一般的なため除外
    "十四代",
    "十五代",
    "十三代",
    "十二代",
    "十一代",
    "十代",
    "九代",
    # "八代" - 苗字（八代亜紀など）と混同するため除外
    "七代",
    "六代",
    "五代",
    "四代",
    # "三代" - 苗字として存在するため除外
    "二代",
]

# 説明文プレフィックス（新規）
DESCRIPTION_PREFIXES = [
    "日本人実業家の",
    "日本の実業家",
    "元日本実業家の",
]


@dataclass
class NormalizationResult:
    """正規化結果"""

    original_name: str
    normalized_name: str
    title: Optional[str]
    affiliation: Optional[str]
    pattern_type: str
    confidence: float
    requires_review: bool
    match_detail: str  # マッチした詳細


class PersonNameNormalizer:
    """人物名正規化エンジン"""

    def __init__(self, min_confidence: float = 0.85, use_llm: bool = False):
        self.min_confidence = min_confidence
        self.use_llm = use_llm
        self.anthropic_client = None

        if use_llm and HAS_ANTHROPIC:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if api_key:
                self.anthropic_client = anthropic.Anthropic(api_key=api_key)

    def is_western_name(self, name: str) -> bool:
        """西洋人名パターンかどうか判定"""
        if "・" not in name:
            return False

        # 関係性キーワードを含む場合は西洋人名ではない
        for rel in RELATIONSHIP_KEYWORDS:
            if rel in name:
                return False

        parts = name.split("・")
        first_part = parts[0]

        # ファーストネームリストに含まれる
        if first_part in WESTERN_FIRST_NAMES:
            return True

        # 全部カタカナ（西洋人名の可能性）
        if self._is_all_katakana(name.replace("・", "")):
            # 2パート以上で、最初のパートが長い（3文字以上）
            if len(parts) >= 2 and len(first_part) >= 3:
                return True

        return False

    def _is_all_katakana(self, text: str) -> bool:
        """全てカタカナかどうか"""
        for char in text:
            if not ("\u30a0" <= char <= "\u30ff" or char in "ー・"):
                return False
        return True

    def normalize(self, person_name: str) -> Optional[NormalizationResult]:
        """人物名を正規化"""
        if not person_name or pd.isna(person_name):
            return None

        # 西洋人名チェック
        if self.is_western_name(person_name):
            return None

        # 別名チェック（最優先）★NEW
        result = self._match_alias(person_name)
        if result:
            return result

        # パターンマッチング（優先度順）
        # 説明文プレフィックス（新規）
        result = self._match_description_prefix(person_name)
        if result:
            return result

        result = self._match_affiliation_prefix(person_name)
        if result:
            return result

        result = self._match_sport_prefix(person_name)
        if result:
            return result

        # 力士名パターン（新規追加）
        result = self._match_rikishi_name(person_name)
        if result:
            return result

        # 修飾職業パターン（秋葉原系漫画家OKAMA など）
        result = self._match_modified_profession(person_name)
        if result:
            return result

        # 複雑なグループ名パターン（新規）
        result = self._match_complex_group_prefix(person_name)
        if result:
            return result

        result = self._match_profession_prefix(person_name)
        if result:
            return result

        # 役割接尾辞パターン（アニメ声優・悟空役野沢雅子 など）
        result = self._match_role_suffix(person_name)
        if result:
            return result

        result = self._match_title_role(person_name)
        if result:
            return result

        result = self._match_relationship(person_name)
        if result:
            return result

        result = self._match_team_member(person_name)
        if result:
            return result

        result = self._match_league_prefix(person_name)
        if result:
            return result

        # アイドルグループパターン（AKB48指原莉乃 など）
        result = self._match_idol_group(person_name)
        if result:
            return result

        # 音楽グループパターン（RADWIMPSの野田洋次郎 など）
        result = self._match_music_group(person_name)
        if result:
            return result

        # お笑いグループパターン（野性爆弾くっきー など）
        result = self._match_comedy_group(person_name)
        if result:
            return result

        # 代数表記パターン（十四代酒井田柿右衛門 など）
        result = self._match_generation_prefix(person_name)
        if result:
            return result

        return None

    def _match_description_prefix(self, name: str) -> Optional[NormalizationResult]:
        """説明文プレフィックス除去（「日本人実業家の稲盛和夫」対応）"""
        for desc in DESCRIPTION_PREFIXES:
            if name.startswith(desc) and len(name) > len(desc):
                person = name[len(desc) :]
                if len(person) >= 2:
                    return NormalizationResult(
                        original_name=name,
                        normalized_name=person,
                        title=desc.rstrip("の"),  # 「日本人実業家」として保存
                        affiliation=None,
                        pattern_type="DESCRIPTION_PREFIX",
                        confidence=0.90,
                        requires_review=False,
                        match_detail=f"説明文「{desc}」を除去",
                    )
        return None

    def _match_affiliation_prefix(self, name: str) -> Optional[NormalizationResult]:
        """会社・人物 形式の検出"""
        for company in COMPANY_KEYWORDS:
            # 会社+肩書+人物 形式（楽天創業者三木谷浩史 など）
            for title_kw in TITLE_KEYWORDS:
                prefix = company + title_kw
                if name.startswith(prefix) and len(name) > len(prefix):
                    person = name[len(prefix) :]
                    if len(person) >= 2:
                        return NormalizationResult(
                            original_name=name,
                            normalized_name=person,
                            title=title_kw,
                            affiliation=company,
                            pattern_type="AFFILIATION_TITLE",
                            confidence=0.95,
                            requires_review=False,
                            match_detail=f"会社「{company}」と肩書「{title_kw}」を分離",
                        )

            # 会社の人物 形式（「理化学研究所の野依良治」など）
            pattern = f"^{re.escape(company)}の(.+)$"
            match = re.match(pattern, name)
            if match:
                person = match.group(1)
                if len(person) >= 2:
                    return NormalizationResult(
                        original_name=name,
                        normalized_name=person,
                        title=None,
                        affiliation=company,
                        pattern_type="AFFILIATION_PREFIX",
                        confidence=0.93,
                        requires_review=False,
                        match_detail=f"会社「{company}」を分離（の）",
                    )

            # 会社・人物 形式
            pattern = f"^{re.escape(company)}・(.+)$"
            match = re.match(pattern, name)
            if match:
                person = match.group(1)
                return NormalizationResult(
                    original_name=name,
                    normalized_name=person,
                    title=None,
                    affiliation=company,
                    pattern_type="AFFILIATION_PREFIX",
                    confidence=0.95,
                    requires_review=False,
                    match_detail=f"会社「{company}」を分離",
                )

            # 会社 人物 形式（スペース区切り、「辻調 辻芳樹」など）
            pattern = f"^{re.escape(company)}\\s+(.+)$"
            match = re.match(pattern, name)
            if match:
                person = match.group(1)
                if len(person) >= 2:
                    return NormalizationResult(
                        original_name=name,
                        normalized_name=person,
                        title=None,
                        affiliation=company,
                        pattern_type="AFFILIATION_PREFIX",
                        confidence=0.90,
                        requires_review=False,
                        match_detail=f"会社「{company}」を分離（スペース）",
                    )

            # 会社人物 形式（区切りなし）
            if name.startswith(company) and len(name) > len(company):
                person = name[len(company) :]
                # 次の文字がカタカナか漢字ならマッチ
                if person and (self._is_all_katakana(person[0]) or "\u4e00" <= person[0] <= "\u9fff"):
                    return NormalizationResult(
                        original_name=name,
                        normalized_name=person,
                        title=None,
                        affiliation=company,
                        pattern_type="AFFILIATION_PREFIX",
                        confidence=0.90,
                        requires_review=False,
                        match_detail=f"会社「{company}」を分離（区切りなし）",
                    )

        return None

    def _match_sport_prefix(self, name: str) -> Optional[NormalizationResult]:
        """スポーツ人物 形式の検出"""
        for sport in SPORT_KEYWORDS:
            # スポーツ・人物 形式
            pattern = f"^{re.escape(sport)}・(.+)$"
            match = re.match(pattern, name)
            if match:
                person = match.group(1)
                return NormalizationResult(
                    original_name=name,
                    normalized_name=person,
                    title=sport,
                    affiliation=None,
                    pattern_type="SPORT_PREFIX",
                    confidence=0.90,
                    requires_review=False,
                    match_detail=f"スポーツ「{sport}」を分離",
                )

            # スポーツ人物 形式（区切りなし）
            if name.startswith(sport) and len(name) > len(sport):
                person = name[len(sport) :]
                if person and ("\u4e00" <= person[0] <= "\u9fff"):  # 漢字で始まる
                    return NormalizationResult(
                        original_name=name,
                        normalized_name=person,
                        title=sport,
                        affiliation=None,
                        pattern_type="SPORT_PREFIX",
                        confidence=0.90,
                        requires_review=False,
                        match_detail=f"スポーツ「{sport}」を分離（区切りなし）",
                    )

        return None

    def _match_rikishi_name(self, name: str) -> Optional[NormalizationResult]:
        """
        力士名パターンの検出（四股名+本名の名 → 四股名）

        パターン:
        1. 既知の四股名+1-2文字の漢字（千代の富士貢 → 千代の富士）
        2. 「の」を含む力士名+1-2文字の漢字（千代の国憲輝 → 千代の国）

        Args:
            name: 人物名

        Returns:
            正規化結果（該当する場合）
        """
        # 既知の四股名リストとマッチ
        for shikona in RIKISHI_SHIKONA:
            # 四股名で始まり、1-2文字の漢字が続くパターン
            if name.startswith(shikona) and len(name) > len(shikona):
                suffix = name[len(shikona) :]

                # サフィックスが1-2文字の漢字のみか確認
                if 1 <= len(suffix) <= 2 and all("\u4e00" <= char <= "\u9fff" for char in suffix):
                    return NormalizationResult(
                        original_name=name,
                        normalized_name=shikona,
                        title="力士",
                        affiliation="大相撲",
                        pattern_type="RIKISHI_SHIKONA",
                        confidence=0.95,
                        requires_review=False,
                        match_detail=f"四股名「{shikona}」から本名の名「{suffix}」を除去",
                    )

        # 「の」を含む未知の力士名パターン（汎用）
        if "の" in name:
            parts = name.split("の")
            if len(parts) >= 2:
                last_part = parts[-1]
                # 最後の部分が3文字以上で、末尾1-2文字が漢字のみなら分離候補
                if len(last_part) >= 3:
                    # 末尾1文字が漢字の場合
                    if "\u4e00" <= last_part[-1] <= "\u9fff":
                        shikona_candidate = name[:-1]
                        removed_char = name[-1]
                        return NormalizationResult(
                            original_name=name,
                            normalized_name=shikona_candidate,
                            title="力士",
                            affiliation="大相撲",
                            pattern_type="RIKISHI_SHIKONA_GENERIC",
                            confidence=0.80,
                            requires_review=True,  # 汎用パターンは要レビュー
                            match_detail=f"「の」を含む力士名から末尾「{removed_char}」を除去",
                        )
                    # 末尾2文字が漢字の場合
                    elif len(last_part) >= 4 and all("\u4e00" <= char <= "\u9fff" for char in last_part[-2:]):
                        shikona_candidate = name[:-2]
                        removed_chars = name[-2:]
                        return NormalizationResult(
                            original_name=name,
                            normalized_name=shikona_candidate,
                            title="力士",
                            affiliation="大相撲",
                            pattern_type="RIKISHI_SHIKONA_GENERIC",
                            confidence=0.80,
                            requires_review=True,
                            match_detail=f"「の」を含む力士名から末尾「{removed_chars}」を除去",
                        )

        return None

    def _match_profession_prefix(self, name: str) -> Optional[NormalizationResult]:
        """職業・人物 形式の検出"""
        for profession in PROFESSION_KEYWORDS:
            # 職業・人物 形式
            pattern = f"^{re.escape(profession)}[・\\s]?(.+)$"
            match = re.match(pattern, name)
            if match:
                person = match.group(1)
                if person and person != name:
                    return NormalizationResult(
                        original_name=name,
                        normalized_name=person,
                        title=profession,
                        affiliation=None,
                        pattern_type="PROFESSION_PREFIX",
                        confidence=0.90,
                        requires_review=False,
                        match_detail=f"職業「{profession}」を分離",
                    )

        return None

    def _match_title_role(self, name: str) -> Optional[NormalizationResult]:
        """肩書人物 形式の検出"""
        for title_kw in TITLE_KEYWORDS:
            # 会社創業者人物 形式
            pattern = f"^(.+?){re.escape(title_kw)}(.+)$"
            match = re.match(pattern, name)
            if match:
                company = match.group(1)
                person = match.group(2)

                # 人物名が短すぎる場合はスキップ
                if len(person) < 2:
                    continue

                return NormalizationResult(
                    original_name=name,
                    normalized_name=person,
                    title=title_kw,
                    affiliation=company if company else None,
                    pattern_type="TITLE_ROLE",
                    confidence=0.85,
                    requires_review=False,
                    match_detail=f"肩書「{title_kw}」を分離、所属「{company}」",
                )

        return None

    def _match_relationship(self, name: str) -> Optional[NormalizationResult]:
        """関係性人物 形式の検出"""
        for rel in RELATIONSHIP_KEYWORDS:
            pattern = f"^(.+){re.escape(rel)}(.+)$"
            match = re.match(pattern, name)
            if match:
                related_person = match.group(1)
                person = match.group(2)

                # 人物名が短すぎる場合はスキップ
                if len(person) < 2:
                    continue

                return NormalizationResult(
                    original_name=name,
                    normalized_name=person,
                    title=f"{related_person}{rel}",
                    affiliation=None,
                    pattern_type="RELATIONSHIP",
                    confidence=0.85,  # LLM検証で信頼度を確保
                    requires_review=False,
                    match_detail=f"関係性「{related_person}{rel}」を分離",
                )

        return None

    def _match_team_member(self, name: str) -> Optional[NormalizationResult]:
        """チーム・人物 形式の検出"""
        for team in TEAM_KEYWORDS:
            pattern = f"^{re.escape(team)}[・\\s]?(.+)$"
            match = re.match(pattern, name)
            if match:
                person = match.group(1)
                return NormalizationResult(
                    original_name=name,
                    normalized_name=person,
                    title=None,
                    affiliation=team,
                    pattern_type="TEAM_MEMBER",
                    confidence=0.75,
                    requires_review=True,
                    match_detail=f"チーム「{team}」を分離",
                )

        return None

    def _match_league_prefix(self, name: str) -> Optional[NormalizationResult]:
        """リーグ・人物 形式の検出"""
        for league in LEAGUE_KEYWORDS:
            pattern = f"^{re.escape(league)}[・\\s]?(.+)$"
            match = re.match(pattern, name)
            if match:
                person = match.group(1)
                return NormalizationResult(
                    original_name=name,
                    normalized_name=person,
                    title=None,
                    affiliation=league,
                    pattern_type="LEAGUE_PREFIX",
                    confidence=0.90,
                    requires_review=False,
                    match_detail=f"リーグ「{league}」を分離",
                )

        return None

    def _match_modified_profession(self, name: str) -> Optional[NormalizationResult]:
        """修飾職業・人物 形式の検出（秋葉原系漫画家OKAMA など）"""
        for modifier in PROFESSION_MODIFIERS:
            for profession in PROFESSION_KEYWORDS:
                # 修飾子+職業+人物 形式
                prefix = modifier + profession
                if name.startswith(prefix) and len(name) > len(prefix):
                    remaining = name[len(prefix) :]

                    # 修飾子+職業+・+役名+人物 形式（アニメ声優・悟空役野沢雅子 など）
                    for role_kw in ROLE_KEYWORDS:
                        role_pattern = f"^[・\\s]?(.+?){re.escape(role_kw)}(.+)$"
                        role_match = re.match(role_pattern, remaining)
                        if role_match:
                            role_name = role_match.group(1)
                            person = role_match.group(2)
                            if len(person) >= 2:
                                full_title = f"{prefix}・{role_name}{role_kw}"
                                return NormalizationResult(
                                    original_name=name,
                                    normalized_name=person,
                                    title=full_title,
                                    affiliation=None,
                                    pattern_type="MODIFIED_PROFESSION_ROLE",
                                    confidence=0.90,
                                    requires_review=False,
                                    match_detail=f"修飾職業+役割「{full_title}」を分離",
                                )

                    # 人物名が空や短すぎる場合はスキップ
                    if len(remaining) >= 2:
                        return NormalizationResult(
                            original_name=name,
                            normalized_name=remaining,
                            title=prefix,
                            affiliation=None,
                            pattern_type="MODIFIED_PROFESSION",
                            confidence=0.88,
                            requires_review=False,
                            match_detail=f"修飾職業「{prefix}」を分離",
                        )

        return None

    def _match_complex_group_prefix(self, name: str) -> Optional[NormalizationResult]:
        """複雑なグループ名パターン（「お笑い・とんねるず石橋貴明」対応）"""
        # お笑い + グループ名 + 人物名
        for modifier in PROFESSION_MODIFIERS:
            for group in COMEDY_GROUP_KEYWORDS:
                prefix = f"{modifier}・{group}"
                if name.startswith(prefix) and len(name) > len(prefix):
                    person = name[len(prefix) :]
                    # 人物名の最低長チェック
                    if len(person) >= 2:
                        return NormalizationResult(
                            original_name=name,
                            normalized_name=person,
                            title=modifier,
                            affiliation=group,
                            pattern_type="COMPLEX_GROUP_PREFIX",
                            confidence=0.95,
                            requires_review=False,
                            match_detail=f"職業+グループ「{prefix}」を分離",
                        )
        return None

    def _match_role_suffix(self, name: str) -> Optional[NormalizationResult]:
        """役割接尾辞・人物 形式の検出（アニメ声優・悟空役野沢雅子 など）"""
        for role_kw in ROLE_KEYWORDS:
            # 〜役人物 形式（役名の後に人物名が続く）
            pattern = f"^(.+){re.escape(role_kw)}(.+)$"
            match = re.match(pattern, name)
            if match:
                role_part = match.group(1)
                person = match.group(2)

                # 人物名が短すぎる場合はスキップ
                if len(person) < 2:
                    continue

                return NormalizationResult(
                    original_name=name,
                    normalized_name=person,
                    title=f"{role_part}{role_kw}",
                    affiliation=None,
                    pattern_type="ROLE_SUFFIX",
                    confidence=0.90,
                    requires_review=False,
                    match_detail=f"役割「{role_part}{role_kw}」を分離",
                )

        return None

    def _match_idol_group(self, name: str) -> Optional[NormalizationResult]:
        """アイドルグループ・人物 形式の検出（AKB48指原莉乃 など）"""
        for group in IDOL_GROUP_KEYWORDS:
            # グループ・人物 形式
            pattern = f"^{re.escape(group)}[・\\s]?(.+)$"
            match = re.match(pattern, name)
            if match:
                person = match.group(1)
                if len(person) >= 2:
                    return NormalizationResult(
                        original_name=name,
                        normalized_name=person,
                        title=None,
                        affiliation=group,
                        pattern_type="IDOL_GROUP",
                        confidence=0.92,
                        requires_review=False,
                        match_detail=f"アイドルグループ「{group}」を分離",
                    )

        return None

    def _match_music_group(self, name: str) -> Optional[NormalizationResult]:
        """音楽グループ・人物 形式の検出（RADWIMPSの野田洋次郎 など）"""
        for group in MUSIC_GROUP_KEYWORDS:
            # グループの人物 形式
            pattern = f"^{re.escape(group)}の(.+)$"
            match = re.match(pattern, name)
            if match:
                person = match.group(1)
                if len(person) >= 1:
                    return NormalizationResult(
                        original_name=name,
                        normalized_name=person,
                        title=None,
                        affiliation=group,
                        pattern_type="MUSIC_GROUP",
                        confidence=0.93,
                        requires_review=False,
                        match_detail=f"音楽グループ「{group}」を分離",
                    )

            # グループ・人物 形式
            pattern = f"^{re.escape(group)}・(.+)$"
            match = re.match(pattern, name)
            if match:
                person = match.group(1)
                if len(person) >= 1:
                    return NormalizationResult(
                        original_name=name,
                        normalized_name=person,
                        title=None,
                        affiliation=group,
                        pattern_type="MUSIC_GROUP",
                        confidence=0.90,
                        requires_review=False,
                        match_detail=f"音楽グループ「{group}」を分離",
                    )

            # グループ 人物 形式（スペース区切り、「レペゼン地球 DJ社長」など）
            pattern = f"^{re.escape(group)}\\s+(.+)$"
            match = re.match(pattern, name)
            if match:
                person = match.group(1)
                if len(person) >= 2:
                    return NormalizationResult(
                        original_name=name,
                        normalized_name=person,
                        title=None,
                        affiliation=group,
                        pattern_type="MUSIC_GROUP",
                        confidence=0.90,
                        requires_review=False,
                        match_detail=f"音楽グループ「{group}」を分離（スペース）",
                    )

        return None

    def _match_comedy_group(self, name: str) -> Optional[NormalizationResult]:
        """お笑いグループ・人物 形式の検出（野性爆弾くっきー など）"""
        for group in COMEDY_GROUP_KEYWORDS:
            # グループ・人物 形式
            pattern = f"^{re.escape(group)}・(.+)$"
            match = re.match(pattern, name)
            if match:
                person = match.group(1)
                if len(person) >= 1:
                    return NormalizationResult(
                        original_name=name,
                        normalized_name=person,
                        title=None,
                        affiliation=group,
                        pattern_type="COMEDY_GROUP",
                        confidence=0.90,
                        requires_review=False,
                        match_detail=f"お笑いグループ「{group}」を分離",
                    )

            # グループ人物 形式（区切りなし）
            if name.startswith(group) and len(name) > len(group):
                person = name[len(group) :]
                # 次の文字がひらがな、カタカナ、漢字ならマッチ
                if person and (
                    "\u3040" <= person[0] <= "\u309f"  # ひらがな
                    or "\u30a0" <= person[0] <= "\u30ff"  # カタカナ
                    or "\u4e00" <= person[0] <= "\u9fff"  # 漢字
                ):
                    return NormalizationResult(
                        original_name=name,
                        normalized_name=person,
                        title=None,
                        affiliation=group,
                        pattern_type="COMEDY_GROUP",
                        confidence=0.88,
                        requires_review=False,
                        match_detail=f"お笑いグループ「{group}」を分離（区切りなし）",
                    )

        return None

    def _match_generation_prefix(self, name: str) -> Optional[NormalizationResult]:
        """代数表記・人物 形式の検出（十四代酒井田柿右衛門 など）"""
        for gen in GENERATION_PREFIXES:
            if name.startswith(gen) and len(name) > len(gen):
                person = name[len(gen) :]
                # 次の文字が漢字またはひらがなならマッチ
                if person and (
                    "\u4e00" <= person[0] <= "\u9fff"  # 漢字
                    or "\u3040" <= person[0] <= "\u309f"  # ひらがな
                ):
                    return NormalizationResult(
                        original_name=name,
                        normalized_name=person,
                        title=gen,
                        affiliation=None,
                        pattern_type="GENERATION_PREFIX",
                        confidence=0.85,
                        requires_review=True,  # 代数表記は要レビュー
                        match_detail=f"代数表記「{gen}」を分離",
                    )

        return None

    def _match_alias(self, name: str) -> Optional[NormalizationResult]:
        """
        別名・通称を正規表記に変換

        Args:
            name: 人物名

        Returns:
            正規化結果（該当する場合）
        """
        if name in ALIAS_KEYWORDS:
            canonical = ALIAS_KEYWORDS[name]
            return NormalizationResult(
                original_name=name,
                normalized_name=canonical,
                title=None,
                affiliation=None,
                pattern_type="ALIAS",
                confidence=1.0,  # 確定的な別名なので信頼度MAX
                requires_review=False,
                match_detail=f"別名「{name}」を正規表記「{canonical}」に変換",
            )

        return None

    def verify_with_llm(self, result: NormalizationResult) -> NormalizationResult:
        """LLMで正規化結果を検証"""
        if not self.anthropic_client:
            return result

        prompt = f"""以下の人物名の正規化結果を検証してください。

元の名前: {result.original_name}
正規化後の名前: {result.normalized_name}
抽出された肩書: {result.title}
抽出された所属: {result.affiliation}
パターン: {result.pattern_type}

以下の形式でJSON形式で回答してください:
{{
    "is_correct": true/false,
    "corrected_name": "修正後の名前（修正不要ならnull）",
    "reason": "判断理由"
}}
"""

        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )

            # レスポンスからJSON抽出
            text = response.content[0].text
            # JSON部分を抽出
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                if not data.get("is_correct") and data.get("corrected_name"):
                    result.normalized_name = data["corrected_name"]
                    result.match_detail += f" [LLM修正: {data.get('reason', '')}]"
                elif data.get("is_correct"):
                    result.confidence = min(result.confidence + 0.05, 1.0)
                    result.requires_review = False
        except Exception as e:
            print(f"  ⚠️ LLM検証エラー: {e}")

        return result

    def batch_normalize(self, df: pd.DataFrame) -> dict:
        """バッチ処理"""
        results: dict = {
            "auto_fixed": [],
            "requires_review": [],
            "skipped": [],
            "by_pattern": {},
        }

        unique_names = df["person_name"].dropna().unique()
        print(f"  ユニーク人物名: {len(unique_names)}件")

        for name in unique_names:
            result = self.normalize(name)

            if result is None:
                results["skipped"].append(name)
            elif result.confidence >= self.min_confidence and not result.requires_review:
                # LLM検証
                if self.use_llm and self.anthropic_client:
                    result = self.verify_with_llm(result)

                results["auto_fixed"].append(result)

                # パターン別集計
                if result.pattern_type not in results["by_pattern"]:
                    results["by_pattern"][result.pattern_type] = []
                results["by_pattern"][result.pattern_type].append(result)
            else:
                results["requires_review"].append(result)

        return results


def save_report(results: dict, output_path: Path):
    """レポートを保存"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "auto_fixed_count": len(results["auto_fixed"]),
            "requires_review_count": len(results["requires_review"]),
            "skipped_count": len(results["skipped"]),
        },
        "by_pattern": {k: len(v) for k, v in results["by_pattern"].items()},
        "auto_fixed": [asdict(r) for r in results["auto_fixed"]],
        "requires_review": [asdict(r) for r in results["requires_review"]],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def apply_normalizations(df: pd.DataFrame, results: List[NormalizationResult]) -> pd.DataFrame:
    """正規化結果をDataFrameに適用"""
    for result in results:
        mask = df["person_name"] == result.original_name

        if mask.sum() > 0:
            # 元の名前を保存
            df.loc[mask, "name_raw"] = result.original_name
            # 正規化された名前
            df.loc[mask, "person_name"] = result.normalized_name
            # 肩書
            if result.title:
                df.loc[mask, "title"] = result.title
            # 所属
            if result.affiliation:
                df.loc[mask, "affiliation"] = result.affiliation

    return df


def main():
    parser = argparse.ArgumentParser(description="人物名正規化")
    parser.add_argument("--dry-run", action="store_true", help="検出のみ（変更なし）")
    parser.add_argument("--execute", action="store_true", help="変更を実行")
    parser.add_argument("--use-llm", action="store_true", help="LLM検証を使用")
    parser.add_argument("--min-confidence", type=float, default=0.85, help="最小信頼度")
    parser.add_argument("--pattern", type=str, help="特定パターンのみ処理")
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("⚠️ --dry-run または --execute を指定してください")
        return

    dry_run = not args.execute

    print("=" * 70)
    print(f"🔧 人物名正規化 {'(dry-run)' if dry_run else '(実行)'}")
    print("=" * 70)
    print(f"  実行日時: {datetime.now().isoformat()}")
    print(f"  最小信頼度: {args.min_confidence}")
    print(f"  LLM検証: {'有効' if args.use_llm else '無効'}")

    # CSV読み込み
    print(f"\n📂 CSV読み込み: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"  レコード数: {len(df)}件")

    # 正規化エンジン初期化
    normalizer = PersonNameNormalizer(
        min_confidence=args.min_confidence,
        use_llm=args.use_llm,
    )

    # バッチ処理
    print("\n🔍 パターン検出中...")
    results = normalizer.batch_normalize(df)

    # 結果表示
    print("\n" + "=" * 70)
    print("📊 検出結果")
    print("=" * 70)
    print(f"  自動修正対象: {len(results['auto_fixed'])}件")
    print(f"  要レビュー: {len(results['requires_review'])}件")
    print(f"  スキップ: {len(results['skipped'])}件")

    print("\n📋 パターン別内訳:")
    for pattern, items in results["by_pattern"].items():
        print(f"  {pattern}: {len(items)}件")

    # 自動修正例を表示
    if results["auto_fixed"]:
        print("\n✅ 自動修正例（先頭10件）:")
        for r in results["auto_fixed"][:10]:
            print(f"  「{r.original_name}」→「{r.normalized_name}」")
            print(f"    肩書: {r.title}, 所属: {r.affiliation}, 信頼度: {r.confidence:.2f}")

    # 要レビュー例を表示
    if results["requires_review"]:
        print("\n⚠️ 要レビュー例（先頭10件）:")
        for r in results["requires_review"][:10]:
            print(f"  「{r.original_name}」→「{r.normalized_name}」")
            print(f"    パターン: {r.pattern_type}, 信頼度: {r.confidence:.2f}")

    # レポート保存
    REPORTS_DIR.mkdir(exist_ok=True)
    report_path = (
        REPORTS_DIR
        / f"name_normalization_{'dryrun' if dry_run else 'executed'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    save_report(results, report_path)
    print(f"\n📄 レポート保存: {report_path}")

    # 実行
    if not dry_run:
        print("\n💾 変更を適用中...")
        df = apply_normalizations(df, results["auto_fixed"])
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"  保存完了: {len(df)}件")

    print("\n✅ 完了")


if __name__ == "__main__":
    main()
