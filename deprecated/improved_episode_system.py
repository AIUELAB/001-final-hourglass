#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改善版エピソード生成システム
事実誤認を防ぐための統合型システム
"""

import os
import json
import time
import logging
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import anthropic
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FactDatabase:
    """事実データベース（ハードコード済み正確情報）"""

    def __init__(self):
        """検証済み事実をハードコード"""
        self.verified_facts = {
            'Ado': {
                'birth_year': 2002,
                'debut_year': 2020,
                'debut_age': 18,
                'debut_song': 'うっせぇわ',
                'debut_song_writer': 'syudou',
                'first_album': '狂言',
                'first_album_year': 2022,
                'notable_facts': [
                    'うっせぇわは2020年にリリース',
                    'syudouが作詞作曲',
                    '2022年にNHK紅白歌合戦初出場',
                    'ワンピースFILM REDで歌唱担当'
                ],
                'avoid_mistakes': [
                    'ヨルシカとのコラボはない',
                    'アルバム名「Ado」は存在しない',
                    'デビューは18歳（21歳ではない）'
                ]
            },
            'HIKAKIN': {
                'birth_year': 1989,
                'youtube_start': 2007,
                'channel_created': 2006,
                'notable_facts': [
                    '日本のYouTuber第一人者',
                    'UUUM株式会社ファウンダー',
                    'ボイスパーカッションで有名',
                    'チャンネル登録者数1000万人超'
                ],
                'avoid_mistakes': [
                    'スキージャンプ選手ではない',
                    '紅白歌合戦で優勝したことはない'
                ]
            },
            'Fukase': {
                'birth_year': 1985,
                'band': 'SEKAI NO OWARI',
                'role': 'ボーカル',
                'notable_facts': [
                    'SEKAI NO OWARIのボーカル',
                    '2010年にメジャーデビュー',
                    'RPGなどのヒット曲',
                    'End of the Worldとして海外活動'
                ],
                'avoid_mistakes': [
                    'アイアムアヒーローという曲は存在しない',
                    'ソロ活動は限定的',
                    'インディーズシーンの革命という表現は誇張'
                ]
            },
            'さくらももこ': {
                'birth_year': 1965,
                'death_year': 2018,
                'masterpiece': 'ちびまる子ちゃん',
                'manga_start': 1986,
                'anime_start': 1990,
                'notable_facts': [
                    '「りぼん」で連載開始（1986年）',
                    'アニメ化は1990年',
                    '国民的作品として長期放送',
                    'エッセイストとしても活動'
                ],
                'avoid_mistakes': [
                    '累計発行部数の誇張に注意',
                    '21歳では連載開始していない（20歳）'
                ]
            }
        }

    def get_facts(self, person_name: str) -> Dict:
        """人物の検証済み事実を取得"""
        return self.verified_facts.get(person_name, {})


class SafePromptBuilder:
    """安全なプロンプト構築器"""

    def __init__(self):
        """初期化"""
        self.fact_db = FactDatabase()

    def build_safe_prompt(self, person_data: Dict, age: int) -> str:
        """事実に基づく安全なプロンプト構築"""

        person_name = person_data.get('person_name_ja', '')
        birth_year = person_data.get('birth_year_int', 0)
        category = person_data.get('category', '')

        # 検証済み事実を取得
        facts = self.fact_db.get_facts(person_name)

        if facts:
            # 事実がある場合は使用
            fact_context = self._format_facts(facts, age, birth_year)
            safety_rules = self._format_safety_rules(facts)
        else:
            # 事実がない場合は一般的なルール
            fact_context = "【注意】検証済みデータがないため、一般的で確実な内容のみ記述"
            safety_rules = "推測や創作は避け、広く知られた事実のみを使用"

        prompt = f"""あなたは事実の正確性を最重要視する伝記作家です。

【絶対厳守ルール】
1. 「あなたと同じ{age}歳のとき、{person_name}は」で始める
2. 誤った情報は絶対に書かない
3. 不確実なことは書かない
4. 創作・推測・誇張は厳禁
5. 150-230文字で簡潔に

【人物】
{person_name}（{birth_year}年生, {category}）

{fact_context}

{safety_rules}

【生成時の注意】
- 作品名、人名、数値は100%確実なもののみ
- 「おそらく」「と言われている」等の曖昧表現禁止
- コラボや共作は実在確認必須

正確なエピソード（改行なし）："""

        return prompt

    def _format_facts(self, facts: Dict, age: int, birth_year: int) -> str:
        """事実をフォーマット"""
        episode_year = birth_year + age

        relevant_facts = []
        for fact in facts.get('notable_facts', []):
            # 年代に関連する事実を選択
            if str(episode_year) in fact or str(age) in fact:
                relevant_facts.append(fact)

        if not relevant_facts:
            relevant_facts = facts.get('notable_facts', [])[:3]

        return f"""【検証済み事実】
- {chr(10).join(f'• {fact}' for fact in relevant_facts)}"""

    def _format_safety_rules(self, facts: Dict) -> str:
        """安全ルールをフォーマット"""
        mistakes = facts.get('avoid_mistakes', [])
        if mistakes:
            return f"""【絶対に避ける誤り】
{chr(10).join(f'❌ {mistake}' for mistake in mistakes)}"""
        return ""


class ImprovedEpisodeGenerator:
    """改善版エピソード生成器"""

    def __init__(self):
        """初期化"""
        self.client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.prompt_builder = SafePromptBuilder()
        self.fact_db = FactDatabase()

        # ファクトチェッカー（既存のものを利用）
        from fact_checker import FactChecker, HallucinationDetector
        self.fact_checker = FactChecker()
        self.hallucination_detector = HallucinationDetector()

    def generate_safe_episode(self, person_data: Dict, age: int) -> Dict:
        """安全なエピソード生成"""

        person_name = person_data.get('person_name_ja', '')
        birth_year = person_data.get('birth_year_int', 0)

        # 1. 安全なプロンプト構築
        prompt = self.prompt_builder.build_safe_prompt(person_data, age)

        # 2. 生成（低温度で事実重視）
        try:
            response = self.client.messages.create(
                model='claude-3-haiku-20240307',
                max_tokens=400,
                temperature=0.2,  # 創造性を最小限に
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            episode = response.content[0].text.strip()

            # 3. ファクトチェック
            check_result = self.fact_checker.check_episode(
                episode, person_name, age, birth_year
            )

            # 4. ハルシネーション検出
            has_hallucination, hallucination_reasons = self.hallucination_detector.detect(episode)

            # 5. 結果をまとめる
            return {
                'episode': episode,
                'is_safe': check_result.is_verified and not has_hallucination,
                'confidence': check_result.confidence_score,
                'warnings': check_result.warnings,
                'corrections': check_result.corrections,
                'hallucination_detected': has_hallucination,
                'hallucination_reasons': hallucination_reasons
            }

        except Exception as e:
            logger.error(f"生成エラー: {e}")
            return {
                'episode': '',
                'is_safe': False,
                'confidence': 0.0,
                'error': str(e)
            }

    def generate_batch_safe(self, persons: List[Dict]) -> List[Dict]:
        """バッチで安全に生成"""
        results = []

        for person in persons:
            person_name = person.get('person_name_ja', '')
            birth_year = int(person.get('birth_year_int', 0))

            # 適切な年齢を選択
            current_year = 2025
            max_age = min(current_year - birth_year, 60)
            age = min(25, max_age) if max_age > 20 else 20

            logger.info(f"🎯 生成中: {person_name} ({age}歳)")

            result = self.generate_safe_episode(person, age)
            result['person_id'] = person.get('person_id', '')
            result['person_name'] = person_name
            result['age'] = age

            results.append(result)

            # レート制限対策
            time.sleep(0.3)

        return results


def main():
    """メイン処理"""

    print("="*60)
    print("🛡️ 改善版エピソード生成システム")
    print("="*60)

    generator = ImprovedEpisodeGenerator()

    # テストデータ（問題があった人物）
    test_persons = [
        {
            'person_id': 'P000001',
            'person_name_ja': 'Ado',
            'birth_year_int': 2002,
            'category': 'エンタメ',
            'occupation': '歌手'
        },
        {
            'person_id': 'P000008',
            'person_name_ja': 'Fukase',
            'birth_year_int': 1985,
            'category': 'その他',
            'occupation': 'ミュージシャン'
        },
        {
            'person_id': 'P030136',
            'person_name_ja': 'さくらももこ',
            'birth_year_int': 1965,
            'category': '漫画・アニメ',
            'occupation': '漫画家'
        },
        {
            'person_id': 'P000002',
            'person_name_ja': 'HIKAKIN',
            'birth_year_int': 1989,
            'category': 'YouTuber',
            'occupation': 'YouTuber'
        }
    ]

    # バッチ生成
    results = generator.generate_batch_safe(test_persons)

    # 結果表示
    print("\n" + "="*60)
    print("📊 生成結果")
    print("="*60)

    safe_count = 0
    for result in results:
        print(f"\n👤 {result['person_name']} ({result['age']}歳)")
        print("-"*40)
        print(f"📝 エピソード:")
        print(result['episode'])
        print(f"\n✅ 安全性: {'OK' if result['is_safe'] else '要確認'}")
        print(f"📊 信頼度: {result.get('confidence', 0):.2f}")

        if result.get('warnings'):
            print(f"⚠️ 警告: {len(result['warnings'])}件")
            for warning in result['warnings'][:2]:
                print(f"  - {warning}")

        if result.get('hallucination_detected'):
            print(f"🧠 ハルシネーション検出:")
            for reason in result['hallucination_reasons']:
                print(f"  - {reason}")

        if result['is_safe']:
            safe_count += 1

    # サマリー
    print("\n" + "="*60)
    print("📈 サマリー")
    print("="*60)
    print(f"生成数: {len(results)}")
    print(f"安全: {safe_count}/{len(results)} ({safe_count/len(results)*100:.1f}%)")
    print(f"要確認: {len(results) - safe_count}")

    # CSVに保存
    output_file = f"safe_episodes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df = pd.DataFrame([{
        'person_id': r['person_id'],
        'person_name': r['person_name'],
        'age': r['age'],
        'episode': r['episode'],
        'is_safe': r['is_safe'],
        'confidence': r.get('confidence', 0)
    } for r in results])

    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n💾 保存完了: {output_file}")


if __name__ == "__main__":
    main()
