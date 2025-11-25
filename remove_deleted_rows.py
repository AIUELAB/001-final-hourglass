#!/usr/bin/env python3
"""
A列に「削除」マークがある行を除外してクリーンなCSVを生成
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple


class DeletedRowRemover:
    """削除マークがある行を除外"""

    def __init__(self):
        self.stats = {
            'total': 0,
            'kept': 0,
            'deleted': 0,
            'deleted_samples': []
        }

    def process_csv(self, input_file: str = '/Users/admin/Desktop/Book1.csv') -> Tuple[str, Dict]:
        """CSVを処理して削除マークのある行を除外"""

        print("📊 削除行の除外処理開始")
        print(f"  入力: {input_file}")

        # CSVを読み込み
        rows_to_keep = []
        header = None

        with open(input_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)

            # ヘッダー行を取得
            header_row = next(reader)
            # A列（最初の列）を除外したヘッダー
            header = header_row[1:] if len(header_row) > 1 else header_row

            # データ行を処理
            for row in reader:
                self.stats['total'] += 1

                if len(row) > 0:
                    # A列の値をチェック
                    first_col = row[0].strip() if row[0] else ''

                    if first_col == '削除':
                        # 削除対象
                        self.stats['deleted'] += 1

                        # サンプル収集（最初の10件）
                        if len(self.stats['deleted_samples']) < 10 and len(row) > 1:
                            self.stats['deleted_samples'].append(row[1] if len(row) > 1 else '')
                    else:
                        # 保持する行（A列を除外）
                        clean_row = row[1:] if len(row) > 1 else []
                        if any(clean_row):  # 空行でない場合のみ追加
                            rows_to_keep.append(clean_row)
                            self.stats['kept'] += 1

        # 出力ファイル名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"cleaned_data_{timestamp}.csv"

        # クリーンなCSVを出力
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)

            # ヘッダー書き込み
            writer.writerow(header)

            # データ書き込み
            writer.writerows(rows_to_keep)

        # レポート出力
        print("\n📊 処理結果:")
        print(f"  総行数: {self.stats['total']:,}")
        print(f"  保持: {self.stats['kept']:,}行")
        print(f"  削除: {self.stats['deleted']:,}行")

        if self.stats['deleted_samples']:
            print("\n🗑️ 削除された行のサンプル:")
            for sample in self.stats['deleted_samples']:
                print(f"  - {sample}")

        print(f"\n✅ 出力: {output_file}")
        print("  A列（削除フラグ）を除外し、削除マークのある行を除去しました")

        return output_file, self.stats

    def create_summary_report(self, output_file: str):
        """サマリーレポートを作成"""

        report = f"""# データクリーニングレポート

## 処理概要
- **処理日時**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **入力ファイル**: Book1.csv
- **出力ファイル**: {output_file}

## 処理結果
- **総行数**: {self.stats['total']:,}
- **保持された行**: {self.stats['kept']:,}
- **削除された行**: {self.stats['deleted']:,}
- **削除率**: {self.stats['deleted']/self.stats['total']*100:.1f}%

## 削除された行の例
"""

        for sample in self.stats['deleted_samples'][:10]:
            report += f"- {sample}\n"

        report += """
## 処理内容
1. A列に「削除」マークがある行を除外
2. A列（削除フラグ列）自体も出力から除外
3. 残りのデータをクリーンなCSVとして出力

---
*クリーニング完了*
"""

        report_file = f"cleaning_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"\n📄 レポート: {report_file}")

        return report_file


def main():
    """メイン実行"""
    remover = DeletedRowRemover()

    # CSVを処理
    output_file, stats = remover.process_csv()

    if output_file:
        # レポート作成
        report_file = remover.create_summary_report(output_file)

        print("\n" + "="*60)
        print("🎯 データクリーニング完了")
        print("="*60)
        print(f"\nクリーンなデータ: {output_file}")
        print(f"削除された行数: {stats['deleted']:,}")


if __name__ == "__main__":
    main()
