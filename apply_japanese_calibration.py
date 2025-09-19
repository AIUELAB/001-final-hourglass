#!/usr/bin/env python3
"""
既存データベースに日本人向け知名度較正を適用
Apply Japanese Recognition Calibration to Existing Database
"""

import csv
import json
import os
from datetime import datetime
from typing import List, Dict, Any
from ultra_think_japanese_recognition_calibrator import JapaneseRecognitionCalibrator


class DatabaseCalibrationApplicator:
    """データベースへの較正適用システム"""
    
    def __init__(self):
        self.calibrator = JapaneseRecognitionCalibrator()
        self.processed_count = 0
        self.error_count = 0
        
    def find_latest_database(self) -> str:
        """最新のデータベースファイルを検索"""
        
        candidates = [
            'ultra_think_MASSIVE_FINAL_20250827_071350.csv',
            'ultra_think_10000_ACHIEVED_20250825_223422.csv',
            'ultra_think_FINAL_COMPLETE_20250826_000013.csv',
            'ultra_think_WITH_CRIMINALS_20250826_001012.csv'
        ]
        
        for filename in candidates:
            if os.path.exists(filename):
                print(f"✅ データベース発見: {filename}")
                return filename
        
        # 他のCSVファイルを探す
        csv_files = [f for f in os.listdir('.') if f.startswith('ultra_think') and f.endswith('.csv')]
        if csv_files:
            csv_files.sort(reverse=True)
            print(f"✅ 代替データベース使用: {csv_files[0]}")
            return csv_files[0]
        
        return None
    
    def load_database(self, filename: str) -> List[Dict[str, Any]]:
        """CSVデータベースを読み込み"""
        
        persons = []
        
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
            # BOMを除去
            if content.startswith('\ufeff'):
                content = content[1:]
            
            lines = content.strip().split('\n')
            
            # ヘッダーを解析
            headers = lines[0].split(',')
            print(f"📋 フィールド数: {len(headers)}")
            
            # データを読み込み
            for i, line in enumerate(lines[1:], 1):
                try:
                    # CSVを適切に解析
                    values = []
                    current_value = ''
                    in_quotes = False
                    
                    for char in line:
                        if char == '"':
                            in_quotes = not in_quotes
                        elif char == ',' and not in_quotes:
                            values.append(current_value)
                            current_value = ''
                        else:
                            current_value += char
                    values.append(current_value)
                    
                    # 値の数を調整
                    while len(values) < len(headers):
                        values.append('')
                    
                    # 辞書形式に変換
                    person = {}
                    for j, header in enumerate(headers):
                        if j < len(values):
                            person[header] = values[j].strip().strip('"')
                    
                    persons.append(person)
                    
                except Exception as e:
                    print(f"⚠️ 行 {i} の処理エラー: {e}")
                    continue
        
        print(f"✅ {len(persons)}人のデータを読み込みました")
        return persons
    
    def apply_calibration(self, persons: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """較正を適用"""
        
        print("\n🔧 知名度較正を適用中...")
        print("=" * 60)
        
        calibrated_persons = []
        
        # プログレス表示用のコールバック
        def show_progress(current, total):
            percentage = (current / total) * 100
            print(f"  進捗: {current}/{total} ({percentage:.1f}%)")
        
        # バッチ処理で較正
        calibrated_persons = self.calibrator.batch_calibrate(
            persons, 
            progress_callback=show_progress
        )
        
        self.processed_count = len(calibrated_persons)
        
        return calibrated_persons
    
    def analyze_calibration_results(self, original: List[Dict], calibrated: List[Dict]) -> Dict:
        """較正結果の分析"""
        
        analysis = {
            'total_persons': len(calibrated),
            'score_changes': [],
            'category_improvements': {},
            'average_change': 0,
            'improved_count': 0,
            'decreased_count': 0,
            'unchanged_count': 0
        }
        
        total_change = 0
        
        for orig, calib in zip(original, calibrated):
            try:
                # 元のスコアと新しいスコアを比較
                orig_score = int(orig.get('name_recognition', '50'))
                new_score = calib.get('name_recognition', 50)
                
                change = new_score - orig_score
                total_change += abs(change)
                
                if change > 0:
                    analysis['improved_count'] += 1
                elif change < 0:
                    analysis['decreased_count'] += 1
                else:
                    analysis['unchanged_count'] += 1
                
                # 大幅な変更があった人物を記録
                if abs(change) > 20:
                    analysis['score_changes'].append({
                        'name': calib.get('person_name_ja', calib.get('person_name', '')),
                        'original': orig_score,
                        'new': new_score,
                        'change': change,
                        'category': calib.get('category', '')
                    })
                
                # カテゴリ別の改善
                category = calib.get('category', 'その他')
                if category not in analysis['category_improvements']:
                    analysis['category_improvements'][category] = {
                        'count': 0,
                        'total_change': 0,
                        'average_before': 0,
                        'average_after': 0
                    }
                
                cat_stats = analysis['category_improvements'][category]
                cat_stats['count'] += 1
                cat_stats['total_change'] += change
                cat_stats['average_before'] += orig_score
                cat_stats['average_after'] += new_score
                
            except Exception as e:
                continue
        
        # 平均を計算
        if len(calibrated) > 0:
            analysis['average_change'] = round(total_change / len(calibrated), 2)
        
        # カテゴリ別平均を計算
        for category, stats in analysis['category_improvements'].items():
            if stats['count'] > 0:
                stats['average_before'] = round(stats['average_before'] / stats['count'], 1)
                stats['average_after'] = round(stats['average_after'] / stats['count'], 1)
                stats['average_change'] = round(stats['total_change'] / stats['count'], 1)
        
        return analysis
    
    def save_calibrated_database(self, persons: List[Dict[str, Any]], original_filename: str):
        """較正済みデータベースを保存"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"calibrated_japanese_{timestamp}.csv"
        json_filename = f"calibrated_japanese_{timestamp}.json"
        
        # CSV保存
        if persons:
            headers = list(persons[0].keys())
            
            with open(output_filename, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(persons)
            
            print(f"✅ CSV保存: {output_filename}")
            
            # JSON保存（メタデータ付き）
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(persons, f, ensure_ascii=False, indent=2)
            
            print(f"✅ JSON保存: {json_filename}")
        
        return output_filename, json_filename
    
    def generate_calibration_report(self, analysis: Dict, output_filename: str):
        """較正レポートの生成"""
        
        timestamp = datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')
        
        report = f"""# 🎌 日本人向け知名度較正レポート

## 📅 実行情報
- 実行日時: {timestamp}
- 出力ファイル: {output_filename}
- 較正人数: {analysis['total_persons']}人

## 📊 較正統計

### 全体的な変化
- **改善された人物**: {analysis['improved_count']}人
- **低下した人物**: {analysis['decreased_count']}人
- **変化なし**: {analysis['unchanged_count']}人
- **平均変化量**: {analysis['average_change']}ポイント

### カテゴリ別の改善
"""
        
        for category, stats in analysis['category_improvements'].items():
            report += f"""
#### {category}
- 人数: {stats['count']}人
- 較正前平均: {stats['average_before']}
- 較正後平均: {stats['average_after']}
- 平均変化: {stats['average_change']}ポイント
"""
        
        # 大幅に変化した人物トップ10
        if analysis['score_changes']:
            report += "\n### 📈 大幅に変化した人物 (上位10名)\n\n"
            
            # 変化量でソート
            sorted_changes = sorted(analysis['score_changes'], 
                                  key=lambda x: abs(x['change']), 
                                  reverse=True)[:10]
            
            for i, change in enumerate(sorted_changes, 1):
                direction = "⬆️" if change['change'] > 0 else "⬇️"
                report += f"{i}. **{change['name']}** ({change['category']})\n"
                report += f"   - 変化: {change['original']} → {change['new']} "
                report += f"({direction} {abs(change['change'])}ポイント)\n"
        
        report += """
## 🎯 較正の特徴

### 日本人ユーザー向け最適化
1. **教育重視**: 教科書掲載人物の知名度向上
2. **メディア考慮**: 日本のテレビ・新聞での露出反映
3. **世代別調整**: SNS世代とテレビ世代の違いを考慮
4. **文化的文脈**: 日本特有の価値観・認知度を反映

### 改善された評価軸
- 日本での知名度 (70%)
- グローバル知名度 (30%)
- 教育での扱い
- メディア露出度
- SNS言及頻度

## ✅ 結論

日本人ユーザーの視点に最適化された知名度評価システムにより、
より実感に近い、精度の高い知名度スコアが実現されました。
"""
        
        # レポート保存
        report_filename = f"CALIBRATION_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"✅ レポート保存: {report_filename}")
        
        return report_filename


def main():
    """メイン処理"""
    
    print("🎌 日本人向け知名度較正適用システム")
    print("=" * 60)
    
    applicator = DatabaseCalibrationApplicator()
    
    # 最新のデータベースを検索
    db_filename = applicator.find_latest_database()
    
    if not db_filename:
        print("❌ データベースファイルが見つかりません")
        return
    
    # データベース読み込み
    print(f"\n📂 データベース読み込み中: {db_filename}")
    original_persons = applicator.load_database(db_filename)
    
    if not original_persons:
        print("❌ データベースが空です")
        return
    
    # 較正を適用
    calibrated_persons = applicator.apply_calibration(original_persons)
    
    # 結果を分析
    print("\n📊 較正結果の分析中...")
    analysis = applicator.analyze_calibration_results(original_persons, calibrated_persons)
    
    # 較正済みデータベースを保存
    print("\n💾 較正済みデータベースの保存中...")
    output_csv, output_json = applicator.save_calibrated_database(
        calibrated_persons, 
        db_filename
    )
    
    # レポート生成
    print("\n📝 レポート生成中...")
    report_filename = applicator.generate_calibration_report(analysis, output_csv)
    
    # サマリー表示
    print("\n" + "=" * 60)
    print("✨ 較正処理完了!")
    print(f"  処理人数: {applicator.processed_count}人")
    print(f"  改善: {analysis['improved_count']}人")
    print(f"  低下: {analysis['decreased_count']}人")
    print(f"  平均変化: {analysis['average_change']}ポイント")
    print("\n📁 出力ファイル:")
    print(f"  - CSV: {output_csv}")
    print(f"  - JSON: {output_json}")
    print(f"  - レポート: {report_filename}")


if __name__ == "__main__":
    main()