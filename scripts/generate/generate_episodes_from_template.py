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
import os
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import anthropic

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 年齢検証モジュールをインポート
try:
    from src.episode_age_validator import validate_episode_before_generation
    from src.birth_year_database import get_birth_year, get_max_valid_age

    AGE_VALIDATION_AVAILABLE = True
except ImportError:
    AGE_VALIDATION_AVAILABLE = False
    print("⚠️ 年齢検証モジュールが見つかりません。検証なしで続行します。")

# グループ名検証モジュールをインポート（品質ゲート）
try:
    from src.validators.person_name_validator import (
        validate_before_episode_generation as validate_person_name,
    )
    from src.group_master import is_group_entity, GROUP_MEMBER_MAP

    GROUP_VALIDATION_AVAILABLE = True
except ImportError:
    GROUP_VALIDATION_AVAILABLE = False
    print("⚠️ グループ名検証モジュールが見つかりません。検証なしで続行します。")

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
    """
    品質スコアを計算

    注意: 7軸スコアは生成時には空欄とし、Layer2で正式評価する。
    ここでは暫定的なcomposite_scoreのみ設定（後で上書きされる）。
    """
    # 7軸スコアは空欄（Layer2評価待ち）
    scores = {
        "memorability_score": "",
        "empathy_score": "",
        "surprise_score": "",
        "generation_quality_score": "",
        "educational_value": "",
        "story_quality": "",
        "factual_density": "",
    }

    # composite_scoreは暫定値（Layer2で再計算される）
    scores["composite_score"] = ""

    return scores


def generate_episode(
    person_name: str,
    category: str,
    person_type: str,
    award_name: Optional[str] = None,
    award_year: Optional[str] = None,
    work_title: Optional[str] = None,
    age: Optional[int] = None,
    group_name: Optional[str] = None,
    is_group_member: Optional[bool] = None,
) -> Optional[Dict]:
    """エピソードを生成"""

    print(f"\n{'='*80}")
    print(f"生成中: {person_name} ({category})")
    if person_type == "FICTIONAL" and work_title:
        print(f"作品: {work_title}")
    if award_name:
        print(f"受賞: {award_name}" + (f" ({award_year}年)" if award_year else ""))
    print(f"{'='*80}")

    # ===== 品質ゲート: グループ名チェック =====
    if GROUP_VALIDATION_AVAILABLE and person_type != "FICTIONAL":
        is_valid, message, suggested_fix = validate_person_name(person_name, person_type)
        if not is_valid:
            if suggested_fix:
                old_name = person_name
                person_name = suggested_fix["person_name"]
                if "group_name" in suggested_fix:
                    group_name = suggested_fix["group_name"]
                    is_group_member = suggested_fix.get("is_group_member", True)
                print(f"⚠️ グループ名修正: {old_name} → {person_name}")
                if group_name:
                    print(f"   グループ: {group_name}")
            else:
                print(f"❌ グループ名エラー（修正不可）: {message}")
                return None

        # 追加チェック: グループ名そのものがperson_nameの場合
        if is_group_entity(person_name):
            print(f"❌ グループ名が直接登録されています: {person_name}")
            print("   DISPERSION_RULESにルールを追加してください")
            return None

    # 年齢の決定と検証
    if age is None:
        if award_year and award_year.isdigit():
            age = random.randint(40, 65)
        else:
            age = random.randint(20, 70)

    # 未来エピソード検証（実在人物のみ）
    if AGE_VALIDATION_AVAILABLE and person_type == "REAL":
        is_valid, message, suggested_age = validate_episode_before_generation(
            person_name, age, person_type, strict_mode=False
        )
        if not is_valid:
            if suggested_age is not None:
                print(f"⚠️ 年齢調整: {age}歳 → {suggested_age}歳（{message}）")
                age = suggested_age
            else:
                print(f"❌ 検証エラー: {message}")
                return None
        else:
            birth_year = get_birth_year(person_name)
            if birth_year:
                max_age = get_max_valid_age(person_name)
                print(f"✅ 年齢検証OK: {person_name} {age}歳（生年{birth_year}年、最大{max_age}歳）")

    # 架空キャラクター用のプロンプト
    if person_type == "FICTIONAL" and work_title:
        prompt = f"""あなたは、架空キャラクターの作品世界内での印象的なエピソードを創作する専門家です。

以下の架空キャラクターについて、{age}歳のときの印象的なエピソードを日本語で生成してください。

【重要】このキャラクターは作品『{work_title}』の登場人物です。作品の世界観・設定を尊重しながら、キャラクターらしいエピソードを創作してください。「架空のキャラクターなので〜」「実在しないため〜」といったメタ的な説明は絶対に書かないでください。

キャラクター名: {person_name}
作品名: {work_title}
カテゴリ: {category}
年齢: {age}歳

エピソードの要件:
1. 「あなたと同じ{age}歳のとき、{person_name}は〜」という形式で必ず始める
2. 作品の世界観に沿った具体的なエピソードを創作する
3. キャラクターの性格や特徴を反映した内容にする
4. 200-300文字程度
5. 読者が感情移入できる印象的な内容にする
6. 「架空のキャラクター」「実在しない」などのメタ説明は絶対に含めない

エピソードテキスト:"""
    else:
        # 実在人物用のプロンプト
        prompt = f"""あなたは、人物の人生における印象的なエピソードを生成する専門家です。

以下の人物について、{age}歳のときの印象的なエピソードを日本語で生成してください。

人物名: {person_name}
カテゴリ: {category}
年齢: {age}歳"""

        # 受賞情報をプロンプトに追加
        if award_name:
            prompt += f"""
受賞した賞: {award_name}"""
            if award_year:
                prompt += f" ({award_year}年)"

        prompt += f"""

エピソードの要件:
1. 「あなたと同じ{age}歳のとき、{person_name}は〜」という形式で始める
2. **その年（{age}歳）に起きた出来事を主軸にする**（別年の出来事は最小限に）
3. 具体的な事実や出来事を含める
4. 記憶に残る印象的な内容にする
5. 200-300文字程度
6. educational_valueのある内容にする
7. 事実に基づいた内容にする（架空の内容は避ける）"""

        # 受賞エピソードの場合の追加要件
        if award_name:
            prompt += f"""
8. {award_name}受賞のエピソードを中心に生成する
9. 受賞時点の状況や心境を描く（長い経緯は避ける）
10. その年の出来事に集中し、別年の作品・受賞は言及しない"""

        prompt += "\n\nエピソードテキスト:"

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

        # award_levelの決定
        award_level_value = ""
        if award_name:
            if "ノーベル" in award_name:
                award_level_value = "NOBEL"
            elif any(x in award_name for x in ["フィールズ", "プリツカー", "チューリング", "ラスカー"]):
                award_level_value = "INTERNATIONAL_TOP"
            elif any(
                x in award_name
                for x in [
                    "アカデミー",
                    "オスカー",
                    "カンヌ",
                    "ベルリン",
                    "ベネチア",
                    "グラミー",
                    "エミー",
                ]
            ):
                award_level_value = "INTERNATIONAL"
            elif any(x in award_name for x in ["直木", "芥川", "日本アカデミー", "文化勲章"]):
                award_level_value = "NATIONAL"
            elif any(x in award_name for x in ["オリンピック", "金メダル"]):
                award_level_value = "OLYMPIC"
            else:
                award_level_value = "AWARD"

        # 人生の節目タグ
        milestone_tags = "受賞" if award_name else ""

        # グループメンバー情報を取得（まだ設定されていなければ）
        if group_name is None and GROUP_VALIDATION_AVAILABLE:
            if person_name in GROUP_MEMBER_MAP:
                group_name = GROUP_MEMBER_MAP[person_name]
                is_group_member = True

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
            "group_name": group_name if group_name else "",
            "is_group_member": is_group_member if is_group_member is not None else "",
            "person_type": person_type,
            "quality_score": "",
            "slot": "",
            "source": "",
            "tier": "",
            "week": "",
            "work_title": work_title if work_title else "",
            "generation_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fame_tier": "",
            "wikipedia_ja": "",
            "textbook": "",
            "award_level": award_level_value,
            "notoriety": "",
            "fame_score": 70.0,
            "composite_score": scores["composite_score"],
            "fame_score_updated_at": "",
            "人生の節目タグ": milestone_tags,
            "memorability_score": scores["memorability_score"],
            "empathy_score": scores["empathy_score"],
            "surprise_score": scores["surprise_score"],
            "generation_quality_score": scores["generation_quality_score"],
            "educational_value": scores["educational_value"],
            "story_quality": scores["story_quality"],
            "factual_density": scores["factual_density"],
            "category_original": category,
        }

        print("✅ 生成成功")
        print(f"   文字数: {len(episode_text)}文字")
        print("   ステータス: Layer2評価待ち")
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
        person_type = row.get("person_type", "REAL")
        award_name = row.get("award_name", "")  # オプションカラム
        award_year = row.get("award_year", "")  # オプションカラム
        work_title = row.get("work_title", "")  # 架空キャラ用
        age_str = row.get("age", "")
        age = int(float(age_str)) if age_str and age_str.replace(".", "").isdigit() else None

        print(f"\n[{i}/{len(template_rows)}] {person_name}")

        episode = generate_episode(
            person_name,
            category,
            person_type,
            award_name,
            award_year,
            work_title=work_title if work_title else None,
            age=age,
        )

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
            "memorability_score",
            "empathy_score",
            "surprise_score",
            "generation_quality_score",
            "educational_value",
            "story_quality",
            "factual_density",
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
