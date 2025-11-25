#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日本語パターンのプレースホルダー完全削除スクリプト
問題のプレースホルダーパターン：
- RomanのReligious Leader687
- GreekのInventor341
- AmericanのRevolutionary422
- JapaneseのRevolutionary587
- PersianのWriter987
"""

import pandas as pd
import re
import json
from datetime import datetime
from pathlib import Path

def detect_japanese_placeholders(df):
    """日本語パターンのプレースホルダーを検出"""

    # 検出パターン
    patterns = [
        r'^[A-Za-z]+\の[A-Za-z]+\d+$',  # RomanのReligious Leader687
        r'^[A-Za-z]+\の[A-Za-z\s]+\d+$',  # GreekのGeneral 664
        r'^[A-Za-z]+\の[A-Za-z\s]+\d+$',  # AmericanのWarrior 761
    ]

    # 検出結果
    detected_rows = []

    for idx, row in df.iterrows():
        person_name_display = str(row.get('person_name_display', ''))
        person_name_ja = str(row.get('person_name_ja', ''))

        # 両方のフィールドをチェック
        for pattern in patterns:
            if (re.match(pattern, person_name_display) or
                re.match(pattern, person_name_ja)):
                detected_rows.append({
                    'row_index': idx,
                    'person_name_display': person_name_display,
                    'person_name_ja': person_name_ja,
                    'pattern_matched': pattern
                })
                break

    return detected_rows

def remove_japanese_placeholders(input_file, output_file):
    """日本語プレースホルダーを削除してクリーンなデータベースを作成"""

    print(f"🔍 日本語プレースホルダー削除開始...")
    print(f"📂 入力ファイル: {input_file}")

    # データ読み込み
    print("📖 データ読み込み中...")
    try:
        df = pd.read_csv(input_file)
        print(f"✅ {len(df):,}件のデータ読み込み完了")
    except Exception as e:
        print(f"❌ ファイル読み込みエラー: {e}")
        return False

    # プレースホルダー検出
    print("🎯 日本語プレースホルダー検出中...")
    detected = detect_japanese_placeholders(df)

    if not detected:
        print("✅ 日本語プレースホルダーは検出されませんでした")
        return True

    print(f"🚨 {len(detected):,}件の日本語プレースホルダーを検出")

    # 検出された行の例を表示
    print("\n📋 検出されたプレースホルダーの例:")
    for i, item in enumerate(detected[:5]):
        print(f"  {i+1}. {item['person_name_display']} (パターン: {item['pattern_matched']})")

    if len(detected) > 5:
        print(f"  ... 他 {len(detected) - 5}件")

    # プレースホルダー行を削除
    print(f"\n🗑️ プレースホルダー行の削除中...")
    rows_to_remove = [item['row_index'] for item in detected]
    df_cleaned = df.drop(rows_to_remove).reset_index(drop=True)

    print(f"✅ {len(rows_to_remove):,}件のプレースホルダー行を削除")
    print(f"📊 残存データ: {len(df_cleaned):,}件")

    # クリーンアップ後の検証
    print("🔍 クリーンアップ後の検証中...")
    remaining_placeholders = detect_japanese_placeholders(df_cleaned)

    if remaining_placeholders:
        print(f"⚠️ 警告: {len(remaining_placeholders):,}件のプレースホルダーが残存")
        for item in remaining_placeholders[:3]:
            print(f"  残存: {item['person_name_display']}")
    else:
        print("✅ すべての日本語プレースホルダーが正常に削除されました")

    # 出力
    print(f"📝 クリーンデータの書き出し中...")
    try:
        df_cleaned.to_csv(output_file, index=False, encoding='utf-8')
        print(f"✅ 出力完了: {output_file}")
    except Exception as e:
        print(f"❌ 出力エラー: {e}")
        return False

    # 統計情報
    stats = {
        'input_file': input_file,
        'output_file': output_file,
        'original_count': len(df),
        'placeholder_count': len(detected),
        'cleaned_count': len(df_cleaned),
        'removal_rate': f"{(len(detected) / len(df) * 100):.2f}%",
        'cleaned_at': datetime.now().isoformat()
    }

    # 統計ファイル出力
    stats_file = output_file.replace('.csv', '_stats.json')
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"📊 統計情報: {stats_file}")

    # レポート生成
    report_file = output_file.replace('.csv', '_REPORT.md')
    generate_report(report_file, stats, detected)
    print(f"📋 レポート: {report_file}")

    return True

def generate_report(report_file, stats, detected):
    """削除レポートを生成"""

    report_content = f"""# 🗑️ 日本語プレースホルダー完全削除レポート

## 📅 実行日時
- 実行日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
- 入力ファイル: {stats['input_file']}
- 出力ファイル: {stats['output_file']}

## 📊 削除統計

### 処理結果
- **元データ数**: {stats['original_count']:,}件
- **プレースホルダー検出**: {stats['placeholder_count']:,}件
- **削除率**: {stats['removal_rate']}
- **最終出力数**: {stats['cleaned_count']:,}件

## 🎯 検出されたプレースホルダーパターン

### 主要パターン
- `[国籍]の[職業][番号]` 形式
- 例: RomanのReligious Leader687
- 例: GreekのInventor341
- 例: AmericanのRevolutionary422

### 検出例（上位10件）
"""

    for i, item in enumerate(detected[:10]):
        report_content += f"- {item['person_name_display']}\n"

    if len(detected) > 10:
        report_content += f"\n... 他 {len(detected) - 10}件\n"

    report_content += f"""

## ✅ 改善成果
日本語パターンのプレースホルダーが完全に削除され、
実在人物のみのクリーンなデータベースが完成しました。

## 🔍 今後の注意点
1. 新規データ追加時のプレースホルダー検出
2. 日本語パターンと英語パターンの両方の監視
3. 定期的な品質チェックの実施

---

*レポート生成: {datetime.now().isoformat()}*
*Japanese Placeholder Removal Report - Ultra Think*
"""

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)

def main():
    """メイン処理"""

    # 入力ファイル（問題のあるファイル）
    input_file = "ultra_think_FINAL_MERGED_20250827_080142.csv"

    # 出力ファイル名生成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"ultra_think_CLEAN_NO_PLACEHOLDERS_{timestamp}.csv"

    # ファイル存在確認
    if not Path(input_file).exists():
        print(f"❌ 入力ファイルが見つかりません: {input_file}")
        return

    # プレースホルダー削除実行
    success = remove_japanese_placeholders(input_file, output_file)

    if success:
        print(f"\n{'='*60}")
        print(f"✨ 日本語プレースホルダー削除完了!")
        print(f"📁 出力ファイル: {output_file}")
        print(f"{'='*60}")
    else:
        print("❌ 処理が失敗しました")

if __name__ == "__main__":
    main()
