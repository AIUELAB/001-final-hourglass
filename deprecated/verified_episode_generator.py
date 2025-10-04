#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
検証済みエピソード生成システム
事実確認を統合した高精度エピソード生成
"""

import os
import time
import logging
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import anthropic
import wikipediaapi
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class VerifiedData:
    """検証済みデータ"""
    person_name: str
    birth_year: int
    death_year: Optional[int]
    occupation: str
    category: str
    wikipedia_url: Optional[str]
    verified_facts: Dict[str, Any]
    notable_achievements: List[str]


class WikipediaVerifier:
    """Wikipedia情報検証器"""

    def __init__(self):
        """初期化"""
        self.wiki = wikipediaapi.Wikipedia(
            user_agent='EpisodeVerifier/2.0 (https://example.com/contact)',
            language='ja'
        )

    def verify_person(self, person_name: str) -> Optional[VerifiedData]:
        """人物情報をWikipediaで検証"""
        try:
            page = self.wiki.page(person_name)
            if not page.exists():
                logger.warning(f"Wikipedia記事なし: {person_name}")
                return None

            # 基本情報を抽出
            summary = page.summary[:1000]  # 要約の最初の1000文字

            # 生年を抽出（簡易的）
            import re
            birth_year_match = re.search(r'(\d{4})年.*生', summary)
            birth_year = int(birth_year_match.group(1)) if birth_year_match else None

            # 死亡年を抽出
            death_year_match = re.search(r'(\d{4})年.*没', summary)
            death_year = int(death_year_match.group(1)) if death_year_match else None

            # 実績を抽出（賞、記録など）
            achievements = []

            # 賞の検出
            award_patterns = [
                r'賞を受賞',
                r'グラミー賞',
                r'アカデミー賞',
                r'ノーベル賞',
                r'金メダル',
                r'世界記録',
                r'日本記録'
            ]

            for pattern in award_patterns:
                if re.search(pattern, page.text[:5000]):
                    achievements.append(pattern.replace('を受賞', ''))

            return VerifiedData(
                person_name=person_name,
                birth_year=birth_year,
                death_year=death_year,
                occupation='',  # 後で設定
                category='',    # 後で設定
                wikipedia_url=page.fullurl,
                verified_facts={
                    'summary': summary,
                    'page_length': len(page.text)
                },
                notable_achievements=achievements
            )

        except Exception as e:
            logger.error(f"Wikipedia検証エラー ({person_name}): {e}")
            return None


class FactBasedPromptBuilder:
    """事実に基づくプロンプト構築器"""

    def build_prompt(self, person_data: Dict, verified_data: Optional[VerifiedData],
                    age: int) -> str:
        """検証済みデータを使用してプロンプトを構築"""

        person_name = person_data.get('person_name_ja', '')
        birth_year = person_data.get('birth_year_int', 0)
        category = person_data.get('category', '')
        occupation = person_data.get('occupation', '')

        # 検証済みデータがある場合は使用
        if verified_data:
            facts_context = f"""
【検証済み事実】
- Wikipedia URL: {verified_data.wikipedia_url}
- 要約: {verified_data.verified_facts.get('summary', '')[:500]}
- 実績: {', '.join(verified_data.notable_achievements[:3]) if verified_data.notable_achievements else 'なし'}
"""
        else:
            facts_context = """
【注意】Wikipedia情報が見つからないため、一般的な事実のみを使用してください。
創作や推測は避け、確実な情報のみを含めてください。
"""

        prompt = f"""あなたは正確性を重視する伝記作家です。
事実に基づいたエピソードのみを作成してください。

【厳守ルール】
1. 必ず「あなたと同じ{age}歳のとき、{person_name}は」で始める
2. 検証可能な事実のみを使用（創作・推測禁止）
3. 具体的な作品名や数値は、確実に正しいもののみ使用
4. 不確実な情報は含めない
5. 150-230文字で完結

【人物情報】
名前: {person_name}
生年: {birth_year}年
カテゴリ: {category}
職業: {occupation}

{facts_context}

【エピソード生成時の注意】
- 「うっせぇわ」の作者はsyudou（Adoは歌唱者）
- 「紅蓮華」の歌手はLiSA（鬼滅の刃主題歌）
- アルバム名、楽曲名、受賞歴は必ず事実確認

エピソード（事実のみ、改行なし）："""

        return prompt


class VerifiedEpisodeGenerator:
    """検証済みエピソード生成器"""

    def __init__(self):
        """初期化"""
        self.client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.verifier = WikipediaVerifier()
        self.prompt_builder = FactBasedPromptBuilder()

        # 二段階生成の設定
        self.two_stage_generation = True

    def generate_episode(self, person_data: Dict, age: int) -> Tuple[str, float]:
        """検証済みエピソード生成"""

        person_name = person_data.get('person_name_ja', '')

        # 1. Wikipedia検証
        logger.info(f"📚 Wikipedia検証中: {person_name}")
        verified_data = self.verifier.verify_person(person_name)

        # 2. プロンプト構築
        prompt = self.prompt_builder.build_prompt(person_data, verified_data, age)

        # 3. 初回生成
        try:
            response = self.client.messages.create(
                model='claude-3-haiku-20240307',
                max_tokens=400,
                temperature=0.3,  # 創造性を抑えて事実重視
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            episode_draft = response.content[0].text.strip()

            # 4. 二段階生成（事実確認）
            if self.two_stage_generation:
                episode_draft = self._verify_and_revise(episode_draft, person_name, age)

            # 信頼度スコア計算
            confidence = 0.9 if verified_data else 0.5

            return episode_draft, confidence

        except Exception as e:
            logger.error(f"生成エラー: {e}")
            return "", 0.0

    def _verify_and_revise(self, episode: str, person_name: str, age: int) -> str:
        """エピソードを検証して修正"""

        verification_prompt = f"""以下のエピソードの事実を確認し、誤りがあれば修正してください。

【エピソード】
{episode}

【確認ポイント】
1. 人名と作品の関係は正しいか
2. 年代や数値は正確か
3. 実際に起きた出来事か

【修正版エピソード】（誤りがない場合は同じものを、ある場合は修正版を出力）："""

        try:
            response = self.client.messages.create(
                model='claude-3-haiku-20240307',
                max_tokens=400,
                temperature=0.1,  # 修正時は創造性を最小に
                messages=[
                    {"role": "user", "content": verification_prompt}
                ]
            )

            return response.content[0].text.strip()

        except Exception as e:
            logger.error(f"検証エラー: {e}")
            return episode


def test_verified_generation():
    """検証済み生成のテスト"""

    generator = VerifiedEpisodeGenerator()

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
            'category': 'YouTuber',
            'occupation': 'YouTuber'
        }
    ]

    print("="*60)
    print("🎯 検証済みエピソード生成テスト")
    print("="*60)

    for person in test_persons:
        print(f"\n👤 {person['person_name_ja']}")
        print("-"*40)

        # エピソード生成
        age = 21
        episode, confidence = generator.generate_episode(person, age)

        print(f"📝 エピソード:")
        print(episode)
        print(f"\n📊 信頼度: {confidence:.2f}")
        print("-"*40)


if __name__ == "__main__":
    test_verified_generation()