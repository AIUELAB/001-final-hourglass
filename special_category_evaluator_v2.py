#!/usr/bin/env python3
"""
特別カテゴリ評価システム V2
教育、政治、文化、スポーツ、エンタメなどの重要度を総合的に評価
"""

import re
from typing import Dict, Tuple, Optional, List
import logging

logger = logging.getLogger(__name__)

class SpecialCategoryEvaluatorV2:
    """特別カテゴリ評価クラス V2"""
    
    def __init__(self):
        """初期化"""
        self._initialize_categories()
    
    def _initialize_categories(self):
        """カテゴリデータの初期化"""
        
        # 国民栄誉賞受賞者（完全リスト）
        self.national_honor_recipients = {
            '王貞治', '長嶋茂雄', '美空ひばり', '古賀政男', '長谷川一夫',
            '植村直己', '山下泰裕', '衣笠祥雄', '藤山一郎', '千代の富士',
            '服部良一', '渥美清', '吉田正', '黒澤明', '高橋尚子',
            '遠藤実', '森繁久彌', '森光子', '森重文',
            '澤穂希', '宮間あや', '川澄奈穂美',  # なでしこジャパン
            '吉田沙保里', '伊調馨', '羽生善治', '井山裕太', '羽生結弦',
            '大谷翔平'
        }
        
        # 歴代内閣総理大臣（主要人物）
        self.prime_ministers = {
            '伊藤博文', '原敬', '高橋是清', '犬養毅', '近衛文麿',
            '東條英機', '吉田茂', '鳩山一郎', '岸信介', '池田勇人',
            '佐藤栄作', '田中角栄', '三木武夫', '福田赳夫', '大平正芳',
            '鈴木善幸', '中曽根康弘', '竹下登', '宇野宗佑', '海部俊樹',
            '宮澤喜一', '細川護熙', '羽田孜', '村山富市', '橋本龍太郎',
            '小渕恵三', '森喜朗', '小泉純一郎', '安倍晋三', '福田康夫',
            '麻生太郎', '鳩山由紀夫', '菅直人', '野田佳彦', '菅義偉',
            '岸田文雄'
        }
        
        # 文化勲章受章者（代表的人物）
        self.culture_medal_recipients = {
            '湯川秀樹', '朝永振一郎', '江崎玲於奈', '福井謙一', '利根川進',
            '白川英樹', '野依良治', '小柴昌俊', '田中耕一', '南部陽一郎',
            '小林誠', '益川敏英', '鈴木章', '根岸英一', '山中伸弥',
            '赤崎勇', '天野浩', '中村修二', '大村智', '梶田隆章',
            '大隅良典', '本庶佑', '吉野彰', '真鍋淑郎',
            '川端康成', '大江健三郎', '三島由紀夫', '谷崎潤一郎',
            '安藤忠雄', '黒澤明', '宮崎駿', '坂本龍一', '小澤征爾'
        }
        
        # 人間国宝（重要無形文化財保持者）
        self.living_national_treasures = {
            '桂米朝', '坂東玉三郎', '中村吉右衛門', '野村萬斎', '尾上菊五郎',
            '片岡仁左衛門', '中村勘九郎', '市川海老蔵', '茂山千作', '茂山千五郎'
        }
        
        # 教科書掲載人物（拡張版）
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
            'ムハンマド', 'イエス・キリスト',
            # 日本の歴史人物
            '聖徳太子', '藤原道長', '平清盛', '源頼朝', '源義経',
            '北条時宗', '足利尊氏', '足利義満', '織田信長', '豊臣秀吉',
            '徳川家康', '徳川吉宗', '西郷隆盛', '大久保利通', '木戸孝允',
            '坂本龍馬', '勝海舟', '福沢諭吉', '渋沢栄一', '伊藤博文'
        }
        
        # オリンピック金メダリスト（個別管理）
        self.olympic_gold_medalists = {
            '松本薫', '内村航平', '羽生結弦', '高橋尚子', '野口みずき',
            '北島康介', '荒川静香', '谷亮子', '野村忠宏', '井上康生',
            '吉田沙保里', '伊調馨', '室伏広治', '山下泰裕', '斉藤仁'
        }
        
        # M-1グランプリ優勝者
        self.m1_champions = {
            '中川家', 'ますだおかだ', 'フットボールアワー',
            'アンタッチャブル', 'ブラックマヨネーズ',
            'チュートリアル', 'サンドウィッチマン', 'NON STYLE',
            'パンクブーブー', 'トレンディエンジェル', '銀シャリ',
            'とろサーモン', '霜降り明星', 'ミルクボーイ',
            'マヂカルラブリー', '錦鯉', 'ウエストランド',
            '令和ロマン'
        }
        
        # M-1グランプリ決勝進出者
        self.m1_finalists = {
            'ランジャタイ', 'インディアンス', 'ゆにばーす',
            'オズワルド', 'ロングコートダディ', 'もも',
            'スーパーマラドーナ', 'ジャングルポケット',
            'かまいたち', '和牛', 'スリムクラブ', '見取り図',
            'からし蓮根', 'ギャロップ', 'ミキ', 'カミナリ'
        }
        
        # 有名バンド（拡張版）
        self.famous_bands = {
            'LUNA SEA', 'X JAPAN', 'GLAY', "L'Arc-en-Ciel",
            'B\'z', 'Mr.Children', 'DREAMS COME TRUE',
            'サザンオールスターズ', 'BUMP OF CHICKEN',
            'ONE OK ROCK', 'RADWIMPS', 'SEKAI NO OWARI',
            'King Gnu', 'Official髭男dism', 'back number',
            'UVERworld', 'MAN WITH A MISSION', '[Alexandros]',
            'BABYMETAL', 'Perfume', 'きゃりーぱみゅぱみゅ',
            'AKB48', '乃木坂46', '櫻坂46', '日向坂46',
            'TWICE', 'BTS', 'SEVENTEEN', 'Stray Kids',
            'YOASOBI', 'Ado', '優里', 'Vaundy'
        }
        
        # YouTuber（拡張版）
        self.mega_youtubers = {
            'HIKAKIN', 'はじめしゃちょー', 'フィッシャーズ',
            '東海オンエア', '水溜りボンド', 'スカイピース',
            'ヒカル', 'ラファエル', 'コムドット', 'フワちゃん',
            'エガちゃんねる', '中田敦彦', 'QuizKnock',
            '兄者弟者', 'ポッキー', 'キヨ', 'レトルト',
            'カジサック', 'ヒカキン', 'セイキン', 'マホト'
        }
        
        # 世界的漫画家
        self.world_manga_artists = {
            '鳥山明', '尾田栄一郎', '岸本斉史', '冨樫義博',
            '荒木飛呂彦', '青山剛昌', '高橋留美子', '井上雄彦',
            '諫山創', '吾峠呼世晴', '手塚治虫', '藤子不二雄',
            '石ノ森章太郎', '永井豪', '松本零士', '水木しげる'
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
        
        # 国民栄誉賞受賞者チェック（最優先）
        if self._is_national_honor_recipient(name):
            max_score = max(max_score, 8.0)
            reason = "国民栄誉賞受賞者"
        
        # 歴代総理大臣チェック
        elif self._is_prime_minister(name):
            max_score = max(max_score, 7.0)
            reason = "歴代内閣総理大臣"
        
        # 文化勲章受章者チェック
        elif self._is_culture_medal_recipient(name):
            # ノーベル賞受賞者は9.0
            if self._is_nobel_laureate(name):
                max_score = max(max_score, 9.0)
                reason = "ノーベル賞受賞者（文化勲章）"
            else:
                max_score = max(max_score, 7.5)
                reason = "文化勲章受章者"
        
        # 人間国宝チェック
        elif self._is_living_national_treasure(name):
            max_score = max(max_score, 7.0)
            reason = "人間国宝（重要無形文化財保持者）"
        
        # 教科書掲載人物チェック
        elif self._is_textbook_figure(name):
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
        
        # 漫画家チェック
        manga_status = self._check_manga_artist(name)
        if manga_status:
            score, desc = manga_status
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
    
    def _is_national_honor_recipient(self, name: str) -> bool:
        """国民栄誉賞受賞者かチェック"""
        for recipient in self.national_honor_recipients:
            if recipient in name:
                return True
        return False
    
    def _is_prime_minister(self, name: str) -> bool:
        """歴代総理大臣かチェック"""
        for pm in self.prime_ministers:
            if pm in name:
                return True
        return False
    
    def _is_culture_medal_recipient(self, name: str) -> bool:
        """文化勲章受章者かチェック"""
        for recipient in self.culture_medal_recipients:
            if recipient in name:
                return True
        return False
    
    def _is_living_national_treasure(self, name: str) -> bool:
        """人間国宝かチェック"""
        for treasure in self.living_national_treasures:
            if treasure in name:
                return True
        return False
    
    def _is_nobel_laureate(self, name: str) -> bool:
        """ノーベル賞受賞者かチェック"""
        nobel_laureates = {
            '湯川秀樹', '朝永振一郎', '江崎玲於奈', '福井謙一', '利根川進',
            '白川英樹', '野依良治', '小柴昌俊', '田中耕一', '南部陽一郎',
            '小林誠', '益川敏英', '鈴木章', '根岸英一', '山中伸弥',
            '赤崎勇', '天野浩', '中村修二', '大村智', '梶田隆章',
            '大隅良典', '本庶佑', '吉野彰', '真鍋淑郎',
            '川端康成', '大江健三郎'
        }
        for laureate in nobel_laureates:
            if laureate in name:
                return True
        return False
    
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
        for medalist in self.olympic_gold_medalists:
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
        
        # ランジャタイ等のメンバー個別チェック
        if 'ランジャタイ' in name or '伊藤幸司' in name or '国崎和也' in name:
            return (6.0, "M-1グランプリ決勝進出者（ランジャタイ）")
        if 'オズワルド' in name or '伊藤俊介' in name or '畠中悠' in name:
            return (6.0, "M-1グランプリ決勝進出者（オズワルド）")
        
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
    
    def _check_manga_artist(self, name: str) -> Optional[Tuple[float, str]]:
        """漫画家ステータスチェック"""
        
        # 世界的漫画家チェック
        for artist in self.world_manga_artists:
            if artist in name:
                # 特に有名な作品の作者は高スコア
                if artist in ['鳥山明', '尾田栄一郎', '手塚治虫']:
                    return (7.5, f"世界的漫画家（{artist}）")
                else:
                    return (6.5, f"有名漫画家（{artist}）")
        
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
    
    def get_category_minimum_scores(self) -> Dict[str, float]:
        """カテゴリ別最低スコアを取得"""
        return {
            '国民栄誉賞受賞者': 8.0,
            'ノーベル賞受賞者': 9.0,
            '文化勲章受章者': 7.5,
            '人間国宝': 7.0,
            '歴代内閣総理大臣': 7.0,
            '世界史的重要人物': 9.0,
            '教科書掲載人物': 7.0,
            'オリンピック金メダリスト': 7.0,
            'M-1グランプリ優勝者': 7.0,
            'M-1グランプリ決勝進出者': 6.0,
            '世界的漫画家': 7.5,
            '有名漫画家': 6.5,
            '有名バンドメンバー': 6.0,
            'YouTuber（100万人以上）': 6.0,
        }