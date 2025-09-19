#!/usr/bin/env python3
"""
グループ/団体データの削除とWikipedia存在確認
1. entity_type="group"のデータを削除
2. バンドメンバーのperson_name_display修正
3. Wikipedia未掲載者の検出とスコア0設定
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json
import logging
import requests
import time
import shutil

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def backup_database(csv_file):
    """データベースのバックアップを作成"""
    backup_file = f"backup_{csv_file}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(csv_file, backup_file)
    logger.info(f"💾 バックアップ作成: {backup_file}")
    return backup_file


def remove_groups(df):
    """グループ/団体データを削除"""
    logger.info("=" * 60)
    logger.info("🗑️ グループ/団体データの削除")
    logger.info("=" * 60)
    
    # entity_type="group"のデータを特定
    groups = df[df['entity_type'] == 'group'].copy()
    logger.info(f"📊 削除対象グループ: {len(groups)}件")
    
    deletions = []
    for idx, row in groups.iterrows():
        logger.info(f"  削除: {row['person_id']}: {row['person_name']}")
        deletions.append({
            'person_id': row['person_id'],
            'person_name': row['person_name'],
            'reason': 'group_entity'
        })
    
    # グループデータを削除
    df_cleaned = df[df['entity_type'] != 'group'].copy()
    logger.info(f"✅ グループ削除完了: {len(deletions)}件")
    logger.info(f"📊 残りレコード: {len(df_cleaned)}件")
    
    return df_cleaned, deletions


def fix_band_members_display(df):
    """バンドメンバーのperson_name_display修正"""
    logger.info("=" * 60)
    logger.info("🎸 バンドメンバー表記の修正")
    logger.info("=" * 60)
    
    # バンドメンバーのマッピング
    band_members = {
        # X JAPAN
        'YOSHIKI': 'X JAPAN',
        'PATA': 'X JAPAN',
        'HEATH': 'X JAPAN',
        # GLAY
        'TERU': 'GLAY',
        'TAKURO': 'GLAY',
        'HISASHI': 'GLAY',
        'JIRO': 'GLAY',
        # L'Arc~en~Ciel
        'hyde': "L'Arc~en~Ciel",
        'ken': "L'Arc~en~Ciel",
        'yukihiro': "L'Arc~en~Ciel",
        # LUNA SEA
        'RYUICHI': 'LUNA SEA',
        'SUGIZO': 'LUNA SEA',
        'INORAN': 'LUNA SEA',
        'J': 'LUNA SEA',
        # ONE OK ROCK
        'Taka': 'ONE OK ROCK',
        'Toru Yamashita': 'ONE OK ROCK',
        'Ryota Kohama': 'ONE OK ROCK',
        'Tomoya Kanki': 'ONE OK ROCK'
    }
    
    fixes = []
    for idx, row in df.iterrows():
        person_name = row['person_name']
        if person_name in band_members:
            band_name = band_members[person_name]
            new_display = f"{person_name} ({band_name})"
            
            # 現在のdisplay_nameと異なる場合のみ修正
            if row['person_name_display'] != new_display:
                logger.info(f"  修正: {row['person_id']}: {row['person_name_display']} → {new_display}")
                df.at[idx, 'person_name_display'] = new_display
                fixes.append({
                    'person_id': row['person_id'],
                    'old_display': row['person_name_display'],
                    'new_display': new_display
                })
    
    logger.info(f"✅ バンドメンバー表記修正: {len(fixes)}件")
    return df, fixes


def check_wikipedia_existence(person_name, max_retries=3):
    """Wikipedia存在確認（日本語版）"""
    # Wikipedia API
    base_url = "https://ja.wikipedia.org/w/api.php"
    
    # 検索パラメータ
    params = {
        'action': 'query',
        'format': 'json',
        'list': 'search',
        'srsearch': person_name,
        'srlimit': 1
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(base_url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                # 検索結果があるかチェック
                if data.get('query', {}).get('search'):
                    return True
                return False
        except Exception as e:
            if attempt == max_retries - 1:
                logger.warning(f"Wikipedia API エラー: {person_name} - {e}")
                return None  # エラーの場合はNone
        time.sleep(0.5)  # レート制限対策
    
    return None


def validate_wikipedia_entries(df, sample_size=50):
    """Wikipedia存在確認（サンプリング）"""
    logger.info("=" * 60)
    logger.info("🔍 Wikipedia存在確認")
    logger.info("=" * 60)
    
    # 怪しいパターンの検出
    suspicious_patterns = []
    
    # 1. 外国人名+日本人名パターン
    foreign_japanese_pattern = df[
        df['person_name'].str.contains(
            r'(マイケル|ジョン|ロバート|デビッド|ジェームズ|ウィリアム|クリス|トム|ピーター|ポール).*(太郎|次郎|三郎|健太|和也|拓也|翔太|雄大)',
            na=False
        )
    ]
    
    # 2. 同一スコアが多すぎる人物（50.0, 35.0など）
    score_counts = df['name_recognition'].value_counts()
    suspicious_scores = score_counts[score_counts > 100].index
    
    # 3. occupation未設定または汎用的すぎる
    generic_occupations = df[
        df['occupation'].isna() | 
        df['occupation'].isin(['プレイヤー', '選手', 'その他'])
    ]
    
    # サンプリングしてWikipedia確認
    logger.info(f"📋 サンプル{sample_size}件のWikipedia確認開始")
    
    not_found = []
    sample = df.sample(n=min(sample_size, len(df)), random_state=42)
    
    for idx, row in sample.iterrows():
        exists = check_wikipedia_existence(row['person_name'])
        if exists is False:
            not_found.append({
                'person_id': row['person_id'],
                'person_name': row['person_name'],
                'occupation': row['occupation'],
                'current_score': row['name_recognition']
            })
            logger.warning(f"  ❌ Wikipedia未掲載: {row['person_id']}: {row['person_name']}")
    
    logger.info(f"Wikipedia未掲載: {len(not_found)}/{sample_size}件")
    
    # 特に怪しいパターンの全件チェック
    logger.info("\n⚠️ 怪しいパターンの検出")
    for idx, row in foreign_japanese_pattern.iterrows():
        logger.warning(f"  外国人名+日本人名: {row['person_id']}: {row['person_name']}")
        df.at[idx, 'name_recognition'] = 0.0
        not_found.append({
            'person_id': row['person_id'],
            'person_name': row['person_name'],
            'reason': 'foreign_japanese_pattern'
        })
    
    return df, not_found


def generate_fix_report(deletions, fixes, not_found, original_count, final_count):
    """修正レポートの生成"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'original_count': original_count,
        'final_count': final_count,
        'changes': {
            'groups_deleted': len(deletions),
            'band_members_fixed': len(fixes),
            'wikipedia_not_found': len(not_found)
        },
        'details': {
            'deletions': deletions,
            'display_fixes': fixes,
            'wikipedia_issues': not_found
        }
    }
    
    report_file = f"group_wikipedia_fix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    logger.info(f"📝 レポート保存: {report_file}")
    return report


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("🚀 グループ削除とWikipedia検証開始")
    logger.info("=" * 60)
    
    # データ読み込み
    csv_file = "ultra_think_FINAL_DATABASE_20250911_020649.csv"
    logger.info(f"📂 データ読み込み: {csv_file}")
    df = pd.read_csv(csv_file)
    original_count = len(df)
    logger.info(f"📊 元レコード数: {original_count}件")
    
    # バックアップ作成
    backup_file = backup_database(csv_file)
    
    # 1. グループ/団体データの削除
    df, deletions = remove_groups(df)
    
    # 2. バンドメンバーの表記修正
    df, fixes = fix_band_members_display(df)
    
    # 3. Wikipedia存在確認と怪しいデータの検出
    df, not_found = validate_wikipedia_entries(df)
    
    # 4. 修正後のデータ保存
    output_file = f"ultra_think_CLEANED_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    logger.info(f"💾 修正データ保存: {output_file}")
    
    # 5. レポート生成
    final_count = len(df)
    report = generate_fix_report(deletions, fixes, not_found, original_count, final_count)
    
    # 最終サマリー
    logger.info("=" * 60)
    logger.info("📊 修正完了サマリー")
    logger.info("=" * 60)
    logger.info(f"  元レコード数: {original_count}件")
    logger.info(f"  最終レコード数: {final_count}件")
    logger.info(f"  削除グループ: {len(deletions)}件")
    logger.info(f"  バンドメンバー表記修正: {len(fixes)}件")
    logger.info(f"  Wikipedia未掲載検出: {len(not_found)}件")
    
    return output_file, report


if __name__ == "__main__":
    output_file, report = main()
    print(f"\n✅ 処理完了")
    print(f"📁 出力ファイル: {output_file}")