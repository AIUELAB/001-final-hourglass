#!/usr/bin/env python3
"""クラシック音楽家エピソード生成スクリプト"""

import argparse
import csv
import hashlib
import os
import sys
from datetime import datetime

import anthropic

API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not API_KEY:
    print("❌ ANTHROPIC_API_KEY環境変数が設定されていません")
    sys.exit(1)

client = anthropic.Anthropic(api_key=API_KEY)


def generate_person_id(person_name: str) -> str:
    hash_obj = hashlib.md5(person_name.encode("utf-8"), usedforsecurity=False)
    return f"P{hash_obj.hexdigest()[:7].upper()}"


def generate_episode_id() -> str:
    return f"EP-{datetime.now().strftime('%y%m%d%H%M%S%f')[:17]}"


def generate_episode(person_name: str, age: int, achievement: str, year: str) -> str:
    prompt = f"""あなたは伝記作家です。以下の人物のエピソードを生成してください。

人物: {person_name}（クラシック音楽家）
年齢: {age}歳
業績: {achievement}（{year}年）

【必須形式】
- 「あなたと同じ{age}歳のとき、{person_name}は」で始める
- 250-350文字程度
- 具体的なエピソードや心情を含める
- 事実に基づいた内容

エピソードを生成してください:"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=500, messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--output", default="generated/classical_episodes.csv")
    args = parser.parse_args()

    template_path = "templates/classical_musicians.csv"
    print(f"テンプレート読み込み: {template_path}")

    with open(template_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        candidates = list(reader)

    print(f"候補数: {len(candidates)}件")

    results = []
    for i, c in enumerate(candidates[: args.limit], 1):
        print(f"\n[{i}/{min(len(candidates), args.limit)}] {c['person_name']} ({c['age']}歳)")
        try:
            episode = generate_episode(c["person_name"], int(c["age"]), c["achievement"], c["year"])

            if not episode.startswith("あなたと同じ"):
                print("  ⚠️ フォーマット不一致、スキップ")
                continue

            results.append(
                {
                    "episode_id": generate_episode_id(),
                    "person_id": generate_person_id(c["person_name"]),
                    "person_name": c["person_name"],
                    "category": c["category"],
                    "age": c["age"],
                    "episode_type": "ACHIEVEMENT",
                    "episode_text": episode,
                    "person_type": "REAL",
                    "source": "classical_musician_generation",
                    "generated_at": datetime.now().isoformat(),
                }
            )
            print(f"  ✅ 生成成功 ({len(episode)}字)")
        except Exception as e:
            print(f"  ❌ エラー: {e}")

    # 保存
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8-sig", newline="") as f:
        fieldnames = [
            "episode_id",
            "person_id",
            "person_name",
            "category",
            "age",
            "episode_type",
            "episode_text",
            "person_type",
            "source",
            "generated_at",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n✅ 保存完了: {args.output} ({len(results)}件)")


if __name__ == "__main__":
    main()
