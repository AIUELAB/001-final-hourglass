#!/usr/bin/env python3
"""
Ultra Think 架空キャラクター作品名追加機能
occupationが架空キャラクターの場合、Wikipedia APIで作品名を取得して追記
"""

import pandas as pd
import re
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import wikipediaapi
import requests
from pathlib import Path

# Wikipedia API設定
wiki_wiki = wikipediaapi.Wikipedia(
    user_agent='Ultra Think Database System/1.0',
    language='ja'
)

class FictionalCharacterEnhancer:
    """架空キャラクターに作品名を追加するクラス"""

    def __init__(self):
        # 既存のデータベースを読み込み
        self.db_file = "fictional_characters_database.json"
        self.character_db = self.load_database()

        # キャッシュ（API呼び出し削減）
        self.wikipedia_cache = {}

        # 処理統計
        self.stats = {
            'total_processed': 0,
            'work_added': 0,
            'already_has_work': 0,
            'wikipedia_found': 0,
            'from_database': 0,
            'not_found': 0
        }

        # 更新ログ
        self.update_log = []

        # 既知の作品名マッピング（よく知られているキャラクター）
        self.known_works = {
            'うずまきナルト': 'NARUTO',
            'うちはサスケ': 'NARUTO',
            'アムロ・レイ': '機動戦士ガンダム',
            'シャア・アズナブル': '機動戦士ガンダム',
            'エドワード・エルリック': '鋼の錬金術師',
            'アルフォンス・エルリック': '鋼の錬金術師',
            'アーニャ・フォージャー': 'SPY×FAMILY',
            'ロイド・フォージャー': 'SPY×FAMILY',
            'ヨル・フォージャー': 'SPY×FAMILY',
            'エレン・イェーガー': '進撃の巨人',
            'Eren Yeager': '進撃の巨人',
            'ミカサ・アッカーマン': '進撃の巨人',

            # NARUTO
            'うずまきナルト': 'NARUTO',
            'Uzumaki Naruto': 'NARUTO',
            'うちはサスケ': 'NARUTO',
            '春野サクラ': 'NARUTO',
            'はたけカカシ': 'NARUTO',
            '我愛羅': 'NARUTO',
            'うちはイタチ': 'NARUTO',
            '自来也': 'NARUTO',
            '綱手': 'NARUTO',
            '大蛇丸': 'NARUTO',

            'ルフィ': 'ONE PIECE',
            'モンキー・D・ルフィ': 'ONE PIECE',
            'ゾロ': 'ONE PIECE',
            'ロロノア・ゾロ': 'ONE PIECE',
            'ナミ': 'ONE PIECE',
            'サンジ': 'ONE PIECE',
            'ピカチュウ': 'ポケットモンスター',
            'イーブイ': 'ポケットモンスター',
            'ドラえもん': 'ドラえもん',
            'のび太': 'ドラえもん',
            'しずかちゃん': 'ドラえもん',
            'ジャイアン': 'ドラえもん',
            'スネ夫': 'ドラえもん',
            # ガンダム
            'アムロ・レイ': '機動戦士ガンダム',
            'シャア・アズナブル': '機動戦士ガンダム',
            'カミーユ・ビダン': '機動戦士Zガンダム',

            # エヴァンゲリオン
            'エヴァンゲリオン初号機': '新世紀エヴァンゲリオン',
            'Evangelion Unit-01': '新世紀エヴァンゲリオン',
            '碇シンジ': '新世紀エヴァンゲリオン',
            '綾波レイ': '新世紀エヴァンゲリオン',
            'アスカ・ラングレー': '新世紀エヴァンゲリオン',

            'ウルトラマン': 'ウルトラシリーズ',
            'Ultraman': 'ウルトラシリーズ',
            'アンパンマン': 'それいけ！アンパンマン',
            'ばいきんまん': 'それいけ！アンパンマン',
            'ドキンちゃん': 'それいけ！アンパンマン',
            'エアリス': 'ファイナルファンタジーVII',
            'エアリス・ゲインズブール': 'ファイナルファンタジーVII',
            'クラウド・ストライフ': 'ファイナルファンタジーVII',
            'Cloud Strife': 'ファイナルファンタジーVII',
            'ティファ・ロックハート': 'ファイナルファンタジーVII',
            'セフィロス': 'ファイナルファンタジーVII',
            'マリオ': 'スーパーマリオシリーズ',
            'ルイージ': 'スーパーマリオシリーズ',
            'ピーチ姫': 'スーパーマリオシリーズ',
            'クッパ': 'スーパーマリオシリーズ',
            'リンク': 'ゼルダの伝説',
            'ゼルダ': 'ゼルダの伝説',
            'ガノンドロフ': 'ゼルダの伝説',

            # Additional mappings
            'ゴジラ': 'ゴジラシリーズ',
            'サトシ': 'ポケットモンスター',
            'セーラームーン': '美少女戦士セーラームーン',
            'トトロ': 'となりのトトロ',
            'リヴァイ・アッカーマン': '進撃の巨人',
            'カービィ': '星のカービィ',
            'ガイル': 'ストリートファイター',
            'ケン': 'ストリートファイター',
            'リュウ': 'ストリートファイター',
            '赤木剛憲': 'SLAM DUNK',
            'Takenori Akagi': 'SLAM DUNK',
            'ジュドー・アーシタ': '機動戦士ガンダムZZ'
        }

    def load_database(self) -> Dict:
        """既存のデータベースを読み込み"""
        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {'characters': {}, 'metadata': {}}

    def save_database(self):
        """更新したデータベースを保存"""
        self.character_db['metadata']['last_updated'] = datetime.now().isoformat()
        self.character_db['metadata']['total_characters'] = len(self.character_db['characters'])

        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(self.character_db, f, ensure_ascii=False, indent=2)
        print(f"📁 データベース更新: {self.db_file}")

    def is_fictional_character(self, occupation: str) -> bool:
        """架空キャラクターかどうかを判定"""
        if not occupation or pd.isna(occupation):
            return False

        # 架空キャラクターを示すキーワード
        keywords = ['架空', 'キャラクター', 'アニメ', 'マンガ', '漫画',
                   'ゲーム', '小説', '映画', 'ドラマ']

        return any(keyword in occupation for keyword in keywords)

    def extract_work_from_display(self, display_name: str) -> Optional[str]:
        """既存のdisplay_nameから作品名を抽出"""
        if '(' in display_name and ')' in display_name:
            match = re.search(r'\((.*?)\)$', display_name)
            if match:
                work = match.group(1)
                # 架空キャラクター系の文字列は作品名ではない
                if '架空' in work or 'キャラクター' in work:
                    return None
                return work
        return None

    def search_wikipedia(self, character_name: str) -> Optional[str]:
        """Wikipedia APIで作品名を検索"""
        # キャッシュチェック
        if character_name in self.wikipedia_cache:
            return self.wikipedia_cache[character_name]

        try:
            # レート制限対策
            time.sleep(0.5)

            # Wikipedia APIでページを取得
            page = wiki_wiki.page(f"{character_name}")

            if page.exists():
                # ページの内容から作品名を抽出
                # 「〜の登場人物」「〜のキャラクター」などのパターンを探す
                patterns = [
                    r'『(.*?)』.*?登場',
                    r'『(.*?)』.*?キャラクター',
                    r'『(.*?)』.*?主人公',
                    r'『(.*?)』.*?登場人物',
                    r'「(.*?)」.*?登場',
                    r'「(.*?)」.*?キャラクター'
                ]

                for pattern in patterns:
                    match = re.search(pattern, page.text[:500])
                    if match:
                        work_name = match.group(1)
                        self.wikipedia_cache[character_name] = work_name
                        return work_name

        except Exception as e:
            # エラーは静かに処理
            pass

        self.wikipedia_cache[character_name] = None
        return None

    def get_work_name(self, character_name: str, character_ja: str) -> Optional[str]:
        """キャラクター名から作品名を取得"""
        # 既知の作品名をチェック
        if character_ja in self.known_works:
            self.stats['from_database'] += 1
            return self.known_works[character_ja]

        if character_name in self.known_works:
            self.stats['from_database'] += 1
            return self.known_works[character_name]

        # データベースをチェック
        if character_ja in self.character_db['characters']:
            self.stats['from_database'] += 1
            return self.character_db['characters'][character_ja].get('work')

        # Wikipedia検索
        work = self.search_wikipedia(character_ja) or self.search_wikipedia(character_name)
        if work:
            self.stats['wikipedia_found'] += 1
            # データベースに追加
            self.character_db['characters'][character_ja] = {
                'name': character_name,
                'work': work,
                'source': 'wikipedia',
                'added': datetime.now().isoformat()
            }
            return work

        return None

    def enhance_character_name(self, row: pd.Series) -> Tuple[str, str]:
        """キャラクター名に作品名を追加"""
        display_name = row['person_name_display']
        character_name = row['person_name']
        character_ja = row.get('person_name_ja', '')
        occupation = row.get('occupation', '')

        # 既に作品名が含まれている場合
        existing_work = self.extract_work_from_display(display_name)
        if existing_work:
            self.stats['already_has_work'] += 1
            return display_name, 'already_has_work'

        # occupationから作品名を抽出する試み
        if 'SPY×FAMILY' in occupation or 'SPY FAMILY' in occupation:
            work_name = 'SPY×FAMILY'
        elif '(' in occupation and ')' in occupation:
            match = re.search(r'\((.*?)\)', occupation)
            if match:
                work_name = match.group(1)
        else:
            # 作品名を取得
            work_name = self.get_work_name(character_name, character_ja)

        if work_name:
            # 外国語名を日本語に変換（先に日本語名を使用）
            base_name = character_ja if character_ja and not pd.isna(character_ja) else display_name
            new_display_name = f"{base_name} ({work_name})"

            self.stats['work_added'] += 1
            self.update_log.append({
                'person_id': row.get('person_id', ''),
                'original': display_name,
                'updated': new_display_name,
                'work': work_name,
                'character_ja': character_ja
            })
            return new_display_name, 'work_added'

        # 作品名が見つからない場合でも日本語名を使用
        if character_ja and not pd.isna(character_ja) and character_ja != display_name:
            new_display_name = f"{character_ja} (架空キャラクター)"
            self.stats['not_found'] += 1
            return new_display_name, 'not_found'

        self.stats['not_found'] += 1
        return display_name, 'not_found'

    def process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """データフレーム全体を処理"""
        print("🎭 架空キャラクターの作品名追加を開始...")

        # 架空キャラクターのみを処理
        fictional_mask = df['occupation'].apply(self.is_fictional_character)
        fictional_chars = df[fictional_mask]

        print(f"   架空キャラクター数: {len(fictional_chars)}件")

        # 各キャラクターを処理
        for idx in fictional_chars.index:
            self.stats['total_processed'] += 1

            new_display_name, status = self.enhance_character_name(df.loc[idx])

            # 更新が必要な場合
            if status in ['work_added', 'not_found']:
                df.at[idx, 'person_name_display'] = new_display_name

            # 進捗表示
            if self.stats['total_processed'] % 10 == 0:
                print(f"  処理中... {self.stats['total_processed']} / {len(fictional_chars)}")

        # データベースを保存
        self.save_database()

        return df

    def generate_report(self) -> str:
        """処理レポートを生成"""
        report = []
        report.append("# Ultra Think 架空キャラクター作品名追加レポート")
        report.append(f"\n生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        report.append("\n## 📊 処理統計")
        report.append(f"- 総処理数: {self.stats['total_processed']}件")
        report.append(f"- 作品名追加: {self.stats['work_added']}件")
        report.append(f"- 既に作品名あり: {self.stats['already_has_work']}件")
        report.append(f"- データベースから取得: {self.stats['from_database']}件")
        report.append(f"- Wikipediaから取得: {self.stats['wikipedia_found']}件")
        report.append(f"- 作品名不明: {self.stats['not_found']}件")

        if self.update_log:
            report.append("\n## 📝 更新詳細（最初の20件）")
            for log in self.update_log[:20]:
                report.append(f"\n### {log['person_id']}")
                report.append(f"- 元の表示名: {log['original']}")
                report.append(f"- 更新後: {log['updated']}")
                report.append(f"- 作品名: {log['work'] if 'work' in log else '不明'}")

        report.append("\n## ✅ 処理完了")
        report.append("架空キャラクターへの作品名追加が完了しました。")

        return '\n'.join(report)


def apply_fictional_character_rules(csv_file: str = None) -> pd.DataFrame:
    """架空キャラクター作品名追加ルールを適用"""
    # CSVファイルの読み込み
    if csv_file is None:
        csv_file = "ultra_think_CONVERTED_20250827_224054.csv"

    print(f"📂 CSVファイル読み込み: {csv_file}")
    df = pd.read_csv(csv_file, encoding='utf-8')

    # 処理実行
    enhancer = FictionalCharacterEnhancer()
    df_enhanced = enhancer.process_dataframe(df)

    # 結果を保存
    output_file = csv_file.replace('.csv', '_fictional_enhanced.csv')
    df_enhanced.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\n💾 更新済みデータを保存: {output_file}")

    # レポート生成
    report = enhancer.generate_report()
    report_file = f"FICTIONAL_CHARACTER_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"📋 レポート生成: {report_file}")

    return df_enhanced


def apply_to_new_data(new_data: pd.DataFrame) -> pd.DataFrame:
    """新規追加データに架空キャラクタールールを適用"""
    enhancer = FictionalCharacterEnhancer()
    return enhancer.process_dataframe(new_data)


if __name__ == "__main__":
    print("=" * 60)
    print("🎭 Ultra Think 架空キャラクター作品名追加")
    print("=" * 60)

    # ルールを適用
    df_result = apply_fictional_character_rules()

    print("\n✅ 処理完了！")
