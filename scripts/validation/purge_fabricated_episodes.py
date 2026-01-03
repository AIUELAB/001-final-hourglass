#!/usr/bin/env python3
"""
捏造エピソード削除スクリプト

以下の問題エピソードを検出・削除:
1. 実在人物の架空未来エピソード（現在年齢+5歳以上）
2. 死亡後の架空エピソード
3. 埋め草パターンが多く具体的事実が少ないエピソード
4. SURPRISE_IMPROVED源で捏造の可能性が高いもの
"""

import csv
import json
import shutil
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
CSV_PATH = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
BACKUP_PATH = (
    PROJECT_ROOT / f"preserved/data/MASTER_EPISODES_CURRENT.csv.bak_purge_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
)
REPORT_PATH = PROJECT_ROOT / "src/reports/purge_fabricated_report.json"

CURRENT_YEAR = 2026

# 既知の人物データ（生年・没年）
KNOWN_PEOPLE = {
    # スポーツ
    "大谷翔平": {"birth": 1994},
    "羽生結弦": {"birth": 1994},
    "藤井聡太": {"birth": 2002},
    "イチロー": {"birth": 1973},
    "松井秀喜": {"birth": 1974},
    "浅田真央": {"birth": 1990},
    "錦織圭": {"birth": 1989},
    # 芸能人・死亡済み
    "志村けん": {"birth": 1950, "death": 2020},
    "坂本龍一": {"birth": 1952, "death": 2023},
    "鳥山明": {"birth": 1955, "death": 2024},
    "ジャニー喜多川": {"birth": 1931, "death": 2019},
    # 音楽・芸術
    "久石譲": {"birth": 1950},
    "エルトン・ジョン": {"birth": 1947},
    "ポール・マッカートニー": {"birth": 1942},
    "ミック・ジャガー": {"birth": 1943},
    # 文化人
    "村上春樹": {"birth": 1949},
    "養老孟司": {"birth": 1937},
    # 歴史上の人物
    "湯川秀樹": {"birth": 1907, "death": 1981},
    "川端康成": {"birth": 1899, "death": 1972},
    "梅棹忠夫": {"birth": 1920, "death": 2010},
}

# 埋め草パターン
FILLER_PATTERNS = [
    "続けていました",
    "行っていました",
    "取り組んでいました",
    "貫いていました",
    "示していました",
    "教えてくれます",
    "体現し",
    "創作活動を行",
    "活動を続けて",
    "挑戦を続けて",
    "ペースで",
    "姿勢を",
    "信念を",
    "次世代の育成",
    "助言者として",
    "還元する",
    "境地にあり",
    "円熟の",
    "精力的に",
    "なお現役",
]

# 具体的事実パターン
CONCRETE_PATTERNS = [
    "発表",
    "発売",
    "受賞",
    "優勝",
    "記録",
    "達成",
    "完成",
    "出版",
    "公開",
    "デビュー",
    "初",
    "金メダル",
    "銀メダル",
    "銅メダル",
    "賞を",
    "に選ばれ",
    "に就任",
    "を設立",
    "を創業",
    "億円",
    "億部",
    "万部",
    "万枚",
    "万人",
]

# 捏造表現パターン（架空の出来事を示唆）
FABRICATION_PATTERNS = [
    "養蜂業",
    "農業を始め",
    "突然現役引退",
    "周囲の猛反対を押し切",
    "意外にも",
    "予想外",
    "衝撃的な告白",
    "コラボレーション",
    "AIと",
    "過疎地域で",
]


def is_future_episode(person_name: str, age: float) -> tuple[bool, str]:
    """未来のエピソードかどうか判定"""
    if person_name not in KNOWN_PEOPLE:
        return False, ""

    data = KNOWN_PEOPLE[person_name]
    birth = data["birth"]
    death = data.get("death")

    episode_year = birth + int(age)

    # 死亡後のエピソード
    if death and episode_year > death:
        return True, f"死亡({death}年)後のエピソード({episode_year}年)"

    # 未来のエピソード（現在年+2年以上先）
    if episode_year > CURRENT_YEAR + 2:
        current_age = CURRENT_YEAR - birth
        return True, f"未来({episode_year}年)、現在{current_age}歳"

    return False, ""


def is_filler_episode(text: str) -> tuple[bool, int, int]:
    """埋め草エピソードか判定"""
    filler_count = sum(1 for p in FILLER_PATTERNS if p in text)
    concrete_count = sum(1 for p in CONCRETE_PATTERNS if p in text)

    # 埋め草パターン3以上、具体的事実2未満
    is_filler = filler_count >= 3 and concrete_count < 2
    return is_filler, filler_count, concrete_count


def is_fabricated_episode(text: str, source: str) -> tuple[bool, str]:
    """捏造エピソードか判定"""
    if "SURPRISE_IMPROVED" not in source:
        return False, ""

    for pattern in FABRICATION_PATTERNS:
        if pattern in text:
            return True, f"SURPRISE_IMPROVED + 捏造パターン「{pattern}」"

    return False, ""


def detect_and_purge(dry_run: bool = True) -> dict:
    """問題エピソードを検出して削除"""

    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    original_count = len(rows)

    episodes_to_delete = []
    report = {
        "analyzed_at": datetime.now().isoformat(),
        "dry_run": dry_run,
        "original_count": original_count,
        "categories": {
            "future_episodes": [],
            "post_death_episodes": [],
            "filler_episodes": [],
            "fabricated_episodes": [],
        },
        "deleted_count": 0,
    }

    for i, row in enumerate(rows):
        episode_id = row.get("episode_id", "")
        person_name = row.get("person_name", "")
        person_type = row.get("person_type", "")
        text = row.get("episode_text", "")
        source = row.get("source", "")

        try:
            age = float(row.get("age", 0))
        except (ValueError, TypeError):
            age = 0

        delete_reason = None
        category = None

        # 実在人物のみチェック
        if person_type == "REAL":
            # 未来・死亡後エピソード
            is_future, future_reason = is_future_episode(person_name, age)
            if is_future:
                if "死亡" in future_reason:
                    category = "post_death_episodes"
                else:
                    category = "future_episodes"
                delete_reason = future_reason

            # 捏造エピソード
            if not delete_reason:
                is_fab, fab_reason = is_fabricated_episode(text, source)
                if is_fab:
                    category = "fabricated_episodes"
                    delete_reason = fab_reason

        # 埋め草エピソード（人物タイプ問わず）
        if not delete_reason:
            is_filler, filler_score, concrete_score = is_filler_episode(text)
            if is_filler and filler_score >= 4:  # 厳し目に4以上
                category = "filler_episodes"
                delete_reason = f"埋め草スコア{filler_score}、具体性{concrete_score}"

        if delete_reason:
            episodes_to_delete.append(i)
            report["categories"][category].append(
                {
                    "episode_id": episode_id,
                    "person_name": person_name,
                    "age": age,
                    "reason": delete_reason,
                    "text_snippet": text[:100],
                }
            )

    # 削除実行
    episodes_to_delete = sorted(set(episodes_to_delete), reverse=True)
    report["deleted_count"] = len(episodes_to_delete)

    if not dry_run and episodes_to_delete:
        print(f"バックアップ作成: {BACKUP_PATH}")
        shutil.copy(CSV_PATH, BACKUP_PATH)

        for idx in episodes_to_delete:
            del rows[idx]

        with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    report["final_count"] = len(rows)
    return report


def main():
    import argparse

    parser = argparse.ArgumentParser(description="捏造エピソード削除")
    parser.add_argument("--execute", action="store_true", help="実際に削除を実行")
    args = parser.parse_args()

    dry_run = not args.execute

    print("=" * 70)
    print("🧹 捏造・埋め草エピソード削除システム")
    print("=" * 70)
    print(f"モード: {'ドライラン' if dry_run else '★実行★'}")

    report = detect_and_purge(dry_run=dry_run)

    print("\n=== 検出結果 ===")
    print(f"元のエピソード数: {report['original_count']}")
    print("\n【カテゴリ別】")
    for cat, items in report["categories"].items():
        print(f"  {cat}: {len(items)}件")

    print(f"\n削除対象: {report['deleted_count']}件")

    # 詳細表示
    for cat, items in report["categories"].items():
        if items:
            print(f"\n--- {cat} (上位10件) ---")
            for item in items[:10]:
                print(f"  {item['episode_id']}: {item['person_name']} ({item['age']}歳)")
                print(f"    理由: {item['reason']}")

    # レポート保存
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nレポート保存: {REPORT_PATH}")

    if not dry_run:
        print(f"\n✅ 削除完了: {report['original_count']} → {report['final_count']}件")
    else:
        print("\n💡 --execute で実際に削除を実行")


if __name__ == "__main__":
    main()
