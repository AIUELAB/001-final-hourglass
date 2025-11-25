#!/usr/bin/env python3
"""
29件の検証済みエピソードがPDCAルールに違反していないかチェック
"""

import pandas as pd
from pdca_guardian import PDCAGuardian
import logging
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def check_trusted_episodes():
    """信頼できるエピソードのPDCAルール違反をチェック"""

    logger.info("="*60)
    logger.info("🔍 検証済みエピソードのPDCAルール違反チェック開始")
    logger.info("="*60)

    # CSVファイル読み込み
    csv_file = 'trusted_episodes_latest.csv'
    logger.info(f"\n📂 読み込みファイル: {csv_file}")

    try:
        df = pd.read_csv(csv_file, encoding='utf-8-sig')
    except FileNotFoundError:
        csv_file = 'trusted_episodes_master_20250922_071200.csv'
        df = pd.read_csv(csv_file, encoding='utf-8-sig')

    logger.info(f"✅ {len(df)}件のエピソードを読み込み")

    # PDCAガーディアン初期化
    guardian = PDCAGuardian()
    # PDCAGuardianはmemoryに保存されているルールを使用
    total_rules = (len(guardian.memory.get('permanent_rules', {})) +
                   len(guardian.memory.get('failed_patterns', [])) +
                   len(guardian.memory.get('success_patterns', [])))
    logger.info(f"✅ PDCAガーディアン初期化（{total_rules}ルール・パターン）")

    # 違反統計の初期化
    total_violations = 0
    episodes_with_violations = 0
    violation_details = []
    violation_summary = {}

    # 各エピソードをチェック
    logger.info("\n📋 エピソードごとの違反チェック:")
    logger.info("-"*50)

    for idx, row in df.iterrows():
        person_name = row['person_name']
        age = row['episode_age']
        episode_text = row['episode_text']
        person_name_display = f"{person_name}（{age}歳）"

        # 違反チェック
        violations = guardian.check_episode_quality(
            episode_text=episode_text,
            age=age,
            person_name_display=person_name_display
        )

        if violations:
            episodes_with_violations += 1
            total_violations += len(violations)

            logger.warning(f"\n⚠️ エピソード{idx+1}: {person_name}（{age}歳）")
            logger.warning(f"   エピソード: {episode_text[:50]}...")
            logger.warning(f"   違反数: {len(violations)}")

            episode_violations = {
                'index': idx,
                'person_name': person_name,
                'age': age,
                'episode_text': episode_text,
                'violations': []
            }

            for v in violations:
                violation_type = v.get('type', 'UNKNOWN')
                rule_id = v.get('rule_id', 'UNKNOWN')
                message = v.get('message', '')

                logger.warning(f"     - {rule_id} ({violation_type}): {message[:100]}")

                episode_violations['violations'].append({
                    'rule_id': rule_id,
                    'type': violation_type,
                    'message': message
                })

                # 違反タイプ別カウント
                if violation_type not in violation_summary:
                    violation_summary[violation_type] = {}
                if rule_id not in violation_summary[violation_type]:
                    violation_summary[violation_type][rule_id] = 0
                violation_summary[violation_type][rule_id] += 1

            violation_details.append(episode_violations)
        else:
            logger.info(f"✅ エピソード{idx+1}: {person_name}（{age}歳）- 違反なし")

    # 結果サマリー
    logger.info("\n" + "="*60)
    logger.info("📊 違反チェック結果サマリー")
    logger.info("="*60)

    logger.info(f"\n📈 全体統計:")
    logger.info(f"  チェック済みエピソード: {len(df)}件")
    logger.info(f"  違反のあるエピソード: {episodes_with_violations}件")
    logger.info(f"  違反のないエピソード: {len(df) - episodes_with_violations}件")
    logger.info(f"  総違反数: {total_violations}")

    if episodes_with_violations > 0:
        logger.info(f"  違反率: {(episodes_with_violations/len(df)*100):.1f}%")
        logger.info(f"  平均違反数: {(total_violations/episodes_with_violations):.1f}件/エピソード")

    if violation_summary:
        logger.info("\n🏷️ 違反タイプ別統計:")
        for vtype, rules in violation_summary.items():
            type_total = sum(rules.values())
            logger.info(f"\n  {vtype}: {type_total}件")
            for rule_id, count in sorted(rules.items(), key=lambda x: x[1], reverse=True)[:5]:
                logger.info(f"    - {rule_id}: {count}件")

    # 詳細レポートの保存
    if violation_details:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f'trusted_episodes_violation_report_{timestamp}.json'

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': {
                    'total_episodes': len(df),
                    'episodes_with_violations': episodes_with_violations,
                    'total_violations': total_violations,
                    'violation_rate': f"{(episodes_with_violations/len(df)*100):.1f}%",
                    'timestamp': timestamp
                },
                'violation_summary': violation_summary,
                'detailed_violations': violation_details
            }, f, ensure_ascii=False, indent=2)

        logger.info(f"\n💾 詳細レポート保存: {report_file}")

    # 最終判定
    logger.info("\n" + "="*60)
    if episodes_with_violations == 0:
        logger.info("✨ 素晴らしい！全29件のエピソードがPDCAルールに完全準拠しています！")
    else:
        logger.warning(f"⚠️ {episodes_with_violations}件のエピソードに{total_violations}個の違反が見つかりました")
        logger.info("📝 詳細レポートを確認して修正が必要です")
    logger.info("="*60)

    return episodes_with_violations, total_violations, violation_details

def analyze_violations_by_rule(violation_details):
    """違反をルール別に分析"""
    if not violation_details:
        return

    logger.info("\n🔍 違反エピソードの詳細分析:")
    logger.info("-"*50)

    rule_violations = {}

    for episode in violation_details:
        for violation in episode['violations']:
            rule_id = violation['rule_id']
            if rule_id not in rule_violations:
                rule_violations[rule_id] = []

            rule_violations[rule_id].append({
                'person': episode['person_name'],
                'age': episode['age'],
                'text': episode['episode_text'][:100],
                'message': violation['message']
            })

    # ルールごとに違反を表示
    for rule_id, violations in sorted(rule_violations.items(), key=lambda x: len(x[1]), reverse=True):
        logger.info(f"\n📌 {rule_id} ({len(violations)}件の違反):")
        for v in violations[:3]:  # 最初の3件のみ表示
            logger.info(f"  - {v['person']}（{v['age']}歳）")
            logger.info(f"    エピソード: {v['text']}...")
            logger.info(f"    問題: {v['message'][:100]}")

if __name__ == "__main__":
    # 違反チェック実行
    episodes_with_violations, total_violations, violation_details = check_trusted_episodes()

    # 詳細分析
    if violation_details:
        analyze_violations_by_rule(violation_details)

    # 推奨事項
    if episodes_with_violations > 0:
        logger.info("\n💡 推奨対応:")
        logger.info("1. FORMAT_ERROR違反は、エピソードの開始フォーマットを統一")
        logger.info("2. CONTENT_QUALITY違反は、事実確認と表現の改善")
        logger.info("3. CHARACTER_COUNT違反は、文字数を150-250文字に調整")
