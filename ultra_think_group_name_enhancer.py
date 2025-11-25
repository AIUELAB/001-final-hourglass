#!/usr/bin/env python3
"""
Ultra Think グループ名追加機能（お笑い芸人・YouTuber対応）
グループ・コンビ・ユニットの場合、Wikipedia APIでグループ名を取得して追記
"""

import pandas as pd
import re
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Set
import wikipediaapi
import requests
from pathlib import Path

# Wikipedia API設定
wiki_wiki = wikipediaapi.Wikipedia(
    user_agent='Ultra Think Database System/1.0',
    language='ja'
)

class GroupNameEnhancer:
    """グループ名を追加するクラス（お笑い芸人・YouTuber共通）"""

    def __init__(self):
        # 既存のデータベースを読み込み
        self.db_file = "groups_database.json"
        self.group_db = self.load_database()

        # Wikipedia検索キャッシュ
        self.wikipedia_cache = {}

        # 処理統計
        self.stats = {
            'comedians': {
                'total': 0,
                'group_added': 0,
                'solo': 0,
                'already_has_group': 0,
                'not_found': 0
            },
            'youtubers': {
                'total': 0,
                'group_added': 0,
                'solo': 0,
                'already_has_group': 0,
                'not_found': 0
            }
        }

        # 更新ログ
        self.update_log = []

        # 既知のグループデータベース
        self.known_groups = {
            'comedians': {
                # ぼる塾
                'あんり': 'ぼる塾',
                'きりやはるか': 'ぼる塾',
                'はるか': 'ぼる塾',
                'たむら': 'ぼる塾',
                '田村': 'ぼる塾',

                # 3時のヒロイン
                'かなで': '3時のヒロイン',
                'ゆめっち': '3時のヒロイン',
                'ふみこ': '3時のヒロイン',

                # 南海キャンディーズ
                'しずちゃん': '南海キャンディーズ',
                '山崎静代': '南海キャンディーズ',
                '山里亮太': '南海キャンディーズ',

                # トム・ブラウン
                'みちお': 'トム・ブラウン',
                '布川ひろき': 'トム・ブラウン',

                # ザ・ドリフターズ
                'いかりや長介': 'ザ・ドリフターズ',
                '高木ブー': 'ザ・ドリフターズ',
                '仲本工事': 'ザ・ドリフターズ',
                '加藤茶': 'ザ・ドリフターズ',
                '志村けん': 'ザ・ドリフターズ',

                # ダウンタウン
                '松本人志': 'ダウンタウン',
                '浜田雅功': 'ダウンタウン',

                # ナインティナイン
                '岡村隆史': 'ナインティナイン',
                '矢部浩之': 'ナインティナイン',

                # 爆笑問題
                '太田光': '爆笑問題',
                '田中裕二': '爆笑問題',

                # さまぁ〜ず
                '大竹一樹': 'さまぁ〜ず',
                '三村マサカズ': 'さまぁ〜ず',

                # オードリー
                '若林正恭': 'オードリー',
                '春日俊彰': 'オードリー',

                # サンドウィッチマン
                '伊達みきお': 'サンドウィッチマン',
                '富澤たけし': 'サンドウィッチマン',

                # 千鳥
                '大悟': '千鳥',
                'ノブ': '千鳥',

                # かまいたち
                '山内健司': 'かまいたち',
                '濱家隆一': 'かまいたち',

                # 霜降り明星
                'せいや': '霜降り明星',
                '粗品': '霜降り明星',

                # EXIT
                '兼近大樹': 'EXIT',
                'りんたろー。': 'EXIT',

                # ミルクボーイ
                '駒場孝': 'ミルクボーイ',
                '内海崇': 'ミルクボーイ',

                # 和牛
                '水田信二': '和牛',
                '川西賢志郎': '和牛',

                # とろサーモン
                '久保田かずのぶ': 'とろサーモン',
                '村田秀亮': 'とろサーモン',

                # 銀シャリ
                '鰻和弘': '銀シャリ',
                '橋本直': '銀シャリ',

                # スーパーマラドーナ
                '武智正剛': 'スーパーマラドーナ',
                '田中一彦': 'スーパーマラドーナ',

                # アインシュタイン
                '稲田直樹': 'アインシュタイン',
                '河井ゆずる': 'アインシュタイン'
            },
            'youtubers': {
                # 東海オンエア
                'てつや': '東海オンエア',
                'しばゆー': '東海オンエア',
                'りょう': '東海オンエア',
                'としみつ': '東海オンエア',
                'ゆめまる': '東海オンエア',
                '虫眼鏡': '東海オンエア',

                # フィッシャーズ
                'シルク': 'フィッシャーズ',
                'マサイ': 'フィッシャーズ',
                'ンダホ': 'フィッシャーズ',
                'モトキ': 'フィッシャーズ',
                'ザカオ': 'フィッシャーズ',
                'ペケタン': 'フィッシャーズ',

                # コムドット
                'やまと': 'コムドット',
                'ゆうた': 'コムドット',
                'ゆうま': 'コムドット',
                'ひゅうが': 'コムドット',
                'あむぎり': 'コムドット',

                # スカイピース
                'テオ': 'スカイピース',
                'じんたん': 'スカイピース',

                # 水溜りボンド
                'カンタ': '水溜りボンド',
                'トミー': '水溜りボンド',

                # QuizKnock
                '伊沢拓司': 'QuizKnock',
                '河村拓哉': 'QuizKnock',
                'ふくらP': 'QuizKnock',
                '須貝駿貴': 'QuizKnock',
                'こうちゃん': 'QuizKnock',
                '山本祥彰': 'QuizKnock',
                '林輝幸': 'QuizKnock'
            }
        }

    def load_database(self) -> Dict:
        """既存のデータベースを読み込み"""
        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                db = json.load(f)
                # Ensure required keys exist
                if 'comedians' not in db:
                    db['comedians'] = {}
                if 'youtubers' not in db:
                    db['youtubers'] = {}
                if 'metadata' not in db:
                    db['metadata'] = {}
                return db
        except FileNotFoundError:
            return {
                'comedians': {},
                'youtubers': {},
                'metadata': {}
            }

    def save_database(self):
        """更新したデータベースを保存"""
        # Ensure required keys exist
        if 'metadata' not in self.group_db:
            self.group_db['metadata'] = {}
        if 'comedians' not in self.group_db:
            self.group_db['comedians'] = {}
        if 'youtubers' not in self.group_db:
            self.group_db['youtubers'] = {}

        self.group_db['metadata']['last_updated'] = datetime.now().isoformat()
        self.group_db['metadata']['total_groups'] = (
            len(self.group_db['comedians']) + len(self.group_db['youtubers'])
        )

        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(self.group_db, f, ensure_ascii=False, indent=2)
        print(f"📁 グループデータベース更新: {self.db_file}")

    def is_comedian(self, occupation: str) -> bool:
        """お笑い芸人かどうかを判定"""
        if not occupation or pd.isna(occupation):
            return False

        keywords = ['お笑い', '芸人', 'コメディアン', 'コメディ', 'コンビ']
        return any(keyword in occupation for keyword in keywords)

    def is_youtuber(self, occupation: str) -> bool:
        """YouTuberかどうかを判定"""
        if not occupation or pd.isna(occupation):
            return False

        keywords = ['YouTuber', 'Youtuber', 'youtuber', 'ユーチューバー']
        return any(keyword in occupation for keyword in keywords)

    def extract_group_from_name(self, person_name: str) -> Optional[str]:
        """person_nameからグループ名を抽出（_で区切られている場合など）"""
        if '_' in person_name:
            parts = person_name.split('_')
            if len(parts) == 2:
                # 名前_グループ名のパターン
                return parts[1]
        return None

    def extract_group_from_display(self, display_name: str) -> Optional[str]:
        """既存のdisplay_nameからグループ名を抽出"""
        if '(' in display_name and ')' in display_name:
            match = re.search(r'\((.*?)\)$', display_name)
            if match:
                return match.group(1)
        return None

    def search_wikipedia_for_group(self, person_name: str, occupation_type: str) -> Optional[str]:
        """Wikipedia APIでグループ名を検索"""
        cache_key = f"{person_name}_{occupation_type}"

        # キャッシュチェック
        if cache_key in self.wikipedia_cache:
            return self.wikipedia_cache[cache_key]

        try:
            # レート制限対策
            time.sleep(0.5)

            # Wikipedia検索
            search_queries = []
            if occupation_type == 'comedian':
                search_queries = [
                    f"{person_name} お笑い芸人",
                    f"{person_name} コンビ",
                    f"{person_name} トリオ"
                ]
            else:  # youtuber
                search_queries = [
                    f"{person_name} YouTuber",
                    f"{person_name} ユーチューバー",
                    f"{person_name} YouTube"
                ]

            for query in search_queries:
                # Wikipedia APIでページを取得
                page = wiki_wiki.page(query)

                if page.exists():

                    # グループ名を抽出するパターン
                    patterns = [
                        r'「(.*?)」.*?メンバー',
                        r'『(.*?)』.*?メンバー',
                        r'コンビ「(.*?)」',
                        r'トリオ「(.*?)」',
                        r'グループ「(.*?)」',
                        r'ユニット「(.*?)」'
                    ]

                    for pattern in patterns:
                        match = re.search(pattern, page.text[:1000])
                        if match:
                            group_name = match.group(1)
                            self.wikipedia_cache[cache_key] = group_name
                            return group_name

        except Exception as e:
            # エラーは静かに処理
            pass

        self.wikipedia_cache[cache_key] = None
        return None

    def get_group_name(self, person_name: str, person_ja: str, occupation_type: str) -> Optional[str]:
        """人名からグループ名を取得"""
        # 既知のグループをチェック
        known_dict = self.known_groups.get(occupation_type + 's', {})

        if person_ja in known_dict:
            return known_dict[person_ja]

        if person_name in known_dict:
            return known_dict[person_name]

        # person_nameからグループ名を抽出
        extracted_group = self.extract_group_from_name(person_name)
        if extracted_group:
            return extracted_group

        # データベースをチェック
        db_section = self.group_db.get(occupation_type + 's', {})
        if person_ja in db_section:
            return db_section[person_ja].get('group')

        # Wikipedia検索
        group = self.search_wikipedia_for_group(person_ja, occupation_type) or \
                self.search_wikipedia_for_group(person_name, occupation_type)

        if group:
            # データベースに追加
            db_section[person_ja] = {
                'name': person_name,
                'group': group,
                'type': occupation_type,
                'source': 'wikipedia',
                'added': datetime.now().isoformat()
            }
            self.group_db[occupation_type + 's'] = db_section
            return group

        return None

    def is_solo_performer(self, person_name: str, person_ja: str, occupation_type: str) -> bool:
        """ソロパフォーマーかどうかを判定"""
        # ソロを示すキーワード
        solo_keywords = ['ピン芸人', 'ソロ', '個人', '単独']

        # グループ名の抽出を試みる
        group_name = self.extract_group_from_name(person_name)
        if not group_name:
            # グループ名が見つからない場合はソロの可能性が高い
            return True

        return False

    def enhance_with_group_name(self, row: pd.Series) -> Tuple[str, str, str]:
        """グループ名を追加（お笑い芸人・YouTuber共通）"""
        display_name = row['person_name_display']
        person_name = row['person_name']
        person_ja = row.get('person_name_ja', '')
        occupation = row.get('occupation', '')

        # 職業タイプを判定
        occupation_type = None
        stats_key = None

        if self.is_comedian(occupation):
            occupation_type = 'comedian'
            stats_key = 'comedians'
        elif self.is_youtuber(occupation):
            occupation_type = 'youtuber'
            stats_key = 'youtubers'
        else:
            return display_name, 'not_applicable', None

        self.stats[stats_key]['total'] += 1

        # 既にグループ名が含まれている場合
        existing_group = self.extract_group_from_display(display_name)
        if existing_group:
            self.stats[stats_key]['already_has_group'] += 1
            return display_name, 'already_has_group', stats_key

        # ソロパフォーマーの判定
        if self.is_solo_performer(person_name, person_ja, occupation_type):
            self.stats[stats_key]['solo'] += 1
            return display_name, 'solo', stats_key

        # グループ名を取得
        group_name = self.get_group_name(person_name, person_ja, occupation_type)

        if group_name:
            # 外国語名を日本語に変換（先に日本語名を使用）
            base_name = person_ja if person_ja and not pd.isna(person_ja) else display_name

            # グループ名がすでに名前に含まれている場合はスキップ
            if group_name not in base_name:
                new_display_name = f"{base_name} ({group_name})"
            else:
                new_display_name = base_name

            self.stats[stats_key]['group_added'] += 1
            self.update_log.append({
                'person_id': row.get('person_id', ''),
                'original': display_name,
                'updated': new_display_name,
                'group': group_name,
                'type': occupation_type
            })
            return new_display_name, 'group_added', stats_key

        self.stats[stats_key]['not_found'] += 1
        return display_name, 'not_found', stats_key

    def process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """データフレーム全体を処理"""
        print("👥 グループ名の追加を開始...")

        # お笑い芸人とYouTuberを処理
        target_mask = df['occupation'].apply(
            lambda x: self.is_comedian(x) or self.is_youtuber(x)
        )
        target_rows = df[target_mask]

        print(f"   対象者数: {len(target_rows)}件")
        print(f"   - お笑い芸人: 約{df['occupation'].apply(self.is_comedian).sum()}件")
        print(f"   - YouTuber: 約{df['occupation'].apply(self.is_youtuber).sum()}件")

        # 各行を処理
        processed = 0
        for idx in target_rows.index:
            processed += 1

            new_display_name, status, category = self.enhance_with_group_name(df.loc[idx])

            # 更新が必要な場合
            if status == 'group_added':
                df.at[idx, 'person_name_display'] = new_display_name

            # 進捗表示
            if processed % 20 == 0:
                print(f"  処理中... {processed} / {len(target_rows)}")

        # データベースを保存
        self.save_database()

        return df

    def generate_report(self) -> str:
        """処理レポートを生成"""
        report = []
        report.append("# Ultra Think グループ名追加レポート")
        report.append(f"\n生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # お笑い芸人の統計
        report.append("\n## 🎭 お笑い芸人")
        c_stats = self.stats['comedians']
        report.append(f"- 総処理数: {c_stats['total']}件")
        report.append(f"- グループ名追加: {c_stats['group_added']}件")
        report.append(f"- ソロ芸人: {c_stats['solo']}件")
        report.append(f"- 既にグループ名あり: {c_stats['already_has_group']}件")
        report.append(f"- グループ名不明: {c_stats['not_found']}件")

        # YouTuberの統計
        report.append("\n## 📹 YouTuber")
        y_stats = self.stats['youtubers']
        report.append(f"- 総処理数: {y_stats['total']}件")
        report.append(f"- グループ名追加: {y_stats['group_added']}件")
        report.append(f"- ソロ活動: {y_stats['solo']}件")
        report.append(f"- 既にグループ名あり: {y_stats['already_has_group']}件")
        report.append(f"- グループ名不明: {y_stats['not_found']}件")

        if self.update_log:
            report.append("\n## 📝 更新詳細（最初の20件）")
            for log in self.update_log[:20]:
                report.append(f"\n### {log['person_id']} ({log['type']})")
                report.append(f"- 元の表示名: {log['original']}")
                report.append(f"- 更新後: {log['updated']}")
                report.append(f"- グループ名: {log['group']}")

        report.append("\n## ✅ 処理完了")
        report.append("お笑い芸人とYouTuberへのグループ名追加が完了しました。")

        return '\n'.join(report)


def apply_group_name_rules(csv_file: str = None) -> pd.DataFrame:
    """グループ名追加ルールを適用"""
    # CSVファイルの読み込み
    if csv_file is None:
        csv_file = "ultra_think_CONVERTED_20250827_224054.csv"

    print(f"📂 CSVファイル読み込み: {csv_file}")
    df = pd.read_csv(csv_file, encoding='utf-8')

    # 処理実行
    enhancer = GroupNameEnhancer()
    df_enhanced = enhancer.process_dataframe(df)

    # 結果を保存
    output_file = csv_file.replace('.csv', '_group_enhanced.csv')
    df_enhanced.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\n💾 更新済みデータを保存: {output_file}")

    # レポート生成
    report = enhancer.generate_report()
    report_file = f"GROUP_NAME_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"📋 レポート生成: {report_file}")

    return df_enhanced


def apply_to_new_data(new_data: pd.DataFrame) -> pd.DataFrame:
    """新規追加データにグループ名ルールを適用"""
    enhancer = GroupNameEnhancer()
    return enhancer.process_dataframe(new_data)


if __name__ == "__main__":
    print("=" * 60)
    print("👥 Ultra Think グループ名追加（お笑い芸人・YouTuber）")
    print("=" * 60)

    # ルールを適用
    df_result = apply_group_name_rules()

    print("\n✅ 処理完了！")
