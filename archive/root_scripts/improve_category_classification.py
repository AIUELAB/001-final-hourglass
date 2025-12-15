#!/usr/bin/env python3
"""
カテゴリ分類を改善するスクリプト
"""

import pandas as pd
import re
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CategoryImprover:
    """カテゴリ分類改善クラス"""

    def __init__(self, input_file: str):
        """初期化"""
        self.input_file = input_file
        self.df = pd.read_csv(input_file, encoding='utf-8-sig')
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.improvements = 0

        # 詳細なカテゴリマッピング
        self.detailed_mappings = {
            'スポーツ': {
                'keywords': ['選手', 'オリンピック', 'メダリスト', 'チャンピオン', '監督', 'コーチ'],
                'sports': ['野球', 'サッカー', 'ボクサー', '力士', '格闘', 'ゴルフ', 'テニス', 'フィギュア',
                          '水泳', '陸上', 'バスケ', 'バレー', 'ラグビー', '卓球', 'バドミントン', '体操',
                          'レスリング', '柔道', '空手', '剣道', 'ボクシング', 'UFC', 'K-1', 'RIZIN',
                          'プロレス', 'スケート', 'スキー', 'マラソン', '駅伝', '相撲'],
                'names': ['フロイド・メイウェザー', 'マイク・タイソン', 'モハメド・アリ', 'ベーブ・ルース',
                         'マイケル・ジョーダン', 'タイガー・ウッズ', 'ロナウド', 'メッシ', '大谷翔平',
                         'イチロー', '松井秀喜', '王貞治', '長嶋茂雄', '野村克也']
            },

            'エンタメ': {
                'keywords': ['俳優', '女優', '歌手', 'アイドル', 'タレント', '芸人', 'お笑い', 'コメディアン',
                            'モデル', 'グラビア', 'アナウンサー', 'MC', '司会', 'ミュージシャン', 'バンド',
                            'DJ', 'プロデューサー', '演出家', '声優', 'ナレーター', 'ラジオ', 'パーソナリティ'],
                'groups': ['YOASOBI', 'SEKAI NO OWARI', 'Official髭男dism', 'King & Prince', 'Snow Man',
                          'SixTONES', 'なにわ男子', 'BTS', 'TWICE', '乃木坂', '櫻坂', '日向坂', 'AKB',
                          'DREAMS COME TRUE', 'サザンオールスターズ', 'Mr.Children', 'RADWIMPS',
                          'ONE OK ROCK', 'BUMP OF CHICKEN', 'ジャニーズ', 'EXILE', '三代目', 'GENERATIONS'],
                'channels': ['YouTuber', 'TikToker', 'インフルエンサー', 'VTuber', 'ストリーマー']
            },

            '文化・芸術': {
                'keywords': ['作家', '小説家', '詩人', '画家', '彫刻家', '写真家', '建築家', 'デザイナー',
                            'イラストレーター', '漫画家', 'アニメーター', '映画監督', '脚本家', '作曲家',
                            '指揮者', '演奏家', 'ピアニスト', 'バイオリニスト', '書道家', '陶芸家',
                            '華道', '茶道', '美術', '芸術', '文学', '音楽家', 'アーティスト'],
                'names': ['武満徹', '相田みつを', '草間彌生', '村上春樹', '宮崎駿', '新海誠', '手塚治虫',
                         '鳥山明', '尾田栄一郎', '諫山創', '坂本龍一', '久石譲', 'YMO', '細野晴臣']
            },

            '歴史': {
                'keywords': ['天皇', '将軍', '武将', '大名', '侍', '幕末', '明治', '大正', '昭和', '戦国',
                            '平安', '鎌倉', '室町', '江戸', '維新', '志士', '軍人', '提督', '元帥', '皇族',
                            '皇后', '親王', '内親王', '公家', '藩主'],
                'eras': ['古代', '中世', '近世', '近代'],
                'names': ['織田信長', '豊臣秀吉', '徳川家康', '坂本龍馬', '西郷隆盛', '福沢諭吉']
            },

            '科学・技術': {
                'keywords': ['科学者', '研究者', '数学者', '物理学者', '化学者', '生物学者', '医学者',
                            '医師', '博士', 'ノーベル賞', '発明家', 'エンジニア', 'プログラマー',
                            '宇宙飛行士', 'AI研究者', 'ロボット', '開発者', 'IT', 'テクノロジー'],
                'names': ['山中伸弥', '本庶佑', '大村智', '梶田隆章', '大隅良典', '真鍋淑郎']
            },

            'ビジネス': {
                'keywords': ['実業家', '起業家', '経営者', 'CEO', '社長', '会長', '創業者', '投資家',
                            'ベンチャー', 'スタートアップ', '財界', '経済', '企業家', 'ファウンダー',
                            '経営コンサルタント', 'ビジネス'],
                'companies': ['ソフトバンク', '楽天', 'ユニクロ', 'トヨタ', 'ソニー', 'ホンダ',
                             'パナソニック', '任天堂', 'DeNA', 'メルカリ', 'LINE', 'サイバーエージェント'],
                'names': ['孫正義', '三木谷浩史', '柳井正', '稲盛和夫', '松下幸之助', '本田宗一郎']
            },

            '政治': {
                'keywords': ['政治家', '首相', '総理', '大臣', '知事', '市長', '議員', '大統領', '国王',
                            '女王', '皇帝', '外交官', '国連', '政府', '内閣', '国会', '参議院', '衆議院'],
                'names': ['安倍晋三', '岸田文雄', '小泉純一郎', '田中角栄', '吉田茂', '中曽根康弘']
            },

            '宗教・思想': {
                'keywords': ['宗教家', '僧侶', '神父', '牧師', '哲学者', '思想家', '教育者', '活動家',
                            '住職', '神主', '宮司', '教祖', '聖人', '高僧', '禅師'],
                'names': ['空海', '最澄', '親鸞', '道元', '日蓮', '一休']
            },

            '犯罪・事件': {
                'keywords': ['犯罪者', '殺人犯', 'テロリスト', '詐欺師', '事件', '犯人', '容疑者',
                            '死刑囚', '服役', '逮捕', '指名手配', 'サイコキラー', '連続殺人'],
                'names': ['テッド・カジンスキー', 'ユナボマー', 'エドワード・スノーデン']
            }
        }

        logger.info("="*60)
        logger.info("📊 カテゴリ分類改善処理開始")
        logger.info("="*60)
        logger.info(f"入力ファイル: {input_file}")
        logger.info(f"レコード数: {len(self.df)}")

    def improve_category(self, row) -> str:
        """より詳細なカテゴリ判定"""

        # 既存の情報を取得
        current_category = row.get('category', 'その他')
        name = str(row.get('person_name_ja', ''))
        display_name = str(row.get('person_name_display', ''))
        occupation = str(row.get('occupation', '')).lower()
        description = str(row.get('description', '')).lower()
        evaluation = str(row.get('evaluation_reason', '')).lower()

        # すべての情報を結合
        combined_text = f"{name} {display_name} {occupation} {description} {evaluation}".lower()

        # スコアベースの判定
        category_scores = {}

        for category, patterns in self.detailed_mappings.items():
            score = 0

            # キーワードマッチング
            if 'keywords' in patterns:
                for keyword in patterns['keywords']:
                    if keyword.lower() in combined_text:
                        score += 10

            # 特定分野のキーワード
            for key in ['sports', 'groups', 'channels', 'eras', 'companies']:
                if key in patterns:
                    for term in patterns[key]:
                        if term.lower() in combined_text:
                            score += 15

            # 特定の名前
            if 'names' in patterns:
                for famous_name in patterns['names']:
                    if famous_name in name or famous_name in display_name:
                        score += 100  # 名前が一致したら確定的

            if score > 0:
                category_scores[category] = score

        # 最高スコアのカテゴリを選択
        if category_scores:
            best_category = max(category_scores, key=category_scores.get)
            if category_scores[best_category] >= 10:  # 閾値
                return best_category

        # 特別なケース
        if '国民栄誉賞' in combined_text:
            # 国民栄誉賞受賞者は個別判定
            if any(k in combined_text for k in ['野球', '相撲', 'オリンピック', 'マラソン']):
                return 'スポーツ'
            elif any(k in combined_text for k in ['歌', '俳優', '女優', '映画']):
                return 'エンタメ'
            elif any(k in combined_text for k in ['作曲', '指揮']):
                return '文化・芸術'

        return current_category  # 変更なし

    def improve_nationality(self, row) -> str:
        """国籍判定の改善"""
        name = str(row.get('person_name_ja', ''))
        current_nationality = row.get('nationality', '日本')

        # 特定の国籍パターン
        nationality_patterns = {
            'アメリカ': ['ジョン', 'マイケル', 'ロバート', 'ウィリアム', 'デイビッド', 'ジェームズ',
                       'ドナルド', 'ジョージ', 'リチャード', 'チャールズ', 'トム', 'ビル'],
            'イギリス': ['エリザベス', 'チャールズ', 'ウィリアム', 'ハリー', 'ジョージ', 'ビクトリア'],
            'フランス': ['ジャン', 'ピエール', 'フランソワ', 'ルイ', 'マリー', 'ジャック', 'ミシェル'],
            'ドイツ': ['ヨハン', 'ハンス', 'カール', 'フリードリヒ', 'ヴィルヘルム', 'オットー'],
            'イタリア': ['ジョバンニ', 'マルコ', 'パオロ', 'ルイジ', 'フランチェスコ', 'アントニオ'],
            'スペイン': ['ホセ', 'カルロス', 'フアン', 'ペドロ', 'フェルナンド', 'アントニオ'],
            'ロシア': ['ウラジミール', 'ミハイル', 'アレクサンドル', 'ニコライ', 'イワン', 'セルゲイ'],
            '中国': ['習', '王', '李', '張', '陳', '劉', '毛', '鄧'],
            '韓国': ['キム', 'パク', 'イ', 'チェ', 'チョン', 'カン', 'ユン', 'ソン']
        }

        # パターンマッチング
        for country, patterns in nationality_patterns.items():
            for pattern in patterns:
                if pattern in name:
                    return country

        # カタカナのみで構成されている場合
        if re.match(r'^[ァ-ヾ・\s]+$', name):
            if current_nationality == '外国':
                # より具体的な国籍を推測
                return 'アメリカ'  # デフォルトで最も可能性が高い
            return current_nationality

        # 漢字またはひらがなが含まれる
        if re.search(r'[\u4e00-\u9fff\u3040-\u309f]', name):
            return '日本'

        return current_nationality

    def process(self):
        """改善処理を実行"""
        logger.info("\n📝 カテゴリ改善処理開始")

        improved_data = []

        for idx, row in self.df.iterrows():
            if idx % 100 == 0:
                logger.info(f"  処理中: {idx}/{len(self.df)}")

            row_dict = row.to_dict()

            # カテゴリ改善
            old_category = row_dict.get('category', 'その他')
            new_category = self.improve_category(row_dict)
            if new_category != old_category:
                self.improvements += 1
                row_dict['category'] = new_category

            # 国籍改善
            old_nationality = row_dict.get('nationality', '日本')
            new_nationality = self.improve_nationality(row_dict)
            if new_nationality != old_nationality and new_nationality != '外国':
                row_dict['nationality'] = new_nationality

            improved_data.append(row_dict)

        self.df_improved = pd.DataFrame(improved_data)
        logger.info(f"✅ 改善完了: {self.improvements}件のカテゴリを修正")

    def save_results(self):
        """結果を保存"""
        output_file = f"database_category_improved_{self.timestamp}.csv"

        # UTF-8 BOM付きで保存
        self.df_improved.to_csv(output_file, index=False, encoding='utf-8-sig')

        logger.info(f"\n💾 出力ファイル: {output_file}")

        # 統計情報
        logger.info("\n📊 改善後のカテゴリ別統計:")
        category_counts = self.df_improved['category'].value_counts()
        for cat, count in category_counts.items():
            percentage = (count / len(self.df_improved)) * 100
            logger.info(f"  {cat}: {count}名 ({percentage:.1f}%)")

        # 「その他」の割合を確認
        others_count = category_counts.get('その他', 0)
        others_percentage = (others_count / len(self.df_improved)) * 100

        if others_percentage > 90:
            logger.warning(f"⚠️ 「その他」カテゴリが{others_percentage:.1f}%と高すぎます")
            logger.info("  より詳細なカテゴリ分類が必要です")

        return output_file

def main():
    """メイン処理"""
    import glob

    # 最新の変換済みファイルを取得
    db_files = glob.glob("database_episode_format_*.csv")
    if not db_files:
        logger.error("変換済みデータベースファイルが見つかりません")
        return

    latest_db = sorted(db_files)[-1]
    logger.info(f"対象ファイル: {latest_db}")

    # 改善処理実行
    improver = CategoryImprover(latest_db)
    improver.process()
    output_file = improver.save_results()

    logger.info("\n" + "="*60)
    logger.info("✅ カテゴリ改善処理完了")
    logger.info("="*60)
    logger.info(f"改善件数: {improver.improvements}")
    logger.info(f"出力ファイル: {output_file}")

if __name__ == "__main__":
    main()
