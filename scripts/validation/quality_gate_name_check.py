#!/usr/bin/env python3
"""
名前-内容整合性品質ゲート

ステージングCSVまたはマスターCSVの全エピソードをチェックし、
名前と内容が一致しないエピソードを検出・レポートする。

使用方法:
    # ステージングCSVをチェック
    python scripts/quality_gate_name_check.py --source staging

    # マスターCSVをチェック
    python scripts/quality_gate_name_check.py --source master

    # 問題エピソードを削除
    python scripts/quality_gate_name_check.py --source master --fix

    # 詳細表示
    python scripts/quality_gate_name_check.py --source master --verbose
"""

import argparse
import csv
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
STAGING_CSV = PROJECT_ROOT / "generated" / "pipeline_staging.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved" / "backup"
REPORT_DIR = PROJECT_ROOT / "reports"


# グループメンバー辞書（許容するケース）
GROUP_MEMBERS = {
    "BTS": ["RM", "アールエム", "ジン", "SUGA", "J-HOPE", "ジミン", "V", "ジョングク"],
    "BLACKPINK": ["ジス", "ジェニ", "ロゼ", "リサ"],
    "TWICE": ["ナヨン", "ジョンヨン", "モモ", "サナ", "ジヒョ", "ミナ", "ダヒョン", "チェヨン", "ツウィ"],
    "KinKi Kids": ["堂本光一", "堂本剛"],
    "V6": ["森田剛", "三宅健", "岡田准一", "長野博", "坂本昌行", "井ノ原快彦"],
    "DREAMS COME TRUE": ["吉田美和", "中村正人"],
    "櫻坂46": ["菅井友香", "小林由依", "土生瑞穂"],
    "ミルクボーイ": ["駒場孝", "内海崇"],
    "千鳥": ["大悟", "ノブ"],
    "ダウンタウン": ["松本人志", "浜田雅功"],
    "NMB48": ["山本彩", "須田亜香里"],
    "Mr.Children": ["桜井和寿"],
    "サザンオールスターズ": ["桑田佳祐"],
    "YOASOBI": ["幾田りら", "Ayase"],
    "水溜りボンド": ["カンタ", "トミー"],
    "東海オンエア": ["てつや", "しばゆー", "りょう", "としみつ", "ゆめまる", "虫眼鏡"],
}

# 表記ゆれ許容パターン
SPELLING_VARIATIONS = {
    "ベートーベン": "ベートーヴェン",
    "ベートーヴェン": "ベートーベン",
    "モーツアルト": "モーツァルト",
    "モーツァルト": "モーツアルト",
}


def extract_text_name(episode_text: str) -> Optional[str]:
    """本文から人物名を抽出"""
    if not episode_text:
        return None

    match = re.search(r"あなたと同じ\d+歳のとき[、, ]?\s*([^はがをにで、,]+?)(?:は|が)", episode_text)
    if match:
        return match.group(1).strip()
    return None


def normalize_name(name: str) -> str:
    """名前を正規化"""
    if not name:
        return ""
    # 括弧内を除去
    name = re.sub(r"[（(][^)）]+[)）]", "", name)
    # 敬称を除去
    name = re.sub(r"(さん|氏|君|様|先生|博士|教授)$", "", name)
    # 空白を除去
    return name.strip().replace(" ", "").replace("　", "")


def is_group_member_mismatch(person_name: str, text_name: str) -> bool:
    """グループメンバーの許容ケースかどうか"""
    for group_name, members in GROUP_MEMBERS.items():
        # text_nameがグループ名で、person_nameがそのメンバー
        if text_name == group_name:
            for member in members:
                if member in person_name or person_name in member:
                    return True
        # 逆パターン：person_nameがグループ名で、text_nameがメンバー
        if person_name == group_name:
            for member in members:
                if member in text_name or text_name in member:
                    return True
    return False


def is_spelling_variation(person_name: str, text_name: str) -> bool:
    """表記ゆれの許容ケースかどうか"""
    pn = normalize_name(person_name)
    tn = normalize_name(text_name)

    # 直接マッピング
    if pn in SPELLING_VARIATIONS and SPELLING_VARIATIONS[pn] == tn:
        return True

    # 類似度チェック（70%以上一致なら許容）
    if len(pn) >= 3 and len(tn) >= 3:
        pn_chars = set(pn)
        tn_chars = set(tn)
        common = pn_chars & tn_chars
        similarity = len(common) / max(len(pn_chars), len(tn_chars))
        if similarity >= 0.7:
            return True

    return False


def extract_parenthetical_name(name: str) -> Optional[str]:
    """括弧内の名前を抽出（例: 'ゆうこりん（小倉優子）' → '小倉優子'）"""
    match = re.search(r"[（(]([^)）]+)[)）]", name)
    if match:
        return match.group(1).strip()
    return None


def is_acceptable_mismatch(person_name: str, text_name: str) -> tuple[bool, str]:
    """
    許容される不一致かどうか判定

    Returns: (is_acceptable, reason)
    """
    pn = normalize_name(person_name)
    tn = normalize_name(text_name)

    # 完全一致
    if pn == tn:
        return True, "exact_match"

    # 部分一致
    if len(pn) >= 2 and len(tn) >= 2:
        if pn in tn or tn in pn:
            return True, "partial_match"

    # 括弧内の本名との一致（例: 'ゆうこりん（小倉優子）' vs '小倉優子'）
    paren_name = extract_parenthetical_name(person_name)
    if paren_name:
        paren_normalized = normalize_name(paren_name)
        # 敬称除去（さん等）
        tn_clean = re.sub(r"(さん|氏|君|様)$", "", tn)
        if paren_normalized == tn_clean or paren_normalized in tn_clean or tn_clean in paren_normalized:
            return True, "alias_match"

    # グループメンバー許容
    if is_group_member_mismatch(person_name, text_name):
        return True, "group_member"

    # 表記ゆれ許容
    if is_spelling_variation(person_name, text_name):
        return True, "spelling_variation"

    # 文字の重複率
    pn_chars = set(pn)
    tn_chars = set(tn)
    common = pn_chars & tn_chars
    if len(common) >= 2 and len(common) / max(len(pn_chars), len(tn_chars)) >= 0.5:
        return True, "char_overlap"

    return False, "mismatch"


def check_all_episodes(csv_path: Path, verbose: bool = False) -> Dict:
    """全エピソードをチェック"""
    results = {
        "total": 0,
        "checked": 0,
        "mismatches": [],
        "acceptable": [],
        "stats": {
            "exact_match": 0,
            "partial_match": 0,
            "alias_match": 0,
            "group_member": 0,
            "spelling_variation": 0,
            "char_overlap": 0,
            "mismatch": 0,
        },
    }

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    results["total"] = len(rows)

    for row in rows:
        episode_id = row.get("episode_id", "")
        person_id = row.get("person_id", "")
        person_name = row.get("person_name", "")
        episode_text = row.get("episode_text", "")

        if not episode_text or not person_name:
            continue

        results["checked"] += 1

        text_name = extract_text_name(episode_text)
        if not text_name:
            continue

        is_acceptable, reason = is_acceptable_mismatch(person_name, text_name)
        results["stats"][reason] += 1

        if is_acceptable:
            if verbose and reason != "exact_match":
                results["acceptable"].append(
                    {
                        "episode_id": episode_id,
                        "person_name": person_name,
                        "text_name": text_name,
                        "reason": reason,
                    }
                )
        else:
            results["mismatches"].append(
                {
                    "episode_id": episode_id,
                    "person_id": person_id,
                    "person_name": person_name,
                    "text_name": text_name,
                    "episode_preview": episode_text[:100],
                }
            )

    return results


def fix_mismatches(csv_path: Path, mismatches: List[Dict]) -> int:
    """不整合エピソードを削除"""
    if not mismatches:
        return 0

    # 削除対象のセット
    delete_keys = {(m["person_id"], m["episode_id"]) for m in mismatches}

    # バックアップ
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"MASTER_before_quality_gate_{timestamp}.csv"
    shutil.copy(csv_path, backup_path)
    print(f"📦 バックアップ: {backup_path}")

    # CSV読み込み
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    original_count = len(rows)

    # フィルタリング
    filtered_rows = [row for row in rows if (row.get("person_id", ""), row.get("episode_id", "")) not in delete_keys]

    deleted_count = original_count - len(filtered_rows)

    # 書き出し
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(filtered_rows)

    return deleted_count


def main():
    parser = argparse.ArgumentParser(description="名前-内容整合性品質ゲート")
    parser.add_argument(
        "--source", choices=["staging", "master"], default="staging", help="チェック対象（staging or master）"
    )
    parser.add_argument("--fix", action="store_true", help="問題エピソードを削除")
    parser.add_argument("--verbose", action="store_true", help="詳細表示")
    args = parser.parse_args()

    csv_path = STAGING_CSV if args.source == "staging" else MASTER_CSV

    if not csv_path.exists():
        print(f"❌ ファイルが見つかりません: {csv_path}")
        sys.exit(1)

    print("=" * 70)
    print("🔍 名前-内容整合性品質ゲート")
    print("=" * 70)
    print(f"📂 対象: {csv_path}")
    print(f"🔧 モード: {'修正実行' if args.fix else 'チェックのみ'}")
    print("=" * 70)

    # チェック実行
    results = check_all_episodes(csv_path, args.verbose)

    # 結果表示
    print("\n📊 チェック結果")
    print(f"  総エピソード: {results['total']:,}")
    print(f"  チェック済み: {results['checked']:,}")
    print()
    print("【統計】")
    for reason, count in results["stats"].items():
        if count > 0:
            print(f"  {reason}: {count:,}")
    print()
    print(f"🔴 不整合（要修正）: {len(results['mismatches'])}件")

    # 不整合サンプル表示
    if results["mismatches"]:
        print("\n【不整合サンプル（最初の10件）】")
        for m in results["mismatches"][:10]:
            print(f"\n  {m['episode_id']} | {m['person_name']}")
            print(f"    → 本文内: {m['text_name']}")

    # 修正実行
    if args.fix and results["mismatches"]:
        print("\n" + "=" * 70)
        print("🔧 修正実行中...")

        deleted = fix_mismatches(csv_path, results["mismatches"])

        print(f"\n✅ 削除完了: {deleted}件")

        # レポート保存
        REPORT_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = REPORT_DIR / f"quality_gate_{timestamp}.json"

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "timestamp": timestamp,
                    "source": args.source,
                    "total_checked": results["checked"],
                    "deleted_count": deleted,
                    "mismatches": results["mismatches"][:100],
                    "stats": results["stats"],
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        print(f"📄 レポート: {report_path}")

    elif results["mismatches"]:
        print("\n💡 修正を実行するには --fix オプションを使用してください")

    # 品質ゲート結果
    print("\n" + "=" * 70)
    if len(results["mismatches"]) == 0:
        print("✅ 品質ゲート: PASS")
    else:
        mismatch_rate = len(results["mismatches"]) / max(1, results["checked"]) * 100
        print("❌ 品質ゲート: FAIL")
        print(f"   不整合率: {mismatch_rate:.2f}%")
        print("   目標: 1%以下")
    print("=" * 70)


if __name__ == "__main__":
    main()
