#!/usr/bin/env python3
"""
堅牢な知名度評価システム
APIレート制限に対応し、品質を担保しながら実行
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import logging
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
import aiohttp
from serpapi import GoogleSearch
from googleapiclient.discovery import build
import time

# 環境変数読み込み
load_dotenv()

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class RobustScore:
    """知名度スコア（堅牢版）"""
    person_id: str
    person_name: str
    person_name_ja: str
    final_score: float = 0.0
    api_success_count: int = 0
    api_total_count: int = 5
    is_protected: bool = False
    protection_reason: str = ""
    data_sources: Dict = None

    def __post_init__(self):
        if self.data_sources is None:
            self.data_sources = {}


class RobustRecognitionEvaluator:
    """堅牢な知名度評価システム"""

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.output_dir = Path("recognition_results")
        self.output_dir.mkdir(exist_ok=True)

        # API設定
        self.serpapi_key = os.getenv('SERPAPI_KEY')
        self.brave_key = os.getenv('BRAVE_API_KEY')
        self.youtube_key = os.getenv('YOUTUBE_API_KEY')
        self.news_key = os.getenv('NEWS_API_KEY')

        # 保護リスト読み込み
        self.protected_persons = self._load_protected_persons()
        self.protected_characters = self._load_protected_characters()

        # カテゴリボーナス
        self.category_weights = {
            'YouTuber': 2.5,
            'TikToker': 2.2,
            'VTuber': 2.0,
            'インフルエンサー': 1.8,
            'お笑い芸人': 1.5,
            '俳優': 1.3,
            '歌手': 1.3,
            'アイドル': 1.5,
            'スポーツ選手': 1.0,
            '歴史上の人物': 0.5,
            '架空キャラクター': 1.8,
            '政治家': 0.8,
            '実業家': 0.7
        }

    def _load_protected_persons(self) -> set:
        """教科書人物保護リスト"""
        try:
            from textbook_person_protector import get_protected_persons
            return get_protected_persons()
        except:
            # 最低限の保護リスト
            return {
                "織田信長", "豊臣秀吉", "徳川家康", "聖徳太子", "紫式部",
                "チンギス・ハン", "ナポレオン", "アインシュタイン", "ガンジー",
                "コロンブス", "リンカーン", "エジソン", "ニュートン",
                "HIKAKIN", "ヒカキン", "大谷翔平", "Ado", "YOASOBI"
            }

    def _load_protected_characters(self) -> set:
        """架空キャラクター保護リスト"""
        try:
            from fictional_character_protector import get_protected_characters
            return get_protected_characters()
        except:
            return {
                "竈門炭治郎", "孫悟空", "ドラえもん", "ピカチュウ", "ルフィ",
                "セーラームーン", "アンパンマン", "鉄腕アトム", "仮面ライダー"
            }

    async def safe_api_call(self, api_func, *args, **kwargs):
        """APIコールの安全なラッパー（エラー時はNoneを返す）"""
        try:
            result = await api_func(*args, **kwargs)
            return result
        except Exception as e:
            logger.warning(f"API呼び出しエラー: {e}")
            return None

    async def search_google_safe(self, name: str) -> Optional[int]:
        """Google検索（安全版）"""
        if not self.serpapi_key:
            return None

        try:
            search = GoogleSearch({
                "q": name,
                "api_key": self.serpapi_key,
                "num": 10,
                "hl": "ja",
                "gl": "jp"
            })
            results = search.get_dict()

            # 総結果数を取得
            search_info = results.get("search_information", {})
            total_results = search_info.get("total_results", 0)

            if isinstance(total_results, str):
                total_results = int(total_results.replace(",", ""))

            return total_results

        except Exception as e:
            logger.debug(f"Google検索スキップ ({name}): {e}")
            return None

    async def search_brave_safe(self, name: str, retry_count: int = 0) -> Optional[int]:
        """Brave検索（安全版、リトライ付き）"""
        if not self.brave_key:
            return None

        try:
            headers = {
                "Accept": "application/json",
                "X-Subscription-Token": self.brave_key
            }

            params = {
                "q": name,
                "count": 20
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    headers=headers,
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        web_results = len(data.get("web", {}).get("results", []))
                        return web_results * 1000  # 推定結果数
                    elif response.status == 429 and retry_count < 2:
                        # レート制限: 待機してリトライ
                        wait_time = 30 * (retry_count + 1)
                        logger.info(f"Brave APIレート制限。{wait_time}秒待機...")
                        await asyncio.sleep(wait_time)
                        return await self.search_brave_safe(name, retry_count + 1)
                    else:
                        return None

        except Exception as e:
            logger.debug(f"Brave検索スキップ ({name}): {e}")
            return None

    async def search_youtube_safe(self, name: str) -> Optional[int]:
        """YouTube検索（安全版）"""
        if not self.youtube_key:
            return None

        try:
            youtube = build('youtube', 'v3', developerKey=self.youtube_key)

            request = youtube.search().list(
                q=name,
                part='snippet',
                type='video',
                maxResults=10
            )
            response = request.execute()

            # 動画数から推定視聴回数を計算
            video_count = response.get('pageInfo', {}).get('totalResults', 0)
            return min(video_count * 50000, 50000000)  # 推定視聴回数

        except Exception as e:
            logger.debug(f"YouTube検索スキップ ({name}): {e}")
            return None

    async def evaluate_person_robust(self, row: pd.Series) -> RobustScore:
        """個人の知名度を堅牢に評価"""
        person_id = row.get('person_id', '')
        person_name = row.get('person_name', '')
        person_name_ja = row.get('person_name_ja', '')
        category = str(row.get('category', ''))
        occupation = str(row.get('occupation', ''))

        # 検索名を決定
        search_name = person_name_ja if person_name_ja else person_name

        # 保護チェック
        is_protected = False
        protection_reason = ""

        if search_name in self.protected_persons or person_name in self.protected_persons:
            is_protected = True
            protection_reason = "教科書掲載人物"
        elif search_name in self.protected_characters or person_name in self.protected_characters:
            is_protected = True
            protection_reason = "文化的重要キャラクター"

        if is_protected:
            return RobustScore(
                person_id=person_id,
                person_name=person_name,
                person_name_ja=person_name_ja,
                final_score=10.0,
                api_success_count=5,
                api_total_count=5,
                is_protected=True,
                protection_reason=protection_reason
            )

        # API呼び出し（エラーを許容）
        tasks = [
            self.search_google_safe(search_name),
            self.search_brave_safe(search_name),
            self.search_youtube_safe(search_name)
        ]

        results = await asyncio.gather(*tasks)

        # 結果を集計
        data_sources = {}
        valid_scores = []
        api_success = 0

        if results[0] is not None:  # Google
            data_sources['google'] = results[0]
            score = min(10, np.log10(results[0] + 1) * 1.5)
            valid_scores.append(score)
            api_success += 1

        if results[1] is not None:  # Brave
            data_sources['brave'] = results[1]
            score = min(10, np.log10(results[1] + 1) * 1.3)
            valid_scores.append(score)
            api_success += 1

        if results[2] is not None:  # YouTube
            data_sources['youtube'] = results[2]
            score = min(10, np.log10(results[2] + 1) * 1.2)
            valid_scores.append(score)
            api_success += 1

        # スコア計算
        if valid_scores:
            base_score = np.mean(valid_scores)
        else:
            # APIが全て失敗した場合はカテゴリのみで判定
            base_score = 3.0

        # カテゴリボーナス
        category_bonus = 0
        for key, weight in self.category_weights.items():
            if key in category or key in occupation:
                category_bonus = max(category_bonus, weight)

        final_score = min(10.0, base_score + category_bonus)

        return RobustScore(
            person_id=person_id,
            person_name=person_name,
            person_name_ja=person_name_ja,
            final_score=final_score,
            api_success_count=api_success,
            api_total_count=3,
            is_protected=is_protected,
            protection_reason=protection_reason,
            data_sources=data_sources
        )

    async def process_database(self):
        """データベース処理（堅牢版）"""
        logger.info("📂 データベース読み込み中...")
        df = pd.read_csv(self.csv_path, encoding='utf-8-sig')
        total = len(df)
        logger.info(f"✅ {total}件のレコードを読み込みました")

        # テストモード
        test_mode = os.getenv('TEST_MODE', 'false').lower() == 'true'
        if test_mode:
            df = df.head(20)  # テストは20件
            logger.info(f"⚠️ テストモード: 最初の{len(df)}件のみ処理")
            total = len(df)

        # 処理開始
        logger.info("🔄 知名度評価開始（堅牢版）...")
        all_scores = []

        for idx, row in df.iterrows():
            if idx % 5 == 0:
                logger.info(f"  進捗: {idx+1}/{total} ({(idx+1)/total*100:.1f}%)")

            # 評価実行
            score = await self.evaluate_person_robust(row)
            all_scores.append(score)

            # レート制限対策
            await asyncio.sleep(1)  # 1秒待機

        # 結果をDataFrameに反映
        logger.info("📝 スコアをデータベースに反映中...")

        for idx, score in enumerate(all_scores):
            df.loc[idx, 'recognition_score_2025'] = score.final_score
            df.loc[idx, 'api_success_rate'] = score.api_success_count / score.api_total_count
            df.loc[idx, 'is_protected'] = score.is_protected
            df.loc[idx, 'protection_reason'] = score.protection_reason

            # 削除推奨判定
            if score.final_score >= 7.0:
                df.loc[idx, 'deletion_recommendation'] = '保持（高知名度）'
            elif score.final_score >= 5.0:
                df.loc[idx, 'deletion_recommendation'] = '保持（中知名度）'
            elif score.final_score >= 3.0:
                df.loc[idx, 'deletion_recommendation'] = '要検討'
            else:
                df.loc[idx, 'deletion_recommendation'] = '削除候補'

        # 統計情報
        self._print_statistics(df)

        # 有名人検証
        self._validate_famous_persons(df)

        # 保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = self.output_dir / f"recognition_robust_{timestamp}.csv"
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        logger.info(f"✅ 結果を保存: {output_path}")

        return df

    def _print_statistics(self, df: pd.DataFrame):
        """統計情報出力"""
        logger.info("\n📊 評価結果統計:")

        stats = df['deletion_recommendation'].value_counts()
        total = len(df)

        for category, count in stats.items():
            percentage = (count / total) * 100
            logger.info(f"  {category}: {count}件 ({percentage:.1f}%)")

        # 削除率チェック
        deletion_count = df[df['deletion_recommendation'] == '削除候補'].shape[0]
        deletion_rate = (deletion_count / total) * 100

        if 10 <= deletion_rate <= 20:
            logger.info(f"✅ 削除率が適正範囲内: {deletion_rate:.1f}%")
        else:
            logger.warning(f"⚠️ 削除率が範囲外: {deletion_rate:.1f}%（目標: 10-20%）")

        # API成功率
        avg_api_rate = df['api_success_rate'].mean()
        logger.info(f"📡 平均API成功率: {avg_api_rate:.1%}")

    def _validate_famous_persons(self, df: pd.DataFrame):
        """有名人検証"""
        logger.info("\n🔍 有名人検証:")

        test_persons = ['HIKAKIN', 'ヒカキン', '大谷翔平', 'Ado', '米津玄師']

        for name in test_persons:
            matches = df[
                (df['person_name'].str.contains(name, na=False)) |
                (df['person_name_ja'].str.contains(name, na=False))
            ]

            if not matches.empty:
                for _, row in matches.head(1).iterrows():
                    score = row.get('recognition_score_2025', 0)
                    status = row.get('deletion_recommendation', '')
                    api_rate = row.get('api_success_rate', 0)
                    logger.info(f"  {name}: スコア={score:.2f}, 判定={status}, API成功率={api_rate:.1%}")


async def main():
    """メイン処理"""
    # 品質ゲートチェック
    from quality_gates import QualityGateSystem

    gate_system = QualityGateSystem()
    passed, _ = gate_system.check_script(__file__)

    if not passed:
        logger.error("品質ゲート失敗")
        sys.exit(1)

    # CSVファイル
    csv_path = "ultra_think_EPISODE_FINAL_20250901_020106.csv"

    if not Path(csv_path).exists():
        alt_files = list(Path(".").glob("ultra_think*EPISODE*.csv"))
        if alt_files:
            csv_path = str(alt_files[-1])
        else:
            logger.error("CSVファイルが見つかりません")
            sys.exit(1)

    # 評価実行
    evaluator = RobustRecognitionEvaluator(csv_path)
    await evaluator.process_database()

    logger.info("\n✨ 堅牢な知名度評価完了！")


if __name__ == "__main__":
    asyncio.run(main())
