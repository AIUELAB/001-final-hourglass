#!/usr/bin/env python3
"""
episode_typeデータクリーニングスクリプト

生成システム由来の値を正規カテゴリに変換:
- 8主要カテゴリ: 転機, 達成, 死去, 挑戦, キャリア, 革新, 創業, 失敗
- 追加カテゴリ: 復帰, 家族

Usage:
    python scripts/validation/clean_episode_type.py --dry-run
    python scripts/validation/clean_episode_type.py --execute
"""

import argparse
import csv
import re
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
CSV_PATH = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved/data/backups"

# 正規カテゴリ
VALID_CATEGORIES = {
    "転機",
    "達成",
    "死去",
    "挑戦",
    "キャリア",
    "革新",
    "創業",
    "失敗",
    "復帰",
    "家族",  # 追加カテゴリ
}

# 直接マッピング（確実に変換できるもの）
DIRECT_MAPPING = {
    "ACHIEVEMENT": "達成",
    "TURNING_POINT": "転機",
    "CHALLENGE": "挑戦",
    "INNOVATION": "革新",
    "FOUNDING": "創業",
    "FAILURE": "失敗",
    "COMEBACK": "復帰",
    "FAMILY": "家族",
    "CAREER": "キャリア",
    "LEGACY": "キャリア",  # レガシー → キャリアに統合
    "人生の転機": "転機",
    "転換点": "転機",
}

# 生成システム由来の値（コンテンツ分析が必要）
GENERATION_ARTIFACTS = {
    "mass_production",
    "factual",
    "narrative",
    "inspirational",
    "pipeline_layer2",
    "nan→DENSITY_IMPROVED",
}

# コンテンツベースの推論パターン
INFERENCE_PATTERNS = {
    "死去": [
        r"死去|死亡|逝去|亡くなった|他界|永眠|没した|命を落と|息を引き取",
        r"\d+歳で.*死|享年\d+",
    ],
    "達成": [
        r"優勝|金メダル|受賞|達成|記録|MVP|年間王者|殿堂入り|1位|グランプリ",
        r"史上最年少|史上初|世界新|最優秀|ベストアルバム",
    ],
    "創業": [
        r"創業|創設|設立|起業|会社を興|開業|立ち上げ",
    ],
    "革新": [
        r"革新|発明|特許|新技術|イノベーション|世界初の|画期的な",
    ],
    "失敗": [
        r"失敗|挫折|破産|倒産|解散|引退.*撤回|降格|敗北",
    ],
    "復帰": [
        r"復帰|カムバック|再起|復活|再デビュー|再始動",
    ],
    "挑戦": [
        r"挑戦|初出場|デビュー|初めて|新たな.*始め|転身|進出",
    ],
}


def infer_category_from_content(text: str) -> str | None:
    """エピソードテキストからカテゴリを推論"""
    if not text:
        return None

    for category, patterns in INFERENCE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text):
                return category

    return None


def clean_episode_type(row: dict) -> tuple[str, str]:
    """
    episode_typeをクリーニング

    Returns:
        (new_value, change_reason)
    """
    original = row.get("episode_type", "").strip()
    text = row.get("episode_text", "")

    # 既に正規カテゴリ
    if original in VALID_CATEGORIES:
        return original, ""

    # 直接マッピング
    if original in DIRECT_MAPPING:
        return DIRECT_MAPPING[original], f"直接変換: {original}"

    # 生成システム由来 → コンテンツから推論
    if original in GENERATION_ARTIFACTS or not original:
        inferred = infer_category_from_content(text)
        if inferred:
            return inferred, f"推論({original or '空'}→{inferred})"
        else:
            # 推論不可 → デフォルトは「転機」（最も汎用的）
            return "転機", f"デフォルト({original or '空'}→転機)"

    # 不明な値 → コンテンツから推論
    inferred = infer_category_from_content(text)
    if inferred:
        return inferred, f"推論({original}→{inferred})"

    # それ以外はデフォルト
    return "転機", f"デフォルト({original}→転機)"


def process_csv(dry_run: bool = True) -> dict:
    """CSVを処理"""
    # バックアップ作成
    if not dry_run:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"MASTER_EPISODES_CURRENT_{timestamp}.csv"
        shutil.copy(CSV_PATH, backup_path)
        print(f"✅ バックアップ作成: {backup_path.name}")

    # データ読み込み
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # 変更追跡
    changes = []
    before_dist = Counter()
    after_dist = Counter()

    # 各行を処理
    for row in rows:
        original = row.get("episode_type", "")
        before_dist[original] += 1

        new_value, reason = clean_episode_type(row)
        after_dist[new_value] += 1

        if new_value != original:
            changes.append(
                {
                    "episode_id": row.get("episode_id", ""),
                    "person_name": row.get("person_name", ""),
                    "original": original,
                    "new": new_value,
                    "reason": reason,
                }
            )
            row["episode_type"] = new_value

    # 書き込み
    if not dry_run and changes:
        with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"✅ CSV更新完了: {len(changes)}件変更")

    return {
        "total": len(rows),
        "changes": changes,
        "before_dist": before_dist,
        "after_dist": after_dist,
    }


def main():
    parser = argparse.ArgumentParser(description="episode_typeデータクリーニング")
    parser.add_argument("--dry-run", action="store_true", help="変更をシミュレート（デフォルト）")
    parser.add_argument("--execute", action="store_true", help="実際に変更を適用")
    args = parser.parse_args()

    dry_run = not args.execute

    print("=" * 60)
    print(f"🔧 episode_type データクリーニング {'[DRY-RUN]' if dry_run else '[EXECUTE]'}")
    print("=" * 60)

    result = process_csv(dry_run=dry_run)

    print("\n📊 処理結果:")
    print(f"   総エピソード数: {result['total']:,}")
    print(f"   変更件数: {len(result['changes']):,}")

    # 変更前分布
    print("\n📈 変更前 episode_type 分布:")
    for val, cnt in result["before_dist"].most_common():
        display = val if val else "(空)"
        print(f"   {cnt:>6} | {display}")

    # 変更後分布
    print("\n📈 変更後 episode_type 分布:")
    for val, cnt in result["after_dist"].most_common():
        print(f"   {cnt:>6} | {val}")

    # 変更サンプル
    if result["changes"]:
        print("\n📝 変更サンプル (最初の10件):")
        for c in result["changes"][:10]:
            print(f"   {c['episode_id']}: {c['original'] or '(空)'} → {c['new']} ({c['reason']})")

        if len(result["changes"]) > 10:
            print(f"   ... 他 {len(result['changes']) - 10} 件")

    # 変更理由サマリー
    reason_dist = Counter(c["reason"].split("(")[0] for c in result["changes"])
    if reason_dist:
        print("\n📊 変更理由サマリー:")
        for reason, cnt in reason_dist.most_common():
            print(f"   {cnt:>6} | {reason}")

    if dry_run and result["changes"]:
        print("\n⚠️  DRY-RUN モード: 実際の変更は行われていません")
        print(f"   実行するには: python {__file__} --execute")

    return 0


if __name__ == "__main__":
    exit(main())
