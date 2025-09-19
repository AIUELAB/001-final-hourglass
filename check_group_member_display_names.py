#!/usr/bin/env python3
"""
段階的な詳細分析：グループメンバーのdisplay名問題
"""

import pandas as pd
import logging
from typing import Dict, List, Tuple
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def step1_understand_structure():
    """ステップ1: データ構造の理解"""
    logger.info("\n" + "="*60)
    logger.info("ステップ1: データ構造の理解")
    logger.info("="*60)
    
    csv_file = "/Users/admin/Documents/AIUELAB/001-final-hourglass/ultra_think_FICTIONAL_RULE077_COMPLETE_WITH_AUTHOR.csv"
    df = pd.read_csv(csv_file, encoding='utf-8-sig')
    
    # 指定されたperson_IDを確認
    target_ids = ['P000051', 'P000063', 'P000111', 'P000401', 'P000432']
    
    logger.info(f"総レコード数: {len(df)}")
    logger.info(f"確認対象ID: {target_ids}")
    
    # 各IDの詳細確認
    for person_id in target_ids:
        record = df[df['person_id'] == person_id]
        if not record.empty:
            row = record.iloc[0]
            logger.info(f"\n{person_id}:")
            logger.info(f"  person_name: {row.get('person_name', 'N/A')}")
            logger.info(f"  person_name_ja: {row.get('person_name_ja', 'N/A')}")
            logger.info(f"  person_name_display: {row.get('person_name_display', 'N/A')}")
            logger.info(f"  occupation: {row.get('occupation', 'N/A')}")
            logger.info(f"  nationality: {row.get('nationality', 'N/A')}")
            logger.info(f"  category: {row.get('category', 'N/A')}")
            logger.info(f"  entity_type: {row.get('entity_type', 'N/A')}")
            
            # 括弧の有無を確認
            display = str(row.get('person_name_display', ''))
            has_parentheses = '(' in display or '（' in display
            logger.info(f"  括弧付きグループ名: {'✓' if has_parentheses else '✗ なし'}")
        else:
            logger.warning(f"{person_id}: レコードが見つかりません")
    
    return df, target_ids

def step2_verify_functions():
    """ステップ2: 各機能の動作検証"""
    logger.info("\n" + "="*60)
    logger.info("ステップ2: 各機能の動作検証")
    logger.info("="*60)
    
    # 既知のグループメンバーパターン
    known_group_members = {
        # BTS
        'RM': 'BTS',
        'Jin': 'BTS',
        'SUGA': 'BTS',
        'J-Hope': 'BTS',
        'Jimin': 'BTS',
        'V': 'BTS',
        'Jungkook': 'BTS',
        'ジン': 'BTS',
        'シュガ': 'BTS',
        'ジェイホープ': 'BTS',
        'ジミン': 'BTS',
        'テテ': 'BTS',
        'ジョングク': 'BTS',
        
        # SEVENTEEN
        'S.Coups': 'SEVENTEEN',
        'Jeonghan': 'SEVENTEEN',
        'Joshua': 'SEVENTEEN',
        'Jun': 'SEVENTEEN',
        'Hoshi': 'SEVENTEEN',
        'Wonwoo': 'SEVENTEEN',
        'Woozi': 'SEVENTEEN',
        'DK': 'SEVENTEEN',
        'Mingyu': 'SEVENTEEN',
        'The8': 'SEVENTEEN',
        'Seungkwan': 'SEVENTEEN',
        'Vernon': 'SEVENTEEN',
        'Dino': 'SEVENTEEN',
        
        # その他
        '大野智': '嵐',
        '櫻井翔': '嵐',
        '相葉雅紀': '嵐',
        '松本潤': '嵐',
        '二宮和也': '嵐',
    }
    
    # occupation に基づくグループ推定
    occupation_to_group = {
        'BTS メンバー': 'BTS',
        'SEVENTEEN メンバー': 'SEVENTEEN',
        '嵐 メンバー': '嵐',
        'アイドル（BTS）': 'BTS',
        'アイドル（SEVENTEEN）': 'SEVENTEEN',
    }
    
    logger.info(f"既知のグループメンバー数: {len(known_group_members)}")
    logger.info(f"職業ベースのマッピング数: {len(occupation_to_group)}")
    
    return known_group_members, occupation_to_group

def step3_identify_bugs_and_edge_cases(df, target_ids):
    """ステップ3: バグとエッジケースの特定"""
    logger.info("\n" + "="*60)
    logger.info("ステップ3: 潜在的なバグとエッジケースの特定")
    logger.info("="*60)
    
    issues = []
    
    # 1. 韓国アイドルの特定
    korean_idols = df[
        (df['nationality'] == '韓国') & 
        (df['occupation'].str.contains('アイドル|歌手', na=False))
    ]
    
    missing_group_count = 0
    for idx, row in korean_idols.iterrows():
        display = str(row.get('person_name_display', ''))
        if '(' not in display and '（' not in display:
            missing_group_count += 1
            issues.append({
                'person_id': row['person_id'],
                'name': row.get('person_name_ja', row.get('person_name')),
                'issue': 'グループ名なし',
                'occupation': row.get('occupation'),
                'nationality': row.get('nationality')
            })
    
    logger.info(f"韓国アイドル総数: {len(korean_idols)}")
    logger.info(f"グループ名欠落: {missing_group_count}件")
    
    # 2. 日本のグループメンバー
    japanese_groups = df[
        (df['nationality'] == '日本') & 
        (df['occupation'].str.contains('メンバー', na=False))
    ]
    
    jp_missing = 0
    for idx, row in japanese_groups.iterrows():
        display = str(row.get('person_name_display', ''))
        if '(' not in display and '（' not in display:
            jp_missing += 1
            issues.append({
                'person_id': row['person_id'],
                'name': row.get('person_name_ja', row.get('person_name')),
                'issue': 'グループ名なし（日本）',
                'occupation': row.get('occupation')
            })
    
    logger.info(f"日本のグループメンバー: {len(japanese_groups)}")
    logger.info(f"グループ名欠落: {jp_missing}件")
    
    # 3. 具体的な問題分析
    logger.info("\n問題パターン分析:")
    logger.info("1. PDCAルールが適用されていない理由:")
    logger.info("   - ルールの検出条件が不十分")
    logger.info("   - occupationフィールドの値が多様すぎる")
    logger.info("   - 自動検出のためのマッピングが不完全")
    
    logger.info("\n2. エッジケース:")
    logger.info("   - ソロ活動もするグループメンバー")
    logger.info("   - 複数グループに所属する人物")
    logger.info("   - グループ名が変更された場合")
    
    return issues

def step4_propose_improvements(df, issues):
    """ステップ4: 改善案の提示"""
    logger.info("\n" + "="*60)
    logger.info("ステップ4: 改善案の提示")
    logger.info("="*60)
    
    # グループメンバー自動検出ロジック
    def detect_group_from_occupation(occupation):
        """occupationからグループ名を抽出"""
        if pd.isna(occupation):
            return None
        
        occupation = str(occupation)
        
        # パターン1: "グループ名 メンバー"
        if 'メンバー' in occupation:
            parts = occupation.split('メンバー')[0].strip()
            if parts and parts not in ['アイドル', '音楽', 'バンド']:
                return parts
        
        # パターン2: "アイドル（グループ名）"
        if '（' in occupation and '）' in occupation:
            import re
            match = re.search(r'（([^）]+）', occupation)
            if match:
                return match.group(1)
        
        # パターン3: 特定のグループ名が含まれる
        known_groups = ['BTS', 'SEVENTEEN', 'TWICE', '嵐', 'SMAP', 'AKB48', '乃木坂46']
        for group in known_groups:
            if group in occupation:
                return group
        
        return None
    
    # 修正提案
    fixes = []
    for issue in issues[:10]:  # 最初の10件を表示
        group = detect_group_from_occupation(issue.get('occupation', ''))
        if group:
            fixes.append({
                'person_id': issue['person_id'],
                'current': issue['name'],
                'suggested': f"{issue['name']} ({group})",
                'group': group
            })
            logger.info(f"修正提案: {issue['person_id']}: {issue['name']} → {issue['name']} ({group})")
    
    logger.info(f"\n自動修正可能: {len(fixes)}件")
    
    return fixes

def main():
    """メイン処理"""
    logger.info("グループメンバーdisplay名の段階的詳細分析")
    logger.info("="*80)
    
    # ステップ1: 構造理解
    df, target_ids = step1_understand_structure()
    
    # ステップ2: 機能検証
    known_groups, occupation_map = step2_verify_functions()
    
    # ステップ3: バグ特定
    issues = step3_identify_bugs_and_edge_cases(df, target_ids)
    
    # ステップ4: 改善提案
    fixes = step4_propose_improvements(df, issues)
    
    # 結論
    logger.info("\n" + "="*60)
    logger.info("結論と根本原因")
    logger.info("="*60)
    logger.info("【根本原因】")
    logger.info("1. PDCAルールが存在するが、実装が不完全")
    logger.info("2. グループ検出ロジックが職業フィールドの多様性に対応できていない")
    logger.info("3. 自動修正のためのマッピングデータが不足")
    logger.info("\n【必要な対策】")
    logger.info("1. より包括的なグループ検出ロジックの実装")
    logger.info("2. occupationフィールドの標準化")
    logger.info("3. PDCAガーディアンへの強力なルール追加")
    
    return df, issues, fixes

if __name__ == "__main__":
    main()