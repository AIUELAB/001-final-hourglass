"""
Fact Checker - Perplexity API を使った人物実在性検証

疑わしいレコード（person_type=REAL, fame_score < 1.0）を
Perplexity API で検証し、実在性を判定する。
"""

import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# API設定
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "")
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

# APIキーファイルから読み込み（環境変数がない場合）
API_KEY_PATH = Path("/Users/admin/Documents/key/Perplexity_API.txt")
if not PERPLEXITY_API_KEY and API_KEY_PATH.exists():
    PERPLEXITY_API_KEY = API_KEY_PATH.read_text().strip()


@dataclass
class FactCheckResult:
    """ファクトチェック結果"""

    person_name: str
    is_real: bool  # 実在する人物か
    confidence: str  # high, medium, low
    evidence: str  # 根拠
    wikipedia_exists: bool  # Wikipedia記事の存在
    category_match: bool  # カテゴリが一致するか
    recommendation: str  # REAL, FICTIONAL, UNVERIFIED
    parse_error: bool = False  # 応答解析エラーフラグ


def check_person_existence(
    person_name: str,
    category: str,
    episode_text: str = "",
) -> FactCheckResult:
    """
    Perplexity API で人物の実在性を検証

    Args:
        person_name: 人物名
        category: カテゴリ（スポーツ、ビジネス等）
        episode_text: エピソードテキスト（追加コンテキスト用）

    Returns:
        FactCheckResult: 検証結果
    """
    if not PERPLEXITY_API_KEY:
        logger.error(
            "PERPLEXITY_API_KEY not configured. Fact checking is disabled. Set via environment variable or %s",
            API_KEY_PATH,
        )
        return FactCheckResult(
            person_name=person_name,
            is_real=False,
            confidence="low",
            evidence="APIキーが設定されていません",
            wikipedia_exists=False,
            category_match=False,
            recommendation="UNVERIFIED",
        )

    # プロンプト作成
    prompt = f"""以下の人物が実在するか検証してください。

人物名: {person_name}
カテゴリ: {category}

以下の形式でJSON形式で回答してください:
{{
    "exists": true/false,
    "confidence": "high/medium/low",
    "evidence": "根拠の説明（50文字以内）",
    "wikipedia": true/false,
    "category_match": true/false,
    "notes": "補足情報"
}}

注意:
- 「実在する」とは、Wikipedia、ニュース記事、公式記録等で確認できる人物
- 名前が似ている別人と混同しないこと
- 架空のキャラクターや創作人物は exists=false"""

    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "llama-3.1-sonar-small-128k-online",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 500,
    }

    try:
        response = requests.post(
            PERPLEXITY_API_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()

        try:
            result = response.json()
        except json.JSONDecodeError as e:
            logger.error(
                "Perplexity API returned invalid JSON: person_name=%s error=%s",
                person_name,
                str(e),
            )
            return FactCheckResult(
                person_name=person_name,
                is_real=False,
                confidence="low",
                evidence="API応答がJSONではありません",
                wikipedia_exists=False,
                category_match=False,
                recommendation="UNVERIFIED",
                parse_error=True,
            )

        try:
            content = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            logger.error(
                "Unexpected Perplexity API response structure: person_name=%s error=%s response=%s",
                person_name,
                str(e),
                str(result)[:200],
            )
            return FactCheckResult(
                person_name=person_name,
                is_real=False,
                confidence="low",
                evidence="API応答構造が予期と異なります",
                wikipedia_exists=False,
                category_match=False,
                recommendation="UNVERIFIED",
                parse_error=True,
            )

        # JSON部分を抽出
        try:
            # JSON部分を探す
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = content[start:end]
                data = json.loads(json_str)

                exists = data.get("exists", False)
                confidence = data.get("confidence", "low")
                evidence = data.get("evidence", "不明")
                wikipedia = data.get("wikipedia", False)
                category_match = data.get("category_match", False)

                # 推奨判定
                if exists and confidence == "high":
                    recommendation = "REAL"
                elif not exists:
                    recommendation = "FICTIONAL"
                else:
                    recommendation = "UNVERIFIED"

                return FactCheckResult(
                    person_name=person_name,
                    is_real=exists,
                    confidence=confidence,
                    evidence=evidence[:100],
                    wikipedia_exists=wikipedia,
                    category_match=category_match,
                    recommendation=recommendation,
                )
            # JSONが見つからなかった場合は、後続で「応答解析エラー」として処理する
            logger.warning(
                "Perplexity応答にJSONが含まれていません: person_name=%s category=%s content_preview=%s",
                person_name,
                category,
                content[:200].replace("\n", " "),
            )
        except json.JSONDecodeError as e:
            # サイレント失敗を避ける（RCA-20260123）
            logger.warning(
                "Perplexity応答のJSON解析に失敗: person_name=%s category=%s error=%s content_preview=%s",
                person_name,
                category,
                str(e),
                content[:200].replace("\n", " "),
            )

        # JSONパースに失敗した場合
        return FactCheckResult(
            person_name=person_name,
            is_real=False,
            confidence="low",
            evidence=f"応答解析エラー: {content[:100]}",
            wikipedia_exists=False,
            category_match=False,
            recommendation="UNVERIFIED",
            parse_error=True,
        )

    except requests.RequestException as e:
        logger.error(
            "Perplexity API error: person_name=%s category=%s error_type=%s error=%s",
            person_name,
            category,
            type(e).__name__,
            str(e),
        )
        return FactCheckResult(
            person_name=person_name,
            is_real=False,
            confidence="low",
            evidence=f"APIエラー: {str(e)[:50]}",
            wikipedia_exists=False,
            category_match=False,
            recommendation="UNVERIFIED",
            parse_error=True,
        )


def batch_fact_check(
    records: list[dict],
    delay: float = 1.0,
    max_records: int = 50,
) -> list[FactCheckResult]:
    """
    複数レコードを一括ファクトチェック

    Args:
        records: レコードリスト（person_name, category を含む）
        delay: API呼び出し間隔（秒）
        max_records: 最大処理件数

    Returns:
        list[FactCheckResult]: 結果リスト
    """
    results = []

    for i, record in enumerate(records[:max_records]):
        person_name = record.get("person_name", "")
        category = record.get("category", "")
        episode_text = record.get("episode_text", "")

        logger.info(f"[{i + 1}/{min(len(records), max_records)}] Checking: {person_name}")

        result = check_person_existence(person_name, category, episode_text)
        results.append(result)

        # レート制限対策
        if i < len(records) - 1:
            time.sleep(delay)

    return results


# CLI対応
if __name__ == "__main__":
    import argparse
    import pandas as pd

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Fact Checker")
    parser.add_argument("--person", help="単一人物名を検証")
    parser.add_argument("--category", default="", help="カテゴリ")
    parser.add_argument("--batch", action="store_true", help="疑わしいレコードを一括検証")
    parser.add_argument("--limit", type=int, default=10, help="一括検証の最大件数")
    args = parser.parse_args()

    if args.person:
        result = check_person_existence(args.person, args.category)
        print("\n=== ファクトチェック結果 ===")
        print(f"人物名: {result.person_name}")
        print(f"実在: {result.is_real}")
        print(f"信頼度: {result.confidence}")
        print(f"根拠: {result.evidence}")
        print(f"Wikipedia: {result.wikipedia_exists}")
        print(f"推奨: {result.recommendation}")

    elif args.batch:
        # 疑わしいレコードを読み込み
        df = pd.read_csv("preserved/data/MASTER_EPISODES_CURRENT.csv", encoding="utf-8-sig")
        suspicious = df[
            (df["person_type"] == "REAL") & (df["fame_score_v3"] < 1.0) & (df["fact_check_result"] == "要再検証")
        ]

        print(f"疑わしいレコード: {len(suspicious)}件")
        print(f"検証対象: {args.limit}件")

        records = suspicious[["person_name", "category", "episode_text"]].to_dict("records")
        results = batch_fact_check(records, max_records=args.limit)

        print("\n=== 検証結果サマリー ===")
        real_count = sum(1 for r in results if r.recommendation == "REAL")
        fictional_count = sum(1 for r in results if r.recommendation == "FICTIONAL")
        unverified_count = sum(1 for r in results if r.recommendation == "UNVERIFIED")

        print(f"REAL: {real_count}")
        print(f"FICTIONAL: {fictional_count}")
        print(f"UNVERIFIED: {unverified_count}")

        print("\n=== 詳細 ===")
        for r in results:
            status = "✓" if r.is_real else "✗"
            print(f"{status} {r.person_name}: {r.recommendation} ({r.confidence}) - {r.evidence[:50]}")
