#!/usr/bin/env python3
"""
象徴的業績エピソード追加スクリプト

4件の象徴的業績エピソードを追加:
1. 黒澤明 (40歳): 羅生門がヴェネツィア国際映画祭で金獅子賞を受賞（1950年）
2. クリストファー・コロンブス (41歳): スペイン女王イザベル1世から西方航海の支援を獲得（1492年）
3. イチロー (27歳): MLBシーズンで新人王とMVPを同時受賞する偉業達成（2001年）
4. 手塚治虫 (45歳): 週刊少年チャンピオンでブラック・ジャックの連載を開始（1973年）

Usage:
    python scripts/fix/add_iconic_achievements.py --dry-run  # 確認のみ
    python scripts/fix/add_iconic_achievements.py --execute  # 実行
"""

import argparse
import logging
import random
import string
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.sage.config import MASTER_CSV
from scripts.score.super_total_scorer import SuperTotalScorer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def generate_episode_id() -> str:
    """ユニークなepisode_idを生成"""
    timestamp = datetime.now().strftime("%y%m%d%H%M%S")
    random_suffix = "".join(random.choices(string.digits + string.ascii_uppercase, k=6))
    return f"EP-{timestamp}{random_suffix}"


def get_person_metadata(df: pd.DataFrame, person_id: str) -> dict:
    """人物のメタ情報を取得"""
    person_rows = df[df["person_id"] == person_id]
    if person_rows.empty:
        return {}

    row = person_rows.iloc[0]
    return {
        "person_id": person_id,
        "person_name": row.get("person_name", ""),
        "fame_tier": row.get("fame_tier"),
        "celebrity_score_v2": row.get("celebrity_score_v2"),
        "fame_score_v3": row.get("fame_score_v3"),
        "fame_rank_v3": row.get("fame_rank_v3"),
        "category": row.get("category", ""),
        "person_type": row.get("person_type", "REAL"),
        "is_japanese": row.get("is_japanese"),
        "birth_year": row.get("birth_year"),
        "death_year": row.get("death_year"),
    }


def check_duplicate(df: pd.DataFrame, person_id: str, age: int) -> bool:
    """同一年齢重複チェック"""
    existing = df[(df["person_id"] == person_id) & (df["age"] == age)]
    return len(existing) > 0


def calculate_episode_fame_v6(row: dict) -> float:
    """episode_fame_v6を計算"""
    scores = [
        row.get("memorability_score"),
        row.get("empathy_score"),
        row.get("surprise_score"),
        row.get("generation_quality_score"),
        row.get("educational_value"),
        row.get("storytelling_quality"),
        row.get("factual_density"),
    ]
    valid_scores = []
    for s in scores:
        if s is not None and not pd.isna(s):
            try:
                valid_scores.append(float(s))
            except (ValueError, TypeError):
                pass
    if not valid_scores:
        return 0.0

    avg = sum(valid_scores) / len(valid_scores)
    fame_v3_raw = row.get("fame_score_v3", 0) or 0
    fame_v3 = float(fame_v3_raw) if fame_v3_raw else 0
    bonus = fame_v3 / 100 if fame_v3 > 0 else 0

    return float(round(avg * 10 + bonus, 2))


def calculate_episode_fame_tier_v6(fame_v6: float) -> int:
    """episode_fame_tier_v6を算出"""
    if fame_v6 >= 90:
        return 5
    elif fame_v6 >= 80:
        return 4
    elif fame_v6 >= 70:
        return 3
    elif fame_v6 >= 60:
        return 2
    else:
        return 1


# 追加するエピソード定義
ICONIC_EPISODES = [
    {
        "person_id": "PBC4ECE7",  # 黒澤明
        "age": 40,
        "episode_text": (
            "あなたと同じ40歳のとき、黒澤明は映画『羅生門』でヴェネツィア国際映画祭金獅子賞を受賞し、"
            "日本映画を初めて世界に知らしめた。1950年、戦後わずか5年で、黒澤は芥川龍之介の短編を原作に、"
            "人間の本質に迫る革新的な物語構成と斬新な撮影技法で世界の映画人を驚愕させた。"
            "森の中での雨のシーンでは、フィルムに映りやすくするため墨汁を混ぜた水を降らせ、"
            "木漏れ日を直接カメラに捉える前代未聞の手法を編み出した。"
            "受賞の知らせが届いた時、黒澤は次回作の準備に没頭しており、「まだ道半ばだ」と静かに語った。"
            "この受賞が、三船敏郎という不世出の俳優とともに、日本映画の黄金時代を切り拓く出発点となった。"
        ),
        "episode_type": "達成",
        "category": "映画・演劇",
        "source": "ICONIC_ACHIEVEMENT_MANUAL",
        "iconic_score": 10.0,
        "axis_scores": {
            "memorability_score": 9.5,
            "empathy_score": 8.5,
            "surprise_score": 9.0,
            "generation_quality_score": 9.0,
            "educational_value": 9.0,
            "storytelling_quality": 9.0,
            "factual_density": 9.5,
        },
        "episode_importance_score": 95.0,
    },
    {
        "person_id": "P6602989",  # クリストファー・コロンブス
        "age": 41,
        "episode_text": (
            "あなたと同じ41歳のとき、クリストファー・コロンブスはスペイン女王イザベル1世から西方航海の支援を獲得した。"
            "1492年4月17日、グラナダ陥落の熱狂が冷めやらぬ中、コロンブスは8年間の執念の交渉を実らせ、"
            "「サンタ・フェ協定」に署名を得た。ポルトガル、イギリス、フランスに断られ続けた壮大な計画が、"
            "ついに王室の後ろ盾を得たのだ。彼は「海の提督」の称号と、発見した土地の総督権、"
            "そして利益の10分の1を獲得する権利を勝ち取った。"
            "8月3日、パロス港から3隻の船団を率いて出港。2ヶ月余りの航海の末、10月12日に新大陸に到達した。"
            "この一人の男の不屈の執念が、人類史の流れを永遠に変えた。"
        ),
        "episode_type": "達成",
        "category": "探検・冒険",
        "source": "ICONIC_ACHIEVEMENT_MANUAL",
        "iconic_score": 10.0,
        "axis_scores": {
            "memorability_score": 9.5,
            "empathy_score": 8.5,
            "surprise_score": 9.5,
            "generation_quality_score": 9.0,
            "educational_value": 9.5,
            "storytelling_quality": 9.0,
            "factual_density": 9.5,
        },
        "episode_importance_score": 98.0,
    },
    {
        "person_id": "PD7F00A6",  # イチロー
        "age": 27,
        "episode_text": (
            "あなたと同じ27歳のとき、イチローはMLB史上初となる新人王とMVPの同時受賞という偉業を達成した。"
            "2001年、日本球界から海を渡ったイチローは、シアトル・マリナーズで242安打を放ち、"
            "打率.350、56盗塁でアメリカン・リーグを席巻した。「振り子打法」と呼ばれる独自のバッティングスタイルは、"
            "当初メジャーでは通用しないと懐疑的に見られたが、イチローはその予測を完全に覆した。"
            "新人として球宴のファン投票1位を獲得し、シーズン終了後には両タイトルの栄冠に輝いた。"
            "記者会見で「まだ始まったばかり」と語った彼の言葉通り、その後も19年間にわたりMLBで活躍を続け、"
            "通算3,089安打を記録。アジア出身選手の可能性を世界に証明した歴史的なシーズンだった。"
        ),
        "episode_type": "達成",
        "category": "スポーツ",
        "source": "ICONIC_ACHIEVEMENT_MANUAL",
        "iconic_score": 10.0,
        "axis_scores": {
            "memorability_score": 9.5,
            "empathy_score": 9.0,
            "surprise_score": 9.0,
            "generation_quality_score": 9.0,
            "educational_value": 8.5,
            "storytelling_quality": 9.0,
            "factual_density": 9.5,
        },
        "episode_importance_score": 92.0,
    },
    {
        "person_id": "P81F556E",  # 手塚治虫
        "age": 45,
        "episode_text": (
            "あなたと同じ45歳のとき、手塚治虫は週刊少年チャンピオンで『ブラック・ジャック』の連載を開始した。"
            "1973年、虫プロダクションの倒産から2年、業界では「手塚時代は終わった」と囁かれていた。"
            "しかし彼は人気投票で最下位からスタートした医療漫画で、圧倒的な復活を遂げた。"
            "無免許の天才外科医が法外な手術料で命を救う物語は、従来の少年漫画の常識を覆し、"
            "生命の尊厳と医療倫理という重いテーマを少年誌で描くという革新をもたらした。"
            "連載開始から1年後には人気投票1位を獲得。「漫画の神様」の復活は、日本漫画界に新たな可能性を示した。"
            "この作品は5年間で約230話が連載され、医療漫画というジャンルを確立した金字塔となった。"
        ),
        "episode_type": "達成",
        "category": "アニメ・漫画・ゲーム",
        "source": "ICONIC_ACHIEVEMENT_MANUAL",
        "iconic_score": 9.5,
        "axis_scores": {
            "memorability_score": 9.0,
            "empathy_score": 9.0,
            "surprise_score": 8.5,
            "generation_quality_score": 9.0,
            "educational_value": 9.0,
            "storytelling_quality": 9.0,
            "factual_density": 9.0,
        },
        "episode_importance_score": 88.0,
    },
]


def create_episode_row(df: pd.DataFrame, episode_def: dict, all_columns: list) -> dict:
    """エピソード行を作成"""
    person_meta = get_person_metadata(df, episode_def["person_id"])

    if not person_meta:
        logger.error(f"人物ID {episode_def['person_id']} が見つかりません")
        return {}

    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    # 8軸スコア
    axis_scores = episode_def["axis_scores"]

    # composite_score計算（7軸平均 * 100）
    axis_values = list(axis_scores.values())
    composite_score = round(sum(axis_values) / len(axis_values) * 100, 1)

    # fame_score_v3を取得
    fame_score_v3 = person_meta.get("fame_score_v3", 500)
    if pd.isna(fame_score_v3):
        fame_score_v3 = 500

    # 新規行を作成
    row = {col: "" for col in all_columns}

    # 基本情報
    row["episode_id"] = generate_episode_id()
    row["person_id"] = episode_def["person_id"]
    row["person_name"] = person_meta.get("person_name", "")
    row["age"] = episode_def["age"]
    row["category"] = episode_def["category"]
    row["episode_text"] = episode_def["episode_text"]
    row["episode_type"] = episode_def["episode_type"]
    row["person_type"] = person_meta.get("person_type", "REAL")
    row["source"] = episode_def["source"]
    row["generation_timestamp"] = timestamp
    row["generated_at"] = timestamp
    row["verification_status"] = "unverified"

    # 人物メタ情報
    row["fame_tier"] = str(person_meta.get("fame_tier", 4))
    row["celebrity_score_v2"] = str(person_meta.get("celebrity_score_v2", 500))
    row["fame_score_v3"] = str(fame_score_v3)
    row["fame_rank_v3"] = str(person_meta.get("fame_rank_v3", 1000))
    row["is_japanese"] = str(person_meta.get("is_japanese", True))
    birth_year = person_meta.get("birth_year")
    death_year = person_meta.get("death_year")
    row["birth_year"] = str(birth_year) if birth_year is not None else ""
    row["death_year"] = str(death_year) if death_year is not None else ""

    # 8軸スコア
    for key, value in axis_scores.items():
        row[key] = str(value)

    # その他のスコア
    row["composite_score"] = str(composite_score)
    row["episode_importance_score"] = str(episode_def["episode_importance_score"])
    row["iconic_score"] = str(episode_def["iconic_score"])

    # episode_fame_v6とtierを計算
    episode_fame_v6 = calculate_episode_fame_v6(row)
    row["episode_fame_v6"] = str(episode_fame_v6)
    row["episode_fame_tier_v6"] = str(calculate_episode_fame_tier_v6(episode_fame_v6))
    row["episode_fame_v6_updated_at"] = timestamp

    # 感情インパクト（empathy + surprise の平均）
    row["感情インパクト"] = str(round((axis_scores["empathy_score"] + axis_scores["surprise_score"]) / 2, 1))

    # 総合品質（7軸平均）
    row["総合品質"] = str(round(sum(axis_values) / len(axis_values), 2))

    # composite_score_5axis（後方互換）
    row["composite_score_5axis"] = str(
        round(
            (
                axis_scores["memorability_score"]
                + axis_scores["empathy_score"]
                + axis_scores["surprise_score"]
                + axis_scores["generation_quality_score"]
                + axis_scores["educational_value"]
            )
            / 5
            * 10,
            2,
        )
    )

    return row


def main():
    parser = argparse.ArgumentParser(description="象徴的業績エピソードを追加")
    parser.add_argument("--dry-run", action="store_true", help="ドライランモード")
    parser.add_argument("--execute", action="store_true", help="実行モード")
    parser.add_argument(
        "--csv",
        type=str,
        default=str(MASTER_CSV),
        help="対象CSVファイル",
    )
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        parser.error("--dry-run または --execute のいずれかを指定してください")

    logger.info(f"Loading CSV: {args.csv}")
    df = pd.read_csv(args.csv, encoding="utf-8-sig", low_memory=False)
    logger.info(f"Total episodes: {len(df)}")

    all_columns = list(df.columns)

    # 追加するエピソードを処理
    episodes_to_add = []

    print("\n" + "=" * 70)
    print("象徴的業績エピソード追加")
    print("=" * 70)

    for ep_def in ICONIC_EPISODES:
        person_id = str(ep_def["person_id"])
        age_value = ep_def["age"]
        age = int(age_value) if isinstance(age_value, (int, float, str)) else 0
        person_meta = get_person_metadata(df, person_id)
        person_name = person_meta.get("person_name", "不明")

        print(f"\n[{person_name} ({age}歳)]")
        print(f"  person_id: {person_id}")

        # 重複チェック
        if check_duplicate(df, person_id, age):
            print(f"  ⚠️ 警告: {person_name} {age}歳のエピソードは既に存在します")
            print("  → スキップします")
            continue

        print("  ✓ 重複なし: 追加可能")

        # エピソード行を作成
        new_row = create_episode_row(df, ep_def, all_columns)
        if not new_row:
            continue

        # super_total_scoreを計算
        episodes_list = df.to_dict("records")
        scorer = SuperTotalScorer(episodes_list)
        result = scorer.calculate(new_row)
        new_row["super_total_score"] = result.score

        episodes_to_add.append(new_row)

        print(f"  episode_id: {new_row['episode_id']}")
        print(f"  iconic_score: {new_row['iconic_score']}")
        print(f"  episode_fame_v6: {new_row['episode_fame_v6']}")
        print(f"  super_total_score: {new_row['super_total_score']:,.0f}")
        print(f"  テキスト: {new_row['episode_text'][:80]}...")

    print("\n" + "-" * 70)
    print(f"追加対象: {len(episodes_to_add)}件")

    if not episodes_to_add:
        print("\n追加するエピソードはありません")
        return

    if args.dry_run:
        print("\n[dry-run] 実行モードで --execute を指定すると追加されます")
        return

    # 実行モード
    if args.execute:
        # バックアップ作成（シンプルな方式）
        import shutil

        csv_path = Path(args.csv)
        backup_dir = csv_path.parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        backup_name = f"{csv_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_pre_iconic.csv"
        backup_path = backup_dir / backup_name
        shutil.copy2(csv_path, backup_path)
        logger.info(f"Backup created: {backup_path}")

        # エピソード追加
        new_rows_df = pd.DataFrame(episodes_to_add)
        df = pd.concat([df, new_rows_df], ignore_index=True)

        # 保存
        df.to_csv(args.csv, index=False, encoding="utf-8-sig")
        logger.info(f"Saved: {args.csv}")

        print("\n" + "=" * 70)
        print(f"✓ {len(episodes_to_add)}件のエピソードを追加しました")
        print("=" * 70)


if __name__ == "__main__":
    main()
