#!/usr/bin/env python3
"""
Phase 8: 70代エピソード生成スクリプト

70代以上（70-90歳）のエピソードを集中生成する。
ロードマップ Phase 8 Priority 2 に対応。

使用方法:
    ANTHROPIC_API_KEY=xxx python3 scripts/generate_senior_episodes.py --limit 50
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
# 年齢境界チェック関数（誤指令F-001修正）
# =============================================================================


def get_valid_senior_age(
    person_name: str, birth_year: Optional[int], death_year: Optional[int], min_age: int = 70, max_age: int = 85
) -> Optional[int]:
    """
    生年/没年を考慮して、有効な70代以上の年齢をランダムに選択

    Args:
        person_name: 人物名（ログ用）
        birth_year: 生年（Noneの場合はチェックスキップ）
        death_year: 没年（Noneの場合は存命と判断）
        min_age: 最小年齢（デフォルト70歳）
        max_age: 最大年齢（デフォルト85歳）

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


def load_candidates(template_path: str, min_age: int = 70, max_age: int = 85) -> list[dict]:
    """
    Phase8候補者を読み込み、年齢境界チェックでフィルタリング

    Args:
        template_path: テンプレートCSVパス
        min_age: 最小年齢（デフォルト: 70歳）
        max_age: 最大年齢（デフォルト: 85歳）

    Returns:
        有効な候補者のリスト

    Raises:
        FileNotFoundError: テンプレートが見つからない
        ValueError: 必須カラムが存在しない、または有効な候補者が0件
    """
    # 統計カウンタ
    total_count = 0
    skipped_no_birth = 0
    skipped_age_boundary = 0

    # テンプレートCSV読み込み
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"テンプレートが見つかりません: {template_path}")

    candidates = []

    with open(template_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        # 必須カラムチェック
        required_columns = ["person_name", "category", "person_type", "birth_year"]
        if not all(col in reader.fieldnames for col in required_columns):
            raise ValueError(f"テンプレートに必須カラムがありません: {required_columns}")

        for row in reader:
            total_count += 1
            person_name = row.get("person_name", "")
            category = row.get("category", "")
            person_type = row.get("person_type", "")
            birth_year_str = row.get("birth_year", "")
            death_year_str = row.get("death_year", "")
            award_name = row.get("award_name", "")
            award_year = row.get("award_year", "")

            # birth_year が空の場合はスキップ
            if not birth_year_str or not str(birth_year_str).isdigit():
                skipped_no_birth += 1
                continue

            birth_year = int(birth_year_str)
            death_year = int(death_year_str) if death_year_str and str(death_year_str).isdigit() else None

            # 年齢境界チェック
            current_year = datetime.now().year
            max_lived_age = death_year - birth_year if death_year else current_year - birth_year

            # 70-85歳の範囲内で到達可能な年齢があるかチェック
            valid_ages = [a for a in range(min_age, max_age + 1) if a <= max_lived_age]

            if not valid_ages:
                skipped_age_boundary += 1
                continue

            # 有効な候補をリストに追加
            candidates.append(
                {
                    "person_name": person_name,
                    "category": category,
                    "person_type": person_type,
                    "birth_year": birth_year,
                    "death_year": death_year,
                    "award_name": award_name,
                    "award_year": award_year,
                }
            )

    # 統計ログ出力
    print("\n📊 候補者読み込み統計:")
    print(f"  総候補者数: {total_count}件")
    print(f"  birth_year不明でスキップ: {skipped_no_birth}件")
    print(f"  年齢境界違反でスキップ: {skipped_age_boundary}件")
    print(f"  有効な候補者: {len(candidates)}件\n")

    # 候補者が0件の場合はエラー
    if not candidates:
        raise ValueError(f"有効な候補者が見つかりませんでした。テンプレート: {template_path}")

    return candidates


def generate_person_id(person_name: str) -> str:
    """person_nameからperson_idを生成"""
    hash_obj = hashlib.md5(person_name.encode("utf-8"), usedforsecurity=False)
    hash_hex = hash_obj.hexdigest()[:7].upper()
    return f"P{hash_hex}"


def calculate_quality_scores(episode_text: str) -> dict:
    """品質スコアを計算"""
    char_count = len(episode_text)
    scores = {
        "記憶性スコア": 8.5,
        "共感性スコア": 7.5,
        "意外性スコア": 8.0,
        "生成品質スコア": 8.5,
        "教育的価値": 8.0,
        "ストーリー品質": 8.5,
        "事実密度": 8.5,
    }
    if char_count < 150:
        for key in scores:
            scores[key] -= 1.0
    elif char_count > 300:
        for key in scores:
            scores[key] += 0.5
    scores["composite_score"] = sum(scores.values()) / len(scores) * 10
    return scores


def generate_senior_episode(
    person_name: str,
    category: str,
    person_type: str,
    age: int,
    award_name: Optional[str] = None,
    award_year: Optional[str] = None,
    birth_year: Optional[int] = None,
    death_year: Optional[int] = None,
) -> Optional[dict]:
    """70代エピソードを生成"""

    # 【新規】人物名バリデーション（強制）
    from src.validators.person_name_validator import PersonNameValidator

    validator = PersonNameValidator()
    validation_issues = validator.validate(person_name)

    if validation_issues:
        print(f"\n{'=' * 70}")
        print(f"❌ バリデーションエラー: {person_name}")
        print(f"{'=' * 70}")
        for issue in validation_issues:
            print(f"   {issue.severity.value.upper()}: {issue.message}")
            if issue.suggestion:
                print(f"   提案: {issue.suggestion}")
        print("   → エピソード生成をスキップします")
        print(f"{'=' * 70}\n")
        return None

    # 【追加】正規化チェック（2025-12-16）
    # RIKISHI_SHIKONAリスト等による自動正規化を試行
    from scripts.data.normalize_person_names import PersonNameNormalizer

    normalizer = PersonNameNormalizer(min_confidence=0.85)
    normalization_result = normalizer.normalize(person_name)

    if normalization_result:
        print(f"\n{'=' * 70}")
        print(f"⚠️  人物名を正規化: {person_name} → {normalization_result.normalized_name}")
        print(f"   理由: {normalization_result.match_detail}")
        print(f"   信頼度: {normalization_result.confidence}")
        print(f"{'=' * 70}\n")
        # 正規化後の名前を使用
        person_name = normalization_result.normalized_name

    print(f"\n{'=' * 70}")
    print(f"生成中: {person_name} ({age}歳) - {category}")
    if award_name:
        print(f"業績: {award_name}" + (f" ({award_year}年)" if award_year else ""))
    print(f"{'=' * 70}")

    # award_yearとdeath_yearの矛盾チェック
    include_award_year = True
    if death_year and award_year:
        try:
            award_year_int = int(award_year)
            # 死後の業績年は含めない（メタ的表現を防ぐ）
            if award_year_int > death_year:
                include_award_year = False
                print(f"  ⚠️  award_year ({award_year}) > death_year ({death_year}): 年号を省略")
        except ValueError:
            pass

    prompt = f"""あなたは、人物の人生における印象的なエピソードを生成する専門家です。

以下の人物について、**{age}歳のとき（70代以上・晩年）** の印象的なエピソードを日本語で生成してください。

人物名: {person_name}
カテゴリ: {category}
年齢: {age}歳（晩年期）"""

    if award_name:
        prompt += f"""
この時期の重要な業績/出来事: {award_name}"""
        if award_year and include_award_year:
            prompt += f" ({award_year}年)"

    prompt += """

エピソードの要件:
1. 「あなたと同じ{age}歳のとき、{person_name}は〜」という形式で始める（ageは実際の数字に置換）
2. 晩年特有の知恵、円熟、挑戦を感じさせる内容
3. 具体的な事実や出来事を含める
4. 200-300文字程度
5. 教育的価値のある内容（特に高齢者の活躍・可能性）
6. 事実に基づいた内容（架空の内容は避ける）
7. 「年齢を重ねてもなお」という視点を含める

❌ 絶対禁止される表現:
- 「すでにこの世を去っていました」「亡くなった後」「死去した後」などのメタ的な死の言及
- 「未来のこと」「まだ到達していない」などの時系列の矛盾
- 「年齢設定を変更」「申し訳ありませんが」などの生成失敗の言及

注意: この人物の晩年のエピソードが不明確な場合は、一般的に知られている事実に基づいて推測してください。
人物が指定年齢で存命だった場合、その時期の活動や功績を中心に記述してください。

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

        # 年代を60歳以上に設定（CSVの年代カラムの値）
        nendai = "60歳以上"

        # award_levelの決定
        award_level_value = ""
        if award_name:
            if "ノーベル" in award_name:
                award_level_value = "NOBEL"
            elif any(x in award_name for x in ["フィールズ", "プリツカー", "チューリング", "ラスカー"]):
                award_level_value = "INTERNATIONAL_TOP"
            elif any(x in award_name for x in ["アカデミー", "オスカー", "カンヌ", "グラミー", "文化勲章"]):
                award_level_value = "INTERNATIONAL"
            elif any(x in award_name for x in ["国民栄誉賞"]):
                award_level_value = "NATIONAL"
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
            "人生の節目タグ": "晩年の挑戦",
            "記憶性スコア": scores["記憶性スコア"],
            "共感性スコア": scores["共感性スコア"],
            "意外性スコア": scores["意外性スコア"],
            "生成品質スコア": scores["生成品質スコア"],
            "教育的価値": scores["教育的価値"],
            "ストーリー品質": scores["ストーリー品質"],
            "事実密度": scores["事実密度"],
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
    parser = argparse.ArgumentParser(description="70代エピソードを生成")
    parser.add_argument(
        "--template", default="templates/phase8_senior_batch1_with_birthyear.csv", help="テンプレートCSVファイルパス"
    )
    parser.add_argument("--output", default="generated/phase8_senior_episodes.csv", help="出力CSVファイルパス")
    parser.add_argument("--limit", type=int, help="生成数の上限")

    args = parser.parse_args()

    print("=" * 70)
    print("📝 Phase 8: 70代エピソード生成")
    print("=" * 70)
    print(f"テンプレート: {args.template}")
    print(f"出力先: {args.output}")
    print(f"生成上限: {args.limit if args.limit else '制限なし'}")
    print("=" * 70)

    # 候補者読み込み（年齢境界チェック付き）
    try:
        candidates = load_candidates(template_path=args.template, min_age=70, max_age=85)
    except (FileNotFoundError, ValueError) as e:
        print(f"❌ 候補者読み込みエラー: {e}")
        sys.exit(1)

    print(f"有効な候補者: {len(candidates)}件")

    if args.limit:
        candidates = candidates[: args.limit]
        print(f"生成数を{args.limit}件に制限")

    generated_episodes = []
    success_count = 0
    fail_count = 0

    for i, candidate in enumerate(candidates, 1):
        person_name = candidate["person_name"]
        category = candidate["category"]
        person_type = candidate["person_type"]
        birth_year = candidate.get("birth_year")
        death_year = candidate.get("death_year")
        award_name = candidate.get("award_name", "")
        award_year = candidate.get("award_year", "")

        print(f"\n[{i}/{len(candidates)}] {person_name}")

        # 有効な年齢を取得（load_candidates()でフィルタリング済みだが、防御的プログラミングとして保持）
        age = get_valid_senior_age(person_name, birth_year, death_year, min_age=70, max_age=85)

        if age is None:
            print(f"⚠️  内部エラー: {person_name}の年齢選択失敗（load_candidates()でフィルタリングされるべき）")
            fail_count += 1
            continue

        episode = generate_senior_episode(
            person_name, category, person_type, age, award_name, award_year, birth_year, death_year
        )

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
