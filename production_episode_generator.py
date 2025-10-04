"""
Production Episode Generator
=============================

SmartIterationEngineを使用した本番環境向けエピソード生成システム

機能:
- データベースから人物リストを読み込み
- バッチ処理でエピソード生成
- CSV形式で結果を出力
- 既存システムとの互換性確保

実行コマンド:
    python3 production_episode_generator.py --input persons.csv --output episodes_generated.csv --count 50
"""

import os
import sys
import argparse
import csv
import json
from typing import List, Dict, Optional
from datetime import datetime
import sqlite3
from pathlib import Path

from smart_iteration_engine import SmartIterationEngine, GenerationResult


class ProductionEpisodeGenerator:
    """本番環境向けエピソード生成器"""

    def __init__(
        self,
        llm_provider: str = "openai",
        model: Optional[str] = None,
        enable_llm_evaluation: bool = True,
        max_iterations: int = 3,
        target_score: float = 8.0
    ):
        """
        初期化

        Args:
            llm_provider: LLMプロバイダー
            model: モデル名
            enable_llm_evaluation: LLM評価の有効化
            max_iterations: 最大反復回数
            target_score: 目標スコア
        """
        self.llm_provider = llm_provider
        self.model = model
        self.enable_llm_evaluation = enable_llm_evaluation
        self.max_iterations = max_iterations
        self.target_score = target_score

        # エンジン初期化
        print(f"🚀 Initializing SmartIterationEngine...")
        print(f"   Provider: {llm_provider}")
        print(f"   Model: {model or 'default'}")
        print(f"   LLM Evaluation: {'Enabled' if enable_llm_evaluation else 'Disabled'}")

        self.engine = SmartIterationEngine(
            max_iterations=max_iterations,
            target_gate_score=target_score,
            llm_provider=llm_provider,
            model=model,
            enable_llm_evaluation=enable_llm_evaluation
        )

    def load_persons_from_csv(self, csv_path: str) -> List[Dict]:
        """
        CSVファイルから人物リストを読み込み

        Args:
            csv_path: CSVファイルパス

        Returns:
            人物リスト
        """
        persons = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                persons.append({
                    'name': row.get('person_name') or row.get('name'),
                    'age': int(row.get('episode_age') or row.get('age')),
                    'category': row.get('category', 'エンターテインメント'),
                    'person_id': row.get('person_id'),
                    'birth_year': row.get('birth_year')
                })
        return persons

    def load_persons_from_database(self, db_path: str, limit: Optional[int] = None) -> List[Dict]:
        """
        SQLiteデータベースから人物リストを読み込み

        Args:
            db_path: データベースパス
            limit: 取得件数制限

        Returns:
            人物リスト
        """
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = """
            SELECT person_id, person_name_ja, birth_year, category, entity_type
            FROM persons
            WHERE birth_year IS NOT NULL
              AND entity_type = 'real_person'
            ORDER BY recognition_score DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query)
        rows = cursor.fetchall()

        persons = []
        for row in rows:
            person_id, name, birth_year, category, entity_type = row

            # entity_type検証（二重チェック）
            if entity_type != 'real_person':
                print(f"⚠️ Skipping {name}: entity_type={entity_type}")
                continue

            # 年齢を計算（例: 30歳、45歳など適切な年齢を選択）
            current_year = datetime.now().year
            age_options = [25, 30, 35, 40, 45, 50]
            # 誕生年から最も適切な年齢を選択
            age = 30  # デフォルト

            persons.append({
                'person_id': person_id,
                'name': name,
                'age': age,
                'category': category or 'エンターテインメント',
                'birth_year': birth_year,
                'entity_type': entity_type
            })

        conn.close()
        return persons

    def generate_batch(
        self,
        persons: List[Dict],
        start_index: int = 0,
        count: Optional[int] = None
    ) -> List[Dict]:
        """
        バッチ処理でエピソード生成

        Args:
            persons: 人物リスト
            start_index: 開始インデックス
            count: 生成件数

        Returns:
            生成結果リスト
        """
        if count:
            persons = persons[start_index:start_index + count]
        else:
            persons = persons[start_index:]

        print(f"\n{'='*80}")
        print(f"🎬 Production Episode Generation")
        print(f"{'='*80}")
        print(f"Total Persons: {len(persons)}")
        print(f"Provider: {self.llm_provider}")
        print(f"Max Iterations: {self.max_iterations}")
        print(f"Target Score: {self.target_score}")
        print(f"{'='*80}\n")

        results = []
        success_count = 0
        failed_count = 0

        for i, person in enumerate(persons, 1):
            print(f"\n[{i}/{len(persons)}] Generating episode for: {person['name']} ({person['age']}歳)")

            try:
                result = self.engine.generate_episode(
                    person_name=person['name'],
                    age=person['age'],
                    category=person['category']
                )

                status = "✅ SUCCESS" if result.success else "❌ FAILED"
                print(f"{status} - {result.total_iterations} iterations, {result.final_gate_score:.1f} score")

                if result.success:
                    success_count += 1
                else:
                    failed_count += 1

                # 結果を記録
                results.append({
                    'person_id': person.get('person_id'),
                    'person_name': person['name'],
                    'episode_age': person['age'],
                    'category': person['category'],
                    'episode_text': result.final_episode,
                    'success': result.success,
                    'iterations': result.total_iterations,
                    'gate_score': result.final_gate_score,
                    'llm_score': result.final_llm_score,
                    'total_score': result.final_total_score,
                    'character_count': len(result.final_episode),
                    'tokens_used': result.total_tokens,
                    'generation_time': result.total_time,
                    'failure_reason': result.failure_reason,
                    'generated_at': datetime.now().isoformat()
                })

            except Exception as e:
                print(f"❌ ERROR: {e}")
                failed_count += 1
                results.append({
                    'person_id': person.get('person_id'),
                    'person_name': person['name'],
                    'episode_age': person['age'],
                    'category': person['category'],
                    'episode_text': None,
                    'success': False,
                    'error': str(e),
                    'generated_at': datetime.now().isoformat()
                })

        # サマリー表示
        print(f"\n{'='*80}")
        print(f"📊 Generation Summary")
        print(f"{'='*80}")
        print(f"Total: {len(results)}")
        print(f"Success: {success_count} ({success_count/len(results)*100:.1f}%)")
        print(f"Failed: {failed_count} ({failed_count/len(results)*100:.1f}%)")
        print(f"{'='*80}\n")

        return results

    def save_to_csv(self, results: List[Dict], output_path: str) -> None:
        """
        結果をCSVファイルに保存（UTF-8 BOM付き）

        Args:
            results: 生成結果リスト
            output_path: 出力ファイルパス
        """
        if not results:
            print("⚠️ No results to save")
            return

        # CSVヘッダー
        fieldnames = [
            'person_id',
            'person_name',
            'episode_age',
            'category',
            'episode_text',
            'success',
            'iterations',
            'gate_score',
            'llm_score',
            'total_score',
            'character_count',
            'tokens_used',
            'generation_time',
            'failure_reason',
            'generated_at'
        ]

        # UTF-8 BOM付きで書き込み（Excel対応）
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for result in results:
                # None値を空文字列に変換
                row = {k: (v if v is not None else '') for k, v in result.items()}
                writer.writerow(row)

        print(f"💾 Results saved to: {output_path}")

    def save_to_json(self, results: List[Dict], output_path: str) -> None:
        """
        結果をJSONファイルに保存

        Args:
            results: 生成結果リスト
            output_path: 出力ファイルパス
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"💾 Results saved to: {output_path}")


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="Production Episode Generator")

    # 入力オプション
    parser.add_argument(
        '--input',
        help='Input CSV file path'
    )
    parser.add_argument(
        '--database',
        help='SQLite database path'
    )

    # 出力オプション
    parser.add_argument(
        '--output',
        default=f'episodes_generated_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
        help='Output CSV file path'
    )
    parser.add_argument(
        '--json',
        help='Output JSON file path (optional)'
    )

    # 生成オプション
    parser.add_argument(
        '--count',
        type=int,
        help='Number of episodes to generate'
    )
    parser.add_argument(
        '--start',
        type=int,
        default=0,
        help='Start index (default: 0)'
    )

    # LLMオプション
    parser.add_argument(
        '--provider',
        choices=['openai', 'anthropic'],
        default='openai',
        help='LLM provider'
    )
    parser.add_argument(
        '--model',
        help='LLM model name'
    )
    parser.add_argument(
        '--no-llm-eval',
        action='store_true',
        help='Disable LLM evaluation'
    )

    # 品質オプション
    parser.add_argument(
        '--max-iterations',
        type=int,
        default=3,
        help='Max iterations per episode'
    )
    parser.add_argument(
        '--target-score',
        type=float,
        default=8.0,
        help='Target gate score'
    )

    args = parser.parse_args()

    # 入力チェック
    if not args.input and not args.database:
        parser.error("Either --input or --database must be specified")

    try:
        # ジェネレーター初期化
        generator = ProductionEpisodeGenerator(
            llm_provider=args.provider,
            model=args.model,
            enable_llm_evaluation=not args.no_llm_eval,
            max_iterations=args.max_iterations,
            target_score=args.target_score
        )

        # 人物リスト読み込み
        if args.input:
            print(f"📂 Loading persons from CSV: {args.input}")
            persons = generator.load_persons_from_csv(args.input)
        else:
            print(f"📂 Loading persons from database: {args.database}")
            persons = generator.load_persons_from_database(args.database, limit=args.count)

        print(f"✅ Loaded {len(persons)} persons")

        # バッチ生成
        results = generator.generate_batch(
            persons=persons,
            start_index=args.start,
            count=args.count
        )

        # CSV保存
        generator.save_to_csv(results, args.output)

        # JSON保存（オプション）
        if args.json:
            generator.save_to_json(results, args.json)

        print(f"\n✅ Production generation complete!")
        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
