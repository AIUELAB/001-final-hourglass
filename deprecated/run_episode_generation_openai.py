#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
エピソード生成システム実行スクリプト（OpenAI版）

OpenAI APIを使用してエピソードを生成する
テスト用バージョン
"""

import sys
import os
import logging
from datetime import datetime
from pathlib import Path

# .envファイルから環境変数を読み込み
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️ python-dotenvがインストールされていません")

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'episode_generation_openai_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def run_simple_test():
    """シンプルなテスト実行（1人分のみ）"""
    logger.info("\n" + "="*60)
    logger.info("🚀 エピソード生成システム（OpenAI版）開始")
    logger.info("="*60)

    try:
        # 必要なモジュールをインポート
        import pandas as pd
        from premium_episode_generator import PremiumEpisodeGenerator
        from episode_quality_evaluator import EpisodeQualityEvaluator

        # CSVファイル読み込み
        csv_files = list(Path('.').glob('ultra_think_*.csv'))
        if not csv_files:
            logger.error("CSVファイルが見つかりません")
            return False

        latest_csv = max(csv_files, key=lambda f: f.stat().st_mtime)
        logger.info(f"📂 使用するCSVファイル: {latest_csv}")

        df = pd.read_csv(str(latest_csv), encoding='utf-8')
        logger.info(f"📊 総人物数: {len(df)}件")

        # birth_year_intがある高認知度の人物を1人選択
        test_df = df[
            (df['birth_year_int'].notna()) &
            (df['recognition_score'] >= 8.0)
        ].sort_values('recognition_score', ascending=False).head(1)

        if test_df.empty:
            logger.error("テスト対象の人物が見つかりません")
            return False

        # 選択された人物の情報
        person = test_df.iloc[0]
        logger.info("\n" + "="*60)
        logger.info("🎯 テスト対象人物")
        logger.info("="*60)
        logger.info(f"名前: {person.get('person_name_ja', 'Unknown')}")
        logger.info(f"生年: {person.get('birth_year_int', 'Unknown')}")
        logger.info(f"認知度スコア: {person.get('recognition_score', 0.0)}")
        logger.info(f"カテゴリ: {person.get('category', 'Unknown')}")

        # エピソード生成器初期化（緩和モードのPDCAガーディアンを使用）
        from pdca_guardian import PDCAGuardian
        relaxed_guardian = PDCAGuardian(relaxed_mode=True)

        # 緩和モード用の設定
        generator_config = {
            'quality_threshold': 40.0,  # 通常は75.0
            'max_retries': 5,  # リトライ回数を増やす
            'preferred_api': 'openai',  # OpenAI優先
        }

        generator = PremiumEpisodeGenerator()
        generator.config.update(generator_config)  # 設定を更新
        generator.pdca_guardian = relaxed_guardian  # 緩和モードのガーディアンを設定

        # 人物データを辞書形式に変換
        person_data = {
            'person_id': person.get('person_id', ''),
            'person_name_ja': person.get('person_name_ja', ''),
            'birth_year': int(person.get('birth_year_int')) if pd.notna(person.get('birth_year_int')) else None,
            'death_year': int(person.get('death_year')) if pd.notna(person.get('death_year')) else None,
            'category': person.get('category', ''),
            'occupation': person.get('occupation', ''),
            'recognition_score': float(person.get('recognition_score', 0.0))
        }

        # エピソード生成
        logger.info("\n" + "="*60)
        logger.info("🎬 エピソード生成開始")
        logger.info("="*60)

        # 生成する年齢を決定（生年から現在まで）
        import random
        current_year = 2025
        person_age = current_year - person_data['birth_year'] if person_data['birth_year'] else 50

        # ランダムに2つの年齢を選択
        if person_age > 20:
            target_ages = random.sample(range(15, min(person_age, 80)), min(2, person_age - 15))
        else:
            target_ages = [15, 20]  # デフォルト

        episodes = generator.generate_premium_episodes(
            person_data=person_data,
            target_ages=target_ages
        )

        if episodes:
            logger.info(f"\n✅ {len(episodes)}個のエピソードを生成しました")

            # 品質評価
            evaluator = EpisodeQualityEvaluator()

            for i, episode in enumerate(episodes, 1):
                logger.info(f"\n--- エピソード {i} ---")
                logger.info(f"年齢: {episode.age}歳")
                logger.info(f"内容: {episode.episode_text}")

                # 品質評価
                quality_result = evaluator.evaluate_episode({
                    'age': episode.age,
                    'episode_text': episode.episode_text,
                    'person_name_ja': person_data['person_name_ja']
                }, person_data)

                logger.info(f"品質スコア: {quality_result['quality_score']:.1f}")
                logger.info(f"グレード: {quality_result['grade']}")

                # 保存用データ
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"output/test_episode_{person.get('person_id', 'unknown')}_{timestamp}.json"

                # outputディレクトリ作成
                Path("output").mkdir(exist_ok=True)

                # JSON形式で保存
                import json
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'person_data': person_data,
                        'episode': {
                            'age': episode.age,
                            'text': episode.episode_text,
                            'quality_score': episode.quality_score,
                            'metadata': episode.metadata
                        },
                        'evaluation': quality_result,
                        'timestamp': timestamp
                    }, f, ensure_ascii=False, indent=2)

                logger.info(f"💾 保存: {output_file}")

            return True
        else:
            logger.error("エピソード生成に失敗しました")
            return False

    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """メイン関数"""
    logger.info("🔍 OpenAI API キーチェック...")

    if not os.getenv('OPENAI_API_KEY'):
        logger.error("❌ OPENAI_API_KEYが設定されていません")
        logger.error("  .envファイルを確認してください")
        sys.exit(1)

    logger.info("✅ OpenAI API キーが設定されています")

    # シンプルテスト実行
    success = run_simple_test()

    if success:
        logger.info("\n🎉 テストが正常に完了しました")
        logger.info("生成されたエピソードはoutputディレクトリに保存されています")
        sys.exit(0)
    else:
        logger.error("\n❌ テスト中にエラーが発生しました")
        sys.exit(1)


if __name__ == "__main__":
    main()
