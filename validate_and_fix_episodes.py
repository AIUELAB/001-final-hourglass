#!/usr/bin/env python3
"""
既存エピソードCSVを統合パイプラインで検証・修正

#episodes_validated_100_20251001.csvの全エピソードを
IntegratedEpisodeEvaluationPipelineで検証し、
不合格のものを特定して修正案を提示
"""

import csv
import json
import logging
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from integrated_episode_evaluation_pipeline import (
    IntegratedEpisodeEvaluationPipeline,
    EvaluationResult
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)


def load_episodes_from_csv(csv_path: str) -> List[Dict]:
    """
    CSVからエピソードを読み込み

    Args:
        csv_path: CSVファイルパス

    Returns:
        エピソードリスト
    """
    episodes = []

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            episode = {
                'episode_id': row['episode_id'],
                'person_name': row['person_name'],
                'episode_age': int(row['episode_age']),
                'episode_text': row['episode_text'],
                'category': row.get('category', row.get('episode_type', 'other')),
                'birth_year': None  # CSVに含まれていない場合は推定
            }

            # 生年を推定（2025年基準で逆算）
            if episode['episode_age'] > 0:
                # 仮の推定（正確な生年が必要な場合は別途データベース参照）
                current_year = 2025
                estimated_birth_year = current_year - episode['episode_age'] - 20
                episode['birth_year'] = estimated_birth_year

            episodes.append(episode)

    logger.info(f"✅ {len(episodes)}件のエピソードを読み込みました")
    return episodes


def validate_all_episodes(csv_path: str) -> Dict:
    """
    全エピソードを統合パイプラインで検証

    Args:
        csv_path: 入力CSVパス

    Returns:
        検証結果統計
    """
    logger.info("="*70)
    logger.info("🔍 統合パイプラインによる全エピソード検証")
    logger.info("="*70)

    # エピソード読み込み
    episodes = load_episodes_from_csv(csv_path)

    # パイプライン初期化
    pipeline = IntegratedEpisodeEvaluationPipeline(
        csv_output_path='#episodes_revalidated_output.csv'
    )
    pipeline.initialize()

    # 検証結果
    results = {
        'total': len(episodes),
        'passed': [],
        'failed_score': [],
        'failed_critical': [],
        'failed_fact': [],
        'evaluations': []
    }

    # 全エピソードを検証
    for i, episode in enumerate(episodes, 1):
        logger.info(f"\n{'='*70}")
        logger.info(f"📋 検証 {i}/{len(episodes)}: {episode['episode_id']} - {episode['person_name']}")
        logger.info(f"{'='*70}")

        evaluation = pipeline.evaluate_episode(episode)

        # 結果の分類
        episode_result = {
            'episode_id': episode['episode_id'],
            'person_name': episode['person_name'],
            'episode_age': episode['episode_age'],
            'episode_text': episode['episode_text'],
            'result': evaluation.result.value,
            'score': evaluation.total_score,
            'violations': evaluation.violations,
            'warnings': evaluation.warnings
        }

        results['evaluations'].append(episode_result)

        if evaluation.result == EvaluationResult.PASS:
            results['passed'].append(episode_result)
            logger.info(f"✅ 合格: {episode['episode_id']} (スコア: {evaluation.total_score:.1f})")
        elif evaluation.result == EvaluationResult.FAIL_LOW_SCORE:
            results['failed_score'].append(episode_result)
            logger.warning(f"⚠️ スコア不足: {episode['episode_id']} (スコア: {evaluation.total_score:.1f})")
        elif evaluation.result == EvaluationResult.FAIL_CRITICAL:
            results['failed_critical'].append(episode_result)
            logger.error(f"❌ CRITICAL違反: {episode['episode_id']}")
        elif evaluation.result == EvaluationResult.FAIL_FACT_CHECK:
            results['failed_fact'].append(episode_result)
            logger.error(f"❌ 事実検証失敗: {episode['episode_id']}")

    # シャットダウン
    pipeline.shutdown()

    return results


def generate_report(results: Dict, output_path: str = 'validation_report.json'):
    """
    検証レポートを生成

    Args:
        results: 検証結果
        output_path: レポート出力パス
    """
    logger.info("\n" + "="*70)
    logger.info("📊 検証結果サマリー")
    logger.info("="*70)
    logger.info(f"  合計: {results['total']}件")
    logger.info(f"  ✅ 合格: {len(results['passed'])}件 ({len(results['passed'])/results['total']*100:.1f}%)")
    logger.info(f"  ⚠️ スコア不足: {len(results['failed_score'])}件")
    logger.info(f"  ❌ CRITICAL違反: {len(results['failed_critical'])}件")
    logger.info(f"  ❌ 事実検証失敗: {len(results['failed_fact'])}件")

    # 詳細レポート生成
    report = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total': results['total'],
            'passed': len(results['passed']),
            'failed_score': len(results['failed_score']),
            'failed_critical': len(results['failed_critical']),
            'failed_fact': len(results['failed_fact']),
            'pass_rate': len(results['passed']) / results['total'] * 100
        },
        'failed_episodes': {
            'score_issues': results['failed_score'],
            'critical_violations': results['failed_critical'],
            'fact_check_failures': results['failed_fact']
        },
        'all_evaluations': results['evaluations']
    }

    # JSON出力
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info(f"\n📝 詳細レポート保存: {output_path}")

    # 失敗エピソードの詳細表示
    if results['failed_score']:
        logger.info("\n" + "="*70)
        logger.info("⚠️ スコア不足エピソード詳細")
        logger.info("="*70)
        for ep in results['failed_score'][:5]:  # 最初の5件のみ表示
            logger.info(f"\nID: {ep['episode_id']} - {ep['person_name']}")
            logger.info(f"スコア: {ep['score']:.1f}点")
            logger.info(f"違反: {ep['violations'][:3]}")  # 最初の3件

    if results['failed_critical']:
        logger.info("\n" + "="*70)
        logger.info("❌ CRITICAL違反エピソード詳細")
        logger.info("="*70)
        for ep in results['failed_critical'][:5]:
            logger.info(f"\nID: {ep['episode_id']} - {ep['person_name']}")
            logger.info(f"違反: {ep['violations'][:3]}")


def main():
    """メイン実行"""
    csv_path = '/Users/admin/Documents/AIUELAB/001-final-hourglass/#episodes_validated_100_20251001.csv'

    # 全エピソード検証
    results = validate_all_episodes(csv_path)

    # レポート生成
    generate_report(results, output_path='validation_report_20251002.json')

    logger.info("\n" + "="*70)
    logger.info("✅ 検証完了")
    logger.info("="*70)


if __name__ == "__main__":
    main()
