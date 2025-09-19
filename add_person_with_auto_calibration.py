#!/usr/bin/env python3
"""
Ultra Think 人物追加統合API
簡単なインターフェースで人物を追加し、自動的にname_recognitionを較正

使用例:
    python add_person_with_auto_calibration.py
    python add_person_with_auto_calibration.py --name "田中太郎" --category "スポーツ"
    python add_person_with_auto_calibration.py --batch batch_persons.json
"""

import json
import sys
import argparse
from typing import Dict, List
from ultra_think_auto_calibrated_person_adder import AutoCalibratedPersonAdder

class PersonAdditionInterface:
    """人物追加のための統合インターフェース"""
    
    def __init__(self):
        # 既存データベースを探す
        database_files = [
            "ultra_think_calibrated_20250827_132748.csv",
            "ultra_think_CLEAN_NO_PLACEHOLDERS_20250827_124619.csv",
            "ultra_think_CLEAN_FINAL_20250827.csv"
        ]
        
        existing_db = None
        for db_file in database_files:
            import os
            if os.path.exists(db_file):
                existing_db = db_file
                break
        
        self.adder = AutoCalibratedPersonAdder(existing_db)
        
    def interactive_add(self):
        """対話式で人物を追加"""
        print("\n🎌 Ultra Think 人物追加システム（自動較正機能付き）")
        print("=" * 60)
        print("※ 空白のままEnterで終了\n")
        
        added_count = 0
        
        while True:
            print(f"\n--- 新規人物追加 #{added_count + 1} ---")
            
            # 人物名（必須）
            person_name = input("人物名（英語/原語）: ").strip()
            if not person_name:
                break
            
            # 日本語名
            person_name_ja = input("日本語名: ").strip()
            if not person_name_ja:
                person_name_ja = person_name
            
            # 表示名
            person_name_display = input(f"表示名（空白で'{person_name_ja}'）: ").strip()
            if not person_name_display:
                person_name_display = person_name_ja
            
            # カテゴリ
            print("\nカテゴリ選択:")
            categories = [
                '1. エンタメ', '2. スポーツ', '3. 学術・科学',
                '4. ビジネス', '5. 政治', '6. 歴史上の人物',
                '7. 文化・芸術', '8. テクノロジー', '9. その他'
            ]
            for cat in categories:
                print(f"  {cat}")
            
            cat_choice = input("カテゴリ番号（1-9）: ").strip()
            category_map = {
                '1': 'エンタメ', '2': 'スポーツ', '3': '学術・科学',
                '4': 'ビジネス', '5': '政治', '6': '歴史上の人物',
                '7': '文化・芸術', '8': 'テクノロジー', '9': 'その他'
            }
            category = category_map.get(cat_choice, 'その他')
            
            # 国籍
            nationality = input("国籍（デフォルト: 日本）: ").strip()
            if not nationality:
                nationality = '日本'
            
            # 職業
            occupation = input("職業: ").strip()
            
            # 生年
            birth_year_str = input("生年（西暦、例: 1980）: ").strip()
            birth_year = None
            if birth_year_str:
                try:
                    birth_year = int(birth_year_str)
                except:
                    print("⚠️  生年は数値で入力してください")
            
            # 確認
            print("\n【入力確認】")
            print(f"  名前: {person_name} / {person_name_ja}")
            print(f"  表示名: {person_name_display}")
            print(f"  カテゴリ: {category}")
            print(f"  国籍: {nationality}")
            print(f"  職業: {occupation}")
            print(f"  生年: {birth_year if birth_year else '未設定'}")
            
            confirm = input("\nこの内容で追加しますか？ (y/n): ").strip().lower()
            if confirm != 'y':
                print("キャンセルしました")
                continue
            
            # 追加実行
            result = self.adder.add_person(
                person_name=person_name,
                person_name_ja=person_name_ja,
                person_name_display=person_name_display,
                category=category,
                nationality=nationality,
                occupation=occupation,
                birth_year=birth_year
            )
            
            if result:
                added_count += 1
                print(f"\n✅ 追加成功！")
                print(f"   人物ID: {result['person_id']}")
                print(f"   知名度スコア: {result['name_recognition']}点")
                
                # 較正の詳細を表示
                metadata = json.loads(result.get('recognition_metadata', '{}'))
                if metadata.get('auto_calibrated'):
                    print(f"   自動較正: 済み")
        
        if added_count > 0:
            # データベースを保存
            save = input(f"\n{added_count}名を追加しました。データベースを保存しますか？ (y/n): ").strip().lower()
            if save == 'y':
                self.adder.save_database()
        
        print("\n終了します")
    
    def batch_add(self, batch_file: str):
        """JSONファイルから一括追加"""
        print(f"\n📂 バッチファイル読み込み中: {batch_file}")
        
        try:
            with open(batch_file, 'r', encoding='utf-8') as f:
                persons_data = json.load(f)
            
            if not isinstance(persons_data, list):
                print("❌ JSONファイルはリスト形式である必要があります")
                return
            
            print(f"  {len(persons_data)}名のデータを読み込みました")
            
            # バッチ追加実行
            added, failed = self.adder.add_persons_batch(persons_data)
            
            # 結果表示
            print(f"\n📊 バッチ追加結果:")
            print(f"  成功: {len(added)}名")
            print(f"  失敗: {len(failed)}名")
            
            if added:
                print("\n【追加された人物（上位10名）】")
                for person in added[:10]:
                    print(f"  {person['person_name_ja']:<20} 知名度: {person['name_recognition']}点")
            
            if added:
                # データベースを保存
                self.adder.save_database()
                
        except FileNotFoundError:
            print(f"❌ ファイルが見つかりません: {batch_file}")
        except json.JSONDecodeError as e:
            print(f"❌ JSONファイルの解析エラー: {e}")
        except Exception as e:
            print(f"❌ エラーが発生しました: {e}")
    
    def quick_add(self, **kwargs):
        """コマンドライン引数から直接追加"""
        result = self.adder.add_person(**kwargs)
        
        if result:
            print(f"\n✅ 追加成功！")
            print(f"   人物: {result['person_name_ja']}")
            print(f"   知名度スコア: {result['name_recognition']}点")
            print(f"   カテゴリ: {result['category']}")
            
            # データベースを保存
            self.adder.save_database()
        else:
            print("\n❌ 追加に失敗しました（重複の可能性があります）")
    
    def show_statistics(self):
        """現在の統計を表示"""
        stats = self.adder.get_statistics()
        
        print("\n📊 データベース統計")
        print("=" * 60)
        print(f"総人数: {stats['total_persons']}名")
        
        print("\n【カテゴリ別】")
        for cat, count in sorted(stats['categories'].items(), key=lambda x: x[1], reverse=True)[:10]:
            bar = '█' * int(count / stats['total_persons'] * 50)
            print(f"  {cat:<15}: {count:>5}名 {bar}")
        
        print("\n【国籍別（上位10）】")
        for nat, count in sorted(stats['nationalities'].items(), key=lambda x: x[1], reverse=True)[:10]:
            bar = '█' * int(count / stats['total_persons'] * 50)
            print(f"  {nat:<10}: {count:>5}名 {bar}")
        
        print("\n【知名度スコア分布】")
        for range_key, count in sorted(stats['score_distribution'].items(), reverse=True):
            if count > 0:
                bar = '█' * int(count / stats['total_persons'] * 50)
                print(f"  {range_key:>6}: {count:>5}名 {bar}")


def create_sample_batch_file():
    """サンプルバッチファイルを作成"""
    sample_data = [
        {
            "person_name": "Hayao Miyazaki",
            "person_name_ja": "宮崎駿",
            "category": "文化・芸術",
            "nationality": "日本",
            "occupation": "アニメーション監督",
            "birth_year": 1941
        },
        {
            "person_name": "Haruki Murakami",
            "person_name_ja": "村上春樹",
            "category": "文化・芸術",
            "nationality": "日本",
            "occupation": "作家",
            "birth_year": 1949
        },
        {
            "person_name": "Yayoi Kusama",
            "person_name_ja": "草間彌生",
            "category": "文化・芸術",
            "nationality": "日本",
            "occupation": "芸術家",
            "birth_year": 1929
        }
    ]
    
    with open("sample_batch_persons.json", "w", encoding="utf-8") as f:
        json.dump(sample_data, f, ensure_ascii=False, indent=2)
    
    print("📄 サンプルファイル 'sample_batch_persons.json' を作成しました")


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description="Ultra Think 人物追加システム（自動較正機能付き）"
    )
    
    parser.add_argument('--name', help='人物名（英語/原語）')
    parser.add_argument('--name-ja', help='日本語名')
    parser.add_argument('--display', help='表示名')
    parser.add_argument('--category', default='その他', help='カテゴリ')
    parser.add_argument('--nationality', default='日本', help='国籍')
    parser.add_argument('--occupation', default='', help='職業')
    parser.add_argument('--birth-year', type=int, help='生年')
    parser.add_argument('--batch', help='バッチ追加用JSONファイル')
    parser.add_argument('--stats', action='store_true', help='統計情報を表示')
    parser.add_argument('--sample', action='store_true', help='サンプルバッチファイルを作成')
    
    args = parser.parse_args()
    
    # サンプル作成
    if args.sample:
        create_sample_batch_file()
        return
    
    interface = PersonAdditionInterface()
    
    # 統計表示
    if args.stats:
        interface.show_statistics()
        return
    
    # バッチ追加
    if args.batch:
        interface.batch_add(args.batch)
        return
    
    # クイック追加
    if args.name:
        interface.quick_add(
            person_name=args.name,
            person_name_ja=args.name_ja or args.name,
            person_name_display=args.display,
            category=args.category,
            nationality=args.nationality,
            occupation=args.occupation,
            birth_year=args.birth_year
        )
        return
    
    # 対話式追加
    interface.interactive_add()


if __name__ == "__main__":
    main()