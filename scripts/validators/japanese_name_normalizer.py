#!/usr/bin/env python3
"""
EPUP: 日本人名正規化バリデータ

機能:
1. ローマ字→カタカナ変換による日本人名検出
2. カタカナ音訳→漢字表記の候補提示
3. Wikidata照合による正式名確認

使用方法:
    # 全件スキャン
    python scripts/validators/japanese_name_normalizer.py

    # 特定の名前をチェック
    python scripts/validators/japanese_name_normalizer.py --check "Akira Kurosawa"

    # 自動修正（要確認）
    python scripts/validators/japanese_name_normalizer.py --fix
"""

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# pykakasi（ローマ字変換）
try:
    import pykakasi

    HAS_PYKAKASI = True
except ImportError:
    HAS_PYKAKASI = False

# ========================================
# 定数
# ========================================

MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"

# ローマ字パターン（日本人名らしきもの）
ROMAJI_PATTERN = re.compile(
    r"^[A-Z][a-z]+\s+[A-Z][a-z]+$"  # "Akira Kurosawa" 形式
    r"|^[A-Z][a-z]+-[A-Z][a-z]+\s+[A-Z][a-z]+$"  # "Ken-ichi Yamamoto" 形式
)

# カタカナ音訳パターン（日本人名らしきもの）
# 日本人名のカタカナ音訳は通常、姓が末尾に来る（クロサワ、ミヤザキ等）
KATAKANA_ROMAJI_PATTERN = re.compile(
    r"^[ア-ン]{2,6}・[ア-ン]{2,6}$"  # "アキラ・クロサワ" 形式（短い）
)

# カタカナ日本人姓リスト（音訳検出用）
JAPANESE_SURNAMES_KATAKANA = {
    "クロサワ",
    "ミヤザキ",
    "タカハタ",
    "キタノ",
    "オズ",
    "ミゾグチ",
    "ムラカミ",
    "ミシマ",
    "カワバタ",
    "オオエ",
    "アクタガワ",
    "ナツメ",
    "ダザイ",
    "テヅカ",
    "トリヤマ",
    "タカハシ",
    "オダ",
    "サカモト",
    "オノ",
    "オザワ",
    "ヤマナカ",
    "モリタ",
    "ホンダ",
    "マツシタ",
    "トヨトミ",
    "トクガワ",
    "コジマ",
}

# 日本人姓リスト（ローマ字）- 検出用
JAPANESE_SURNAMES_ROMAJI = {
    "Abe",
    "Aoki",
    "Fujita",
    "Fukuda",
    "Goto",
    "Hashimoto",
    "Hayashi",
    "Honda",
    "Inoue",
    "Ishida",
    "Ito",
    "Iwasaki",
    "Kato",
    "Kawabata",
    "Kimura",
    "Kobayashi",
    "Kondo",
    "Kurosawa",
    "Maeda",
    "Matsuda",
    "Matsumoto",
    "Matsushita",
    "Miyamoto",
    "Miyazaki",
    "Mori",
    "Morita",
    "Murakami",
    "Nakamura",
    "Nakayama",
    "Nishida",
    "Oda",
    "Ogawa",
    "Okada",
    "Okazaki",
    "Ono",
    "Ozawa",
    "Saito",
    "Sakamoto",
    "Sasaki",
    "Sato",
    "Shimizu",
    "Suzuki",
    "Takahashi",
    "Takeda",
    "Tanaka",
    "Tezuka",
    "Tokugawa",
    "Toyotomi",
    "Ueda",
    "Watanabe",
    "Yamada",
    "Yamaguchi",
    "Yamamoto",
    "Yamanaka",
    "Yamashita",
    "Yoshida",
}


def is_likely_japanese_romaji(name: str) -> bool:
    """ローマ字表記の日本人名かどうかを判定"""
    if not ROMAJI_PATTERN.match(name):
        return False

    # 姓がリストにあるか確認
    parts = name.split()
    if len(parts) >= 2:
        # "Firstname Lastname" または "Lastname Firstname" 形式
        if parts[-1] in JAPANESE_SURNAMES_ROMAJI or parts[0] in JAPANESE_SURNAMES_ROMAJI:
            return True

    return False


def is_katakana_romaji(name: str) -> bool:
    """カタカナ音訳の日本人名かどうかを判定"""
    if not KATAKANA_ROMAJI_PATTERN.match(name):
        return False

    # 姓がリストにあるか確認
    parts = name.split("・")
    if len(parts) == 2:
        # "名・姓" 形式（アキラ・クロサワ）
        if parts[-1] in JAPANESE_SURNAMES_KATAKANA:
            return True

    return False


def romaji_to_katakana(romaji: str) -> Optional[str]:
    """ローマ字をカタカナに変換"""
    if not HAS_PYKAKASI:
        return None

    kks = pykakasi.kakasi()
    result = kks.convert(romaji.lower())
    katakana = "".join([item["kana"] for item in result])
    return katakana


def query_wikidata_japanese_label(name: str) -> Optional[str]:
    """Wikidataで日本語ラベルを検索"""
    try:
        # Wikidata検索API
        search_url = "https://www.wikidata.org/w/api.php"
        params = {
            "action": "wbsearchentities",
            "search": name,
            "language": "en",
            "format": "json",
            "limit": 5,
        }

        response = requests.get(search_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get("search"):
            return None

        # 最初の候補のQIDを取得
        qid = data["search"][0]["id"]

        # エンティティ詳細を取得
        entity_url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
        entity_response = requests.get(entity_url, timeout=10)
        entity_response.raise_for_status()
        entity_data = entity_response.json()

        # 日本語ラベルを取得
        labels = entity_data.get("entities", {}).get(qid, {}).get("labels", {})
        if "ja" in labels:
            return labels["ja"]["value"]

        return None

    except Exception as e:
        print(f"  Wikidata照合エラー: {e}")
        return None


def detect_non_standard_japanese_names(csv_path: Path) -> list[dict]:
    """非標準の日本人名表記を検出"""
    df = pd.read_csv(csv_path, low_memory=False)

    # 人物名のユニークリストを取得
    persons = df.groupby("person_id").agg({"person_name": "first", "person_type": "first"}).reset_index()

    issues = []

    for _, row in persons.iterrows():
        name = str(row["person_name"])
        person_type = str(row.get("person_type", "")).upper()

        # 架空キャラはスキップ
        if "FICTIONAL" in person_type:
            continue

        issue = None

        # ローマ字表記チェック
        if is_likely_japanese_romaji(name):
            issue = {
                "person_id": row["person_id"],
                "person_name": name,
                "issue_type": "ROMAJI",
                "suggestion": None,
            }

        # カタカナ音訳チェック
        elif is_katakana_romaji(name):
            issue = {
                "person_id": row["person_id"],
                "person_name": name,
                "issue_type": "KATAKANA_ROMAJI",
                "suggestion": None,
            }

        if issue:
            issues.append(issue)

    return issues


def enrich_with_wikidata(issues: list[dict], max_queries: int = 50) -> list[dict]:
    """Wikidataで正式名を照合"""
    enriched = []
    query_count = 0

    for issue in issues:
        if query_count >= max_queries:
            print(f"  ⚠️ Wikidata照合上限({max_queries}件)に到達")
            issue["suggestion"] = "(照合スキップ)"
            enriched.append(issue)
            continue

        name = issue["person_name"]
        print(f"  照合中: {name}")

        ja_label = query_wikidata_japanese_label(name)
        query_count += 1

        if ja_label and ja_label != name:
            issue["suggestion"] = ja_label
            print(f"    → {ja_label}")
        else:
            issue["suggestion"] = "(見つからず)"

        enriched.append(issue)
        time.sleep(0.5)  # レート制限

    return enriched


def main():
    parser = argparse.ArgumentParser(description="EPUP: 日本人名正規化バリデータ")
    parser.add_argument("--check", type=str, help="特定の名前をチェック")
    parser.add_argument("--fix", action="store_true", help="自動修正を実行")
    parser.add_argument("--no-wikidata", action="store_true", help="Wikidata照合をスキップ")
    args = parser.parse_args()

    if args.check:
        # 単一名前のチェック
        name = args.check
        print(f"=== 名前チェック: {name} ===\n")

        if is_likely_japanese_romaji(name):
            print("検出: ローマ字表記の日本人名")
            if not args.no_wikidata:
                ja_label = query_wikidata_japanese_label(name)
                if ja_label:
                    print(f"Wikidata日本語ラベル: {ja_label}")
        elif is_katakana_romaji(name):
            print("検出: カタカナ音訳の日本人名")
        else:
            print("問題なし: 標準的な表記")
        return 0

    # 全件スキャン
    if not MASTER_CSV.exists():
        print(f"❌ CSVファイルが見つかりません: {MASTER_CSV}")
        return 1

    print("🔍 非標準の日本人名表記を検出中...\n")
    issues = detect_non_standard_japanese_names(MASTER_CSV)

    if not issues:
        print("✅ 非標準の日本人名表記は見つかりませんでした")
        return 0

    print(f"検出件数: {len(issues)}件\n")

    # タイプ別集計
    romaji_count = sum(1 for i in issues if i["issue_type"] == "ROMAJI")
    katakana_count = sum(1 for i in issues if i["issue_type"] == "KATAKANA_ROMAJI")

    print(f"  ローマ字表記: {romaji_count}件")
    print(f"  カタカナ音訳: {katakana_count}件")
    print()

    # Wikidata照合
    if not args.no_wikidata:
        print("📡 Wikidata照合中...\n")
        issues = enrich_with_wikidata(issues)
        print()

    # 結果表示
    print("=== 検出結果 ===\n")
    for issue in issues:
        suggestion = issue.get("suggestion", "")
        if suggestion and suggestion not in ["(照合スキップ)", "(見つからず)"]:
            print(f"  {issue['person_id']}: {issue['person_name']} → {suggestion}")
        else:
            print(f"  {issue['person_id']}: {issue['person_name']} ({issue['issue_type']})")

    if args.fix:
        print("\n⚠️ 自動修正は未実装です。手動で修正してください。")

    return 0


if __name__ == "__main__":
    exit(main())
