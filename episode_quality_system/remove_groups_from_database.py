#!/usr/bin/env python3
"""
グループ/団体除去システム
データベースから個人ではないエントリを完全に除去
"""

import json
import csv
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Set

class GroupRemovalSystem:
    """グループ/団体除去システム"""

    def __init__(self):
        """初期化"""
        self.known_groups = self._get_known_groups()
        self.group_patterns = self._get_group_patterns()
        self.confirmed_individuals = self._get_confirmed_individuals()
        self.removal_log = []
        self.stats = {
            'total_processed': 0,
            'groups_removed': 0,
            'individuals_kept': 0
        }

    def _get_known_groups(self) -> Set[str]:
        """既知のグループ/団体/バンド名"""
        return {
            # 音楽バンド・ユニット
            'サカナクション', 'Mr.Children', 'B\'z', 'EXILE', 'ONE OK ROCK',
            'SEKAI NO OWARI', 'RADWIMPS', 'BUMP OF CHICKEN', 'スピッツ',
            'ゆず', 'コブクロ', 'GReeeeN', 'DREAMS COME TRUE', 'いきものがかり',
            'Perfume', 'CHEMISTRY', 'KinKi Kids', 'TOKIO', 'V6',

            # アイドルグループ
            'AKB48', 'SKE48', 'NMB48', 'HKT48', 'NGT48', 'STU48',
            '乃木坂46', '欅坂46', '櫻坂46', '日向坂46',
            '嵐', 'SMAP', '関ジャニ∞', 'Hey! Say! JUMP', 'Kis-My-Ft2',
            'Sexy Zone', 'King & Prince', 'SixTONES', 'Snow Man',
            'NEWS', 'KAT-TUN', '少年隊', '光GENJI',

            # K-POPグループ
            'BTS', 'BLACKPINK', 'TWICE', 'SEVENTEEN', 'Stray Kids',
            'ENHYPEN', 'TXT', 'NCT', 'ATEEZ', 'TREASURE',

            # お笑いグループ
            'ダウンタウン', 'とんねるず', 'ウッチャンナンチャン', 'ナインティナイン',
            '南海キャンディーズ', 'オリエンタルラジオ', 'サンドウィッチマン',
            'アンジャッシュ', 'インパルス', 'ロンドンブーツ1号2号',

            # スポーツチーム
            'なでしこジャパン', 'サムライジャパン', '侍ジャパン'
        }

    def _get_group_patterns(self) -> List[str]:
        """グループを示すパターン"""
        return [
            # 日本語パターン
            'バンド', 'ユニット', 'グループ', 'チーム', 'コンビ', 'トリオ',
            '劇団', '楽団', 'オーケストラ', 'カルテット', 'クインテット',
            '一座', '隊', '団', '会', '組', 'ファミリー',

            # 英語パターン
            'Band', 'Unit', 'Group', 'Team', 'Crew', 'Squad',
            'Orchestra', 'Ensemble', 'Quartet', 'Trio', 'Duo',

            # 数字系（複数人を示唆）
            '48', '46', 'ジャニーズ', 'JAPAN', 'ジャパン'
        ]

    def _get_confirmed_individuals(self) -> Set[str]:
        """確実に個人であることが確認された名前"""
        return {
            # 個人アーティスト
            'HIKAKIN', 'YOSHIKI', 'Ado', 'あいみょん', '米津玄師',
            '星野源', '福山雅治', '宇多田ヒカル', '安室奈美恵', '浜崎あゆみ',

            # 俳優・タレント
            '新垣結衣', '綾瀬はるか', '岡田准一', '福山雅治', '渡辺謙',

            # スポーツ選手
            '大谷翔平', 'イチロー', '松井秀喜', '王貞治', '長嶋茂雄',
            '羽生結弦', '浅田真央', '荒川静香', '池江璃花子',

            # 文化人・学者
            '村上春樹', '宮崎駿', '黒澤明', '手塚治虫', '山中伸弥',

            # 実業家
            '孫正義', '柳井正', '三木谷浩史', '前澤友作', '堀江貴文',

            # 政治家
            '安倍晋三', '小泉純一郎',

            # 外国人個人
            'スティーブ・ジョブズ', 'ビル・ゲイツ', 'イーロン・マスク',
            'ジェフ・ベゾス', 'アルベルト・アインシュタイン',
            'マリー・キュリー', 'ヘレン・ケラー', 'マザー・テレサ'
        }

    def is_group(self, name: str) -> bool:
        """グループかどうか判定"""

        # 1. 確実に個人と確認されている場合
        if name in self.confirmed_individuals:
            return False

        # 2. 既知のグループ名と一致
        if name in self.known_groups:
            self.removal_log.append(f"{name}: 既知のグループ")
            return True

        # 3. グループを示すパターンを含む
        for pattern in self.group_patterns:
            if pattern in name:
                # ただし、個人名の一部である可能性を考慮
                if name not in self.confirmed_individuals:
                    # スティーブ・ジョブズのような「ズ」で終わる個人名を除外
                    if pattern == 'ズ' and 'ジョブ' in name:
                        return False
                    if pattern in ['JAPAN', 'ジャパン'] and 'なでしこ' not in name:
                        return False

                    self.removal_log.append(f"{name}: パターン '{pattern}' を含む")
                    return True

        return False

    def clean_expanded_moments_database(self):
        """expanded_moments_database.jsonからグループを除去"""
        try:
            with open('expanded_moments_database.json', 'r', encoding='utf-8') as f:
                data = json.load(f)

            if 'persons' in data:
                persons = data['persons']
                original_count = len(persons)

                # グループを除去
                cleaned_persons = {}
                removed_groups = []

                for name, info in persons.items():
                    if not self.is_group(name):
                        cleaned_persons[name] = info
                    else:
                        removed_groups.append(name)

                # バックアップ作成
                import shutil
                shutil.copy('expanded_moments_database.json',
                           'expanded_moments_database_backup.json')

                # クリーンなデータを保存
                data['persons'] = cleaned_persons
                with open('expanded_moments_database_clean.json', 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                print(f"\n拡張データベースのクリーニング:")
                print(f"  元のエントリ数: {original_count}")
                print(f"  削除されたグループ: {len(removed_groups)}")
                print(f"  残った個人: {len(cleaned_persons)}")

                if removed_groups:
                    print(f"\n削除されたグループ:")
                    for group in removed_groups:
                        print(f"    - {group}")

                return cleaned_persons

        except FileNotFoundError:
            print("警告: expanded_moments_database.jsonが見つかりません")
            return {}

    def clean_csv_database(self, input_csv: str, output_csv: str = None):
        """CSVデータベースからグループを除去"""
        if not output_csv:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_csv = f"individual_only_database_{timestamp}.csv"

        # データ読み込み
        df = pd.read_csv(input_csv, encoding='utf-8-sig')
        self.stats['total_processed'] = len(df)

        print(f"\nCSVデータベースのクリーニング:")
        print(f"  入力ファイル: {input_csv}")
        print(f"  総エントリ数: {len(df)}")

        # グループを検出して除去
        cleaned_rows = []
        removed_groups = []

        for _, row in df.iterrows():
            person_name = row['person_name']

            if not self.is_group(person_name):
                cleaned_rows.append(row.to_dict())
                self.stats['individuals_kept'] += 1
            else:
                removed_groups.append(person_name)
                self.stats['groups_removed'] += 1

        # クリーンなデータフレーム作成
        clean_df = pd.DataFrame(cleaned_rows)

        # CSV保存
        clean_df.to_csv(output_csv, index=False, encoding='utf-8-sig')

        print(f"\n処理結果:")
        print(f"  削除されたグループ: {self.stats['groups_removed']}件")
        print(f"  保持された個人: {self.stats['individuals_kept']}件")
        print(f"  出力ファイル: {output_csv}")

        if removed_groups:
            print(f"\n削除されたエントリ:")
            for group in removed_groups:
                print(f"    ✗ {group}")

        return output_csv

    def validate_final_database(self, csv_path: str):
        """最終データベースの品質検証"""
        df = pd.read_csv(csv_path, encoding='utf-8-sig')

        print("\n" + "="*60)
        print("最終品質検証")
        print("="*60)

        # グループチェック
        remaining_groups = []
        for name in df['person_name'].unique():
            if self.is_group(name):
                remaining_groups.append(name)

        if not remaining_groups:
            print("✅ グループ/団体: 完全除去（0件）")
        else:
            print(f"❌ 残存グループ: {len(remaining_groups)}件")
            for group in remaining_groups:
                print(f"    - {group}")

        # 文字数チェック
        valid = df[(df['character_count'] >= 132) & (df['character_count'] <= 250)]
        print(f"✅ 文字数適正率: {len(valid)/len(df)*100:.1f}%")

        # 重複チェック
        duplicates = df['person_name'].duplicated().sum()
        if duplicates == 0:
            print("✅ 重複: なし")
        else:
            print(f"⚠️ 重複: {duplicates}件")

        print(f"\n最終個人数: {len(df)}人")

        # サンプル表示
        print("\n個人エピソードサンプル（3件）:")
        print("-"*60)
        for i, (_, row) in enumerate(df.sample(min(3, len(df))).iterrows(), 1):
            print(f"\n{i}. 【{row['person_name']}】({row['age']}歳)")
            print(f"   {row['episode'][:100]}...")

    def generate_removal_report(self):
        """除去レポート生成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"group_removal_report_{timestamp}.txt"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("グループ/団体除去レポート\n")
            f.write("="*60 + "\n")
            f.write(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("処理統計:\n")
            f.write(f"  総処理数: {self.stats['total_processed']}\n")
            f.write(f"  削除グループ: {self.stats['groups_removed']}\n")
            f.write(f"  保持個人: {self.stats['individuals_kept']}\n\n")

            if self.removal_log:
                f.write("削除理由詳細:\n")
                for log in self.removal_log:
                    f.write(f"  - {log}\n")

        print(f"\n除去レポート保存: {report_file}")


def main():
    """メイン実行"""
    print("グループ/団体除去システム")
    print("="*60)

    remover = GroupRemovalSystem()

    # 1. expanded_moments_databaseのクリーニング
    print("\n1. 拡張データベースのクリーニング")
    remover.clean_expanded_moments_database()

    # 2. CSVデータベースのクリーニング
    print("\n2. CSVデータベースのクリーニング")
    input_csv = "perfect_unified_database_20250923_181324.csv"
    output_csv = remover.clean_csv_database(input_csv)

    # 3. 品質検証
    remover.validate_final_database(output_csv)

    # 4. レポート生成
    remover.generate_removal_report()

    print("\n" + "="*60)
    print("✅ グループ/団体除去完了")
    print(f"📁 個人のみのデータベース: {output_csv}")


if __name__ == "__main__":
    main()
