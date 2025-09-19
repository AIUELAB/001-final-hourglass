#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
エピソード大量生成システム（Anthropic Claude API版）
$10のクレジットで約33,000エピソード生成可能
"""

import os
import sys
import json
import time
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import anthropic
from tqdm import tqdm

# .envファイルから環境変数を読み込み
from dotenv import load_dotenv
load_dotenv()

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'episode_generation_anthropic_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class EpisodeResult:
    """エピソード生成結果"""
    person_id: str
    person_name: str
    age: int
    episode_text: str
    quality_score: float = 0.0
    generation_time: float = 0.0
    model_used: str = "claude-3-haiku-20240307"
    success: bool = True
    error_message: Optional[str] = None


class AnthropicEpisodeGenerator:
    """Anthropic APIを使用したエピソード生成器"""

    def __init__(self, relaxed_mode: bool = True):
        """初期化

        Args:
            relaxed_mode: PDCAガーディアンの緩和モード使用
        """
        self.client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.relaxed_mode = relaxed_mode

        # PDCAガーディアン（緩和モード）
        if relaxed_mode:
            from pdca_guardian import PDCAGuardian
            self.pdca_guardian = PDCAGuardian(relaxed_mode=True)
        else:
            self.pdca_guardian = None

        # 統計情報
        self.stats = {
            'total_generated': 0,
            'successful': 0,
            'failed': 0,
            'total_cost': 0.0,
            'total_time': 0.0
        }

    def generate_episode(self, person_data: Dict[str, Any], age: int) -> EpisodeResult:
        """単一エピソード生成

        Args:
            person_data: 人物データ
            age: エピソード年齢

        Returns:
            生成結果
        """
        start_time = time.time()
        person_name = person_data.get('person_name_ja', '')
        person_id = person_data.get('person_id', '')

        try:
            # プロンプト構築
            prompt = self._build_prompt(person_data, age)

            # Claude APIで生成（Haikuモデル - 最もコスト効率が良い）
            response = self.client.messages.create(
                model='claude-3-haiku-20240307',
                max_tokens=400,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            episode_text = response.content[0].text.strip()

            # PDCAガーディアンでのチェック（緩和モード）
            if self.pdca_guardian:
                violations = self.pdca_guardian.check_episode_quality(
                    episode_text, age, person_name
                )
                if violations:
                    # 違反があっても緩和モードなので警告のみ
                    logger.warning(f"PDCA違反検出（{len(violations)}件）: {person_name}")

            # 文字数調整（長すぎる場合）
            if len(episode_text) > 250:
                episode_text = episode_text[:247] + "..."

            generation_time = time.time() - start_time

            # 統計更新
            self.stats['total_generated'] += 1
            self.stats['successful'] += 1
            self.stats['total_time'] += generation_time
            self.stats['total_cost'] += 0.0003  # Haiku推定コスト

            return EpisodeResult(
                person_id=person_id,
                person_name=person_name,
                age=age,
                episode_text=episode_text,
                generation_time=generation_time,
                success=True
            )

        except Exception as e:
            logger.error(f"エピソード生成エラー ({person_name}, {age}歳): {e}")
            self.stats['failed'] += 1

            return EpisodeResult(
                person_id=person_id,
                person_name=person_name,
                age=age,
                episode_text="",
                generation_time=time.time() - start_time,
                success=False,
                error_message=str(e)
            )

    def _build_prompt(self, person_data: Dict[str, Any], age: int) -> str:
        """プロンプト構築"""
        person_name = person_data.get('person_name_ja', '')
        birth_year = person_data.get('birth_year_int', 0)
        category = person_data.get('category', '')
        occupation = person_data.get('occupation', '')

        # カテゴリごとの重点ポイント
        focus_points = {
            'スポーツ': '記録、優勝、メダル、怪我からの復活',
            '音楽': 'ヒット曲、売上枚数、コンサート動員数、賞',
            '芸能': '出演作品、視聴率、興行収入、受賞',
            '政治': '当選、政策、法案、歴史的決定',
            '実業家': '起業、売上、革新的製品、事業拡大',
            'YouTuber': '登録者数、再生回数、企画、コラボ',
            '漫画・アニメ': '連載開始、巻数、発行部数、アニメ化'
        }

        focus = focus_points.get(category, '偉業、転機、革新')

        prompt = f"""あなたは日本の歴史と文化に精通した伝記作家です。

【人物情報】
名前: {person_name}
生年: {birth_year}年
カテゴリ: {category}
職業: {occupation}

【必須ルール】
1. 必ず「あなたと同じ{age}歳のとき、{person_name}は」で始める
2. その後、年齢は二度と書かない、人名は代名詞で
3. 具体的な数値データを必ず含める（{focus}）
4. 150-230文字で完結させる
5. 感動的または驚きのある内容にする

エピソード（1つだけ、改行なし）:"""

        return prompt

    def generate_batch(self, df: pd.DataFrame, limit: Optional[int] = None) -> List[EpisodeResult]:
        """バッチ生成

        Args:
            df: 人物データフレーム
            limit: 生成数制限

        Returns:
            生成結果リスト
        """
        results = []

        # 対象人物を選択（birth_yearがあり、認知度が高い順）
        target_df = df[df['birth_year_int'].notna()].sort_values(
            'recognition_score', ascending=False
        )

        if limit:
            target_df = target_df.head(limit)

        logger.info(f"📊 エピソード生成開始: {len(target_df)}人")

        # プログレスバー付きで生成
        for idx, person in tqdm(target_df.iterrows(), total=len(target_df), desc="生成中"):
            person_data = person.to_dict()

            # 年齢選択（20-60歳のランダム）
            birth_year = int(person_data['birth_year_int'])
            current_year = 2025
            max_age = min(current_year - birth_year, 60)

            if max_age > 20:
                import random
                age = random.randint(20, max_age)
            else:
                age = 20

            # エピソード生成
            result = self.generate_episode(person_data, age)
            results.append(result)

            # レート制限対策（1秒に5リクエストまで）
            time.sleep(0.2)

            # 定期的に進捗を保存
            if len(results) % 100 == 0:
                self._save_checkpoint(results)
                self._print_stats()

        return results

    def _save_checkpoint(self, results: List[EpisodeResult]):
        """チェックポイント保存"""
        checkpoint_file = f"episode_checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        data = [asdict(r) for r in results]
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"💾 チェックポイント保存: {checkpoint_file}")

    def _print_stats(self):
        """統計情報表示"""
        logger.info("="*60)
        logger.info("📊 生成統計")
        logger.info(f"  成功: {self.stats['successful']}件")
        logger.info(f"  失敗: {self.stats['failed']}件")
        logger.info(f"  推定コスト: ${self.stats['total_cost']:.4f}")
        logger.info(f"  平均生成時間: {self.stats['total_time']/max(self.stats['total_generated'], 1):.2f}秒")
        logger.info("="*60)

    def save_to_database(self, results: List[EpisodeResult], csv_file: str):
        """データベースに保存"""
        # 既存のCSVを読み込み
        df = pd.read_csv(csv_file, encoding='utf-8')

        # エピソードを追加
        for result in results:
            if result.success and result.episode_text:
                # person_idでマッチング
                mask = df['person_id'] == result.person_id
                if mask.any():
                    # エピソード列を追加（まだない場合）
                    episode_col = f'episode_{result.age}'
                    if episode_col not in df.columns:
                        df[episode_col] = ""

                    # エピソードを設定
                    df.loc[mask, episode_col] = result.episode_text

        # 保存
        output_file = csv_file.replace('.csv', f'_with_episodes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
        df.to_csv(output_file, index=False, encoding='utf-8-sig')  # BOM付きUTF-8

        logger.info(f"✅ データベース保存完了: {output_file}")
        return output_file


def main():
    """メイン処理"""
    logger.info("="*60)
    logger.info("🚀 Anthropic エピソード大量生成システム起動")
    logger.info("="*60)

    # APIキー確認
    if not os.getenv('ANTHROPIC_API_KEY'):
        logger.error("❌ ANTHROPIC_API_KEYが設定されていません")
        return

    # 最新のCSVファイル検索
    csv_files = list(Path('.').glob('ultra_think_*.csv'))
    if not csv_files:
        logger.error("❌ CSVファイルが見つかりません")
        return

    latest_csv = max(csv_files, key=lambda x: x.stat().st_mtime)
    logger.info(f"📂 使用CSVファイル: {latest_csv}")

    # データ読み込み
    df = pd.read_csv(str(latest_csv), encoding='utf-8')
    logger.info(f"📊 総人物数: {len(df)}件")

    # ジェネレーター初期化（緩和モード）
    generator = AnthropicEpisodeGenerator(relaxed_mode=True)

    # バッチサイズ設定（テストは10人、本番は100人から開始）
    batch_size = int(input("生成する人数を入力してください (推奨: 10-100): ") or "10")

    # エピソード生成
    logger.info(f"\n🎬 {batch_size}人分のエピソード生成を開始します")
    results = generator.generate_batch(df, limit=batch_size)

    # 統計表示
    generator._print_stats()

    # データベース保存
    if results:
        output_file = generator.save_to_database(results, str(latest_csv))

        # 成功率計算
        success_rate = sum(1 for r in results if r.success) / len(results) * 100

        logger.info("\n" + "="*60)
        logger.info("✨ 生成完了サマリー")
        logger.info(f"  生成人数: {len(results)}人")
        logger.info(f"  成功率: {success_rate:.1f}%")
        logger.info(f"  総コスト: ${generator.stats['total_cost']:.4f}")
        logger.info(f"  出力ファイル: {output_file}")
        logger.info("="*60)


if __name__ == "__main__":
    main()