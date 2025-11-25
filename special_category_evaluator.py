#!/usr/bin/env python3
"""
特別カテゴリ評価システム
教育、スポーツ、エンタメ、音楽などの文化的重要度を考慮した評価
"""

import re
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class SpecialCategoryEvaluator:
    """特別カテゴリ評価クラス"""

    def __init__(self):
        """初期化"""

        # 教科書掲載人物リスト
        self.textbook_figures = {
            'ガンジー', 'ガンディー', 'マハトマ・ガンジー',
            'ナポレオン', 'ナポレオン・ボナパルト',
            'コロンブス', 'クリストファー・コロンブス',
            'エジソン', 'トーマス・エジソン',
            'アインシュタイン', 'アルベルト・アインシュタイン',
            'リンカーン', 'エイブラハム・リンカーン',
            'ワシントン', 'ジョージ・ワシントン',
            'ルター', 'マルティン・ルター',
            'ダーウィン', 'チャールズ・ダーウィン',
            'ニュートン', 'アイザック・ニュートン',
            'ガリレオ', 'ガリレオ・ガリレイ',
            'マザー・テレサ', 'キング牧師', 'マーティン・ルーサー・キング',
            'ヘレン・ケラー', 'ベートーヴェン', 'モーツァルト',
            'レオナルド・ダ・ヴィンチ', 'ミケランジェロ',
            'シェイクスピア', 'ゲーテ', 'ダンテ',
            'カエサル', 'アレクサンダー大王', 'チンギス・ハン',
            '始皇帝', '孔子', '釈迦', 'ブッダ',
            'ムハンマド', 'イエス・キリスト'
        }

        # オリンピック関連キーワード
        self.olympic_keywords = {
            'オリンピック', '五輪', 'Olympic',
            '金メダリスト', '銀メダリスト', '銅メダリスト',
            '金メダル', '銀メダル', '銅メダル'
        }

        # M-1関連
        self.m1_champions = {
            '中川家', 'ますだおかだ', 'フットボールアワー',
            'アンタッチャブル', 'ブラックマヨネーズ',
            'チュートリアル', 'サンドウィッチマン', 'NON STYLE',
            'パンクブーブー', 'トレンディエンジェル', '銀シャリ',
            'とろサーモン', '霜降り明星', 'ミルクボーイ',
            'マヂカルラブリー', '錦鯉', 'ウエストランド',
            '令和ロマン'
        }

        self.m1_finalists = {
            'ランジャタイ', 'インディアンス', 'ゆにばーす',
            'オズワルド', 'ロングコートダディ', 'もも',
            'スーパーマラドーナ', 'ジャングルポケット',
            'かまいたち', '和牛', 'スリムクラブ'
        }

        # 有名バンド（武道館/ドーム公演実績）
        self.famous_bands = {
            'LUNA SEA', 'X JAPAN', 'GLAY', "L'Arc-en-Ciel",
            'B\'z', 'Mr.Children', 'DREAMS COME TRUE',
            'サザンオールスターズ', 'BUMP OF CHICKEN',
            'ONE OK ROCK', 'RADWIMPS', 'SEKAI NO OWARI',
            'King Gnu', 'Official髭男dism', 'back number',
            'UVERworld', 'MAN WITH A MISSION', '[Alexandros]',
            'BABYMETAL', 'Perfume', 'きゃりーぱみゅぱみゅ',
            'AKB48', '乃木坂46', '櫻坂46', '日向坂46',
            'TWICE', 'BTS', 'SEVENTEEN', 'Stray Kids'
        }

        # YouTuber（100万人以上）
        self.mega_youtubers = {
            'HIKAKIN', 'はじめしゃちょー', 'フィッシャーズ',
            '東海オンエア', '水溜りボンド', 'スカイピース',
            'ヒカル', 'ラファエル', 'コムドット', 'フワちゃん',
            'エガちゃんねる', '中田敦彦', 'QuizKnock',
            '兄者弟者', 'ポッキー', 'キヨ', 'レトルト'
        }

        # 女子プロレス団体
        self.womens_wrestling = {
            'スターダム', 'STARDOM', 'アイスリボン', 'Ice Ribbon',
            'TJPW', '東京女子プロレス', 'SEAdLINNNG', 'シーダリング',
            'OZ', 'オズアカデミー', 'マーベラス', 'Marvelous',
            'センダイガールズ', 'Sendai Girls', 'Wave'
        }

    def evaluate(self, name: str, wikipedia_page: str = None,
                 current_score: float = 0.0) -> Tuple[float, str]:
        """
        特別カテゴリ評価を実施

        Args:
            name: 人物名
            wikipedia_page: Wikipediaページタイトル
            current_score: 現在のスコア

        Returns:
            (最終スコア, 評価理由)
        """

        max_score = current_score
        reason = ""

        # 教科書掲載人物チェック
        if self._is_textbook_figure(name):
            # 世界史的重要人物は9.0、その他は7.0
            if self._is_world_historical_figure(name):
                max_score = max(max_score, 9.0)
                reason = "世界史的重要人物（教科書掲載）"
            else:
                max_score = max(max_score, 7.0)
                reason = "教科書掲載人物"

        # オリンピック関連チェック
        olympic_status = self._check_olympic_status(name, wikipedia_page)
        if olympic_status:
            score, desc = olympic_status
            if score > max_score:
                max_score = score
                reason = desc

        # M-1関連チェック
        m1_status = self._check_m1_status(name)
        if m1_status:
            score, desc = m1_status
            if score > max_score:
                max_score = score
                reason = desc

        # 音楽関連チェック
        music_status = self._check_music_status(name)
        if music_status:
            score, desc = music_status
            if score > max_score:
                max_score = score
                reason = desc

        # YouTuber関連チェック
        youtube_status = self._check_youtube_status(name)
        if youtube_status:
            score, desc = youtube_status
            if score > max_score:
                max_score = score
                reason = desc

        # 女子プロレス関連チェック
        wrestling_status = self._check_womens_wrestling(name)
        if wrestling_status:
            score, desc = wrestling_status
            if score > max_score:
                max_score = score
                reason = desc

        # 最終スコアと理由を返す
        if reason:
            return max_score, reason
        else:
            return current_score, f"知名度スコア: {current_score:.1f}"

    def _is_textbook_figure(self, name: str) -> bool:
        """教科書掲載人物かチェック"""
        for figure in self.textbook_figures:
            if figure in name:
                return True
        return False

    def _is_world_historical_figure(self, name: str) -> bool:
        """世界史的重要人物かチェック"""
        world_figures = {
            'ガンジー', 'ガンディー', 'ナポレオン', 'コロンブス',
            'アインシュタイン', 'リンカーン', 'ワシントン',
            'カエサル', 'アレクサンダー大王', 'チンギス・ハン',
            '始皇帝', '孔子', '釈迦', 'ブッダ', 'ムハンマド',
            'イエス・キリスト', 'ダーウィン', 'ニュートン'
        }
        for figure in world_figures:
            if figure in name:
                return True
        return False

    def _check_olympic_status(self, name: str,
                            wikipedia_page: str = None) -> Optional[Tuple[float, str]]:
        """オリンピック関連ステータスチェック"""

        # 名前やWikipediaページにオリンピック関連キーワードがあるか
        text_to_check = f"{name} {wikipedia_page or ''}"

        if '金メダル' in text_to_check or '金メダリスト' in text_to_check:
            return (7.0, "オリンピック金メダリスト")
        elif '銀メダル' in text_to_check or '銅メダル' in text_to_check:
            return (6.0, "オリンピックメダリスト")
        elif '世界選手権' in text_to_check and '優勝' in text_to_check:
            return (6.0, "世界選手権優勝者")

        # 個別の金メダリスト
        gold_medalists = {'松本薫', '内村航平', '羽生結弦', '高橋尚子', '野口みずき'}
        for medalist in gold_medalists:
            if medalist in name:
                return (7.0, "オリンピック金メダリスト")

        return None

    def _check_m1_status(self, name: str) -> Optional[Tuple[float, str]]:
        """M-1グランプリ関連ステータスチェック"""

        # M-1優勝者チェック
        for champion in self.m1_champions:
            if champion in name:
                return (7.0, "M-1グランプリ優勝者")

        # トレンディエンジェルのメンバー
        if 'トレンディエンジェル' in name or name in ['斎藤司', 'たかし']:
            if '斎藤司' in name:
                return (7.0, "M-1グランプリ優勝者（トレンディエンジェル）")

        # M-1決勝進出者チェック
        for finalist in self.m1_finalists:
            if finalist in name:
                return (6.0, "M-1グランプリ決勝進出者")

        # ランジャタイ、オズワルド等のメンバー
        if 'ランジャタイ' in name or '伊藤幸司' in name or '国崎和也' in name:
            return (6.0, "M-1グランプリ決勝進出者（ランジャタイ）")
        if 'オズワルド' in name or '伊藤俊介' in name or '畠中悠' in name:
            return (6.0, "M-1グランプリ決勝進出者（オズワルド）")
        if 'スーパーマラドーナ' in name or '田中一彦' in name or '武智' in name:
            return (6.0, "M-1グランプリ決勝進出者（スーパーマラドーナ）")
        if 'ジャングルポケット' in name or 'おたけ' in name or '太田博久' in name:
            return (6.0, "M-1グランプリ決勝進出者（ジャングルポケット）")

        return None

    def _check_music_status(self, name: str) -> Optional[Tuple[float, str]]:
        """音楽関連ステータスチェック"""

        # 有名バンドメンバーチェック
        for band in self.famous_bands:
            if band in name:
                return (6.0, f"有名バンドメンバー（{band}）")

        # LUNA SEAメンバー
        luna_sea_members = ['真矢', 'SUGIZO', 'RYUICHI', 'J', 'INORAN']
        if 'LUNA SEA' in name:
            return (6.0, "有名バンドメンバー（LUNA SEA）")
        for member in luna_sea_members:
            if member in name and 'LUNA' in name:
                return (6.0, "有名バンドメンバー（LUNA SEA）")

        return None

    def _check_youtube_status(self, name: str) -> Optional[Tuple[float, str]]:
        """YouTube関連ステータスチェック"""

        # 100万人以上のYouTuberチェック
        for youtuber in self.mega_youtubers:
            if youtuber in name:
                return (6.0, f"YouTuber（登録者100万人以上）")

        # 水溜りボンドメンバー
        if '水溜りボンド' in name or name in ['カンタ', 'トミー']:
            if 'カンタ' in name or 'トミー' in name:
                return (6.0, "YouTuber（水溜りボンド・登録者100万人以上）")

        return None

    def _check_womens_wrestling(self, name: str) -> Optional[Tuple[float, str]]:
        """女子プロレス関連チェック"""

        # 女子プロレス関連キーワード
        wrestling_keywords = ['女子プロレス', 'スターダム', 'STARDOM']

        for keyword in wrestling_keywords:
            if keyword in name:
                return (4.0, "女子プロレスラー（大規模興行実績）")

        # 特定の選手名
        wrestlers = {'井上貴子', '井上京子', 'ダイナマイト関西'}
        for wrestler in wrestlers:
            if wrestler in name:
                return (4.0, "女子プロレスラー（大規模興行実績）")

        return None
