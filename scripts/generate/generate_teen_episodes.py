#!/usr/bin/env python3
"""
Phase 8: 10代エピソード生成スクリプト

10代（14-19歳）のエピソードを集中生成する。
ロードマップ Phase 8 Priority 1 に対応。

使用方法:
    ANTHROPIC_API_KEY=xxx python3 scripts/generate_teen_episodes.py --limit 50
"""

import argparse
import csv
import hashlib
import os
import random
import sys
from datetime import datetime
from typing import Optional

import anthropic

# 環境変数チェック
API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not API_KEY:
    print("❌ ANTHROPIC_API_KEY環境変数が設定されていません")
    sys.exit(1)

# Anthropic クライアント初期化
client = anthropic.Anthropic(api_key=API_KEY)


# =============================================================================
# 年齢境界チェック関数（誤指令F-002修正）
# =============================================================================


def get_valid_teen_age(
    person_name: str, birth_year: Optional[int], death_year: Optional[int], min_age: int = 14, max_age: int = 19
) -> Optional[int]:
    """
    生年/没年を考慮して、有効な10代の年齢をランダムに選択

    Args:
        person_name: 人物名（ログ用）
        birth_year: 生年（Noneの場合はチェックスキップ）
        death_year: 没年（Noneの場合は存命と判断）
        min_age: 最小年齢（デフォルト14歳）
        max_age: 最大年齢（デフォルト19歳）

    Returns:
        有効な年齢、または到達不可能な場合はNone
    """
    if birth_year is None:
        print(f"⚠️  {person_name}: birth_year不明のため年齢チェックをスキップ（範囲内からランダム選択）")
        return random.randint(min_age, max_age)

    current_year = datetime.now().year

    # 最大到達年齢を計算
    if death_year:
        max_lived_age = death_year - birth_year
        print(f"   {person_name}: 没年{death_year}年、享年{max_lived_age}歳")
    else:
        max_lived_age = current_year - birth_year
        print(f"   {person_name}: 存命中、現在{max_lived_age}歳（推定）")

    # 有効な年齢範囲を計算
    valid_ages = [a for a in range(min_age, max_age + 1) if a <= max_lived_age]

    if not valid_ages:
        print(f"❌ {person_name}は{min_age}歳に到達していません（最大{max_lived_age}歳）")
        return None

    selected_age = random.choice(valid_ages)
    print(f"✅ 選択年齢: {selected_age}歳（有効範囲: {min(valid_ages)}-{max(valid_ages)}歳）")
    return selected_age


def generate_person_id(person_name: str) -> str:
    """person_nameからperson_idを生成"""
    hash_obj = hashlib.md5(person_name.encode("utf-8"), usedforsecurity=False)
    hash_hex = hash_obj.hexdigest()[:7].upper()
    return f"P{hash_hex}"


def calculate_quality_scores(episode_text: str) -> dict:
    """品質スコアを計算"""
    char_count = len(episode_text)
    scores = {
        "memorability_score": 8.5,
        "empathy_score": 7.5,
        "surprise_score": 8.0,
        "generation_quality_score": 8.5,
        "educational_value": 8.0,
        "story_quality": 8.5,
        "factual_density": 8.5,
    }
    if char_count < 150:
        for key in scores:
            scores[key] -= 1.0
    elif char_count > 300:
        for key in scores:
            scores[key] += 0.5
    scores["composite_score"] = sum(scores.values()) / len(scores) * 10
    return scores


def generate_teen_episode(
    person_name: str,
    category: str,
    person_type: str,
    age: int,
    award_name: Optional[str] = None,
    award_year: Optional[str] = None,
) -> Optional[dict]:
    """10代エピソードを生成"""

    print(f"\n{'=' * 70}")
    print(f"生成中: {person_name} ({age}歳) - {category}")
    if award_name:
        print(f"受賞: {award_name}" + (f" ({award_year}年)" if award_year else ""))
    print(f"{'=' * 70}")

    prompt = f"""あなたは、人物の人生における印象的なエピソードを生成する専門家です。

以下の人物について、**{age}歳のとき（10代）** の印象的なエピソードを日本語で生成してください。

人物名: {person_name}
カテゴリ: {category}
年齢: {age}歳（10代）"""

    if award_name:
        prompt += f"""
この時期の重要な出来事: {award_name}"""
        if award_year:
            prompt += f" ({award_year}年)"

    prompt += """

エピソードの要件:
1. 「あなたと同じ{age}歳のとき、{person_name}は〜」という形式で始める（ageは実際の数字に置換）
2. 10代特有の若さ、挑戦、成長を感じさせる内容
3. 具体的な事実や出来事を含める
4. 200-300文字程度
5. educational_valueのある内容
6. 事実に基づいた内容（架空の内容は避ける）
7. 若い読者が共感できる内容

注意: この人物の10代のエピソードが不明確な場合は、一般的に知られている事実に基づいて推測してください。

エピソードテキスト:"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=500,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}],
        )

        episode_text = message.content[0].text.strip()
        person_id = generate_person_id(person_name)
        scores = calculate_quality_scores(episode_text)

        # 年代を10代に設定
        nendai = "10代"

        # award_levelの決定
        award_level_value = ""
        if award_name:
            if "ノーベル" in award_name:
                award_level_value = "NOBEL"
            elif any(x in award_name for x in ["フィールズ", "プリツカー", "チューリング", "ラスカー"]):
                award_level_value = "INTERNATIONAL_TOP"
            elif any(x in award_name for x in ["アカデミー", "オスカー", "カンヌ", "グラミー"]):
                award_level_value = "INTERNATIONAL"
            elif any(x in award_name for x in ["オリンピック", "金メダル"]):
                award_level_value = "OLYMPIC"
            else:
                award_level_value = "AWARD"

        episode = {
            "episode_id": "",
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
            "is_group_member": False,
            "person_type": person_type,
            "quality_score": "",
            "年代": nendai,
            "source": "LLM_GENERATED",
            "tier": "",
            "week": "",
            "work_title": "",
            "generation_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fame_tier": "",
            "wikipedia_ja": "",
            "textbook": "",
            "award_level": award_level_value,
            "notoriety": "",
            "fame_score": 7.0,
            "composite_score": scores["composite_score"],
            "fame_score_updated_at": "",
            "episode_fame_tier": "",
            "episode_fame_score": 7.0,
            "episode_fame_score_updated_at": "",
            "人生の節目タグ": "若き挑戦",
            "memorability_score": scores["memorability_score"],
            "empathy_score": scores["empathy_score"],
            "surprise_score": scores["surprise_score"],
            "generation_quality_score": scores["generation_quality_score"],
            "educational_value": scores["educational_value"],
            "story_quality": scores["story_quality"],
            "factual_density": scores["factual_density"],
            "category_original": category,
            "historical_significance_score": "",
            "verifiability_score": "",
            "cultural_impact_score": "",
            "essential_insight_score": "",
            "temporal_permanence_score": "",
            "episode_importance_score": "",
            "is_highlight": "",
            "highlight_rank": "",
            "highlight_selection_method": "",
            "highlight": "",
        }

        print("✅ 生成成功")
        print(f"   文字数: {len(episode_text)}文字")
        print(f"   エピソード: {episode_text[:80]}...")

        return episode

    except Exception as e:
        print(f"❌ エラー: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="10代エピソードを生成")
    parser.add_argument("--template", default="templates/phase8_teen_batch1.csv", help="テンプレートCSVファイルパス")
    parser.add_argument("--output", default="generated/phase8_teen_episodes.csv", help="出力CSVファイルパス")
    parser.add_argument("--limit", type=int, help="生成数の上限")

    args = parser.parse_args()

    print("=" * 70)
    print("📝 Phase 8: 10代エピソード生成")
    print("=" * 70)
    print(f"テンプレート: {args.template}")
    print(f"出力先: {args.output}")
    print(f"生成上限: {args.limit if args.limit else '制限なし'}")
    print("=" * 70)

    # テンプレート読み込み
    try:
        with open(args.template, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            template_rows = list(reader)
    except FileNotFoundError:
        print(f"❌ テンプレートファイルが見つかりません: {args.template}")
        sys.exit(1)

    print(f"\nテンプレート読み込み: {len(template_rows)}件")

    if args.limit:
        template_rows = template_rows[: args.limit]
        print(f"生成数を{args.limit}件に制限")

    generated_episodes = []
    success_count = 0
    fail_count = 0

    for i, row in enumerate(template_rows, 1):
        person_name = row["person_name"]
        category = row["category"]
        person_type = row["person_type"]
        award_name = row.get("award_name", "")
        award_year = row.get("award_year", "")

        # 🔒 誤指令F-002修正: 生年/没年を考慮して年齢を選択
        birth_year_str = row.get("birth_year", "")
        death_year_str = row.get("death_year", "")

        birth_year = int(birth_year_str) if birth_year_str and str(birth_year_str).isdigit() else None
        death_year = int(death_year_str) if death_year_str and str(death_year_str).isdigit() else None

        print(f"\n[{i}/{len(template_rows)}] {person_name}")

        # 有効な年齢を取得
        age = get_valid_teen_age(person_name, birth_year, death_year, min_age=14, max_age=19)

        if age is None:
            print(f"⏭️  スキップ: {person_name}（14歳未到達）")
            fail_count += 1
            continue

        episode = generate_teen_episode(person_name, category, person_type, age, award_name, award_year)

        if episode:
            generated_episodes.append(episode)
            success_count += 1
        else:
            fail_count += 1

    print("\n" + "=" * 70)
    print("📊 生成結果")
    print("=" * 70)
    print(f"成功: {success_count}件")
    print(f"失敗: {fail_count}件")
    print(f"合計: {len(generated_episodes)}件")

    if generated_episodes:
        # 既存のCSVから列順を取得
        master_csv = "preserved/data/MASTER_EPISODES_CURRENT.csv"
        with open(master_csv, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames

        with open(args.output, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(generated_episodes)

        print(f"\n✅ 保存完了: {args.output}")
    else:
        print("\n⚠️  生成されたエピソードがありません")

    print("\n" + "=" * 70)
    print("完了")
    print("=" * 70)


if __name__ == "__main__":
    main()
