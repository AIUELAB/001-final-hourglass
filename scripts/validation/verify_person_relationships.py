#!/usr/bin/env python3
"""
人物関係検証スクリプト

エピソードテキスト内の人物関係記述をマスターデータと照合し、不一致を検出する。

機能:
- MASTER_EPISODES_CURRENT.csv を読み込み
- episode カラムから「夫」「妻」「配偶者」「パートナー」等のキーワードを抽出
- person_relationships_master.json と照合
- 不一致を検出してレポート

使用方法:
    # ドライラン（検出のみ）
    python scripts/validation/verify_person_relationships.py

    # レポート出力先指定
    python scripts/validation/verify_person_relationships.py --report reports/relationships.md

    # 詳細表示
    python scripts/validation/verify_person_relationships.py --verbose
"""

import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
RELATIONSHIPS_MASTER = PROJECT_ROOT / "preserved" / "data" / "person_relationships_master.json"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "src" / "reports"

# 配偶者関係を示すパターン（正規表現）
# より厳密なパターンのみを使用して誤検出を減らす
SPOUSE_PATTERNS = [
    # 「夫の○○」「妻の○○」- 具体的な人物名が続く場合のみ
    # 「夫で俳優の○○」「妻で歌手の○○」等の職業付きパターン
    r"(?P<relation>夫|妻)で(?:俳優|女優|歌手|タレント|アナウンサー|作家|実業家|政治家|音楽家|ミュージシャン|芸人|コメディアン|プロデューサー|ディレクター|監督|脚本家|放送作家|デザイナー|モデル|アスリート|選手)の(?P<name>[一-龯ぁ-んァ-ヶA-Za-zー・]{2,20})",
    # 「夫・○○」「妻・○○」パターン（中黒で続く場合）
    r"(?P<relation>夫|妻)[・](?P<name>[一-龯ぁ-んァ-ヶA-Za-zー・]{2,20})",
    # 「○○と結婚した」「○○と結婚し」パターン（動詞形）
    r"(?P<name>[一-龯ぁ-んァ-ヶA-Za-zー・]{2,15})と(?P<relation>結婚)し(?:た|て)",
    # 「○○との結婚」パターン
    r"(?P<name>[一-龯ぁ-んァ-ヶA-Za-zー・]{2,15})との(?P<relation>結婚)",
    # 「配偶者の○○」「配偶者である○○」
    r"(?P<relation>配偶者)(?:の|である)(?P<name>[一-龯ぁ-んァ-ヶA-Za-zー・]{2,20})",
    # 「最愛の夫○○」「最愛の妻○○」- 必ず名前が続く
    r"最愛の(?P<relation>夫|妻)[・、]?(?P<name>[一-龯ぁ-んァ-ヶA-Za-zー・]{2,20})",
    # 「夫である○○」「妻である○○」パターン
    r"(?P<relation>夫|妻)である(?P<name>[一-龯ぁ-んァ-ヶA-Za-zー・]{2,20})",
    # 「○○夫妻」から夫または妻を抽出するのは困難なのでスキップ
]

# 除外すべき誤検出パターン（名前部分に含まれていたら除外）
EXCLUDE_NAME_PATTERNS = [
    r"^(の|が|は|を|に|と|で|から|まで|より|へ)$",  # 助詞のみ
    r"^(こと|もの|とき|ため|ところ|うち|あと|ほど|ばかり)$",  # 形式名詞
    r"^(看病|専念|決断|死|癌|病気|介護|支援|励まし)$",  # 抽象名詞
    r"^(中|後|前|時|年|月|日|頃|間)$",  # 時間関連
    r"^(共著|合作|コラボ)$",  # 創作関連
    r".*財団.*",  # 財団名
    r".*協会.*",  # 協会名
    r".*(?:子供|息子|娘|母|父|祖父|祖母|兄|弟|姉|妹).*",  # 他の親族関係
]

# 文脈として除外すべきパターン
EXCLUDE_CONTEXT_PATTERNS = [
    r"夫婦",  # 「夫婦」という単語
    r"結婚式",  # 「結婚式」
    r"結婚生活",  # 「結婚生活」
    r"結婚25?0?周年",  # 「結婚○周年」
    r"夫人",  # 「夫人」（敬称）
    r"新婦",  # 「新婦」
    r"主婦",  # 「主婦」
    r"パートナーシップ",  # 「パートナーシップ」（ビジネス用語）
    r"ビジネスパートナー",  # ビジネスパートナー
    r"長年のパートナー(?!で|と結婚)",  # 音楽等のパートナー（ただし結婚関連は除く）
]


def load_relationships_master() -> dict[str, Any]:
    """人物関係マスターデータを読み込み"""
    if not RELATIONSHIPS_MASTER.exists():
        print(f"[INFO] マスターデータが存在しません: {RELATIONSHIPS_MASTER}")
        print("[INFO] 空のマスターデータを使用します")
        return {"relationships": {}, "meta": {"created": datetime.now().isoformat()}}

    with open(RELATIONSHIPS_MASTER, "r", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
        return data


def save_relationships_master(data: dict[str, Any]) -> None:
    """人物関係マスターデータを保存"""
    data["meta"]["updated"] = datetime.now().isoformat()
    with open(RELATIONSHIPS_MASTER, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[INFO] マスターデータを保存: {RELATIONSHIPS_MASTER}")


def normalize_name(name: str) -> str:
    """名前を正規化"""
    if not name:
        return ""
    # 敬称・称号を除去
    name = re.sub(r"(さん|氏|君|様|先生|博士|教授|女史)$", "", name)
    # 括弧内を除去
    name = re.sub(r"[（(][^)）]*[)）]", "", name)
    # 空白除去
    name = name.strip().replace(" ", "").replace("　", "")
    return name


def extract_spouse_mentions(text: str) -> list[dict]:
    """
    エピソードテキストから配偶者に関する記述を抽出

    Returns:
        list of dict: [{"relation": "夫/妻/結婚/...", "name": "配偶者名", "context": "前後の文脈"}]
    """
    if not text:
        return []

    mentions = []

    # 文脈除外パターンに該当する部分を一時的にマスク
    masked_text = text
    for pattern in EXCLUDE_CONTEXT_PATTERNS:
        masked_text = re.sub(pattern, "____", masked_text)

    for pattern in SPOUSE_PATTERNS:
        for match in re.finditer(pattern, masked_text):
            groups = match.groupdict()
            relation = groups.get("relation", "")
            name = groups.get("name", "")

            if not name or len(name) < 2:
                continue

            # 名前として不適切なパターンを除外
            normalized = normalize_name(name)
            if any(re.search(ex, normalized) for ex in EXCLUDE_NAME_PATTERNS):
                continue

            # 文脈を取得（前後30文字）
            start = max(0, match.start() - 30)
            end = min(len(text), match.end() + 30)
            context = text[start:end]

            mentions.append(
                {
                    "relation": relation,
                    "name": normalized,
                    "raw_name": name,
                    "context": context,
                    "match_text": match.group(0),
                }
            )

    return mentions


def check_relationship_consistency(
    person_name: str,
    mentioned_spouse: str,
    relation_type: str,
    master_data: dict,
) -> Optional[dict]:
    """
    抽出した配偶者情報とマスターデータを照合

    Returns:
        None: 一致または未登録
        dict: 不一致情報
    """
    relationships = master_data.get("relationships", {})

    # 正規化
    normalized_person = normalize_name(person_name)
    normalized_spouse = normalize_name(mentioned_spouse)

    # マスターに登録があるか確認
    if normalized_person not in relationships:
        return None  # 未登録はスキップ

    master_spouse = relationships[normalized_person].get("spouse", "")
    normalized_master_spouse = normalize_name(master_spouse)

    if not normalized_master_spouse:
        return None  # マスターに配偶者情報なし

    # 一致チェック
    if normalized_spouse == normalized_master_spouse:
        return None  # 一致

    # 部分一致チェック
    if normalized_spouse in normalized_master_spouse or normalized_master_spouse in normalized_spouse:
        return None  # 部分一致は許容

    # 不一致
    return {
        "person_name": person_name,
        "text_spouse": mentioned_spouse,
        "master_spouse": master_spouse,
        "relation_type": relation_type,
    }


def verify_relationships(csv_path: Path, master_data: dict[str, Any], verbose: bool = False) -> dict[str, Any]:
    """
    全エピソードの人物関係を検証

    Returns:
        dict: 検証結果
    """
    stats: dict[str, int] = {
        "total_episodes": 0,
        "episodes_with_spouse_mention": 0,
        "total_mentions": 0,
        "mismatches_found": 0,
        "unregistered_found": 0,
    }
    results: dict[str, Any] = {
        "mismatches": [],
        "unregistered": [],
        "stats": stats,
        "extracted_relationships": defaultdict(list),  # 新規発見した関係
    }

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    stats["total_episodes"] = len(rows)

    for row in rows:
        episode_id = row.get("episode_id", "")
        person_name = row.get("person_name", "")
        episode_text = row.get("episode_text", "")

        if not episode_text:
            continue

        # 配偶者記述を抽出
        mentions = extract_spouse_mentions(episode_text)

        if not mentions:
            continue

        stats["episodes_with_spouse_mention"] += 1
        stats["total_mentions"] += len(mentions)

        for mention in mentions:
            spouse_name = mention["name"]
            relation_type = mention["relation"]

            # マスターデータと照合
            mismatch = check_relationship_consistency(person_name, spouse_name, relation_type, master_data)

            if mismatch:
                mismatch["episode_id"] = episode_id
                mismatch["context"] = mention["context"]
                results["mismatches"].append(mismatch)
                stats["mismatches_found"] += 1
            else:
                # 未登録の関係を記録
                normalized_person = normalize_name(person_name)
                if normalized_person not in master_data.get("relationships", {}):
                    results["extracted_relationships"][normalized_person].append(
                        {
                            "spouse": spouse_name,
                            "relation": relation_type,
                            "episode_id": episode_id,
                            "context": mention["context"],
                        }
                    )
                    stats["unregistered_found"] += 1

            if verbose:
                print(f"  [{episode_id}] {person_name} -> {relation_type}: {spouse_name}")

    return results


def generate_report(results: dict[str, Any], output_path: Path) -> Path:
    """検証レポートを生成"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# 人物関係検証レポート\n\n")
        f.write(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # 統計
        stats = results["stats"]
        f.write("## 統計\n\n")
        f.write(f"- 総エピソード数: {stats['total_episodes']:,}\n")
        f.write(f"- 配偶者記述があるエピソード: {stats['episodes_with_spouse_mention']:,}\n")
        f.write(f"- 抽出した配偶者記述数: {stats['total_mentions']:,}\n")
        f.write(f"- マスターとの不一致: {stats['mismatches_found']:,}\n")
        f.write(f"- 未登録の関係: {stats['unregistered_found']:,}\n\n")

        # 不一致リスト
        f.write("## 不一致リスト\n\n")
        if results["mismatches"]:
            for item in results["mismatches"]:
                f.write(f"### [MISMATCH] {item['episode_id']}: {item['person_name']}の{item['relation_type']}\n")
                f.write(f"  - テキスト記載: {item['text_spouse']}\n")
                f.write(f"  - マスターデータ: {item['master_spouse']}\n")
                f.write(f"  - 文脈: ...{item['context']}...\n\n")
        else:
            f.write("不一致は検出されませんでした。\n\n")

        # 新規発見した関係（マスター未登録）
        f.write("## 新規発見した関係（マスター未登録）\n\n")
        if results["extracted_relationships"]:
            for person, relations in sorted(results["extracted_relationships"].items()):
                # 重複を排除して表示
                unique_spouses = {}
                for rel in relations:
                    spouse = rel["spouse"]
                    if spouse not in unique_spouses:
                        unique_spouses[spouse] = rel

                f.write(f"### {person}\n")
                for spouse, rel in unique_spouses.items():
                    f.write(f"  - {rel['relation']}: {spouse} (ep: {rel['episode_id']})\n")
                f.write("\n")
        else:
            f.write("新規関係は発見されませんでした。\n\n")

    return output_path


def print_summary(results: dict[str, Any]) -> None:
    """結果サマリーを表示"""
    print("\n" + "=" * 60)
    print("人物関係検証 - 結果サマリー")
    print("=" * 60)

    stats = results["stats"]
    print(f"\n総エピソード数: {stats['total_episodes']:,}")
    print(f"配偶者記述があるエピソード: {stats['episodes_with_spouse_mention']:,}")
    print(f"抽出した配偶者記述数: {stats['total_mentions']:,}")

    print(f"\n[MISMATCH] マスターとの不一致: {stats['mismatches_found']:,}")
    print(f"[NEW] 未登録の関係: {stats['unregistered_found']:,}")

    # サンプル表示
    if results["mismatches"]:
        print("\n--- 不一致サンプル（最大5件）---")
        for item in results["mismatches"][:5]:
            print(f"\n[MISMATCH] {item['episode_id']}: {item['person_name']}の{item['relation_type']}")
            print(f"  - テキスト記載: {item['text_spouse']}")
            print(f"  - マスターデータ: {item['master_spouse']}")

    if results["extracted_relationships"]:
        print("\n--- 新規発見した関係サンプル（最大5件）---")
        count = 0
        for person, relations in list(results["extracted_relationships"].items())[:5]:
            if relations:
                rel = relations[0]
                print(f"  {person} -> {rel['relation']}: {rel['spouse']}")
                count += 1
                if count >= 5:
                    break


def create_initial_master_template() -> dict[str, Any]:
    """
    初期マスターデータテンプレートを作成

    Returns:
        dict: 初期マスターデータ
    """
    return {
        "meta": {
            "description": "人物関係マスターデータ",
            "version": "1.0.0",
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
        },
        "relationships": {
            # サンプルエントリ
            "大島美幸": {
                "spouse": "鈴木おさむ",
                "spouse_occupation": "放送作家",
                "marriage_year": 2002,
                "notes": "",
            },
            "パティ・スミス": {
                "spouse": "フレッド・ソニック・スミス",
                "spouse_occupation": "ミュージシャン（MC5）",
                "marriage_year": 1980,
                "death_year": 1994,
                "notes": "夫フレッドは1994年に心臓発作で死去",
            },
        },
    }


def main():
    parser = argparse.ArgumentParser(description="エピソードテキスト内の人物関係記述をマスターデータと照合")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="検出のみ（デフォルト）",
    )
    parser.add_argument(
        "--report",
        type=str,
        help="レポート出力先パス",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="自動修正（将来対応、現在は未実装）",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="詳細表示",
    )
    parser.add_argument(
        "--init-master",
        action="store_true",
        help="マスターデータを初期化（存在しない場合のみ）",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("人物関係検証スクリプト")
    print("=" * 60)

    # マスターデータの初期化
    if args.init_master:
        if RELATIONSHIPS_MASTER.exists():
            print(f"[WARN] マスターデータは既に存在します: {RELATIONSHIPS_MASTER}")
            print("[WARN] 上書きを避けるため、初期化をスキップします")
        else:
            template = create_initial_master_template()
            RELATIONSHIPS_MASTER.parent.mkdir(parents=True, exist_ok=True)
            with open(RELATIONSHIPS_MASTER, "w", encoding="utf-8") as f:
                json.dump(template, f, ensure_ascii=False, indent=2)
            print(f"[INFO] マスターデータを初期化しました: {RELATIONSHIPS_MASTER}")
        return

    # 自動修正は未実装
    if args.fix:
        print("[WARN] --fix オプションは将来対応予定です。現在は未実装です。")
        print("[INFO] --dry-run モードで実行します。")

    # ファイル存在確認
    if not MASTER_CSV.exists():
        print(f"[ERROR] CSVファイルが見つかりません: {MASTER_CSV}")
        sys.exit(1)

    # マスターデータ読み込み
    master_data = load_relationships_master()
    print(f"\n入力ファイル: {MASTER_CSV}")
    print(f"マスターデータ: {RELATIONSHIPS_MASTER}")
    print(f"登録済み関係数: {len(master_data.get('relationships', {}))}")

    # 検証実行
    print("\n検証中...")
    results = verify_relationships(MASTER_CSV, master_data, verbose=args.verbose)

    # サマリー表示
    print_summary(results)

    # レポート生成
    if args.report:
        report_path = Path(args.report)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = DEFAULT_REPORT_DIR / f"person_relationships_report_{timestamp}.md"

    report_file = generate_report(results, report_path)
    print(f"\nレポート生成完了: {report_file}")

    # 終了コード
    if results["mismatches"]:
        print(f"\n[WARN] {len(results['mismatches'])} 件の不一致が検出されました")
        sys.exit(1)
    else:
        print("\n[OK] 不一致は検出されませんでした")
        sys.exit(0)


if __name__ == "__main__":
    main()
