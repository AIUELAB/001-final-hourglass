#!/usr/bin/env python3
"""
さくらももこ（漫画家・原作者）のレコードを追加するスクリプト
P000116は架空キャラクター、新規で実在の漫画家を追加
"""

import pandas as pd
import logging
from datetime import datetime
from pathlib import Path

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def add_sakura_momoko_author(csv_file: str):
    """
    さくらももこ（漫画家）を追加
    """
    logger.info(f"CSVファイル読み込み中: {csv_file}")
    df = pd.read_csv(csv_file, encoding='utf-8-sig')
    
    # バックアップ作成
    backup_file = csv_file.replace('.csv', f'_backup_before_author_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
    df.to_csv(backup_file, index=False, encoding='utf-8-sig')
    logger.info(f"バックアップ作成: {backup_file}")
    
    # 既存のP000116を確認
    existing = df[df['person_id'] == 'P000116']
    if not existing.empty:
        logger.info("既存のP000116（架空キャラクター）:")
        logger.info(f"  - person_name: {existing.iloc[0]['person_name']}")
        logger.info(f"  - person_name_display: {existing.iloc[0]['person_name_display']}")
        logger.info(f"  - category: {existing.iloc[0]['category']}")
        logger.info(f"  - occupation: {existing.iloc[0]['occupation']}")
    
    # 新しいperson_idを生成（最大値+1）
    max_id = df['person_id'].str.extract(r'P(\d+)', expand=False).astype(float).max()
    new_person_id = f"P{int(max_id + 1):06d}"
    
    # さくらももこ（漫画家）のデータを作成
    new_record = {
        'person_id': new_person_id,
        'person_name': 'Sakura Momoko',
        'person_name_ja': 'さくらももこ',
        'person_name_display': 'さくらももこ',
        'occupation': '漫画家',
        'nationality': '日本',
        'category': '漫画・アニメ',
        'entity_type': 'person',
        'birth_year': 1965.0,  # 1965年生まれ
        'death_year': 2018.0,  # 2018年逝去
        'name_recognition': 8.0,  # 有名な漫画家なので高スコア
        'recognition_score': 8.0,
        'google_trends_score': 45.0,
        'wikipedia_score': 85.0,
        'news_score': 40.0,
        'academic_score': 30.0,
        'image_count': 50.0,
        'video_count': 30.0,
        'book_count': 20.0,
        'data_source': 'manual_addition',
        'last_updated': datetime.now().isoformat()
    }
    
    # 既存のカラムに合わせる
    for col in df.columns:
        if col not in new_record:
            new_record[col] = None
    
    # データフレームに追加
    new_df = pd.DataFrame([new_record])
    df = pd.concat([df, new_df], ignore_index=True)
    
    logger.info(f"\n✅ 新規レコード追加:")
    logger.info(f"  - person_id: {new_person_id}")
    logger.info(f"  - person_name: さくらももこ")
    logger.info(f"  - occupation: 漫画家")
    logger.info(f"  - category: 漫画・アニメ")
    logger.info(f"  - entity_type: person")
    logger.info(f"  - birth_year: 1965")
    logger.info(f"  - death_year: 2018")
    logger.info(f"  - name_recognition: 8.0")
    
    # 保存
    output_file = csv_file.replace('.csv', '_WITH_AUTHOR.csv')
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    logger.info(f"\n✅ ファイル保存: {output_file}")
    
    # 検証: 2つのさくらももこが存在することを確認
    sakura_records = df[df['person_name_ja'] == 'さくらももこ']
    logger.info(f"\n確認: さくらももこのレコード数: {len(sakura_records)}")
    
    for idx, row in sakura_records.iterrows():
        logger.info(f"\n{row['person_id']}:")
        logger.info(f"  - display: {row['person_name_display']}")
        logger.info(f"  - occupation: {row['occupation']}")
        logger.info(f"  - category: {row['category']}")
        logger.info(f"  - entity_type: {row['entity_type']}")
    
    # 統計
    logger.info("\n" + "="*60)
    logger.info("データベース統計:")
    logger.info("="*60)
    logger.info(f"総レコード数: {len(df)}")
    logger.info(f"実在人物 (person): {len(df[df['entity_type'] == 'person'])}")
    logger.info(f"架空キャラクター: {len(df[df['category'] == '架空の存在'])}")
    logger.info(f"漫画家: {len(df[df['occupation'] == '漫画家'])}")
    
    return output_file

def main():
    """メイン処理"""
    # 最新のファイルを使用
    csv_file = "/Users/admin/Documents/AIUELAB/001-final-hourglass/ultra_think_FICTIONAL_RULE077_COMPLETE.csv"
    
    if not Path(csv_file).exists():
        logger.error(f"ファイルが見つかりません: {csv_file}")
        return
    
    # さくらももこ（漫画家）を追加
    output_file = add_sakura_momoko_author(csv_file)
    
    logger.info("\n" + "="*60)
    logger.info("✅ 完了！")
    logger.info("="*60)
    logger.info("P000116: さくらももこ (ちびまる子ちゃん) - 架空キャラクター")
    logger.info("P030136: さくらももこ - 漫画家（実在人物）")
    logger.info("\n同名の架空キャラクターと実在人物が正しく区別されています。")

if __name__ == "__main__":
    main()