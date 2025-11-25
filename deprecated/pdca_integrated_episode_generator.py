#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDCA統合型エピソード生成システム
事実正確性チェックを組み込んだ安全な生成システム
"""

import os
import sys
import time
import logging
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import anthropic
from dotenv import load_dotenv

# PDCAガーディアンをインポート
from pdca_guardian import PDCAGuardian

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SafeEpisodeResult:
    """安全なエピソード生成結果"""
    person_id: str
    person_name: str
    age: int
    episode_text: str
    is_safe: bool
    confidence_score: float
    pdca_violations: List[Dict]
    generation_time: float
    retry_count: int = 0


class PDCAIntegratedGenerator:
    """PDCA統合エピソード生成器"""

    def __init__(self):
        """初期化"""
        self.client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.pdca_guardian = PDCAGuardian(relaxed_mode=False)  # 厳格モード

        # 統計
        self.stats = {
            'total_generated': 0,
            'safe_episodes': 0,
            'rejected_episodes': 0,
            'retry_success': 0
        }

    def generate_with_pdca_check(self, person_data: Dict, age: int,
                                 max_retries: int = 3) -> SafeEpisodeResult:
        """PDCAチェック付きエピソード生成"""

        person_name = person_data.get('person_name_ja', '')
        person_id = person_data.get('person_id', '')
        birth_year = person_data.get('birth_year_int', 0)

        retry_count = 0
        best_episode = None
        best_score = 0

        while retry_count < max_retries:
            start_time = time.time()

            # 1. プロンプト構築（事実重視版）
            prompt = self._build_factual_prompt(person_data, age, retry_count)

            # 2. エピソード生成
            try:
                response = self.client.messages.create(
                    model='claude-3-haiku-20240307',
                    max_tokens=400,
                    temperature=0.1 + (retry_count * 0.05),  # リトライごとに少し温度上げる
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )

                episode_text = response.content[0].text.strip()

                # 3. PDCAガーディアンでチェック
                violations = []

                # 品質チェック
                quality_violations = self.pdca_guardian.check_episode_quality(
                    episode_text,
                    age,
                    person_name,
                    person_data
                )
                violations.extend(quality_violations)

                # 事実正確性チェック（新機能）
                factual_violations = self.pdca_guardian.check_factual_accuracy(
                    episode_text,
                    person_data
                )
                violations.extend(factual_violations)

                # 重大な違反があるか確認
                critical_violations = [v for v in violations if v.get('severity') == 'critical']

                generation_time = time.time() - start_time

                # 信頼度スコア計算
                confidence = self._calculate_confidence(violations)

                # このエピソードが最良か記録
                if confidence > best_score:
                    best_episode = episode_text
                    best_score = confidence

                # 重大な違反がなければ採用
                if not critical_violations:
                    self.stats['safe_episodes'] += 1

                    return SafeEpisodeResult(
                        person_id=person_id,
                        person_name=person_name,
                        age=age,
                        episode_text=episode_text,
                        is_safe=True,
                        confidence_score=confidence,
                        pdca_violations=violations,
                        generation_time=generation_time,
                        retry_count=retry_count
                    )

                # 重大な違反があればリトライ
                logger.warning(f"❌ 重大な違反検出 ({person_name}): {len(critical_violations)}件")
                for v in critical_violations[:2]:
                    logger.warning(f"  - {v['message']}")

                retry_count += 1

            except Exception as e:
                logger.error(f"生成エラー: {e}")
                retry_count += 1
                time.sleep(0.5)

        # リトライ上限に達した場合は最良のものを返す
        self.stats['rejected_episodes'] += 1

        return SafeEpisodeResult(
            person_id=person_id,
            person_name=person_name,
            age=age,
            episode_text=best_episode or "",
            is_safe=False,
            confidence_score=best_score,
            pdca_violations=violations if 'violations' in locals() else [],
            generation_time=0,
            retry_count=retry_count
        )

    def _build_factual_prompt(self, person_data: Dict, age: int, retry: int) -> str:
        """事実重視のプロンプト構築"""

        person_name = person_data.get('person_name_ja', '')
        birth_year = person_data.get('birth_year_int', 0)
        category = person_data.get('category', '')

        # リトライ時は追加の制約を加える
        retry_constraint = ""
        if retry > 0:
            retry_constraint = """
【追加制約】
- 前回の生成で誤りがあった可能性があります
- より慎重に、確実な事実のみを使用してください
- 作品名や人名の関係は特に注意深く確認
"""

        # 既知の正確な情報を提供
        known_facts = self._get_known_facts(person_name)

        prompt = f"""あなたは事実の正確性を最重要視する伝記作家です。

【人物】
{person_name}（{birth_year}年生, {category}）

{known_facts}

【絶対厳守ルール】
1. 「あなたと同じ{age}歳のとき、{person_name}は」で始める
2. 誤った情報は絶対に書かない（特に作品名、コラボ、受賞歴）
3. 不確実なことは書かない
4. 150-230文字で簡潔に
5. 年代は正確に（{age}歳は{birth_year + age}年）

{retry_constraint}

正確なエピソード（改行なし）："""

        return prompt

    def _get_known_facts(self, person_name: str) -> str:
        """既知の正確な事実を取得"""

        facts_db = {
            'Ado': """【確認済み事実】
- デビュー: 2020年（18歳）「うっせぇわ」
- 作詞作曲: syudou
- 1stアルバム: 「狂言」（2022年）
- 注意: ヨルシカとのコラボはない""",

            'HIKAKIN': """【確認済み事実】
- YouTuber第一人者
- UUUM株式会社ファウンダー
- ボイスパーカッション
- 注意: 紅白歌合戦出場はない""",

            'Fukase': """【確認済み事実】
- SEKAI NO OWARIのボーカル
- メジャーデビュー: 2010年
- 代表曲: RPG、炎と森のカーニバル
- 注意: 「アイアムアヒーロー」という曲はない"""
        }

        return facts_db.get(person_name, "【注意】検証済み情報がないため、一般的な事実のみ使用")

    def _calculate_confidence(self, violations: List[Dict]) -> float:
        """信頼度スコア計算"""

        score = 1.0

        for v in violations:
            severity = v.get('severity', 'low')
            v_type = v.get('type', '')

            # 事実誤認系の違反は大きく減点
            if '事実誤認' in v_type or 'ハルシネーション' in v_type:
                if severity == 'critical':
                    score -= 0.5
                elif severity == 'high':
                    score -= 0.3
                else:
                    score -= 0.1
            # その他の違反
            else:
                if severity == 'critical':
                    score -= 0.2
                elif severity == 'high':
                    score -= 0.1
                else:
                    score -= 0.05

        return max(0.0, min(1.0, score))


def main():
    """メイン処理"""

    print("="*60)
    print("🛡️ PDCA統合型エピソード生成システム")
    print("="*60)

    generator = PDCAIntegratedGenerator()

    # テストデータ
    test_persons = [
        {
            'person_id': 'P000001',
            'person_name_ja': 'Ado',
            'birth_year_int': 2002,
            'category': 'エンタメ',
            'occupation': '歌手'
        },
        {
            'person_id': 'P000002',
            'person_name_ja': 'HIKAKIN',
            'birth_year_int': 1989,
            'category': 'YouTuber'
        },
        {
            'person_id': 'P000008',
            'person_name_ja': 'Fukase',
            'birth_year_int': 1985,
            'category': '音楽'
        }
    ]

    results = []

    for person in test_persons:
        person_name = person['person_name_ja']
        birth_year = person['birth_year_int']

        # 適切な年齢を選択
        current_year = 2025
        max_age = min(current_year - birth_year, 60)
        age = min(25, max_age) if max_age > 20 else 20

        print(f"\n🎯 生成中: {person_name} ({age}歳)")
        print("-"*40)

        # PDCA統合生成
        result = generator.generate_with_pdca_check(person, age)
        results.append(result)

        # 結果表示
        print(f"📝 エピソード:")
        print(result.episode_text)
        print(f"\n✅ 安全性: {'OK' if result.is_safe else '要改善'}")
        print(f"📊 信頼度: {result.confidence_score:.2f}")
        print(f"🔄 リトライ: {result.retry_count}回")

        if result.pdca_violations:
            critical = [v for v in result.pdca_violations if v.get('severity') == 'critical']
            if critical:
                print(f"⚠️ 重大な違反: {len(critical)}件")

        # レート制限対策
        time.sleep(0.5)

    # 統計表示
    print("\n" + "="*60)
    print("📈 生成統計")
    print("="*60)
    print(f"安全なエピソード: {generator.stats['safe_episodes']}/{len(test_persons)}")
    print(f"却下されたエピソード: {generator.stats['rejected_episodes']}")
    print(f"平均信頼度: {sum(r.confidence_score for r in results)/len(results):.2f}")


if __name__ == "__main__":
    main()
