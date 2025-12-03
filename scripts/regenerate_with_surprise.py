#!/usr/bin/env python3
"""
意外性を重視したエピソード再生成スクリプト

低い意外性スコアのエピソードを、予想外の展開や転機を含むエピソードに再生成する。
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"

API_KEY = os.getenv("ANTHROPIC_API_KEY")

# 意外性重視の再生成プロンプト
SURPRISE_PROMPT = """あなたは著名人の人生における「意外な転機」を描くエピソード作家です。

【人物情報】
- 名前: {person_name}
- カテゴリ: {category}
- 対象年齢: {age}歳
- 人物タイプ: {person_type}

【現在のエピソード（意外性が低い）】
{current_text}

【改善要件】
1. 形式: 「あなたと同じ{age}歳のとき、{person_name}は〜」で開始
2. 長さ: 200-350文字
3. **意外性を高める要素を必ず含める**:
   - 予想外の失敗や挫折からの学び
   - 意外な出会いや偶然の発見
   - 常識に反する決断
   - 逆転や転機となる出来事
   - 周囲の反対を押し切った行動
   - 意外な副業や趣味との関係

4. 具体性:
   - 検証可能な事実をベースに
   - 具体的な日付、数字、エピソードを使用
   - 実際に起きた転機を描写

5. ドラマ構造:
   - 状況→転機→結果の3段構成
   - 読者の「へぇ〜」という驚きを引き出す

【注意】
- 平凡な成功譚は避ける
- 「順調に〜」「努力が実り〜」などの定型表現は使わない
- 実在の事実に基づく意外な側面を描く

エピソードテキストのみを出力してください:"""


def regenerate_with_surprise(client, row: dict) -> str | None:
    """意外性を重視してエピソードを再生成"""
    prompt = SURPRISE_PROMPT.format(
        person_name=row.get("person_name", "不明"),
        age=row.get("age", "不明"),
        category=row.get("category", "不明"),
        person_type=row.get("person_type", "REAL"),
        current_text=row.get("episode_text", ""),
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            temperature=0.8,  # 少し高めで創造性を促す
            messages=[{"role": "user", "content": prompt}],
        )

        new_text = response.content[0].text.strip()

        # 形式チェック
        if not new_text.startswith("あなたと同じ"):
            return None

        return new_text

    except Exception as e:
        print(f"  ❌ 再生成エラー: {e}")
        return None


def evaluate_surprise(client, episode_text: str, person_name: str) -> float | None:
    """エピソードの意外性を評価"""
    prompt = f"""以下のエピソードの「意外性」を1-10で評価してください。

【人物】{person_name}
【エピソード】
{episode_text}

【評価基準】
- 10: 予想を大きく覆す驚きの展開
- 7-9: 意外な側面や転機が含まれる
- 5-6: やや意外な要素がある
- 3-4: 予想通りの内容
- 1-2: 完全に定型的

数字のみを出力してください:"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=10,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )

        result = response.content[0].text.strip()
        # 数字を抽出
        for char in result:
            if char.isdigit():
                score = int(char)
                if 1 <= score <= 10:
                    return float(score)
        return None

    except Exception as e:
        print(f"  ❌ 評価エラー: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="意外性重視のエピソード再生成")
    parser.add_argument("--threshold", type=float, default=5.0, help="対象の意外性スコア閾値")
    parser.add_argument("--limit", type=int, default=30, help="処理上限")
    parser.add_argument("--execute", action="store_true", help="実際に再生成を実行")
    args = parser.parse_args()

    print("=" * 70)
    print("🎭 意外性重視エピソード再生成システム")
    print("=" * 70)

    # CSV読み込み
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"\n📂 DB: {len(df)}件")

    # 意外性スコアが低いものを抽出
    surprise_scores = pd.to_numeric(df["意外性スコア"], errors="coerce")
    targets = df[surprise_scores < args.threshold].copy()
    targets = targets.head(args.limit)

    print(f"🎯 対象（意外性 < {args.threshold}）: {len(targets)}件")

    if len(targets) == 0:
        print("⚠️ 対象エピソードがありません")
        return 0

    if not args.execute:
        print("\n💡 --execute オプションで実際に再生成を実行します")
        print("\n【対象サンプル】")
        for _, row in targets.head(5).iterrows():
            print(f"  {row['episode_id']}: {row['person_name']} ({row['age']}歳) 意外性={row['意外性スコア']}")
        return 0

    if not API_KEY:
        print("❌ ANTHROPIC_API_KEY が設定されていません")
        return 1

    import anthropic

    client = anthropic.Anthropic(api_key=API_KEY)

    print(f"\n🔧 意外性重視の再生成を開始（{len(targets)}件）...")

    improved = []
    failed = []

    for i, (idx, row) in enumerate(targets.iterrows(), 1):
        episode_id = row["episode_id"]
        person_name = row["person_name"]
        age = row["age"]
        old_score = row["意外性スコア"]

        print(f"\n[{i}/{len(targets)}] {person_name} ({age}歳) - 現在: {old_score}")

        # 再生成
        new_text = regenerate_with_surprise(client, row.to_dict())

        if not new_text:
            print("  ❌ 再生成失敗")
            failed.append({"episode_id": episode_id, "reason": "再生成失敗"})
            continue

        # 新しいエピソードの意外性を評価
        new_score = evaluate_surprise(client, new_text, person_name)

        if new_score is None:
            print("  ❌ 評価失敗")
            failed.append({"episode_id": episode_id, "reason": "評価失敗"})
            continue

        print(f"  📊 新スコア: {new_score}")

        if new_score > old_score:
            print(f"  ✅ 改善: {old_score} → {new_score}")
            improved.append(
                {
                    "episode_id": episode_id,
                    "person_name": person_name,
                    "old_score": old_score,
                    "new_score": new_score,
                    "new_text": new_text,
                }
            )

            # CSVを更新
            df.loc[idx, "episode_text"] = new_text
            df.loc[idx, "意外性スコア"] = new_score
            df.loc[idx, "source"] = f"{row.get('source', '')}→SURPRISE_IMPROVED"
        else:
            print(f"  ⚠️ 改善なし: {old_score} → {new_score}")

    # 結果サマリー
    print(f"\n{'=' * 70}")
    print("📊 再生成結果サマリー")
    print(f"{'=' * 70}")
    print(f"  処理完了: {len(targets)}件")
    print(f"  改善成功: {len(improved)}件")
    print(f"  失敗: {len(failed)}件")

    if improved:
        print("\n【改善されたエピソード】")
        for imp in improved[:10]:
            print(f"  {imp['person_name']}: {imp['old_score']} → {imp['new_score']}")

        # CSV保存
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"\n💾 CSV更新完了: {CSV_PATH}")

    # レポート保存
    REPORTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"surprise_improvement_{timestamp}.json"

    report = {
        "timestamp": timestamp,
        "threshold": args.threshold,
        "total_processed": len(targets),
        "improved_count": len(improved),
        "failed_count": len(failed),
        "improved_episodes": improved,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n📄 レポート: {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
