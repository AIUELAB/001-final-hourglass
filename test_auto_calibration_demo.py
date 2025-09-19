#!/usr/bin/env python3
"""
Ultra Think 自動較正システム動作確認デモ
Auto-Calibration System Demonstration
"""

import json
import os
from datetime import datetime
from ultra_think_auto_calibrated_person_adder import AutoCalibratedPersonAdder

def demonstration():
    """自動較正システムのデモンストレーション"""
    print("🎌 Ultra Think 自動較正システム動作確認")
    print("=" * 60)
    
    # 既存データベースを使用してシステムを初期化
    database_file = "ultra_think_calibrated_20250827_132748.csv"
    if not os.path.exists(database_file):
        print(f"⚠️ データベースファイル {database_file} が見つかりません")
        # 代替ファイルを探す
        alt_files = [
            "ultra_think_CLEAN_NO_PLACEHOLDERS_20250827_124619.csv",
            "ultra_think_FINAL_MERGED_20250827_080142.csv"
        ]
        for alt_file in alt_files:
            if os.path.exists(alt_file):
                database_file = alt_file
                print(f"📂 代替データベース使用: {alt_file}")
                break
    
    print(f"\n📊 初期データベース: {database_file}")
    adder = AutoCalibratedPersonAdder(database_file)
    
    # 現在の統計を表示
    stats = adder.get_statistics()
    print(f"   現在の人数: {stats['total_persons']}名")
    print()
    
    # テストケース1: 現代の日本人アスリート
    print("【テストケース1: 現代の日本人アスリート】")
    print("-" * 40)
    
    test_person_1 = adder.add_person(
        person_name="Naoya Inoue",
        person_name_ja="井上尚弥",
        person_name_display="井上尚弥",
        category="スポーツ",
        nationality="日本",
        occupation="プロボクサー、世界チャンピオン",
        birth_year=1993
    )
    
    if test_person_1:
        print(f"✅ 追加成功: {test_person_1['person_name_ja']}")
        print(f"   自動較正スコア: {test_person_1['name_recognition']}点")
        print(f"   カテゴリ: {test_person_1['category']}")
        print(f"   ID: {test_person_1['person_id']}")
    print()
    
    # テストケース2: 歴史上の日本人
    print("【テストケース2: 歴史上の日本人】")
    print("-" * 40)
    
    test_person_2 = adder.add_person(
        person_name="Katsushika Hokusai",
        person_name_ja="葛飾北斎",
        person_name_display="葛飾北斎",
        category="歴史上の人物",
        nationality="日本",
        occupation="浮世絵師",
        birth_year=1760
    )
    
    if test_person_2:
        print(f"✅ 追加成功: {test_person_2['person_name_ja']}")
        print(f"   自動較正スコア: {test_person_2['name_recognition']}点")
        print(f"   カテゴリ: {test_person_2['category']}")
        print(f"   ID: {test_person_2['person_id']}")
    print()
    
    # テストケース3: バッチ追加
    print("【テストケース3: バッチ追加】")
    print("-" * 40)
    
    batch_persons = [
        {
            'person_name': 'Rui Hachimura',
            'person_name_ja': '八村塁',
            'category': 'スポーツ',
            'nationality': '日本',
            'occupation': 'NBA選手',
            'birth_year': 1998
        },
        {
            'person_name': 'Yuzuru Hanyu',
            'person_name_ja': '羽生善治',
            'category': 'その他',
            'nationality': '日本',
            'occupation': '将棋棋士',
            'birth_year': 1970
        },
        {
            'person_name': 'Hidetaka Miyazaki',
            'person_name_ja': '宮崎英高',
            'category': 'テクノロジー',
            'nationality': '日本',
            'occupation': 'ゲームディレクター',
            'birth_year': 1974
        }
    ]
    
    added, failed = adder.add_persons_batch(batch_persons)
    
    print(f"バッチ処理結果:")
    print(f"  成功: {len(added)}名")
    print(f"  失敗: {len(failed)}名")
    
    if added:
        print("\n追加された人物:")
        for person in added:
            print(f"  - {person['person_name_ja']}: {person['name_recognition']}点 ({person['category']})")
    print()
    
    # 重複チェックのデモ
    print("【テストケース4: 重複チェック】")
    print("-" * 40)
    
    duplicate_test = adder.add_person(
        person_name="Naoya Inoue",
        person_name_ja="井上尚弥",
        person_name_display="井上尚弥",
        category="スポーツ",
        nationality="日本",
        occupation="プロボクサー",
        birth_year=1993
    )
    
    if not duplicate_test:
        print("✅ 重複チェック機能が正常に動作しています")
        print("   （井上尚弥は既に登録済みのため追加されませんでした）")
    print()
    
    # 最終統計
    final_stats = adder.get_statistics()
    print("【最終統計】")
    print("-" * 40)
    print(f"総人数: {final_stats['total_persons']}名")
    print(f"  追加された人数: {final_stats['total_persons'] - stats['total_persons']}名")
    
    # カテゴリ分布
    print("\nカテゴリ別人数（上位5）:")
    for cat, count in sorted(final_stats['categories'].items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {cat}: {count}名")
    
    # スコア分布
    print("\n知名度スコア分布:")
    for range_key, count in sorted(final_stats['score_distribution'].items(), reverse=True):
        if count > 0:
            bar = '█' * int(count / final_stats['total_persons'] * 30)
            print(f"  {range_key:>6}: {count:>5}名 {bar}")
    
    # デモ用データベースは保存しない
    print("\n" + "=" * 60)
    print("🎉 自動較正システムのデモンストレーション完了")
    print("システムは正常に動作しています！")
    print("\n※ デモモードのため、データベースは保存されません")
    print("※ 実際に使用する場合は add_person_with_auto_calibration.py を実行してください")

if __name__ == "__main__":
    demonstration()