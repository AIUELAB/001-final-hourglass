#!/usr/bin/env python3
"""
Ultra Think 外国語名日本語変換ルール強化版
person_name_displayが外国語の場合、日本語に変換
芸名・アーティスト名は対象外
"""

import pandas as pd
import re
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import gspread
from google.oauth2.service_account import Credentials
import time

# Google Sheets設定
SPREADSHEET_ID = "1G0ec3d5DHGiahLetsqey9W23HGFOn2tkEacsFd5ZSps"

class ForeignNameConverter:
    """外国語名を日本語に変換するクラス"""

    def __init__(self):
        # 芸名として維持する職業リスト
        self.artist_occupations = {
            '歌手', 'ミュージシャン', '俳優', '女優', 'アーティスト',
            'タレント', 'モデル', '声優', 'アイドル', 'ダンサー',
            'ラッパー', 'DJ', 'プロデューサー', '作曲家', '演出家',
            'VTuber', 'YouTuber', 'インフルエンサー', 'ストリーマー',
            'バンドメンバー', 'ギタリスト', 'ベーシスト', 'ドラマー',
            'ボーカリスト', 'キーボーディスト'
        }

        # 変換統計
        self.stats = {
            'total_processed': 0,
            'converted': 0,
            'kept_as_artist_name': 0,
            'already_japanese': 0,
            'no_japanese_available': 0
        }

        # 変換ログ
        self.conversion_log = []

    def is_foreign_name(self, name: str) -> bool:
        """外国語名かどうかを判定"""
        if not name or pd.isna(name):
            return False

        # 日本語文字（ひらがな、カタカナ、漢字）のパターン
        japanese_pattern = r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]'
        has_japanese = bool(re.search(japanese_pattern, name))

        # アルファベットのパターン
        alphabet_pattern = r'[A-Za-z]'
        has_alphabet = bool(re.search(alphabet_pattern, name))

        # 韓国語（ハングル）のパターン
        korean_pattern = r'[\uAC00-\uD7AF]'
        has_korean = bool(re.search(korean_pattern, name))

        # 中国語（簡体字・繁体字）のパターン - 日本の漢字と重複するので追加チェック
        chinese_pattern = r'[\u4E00-\u9FFF]'

        # 外国語名の判定
        # 1. アルファベットのみ
        # 2. ハングルを含む
        # 3. 日本語文字がなくアルファベットを含む
        if not has_japanese and (has_alphabet or has_korean):
            return True

        return False

    def is_artist_occupation(self, occupation: str) -> bool:
        """芸名系の職業かどうかを判定"""
        if not occupation or pd.isna(occupation):
            return False

        # 職業に芸名系のキーワードが含まれるかチェック
        for artist_job in self.artist_occupations:
            if artist_job in occupation:
                return True

        return False

    def convert_to_japanese(self, row: pd.Series) -> Tuple[str, str]:
        """外国語名を日本語に変換"""
        original_display = row['person_name_display']
        person_name_ja = row.get('person_name_ja', '')
        occupation = row.get('occupation', '')

        # 既に日本語の場合
        if not self.is_foreign_name(original_display):
            self.stats['already_japanese'] += 1
            return original_display, 'already_japanese'

        # 芸名・アーティスト名の場合は維持
        if self.is_artist_occupation(occupation):
            self.stats['kept_as_artist_name'] += 1
            return original_display, 'kept_as_artist_name'

        # person_name_jaから日本語名を取得
        if person_name_ja and not pd.isna(person_name_ja) and person_name_ja != '':
            # person_name_jaが利用可能
            self.stats['converted'] += 1
            self.conversion_log.append({
                'person_id': row.get('person_id', ''),
                'original': original_display,
                'converted': person_name_ja,
                'occupation': occupation,
                'nationality': row.get('nationality', ''),
                'reason': 'converted_from_ja'
            })
            return person_name_ja, 'converted'

        # 日本語名が利用できない場合
        self.stats['no_japanese_available'] += 1
        return original_display, 'no_japanese_available'

    def process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """データフレーム全体を処理"""
        print("🔍 外国語名の検出と変換を開始...")

        # バックアップ
        df_copy = df.copy()

        # 各行を処理
        for idx, row in df.iterrows():
            self.stats['total_processed'] += 1

            new_display_name, status = self.convert_to_japanese(row)

            # 変換が必要な場合のみ更新
            if status == 'converted':
                df.at[idx, 'person_name_display'] = new_display_name

            # 進捗表示
            if self.stats['total_processed'] % 100 == 0:
                print(f"  処理中... {self.stats['total_processed']} / {len(df)}")

        return df

    def generate_report(self) -> str:
        """処理レポートを生成"""
        report = []
        report.append("# Ultra Think 外国語名日本語変換レポート")
        report.append(f"\n生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        report.append("\n## 📊 処理統計")
        report.append(f"- 総処理数: {self.stats['total_processed']}件")
        report.append(f"- 日本語に変換: {self.stats['converted']}件")
        report.append(f"- 芸名として維持: {self.stats['kept_as_artist_name']}件")
        report.append(f"- 既に日本語: {self.stats['already_japanese']}件")
        report.append(f"- 日本語名なし: {self.stats['no_japanese_available']}件")

        if self.conversion_log:
            report.append("\n## 📝 変換詳細（最初の20件）")
            for log in self.conversion_log[:20]:
                report.append(f"\n### {log['person_id']}")
                report.append(f"- 元の表示名: {log['original']}")
                report.append(f"- 変換後: {log['converted']}")
                report.append(f"- 職業: {log['occupation']}")
                report.append(f"- 国籍: {log['nationality']}")

        report.append("\n## ✅ 処理完了")
        report.append("外国語名の日本語変換が完了しました。")

        return '\n'.join(report)

    def save_conversion_database(self):
        """変換データベースを保存"""
        if self.conversion_log:
            db_file = f"foreign_name_conversions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(db_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'conversions': self.conversion_log,
                    'stats': self.stats,
                    'timestamp': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            print(f"📁 変換データベース保存: {db_file}")


def apply_foreign_name_rules(csv_file: str = None) -> pd.DataFrame:
    """外国語名変換ルールを適用"""
    # CSVファイルの読み込み
    if csv_file is None:
        csv_file = "ultra_think_CONVERTED_20250827_224054.csv"

    print(f"📂 CSVファイル読み込み: {csv_file}")
    df = pd.read_csv(csv_file, encoding='utf-8')
    print(f"   データ数: {len(df)}行")

    # 変換処理
    converter = ForeignNameConverter()
    df_converted = converter.process_dataframe(df)

    # 結果を保存
    output_file = csv_file.replace('.csv', '_foreign_converted.csv')
    df_converted.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\n💾 変換済みデータを保存: {output_file}")

    # レポート生成
    report = converter.generate_report()
    report_file = f"FOREIGN_NAME_CONVERSION_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"📋 レポート生成: {report_file}")

    # 変換データベースを保存
    converter.save_conversion_database()

    return df_converted


def apply_to_new_data(new_data: pd.DataFrame) -> pd.DataFrame:
    """新規追加データに外国語名変換ルールを適用"""
    converter = ForeignNameConverter()
    return converter.process_dataframe(new_data)


if __name__ == "__main__":
    print("=" * 60)
    print("🌏 Ultra Think 外国語名日本語変換ルール（強化版）")
    print("=" * 60)

    # ルールを適用
    df_result = apply_foreign_name_rules()

    print("\n✅ 処理完了！")
