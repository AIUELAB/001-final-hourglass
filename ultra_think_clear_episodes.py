#!/usr/bin/env python3
"""
Ultra Think エピソードフィールドクリアシステム
エピソード関連7フィールドを空にして人物マスターデータを作成
"""
import csv
import json
from datetime import datetime
from typing import Dict, List
import os

class UltraThinkEpisodeClearer:
    def __init__(self):
        # クリア対象のエピソードフィールド
        self.episode_fields_to_clear = [
            'episode_title',
            'episode_text', 
            'episode_year',
            'episode_date',
            'episode_type',
            'age',
            'age_months'
        ]
        
        self.stats = {
            'total_input': 0,
            'unique_persons': 0,
            'duplicates_merged': 0,
            'fields_cleared': 0,
            'total_output': 0
        }
        
        self.person_dict = {}  # person_name をキーとする辞書
    
    def calculate_person_quality(self, row: Dict) -> float:
        """人物データの品質スコアを計算"""
        score = 0.0
        
        # 1. name_recognition（最大40点）
        try:
            recognition = float(row.get('name_recognition', 0))
            score += recognition * 0.4  # 0-100 → 0-40点
        except (ValueError, TypeError):
            pass
        
        # 2. accuracy_score（最大20点）
        try:
            accuracy = float(row.get('accuracy_score', 0))
            score += accuracy * 4  # 1-5 → 4-20点
        except (ValueError, TypeError):
            pass
        
        # 3. impact_score（最大20点）  
        try:
            impact = float(row.get('impact_score', 0))
            score += impact * 4  # 1-5 → 4-20点
        except (ValueError, TypeError):
            pass
        
        # 4. 人物情報の完全性（最大20点）
        person_fields = ['person_name', 'person_name_ja', 'person_name_display', 
                        'category', 'nationality', 'occupation', 'era']
        completeness = sum(1 for field in person_fields if row.get(field))
        score += completeness * (20 / 7)
        
        return score
    
    def clear_episode_fields(self, row: Dict) -> Dict:
        """エピソードフィールドをクリア"""
        cleared_row = row.copy()
        for field in self.episode_fields_to_clear:
            if field in cleared_row:
                cleared_row[field] = ''
                self.stats['fields_cleared'] += 1
        return cleared_row
    
    def process_file(self, input_file: str) -> str:
        """ファイル処理メイン"""
        print("🚀 Ultra Think エピソードクリア処理開始...")
        print(f"  入力: {input_file}")
        
        # 出力ファイル名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"ultra_think_person_master_{timestamp}.csv"
        
        # 1. データ読み込みと処理
        print("\n📂 データ読み込み中...")
        with open(input_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            
            for row_num, row in enumerate(reader, 1):
                self.stats['total_input'] += 1
                
                # エピソードフィールドをクリア
                cleared_row = self.clear_episode_fields(row)
                
                # 品質スコア計算
                cleared_row['_quality_score'] = self.calculate_person_quality(cleared_row)
                
                # person_nameで集約
                person_name = cleared_row.get('person_name', '').strip()
                
                if not person_name:
                    # person_nameが空の場合はperson_name_jaを使用
                    person_name = cleared_row.get('person_name_ja', '').strip()
                
                if person_name:
                    if person_name in self.person_dict:
                        # 既存の人物と比較して品質が高い方を保持
                        existing_quality = self.person_dict[person_name].get('_quality_score', 0)
                        new_quality = cleared_row.get('_quality_score', 0)
                        
                        if new_quality > existing_quality:
                            self.person_dict[person_name] = cleared_row
                        
                        self.stats['duplicates_merged'] += 1
                    else:
                        # 新規人物
                        self.person_dict[person_name] = cleared_row
                
                # 進捗表示
                if row_num % 10000 == 0:
                    print(f"  処理中... {row_num:,}件完了")
        
        print(f"  ✅ 読み込み完了: {self.stats['total_input']:,}件")
        
        # 2. 人物マスターファイル書き出し
        print("\n📝 人物マスターファイル書き出し中...")
        
        # person_idを再割り当て
        sorted_persons = sorted(self.person_dict.values(), 
                               key=lambda x: (x.get('person_name', ''), 
                                            x.get('person_name_ja', '')))
        
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            # _quality_scoreを除外
            output_fields = [field for field in fieldnames if not field.startswith('_')]
            writer = csv.DictWriter(f, fieldnames=output_fields)
            writer.writeheader()
            
            for idx, person_data in enumerate(sorted_persons, 1):
                # person_idを更新
                person_data['person_id'] = f"P{idx:06d}"
                
                # メタデータを削除して書き込み
                clean_data = {k: v for k, v in person_data.items() if not k.startswith('_')}
                writer.writerow(clean_data)
                self.stats['total_output'] += 1
        
        self.stats['unique_persons'] = len(self.person_dict)
        
        print(f"  ✅ 書き出し完了: {self.stats['total_output']:,}人")
        
        # 3. レポート作成
        self.create_report(timestamp, output_file, input_file)
        
        return output_file
    
    def create_report(self, timestamp: str, output_file: str, input_file: str):
        """処理レポート作成"""
        report = f"""# 🎯 Ultra Think 人物マスター作成レポート

## 📅 実行情報
- 実行日時: {datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}
- 入力ファイル: {input_file}
- 出力ファイル: {output_file}

## 📊 処理統計

### 入力データ
- **総エピソード数**: {self.stats['total_input']:,}件
- **クリアしたフィールド数**: {self.stats['fields_cleared']:,}個

### エピソードフィールドクリア
以下の7フィールドを空にしました：
- episode_title（エピソードタイトル）
- episode_text（エピソード本文）
- episode_year（発生年）
- episode_date（発生日）
- episode_type（エピソードタイプ）
- age（エピソード時の年齢）
- age_months（エピソード時の月齢）

### 人物統合結果
- **ユニーク人物数**: {self.stats['unique_persons']:,}人
- **重複マージ数**: {self.stats['duplicates_merged']:,}件
- **最終出力人物数**: {self.stats['total_output']:,}人
- **データ圧縮率**: {(1 - self.stats['total_output'] / max(self.stats['total_input'], 1)) * 100:.1f}%

## ✅ 保持データ
以下の17フィールドは維持されています：

### 識別情報
- episode_id, person_id, episode_hash

### 人物情報
- person_name（原語・英語表記）
- person_name_ja（日本語正式表記）
- person_name_display（アプリ表示用）

### 分類情報
- category（大分類）
- nationality（国籍・出身国）
- occupation（職業・肩書き）
- era（時代区分）

### 品質指標
- name_recognition（知名度スコア）
- accuracy_score（事実確認度）
- impact_score（インパクトスコア）

### システム
- source（出典）
- created_at（作成日時）
- is_published（公開フラグ）
- extended_data（追加情報）

## 🎯 次のステップ
1. 新しいエピソード生成ルールの策定
2. AIによる高品質エピソード再生成
3. 年齢別エピソードの体系的作成

## 🏆 成果
エピソードフィールドをクリアし、**{self.stats['unique_persons']:,}人の人物マスターデータ**を作成しました。
これは新しいエピソード生成の基盤となります。
"""
        
        report_file = f"ULTRA_THINK_PERSON_MASTER_REPORT_{timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n📋 レポート: {report_file}")
        
        # 統計情報をJSON保存
        stats_file = f"ultra_think_person_master_stats_{timestamp}.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)
        
        print(f"📊 統計: {stats_file}")

def main():
    clearer = UltraThinkEpisodeClearer()
    
    # 入力ファイル
    input_file = "ultra_think_master_20250827_053251.csv"
    
    # ファイル存在確認
    if not os.path.exists(input_file):
        print(f"❌ ファイルが見つかりません: {input_file}")
        return None
    
    # 処理実行
    output_file = clearer.process_file(input_file)
    
    print("\n" + "=" * 50)
    print("✨ Ultra Think エピソードクリア完了!")
    print(f"📁 人物マスター: {output_file}")
    print("=" * 50)
    
    return output_file

if __name__ == "__main__":
    main()