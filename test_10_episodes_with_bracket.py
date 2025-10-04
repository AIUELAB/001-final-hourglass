#!/usr/bin/env python3
"""
Phase 5: 括弧表示システム 10エピソードテスト

目的:
1. 括弧表示エンジンをエピソード生成システムに統合
2. 10件の多様な人物でテスト実行
3. 括弧表示の正確性を検証

テスト対象:
- 架空キャラクター: 2件
- お笑い芸人: 3件
- バンド: 3件
- YouTuber: 2件
"""

import sqlite3
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

from bracket_display_engine import (
    BracketDisplayEngine,
    BracketDisplayResult
)
from smart_iteration_engine import SmartIterationEngine, GenerationResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BracketEpisodeGenerator:
    """括弧表示対応エピソード生成器"""

    def __init__(
        self,
        db_path: str = "episode_database.db",
        llm_provider: str = "openai",
        model: Optional[str] = None
    ):
        """
        初期化

        Args:
            db_path: データベースパス
            llm_provider: LLMプロバイダー
            model: モデル名
        """
        self.db_path = db_path
        self.bracket_engine = BracketDisplayEngine()
        self.episode_engine = SmartIterationEngine(
            max_iterations=3,
            target_gate_score=8.0,
            llm_provider=llm_provider,
            model=model,
            enable_llm_evaluation=False  # 速度優先
        )

    def load_test_persons(self) -> List[Dict]:
        """
        テスト対象人物を読み込み

        Returns:
            人物リスト（10件）
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # テスト対象の具体的な人物を指定
        test_persons = [
            # 架空キャラクター（2件）
            "さくらももこ",
            "モンキー・D・ルフィ",

            # お笑い芸人（3件）
            "又吉直樹",
            "上田晋也",
            "ノブ",

            # バンド（3件）
            "hyde",
            "野田洋次郎",
            "TERU",

            # YouTuber（2件）
            "しばゆー",
            "ぺけたん"
        ]

        persons = []
        for person_name in test_persons:
            cursor.execute("""
                SELECT
                    person_id,
                    person_name_ja,
                    birth_year,
                    category,
                    entity_type,
                    group_affiliation,
                    primary_work,
                    show_group_in_bracket,
                    bracket_display_text,
                    group_status,
                    fame_level
                FROM persons
                WHERE person_name_ja = ?
                ORDER BY
                    CASE
                        WHEN entity_type = 'fictional_character' THEN 1
                        WHEN show_group_in_bracket = 1 THEN 2
                        ELSE 3
                    END
                LIMIT 1
            """, (person_name,))

            row = cursor.fetchone()
            if row:
                persons.append(dict(row))
            else:
                logger.warning(f"人物が見つかりません: {person_name}")

        conn.close()

        logger.info(f"テスト対象人物: {len(persons)}件読み込み")
        return persons

    def generate_episode_with_bracket(
        self,
        person_data: Dict,
        age: int = 30
    ) -> Dict:
        """
        括弧表示付きエピソード生成

        Args:
            person_data: 人物データ（データベースから取得）
            age: エピソード年齢

        Returns:
            生成結果辞書
        """
        person_name = person_data['person_name_ja']

        # Step 1: 括弧表示判定
        # bracket_display_engineは'person_name'キーを期待するため、データを変換
        bracket_input = {
            'person_name': person_name,
            'entity_type': person_data.get('entity_type'),
            'primary_work': person_data.get('primary_work'),
            'group_affiliation': person_data.get('group_affiliation'),
            'show_group_in_bracket': person_data.get('show_group_in_bracket'),
            'bracket_display_text': person_data.get('bracket_display_text'),
            'group_status': person_data.get('group_status'),
            'fame_level': person_data.get('fame_level')
        }
        bracket_result = self.bracket_engine.should_show_bracket(bracket_input)

        logger.info(f"{'='*80}")
        logger.info(f"人物: {person_name} ({age}歳)")
        logger.info(f"括弧表示: {bracket_result.should_show}")
        logger.info(f"理由: {bracket_result.reason}")

        if bracket_result.should_show:
            logger.info(f"表示形式: {bracket_result.formatted_name}")
            logger.info(f"括弧テキスト: {bracket_result.bracket_text}")

        # Step 2: エピソード生成（括弧表示を考慮）
        generation_result = self.episode_engine.generate_episode(
            person_name=bracket_result.formatted_name,  # 括弧付き名前を使用
            age=age,
            category=person_data.get('category', 'エンタメ'),
            additional_context={
                'bracket_text': bracket_result.bracket_text,
                'entity_type': person_data.get('entity_type'),
                'group_affiliation': person_data.get('group_affiliation')
            }
        )

        # Step 3: 括弧内ワードの重複チェックと除去
        if bracket_result.should_show and bracket_result.bracket_text:
            episode_text = generation_result.final_episode

            # エピソード本文から括弧内ワードを除去
            cleaned_text = self.bracket_engine.remove_bracket_word_from_text(
                text=episode_text,
                bracket_word=bracket_result.bracket_text,
                person_name=person_name
            )

            # 重複検証
            is_valid, duplications = self.bracket_engine.validate_no_word_duplication(
                episode_text=cleaned_text,
                bracket_word=bracket_result.bracket_text,
                person_name=person_name
            )

            if not is_valid:
                logger.warning(f"⚠️ 括弧内ワードの重複検出: {duplications}")

                # 🆕 自動修正を試みる
                logger.info(f"🔧 自動修正を実行中...")
                corrected_text = self.bracket_engine.auto_correct_duplication(
                    episode_text=cleaned_text,
                    bracket_word=bracket_result.bracket_text,
                    person_name=person_name
                )

                # 再検証
                is_valid_after, duplications_after = self.bracket_engine.validate_no_word_duplication(
                    episode_text=corrected_text,
                    bracket_word=bracket_result.bracket_text,
                    person_name=person_name
                )

                if is_valid_after:
                    logger.info(f"✅ 自動修正成功（重複なし）")
                    final_episode = corrected_text
                    is_valid = True
                    duplications = []
                else:
                    logger.error(f"❌ 自動修正失敗（重複残存）: {duplications_after}")
                    final_episode = corrected_text  # ベストエフォート
                    is_valid = False
                    duplications = duplications_after
            else:
                logger.info(f"✅ 括弧内ワード重複なし")
                final_episode = cleaned_text
        else:
            final_episode = generation_result.final_episode
            is_valid = True
            duplications = []

        # Step 4: 結果を返す
        return {
            'person_id': person_data['person_id'],
            'person_name': person_name,
            'formatted_name': bracket_result.formatted_name,
            'episode_age': age,
            'episode_text': final_episode,
            'category': person_data.get('category'),

            # 括弧表示情報
            'show_bracket': bracket_result.should_show,
            'bracket_text': bracket_result.bracket_text,
            'bracket_reason': bracket_result.reason,

            # 品質情報
            'success': generation_result.success,
            'iterations': generation_result.total_iterations,
            'gate_score': generation_result.final_gate_score,
            'duplication_check': is_valid,
            'duplications': duplications,

            # メタデータ
            'entity_type': person_data.get('entity_type'),
            'group_affiliation': person_data.get('group_affiliation'),
            'primary_work': person_data.get('primary_work'),
            'timestamp': datetime.now().isoformat()
        }

    def run_test_generation(self) -> List[Dict]:
        """
        10エピソードテスト生成を実行

        Returns:
            生成結果リスト
        """
        print("="*80)
        print("Phase 5: 括弧表示システム 10エピソードテスト")
        print("="*80)

        # テスト対象を読み込み
        persons = self.load_test_persons()

        if len(persons) < 10:
            logger.error(f"テスト対象が不足: {len(persons)}件（10件必要）")
            return []

        # エピソード生成
        results = []
        success_count = 0
        bracket_count = 0
        duplication_error_count = 0

        for i, person_data in enumerate(persons, 1):
            print(f"\n[{i}/10] {person_data['person_name_ja']}")

            try:
                result = self.generate_episode_with_bracket(
                    person_data=person_data,
                    age=30
                )

                results.append(result)

                if result['success']:
                    success_count += 1

                if result['show_bracket']:
                    bracket_count += 1

                if not result['duplication_check']:
                    duplication_error_count += 1

                # 結果サマリー表示
                status = "✅" if result['success'] else "❌"
                bracket_status = f"[{result['bracket_text']}]" if result['show_bracket'] else "[括弧なし]"
                print(f"{status} {bracket_status} - {result['iterations']}回反復, スコア{result['gate_score']:.1f}")

            except Exception as e:
                logger.error(f"エピソード生成エラー: {person_data['person_name_ja']} - {e}")
                import traceback
                traceback.print_exc()

        # 統計表示
        print("\n" + "="*80)
        print("テスト結果サマリー")
        print("="*80)
        print(f"生成成功: {success_count}/10")
        print(f"括弧表示: {bracket_count}/10")
        print(f"重複エラー: {duplication_error_count}/10")

        return results

    def save_results(self, results: List[Dict], output_path: str = None):
        """
        結果をJSONファイルに保存

        Args:
            results: 生成結果リスト
            output_path: 出力ファイルパス
        """
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"test_10_episodes_results_{timestamp}.json"

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        logger.info(f"結果を保存: {output_path}")

        # レポート生成
        self._generate_report(results, output_path.replace('.json', '_report.md'))

    def _generate_report(self, results: List[Dict], report_path: str):
        """
        テストレポートを生成

        Args:
            results: 生成結果リスト
            report_path: レポート出力パス
        """
        timestamp = datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')

        report_lines = [
            f"# Phase 5: 括弧表示システム 10エピソードテスト結果",
            f"",
            f"**実施日時**: {timestamp}",
            f"**テスト件数**: {len(results)}件",
            f"",
            f"---",
            f"",
            f"## 📊 統計サマリー",
            f"",
        ]

        # 統計計算
        success_count = sum(1 for r in results if r['success'])
        bracket_count = sum(1 for r in results if r['show_bracket'])
        duplication_ok_count = sum(1 for r in results if r['duplication_check'])

        avg_iterations = sum(r['iterations'] for r in results) / len(results) if results else 0
        avg_score = sum(r['gate_score'] for r in results) / len(results) if results else 0

        report_lines.extend([
            f"| 項目 | 結果 |",
            f"|------|------|",
            f"| 生成成功率 | {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%) |",
            f"| 括弧表示数 | {bracket_count}/{len(results)} |",
            f"| 重複チェック通過 | {duplication_ok_count}/{len(results)} |",
            f"| 平均反復回数 | {avg_iterations:.1f}回 |",
            f"| 平均品質スコア | {avg_score:.1f}/10.0 |",
            f"",
            f"---",
            f"",
            f"## 📝 個別結果",
            f"",
        ])

        # 個別結果
        for i, result in enumerate(results, 1):
            bracket_display = f"{result['formatted_name']}" if result['show_bracket'] else result['person_name']
            status = "✅ 成功" if result['success'] else "❌ 失敗"
            dup_status = "✅ 重複なし" if result['duplication_check'] else f"⚠️ 重複あり: {result['duplications']}"

            report_lines.extend([
                f"### {i}. {result['person_name']}",
                f"",
                f"- **表示形式**: {bracket_display}",
                f"- **Entity Type**: {result['entity_type']}",
                f"- **括弧表示**: {'あり' if result['show_bracket'] else 'なし'}",
            ])

            if result['show_bracket']:
                report_lines.append(f"- **括弧テキスト**: {result['bracket_text']}")
                report_lines.append(f"- **理由**: {result['bracket_reason']}")

            report_lines.extend([
                f"- **生成状態**: {status}",
                f"- **反復回数**: {result['iterations']}回",
                f"- **品質スコア**: {result['gate_score']}/10.0",
                f"- **重複チェック**: {dup_status}",
                f"",
                f"**エピソード本文**:",
                f"```",
                f"{result['episode_text'][:200]}...",  # 最初の200文字のみ
                f"```",
                f"",
            ])

        # レポート保存
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))

        logger.info(f"レポートを保存: {report_path}")


def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description='Phase 5: 括弧表示システム 10エピソードテスト')
    parser.add_argument('--db', default='episode_database.db', help='データベースパス')
    parser.add_argument('--provider', default='openai', choices=['openai', 'anthropic'], help='LLMプロバイダー')
    parser.add_argument('--model', help='モデル名')
    parser.add_argument('--output', help='出力ファイルパス')

    args = parser.parse_args()

    # 生成器初期化
    generator = BracketEpisodeGenerator(
        db_path=args.db,
        llm_provider=args.provider,
        model=args.model
    )

    # テスト実行
    results = generator.run_test_generation()

    # 結果保存
    if results:
        generator.save_results(results, args.output)
        print("\n✅ Phase 5テスト完了！")
    else:
        print("\n❌ テスト失敗")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
