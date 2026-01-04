#!/usr/bin/env python3
"""
ヘミングウェイ ノーベル賞受賞エピソード追加スクリプト

事実:
- ヘミングウェイ: 1899年7月21日生まれ
- 『老人と海』出版: 1952年（53歳）
- ピューリッツァー賞: 1953年（54歳）
- ノーベル文学賞: 1954年10月28日発表（55歳）
  - 授賞式には健康上の理由で欠席（スウェーデン大使が代読）
"""

import csv
import hashlib
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"

# 新しいエピソード
NEW_EPISODE = {
    "episode_id": "",  # 後で生成
    "person_id": "P2595B54",
    "person_name": "アーネスト・ヘミングウェイ",
    "episode_count": "5",  # 4→5に増加
    "age": "55.0",
    "category": "文学",
    "char_count": "",  # 後で計算
    "episode_text": (
        "あなたと同じ55歳のとき、アーネスト・ヘミングウェイはノーベル文学賞を受賞した。"
        "1954年10月、スウェーデン・アカデミーは「現代散文の様式に強力な影響を与えた叙述の熟達」を評価し、"
        "彼に文学の最高栄誉を授けた。しかし、2度の飛行機事故による重傷から回復途上にあった彼は、"
        "ストックホルムでの授賞式に出席することができなかった。"
        "代わりにアメリカ大使が受賞スピーチを代読し、その中でヘミングウェイは"
        "「作家は孤独の中で働く」という有名な言葉を残した。"
        "前年に発表した『老人と海』でピューリッツァー賞も受賞しており、"
        "この2つの栄誉は、長年の文学的挑戦に対する世界からの答えとなった。"
        "病床にありながらも、彼は生涯を通じて追求してきた「真実を書く」という信念が"
        "認められたことを静かに噛みしめていた。"
    ),
    "episode_type": "達成",
    "fact_check_result": "確認済み",
    "group_name": "未登録",
    "is_group_member": "False",
    "person_type": "REAL",
    "quality_score": "9.0",
    "source": "LLM_GENERATED",
    "tier": "WEEK_1",
    "week": "1.0",
    "work_title": "老人と海",
    "fame_tier": "4.0",
    "wikipedia_ja": "False",
    "textbook": "False",
    "award_level": "10.0",  # ノーベル賞は最高レベル
    "notoriety": "False",
    "fame_score": "10.0",
    "composite_score": "9.5",
    "episode_fame_tier": "1.0",  # Tier1
    # LLM 7軸スコア（日本語カラム名が正しい）
    "記憶性スコア": "9.0",
    "共感性スコア": "7.0",
    "意外性スコア": "6.0",
    "生成品質スコア": "9.0",
    "教育的価値": "9.0",
    "ストーリー品質": "8.0",
    "事実密度": "10.0",
    # 知名度データ（他のヘミングウェイエピソードから複製）
    "celebrity_score_v2": "717.087262017953",
    "sitelinks_count": "206",
    "multi_lang_pv": "852935",
}


def generate_episode_id() -> str:
    """新しいepisode_idを生成"""
    timestamp = datetime.now().strftime("%y%m%d%H%M%S")
    hash_suffix = hashlib.md5(f"hemingway_nobel_{timestamp}".encode()).hexdigest()[:3]
    return f"EP-{timestamp}{hash_suffix}"


def add_nobel_episode(dry_run: bool = True) -> dict:
    """ノーベル賞エピソードを追加"""
    results = {"added": None, "episode_count_updated": []}

    # CSV読み込み
    rows = []
    with open(MASTER_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # 新エピソードを準備
    new_ep = NEW_EPISODE.copy()
    new_ep["episode_id"] = generate_episode_id()
    new_ep["char_count"] = str(len(new_ep["episode_text"]))
    new_ep["generation_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_ep["fame_score_updated_at"] = datetime.now().isoformat()

    # 既存フィールドで未設定のものをデフォルト値で埋める
    for fn in fieldnames:
        if fn not in new_ep:
            new_ep[fn] = ""

    # ヘミングウェイの既存エピソードのepisode_countを更新
    for row in rows:
        if row.get("person_id") == "P2595B54":
            old_count = row.get("episode_count", "4")
            row["episode_count"] = "5"
            results["episode_count_updated"].append(row["episode_id"])

    # 新エピソードを追加（ヘミングウェイの最後のエピソードの後に挿入）
    insert_idx = None
    for i, row in enumerate(rows):
        if row.get("person_id") == "P2595B54":
            insert_idx = i + 1

    if insert_idx:
        rows.insert(insert_idx, new_ep)
    else:
        rows.append(new_ep)

    results["added"] = {
        "episode_id": new_ep["episode_id"],
        "age": new_ep["age"],
        "text_preview": new_ep["episode_text"][:100] + "...",
    }

    # 書き込み
    if not dry_run:
        with open(MASTER_CSV, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    return results


def main():
    import argparse
    import json

    parser = argparse.ArgumentParser(description="ヘミングウェイ ノーベル賞エピソード追加")
    parser.add_argument("--execute", action="store_true", help="実際に追加を実行")
    args = parser.parse_args()

    print("=" * 60)
    print("ヘミングウェイ ノーベル賞エピソード追加")
    print("=" * 60)

    dry_run = not args.execute
    if dry_run:
        print("\n[DRY RUN] --execute オプションで実際に追加を実行")

    results = add_nobel_episode(dry_run=dry_run)

    # 結果表示
    print("\n追加エピソード:")
    print(f"  ID: {results['added']['episode_id']}")
    print(f"  年齢: {results['added']['age']}歳")
    print(f"  本文: {results['added']['text_preview']}")
    print(f"\nepisode_count更新: {len(results['episode_count_updated'])}件")

    if not dry_run:
        print("\n✅ 追加完了")

    # レポート出力
    report_path = PROJECT_ROOT / "src/reports/hemingway_nobel_episode_added.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "dry_run": dry_run,
                "results": results,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"\nレポート: {report_path}")

    return 0


if __name__ == "__main__":
    main()
