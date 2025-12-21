#!/usr/bin/env python3
"""
エピソード名前-内容不整合検出スクリプト

問題パターン:
1. person_name と episode_text 冒頭の人物名が異なる
2. 同一episode_idが複数人物に割り当てられている
3. episode_text内に別人物のエピソードが含まれている
"""

import csv
import re
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
OUTPUT_DIR = PROJECT_ROOT / "reports"


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
    """名前を正規化して比較しやすくする"""
    if not name:
        return ""
    # 敬称・称号を除去
    name = re.sub(r"[（(][^)）]+[)）]", "", name)
    name = re.sub(r"(さん|氏|君|様|先生|博士|教授)$", "", name)
    # 空白除去
    name = name.strip().replace(" ", "").replace("　", "")
    return name


def name_matches(person_name: str, text_name: str) -> bool:
    """2つの名前が同一人物を指しているか判定"""
    if not person_name or not text_name:
        return False

    pn = normalize_name(person_name)
    tn = normalize_name(text_name)

    # 完全一致
    if pn == tn:
        return True

    # 部分一致（短い方が長い方に含まれる）
    if len(pn) >= 2 and len(tn) >= 2:
        if pn in tn or tn in pn:
            return True

    # 姓のみ一致（日本人名の場合）
    pn_parts = re.split(r"[・\s]", pn)
    tn_parts = re.split(r"[・\s]", tn)
    if len(pn_parts) > 1 and len(tn_parts) > 1:
        if pn_parts[0] == tn_parts[0]:
            return True

    return False


def detect_mismatches(csv_path: Path) -> dict:
    """不整合エピソードを検出"""
    results = {
        "name_content_mismatch": [],  # 名前と内容の不一致
        "duplicate_episode_id": defaultdict(list),  # 重複episode_id
        "suspicious_templates": [],  # テンプレート疑い（同じ内容が複数人に）
        "stats": {
            "total_episodes": 0,
            "checked_episodes": 0,
            "mismatches_found": 0,
        },
    }

    # エピソード内容のハッシュ → 人物リスト
    content_hash_map = defaultdict(list)

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    results["stats"]["total_episodes"] = len(rows)

    for row in rows:
        episode_id = row.get("episode_id", "")
        person_id = row.get("person_id", "")
        person_name = row.get("person_name", "")
        episode_text = row.get("episode_text", "")

        if not episode_text or not person_name:
            continue

        results["stats"]["checked_episodes"] += 1

        # episode_id重複チェック
        results["duplicate_episode_id"][episode_id].append(
            {
                "person_id": person_id,
                "person_name": person_name,
            }
        )

        # 内容ハッシュ（最初の100文字）で重複検出
        content_key = episode_text[:100] if len(episode_text) >= 100 else episode_text
        content_hash_map[content_key].append(
            {
                "episode_id": episode_id,
                "person_id": person_id,
                "person_name": person_name,
            }
        )

        # 名前-内容不整合チェック
        text_name = extract_person_name_from_text(episode_text)
        if text_name and not name_matches(person_name, text_name):
            results["name_content_mismatch"].append(
                {
                    "episode_id": episode_id,
                    "person_id": person_id,
                    "person_name": person_name,
                    "text_name": text_name,
                    "episode_preview": episode_text[:200],
                }
            )
            results["stats"]["mismatches_found"] += 1

    # 同一内容が複数人物に割り当てられているケースを検出
    for content_key, persons in content_hash_map.items():
        if len(persons) > 1:
            # 異なる人物に同じ内容が割り当てられている
            unique_persons = set(p["person_name"] for p in persons)
            if len(unique_persons) > 1:
                results["suspicious_templates"].append(
                    {
                        "content_preview": content_key[:100],
                        "affected_persons": persons,
                        "count": len(persons),
                    }
                )

    # 重複episode_id（2人以上に割り当て）のみ抽出
    results["duplicate_episode_id"] = {k: v for k, v in results["duplicate_episode_id"].items() if len(v) > 1}

    return results


def generate_report(results: dict, output_path: Path):
    """レポートを生成"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_path / f"name_content_mismatch_{timestamp}.md"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# エピソード名前-内容不整合レポート\n\n")
        f.write(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # 統計
        stats = results["stats"]
        f.write("## 統計\n\n")
        f.write(f"- 総エピソード数: {stats['total_episodes']}\n")
        f.write(f"- チェック済み: {stats['checked_episodes']}\n")
        f.write(f"- 不整合検出数: {stats['mismatches_found']}\n")
        f.write(f"- 重複episode_id数: {len(results['duplicate_episode_id'])}\n")
        f.write(f"- テンプレート疑惑数: {len(results['suspicious_templates'])}\n\n")

        # 名前-内容不整合
        f.write("## 名前-内容不整合リスト\n\n")
        for item in results["name_content_mismatch"][:50]:  # 最初の50件
            f.write(f"### {item['episode_id']}\n")
            f.write(f"- **person_name**: {item['person_name']}\n")
            f.write(f"- **text内の人物**: {item['text_name']}\n")
            f.write(f"- **内容プレビュー**: {item['episode_preview'][:100]}...\n\n")

        if len(results["name_content_mismatch"]) > 50:
            f.write(f"(他 {len(results['name_content_mismatch']) - 50} 件省略)\n\n")

        # 重複episode_id
        f.write("## 重複episode_id\n\n")
        for ep_id, persons in list(results["duplicate_episode_id"].items())[:20]:
            f.write(f"### {ep_id} ({len(persons)}人に割当)\n")
            for p in persons[:5]:
                f.write(f"- {p['person_name']} ({p['person_id']})\n")
            if len(persons) > 5:
                f.write(f"- (他 {len(persons) - 5} 人)\n")
            f.write("\n")

        # テンプレート疑惑
        f.write("## テンプレート疑惑（同一内容→複数人物）\n\n")
        for item in results["suspicious_templates"][:10]:
            f.write(f"### {item['count']}人に同一内容\n")
            f.write(f"内容: {item['content_preview'][:80]}...\n")
            f.write("対象者:\n")
            for p in item["affected_persons"][:5]:
                f.write(f"- {p['person_name']}\n")
            if len(item["affected_persons"]) > 5:
                f.write(f"- (他 {len(item['affected_persons']) - 5} 人)\n")
            f.write("\n")

    print(f"レポート生成完了: {report_path}")
    return report_path


def export_mismatch_csv(results: dict, output_path: Path):
    """不整合リストをCSVでエクスポート"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = output_path / f"name_content_mismatch_{timestamp}.csv"

    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["episode_id", "person_id", "person_name", "text_name", "mismatch_type"])

        for item in results["name_content_mismatch"]:
            writer.writerow(
                [item["episode_id"], item["person_id"], item["person_name"], item["text_name"], "name_content_mismatch"]
            )

        for ep_id, persons in results["duplicate_episode_id"].items():
            for p in persons:
                writer.writerow([ep_id, p["person_id"], p["person_name"], "", "duplicate_episode_id"])

    print(f"CSV出力完了: {csv_path}")
    return csv_path


def main():
    print("=" * 60)
    print("エピソード名前-内容不整合検出")
    print("=" * 60)

    if not MASTER_CSV.exists():
        print(f"エラー: CSVファイルが見つかりません: {MASTER_CSV}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(exist_ok=True)

    print(f"\n入力ファイル: {MASTER_CSV}")
    print("検出中...")

    results = detect_mismatches(MASTER_CSV)

    print("\n=== 検出結果 ===")
    print(f"総エピソード数: {results['stats']['total_episodes']}")
    print(f"チェック済み: {results['stats']['checked_episodes']}")
    print(f"名前-内容不整合: {len(results['name_content_mismatch'])} 件")
    print(f"重複episode_id: {len(results['duplicate_episode_id'])} 件")
    print(f"テンプレート疑惑: {len(results['suspicious_templates'])} 件")

    # レポート生成
    report_path = generate_report(results, OUTPUT_DIR)
    csv_path = export_mismatch_csv(results, OUTPUT_DIR)

    # サンプル表示
    if results["name_content_mismatch"]:
        print("\n=== 不整合サンプル（最初の5件）===")
        for item in results["name_content_mismatch"][:5]:
            print(f"\n{item['episode_id']}")
            print(f"  person_name: {item['person_name']}")
            print(f"  text内人物: {item['text_name']}")

    return results


if __name__ == "__main__":
    main()
