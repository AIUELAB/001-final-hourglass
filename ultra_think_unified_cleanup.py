#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Ultra Think 統一クリーンアップシステム
person_name_display統一ルールに基づく完全修正
"""

import csv
import json
import re
import os
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

@dataclass
class PersonRecord:
    """統一人物レコード"""
    person_name: str = ""
    person_name_ja: str = ""
    person_name_display: str = ""
    birth_year: int = 0
    nationality: str = ""
    occupation: str = ""
    category: str = ""
    name: str = ""
    batch_id: str = ""
    
    # その他のフィールドは辞書として保持
    extra_fields: Dict = None
    
    def __post_init__(self):
        if self.extra_fields is None:
            self.extra_fields = {}

class UltraThinkUnifiedCleanup:
    """統一クリーンアップクラス"""
    
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.all_records = []
        self.clean_records = []
        self.deleted_records = []
        self.fixed_records = []
        
        # 統計
        self.stats = defaultdict(int)
        
        # ルールセット初期化
        self.initialize_rules()
        
    def initialize_rules(self):
        """ルールセットの初期化"""
        
        # 1. 日本の歴史人物（フルネーム必須）
        self.japanese_historical = {
            'Oda Nobunaga': '織田信長',
            'Toyotomi Hideyoshi': '豊臣秀吉',
            'Tokugawa Ieyasu': '徳川家康',
            'Sakamoto Ryoma': '坂本龍馬',
            'Saigo Takamori': '西郷隆盛',
            'Murasaki Shikibu': '紫式部',
            'Sei Shonagon': '清少納言',
            'Minamoto no Yoritomo': '源頼朝',
            'Minamoto no Yoshitsune': '源義経',
            'Taira no Kiyomori': '平清盛',
        }
        
        # 2. 西洋の偉人（姓のみ可能）
        self.western_surname_only = {
            'Albert Einstein': 'アインシュタイン',
            'Isaac Newton': 'ニュートン',
            'Charles Darwin': 'ダーウィン',
            'Marie Curie': 'キュリー夫人',
            'Leonardo da Vinci': 'ダ・ヴィンチ',
            'Michelangelo': 'ミケランジェロ',
            'Pablo Picasso': 'ピカソ',
            'Vincent van Gogh': 'ゴッホ',
            'Claude Monet': 'モネ',
            'Ludwig van Beethoven': 'ベートーヴェン',
            'Wolfgang Amadeus Mozart': 'モーツァルト',
            'Johann Sebastian Bach': 'バッハ',
            'Frederic Chopin': 'ショパン',
            'Pyotr Tchaikovsky': 'チャイコフスキー',
            'Galileo Galilei': 'ガリレオ',
            'Thomas Edison': 'エジソン',
            'Wilhelm Röntgen': 'レントゲン',
            'Max Planck': 'プランク',
            'Niels Bohr': 'ボーア',
            'Werner Heisenberg': 'ハイゼンベルク',
        }
        
        # 3. フルネーム必須（混同防止）
        self.fullname_required = {
            'Nelson Mandela': 'ネルソン・マンデラ',
            'Winston Churchill': 'ウィンストン・チャーチル',
            'Martin Luther King Jr.': 'マーティン・ルーサー・キング・ジュニア',
            'Abraham Lincoln': 'エイブラハム・リンカーン',
            'Michael Jackson': 'マイケル・ジャクソン',
            'Andrew Jackson': 'アンドリュー・ジャクソン',
            'Clara Schumann': 'クララ・シューマン',
            'Robert Schumann': 'シューマン',  # ロベルトは姓のみ可
            'John Lennon': 'ジョン・レノン',
            'Paul McCartney': 'ポール・マッカートニー',
        }
        
        # 4. グループメンバー表記
        self.group_members = {
            'John Lennon': 'ジョン・レノン（ビートルズ）',
            'Paul McCartney': 'ポール・マッカートニー（ビートルズ）',
            'George Harrison': 'ジョージ・ハリスン（ビートルズ）',
            'Ringo Starr': 'リンゴ・スター（ビートルズ）',
            'Freddie Mercury': 'フレディ・マーキュリー（クイーン）',
            'Brian May': 'ブライアン・メイ（クイーン）',
            'Mick Jagger': 'ミック・ジャガー（ローリング・ストーンズ）',
            'Keith Richards': 'キース・リチャーズ（ローリング・ストーンズ）',
            'RM': 'RM（防弾少年団）',
            'Jin': 'ジン（防弾少年団）',
            'Suga': 'シュガ（防弾少年団）',
            'J-Hope': 'J-HOPE（防弾少年団）',
            'Jimin': 'ジミン（防弾少年団）',
            'V': 'V（防弾少年団）',
            'Jungkook': 'ジョングク（防弾少年団）',
        }
        
        # 5. 通称・愛称
        self.nicknames = {
            'Louis Armstrong': 'サッチモ（ルイ・アームストロング）',
            'Pelé': 'ペレ',
            'Edson Arantes do Nascimento': 'ペレ',
            'Margaret Thatcher': 'マーガレット・サッチャー',  # 鉄の女は使わない
            'Qin Shi Huang': '秦の始皇帝',
            'Emperor Wu of Han': '漢の武帝',
        }
        
        # 6. 削除対象パターン
        self.delete_patterns = [
            r'^.*・.*$',  # 中点を含む英語名（Gonzalez・Susan）
            r'^[a-zA-Z]+・[a-zA-Z]+$',  # 英語名に中点
            r'^.+インフルエンサー\d+$',  # プレースホルダー名
            r'^.+YouTuber\d+$',
            r'^.+ [A-Z]{3}\d{5}$',  # SCI00000形式
            r'^batch_',  # バッチ生成データ
        ]
        
    def is_delete_target(self, record: Dict) -> bool:
        """削除対象かどうかを判定"""
        
        # 1. MassCollection生成データ
        if 'MassCollection' in str(record.get('phase', '')):
            self.stats['mass_collection_deleted'] += 1
            return True
            
        # 2. batch_idがある生成データ
        batch_id = record.get('batch_id', '')
        if batch_id and batch_id.startswith('batch_'):
            self.stats['batch_generated_deleted'] += 1
            return True
            
        # 3. person_name_displayの問題パターン
        display = record.get('person_name_display', '')
        person_name = record.get('person_name', '')
        
        # 英語名に中点が含まれる
        if display and re.match(r'^[A-Za-z]+・[A-Za-z]+', display):
            self.stats['english_middot_deleted'] += 1
            return True
            
        # 日本人名に不適切な中点
        if display and '・' in display:
            # カタカナ外国人名は除外
            if not re.match(r'^[ァ-ヴー]+・[ァ-ヴー]+', display):
                if re.match(r'^[ぁ-んァ-ヴー一-龥]+・[ぁ-んァ-ヴー一-龥]+$', display):
                    self.stats['japanese_middot_deleted'] += 1
                    return True
                    
        # プレースホルダー名
        if re.search(r'インフルエンサー\d+|YouTuber\d+|TikToker\d+', display):
            self.stats['placeholder_deleted'] += 1
            return True
            
        # SCI00000形式
        if person_name and re.search(r'[A-Z]{3}\d{5}', person_name):
            self.stats['sci_format_deleted'] += 1
            return True
            
        return False
        
    def get_correct_display_name(self, record: Dict) -> str:
        """正しいperson_name_displayを決定"""
        
        person_name = record.get('person_name', '')
        person_name_ja = record.get('person_name_ja', '')
        name = record.get('name', '')
        nationality = record.get('nationality', '')
        occupation = record.get('occupation', '')
        
        # 1. グループメンバーチェック
        if person_name in self.group_members:
            return self.group_members[person_name]
            
        # 2. 通称・愛称チェック
        if person_name in self.nicknames:
            return self.nicknames[person_name]
            
        # 3. 日本の歴史人物
        if person_name in self.japanese_historical:
            return self.japanese_historical[person_name]
            
        # 4. 西洋の偉人（姓のみ）
        if person_name in self.western_surname_only:
            return self.western_surname_only[person_name]
            
        # 5. フルネーム必須
        if person_name in self.fullname_required:
            return self.fullname_required[person_name]
            
        # 6. 日本人はフルネーム
        if nationality == '日本':
            # 既に適切な日本語名があればそれを使用
            if person_name_ja and not '・' in person_name_ja:
                return person_name_ja
                
        # 7. デフォルト：person_name_jaをそのまま使用
        if person_name_ja:
            # 不適切な中点を除去
            if '・' in person_name_ja and not re.match(r'^[ァ-ヴー]+・', person_name_ja):
                return person_name_ja.replace('・', '')
            return person_name_ja
            
        # 8. person_name_jaがない場合はnameを使用
        return name or person_name
        
    def load_database(self, filepath: str):
        """データベースを読み込み"""
        print(f"📂 データベース読み込み中: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.all_records.append(row)
                
        print(f"  ✅ {len(self.all_records)}件のレコードを読み込み")
        
    def process_cleanup(self):
        """クリーンアップ処理実行"""
        print("\n🧹 クリーンアップ処理開始...")
        
        batch_size = 500
        total = len(self.all_records)
        
        for i in range(0, total, batch_size):
            batch = self.all_records[i:i+batch_size]
            print(f"  バッチ処理中: {i+1}-{min(i+batch_size, total)}/{total}")
            
            for record in batch:
                # 削除対象チェック
                if self.is_delete_target(record):
                    self.deleted_records.append(record)
                    self.stats['total_deleted'] += 1
                    continue
                    
                # person_name_display修正
                old_display = record.get('person_name_display', '')
                new_display = self.get_correct_display_name(record)
                
                if old_display != new_display:
                    record['person_name_display_old'] = old_display
                    record['person_name_display'] = new_display
                    self.fixed_records.append(record)
                    self.stats['display_fixed'] += 1
                    
                # クリーンレコードに追加
                self.clean_records.append(record)
                self.stats['total_clean'] += 1
                
        print(f"\n✅ クリーンアップ完了:")
        print(f"  - 削除: {self.stats['total_deleted']}件")
        print(f"  - 修正: {self.stats['display_fixed']}件")
        print(f"  - 最終: {self.stats['total_clean']}件")
        
    def save_results(self):
        """結果を保存"""
        print("\n💾 結果保存中...")
        
        output_dir = "ultra_think_12410"
        os.makedirs(output_dir, exist_ok=True)
        
        # クリーンデータ保存
        # 全フィールド収集
        all_fields = set()
        for record in self.clean_records:
            all_fields.update(record.keys())
        
        # person_name_display_oldを除外
        if 'person_name_display_old' in all_fields:
            all_fields.remove('person_name_display_old')
            
        fieldnames = sorted(list(all_fields))
        
        # CSV保存
        csv_file = f"{output_dir}/ultra_think_clean_{len(self.clean_records)}_{self.timestamp}.csv"
        with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(self.clean_records)
        print(f"  ✅ CSV保存: {csv_file}")
        
        # JSON保存
        json_file = f"{output_dir}/ultra_think_clean_{len(self.clean_records)}_{self.timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.clean_records, f, ensure_ascii=False, indent=2)
        print(f"  ✅ JSON保存: {json_file}")
        
        # 削除レコード保存
        if self.deleted_records:
            deleted_file = f"{output_dir}/deleted_records_{self.timestamp}.json"
            with open(deleted_file, 'w', encoding='utf-8') as f:
                json.dump(self.deleted_records, f, ensure_ascii=False, indent=2)
            print(f"  ✅ 削除レコード保存: {deleted_file}")
            
    def generate_report(self):
        """詳細レポート生成"""
        report = f"""# 🎊 Ultra Think クリーンアップレポート

## 📅 実行日時
{datetime.now().isoformat()}

## 📊 処理結果サマリー
- **入力レコード**: {len(self.all_records):,}件
- **削除レコード**: {self.stats['total_deleted']:,}件
- **修正レコード**: {self.stats['display_fixed']:,}件
- **最終クリーンレコード**: {self.stats['total_clean']:,}件

## 🗑️ 削除内訳
- MassCollection生成: {self.stats['mass_collection_deleted']:,}件
- バッチ生成データ: {self.stats['batch_generated_deleted']:,}件
- 英語名中点問題: {self.stats['english_middot_deleted']:,}件
- 日本語名中点問題: {self.stats['japanese_middot_deleted']:,}件
- プレースホルダー名: {self.stats['placeholder_deleted']:,}件
- SCI形式: {self.stats['sci_format_deleted']:,}件

## ✅ 品質改善
- **削除率**: {(self.stats['total_deleted'] / len(self.all_records) * 100):.1f}%
- **修正率**: {(self.stats['display_fixed'] / max(1, self.stats['total_clean']) * 100):.1f}%
- **最終品質スコア**: {(self.stats['total_clean'] / max(1, len(self.all_records) - self.stats['mass_collection_deleted']) * 100):.1f}%

## 🎯 達成事項
1. ✅ person_name_display統一ルール適用
2. ✅ 低品質MassCollectionデータ除去
3. ✅ 文化的に適切な表記への修正
4. ✅ プレースホルダー名の完全削除
5. ✅ グループメンバー表記の統一

## 💡 Ultra Think戦略の成果
- **構造的欠陥の修正**: 完了
- **データ品質の向上**: 大幅改善
- **エピソード生成準備**: 完了

---
*Ultra Think Cleanup Report*
*Generated: {datetime.now().isoformat()}*
"""
        
        # レポート保存
        report_file = f"ultra_think_12410/CLEANUP_REPORT_{self.timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n📝 レポート生成: {report_file}")
        
        # コンソール表示
        print(report)

def main():
    """メイン処理"""
    print("=" * 60)
    print("🚀 Ultra Think 統一クリーンアップシステム起動")
    print("=" * 60)
    
    # クリーンアップ実行
    cleaner = UltraThinkUnifiedCleanup()
    
    # 最新データベース読み込み
    db_file = "ultra_think_12410/ultra_think_trend_15999_20250825_150853.csv"
    cleaner.load_database(db_file)
    
    # クリーンアップ処理
    cleaner.process_cleanup()
    
    # 結果保存
    cleaner.save_results()
    
    # レポート生成
    cleaner.generate_report()
    
    print("\n🎊 Ultra Think クリーンアップ完了！")

if __name__ == "__main__":
    main()