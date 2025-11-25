#!/usr/bin/env python3
"""
Ultra Think マスターファイル統合システム
Firestore由来とcriminals由来の2つのデータセットを統合
"""
import csv
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Tuple
import os

class UltraThinkMergeMaster:
    def __init__(self):
        self.stats = {
            'firestore_episodes': 0,
            'criminals_episodes': 0,
            'total_merged': 0,
            'duplicates_found': 0,
            'duplicates_resolved': 0,
            'new_episodes_added': 0,
            'firestore_priority': 0,
            'criminals_priority': 0
        }

        self.duplicate_log = []

    def calculate_episode_quality(self, episode: Dict) -> float:
        """エピソードの品質スコアを計算"""
        score = 0.0

        # 1. エピソードテキストの長さ（最大30点）
        text_length = len(episode.get('episode_text', ''))
        if text_length > 200:
            score += 30
        elif text_length > 100:
            score += 20
        elif text_length > 50:
            score += 10
        else:
            score += 5

        # 2. accuracy_score（最大25点）
        try:
            accuracy = float(episode.get('accuracy_score', 0))
            score += accuracy * 5  # 1-5 → 5-25点
        except (ValueError, TypeError):
            pass

        # 3. impact_score（最大25点）
        try:
            impact = float(episode.get('impact_score', 0))
            score += impact * 5  # 1-5 → 5-25点
        except (ValueError, TypeError):
            pass

        # 4. name_recognition（最大10点）
        try:
            recognition = float(episode.get('name_recognition', 0))
            score += recognition / 10  # 0-100 → 0-10点
        except (ValueError, TypeError):
            pass

        # 5. フィールド完全性（最大10点）
        required_fields = ['episode_title', 'episode_year', 'episode_type', 'source']
        completeness = sum(1 for field in required_fields if episode.get(field))
        score += completeness * 2.5

        return score

    def create_duplicate_key(self, episode: Dict) -> str:
        """重複判定用のキーを生成（person_name + age）"""
        person_name = episode.get('person_name', '').strip()
        age = str(episode.get('age', '')).strip()
        return f"{person_name}_{age}"

    def merge_files(self, firestore_file: str, criminals_file: str) -> str:
        """2つのファイルを統合"""
        print("🚀 Ultra Think マスター統合開始...")

        # 出力ファイル名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"ultra_think_master_{timestamp}.csv"

        # エピソード格納用辞書（キー: person_name_age）
        episodes_dict = {}

        # 1. Firestore由来データを読み込み（優先）
        print("\n📂 Firestore由来データ読み込み中...")
        with open(firestore_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames

            for row in reader:
                self.stats['firestore_episodes'] += 1
                key = self.create_duplicate_key(row)

                # ソース情報を追加
                row['_source'] = 'firestore'
                row['_quality_score'] = self.calculate_episode_quality(row)

                episodes_dict[key] = row

                if self.stats['firestore_episodes'] % 500 == 0:
                    print(f"  処理中... {self.stats['firestore_episodes']:,}件")

        print(f"  ✅ Firestore: {self.stats['firestore_episodes']:,}件読み込み完了")

        # 2. Criminals由来データを読み込み
        print("\n📂 Criminals由来データ読み込み中...")
        with open(criminals_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            for row in reader:
                self.stats['criminals_episodes'] += 1
                key = self.create_duplicate_key(row)

                # ソース情報を追加
                row['_source'] = 'criminals'
                row['_quality_score'] = self.calculate_episode_quality(row)

                # 重複チェック
                if key in episodes_dict:
                    self.stats['duplicates_found'] += 1

                    # 品質比較
                    existing = episodes_dict[key]
                    existing_quality = existing['_quality_score']
                    new_quality = row['_quality_score']

                    # 重複ログ記録
                    self.duplicate_log.append({
                        'key': key,
                        'person_name': row.get('person_name'),
                        'age': row.get('age'),
                        'firestore_quality': existing_quality,
                        'criminals_quality': new_quality,
                        'selected': 'firestore' if existing_quality >= new_quality else 'criminals'
                    })

                    # 品質が高い方を保持（同点ならFirestore優先）
                    if new_quality > existing_quality:
                        episodes_dict[key] = row
                        self.stats['criminals_priority'] += 1
                    else:
                        self.stats['firestore_priority'] += 1

                    self.stats['duplicates_resolved'] += 1
                else:
                    # 新規エピソード
                    episodes_dict[key] = row
                    self.stats['new_episodes_added'] += 1

                if self.stats['criminals_episodes'] % 10000 == 0:
                    print(f"  処理中... {self.stats['criminals_episodes']:,}件")

        print(f"  ✅ Criminals: {self.stats['criminals_episodes']:,}件読み込み完了")

        # 3. 統合データを書き出し
        print("\n📝 統合ファイル書き出し中...")
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            # _source と _quality_score を除外してフィールド名を設定
            output_fields = [field for field in fieldnames if not field.startswith('_')]
            writer = csv.DictWriter(f, fieldnames=output_fields)
            writer.writeheader()

            # person_name と age でソート
            sorted_episodes = sorted(episodes_dict.values(),
                                    key=lambda x: (x.get('person_name', ''),
                                                 int(x.get('age', 0)) if x.get('age') else 0))

            for episode in sorted_episodes:
                # メタデータフィールドを削除
                clean_episode = {k: v for k, v in episode.items() if not k.startswith('_')}
                writer.writerow(clean_episode)
                self.stats['total_merged'] += 1

        print(f"  ✅ 統合完了: {self.stats['total_merged']:,}件")

        # 4. レポート作成
        self.create_report(timestamp, output_file)

        return output_file

    def create_report(self, timestamp: str, output_file: str):
        """統合レポート作成"""
        report = f"""# 🎯 Ultra Think マスター統合レポート

## 📅 実行情報
- 実行日時: {datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}
- 出力ファイル: {output_file}

## 📊 統合統計

### 入力データ
- **Firestore由来**: {self.stats['firestore_episodes']:,}エピソード
- **Criminals由来**: {self.stats['criminals_episodes']:,}エピソード
- **入力合計**: {self.stats['firestore_episodes'] + self.stats['criminals_episodes']:,}エピソード

### 重複処理
- **重複検出数**: {self.stats['duplicates_found']:,}件
- **重複解決数**: {self.stats['duplicates_resolved']:,}件
- **Firestore優先**: {self.stats['firestore_priority']:,}件
- **Criminals優先**: {self.stats['criminals_priority']:,}件

### 統合結果
- **新規追加**: {self.stats['new_episodes_added']:,}エピソード
- **最終統合数**: {self.stats['total_merged']:,}エピソード
- **削減数**: {(self.stats['firestore_episodes'] + self.stats['criminals_episodes']) - self.stats['total_merged']:,}エピソード

## 📈 効率性
- **重複率**: {(self.stats['duplicates_found'] / max(self.stats['criminals_episodes'], 1) * 100):.1f}%
- **データ圧縮率**: {(1 - self.stats['total_merged'] / max(self.stats['firestore_episodes'] + self.stats['criminals_episodes'], 1)) * 100:.1f}%

## 🔍 重複処理詳細
"""

        # 重複の上位10件を表示
        if self.duplicate_log:
            report += "\n### 重複エピソード例（上位10件）\n"
            report += "| 人物名 | 年齢 | Firestore品質 | Criminals品質 | 選択 |\n"
            report += "|-------|------|--------------|--------------|------|\n"

            for dup in self.duplicate_log[:10]:
                report += f"| {dup['person_name']} | {dup['age']} | "
                report += f"{dup['firestore_quality']:.1f} | "
                report += f"{dup['criminals_quality']:.1f} | "
                report += f"{dup['selected']} |\n"

        report += f"""
## ✅ 品質保証
- person_name + age による重複排除
- 品質スコアベースの選択（テキスト長、accuracy、impact等）
- Firestore由来を優先（同品質の場合）
- 24フィールド形式維持

## 🎉 統合成功
{self.stats['total_merged']:,}件のユニークなエピソードを含むマスターファイルが完成しました。
"""

        # レポート保存
        report_file = f"ULTRA_THINK_MERGE_REPORT_{timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        # 重複ログ保存
        log_file = f"ultra_think_merge_duplicates_{timestamp}.json"
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(self.duplicate_log, f, ensure_ascii=False, indent=2)

        print(f"\n📋 レポート: {report_file}")
        print(f"🔍 重複ログ: {log_file}")

def main():
    merger = UltraThinkMergeMaster()

    # 統合対象ファイル
    firestore_file = "ultra_think_perfect_20250827_043032.csv"
    criminals_file = "ultra_think_converted_episodes_20250827_045202.csv"

    # ファイル存在確認
    if not os.path.exists(firestore_file):
        print(f"❌ ファイルが見つかりません: {firestore_file}")
        return

    if not os.path.exists(criminals_file):
        print(f"❌ ファイルが見つかりません: {criminals_file}")
        return

    # 統合実行
    output_file = merger.merge_files(firestore_file, criminals_file)

    print("\n" + "=" * 50)
    print("✨ Ultra Think マスター統合完了!")
    print(f"📁 マスターファイル: {output_file}")
    print("=" * 50)

    return output_file

if __name__ == "__main__":
    main()
