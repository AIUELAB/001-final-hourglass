#!/usr/bin/env python3
"""
Phase 8.2: バッチエピソード改善システム

Phase 7で構築したRULE_182 + RULE_183を活用し、
100エピソードを効率的に改善する。
"""

import csv
import json
import time
import sys
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

# Phase 7システムのインポート
sys.path.insert(0, str(Path(__file__).parent / "rules"))

from rules.unified_improvement_interface import (
    get_unified_interface,
    CostManager
)


class BatchEpisodeImprover:
    """100エピソード一括改善システム"""

    def __init__(
        self,
        daily_budget_usd: float = 2.50,
        checkpoint_interval: int = 10
    ):
        """
        Args:
            daily_budget_usd: 日次予算上限
            checkpoint_interval: チェックポイント保存間隔
        """
        self.interface = get_unified_interface(reset=True)
        self.interface.cost_manager = CostManager(daily_limit_usd=daily_budget_usd)
        self.checkpoint_interval = checkpoint_interval

        self.stats = {
            "total_processed": 0,
            "improved": 0,
            "failed": 0,
            "skipped": 0,
            "total_cost": 0.0,
            "start_time": None,
            "end_time": None,
            "improvements": []  # 詳細記録
        }

    def load_episodes_with_scores(
        self,
        episodes_path: str,
        scores_path: str
    ) -> List[Dict]:
        """エピソードとスコアを統合読み込み"""

        # エピソード読み込み
        episodes = {}
        with open(episodes_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                episodes[row['episode_id']] = row

        # スコア読み込み
        scores = {}
        with open(scores_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                scores[row['episode_id']] = float(row['impact_keyword_score'])

        # 統合してソート（スコア昇順＝優先度順）
        combined = []
        for episode_id, episode in episodes.items():
            if episode_id in scores:
                combined.append({
                    **episode,
                    'current_score': scores[episode_id]
                })

        # スコア昇順でソート（低スコア＝高優先度）
        combined.sort(key=lambda x: x['current_score'])

        return combined

    def improve_single_episode(
        self,
        episode: Dict,
        llm_provider: str = "openai"
    ) -> Tuple[Optional[str], Dict]:
        """
        単一エピソードの改善

        Returns:
            (improved_text, summary)
        """
        try:
            # 人物コンテキスト構築
            person_context = {
                "person_name": episode['person_name'],
                "birth_year": None,  # CSVから取得可能なら設定
                "category": episode.get('category', 'unknown'),
                "age": int(episode['episode_age'])
            }

            # Phase 7の統合インターフェースで改善
            # （RULE_179評価は内部で自動実行される）
            improved_text, summary = self.interface.improve_episode_unified(
                episode_id=episode['episode_id'],
                person_name=episode['person_name'],
                episode_text=episode['episode_text'],
                database_age=int(episode['episode_age']),
                person_context=person_context,
                strategy_mode="auto",  # Auto戦略
                llm_provider=llm_provider
            )

            return improved_text, summary

        except Exception as e:
            import traceback
            return None, {
                "improved": False,
                "method": "error",
                "error": str(e),
                "traceback": traceback.format_exc()
            }

    def save_checkpoint(
        self,
        output_path: str,
        improved_episodes: List[Dict],
        checkpoint_num: int
    ):
        """チェックポイント保存"""

        checkpoint_path = output_path.replace('.csv', f'_checkpoint_{checkpoint_num}.csv')

        with open(checkpoint_path, 'w', encoding='utf-8-sig', newline='') as f:
            if improved_episodes:
                fieldnames = improved_episodes[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(improved_episodes)

        print(f"  💾 チェックポイント保存: {checkpoint_path}")

    def process_batch(
        self,
        episodes_path: str,
        scores_path: str,
        output_path: str,
        max_episodes: Optional[int] = None,
        llm_provider: str = "openai",
        test_mode: bool = False
    ) -> Dict:
        """
        バッチ処理メイン

        Args:
            episodes_path: 元のエピソードCSV
            scores_path: スコアCSV
            output_path: 出力先CSV
            max_episodes: 処理件数上限（Noneなら全件）
            llm_provider: LLMプロバイダー
            test_mode: テストモード（5件のみ）
        """

        print("=" * 60)
        print("Phase 8.2: バッチエピソード改善システム")
        print("=" * 60)

        # データ読み込み
        print("\n📂 データ読み込み中...")
        episodes = self.load_episodes_with_scores(episodes_path, scores_path)
        print(f"✅ {len(episodes)}エピソード読み込み完了（優先度順ソート済み）")

        # 処理件数決定
        if test_mode:
            max_episodes = 5
            print(f"\n⚠️  テストモード: 最初の{max_episodes}件のみ処理")

        if max_episodes:
            episodes = episodes[:max_episodes]
            print(f"📋 処理対象: {len(episodes)}件")

        # 処理開始
        self.stats['start_time'] = datetime.now()
        improved_episodes = []

        print(f"\n🚀 改善処理開始（予算: ${self.interface.cost_manager.daily_limit:.2f}）")
        print("-" * 60)

        for idx, episode in enumerate(episodes, 1):
            print(f"\n[{idx}/{len(episodes)}] {episode['episode_id']}: {episode['person_name']}")
            print(f"  現在スコア: {episode['current_score']:.1f}点")
            print(f"  元テキスト: {episode['episode_text'][:80]}...")

            # 予算チェック
            remaining = self.interface.cost_manager.get_remaining_budget()
            print(f"  残予算: ${remaining:.2f}")

            if remaining < 0.01:
                print(f"  ⚠️  予算残少 - スキップ")
                self.stats['skipped'] += 1
                continue

            # 改善実行
            start_time = time.time()
            improved_text, summary = self.improve_single_episode(episode, llm_provider)
            elapsed = time.time() - start_time

            # 結果記録
            if improved_text and summary.get('improved', False):
                # 改善成功
                episode_improved = {
                    'episode_id': episode['episode_id'],
                    'person_name': episode['person_name'],
                    'episode_age': episode['episode_age'],
                    'episode_text': improved_text,  # 改善後テキスト
                    'episode_type': episode.get('episode_type', 'iconic'),
                    'character_count': len(improved_text),
                    'category': episode.get('category', 'unknown'),
                    'is_valid': 'True',
                    'violation_count': 0,
                    'emotional_impact_score': episode.get('emotional_impact_score', 0.3),
                    'specificity_score': episode.get('specificity_score', 0.5),
                    'has_numerical_data': 'True',
                    'has_proper_nouns': 'True',
                    'fact_check_status': episode.get('fact_check_status', 'improved'),
                    'created_date': datetime.now().strftime('%Y%m%d_%H%M%S'),
                    'improvement_method': summary.get('method', 'unknown'),
                    'processing_time': f"{elapsed:.2f}s"
                }

                # スコア再評価（オプション）
                if 'final_score' in summary:
                    improvement = summary['final_score'] - episode['current_score']
                    print(f"  ✅ 改善成功: {summary['method']}")
                    print(f"     スコア: {episode['current_score']:.1f} → {summary['final_score']:.1f} (+{improvement:.1f})")
                else:
                    print(f"  ✅ 改善成功: {summary['method']}")
                    print(f"     改善後文字数: {len(improved_text)}文字")

                improved_episodes.append(episode_improved)
                self.stats['improved'] += 1

                # 詳細記録
                self.stats['improvements'].append({
                    "episode_id": episode['episode_id'],
                    "person_name": episode['person_name'],
                    "method": summary.get('method'),
                    "original_score": episode['current_score'],
                    "final_score": summary.get('final_score'),
                    "processing_time": elapsed
                })

            else:
                # 改善失敗 - 元のエピソードを保持（current_scoreフィールドを削除）
                error_msg = summary.get('error', summary.get('reason', 'unknown'))
                print(f"  ❌ 改善失敗: {error_msg}")
                self.stats['failed'] += 1

                # 元データから必要フィールドのみコピー
                episode_copy = {
                    key: value for key, value in episode.items()
                    if key != 'current_score'  # スコアフィールドは除外
                }
                improved_episodes.append(episode_copy)

            self.stats['total_processed'] += 1

            # チェックポイント保存
            if idx % self.checkpoint_interval == 0:
                self.save_checkpoint(output_path, improved_episodes, idx // self.checkpoint_interval)

            # コスト更新
            if 'cost' in summary:
                self.stats['total_cost'] += summary['cost']

        # 最終保存
        print("\n" + "=" * 60)
        print("💾 最終結果保存中...")

        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            if improved_episodes:
                # すべてのエピソードから全フィールド名を収集
                all_fieldnames = set()
                for ep in improved_episodes:
                    all_fieldnames.update(ep.keys())

                # フィールド名を決定（順序を保証）
                base_fields = ['episode_id', 'person_name', 'episode_age', 'episode_text',
                               'episode_type', 'character_count', 'category', 'is_valid',
                               'violation_count', 'emotional_impact_score', 'specificity_score',
                               'has_numerical_data', 'has_proper_nouns', 'fact_check_status',
                               'created_date']
                extra_fields = sorted(all_fieldnames - set(base_fields))
                fieldnames = base_fields + extra_fields

                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(improved_episodes)

        print(f"✅ 保存完了: {output_path}")

        # 統計保存
        self.stats['end_time'] = datetime.now()
        stats_path = output_path.replace('.csv', '_stats.json')

        with open(stats_path, 'w', encoding='utf-8') as f:
            stats_serializable = {
                **self.stats,
                'start_time': self.stats['start_time'].isoformat(),
                'end_time': self.stats['end_time'].isoformat(),
                'duration_seconds': (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            }
            json.dump(stats_serializable, f, ensure_ascii=False, indent=2)

        print(f"✅ 統計保存: {stats_path}")

        # サマリー表示
        self.print_summary()

        return self.stats

    def print_summary(self):
        """処理サマリー表示"""

        print("\n" + "=" * 60)
        print("📊 処理サマリー")
        print("=" * 60)

        print(f"\n処理件数: {self.stats['total_processed']}件")
        print(f"  ✅ 改善成功: {self.stats['improved']}件 ({self.stats['improved']/max(self.stats['total_processed'],1)*100:.1f}%)")
        print(f"  ❌ 改善失敗: {self.stats['failed']}件")
        print(f"  ⏭️  スキップ: {self.stats['skipped']}件")

        print(f"\nコスト:")
        print(f"  使用額: ${self.stats['total_cost']:.2f}")
        print(f"  残予算: ${self.interface.cost_manager.get_remaining_budget():.2f}")

        if self.stats['start_time'] and self.stats['end_time']:
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            print(f"\n処理時間: {duration:.1f}秒 ({duration/60:.1f}分)")

            if self.stats['total_processed'] > 0:
                avg_time = duration / self.stats['total_processed']
                print(f"  平均: {avg_time:.2f}秒/件")

        # 改善効果分析
        if self.stats['improvements']:
            improvements_with_score = [
                imp for imp in self.stats['improvements']
                if imp.get('final_score') is not None
            ]

            if improvements_with_score:
                avg_improvement = sum(
                    imp['final_score'] - imp['original_score']
                    for imp in improvements_with_score
                ) / len(improvements_with_score)

                print(f"\n改善効果:")
                print(f"  平均スコア向上: +{avg_improvement:.1f}点")

        print("\n" + "=" * 60)


def main():
    """メイン実行"""

    import argparse

    parser = argparse.ArgumentParser(description='Phase 8.2: バッチエピソード改善')
    parser.add_argument('--episodes', default='episodes_validated_100_20251001.csv',
                        help='エピソードCSV')
    parser.add_argument('--scores', default='episodes_validated_100_20251001_optimized_evaluation.csv',
                        help='スコアCSV')
    parser.add_argument('--output', default='episodes_phase8_improved.csv',
                        help='出力CSV')
    parser.add_argument('--max-episodes', type=int, default=None,
                        help='処理件数上限')
    parser.add_argument('--budget', type=float, default=2.50,
                        help='予算上限（USD）')
    parser.add_argument('--provider', default='openai',
                        choices=['openai', 'anthropic', 'mock'],
                        help='LLMプロバイダー')
    parser.add_argument('--test', action='store_true',
                        help='テストモード（5件のみ）')

    args = parser.parse_args()

    # 実行
    improver = BatchEpisodeImprover(daily_budget_usd=args.budget)

    stats = improver.process_batch(
        episodes_path=args.episodes,
        scores_path=args.scores,
        output_path=args.output,
        max_episodes=args.max_episodes,
        llm_provider=args.provider,
        test_mode=args.test
    )

    # 終了コード
    if stats['improved'] > 0:
        sys.exit(0)  # 成功
    else:
        sys.exit(1)  # 失敗


if __name__ == "__main__":
    main()
