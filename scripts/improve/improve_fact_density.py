#!/usr/bin/env python3
"""
factual_density改善スクリプト

factual_density3.0-3.5のエピソードを改稿してfactual_densityを向上させる

使用方法:
    # テスト実行（5件）
    python scripts/improve_fact_density.py --count 5 --dry-run

    # 本番実行
    python scripts/improve_fact_density.py --count 50 --execute

環境変数:
    ANTHROPIC_API_KEY: Anthropic APIキー
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import anthropic
import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# CSVパス
CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = PROJECT_ROOT / "reports"

# 環境変数チェック
API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not API_KEY:
    print("❌ ANTHROPIC_API_KEY環境変数が設定されていません")
    sys.exit(1)

# Anthropic クライアント
client = anthropic.Anthropic(api_key=API_KEY)

# 7軸フィールド
SEVEN_AXIS_FIELDS = [
    "memorability_score",
    "empathy_score",
    "surprise_score",
    "generation_quality_score",
    "educational_value",
    "story_quality",
    "factual_density",
]


def calculate_composite_score(scores: Dict[str, float]) -> float:
    """7軸スコアから超総合スコア(0-1000)を計算"""
    vals = [scores.get(axis, 0) for axis in SEVEN_AXIS_FIELDS if axis in scores]
    if not vals:
        return 0
    avg = sum(vals) / len(vals)
    normalized = max(0, (avg - 1.0) / 9.0)
    transformed = normalized**0.85
    return round(transformed * 1000, 1)


def build_fact_improvement_prompt(episode_text: str, person_name: str, age: int) -> str:
    """factual_density向上用プロンプト"""
    return f"""以下のエピソードを改稿して、factual_densityを大幅に向上させてください。

【元のエピソード】
{episode_text}

【人物情報】
人物名: {person_name}
年齢: {age}歳

【改善指示 - factual_densityを最優先で向上】
以下の具体的な事実・データを必ず追加してください：
1. 具体的な年号（例: 1985年、2003年3月）
2. 数値データ（例: 100万部突破、3時間32分、世界ランキング2位）
3. 固有名詞（作品名、大会名、場所名、関係者名）
4. 検証可能な記録や受賞歴（例: ○○賞受賞、史上最年少記録）
5. 具体的な出来事や事件

【禁止事項】
- 「多くの」「長年にわたり」などの曖昧な表現
- 架空の情報の創作
- 検証できない内面描写の過度な追加

【必須ルール】
1. 「あなたと同じ{age}歳のとき、{person_name}は〜」という形式で必ず始める
2. 250-350文字程度
3. 元のエピソードの核心は維持しつつ、具体的な事実を追加

改稿後のエピソード:"""


def llm_improve_episode(episode_text: str, person_name: str, age: int) -> Optional[str]:
    """LLMでエピソードを改稿"""
    prompt = build_fact_improvement_prompt(episode_text, person_name, age)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=600, messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"  ❌ 改稿エラー: {e}")
        return None


def llm_evaluate_7axis(episode_text: str) -> Optional[Dict[str, float]]:
    """LLMで7軸評価"""
    prompt = f"""以下のエピソードを7軸で評価してください。各軸1.0〜10.0点で採点してください。

【エピソード】
{episode_text}

【評価軸】
1. memorability_score: 読後も印象に残るか
2. empathy_score: 感情移入できるか
3. surprise_score: 予想外の展開があるか
4. generation_quality_score: 文章として完成度が高いか
5. educational_value: 学びや教訓があるか
6. story_quality: 構成が良いか
7. factual_density: 具体的なデータ・事実があるか

必ず以下のJSON形式のみで回答してください:
{{"memorability_score": X.X, "empathy_score": X.X, "surprise_score": X.X, "generation_quality_score": X.X, "educational_value": X.X, "story_quality": X.X, "factual_density": X.X}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=200, messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()
        json_match = re.search(r"\{[^}]+\}", text)
        if json_match:
            return json.loads(json_match.group())
        return None
    except Exception as e:
        print(f"  ❌ 評価エラー: {e}")
        return None


def get_low_fact_density_episodes(df: pd.DataFrame, count: int) -> pd.DataFrame:
    """factual_density3.0-3.5のエピソードを取得"""
    low_fact = df[(df["factual_density"] >= 3.0) & (df["factual_density"] < 3.5)].copy()
    # factual_densityが低い順にソート
    low_fact = low_fact.sort_values("factual_density")
    return low_fact.head(count)


def improve_episode(row: pd.Series) -> Optional[Dict]:
    """1件のエピソードを改稿"""
    episode_id = row["episode_id"]
    person_name = row["person_name"]
    age = int(row["age"])
    original_text = str(row["episode_text"])
    original_fact_density = float(row["factual_density"])

    print(f"\n{'='*60}")
    print(f"改稿中: {person_name} ({age}歳) [{episode_id}]")
    print(f"元のfactual_density: {original_fact_density:.2f}")
    print(f"{'='*60}")

    # 改稿
    print("  改稿中...")
    improved_text = llm_improve_episode(original_text, person_name, age)

    if not improved_text:
        print("  ❌ 改稿失敗")
        return None

    # 再評価
    print("  再評価中...")
    time.sleep(0.3)
    new_scores = llm_evaluate_7axis(improved_text)

    if not new_scores:
        print("  ❌ 再評価失敗")
        return None

    new_fact_density = new_scores.get("factual_density", 0)
    new_composite = calculate_composite_score(new_scores)

    # 改善判定
    fact_improved = new_fact_density > original_fact_density
    gate_passed = new_fact_density >= 3.5

    if fact_improved and gate_passed:
        print(f"  ✅ factual_density向上: {original_fact_density:.2f} → {new_fact_density:.2f}")
        print("  ✅ 品質ゲート合格 (≥3.5)")
        return {
            "episode_id": episode_id,
            "person_name": person_name,
            "age": age,
            "original_text": original_text,
            "improved_text": improved_text,
            "original_fact_density": original_fact_density,
            "new_fact_density": new_fact_density,
            "new_composite": new_composite,
            "new_scores": new_scores,
            "status": "improved",
        }
    elif fact_improved:
        print(f"  🔄 factual_density向上: {original_fact_density:.2f} → {new_fact_density:.2f}")
        print("  ⚠️ 品質ゲート未達 (<3.5)")
        return {
            "episode_id": episode_id,
            "person_name": person_name,
            "age": age,
            "original_text": original_text,
            "improved_text": improved_text,
            "original_fact_density": original_fact_density,
            "new_fact_density": new_fact_density,
            "new_composite": new_composite,
            "new_scores": new_scores,
            "status": "partial",
        }
    else:
        print(f"  ❌ factual_density未改善: {original_fact_density:.2f} → {new_fact_density:.2f}")
        return {"episode_id": episode_id, "status": "no_improvement"}


def run_improvement(count: int, execute: bool) -> Dict:
    """改稿バッチ実行"""
    print("=" * 60)
    print("📊 Phase 5: factual_density改善")
    print("=" * 60)

    # CSV読み込み
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"  総エピソード: {len(df)}件")

    # 対象抽出
    targets = get_low_fact_density_episodes(df, count)
    print(f"  改稿対象: {len(targets)}件 (factual_density 3.0-3.5)")

    if len(targets) == 0:
        print("  ⚠️ 対象エピソードがありません")
        return {}

    # 改稿実行
    results = {"improved": [], "partial": [], "no_improvement": [], "failed": []}

    for i, (_, row) in enumerate(targets.iterrows()):
        print(f"\n[{i+1}/{len(targets)}]", end="")
        result = improve_episode(row)

        if result is None:
            results["failed"].append(row["episode_id"])
        elif result["status"] == "improved":
            results["improved"].append(result)
        elif result["status"] == "partial":
            results["partial"].append(result)
        else:
            results["no_improvement"].append(result)

        time.sleep(0.5)

    # サマリー
    print("\n" + "=" * 60)
    print("📊 改稿結果サマリー")
    print("=" * 60)
    print(f"  品質ゲート合格: {len(results['improved'])}件")
    print(f"  部分改善: {len(results['partial'])}件")
    print(f"  未改善: {len(results['no_improvement'])}件")
    print(f"  失敗: {len(results['failed'])}件")

    if not execute:
        print("\n⚠️ --execute オプションなし: 保存スキップ")
        return results

    # CSV更新
    update_count = 0
    for improved in results["improved"] + results["partial"]:
        if improved["status"] in ["improved", "partial"]:
            idx = df[df["episode_id"] == improved["episode_id"]].index
            if len(idx) > 0:
                df.loc[idx[0], "episode_text"] = improved["improved_text"]
                for axis in SEVEN_AXIS_FIELDS:
                    if axis in improved["new_scores"]:
                        df.loc[idx[0], axis] = improved["new_scores"][axis]
                df.loc[idx[0], "composite_score"] = improved["new_composite"]
                update_count += 1

    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"\n✅ CSVを更新: {update_count}件")

    # レポート保存
    REPORT_DIR.mkdir(exist_ok=True)
    report_path = REPORT_DIR / f"fact_density_improvement_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "target_count": len(targets),
                "improved_count": len(results["improved"]),
                "partial_count": len(results["partial"]),
                "no_improvement_count": len(results["no_improvement"]),
                "failed_count": len(results["failed"]),
                "improved_episodes": [
                    {
                        "episode_id": r["episode_id"],
                        "person_name": r["person_name"],
                        "age": r["age"],
                        "original_fact_density": r["original_fact_density"],
                        "new_fact_density": r["new_fact_density"],
                    }
                    for r in results["improved"]
                ],
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"📝 レポート保存: {report_path}")

    return results


def main():
    parser = argparse.ArgumentParser(description="factual_density改善スクリプト")
    parser.add_argument("--count", type=int, default=50, help="改稿件数")
    parser.add_argument("--dry-run", action="store_true", help="テスト実行（保存なし）")
    parser.add_argument("--execute", action="store_true", help="本番実行")
    args = parser.parse_args()

    execute = args.execute and not args.dry_run

    run_improvement(args.count, execute)


if __name__ == "__main__":
    main()
