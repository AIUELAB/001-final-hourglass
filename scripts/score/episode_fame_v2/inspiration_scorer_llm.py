"""
InspirationScore LLM直接評価（v2.4）

キーワードマッチングに代わり、LLMが感銘度5軸を直接評価
"""

import hashlib
import json
import logging
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# LLM評価プロンプト（v2.4.1 キャリブレーション済み）
INSPIRATION_PROMPT = """あなたは物語の深さと人間的成長を評価する厳格な審査員です。

【重要：採点基準】
- 9-10点は「歴史に残る極めて稀な事例」のみに付与（全エピソードの1%未満）
- 7-8点は「顕著な達成」（全体の10%程度）
- 5-6点が「標準的な良いエピソード」の中央値
- ほとんどのエピソードは3-6点の範囲に収まるべき
- 文中に明示的記述がない軸は0-2点とすること

【エピソード】
{episode_text}

【人物情報】
人物名: {person_name}

【評価軸の定義（厳格適用）】
1. 困難度（0-10）: 直面した試練・障害の客観的な大きさ
   - 0-2: 困難の記述なし、または日常的な困難
   - 3-4: 一般的な挫折・失敗（受験失敗、失業など）
   - 5-6: 重大な困難（長期の病気、経済的困窮）
   - 7-8: 極めて重大な困難（迫害、投獄、生命の危機）
   - 9-10: 歴史的に稀な極限的困難（27年の獄中、ホロコースト生存など）

2. 努力度（0-10）: 困難を乗り越えるための継続的行動
   - 0-2: 努力の記述なし
   - 3-4: 一般的な努力（数年の練習・学習）
   - 5-6: 長期的な努力（5-10年の継続）
   - 7-8: 非常に長期の集中的努力（10年以上の献身）
   - 9-10: 生涯を通じた極限的な献身

3. 決断度（0-10）: 人生の転機となる選択の有無と質
   - 0-2: 決断の記述なし
   - 3-4: 一般的な決断（進路選択、転職）
   - 5-6: 重要な決断（リスクある挑戦、価値観に基づく選択）
   - 7-8: 非常に重大な決断（命をかけた選択、信念の貫徹）
   - 9-10: 歴史的決断（敵との和解、自己犠牲による社会変革）

4. 達成度（0-10）: 達成の客観的規模と時間的意義
   - 0-2: 達成の記述なし
   - 3-4: 個人的達成（資格取得、初勝利）
   - 5-6: 社会的達成（業界での成功、地域貢献）
   - 7-8: 国家・国際規模の達成（オリンピック、国家的受賞）
   - 9-10: 歴史的達成（ノーベル賞、世界初の偉業、革命的変化）

5. 社会的影響度（0-10）: 個人の行動が社会に及ぼす波及
   - 0-2: 個人的影響のみ
   - 3-4: 身近な人々への影響
   - 5-6: 地域・業界規模の影響
   - 7-8: 国家規模の影響
   - 9-10: 世界規模・歴史的影響（人類史に残る影響）

【ナラティブ構造】
物語のパターン（困難→決断→努力→達成など）を分析。
narrative_depthは「物語としての完成度」を0-10で評価（5が標準）。

JSON形式で回答（数値は整数）:
{{
  "difficulty": 数値,
  "effort": 数値,
  "decision": 数値,
  "achievement": 数値,
  "social_impact": 数値,
  "narrative_pattern": "パターン名",
  "narrative_depth": 0-10,
  "reasoning": "評価理由（50字以内）"
}}"""


class InspirationScorerLLM:
    """LLMベースの感銘度評価"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-haiku-20241022",
        cache_dir: str = "data/cache",
    ):
        """
        初期化

        Args:
            api_key: Anthropic APIキー（Noneの場合は環境変数から取得）
            model: 使用するモデル
            cache_dir: キャッシュディレクトリ
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_db = self.cache_dir / "inspiration_llm_cache.db"
        self._client = None
        self._init_cache()

    @property
    def client(self):
        """遅延初期化されたAnthropicクライアント"""
        if self._client is None:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package required: pip install anthropic")
        return self._client

    def _init_cache(self):
        """キャッシュDB初期化"""
        conn = sqlite3.connect(str(self.cache_db))
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS inspiration_scores (
                episode_hash TEXT PRIMARY KEY,
                difficulty REAL,
                effort REAL,
                decision REAL,
                achievement REAL,
                social_impact REAL,
                narrative_pattern TEXT,
                narrative_depth REAL,
                reasoning TEXT,
                total REAL,
                evaluated_at TEXT,
                model TEXT
            )
        """
        )
        conn.commit()
        conn.close()

    def _get_episode_hash(self, text: str) -> str:
        """エピソードのハッシュ値を取得"""
        return hashlib.md5(text.encode()).hexdigest()

    def _get_cached(self, episode_hash: str) -> Optional[dict]:
        """キャッシュから結果を取得"""
        conn = sqlite3.connect(str(self.cache_db))
        cursor = conn.execute(
            """
            SELECT difficulty, effort, decision, achievement, social_impact,
                   narrative_pattern, narrative_depth, reasoning, total
            FROM inspiration_scores WHERE episode_hash = ?
        """,
            (episode_hash,),
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "difficulty": row[0],
                "effort": row[1],
                "decision": row[2],
                "achievement": row[3],
                "social_impact": row[4],
                "narrative_pattern": row[5],
                "narrative_depth": row[6],
                "reasoning": row[7],
                "total": row[8],
                "cached": True,
            }
        return None

    def _save_cache(self, episode_hash: str, result: dict):
        """キャッシュに結果を保存"""
        conn = sqlite3.connect(str(self.cache_db))
        conn.execute(
            """
            INSERT OR REPLACE INTO inspiration_scores
            (episode_hash, difficulty, effort, decision, achievement, social_impact,
             narrative_pattern, narrative_depth, reasoning, total, evaluated_at, model)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
        """,
            (
                episode_hash,
                result.get("difficulty", 0),
                result.get("effort", 0),
                result.get("decision", 0),
                result.get("achievement", 0),
                result.get("social_impact", 0),
                result.get("narrative_pattern", ""),
                result.get("narrative_depth", 0),
                result.get("reasoning", ""),
                result.get("total", 0),
                self.model,
            ),
        )
        conn.commit()
        conn.close()

    def _build_prompt(self, text: str, person_name: str = "") -> str:
        """評価プロンプトを構築"""
        return INSPIRATION_PROMPT.format(
            episode_text=text,
            person_name=person_name or "不明",
        )

    def _parse_response(self, response_text: str) -> dict:
        """LLMレスポンスからJSONを抽出"""
        # JSON部分を抽出
        json_match = re.search(r"\{[^{}]*\}", response_text, re.DOTALL)
        if not json_match:
            raise ValueError(f"JSON not found in response: {response_text[:200]}")

        try:
            result = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON parse error: {e}, text: {json_match.group()[:200]}")

        # 必須フィールドの検証
        required_fields = [
            "difficulty",
            "effort",
            "decision",
            "achievement",
            "social_impact",
        ]
        for field in required_fields:
            if field not in result:
                result[field] = 0.0
            else:
                # 数値に変換
                try:
                    result[field] = float(result[field])
                except (ValueError, TypeError):
                    result[field] = 0.0
                # 0-10の範囲に制限
                result[field] = max(0.0, min(10.0, result[field]))

        return result

    def _calculate_total(self, result: dict) -> float:
        """5軸から総合スコアを計算（0-100）"""
        # 重み配分（config.pyのINSPIRATION_AXESと同じ）
        weights = {
            "difficulty": 0.25,
            "effort": 0.20,
            "decision": 0.15,
            "achievement": 0.25,
            "social_impact": 0.15,
        }

        weighted_sum = sum(result.get(axis, 0) * weight for axis, weight in weights.items())

        # 0-10スケールを0-100に変換
        base_score = weighted_sum * 10

        # ナラティブボーナス（v2.4.1: 縮小 1.5→0.5、上限15→5）
        narrative_bonus = min(5.0, result.get("narrative_depth", 0) * 0.5)

        total = base_score + narrative_bonus
        return max(0.0, min(100.0, total))

    def evaluate(
        self,
        text: str,
        person_name: str = "",
        use_cache: bool = True,
        retry_count: int = 3,
    ) -> dict:
        """
        エピソードの感銘度をLLMで評価

        Args:
            text: エピソード本文
            person_name: 人物名
            use_cache: キャッシュを使用するか
            retry_count: リトライ回数

        Returns:
            {
                "difficulty": 0-10,
                "effort": 0-10,
                "decision": 0-10,
                "achievement": 0-10,
                "social_impact": 0-10,
                "narrative_pattern": str,
                "narrative_depth": 0-10,
                "reasoning": str,
                "total": 0-100,
                "cached": bool
            }
        """
        if not text or not text.strip():
            return {
                "difficulty": 0,
                "effort": 0,
                "decision": 0,
                "achievement": 0,
                "social_impact": 0,
                "narrative_pattern": "",
                "narrative_depth": 0,
                "reasoning": "",
                "total": 0,
                "cached": False,
            }

        episode_hash = self._get_episode_hash(text)

        # キャッシュ確認
        if use_cache:
            cached = self._get_cached(episode_hash)
            if cached:
                logger.debug(f"Cache hit: {episode_hash[:8]}")
                return cached

        # LLM評価
        prompt = self._build_prompt(text, person_name)

        for attempt in range(retry_count):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=400,
                    messages=[{"role": "user", "content": prompt}],
                )
                result = self._parse_response(response.content[0].text)
                result["total"] = self._calculate_total(result)
                result["cached"] = False

                # キャッシュ保存
                if use_cache:
                    self._save_cache(episode_hash, result)

                return result

            except Exception as e:
                logger.warning(f"LLM evaluation failed (attempt {attempt + 1}): {e}")
                if "rate" in str(e).lower():
                    time.sleep(30 * (attempt + 1))
                elif attempt < retry_count - 1:
                    time.sleep(2)
                else:
                    raise

        # フォールバック
        return {
            "difficulty": 0,
            "effort": 0,
            "decision": 0,
            "achievement": 0,
            "social_impact": 0,
            "narrative_pattern": "",
            "narrative_depth": 0,
            "reasoning": "評価失敗",
            "total": 0,
            "cached": False,
            "error": True,
        }

    def batch_evaluate(
        self,
        episodes: list,
        delay: float = 0.5,
        progress_callback=None,
    ) -> list:
        """
        複数エピソードをバッチ評価

        Args:
            episodes: [{"text": str, "person_name": str}, ...]
            delay: API呼び出し間の遅延（秒）
            progress_callback: 進捗コールバック(i, total)

        Returns:
            評価結果のリスト
        """
        results = []
        total = len(episodes)

        for i, ep in enumerate(episodes):
            text = ep.get("text", "")
            person_name = ep.get("person_name", "")

            result = self.evaluate(text, person_name)
            results.append(result)

            if progress_callback:
                progress_callback(i + 1, total)

            # キャッシュヒットでなければ遅延
            if not result.get("cached", False):
                time.sleep(delay)

        return results

    def get_cache_stats(self) -> dict:
        """キャッシュ統計を取得"""
        conn = sqlite3.connect(str(self.cache_db))
        cursor = conn.execute("SELECT COUNT(*) FROM inspiration_scores")
        count = cursor.fetchone()[0]
        conn.close()
        return {"cached_count": count}


def calculate_inspiration_score_llm(
    text: str,
    person_name: str = "",
    category: str = "",
    api_key: str = None,
) -> dict:
    """
    LLMで感銘度を計算（関数インターフェース）

    Args:
        text: エピソード本文
        person_name: 人物名
        category: カテゴリ（現在未使用）
        api_key: APIキー

    Returns:
        calculate_inspiration_scoreと互換の出力形式
    """
    scorer = InspirationScorerLLM(api_key=api_key)
    result = scorer.evaluate(text, person_name)

    # 従来形式に変換
    return {
        "total": result["total"],
        "axes": {
            "difficulty": result["difficulty"],
            "effort": result["effort"],
            "decision": result["decision"],
            "achievement": result["achievement"],
            "social_impact": result["social_impact"],
        },
        "narrative_bonus": result.get("narrative_depth", 0) * 1.5,
        "details": {
            "matched_keywords": {},  # LLM版ではキーワードなし
            "base_score": result["total"] - result.get("narrative_depth", 0) * 1.5,
            "llm_reasoning": result.get("reasoning", ""),
            "narrative_pattern": result.get("narrative_pattern", ""),
        },
        "llm_evaluated": True,
    }
