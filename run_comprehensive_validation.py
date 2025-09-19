#!/usr/bin/env python3
"""
包括的なデータ検証スクリプト
PDCA Guardianの全ルールを適用して健全性をチェック
"""

import pandas as pd
import logging
from datetime import datetime
from pdca_guardian import PDCAGuardian, ViolationType
from typing import Dict, List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_comprehensive_validation():
    """全データの包括的検証"""
    
    # 最新のクリーンデータを使用
    csv_file = "ultra_think_CLEAN_NO_SYNTHETIC_ATHLETES_20250912_060705.csv"
    
    logger.info("="*80)
    logger.info("包括的データ検証開始")
    logger.info("="*80)
    
    # PDCAガーディアン初期化
    guardian = PDCAGuardian()
    
    # データ読み込み
    logger.info(f"\nデータファイル読み込み: {csv_file}")
    df = pd.read_csv(csv_file, encoding='utf-8-sig')
    logger.info(f"総レコード数: {len(df)}")
    
    # 各種チェック実行
    all_violations = []
    check_results = {}
    
    # 1. 架空キャラクター表示名チェック
    logger.info("\n1. 架空キャラクター表示名チェック...")
    fictional_violations = guardian.check_fictional_character_display(csv_file)
    all_violations.extend(fictional_violations)
    check_results['fictional_characters'] = len(fictional_violations)
    
    # 2. 合成アスリートチェック
    logger.info("\n2. 合成アスリート検出チェック...")
    synthetic_violations = guardian.check_synthetic_athletes(csv_file)
    all_violations.extend(synthetic_violations)
    check_results['synthetic_athletes'] = len(synthetic_violations)
    
    # 3. グループメンバー表示名チェック
    logger.info("\n3. グループメンバー表示名チェック...")
    group_violations = []
    
    # 既知のグループメンバーマッピング
    GROUP_MAPPING = {
        'あんり': 'ぼる塾', 'きりやはるか': 'ぼる塾', '酒寄希望': 'ぼる塾', '田辺智加': 'ぼる塾',
        'ふくらP': 'QuizKnock', '伊沢拓司': 'QuizKnock',
        'カズレーザー': 'メイプル超合金', '安藤なつ': 'メイプル超合金',
        'ガク': 'GAG少年楽団', '宮戸洋行': 'GAG少年楽団',
        '大悟': '千鳥', 'ノブ': '千鳥',
        'カンタ': '水溜りボンド', 'トミー': '水溜りボンド',
        'シルクロード': 'フィッシャーズ', 'マサイ': 'フィッシャーズ', 'ンダホ': 'フィッシャーズ',
        'ペケタン': 'フィッシャーズ', 'ダーマ': 'フィッシャーズ', 'ザカオ': 'フィッシャーズ', 'モトキ': 'フィッシャーズ'
    }
    
    for idx, row in df.iterrows():
        name_ja = row.get('person_name_ja', '')
        display = str(row.get('person_name_display', ''))
        
        if name_ja in GROUP_MAPPING:
            expected_group = GROUP_MAPPING[name_ja]
            if f"({expected_group})" not in display and f"（{expected_group}）" not in display:
                group_violations.append({
                    'person_id': row['person_id'],
                    'name': name_ja,
                    'current': display,
                    'expected': f"{name_ja} ({expected_group})"
                })
    
    all_violations.extend([v for v in group_violations])  # Convert to violations format if needed
    check_results['group_members'] = len(group_violations)
    
    # 4. データ品質統計
    logger.info("\n4. データ品質統計分析...")
    
    # カテゴリ別統計
    category_stats = df['category'].value_counts()
    
    # 国籍別統計
    nationality_stats = df['nationality'].value_counts().head(10)
    
    # 認知度スコア分布
    score_stats = {
        'スコア0': len(df[df['name_recognition'] == 0]),
        'スコア1-3': len(df[(df['name_recognition'] > 0) & (df['name_recognition'] <= 3)]),
        'スコア4-6': len(df[(df['name_recognition'] > 3) & (df['name_recognition'] <= 6)]),
        'スコア7-9': len(df[(df['name_recognition'] > 6) & (df['name_recognition'] <= 9)]),
        'スコア10': len(df[df['name_recognition'] == 10])
    }
    
    # 結果レポート生成
    logger.info("\n" + "="*80)
    logger.info("検証結果サマリー")
    logger.info("="*80)
    
    logger.info(f"\n✅ 検証完了:")
    logger.info(f"  - 総レコード数: {len(df)}")
    logger.info(f"  - 架空キャラクター違反: {check_results['fictional_characters']}件")
    logger.info(f"  - 合成アスリート検出: {check_results['synthetic_athletes']}件")
    logger.info(f"  - グループメンバー表示違反: {check_results['group_members']}件")
    logger.info(f"  - 総違反数: {len(all_violations)}件")
    
    logger.info(f"\n📊 カテゴリ分布:")
    for category, count in category_stats.head(10).items():
        logger.info(f"  - {category}: {count}件")
    
    logger.info(f"\n🌍 国籍分布（上位10）:")
    for nationality, count in nationality_stats.items():
        logger.info(f"  - {nationality}: {count}件")
    
    logger.info(f"\n📈 認知度スコア分布:")
    for range_name, count in score_stats.items():
        logger.info(f"  - {range_name}: {count}件")
    
    # 違反の詳細（最初の10件）
    if all_violations:
        logger.info(f"\n⚠️ 検出された違反（最初の10件）:")
        for i, violation in enumerate(all_violations[:10], 1):
            if isinstance(violation, dict):
                logger.info(f"  {i}. {violation.get('person_id', 'N/A')}: {violation.get('name', 'N/A')}")
            else:
                logger.info(f"  {i}. Line {violation.line}: {violation.description}")
    
    # レポートファイル保存
    report_file = f"COMPREHENSIVE_VALIDATION_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# 包括的データ検証レポート\n\n")
        f.write(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## 検証結果サマリー\n\n")
        f.write(f"- 総レコード数: {len(df)}\n")
        f.write(f"- 架空キャラクター違反: {check_results['fictional_characters']}件\n")
        f.write(f"- 合成アスリート検出: {check_results['synthetic_athletes']}件\n")
        f.write(f"- グループメンバー表示違反: {check_results['group_members']}件\n")
        f.write(f"- **総違反数: {len(all_violations)}件**\n\n")
        
        if len(all_violations) == 0:
            f.write("## ✅ データ健全性確認\n\n")
            f.write("すべてのPDCAルールに準拠しています。データベースは健全な状態です。\n")
        else:
            f.write("## ⚠️ 要対応項目\n\n")
            f.write("以下の違反が検出されました。修正が必要です。\n\n")
            for violation in all_violations[:50]:  # 最初の50件
                if isinstance(violation, dict):
                    f.write(f"- {violation}\n")
                else:
                    f.write(f"- {violation.description}\n")
    
    logger.info(f"\n📄 レポート保存: {report_file}")
    
    # 健全性判定
    if len(all_violations) == 0:
        logger.info("\n" + "="*80)
        logger.info("✅ データベース健全性: 完璧")
        logger.info("すべてのPDCAルールに準拠しています")
        logger.info("="*80)
    else:
        logger.info("\n" + "="*80)
        logger.info(f"⚠️ データベース健全性: {len(all_violations)}件の違反検出")
        logger.info("修正が必要です")
        logger.info("="*80)
    
    return all_violations, check_results

if __name__ == "__main__":
    violations, results = run_comprehensive_validation()