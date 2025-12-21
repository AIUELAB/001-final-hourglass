#!/usr/bin/env python3
"""
エピソード名前-内容不整合修正スクリプト

真の不整合（完全に別人のエピソード）を検出し削除する
グループメンバー→グループ名、表記ゆれは許容する
"""

import csv
import re
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import shutil

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved" / "backup"
OUTPUT_DIR = PROJECT_ROOT / "reports"


# グループ名とメンバーの対応（許容するケース）
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
}

# 表記ゆれ許容パターン
SPELLING_VARIATIONS = [
    ("ベートーベン", "ベートーヴェン"),
    ("濱田龍臣", "濱田龍臉"),
    ("水溜りボンド カンタ", "水溜りボンドのカンタ"),
]


def is_group_member_episode(person_name: str, text_name: str) -> bool:
    """グループメンバーのエピソードでグループ名が使われているかチェック"""
    for group_name, members in GROUP_MEMBERS.items():
        if text_name == group_name:
            # person_nameがこのグループのメンバーか
            for member in members:
                if member in person_name or person_name in member:
                    return True
    return False


def is_spelling_variation(person_name: str, text_name: str) -> bool:
    """表記ゆれかどうかチェック"""
    for var1, var2 in SPELLING_VARIATIONS:
        if (person_name == var1 and text_name == var2) or (person_name == var2 and text_name == var1):
            return True
    # 類似度チェック（80%以上一致なら許容）
    if len(person_name) >= 3 and len(text_name) >= 3:
        common_chars = set(person_name) & set(text_name)
        similarity = len(common_chars) / max(len(set(person_name)), len(set(text_name)))
        if similarity >= 0.7:
            return True
    return False


def extract_person_name_from_text(episode_text: str) -> str | None:
    """エピソード本文から人物名を抽出"""
    if not episode_text:
        return None

    # パターン1: 「あなたと同じXX歳のとき、【人物名】は」
    match = re.search(r"あなたと同じ\d+歳のとき[、, ]?\s*([^はがをにで、,]+?)(?:は|が)", episode_text)
    if match:
        return match.group(1).strip()

    # パターン2: 冒頭に人物名（改行後）
    match = re.search(r"^(?:【[^】]+】\s*)?([^はがをにで、,\n]+?)(?:は|が)", episode_text)
    if match:
        return match.group(1).strip()

    return None


def normalize_name(name: str) -> str:
    """名前を正規化"""
    if not name:
        return ""
    name = re.sub(r"[（(][^)）]+[)）]", "", name)
    name = re.sub(r"(さん|氏|君|様|先生|博士|教授)$", "", name)
    name = name.strip().replace(" ", "").replace("　", "")
    return name


def is_true_mismatch(person_name: str, text_name: str, episode_text: str) -> tuple[bool, str]:
    """
    真の不整合かどうか判定
    Returns: (is_mismatch, reason)
    """
    if not text_name:
        return False, "text_name_not_found"

    # グループメンバーチェック
    if is_group_member_episode(person_name, text_name):
        return False, "group_member"

    # 表記ゆれチェック
    if is_spelling_variation(person_name, text_name):
        return False, "spelling_variation"

    # 名前の部分一致チェック
    pn = normalize_name(person_name)
    tn = normalize_name(text_name)

    if pn == tn:
        return False, "exact_match"

    # 部分一致（2文字以上）- 括弧内の名前も考慮
    # 例: "YOASOBI（幾田りら）" と "幾田りら"
    person_name_expanded = normalize_name(person_name)
    # 括弧内も抽出
    bracket_match = re.search(r"[（(]([^)）]+)[)）]", person_name)
    if bracket_match:
        person_name_expanded += bracket_match.group(1)

    if len(pn) >= 2 and len(tn) >= 2:
        if pn in tn or tn in pn:
            return False, "partial_match"
        # 括弧内の名前でもチェック
        if tn in person_name_expanded or person_name_expanded in tn:
            return False, "partial_match"

    # text_nameがperson_nameの一部を含むかチェック（日本語名向け）
    # 例: person_name="水溜りボンド カンタ", text_name="水溜りボンドのカンタ"
    pn_chars = set(pn)
    tn_chars = set(tn)
    common = pn_chars & tn_chars
    if len(common) >= 3 and len(common) / max(len(pn_chars), len(tn_chars)) >= 0.5:
        return False, "char_overlap"

    # メタ的表現チェック（「申し訳ございません」など）
    if "申し訳" in text_name or "エラー" in text_name:
        return True, "meta_expression"

    # ここまで来たら真の不整合
    return True, "completely_different_person"


def detect_critical_mismatches(csv_path: Path) -> dict:
    """クリティカルな不整合を検出"""
    results = {
        "critical_mismatches": [],
        "duplicate_episode_ids": defaultdict(list),
        "ignored_cases": [],
        "stats": {
            "total": 0,
            "checked": 0,
            "critical": 0,
            "ignored": 0,
        },
    }

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    results["stats"]["total"] = len(rows)

    for row in rows:
        episode_id = row.get("episode_id", "")
        person_id = row.get("person_id", "")
        person_name = row.get("person_name", "")
        episode_text = row.get("episode_text", "")

        if not episode_text or not person_name:
            continue

        results["stats"]["checked"] += 1

        # episode_id重複追跡
        results["duplicate_episode_ids"][episode_id].append(
            {
                "person_id": person_id,
                "person_name": person_name,
            }
        )

        # 名前抽出
        text_name = extract_person_name_from_text(episode_text)
        if not text_name:
            continue

        # 真の不整合チェック
        is_mismatch, reason = is_true_mismatch(person_name, text_name, episode_text)

        if is_mismatch:
            results["critical_mismatches"].append(
                {
                    "episode_id": episode_id,
                    "person_id": person_id,
                    "person_name": person_name,
                    "text_name": text_name,
                    "reason": reason,
                    "episode_preview": episode_text[:150],
                }
            )
            results["stats"]["critical"] += 1
        else:
            results["ignored_cases"].append(
                {
                    "person_name": person_name,
                    "text_name": text_name,
                    "reason": reason,
                }
            )
            results["stats"]["ignored"] += 1

    # 重複episode_id（2人以上）のみ保持
    results["duplicate_episode_ids"] = {k: v for k, v in results["duplicate_episode_ids"].items() if len(v) > 1}

    return results


def fix_mismatches(csv_path: Path, results: dict, execute: bool = False) -> int:
    """不整合エピソードを削除"""
    # 削除対象のperson_id + episode_id のセット
    delete_targets = set()

    # まずCSVを読み込んでepisode_idごとのデータを取得
    ep_data = {}
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ep_id = row.get("episode_id", "")
            if ep_id not in ep_data:
                ep_data[ep_id] = []
            ep_data[ep_id].append(
                {
                    "person_id": row.get("person_id", ""),
                    "person_name": row.get("person_name", ""),
                    "episode_text": row.get("episode_text", ""),
                }
            )

    # クリティカル不整合
    for item in results["critical_mismatches"]:
        delete_targets.add((item["person_id"], item["episode_id"]))

    # 重複episode_id（同一IDが複数人に割り当て）
    for ep_id, persons in results["duplicate_episode_ids"].items():
        if len(persons) <= 1:
            continue

        # この episode_id のエピソード内容から人物名を抽出
        if ep_id in ep_data:
            sample_text = ep_data[ep_id][0]["episode_text"]
            text_name = extract_person_name_from_text(sample_text)

            # 正しいマッピング（person_name と text_name が一致）を探す
            correct_person = None
            for p in persons:
                pn = normalize_name(p["person_name"])
                tn = normalize_name(text_name) if text_name else ""
                if pn and tn and (pn in tn or tn in pn or pn == tn):
                    correct_person = p["person_id"]
                    break

            # 正しい人以外を削除対象に
            for p in persons:
                if p["person_id"] != correct_person:
                    delete_targets.add((p["person_id"], ep_id))
        else:
            # データがない場合は全員削除
            for p in persons:
                delete_targets.add((p["person_id"], ep_id))

    print(f"\n削除対象: {len(delete_targets)} 件")

    if not execute:
        print("\n--execute オプションなし: ドライラン終了")
        return 0

    # バックアップ
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"MASTER_before_mismatch_fix_{timestamp}.csv"
    shutil.copy(csv_path, backup_path)
    print(f"バックアップ: {backup_path}")

    # CSVを読み込んで削除対象を除外
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    original_count = len(rows)
    filtered_rows = []

    for row in rows:
        key = (row.get("person_id", ""), row.get("episode_id", ""))
        if key not in delete_targets:
            filtered_rows.append(row)

    deleted_count = original_count - len(filtered_rows)

    # 書き出し
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(filtered_rows)

    print(f"\n削除完了: {deleted_count} 件")
    print(f"残存エピソード: {len(filtered_rows)} 件")

    return deleted_count


def main():
    import argparse

    parser = argparse.ArgumentParser(description="名前-内容不整合エピソード修正")
    parser.add_argument("--execute", action="store_true", help="実際に削除を実行")
    args = parser.parse_args()

    print("=" * 60)
    print("エピソード名前-内容不整合修正")
    print("=" * 60)

    if not MASTER_CSV.exists():
        print(f"エラー: {MASTER_CSV}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(exist_ok=True)

    print(f"\n入力: {MASTER_CSV}")
    print("クリティカル不整合を検出中...")

    results = detect_critical_mismatches(MASTER_CSV)

    print("\n=== 検出結果 ===")
    print(f"総エピソード: {results['stats']['total']}")
    print(f"チェック済み: {results['stats']['checked']}")
    print(f"クリティカル不整合: {results['stats']['critical']} 件")
    print(f"許容ケース: {results['stats']['ignored']} 件")
    print(f"重複episode_id: {len(results['duplicate_episode_ids'])} 件")

    # サンプル表示
    if results["critical_mismatches"]:
        print("\n=== クリティカル不整合サンプル（最初の10件）===")
        for item in results["critical_mismatches"][:10]:
            print(f"\n{item['episode_id']} | {item['person_name']}")
            print(f"  → 本文内: {item['text_name']}")
            print(f"  理由: {item['reason']}")

    # 重複episode_id サンプル
    if results["duplicate_episode_ids"]:
        print("\n=== 重複episode_id（上位5件）===")
        sorted_dups = sorted(results["duplicate_episode_ids"].items(), key=lambda x: -len(x[1]))
        for ep_id, persons in sorted_dups[:5]:
            print(f"\n{ep_id}: {len(persons)}人に同一IDが割当")
            for p in persons[:3]:
                print(f"  - {p['person_name']}")
            if len(persons) > 3:
                print(f"  - (他{len(persons)-3}人)")

    # 修正実行
    deleted = fix_mismatches(MASTER_CSV, results, execute=args.execute)

    if args.execute:
        # レポート出力
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = OUTPUT_DIR / f"mismatch_fix_{timestamp}.json"
        import json

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "timestamp": timestamp,
                    "deleted_count": deleted,
                    "critical_mismatches": results["critical_mismatches"][:100],
                    "stats": results["stats"],
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        print(f"\nレポート: {report_path}")


if __name__ == "__main__":
    main()
