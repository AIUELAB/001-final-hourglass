#!/usr/bin/env python3
"""
統合パイプラインのエンドツーエンドテスト
End-to-End Test for Integrated Pipeline

有名人データベース → SmartIterationEngine → エピソード生成
の完全な流れをテストする

テスト対象:
1. category_based_candidate_selector.py - 有名人選定
2. production_episode_generator.py - エピソード生成（Phase 1-4統合）
3. episode_merge_tool.py - データマージ

実行コマンド:
    python3 test_integrated_pipeline.py --count 5 --provider openai

Created: 2025-10-02
"""

import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# プロジェクト内モジュール
from category_based_candidate_selector import CategoryBasedCandidateSelector
from production_episode_generator import ProductionEpisodeGenerator

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)


def test_integrated_pipeline(
    max_persons: int = 5,
    episodes_per_person: int = 1,
    llm_provider: str = "openai",
    llm_model: str = None
):
    """
    統合パイプラインテスト

    Args:
        max_persons: テスト対象人物数
        episodes_per_person: 1人あたりエピソード数
        llm_provider: LLMプロバイダー
        llm_model: モデル名
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    logger.info(f"\n{'='*60}")
    logger.info(f"🧪 統合パイプライン エンドツーエンドテスト")
    logger.info(f"{'='*60}")
    logger.info(f"対象人物数: {max_persons}")
    logger.info(f"エピソード/人: {episodes_per_person}")
    logger.info(f"LLMプロバイダー: {llm_provider}")
    logger.info(f"モデル: {llm_model or 'default'}")

    # ========================================
    # Step 1: 有名人選定
    # ========================================
    logger.info(f"\n{'='*60}")
    logger.info(f"📋 Step 1: 有名人選定")
    logger.info(f"{'='*60}")

    selector = CategoryBasedCandidateSelector()
    persons_data = selector.select_from_database(max_candidates=max_persons)

    if not persons_data:
        logger.error("❌ 有名人が選定できませんでした")
        return False

    logger.info(f"✅ {len(persons_data)}名を選定")

    # ========================================
    # Step 2: エピソード生成用データ作成
    # ========================================
    logger.info(f"\n{'='*60}")
    logger.info(f"🎬 Step 2: エピソード生成用データ作成")
    logger.info(f"{'='*60}")

    # 年齢リストを生成（20歳代、30歳代、40歳代から選択）
    age_options = [25, 30, 35, 40, 45]

    batch_input = []
    for person_data in persons_data:
        birth_year = person_data['birth_year']
        current_year = datetime.now().year
        person_age = current_year - birth_year

        # 実際に生きた年齢範囲で選択
        valid_ages = [age for age in age_options if age <= person_age][:episodes_per_person]

        for age in valid_ages:
            batch_input.append({
                'name': person_data['person_name_ja'],
                'age': age,
                'category': person_data['category'],
                'person_id': person_data['person_id'],
                'birth_year': birth_year
            })

    logger.info(f"✅ バッチ入力生成: {len(batch_input)}エピソード")

    for i, item in enumerate(batch_input[:5], 1):
        logger.info(f"  {i}. {item['name']} ({item['age']}歳, {item['category']})")

    # ========================================
    # Step 3: エピソード生成
    # ========================================
    logger.info(f"\n{'='*60}")
    logger.info(f"🎨 Step 3: SmartIterationEngineでエピソード生成")
    logger.info(f"{'='*60}")

    generator = ProductionEpisodeGenerator(
        llm_provider=llm_provider,
        model=llm_model,
        enable_llm_evaluation=True,
        max_iterations=3,
        target_score=8.0
    )

    results = generator.generate_batch(batch_input)

    # ========================================
    # Step 4: 結果分析
    # ========================================
    logger.info(f"\n{'='*60}")
    logger.info(f"📊 Step 4: 結果分析")
    logger.info(f"{'='*60}")

    success_count = sum(1 for r in results if r['success'])
    failed_count = len(results) - success_count

    # 成功したエピソードのみで統計計算
    successful_results = [r for r in results if r['success']]

    if successful_results:
        avg_gate_score = sum(r['gate_score'] for r in successful_results) / len(successful_results)

        llm_scores = [r['llm_score'] for r in successful_results if r['llm_score'] is not None]
        avg_llm_score = sum(llm_scores) / len(llm_scores) if llm_scores else 0.0

        total_scores = [r['total_score'] for r in successful_results if r['total_score'] is not None]
        avg_total_score = sum(total_scores) / len(total_scores) if total_scores else avg_gate_score

        avg_iterations = sum(r['iterations'] for r in successful_results) / len(successful_results)
        total_tokens = sum(r['tokens_used'] for r in successful_results)
    else:
        avg_gate_score = 0.0
        avg_llm_score = 0.0
        avg_total_score = 0.0
        avg_iterations = 0.0
        total_tokens = 0

    logger.info(f"総エピソード数: {len(results)}")
    logger.info(f"成功: {success_count} ({success_count/len(results)*100:.1f}%)")
    logger.info(f"失敗: {failed_count} ({failed_count/len(results)*100:.1f}%)")
    logger.info(f"\n平均スコア:")
    logger.info(f"  Gate: {avg_gate_score:.2f}/10.0")
    logger.info(f"  LLM: {avg_llm_score:.2f}/30.0")
    logger.info(f"  Total: {avg_total_score:.2f}/40.0")
    logger.info(f"\n平均反復回数: {avg_iterations:.2f}")
    logger.info(f"総トークン数: {total_tokens:,}")

    # ========================================
    # Step 5: CSV出力
    # ========================================
    output_csv = f"test_pipeline_results_{timestamp}.csv"
    generator.save_to_csv(results, output_csv)

    logger.info(f"\n💾 結果出力: {output_csv}")

    # ========================================
    # Step 6: サンプルエピソード表示
    # ========================================
    logger.info(f"\n{'='*60}")
    logger.info(f"📝 サンプルエピソード（成功した最初の3件）")
    logger.info(f"{'='*60}")

    displayed = 0
    for result in results:
        if result['success'] and displayed < 3:
            logger.info(f"\n{displayed + 1}. {result['person_name']} ({result['episode_age']}歳)")
            logger.info(f"   カテゴリ: {result['category']}")
            logger.info(f"   スコア: Gate {result['gate_score']:.1f} | LLM {result['llm_score']:.1f} | Total {result['total_score']:.1f}")
            logger.info(f"   反復: {result['iterations']}回")
            logger.info(f"   エピソード: {result['episode_text']}")
            displayed += 1

    # ========================================
    # 完了
    # ========================================
    logger.info(f"\n{'='*60}")
    if success_count >= len(results) * 0.7:  # 70%以上成功
        logger.info(f"✅ テスト成功 ({success_count}/{len(results)} = {success_count/len(results)*100:.1f}%)")
        logger.info(f"{'='*60}")
        return True
    else:
        logger.info(f"⚠️ テスト部分成功 ({success_count}/{len(results)} = {success_count/len(results)*100:.1f}%)")
        logger.info(f"{'='*60}")
        return False


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="Integrated Pipeline E2E Test")
    parser.add_argument('--count', type=int, default=5, help='テスト対象人物数')
    parser.add_argument('--episodes-per-person', type=int, default=1, help='1人あたりエピソード数')
    parser.add_argument('--provider', choices=['openai', 'anthropic'], default='openai', help='LLMプロバイダー')
    parser.add_argument('--model', help='モデル名')

    args = parser.parse_args()

    success = test_integrated_pipeline(
        max_persons=args.count,
        episodes_per_person=args.episodes_per_person,
        llm_provider=args.provider,
        llm_model=args.model
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
