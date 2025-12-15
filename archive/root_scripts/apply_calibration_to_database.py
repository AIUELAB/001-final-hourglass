#!/usr/bin/env python3
"""
既存データベースに日本人向け知名度較正を適用
Apply Japanese Recognition Calibration to Database
"""

import csv
import json
import os
from datetime import datetime
from typing import List, Dict
import sys

# 較正システムをインポート
from ultra_think_japanese_recognition_calibrator import JapaneseRecognitionCalibrator

def load_csv_data(filepath: str) -> List[Dict]:
    """CSVファイルからデータを読み込む"""
    data = []

    if not os.path.exists(filepath):
        print(f"❌ ファイルが見つかりません: {filepath}")
        return data

    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(dict(row))

    return data

def save_csv_data(data: List[Dict], output_path: str):
    """データをCSVファイルに保存"""
    if not data:
        print("❌ 保存するデータがありません")
        return

    # ヘッダーを取得
    headers = list(data[0].keys())

    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)

def apply_calibration(input_file: str, output_file: str = None):
    """較正を適用するメイン処理"""

    print("🎌 日本人向け知名度較正適用システム")
    print("=" * 60)

    # データを読み込む
    print(f"\n📂 データ読み込み中: {input_file}")
    original_data = load_csv_data(input_file)

    if not original_data:
        print("❌ データの読み込みに失敗しました")
        return

    print(f"  ✅ {len(original_data)}件のデータを読み込みました")

    # 較正システムを初期化
    calibrator = JapaneseRecognitionCalibrator()

    # 較正を適用
    print("\n🔧 較正処理中...")

    # オリジナルデータのコピーを作成（比較用）
    original_copy = [dict(d) for d in original_data]

    # バッチで較正を実行
    calibrated_data = calibrator.calibrate_batch(original_data)

    # レポートを生成
    print("\n📊 較正レポート生成中...")
    report = calibrator.generate_report(original_copy, calibrated_data)

    # 出力ファイル名を決定
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"ultra_think_calibrated_{timestamp}.csv"

    # 保存
    print(f"\n💾 較正済みデータを保存中: {output_file}")
    save_csv_data(calibrated_data, output_file)
    print(f"  ✅ {len(calibrated_data)}件のデータを保存しました")

    # レポートを表示
    display_report(report)

    # レポートをファイルに保存
    save_report(report)

    return calibrated_data, report

def display_report(report: Dict):
    """較正レポートを表示"""
    print("\n" + "=" * 60)
    print("📊 較正結果サマリー")
    print("=" * 60)

    print(f"\n総処理人数: {report['total_persons']}名")
    print(f"較正実行日時: {report['calibration_date']}")

    print("\n【スコア変化】")
    print(f"  向上: {report['changes']['improved']}名")
    print(f"  低下: {report['changes']['decreased']}名")
    print(f"  変化なし: {report['changes']['unchanged']}名")

    print("\n【スコア分布】")
    for range_key, count in sorted(report['score_distribution'].items(), reverse=True):
        if count > 0:
            percentage = (count / report['total_persons']) * 100
            bar = '█' * int(percentage / 2)
            print(f"  {range_key:>6}: {count:>4}名 ({percentage:>5.1f}%) {bar}")

    print("\n【カテゴリ別平均スコア】")
    for category, stats in report['category_averages'].items():
        print(f"  {category:<12}: 平均 {stats['average']:>5.1f} (最小 {stats['min']:>3}, 最大 {stats['max']:>3}, {stats['count']:>4}名)")

    if report['examples']:
        print("\n【大幅変化例（|変化| > 20）】")
        for example in report['examples'][:5]:
            change_symbol = "↑" if example['change'] > 0 else "↓"
            print(f"  {example['name']:<20} [{example['category']:<10}]: {example['original']:>3} → {example['calibrated']:>3} ({change_symbol}{abs(example['change']):>2})")

def save_report(report: Dict):
    """レポートをMarkdownファイルとして保存"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"calibration_report_{timestamp}.md"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# 🎌 日本人向け知名度較正レポート\n\n")
        f.write(f"## 実行情報\n")
        f.write(f"- 較正日時: {report['calibration_date']}\n")
        f.write(f"- 総処理人数: {report['total_persons']}名\n\n")

        f.write("## スコア変化統計\n")
        f.write(f"- 向上: {report['changes']['improved']}名\n")
        f.write(f"- 低下: {report['changes']['decreased']}名\n")
        f.write(f"- 変化なし: {report['changes']['unchanged']}名\n\n")

        f.write("## スコア分布\n")
        f.write("| スコア範囲 | 人数 | 割合 |\n")
        f.write("|-----------|------|------|\n")
        for range_key, count in sorted(report['score_distribution'].items(), reverse=True):
            percentage = (count / report['total_persons']) * 100
            f.write(f"| {range_key} | {count} | {percentage:.1f}% |\n")

        f.write("\n## カテゴリ別統計\n")
        f.write("| カテゴリ | 平均 | 最小 | 最大 | 人数 |\n")
        f.write("|----------|------|------|------|------|\n")
        for category, stats in report['category_averages'].items():
            f.write(f"| {category} | {stats['average']:.1f} | {stats['min']} | {stats['max']} | {stats['count']} |\n")

        if report['examples']:
            f.write("\n## 大幅変化例\n")
            for example in report['examples']:
                change_symbol = "↑" if example['change'] > 0 else "↓"
                f.write(f"- **{example['name']}** ({example['category']}): {example['original']} → {example['calibrated']} ({change_symbol}{abs(example['change'])})\n")

        f.write("\n---\n")
        f.write("*Ultra Think Japanese Recognition Calibration System*\n")

    print(f"\n📄 レポートを保存しました: {report_file}")

    # JSON形式でも保存
    json_file = f"calibration_stats_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"📊 統計データを保存しました: {json_file}")

def main():
    """メイン処理"""
    # 入力ファイルを決定
    input_files = [
        "ultra_think_CLEAN_NO_PLACEHOLDERS_20250827_124619.csv",
        "ultra_think_CLEAN_FINAL_20250827.csv"
    ]

    input_file = None
    for file in input_files:
        if os.path.exists(file):
            input_file = file
            break

    if not input_file:
        print("❌ 処理対象のCSVファイルが見つかりません")
        print(f"   探したファイル: {', '.join(input_files)}")
        sys.exit(1)

    # 較正を適用
    apply_calibration(input_file)

if __name__ == "__main__":
    main()
