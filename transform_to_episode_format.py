#!/usr/bin/env python3
"""
データベースをultra_think_EPISODE_FINALフォーマットに変換
"""

import pandas as pd
import re
import logging
from datetime import datetime
from pathlib import Path
import unicodedata

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseTransformer:
    """データベース変換クラス"""
    
    def __init__(self, input_file: str):
        """初期化"""
        self.input_file = input_file
        self.df = pd.read_csv(input_file, encoding='utf-8-sig')
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # カテゴリマッピング
        self.category_mappings = {
            'スポーツ': ['選手', 'オリンピック', 'メダリスト', 'チャンピオン', '監督', 'コーチ', '野球', 'サッカー', 'ボクサー', '力士', '格闘', 'ゴルフ', 'テニス', 'フィギュア', '水泳', '陸上', 'バスケ', 'バレー', 'ラグビー', '卓球', 'バドミントン', '体操', 'レスリング', '柔道', '空手', '剣道'],
            'エンタメ': ['俳優', '女優', '歌手', 'アイドル', 'タレント', '芸人', 'お笑い', 'コメディアン', 'モデル', 'グラビア', 'アナウンサー', 'MC', '司会', 'YouTuber', 'TikToker', 'インフルエンサー', 'VTuber', 'ミュージシャン', 'バンド', 'DJ', 'プロデューサー', '演出家'],
            '文化・芸術': ['作家', '小説家', '詩人', '画家', '彫刻家', '写真家', '建築家', 'デザイナー', 'イラストレーター', '漫画家', 'アニメーター', '映画監督', '脚本家', '作曲家', '指揮者', '演奏家', 'ピアニスト', 'バイオリニスト', '書道家', '陶芸家', '華道', '茶道'],
            '歴史': ['天皇', '将軍', '武将', '大名', '侍', '幕末', '明治', '大正', '昭和', '戦国', '平安', '鎌倉', '室町', '江戸', '維新', '志士', '軍人', '提督'],
            '科学・技術': ['科学者', '研究者', '数学者', '物理学者', '化学者', '生物学者', '医学者', '医師', '博士', 'ノーベル賞', '発明家', 'エンジニア', 'プログラマー', '宇宙飛行士', 'AI研究者', 'ロボット'],
            'ビジネス': ['実業家', '起業家', '経営者', 'CEO', '社長', '会長', '創業者', '投資家', 'ベンチャー', 'スタートアップ', '財界', '経済'],
            '政治': ['政治家', '首相', '大臣', '知事', '市長', '議員', '大統領', '国王', '女王', '皇帝', '外交官', '国連'],
            '宗教・思想': ['宗教家', '僧侶', '神父', '牧師', '哲学者', '思想家', '教育者', '活動家'],
            '犯罪・事件': ['犯罪者', '殺人犯', 'テロリスト', '詐欺師', '事件', '犯人']
        }
        
        # グループ名パターン（括弧で表示される）
        self.group_patterns = [
            (r'YOASOBI', ['Ayase', 'ikura']),
            (r'SEKAI NO OWARI', ['Fukase', 'Nakajin', 'Saori', 'DJ LOVE']),
            (r'Official髭男dism', ['藤原聡', '小笹大輔', '楢崎誠', '松浦匡希']),
            (r'King & Prince', ['平野紫耀', '永瀬廉', '高橋海人', '岸優太', '神宮寺勇太']),
            (r'Snow Man', ['深澤辰哉', '佐久間大介', '渡辺翔太', '宮舘涼太', '岩本照', '阿部亮平', '向井康二', '目黒蓮', 'ラウール']),
            (r'SixTONES', ['ジェシー', '京本大我', '松村北斗', '髙地優吾', '森本慎太郎', '田中樹']),
            (r'なにわ男子', ['西畑大吾', '大西流星', '道枝駿佑', '高橋恭平', '長尾謙杜', '藤原丈一郎', '大橋和也']),
            (r'BTS', ['RM', 'Jin', 'SUGA', 'J-Hope', 'Jimin', 'V', 'Jungkook']),
            (r'TWICE', ['ナヨン', 'ジョンヨン', 'モモ', 'サナ', 'ジヒョ', 'ミナ', 'ダヒョン', 'チェヨン', 'ツウィ']),
            (r'乃木坂46', ['秋元真夏', '生田絵梨花', '齋藤飛鳥', '与田祐希', '山下美月', '遠藤さくら', '賀喜遥香']),
            (r'櫻坂46', ['菅井友香', '土生瑞穂', '小林由依', '田村保乃', '藤吉夏鈴', '森田ひかる']),
            (r'日向坂46', ['佐々木久美', '佐々木美玲', '加藤史帆', '小坂菜緒', '金村美玖', '河田陽菜']),
            (r'AKB48', ['柏木由紀', '岡田奈々', '向井地美音', '小栗有以']),
            (r'DREAMS COME TRUE', ['吉田美和', '中村正人']),
            (r'サザンオールスターズ', ['桑田佳祐', '原由子', '関口和之', '松田弘', '野沢秀行']),
            (r'Mr.Children', ['桜井和寿', '田原健一', '中川敬輔', '鈴木英哉']),
            (r'RADWIMPS', ['野田洋次郎', '桑原彰', '武田祐介']),
            (r'ONE OK ROCK', ['Taka', 'Toru', 'Ryota', 'Tomoya']),
            (r'BUMP OF CHICKEN', ['藤原基央', '増川弘明', '直井由文', '升秀夫']),
        ]
        
        logger.info("="*60)
        logger.info("📊 データベース変換処理開始")
        logger.info("="*60)
        logger.info(f"入力ファイル: {input_file}")
        logger.info(f"レコード数: {len(self.df)}")
        
    def determine_category(self, row) -> str:
        """カテゴリを判定"""
        occupation = str(row.get('occupation', '')).lower()
        description = str(row.get('description', '')).lower()
        category_col = str(row.get('category', '')).lower()
        
        combined_text = f"{occupation} {description} {category_col}"
        
        # カテゴリマッピングでチェック
        for category, keywords in self.category_mappings.items():
            for keyword in keywords:
                if keyword.lower() in combined_text:
                    return category
        
        # デフォルト
        return 'その他'
    
    def determine_nationality(self, name: str) -> str:
        """国籍を判定"""
        # カタカナのみの名前は外国人の可能性が高い
        if re.match(r'^[ァ-ヾ・\s]+$', name):
            # 特定のパターンで国籍判定
            if any(k in name for k in ['ジョン', 'マイケル', 'ロバート', 'ウィリアム', 'デイビッド', 'ジェームズ']):
                return 'アメリカ'
            elif any(k in name for k in ['ジャン', 'ピエール', 'フランソワ', 'ルイ', 'マリー']):
                return 'フランス'
            elif any(k in name for k in ['ヨハン', 'ハンス', 'カール', 'フリードリヒ']):
                return 'ドイツ'
            elif any(k in name for k in ['ホセ', 'カルロス', 'フアン', 'ペドロ']):
                return 'スペイン'
            elif any(k in name for k in ['ジョバンニ', 'マルコ', 'パオロ', 'ルイジ']):
                return 'イタリア'
            elif any(k in name for k in ['王', '李', '張', '陳', '劉']):
                return '中国'
            elif any(k in name for k in ['キム', 'パク', 'イ', 'チェ', 'チョン']):
                return '韓国'
            else:
                return '外国'  # 国籍不明の外国人
        
        # 漢字が含まれていれば日本人
        if re.search(r'[\u4e00-\u9fff]', name):
            return '日本'
        
        # ひらがなが含まれていれば日本人
        if re.search(r'[\u3040-\u309f]', name):
            return '日本'
        
        return '日本'  # デフォルト
    
    def romanize_japanese(self, name: str) -> str:
        """日本語名をローマ字に変換"""
        # 簡易的なローマ字変換テーブル
        romanization = {
            'あ': 'a', 'い': 'i', 'う': 'u', 'え': 'e', 'お': 'o',
            'か': 'ka', 'き': 'ki', 'く': 'ku', 'け': 'ke', 'こ': 'ko',
            'が': 'ga', 'ぎ': 'gi', 'ぐ': 'gu', 'げ': 'ge', 'ご': 'go',
            'さ': 'sa', 'し': 'shi', 'す': 'su', 'せ': 'se', 'そ': 'so',
            'ざ': 'za', 'じ': 'ji', 'ず': 'zu', 'ぜ': 'ze', 'ぞ': 'zo',
            'た': 'ta', 'ち': 'chi', 'つ': 'tsu', 'て': 'te', 'と': 'to',
            'だ': 'da', 'ぢ': 'ji', 'づ': 'zu', 'で': 'de', 'ど': 'do',
            'な': 'na', 'に': 'ni', 'ぬ': 'nu', 'ね': 'ne', 'の': 'no',
            'は': 'ha', 'ひ': 'hi', 'ふ': 'fu', 'へ': 'he', 'ほ': 'ho',
            'ば': 'ba', 'び': 'bi', 'ぶ': 'bu', 'べ': 'be', 'ぼ': 'bo',
            'ぱ': 'pa', 'ぴ': 'pi', 'ぷ': 'pu', 'ぺ': 'pe', 'ぽ': 'po',
            'ま': 'ma', 'み': 'mi', 'む': 'mu', 'め': 'me', 'も': 'mo',
            'や': 'ya', 'ゆ': 'yu', 'よ': 'yo',
            'ら': 'ra', 'り': 'ri', 'る': 'ru', 'れ': 're', 'ろ': 'ro',
            'わ': 'wa', 'を': 'wo', 'ん': 'n',
            'ー': '-', '・': ' '
        }
        
        # カタカナをひらがなに変換
        name_hiragana = ''
        for char in name:
            if 'ァ' <= char <= 'ヾ':
                # カタカナをひらがなに変換
                char = chr(ord(char) - ord('ァ') + ord('ぁ'))
            name_hiragana += char
        
        # ひらがなをローマ字に変換
        result = ''
        for char in name_hiragana:
            if char in romanization:
                result += romanization[char]
            elif char == ' ' or char == '　':
                result += ' '
            else:
                result += char
        
        return result
    
    def get_display_name(self, name: str) -> str:
        """表示名を取得（グループ名付き）"""
        # グループメンバーかチェック
        for group_name, members in self.group_patterns:
            for member in members:
                if member in name or name in member:
                    return f"{name} ({group_name})"
        
        # 既に括弧がある場合はそのまま
        if '(' in name and ')' in name:
            return name
        
        # 特定のパターン（所属が明確な場合）
        if 'AKB' in name or 'SKE' in name or 'NMB' in name or 'HKT' in name:
            # アイドルグループメンバー
            return name
        
        return name
    
    def get_person_name(self, name: str, nationality: str) -> str:
        """言語表記の名前を取得"""
        if nationality == '日本':
            # 日本人名はローマ字変換
            return self.romanize_japanese(name)
        else:
            # 外国人名はそのまま（またはカタカナから推測）
            # ここでは簡易的にカタカナをそのままローマ字風に
            return name.replace('・', ' ')
    
    def transform(self):
        """データベースを変換"""
        logger.info("\n📝 変換処理開始")
        
        # 新しいカラムを追加
        transformed_data = []
        
        for idx, row in self.df.iterrows():
            if idx % 100 == 0:
                logger.info(f"  処理中: {idx}/{len(self.df)}")
            
            name = row['name']
            
            # カテゴリ判定
            category = self.determine_category(row)
            
            # 国籍判定
            nationality = self.determine_nationality(name)
            
            # 職業（既存のoccupationを使用、なければdescriptionから）
            occupation = row.get('occupation', '')
            if pd.isna(occupation) or occupation == '':
                occupation = row.get('description', '').split('、')[0] if pd.notna(row.get('description')) else ''
            
            # person_name（言語表記）
            person_name = self.get_person_name(name, nationality)
            
            # person_name_display（表示名）
            person_name_display = self.get_display_name(name)
            
            # person_name_ja（日本語名）
            person_name_ja = name
            
            # 新しい行を作成
            new_row = row.to_dict()
            new_row['category'] = category
            new_row['nationality'] = nationality
            new_row['occupation'] = occupation
            new_row['person_name'] = person_name
            new_row['person_name_display'] = person_name_display
            new_row['person_name_ja'] = person_name_ja
            
            # nameカラムは削除（person_name_displayに置き換え）
            if 'name' in new_row:
                del new_row['name']
            
            transformed_data.append(new_row)
        
        # データフレーム作成
        self.df_transformed = pd.DataFrame(transformed_data)
        
        # カラムの順序を調整（ultra_think_EPISODE_FINALの順序に近づける）
        column_order = [
            'person_id',
            'person_name',
            'person_name_display', 
            'person_name_ja',
            'category',
            'nationality', 
            'occupation',
            'recognition_score',
            'wikipedia_found',
            'wikipedia_page',
            'description',
            'evaluation_reason',
            'protected',
            'source',
            'added_date',
            'should_delete',
            'reason',
            'old_score',
            'improvement',
            'original_score',
            'score_improvement',
            'original_min_score',
            'api_details'
        ]
        
        # 存在するカラムのみを並び替え
        existing_columns = [col for col in column_order if col in self.df_transformed.columns]
        self.df_transformed = self.df_transformed[existing_columns]
        
        logger.info(f"✅ 変換完了: {len(self.df_transformed)}件")
        
    def save_results(self):
        """結果を保存"""
        output_file = f"database_episode_format_{self.timestamp}.csv"
        
        # UTF-8 BOM付きで保存（Excel対応）
        self.df_transformed.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        logger.info(f"\n💾 出力ファイル: {output_file}")
        
        # 統計情報
        logger.info("\n📊 カテゴリ別統計:")
        category_counts = self.df_transformed['category'].value_counts()
        for cat, count in category_counts.items():
            logger.info(f"  {cat}: {count}名")
        
        logger.info("\n🌍 国籍別統計:")
        nationality_counts = self.df_transformed['nationality'].value_counts().head(10)
        for nat, count in nationality_counts.items():
            logger.info(f"  {nat}: {count}名")
        
        # サンプル出力
        logger.info("\n📋 変換サンプル（最初の5件）:")
        sample_cols = ['person_id', 'person_name_display', 'category', 'nationality']
        for idx, row in self.df_transformed.head(5).iterrows():
            logger.info(f"  {row['person_id']}: {row['person_name_display']} ({row['category']}, {row['nationality']})")
        
        return output_file

def main():
    """メイン処理"""
    import glob
    
    # 最新のデータベースファイルを取得
    db_file = 'database_fixed_20250910_104141.csv'
    
    if not Path(db_file).exists():
        # 他のファイルを探す
        db_files = glob.glob("database_fixed_*.csv")
        if db_files:
            db_file = sorted(db_files)[-1]
        else:
            logger.error("変換対象のデータベースファイルが見つかりません")
            return
    
    logger.info(f"対象ファイル: {db_file}")
    
    # 変換実行
    transformer = DatabaseTransformer(db_file)
    transformer.transform()
    output_file = transformer.save_results()
    
    logger.info("\n" + "="*60)
    logger.info("✅ 変換処理完了")
    logger.info("="*60)
    logger.info(f"出力ファイル: {output_file}")
    logger.info("新しいフォーマットでデータベースが作成されました")

if __name__ == "__main__":
    main()