#!/usr/bin/env python3
"""
テンプレートCSVからエピソードを生成するスクリプト

使用方法:
    python3 generate_episodes_from_template.py \
        --template templates/film_theater_batch1.csv \
        --output generated_episodes.csv \
        --limit 5

環境変数:
    ANTHROPIC_API_KEY: Anthropic APIキー
"""

import argparse
import csv
import hashlib
import json
import os
import random
import sys
from datetime import datetime
from typing import Dict, List, Optional

import anthropic

# 環境変数チェック
API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not API_KEY:
    print("❌ ANTHROPIC_API_KEY環境変数が設定されていません")
    sys.exit(1)

# Anthropic クライアント初期化
client = anthropic.Anthropic(api_key=API_KEY)


def generate_person_id(person_name: str) -> str:
    """person_nameからperson_idを生成"""
    hash_obj = hashlib.md5(person_name.encode("utf-8"), usedforsecurity=False)  # noqa: S324
    hash_hex = hash_obj.hexdigest()[:7].upper()
    return f"P{hash_hex}"


def calculate_quality_scores(episode_text: str) -> Dict[str, float]:
    """品質スコアを計算（簡易版）"""
    # 文字数
    char_count = len(episode_text)

    # 基本スコア
    scores = {
        "記憶性スコア": 8.5,
        "共感性スコア": 7.0,
        "意外性スコア": 8.0,
        "生成品質スコア": 8.5,
        "教育的価値": 8.0,
        "ストーリー品質": 8.5,
        "事実密度": 8.5,
    }

    # 文字数による調整
    if char_count < 150:
        for key in scores:
            scores[key] -= 1.0
    elif char_count > 300:
        for key in scores:
            scores[key] += 0.5

    # composite_score計算
    scores["composite_score"] = sum(scores.values()) / len(scores) * 10

    return scores


def generate_episode(person_name: str, category: str, person_type: str) -> Optional[Dict]:
    """エピソードを生成"""

    print(f"\n{'='*80}")
    print(f"生成中: {person_name} ({category})")
    print(f"{'='*80}")

    # ランダムな年齢を生成（20-70歳）
    age = random.randint(20, 70)

    # プロンプト作成
    prompt = f"""あなたは、人物の人生における印象的なエピソードを生成する専門家です。

以下の人物について、{age}歳のときの印象的なエピソードを日本語で生成してください。

人物名: {person_name}
カテゴリ: {category}
年齢: {age}歳

エピソードの要件:
1. 「あなたと同じ{age}歳のとき、{person_name}は〜」という形式で始める
2. 具体的な事実や出来事を含める
3. 記憶に残る印象的な内容にする
4. 200-300文字程度
5. 教育的価値のある内容にする
6. 事実に基づいた内容にする（架空の内容は避ける）

エピソードテキスト:"""

    try:
        # Anthropic API呼び出し
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=500,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}],
        )

        episode_text = message.content[0].text.strip()

        # person_id生成
        person_id = generate_person_id(person_name)

        # 品質スコア計算
        scores = calculate_quality_scores(episode_text)

        # エピソードデータ作成
        episode = {
            "person_id": person_id,
            "person_name": person_name,
            "episode_count": "",
            "age": age,
            "category": category,
            "char_count": len(episode_text),
            "episode_text": episode_text,
            "episode_type": "ACHIEVEMENT",
            "fact_check_result": "",
            "group_name": "",
            "is_group_member": "",
            "person_type": person_type,
            "quality_score": "",
            "slot": "",
            "source": "",
            "tier": "",
            "week": "",
            "work_title": "",
            "generation_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fame_tier": "",
            "wikipedia_ja": "",
            "textbook": "",
            "award_level": "",
            "notoriety": "",
            "fame_score": 70.0,
            "composite_score": scores["composite_score"],
            "fame_score_updated_at": "",
            "人生の節目タグ": "",
            "記憶性スコア": scores["記憶性スコア"],
            "共感性スコア": scores["共感性スコア"],
            "意外性スコア": scores["意外性スコア"],
            "生成品質スコア": scores["生成品質スコア"],
            "教育的価値": scores["教育的価値"],
            "ストーリー品質": scores["ストーリー品質"],
            "事実密度": scores["事実密度"],
            "category_original": category,
        }

        print("✅ 生成成功")
        print(f"   文字数: {len(episode_text)}文字")
        print(f"   composite_score: {scores['composite_score']:.2f}点")
        print(f"   エピソード: {episode_text[:80]}...")

        return episode

    except Exception as e:
        print(f"❌ エラー: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="テンプレートCSVからエピソードを生成")
    parser.add_argument("--template", required=True, help="テンプレートCSVファイルパス")
    parser.add_argument("--output", required=True, help="出力CSVファイルパス")
    parser.add_argument("--limit", type=int, help="生成数の上限")

    args = parser.parse_args()

    print("=" * 80)
    print("📝 エピソード生成スクリプト")
    print("=" * 80)
    print(f"テンプレート: {args.template}")
    print(f"出力先: {args.output}")
    print(f"生成上限: {args.limit if args.limit else '制限なし'}")
    print("=" * 80)

    # テンプレート読み込み
    try:
        with open(args.template, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            template_rows = list(reader)
    except FileNotFoundError:
        print(f"❌ テンプレートファイルが見つかりません: {args.template}")
        sys.exit(1)

    print(f"\nテンプレート読み込み: {len(template_rows)}件")

    # 生成数制限
    if args.limit:
        template_rows = template_rows[: args.limit]
        print(f"生成数を{args.limit}件に制限")

    # エピソード生成
    generated_episodes = []
    success_count = 0
    fail_count = 0

    for i, row in enumerate(template_rows, 1):
        person_name = row["person_name"]
        category = row["category"]
        person_type = row["person_type"]

        print(f"\n[{i}/{len(template_rows)}] {person_name}")

        episode = generate_episode(person_name, category, person_type)

        if episode:
            generated_episodes.append(episode)
            success_count += 1
        else:
            fail_count += 1

    # 結果表示
    print("\n" + "=" * 80)
    print("📊 生成結果")
    print("=" * 80)
    print(f"成功: {success_count}件")
    print(f"失敗: {fail_count}件")
    print(f"合計: {len(generated_episodes)}件")

    # CSV出力
    if generated_episodes:
        # CSVフィールド名（MASTER_EPISODES_CURRENT.csvと同じ順序）
        fieldnames = [
            "person_id",
            "person_name",
            "episode_count",
            "age",
            "category",
            "char_count",
            "episode_text",
            "episode_type",
            "fact_check_result",
            "group_name",
            "is_group_member",
            "person_type",
            "quality_score",
            "slot",
            "source",
            "tier",
            "week",
            "work_title",
            "generation_timestamp",
            "fame_tier",
            "wikipedia_ja",
            "textbook",
            "award_level",
            "notoriety",
            "fame_score",
            "composite_score",
            "fame_score_updated_at",
            "人生の節目タグ",
            "記憶性スコア",
            "共感性スコア",
            "意外性スコア",
            "生成品質スコア",
            "教育的価値",
            "ストーリー品質",
            "事実密度",
            "category_original",
        ]

        with open(args.output, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(generated_episodes)

        print(f"\n✅ 保存完了: {args.output}")
    else:
        print("\n⚠️  生成されたエピソードがありません")

    print("\n" + "=" * 80)
    print("完了")
    print("=" * 80)


if __name__ == "__main__":
    main()
