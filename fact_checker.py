#!/usr/bin/env python3
"""
ファクトチェックモジュール (RCA-Kaizen #025)
エピソードの事実関係を検証し、品質を保証する

目的:
- LLMの知識ベースを活用してエピソードの事実確認
- 事実誤認を早期検出して品質を保証
- 確認済みエピソードのみをデータベースに保存

使用方法:
    checker = EpisodeFactChecker(anthropic_api_key=api_key)
    result = checker.check_episode(person_name, age, episode_text, category)

    if result.status == "確認済み":
        # エピソードを保存
    elif result.status == "事実誤認":
        # 修正案を適用して再生成
"""

import json
import logging
import anthropic
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class FactCheckResult:
    """ファクトチェック結果"""
    status: str  # "確認済み", "要確認", "事実誤認"
    confidence: float  # 0.0-1.0
    verification_sources: List[str]
    notes: str
    corrections: Optional[str] = None

    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return asdict(self)


class EpisodeFactChecker:
    """
    エピソードファクトチェッカー

    LLMの知識ベースを活用してエピソードの事実関係を検証
    """

    def __init__(self, anthropic_api_key: str):
        """
        初期化

        Args:
            anthropic_api_key: Anthropic APIキー
        """
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.model = "claude-3-5-sonnet-20241022"

        # 統計情報
        self.stats = {
            'total_checks': 0,
            'verified': 0,
            'needs_review': 0,
            'errors': 0
        }

    def check_episode(
        self,
        person_name: str,
        age: int,
        episode_text: str,
        category: str
    ) -> FactCheckResult:
        """
        エピソードをファクトチェック

        Args:
            person_name: 人物名
            age: 年齢
            episode_text: エピソード本文
            category: カテゴリ

        Returns:
            FactCheckResult: 検証結果
        """
        self.stats['total_checks'] += 1

        logger.info(f"  🔍 ファクトチェック開始: {person_name} ({age}歳)")

        try:
            # LLMに事実確認を依頼
            verification_prompt = f"""
あなたは歴史・人物情報の専門家です。以下のエピソードが事実として正確かどうかを検証してください。

【人物情報】
- 名前: {person_name}
- 年齢: {age}歳
- カテゴリ: {category}

【エピソード】
{episode_text}

【検証タスク】
1. この人物が{age}歳の時期に、記述された出来事が実際に起きたか
2. 業績や事実関係に誤りがないか
3. 時代背景や状況設定に矛盾がないか
4. 年齢と出来事の時系列が正確か

【回答形式】
必ず以下の形式で回答してください：

【判定】
(確認済み/要確認/事実誤認のいずれか1つを記載)

【信頼度】
(0.0から1.0の数値。1.0が最も確実)

【検証根拠】
- (箇条書きで具体的な理由や情報源を記載)

【注意事項】
(追加で確認すべき点や疑問点があれば記載)

【修正案】
(事実誤認の場合のみ、正しいエピソードの案を記載)
"""

            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": verification_prompt}]
            )

            result_text = response.content[0].text

            # 結果をパース
            status = self._extract_status(result_text)
            confidence = self._extract_confidence(result_text)
            sources = self._extract_sources(result_text)
            notes = self._extract_notes(result_text)
            corrections = self._extract_corrections(result_text)

            # 統計更新
            if status == "確認済み":
                self.stats['verified'] += 1
                logger.info(f"  ✅ 確認済み (信頼度: {confidence:.2f})")
            elif status == "要確認":
                self.stats['needs_review'] += 1
                logger.warning(f"  ⚠️  要確認 (信頼度: {confidence:.2f})")
            else:  # 事実誤認
                self.stats['errors'] += 1
                logger.error(f"  ❌ 事実誤認 (信頼度: {confidence:.2f})")

            return FactCheckResult(
                status=status,
                confidence=confidence,
                verification_sources=sources,
                notes=notes,
                corrections=corrections
            )

        except Exception as e:
            logger.error(f"  ❌ ファクトチェックエラー: {e}")

            # エラー時はデフォルトで要確認
            return FactCheckResult(
                status="要確認",
                confidence=0.0,
                verification_sources=["LLM知識ベース"],
                notes=f"検証エラー: {str(e)}",
                corrections=None
            )

    def _extract_status(self, text: str) -> str:
        """判定ステータスを抽出"""
        text_lower = text.lower()

        if "確認済み" in text or "confirmed" in text_lower:
            return "確認済み"
        elif "事実誤認" in text or "factual error" in text_lower or "incorrect" in text_lower:
            return "事実誤認"
        else:
            return "要確認"

    def _extract_confidence(self, text: str) -> float:
        """信頼度スコアを抽出"""
        import re

        # 【信頼度】セクションから数値を探す
        confidence_section = re.search(r'【信頼度】[^\d]*([\d.]+)', text)

        if confidence_section:
            try:
                score = float(confidence_section.group(1))
                return max(0.0, min(1.0, score))
            except ValueError:
                pass

        # デフォルト: ステータスに応じた信頼度
        status = self._extract_status(text)
        if status == "確認済み":
            return 0.8
        elif status == "事実誤認":
            return 0.7
        else:
            return 0.5

    def _extract_sources(self, text: str) -> List[str]:
        """検証根拠を抽出"""
        sources = []

        # 【検証根拠】セクションを探す
        import re
        sources_section = re.search(r'【検証根拠】(.*?)(?=【|$)', text, re.DOTALL)

        if sources_section:
            content = sources_section.group(1)
            # 箇条書きを抽出
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('- '):
                    sources.append(line[2:].strip())

        if not sources:
            sources = ["LLM知識ベース"]

        return sources

    def _extract_notes(self, text: str) -> str:
        """注意事項を抽出"""
        import re

        # 【注意事項】セクションを探す
        notes_section = re.search(r'【注意事項】(.*?)(?=【|$)', text, re.DOTALL)

        if notes_section:
            return notes_section.group(1).strip()

        return "特になし"

    def _extract_corrections(self, text: str) -> Optional[str]:
        """修正案を抽出"""
        import re

        # 【修正案】セクションを探す
        corrections_section = re.search(r'【修正案】(.*?)(?=【|$)', text, re.DOTALL)

        if corrections_section:
            content = corrections_section.group(1).strip()
            if content and content != "なし" and content != "特になし":
                return content

        return None

    def batch_check_episodes(
        self,
        episodes: List[Dict]
    ) -> List[Dict]:
        """
        複数エピソードを一括でファクトチェック

        Args:
            episodes: エピソードのリスト

        Returns:
            List[Dict]: fact_check_resultフィールドが追加されたエピソードリスト
        """
        logger.info(f"\n📊 バッチファクトチェック開始: {len(episodes)}件")

        checked_episodes = []

        for i, ep in enumerate(episodes, 1):
            logger.info(f"\n  [{i}/{len(episodes)}] {ep.get('person_name')} ({ep.get('age')}歳)")

            result = self.check_episode(
                person_name=ep.get('person_name', ''),
                age=ep.get('age', 0),
                episode_text=ep.get('episode_text', ''),
                category=ep.get('category', 'その他')
            )

            # エピソードに検証結果を追加
            ep_with_check = ep.copy()
            ep_with_check['fact_check_result'] = result.status
            ep_with_check['fact_check_confidence'] = result.confidence
            ep_with_check['fact_check_sources'] = result.verification_sources
            ep_with_check['fact_check_notes'] = result.notes

            if result.corrections:
                ep_with_check['fact_check_corrections'] = result.corrections

            checked_episodes.append(ep_with_check)

            # レート制限対策
            time.sleep(1)

        logger.info(f"\n✅ バッチファクトチェック完了")
        logger.info(f"  確認済み: {self.stats['verified']}件")
        logger.info(f"  要確認: {self.stats['needs_review']}件")
        logger.info(f"  事実誤認: {self.stats['errors']}件")

        return checked_episodes

    def get_stats(self) -> Dict:
        """統計情報を取得"""
        return {
            **self.stats,
            'verification_rate': (
                self.stats['verified'] / self.stats['total_checks']
                if self.stats['total_checks'] > 0 else 0
            ),
            'error_rate': (
                self.stats['errors'] / self.stats['total_checks']
                if self.stats['total_checks'] > 0 else 0
            )
        }


def main():
    """テスト実行"""
    import os

    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY環境変数が設定されていません")

    # テスト
    checker = EpisodeFactChecker(api_key)

    # テストエピソード
    test_episode = {
        'person_name': 'アイザック・ニュートン',
        'age': 23,
        'episode_text': 'あなたと同じ23歳のとき、アイザック・ニュートンは万有引力の法則を発見した',
        'category': '科学'
    }

    logger.info(f"\n🔍 テストエピソード:")
    logger.info(f"  人物: {test_episode['person_name']}")
    logger.info(f"  年齢: {test_episode['age']}歳")
    logger.info(f"  エピソード: {test_episode['episode_text']}")

    result = checker.check_episode(
        person_name=test_episode['person_name'],
        age=test_episode['age'],
        episode_text=test_episode['episode_text'],
        category=test_episode['category']
    )

    logger.info(f"\n📊 検証結果:")
    logger.info(f"  判定: {result.status}")
    logger.info(f"  信頼度: {result.confidence:.2f}")
    logger.info(f"  検証根拠:")
    for source in result.verification_sources:
        logger.info(f"    - {source}")
    logger.info(f"  注意事項: {result.notes}")

    if result.corrections:
        logger.info(f"  修正案: {result.corrections}")

    # 統計表示
    stats = checker.get_stats()
    logger.info(f"\n📊 統計情報:")
    logger.info(f"  総チェック数: {stats['total_checks']}")
    logger.info(f"  確認済み率: {stats['verification_rate']*100:.1f}%")
    logger.info(f"  事実誤認率: {stats['error_rate']*100:.1f}%")


if __name__ == "__main__":
    main()
