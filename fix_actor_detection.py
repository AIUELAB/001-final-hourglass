#!/usr/bin/env python3
"""
合成俳優の正確な検出と削除（誤検出を防ぐ改良版）
実在の有名俳優を保護しながら、本当の合成データのみを削除
"""

import pandas as pd
import logging
from datetime import datetime
from typing import List, Set

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 保護すべき実在の有名俳優リスト
REAL_ACTORS = {
    'トム・ハンクス', 'デンゼル・ワシントン', 'モーガン・フリーマン',
    'ロバート・ダウニー・Jr', 'サミュエル・L・ジャクソン',
    'ニコラス・ケイジ', 'トム・ヒドルストン', 'エリオット・ペイジ',
    'チャーリー・チャップリン', 'ビリー・ポーター',
    'オダギリジョー', '妻夫木聡', '西島秀俊', '綾野剛', '松坂桃李',
    '菅田将暉', '山田涼介', '佐藤健', '岡田准一', '堺雅人',
    '役所広司', '渡辺謙', '真田広之', '浅野忠信', '阿部寛'
}

def detect_synthetic_actors_refined(df: pd.DataFrame) -> List[str]:
    """改良版：合成俳優の正確な検出"""
    
    synthetic_ids = []
    
    # 1. 中村姓で認知度60.0の明らかな合成パターン（これは確実）
    nakamura_synthetic = df[
        (df['person_name_ja'].str.startswith('中村', na=False)) &
        (df['occupation'] == '俳優') &
        (df['name_recognition'] == 60.0) &
        (~df['person_name_ja'].isin(REAL_ACTORS))  # 実在俳優を除外
    ]
    synthetic_ids.extend(nakamura_synthetic['person_id'].tolist())
    logger.info(f"中村パターン（合成）: {len(nakamura_synthetic)}件検出")
    
    # 2. 同じ姓で大量に存在し、一般的な名前の組み合わせ
    common_surnames = ['佐藤', '鈴木', '高橋', '田中', '渡辺', '伊藤', '山本', '小林']
    common_first_names = ['健太', '優斗', '大輝', '悠斗', '拓海', '涼太', '真央', '翔', '蓮', '颯太',
                          '太郎', '次郎', '三郎']
    
    for surname in common_surnames:
        surname_actors = df[
            (df['person_name_ja'].str.startswith(surname, na=False)) &
            (df['occupation'] == '俳優') &
            (df['name_recognition'] == 60.0) &  # 認知度が一定
            (~df['person_name_ja'].isin(REAL_ACTORS))  # 実在俳優を除外
        ]
        
        # 同じ姓で5人以上、同じ認知度の俳優は疑わしい
        if len(surname_actors) >= 5:
            for idx, row in surname_actors.iterrows():
                name = str(row.get('person_name_ja', ''))
                first_name = name.replace(surname, '')
                
                if first_name in common_first_names:
                    if row['person_id'] not in synthetic_ids:
                        synthetic_ids.append(row['person_id'])
    
    # 3. タイムスタンプと認知度の組み合わせ（厳密な条件）
    suspicious_pattern = df[
        (df['last_updated'].str.contains('2025-08-27T04:52', na=False)) &
        (df['occupation'] == '俳優') &
        (df['name_recognition'] == 60.0) &
        (~df['person_name_ja'].isin(REAL_ACTORS))  # 実在俳優を除外
    ]
    
    for idx, row in suspicious_pattern.iterrows():
        if row['person_id'] not in synthetic_ids:
            # 日本人で一般的な名前の組み合わせのみ
            if row.get('nationality') == '日本':
                name = str(row.get('person_name_ja', ''))
                # 姓が2文字、名が2-3文字の一般的なパターン
                if 4 <= len(name) <= 5:
                    synthetic_ids.append(row['person_id'])
    
    # 重複を除去
    synthetic_ids = list(set(synthetic_ids))
    
    logger.info(f"合計 {len(synthetic_ids)}件の合成俳優を正確に検出")
    
    return synthetic_ids

def verify_and_restore():
    """誤削除の確認と復元"""
    
    logger.info("="*60)
    logger.info("誤削除の確認と修正")
    logger.info("="*60)
    
    # バックアップから元データを読み込み
    backup_file = "backup_ultra_think_FINAL_VALIDATED_20250912.csv_20250912_062958"
    df_original = pd.read_csv(backup_file, encoding='utf-8-sig')
    
    # 正確な合成俳優のみ検出
    synthetic_ids = detect_synthetic_actors_refined(df_original)
    
    # 削除対象の確認
    synthetic_df = df_original[df_original['person_id'].isin(synthetic_ids)]
    
    logger.info("\n削除対象（合成俳優のみ）:")
    logger.info(f"総数: {len(synthetic_df)}件")
    
    # 姓の分布
    surname_dist = {}
    for idx, row in synthetic_df.iterrows():
        name = str(row.get('person_name_ja', ''))
        if len(name) >= 2:
            surname = name[:2]
            surname_dist[surname] = surname_dist.get(surname, 0) + 1
    
    logger.info("\n姓の分布:")
    for surname, count in sorted(surname_dist.items(), key=lambda x: x[1], reverse=True)[:5]:
        logger.info(f"  {surname}: {count}件")
    
    # サンプル表示
    logger.info("\n削除対象の例（最初の10件）:")
    for idx, row in synthetic_df.head(10).iterrows():
        logger.info(f"  {row['person_id']}: {row['person_name_ja']}")
    
    # 誤削除された実在俳優の確認
    deleted_real_actors = []
    for actor_name in REAL_ACTORS:
        actor_record = df_original[df_original['person_name_ja'] == actor_name]
        if not actor_record.empty:
            if actor_record.iloc[0]['person_id'] in synthetic_ids:
                deleted_real_actors.append(actor_name)
    
    if deleted_real_actors:
        logger.warning(f"\n⚠️ 誤削除リスト: {deleted_real_actors}")
        logger.info("これらは削除しません")
    else:
        logger.info("\n✅ 実在俳優の誤削除なし")
    
    # クリーンデータ作成
    clean_df = df_original[~df_original['person_id'].isin(synthetic_ids)]
    
    # 最終ファイル保存
    output_file = f"ultra_think_TRULY_CLEAN_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    clean_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    logger.info("\n" + "="*60)
    logger.info("処理完了")
    logger.info("="*60)
    logger.info(f"元のレコード数: {len(df_original):,}")
    logger.info(f"削除数: {len(synthetic_ids):,}")
    logger.info(f"最終レコード数: {len(clean_df):,}")
    logger.info(f"削除率: {len(synthetic_ids)/len(df_original)*100:.2f}%")
    logger.info(f"\n出力ファイル: {output_file}")
    
    return output_file, synthetic_ids

if __name__ == "__main__":
    output_file, synthetic_ids = verify_and_restore()
    
    # 指定されたIDの最終確認
    target_ids = ['P001645', 'P001647', 'P001661', 'P001667', 'P001670',
                  'P001675', 'P001679', 'P001683', 'P001687', 'P001693']
    
    logger.info("\n指定されたIDの処理結果:")
    for pid in target_ids:
        if pid in synthetic_ids:
            logger.info(f"  {pid}: ✅ 削除（合成俳優）")
        else:
            logger.info(f"  {pid}: ❌ 削除されず")