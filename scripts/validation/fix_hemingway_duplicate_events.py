#!/usr/bin/env python3
"""
ヘミングウェイ重複イベント修正スクリプト

問題:
- EP-000003503 (45歳) と EP-000003380 (61歳) が同一出来事（『老人と海』執筆〜受賞）を記述
- 事実: 『老人と海』出版=1952年(53歳)、ピューリッツァー賞=1953年(54歳)、ノーベル賞=1954年(55歳)

修正:
- 45歳: 1944年頃の出来事（第二次世界大戦従軍記者時代）
- 61歳: 1960年頃の出来事（キューバからの帰国、晩年）
"""

import csv
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "src/reports/logs"

# 修正対象
FIX_TARGETS = {
    "EP-000003503": {  # 45歳
        "old_keywords": ["『老人と海』", "ピューリッツァー賞", "ノーベル文学賞"],
        "new_text": (
            "あなたと同じ45歳のとき、アーネスト・ヘミングウェイは第二次世界大戦の従軍記者として"
            "ヨーロッパ戦線に赴いていた。コリアーズ誌の特派員として、ノルマンディー上陸作戦を取材し、"
            "パリ解放では自ら武装した民兵グループを率いてリッツ・ホテルを「解放」するという"
            "破天荒な行動に出た。この時期、3番目の妻マーサ・ゲルホーンとの関係は破綻しつつあり、"
            "タイム誌の記者メアリー・ウェルシュと運命的な出会いを果たした。"
            "戦場での経験は後の創作に深い影響を与え、人間の勇気と苦悩を描く作家としての"
            "視座をさらに深めることになった。"
        ),
    },
    "EP-000003380": {  # 61歳
        "old_keywords": ["『老人と海』", "ピューリッツァー賞", "ノーベル文学賞", "92日間"],
        "new_text": (
            "あなたと同じ61歳のとき、アーネスト・ヘミングウェイは20年以上暮らしたキューバを離れ、"
            "アメリカへの永久帰国を余儀なくされていた。カストロ革命後の政治情勢により、"
            "愛着のあるフィンカ・ビヒアの屋敷を後にし、アイダホ州ケッチャムに新たな住まいを構えた。"
            "この頃、度重なる飛行機事故の後遺症や高血圧に苦しみながらも、執筆への情熱は失われていなかった。"
            "若き日のパリでの文学修業を振り返りながら、妻メアリーに支えられ、"
            "残された時間で自らの文学的遺産を整理することに心を砕いていた。"
        ),
    },
}


def fix_hemingway_episodes(dry_run: bool = True) -> dict:
    """ヘミングウェイの重複イベントを修正"""
    results = {"fixed": [], "errors": [], "backup_path": None}

    # バックアップ
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / f"hemingway_fix_backup_{timestamp}.csv"

    # CSV読み込み（BOM対応）
    rows = []
    with open(MASTER_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # 修正実行
    for row in rows:
        ep_id = row.get("episode_id", "")
        if ep_id in FIX_TARGETS:
            target = FIX_TARGETS[ep_id]
            old_text = row.get("episode_text", "")

            # 修正前の確認
            has_keywords = any(kw in old_text for kw in target["old_keywords"])
            if not has_keywords:
                results["errors"].append({"episode_id": ep_id, "reason": "Keywords not found - may already be fixed"})
                continue

            # 修正
            result_entry = {
                "episode_id": ep_id,
                "age": row.get("age"),
                "old_text_preview": old_text[:100] + "..." if len(old_text) > 100 else old_text,
                "new_text_preview": target["new_text"][:100] + "...",
            }

            if not dry_run:
                row["episode_text"] = target["new_text"]
                row["char_count"] = str(len(target["new_text"]))

            results["fixed"].append(result_entry)

    # 書き込み
    if not dry_run and results["fixed"]:
        # バックアップ保存（BOM付きutf-8）
        with open(backup_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        results["backup_path"] = str(backup_path)

        # 元ファイル更新（BOM付きutf-8）
        with open(MASTER_CSV, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    return results


def main():
    import argparse
    import json

    parser = argparse.ArgumentParser(description="ヘミングウェイ重複イベント修正")
    parser.add_argument("--execute", action="store_true", help="実際に修正を実行")
    args = parser.parse_args()

    print("=" * 60)
    print("ヘミングウェイ重複イベント修正")
    print("=" * 60)

    dry_run = not args.execute
    if dry_run:
        print("\n[DRY RUN] --execute オプションで実際に修正を実行")

    results = fix_hemingway_episodes(dry_run=dry_run)

    # 結果表示
    print(f"\n修正対象: {len(results['fixed'])}件")
    for fix in results["fixed"]:
        print(f"\n  {fix['episode_id']} ({fix['age']}歳)")
        print(f"    旧: {fix['old_text_preview']}")
        print(f"    新: {fix['new_text_preview']}")

    if results["errors"]:
        print(f"\nエラー: {len(results['errors'])}件")
        for err in results["errors"]:
            print(f"  {err['episode_id']}: {err['reason']}")

    if not dry_run and results["backup_path"]:
        print("\n✅ 修正完了")
        print(f"  バックアップ: {results['backup_path']}")

    # レポート出力
    report_path = PROJECT_ROOT / "src/reports/hemingway_fix_result.json"
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
