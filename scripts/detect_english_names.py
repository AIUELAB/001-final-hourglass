#!/usr/bin/env python3
"""
英語表記人物名の検出・分類スクリプト

機能:
1. CSVから英語表記の人物名を検出
2. GROUP_MEMBER_MAP/SOLO_ARTISTSから英語名維持リストを自動生成
3. 変換対象/維持対象/レビュー必要の3分類に振り分け
4. 結果をJSON/CSVで出力

Usage:
    python scripts/detect_english_names.py [--output-dir OUTPUT_DIR]
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.group_master import GROUP_ENTITIES, GROUP_MEMBER_MAP, SOLO_ARTISTS


# ========================================
# 英語名判定ロジック
# ========================================


def is_english_name(name: str) -> bool:
    """
    英語表記の名前かどうか判定

    判定基準:
    - 2文字以上連続する英字を含む
    - ただし、日本語（ひらがな、カタカナ、漢字）を含む場合は除外

    Args:
        name: 人物名

    Returns:
        英語表記ならTrue
    """
    if not name or pd.isna(name):
        return False

    name = str(name).strip()

    # 日本語文字（ひらがな、カタカナ、漢字）を含むか
    japanese_pattern = r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]"
    has_japanese = bool(re.search(japanese_pattern, name))

    # 2文字以上連続する英字を含むか
    english_pattern = r"[A-Za-z]{2,}"
    has_english = bool(re.search(english_pattern, name))

    # 英字のみ（日本語なし）で構成されている場合
    if has_english and not has_japanese:
        return True

    return False


def is_pure_english_name(name: str) -> bool:
    """
    純粋な英語名かどうか判定（英字、スペース、記号のみ）

    Args:
        name: 人物名

    Returns:
        純粋な英語名ならTrue
    """
    if not name or pd.isna(name):
        return False

    name = str(name).strip()
    # 英字、スペース、ピリオド、ハイフン、アポストロフィのみ
    pattern = r"^[A-Za-z\s\.\-\'&]+$"
    return bool(re.match(pattern, name))


def is_romanized_japanese_name(name: str) -> bool:
    """
    日本人名のローマ字表記かどうか判定

    判定基準:
    - 2-3単語構成（姓 名 or 姓 ミドル 名）
    - 各単語が先頭大文字
    - 日本人名によくあるパターン（母音で終わる、特定の音節）
    - 西洋人名の特徴を持たない

    Args:
        name: 人物名

    Returns:
        日本人名のローマ字表記の可能性が高ければTrue
    """
    if not name or pd.isna(name):
        return False

    name = str(name).strip()

    # 純粋な英語名でない場合は対象外
    if not is_pure_english_name(name):
        return False

    # スペースで分割
    parts = name.split()

    # 2-3単語構成でない場合は対象外
    if len(parts) < 2 or len(parts) > 3:
        return False

    # 各単語が先頭大文字かチェック
    for part in parts:
        if not part[0].isupper():
            return False

    # 一般的な西洋人ファーストネーム（日本人名ではない）
    western_first_names = {
        # 男性名
        "michael",
        "john",
        "james",
        "robert",
        "david",
        "william",
        "richard",
        "thomas",
        "charles",
        "daniel",
        "matthew",
        "anthony",
        "mark",
        "paul",
        "steven",
        "andrew",
        "joshua",
        "kenneth",
        "kevin",
        "brian",
        "george",
        "edward",
        "ronald",
        "timothy",
        "jason",
        "jeffrey",
        "ryan",
        "jacob",
        "gary",
        "nicholas",
        "eric",
        "jonathan",
        "stephen",
        "larry",
        "justin",
        "scott",
        "brandon",
        "benjamin",
        "samuel",
        "raymond",
        "gregory",
        "frank",
        "alexander",
        "patrick",
        "raymond",
        "jack",
        "dennis",
        "jerry",
        "tyler",
        "aaron",
        "jose",
        "adam",
        "henry",
        "nathan",
        "douglas",
        "zachary",
        "peter",
        "kyle",
        "noah",
        "ethan",
        "jeremy",
        "walter",
        "christian",
        "keith",
        "roger",
        "terry",
        "austin",
        "sean",
        "gerald",
        "carl",
        "harold",
        "dylan",
        "arthur",
        "lawrence",
        "jordan",
        "jesse",
        "bryan",
        "billy",
        "bruce",
        "gabriel",
        "joe",
        "logan",
        "albert",
        "willie",
        "alan",
        "eugene",
        "russell",
        "louis",
        "vincent",
        "philip",
        "bobby",
        "johnny",
        "bradley",
        "elliot",
        "elliott",
        "leonardo",
        "tom",
        "brad",
        # 女性名
        "mary",
        "patricia",
        "jennifer",
        "linda",
        "elizabeth",
        "barbara",
        "susan",
        "jessica",
        "sarah",
        "karen",
        "lisa",
        "nancy",
        "betty",
        "margaret",
        "sandra",
        "ashley",
        "kimberly",
        "emily",
        "donna",
        "michelle",
        "dorothy",
        "carol",
        "amanda",
        "melissa",
        "deborah",
        "stephanie",
        "rebecca",
        "sharon",
        "laura",
        "cynthia",
        "kathleen",
        "amy",
        "angela",
        "shirley",
        "anna",
        "brenda",
        "pamela",
        "emma",
        "nicole",
        "helen",
        "samantha",
        "katherine",
        "christine",
        "debra",
        "rachel",
        "carolyn",
        "janet",
        "catherine",
        "maria",
        "heather",
        "diane",
        "ruth",
        "julie",
        "olivia",
        "joyce",
        "virginia",
        "victoria",
        "kelly",
        "lauren",
        "christina",
        "joan",
        "evelyn",
        "judith",
        "megan",
        "andrea",
        "cheryl",
        "hannah",
        "jacqueline",
        "martha",
        "gloria",
        "teresa",
        "ann",
        "sara",
        "madison",
        "frances",
        "kathryn",
        "janice",
        "jean",
        "abigail",
        "alice",
        "judy",
        "sophia",
        "grace",
        "denise",
        "amber",
        "doris",
        "marilyn",
        "danielle",
        "beverly",
        "isabella",
        "theresa",
        "diana",
        "natalie",
        "brittany",
        "charlotte",
        "marie",
        "kayla",
        "alexis",
        "lori",
        "scarlett",
        "margot",
    }

    # 一般的な西洋人ラストネーム
    western_surnames = {
        "smith",
        "johnson",
        "williams",
        "brown",
        "jones",
        "garcia",
        "miller",
        "davis",
        "rodriguez",
        "martinez",
        "hernandez",
        "lopez",
        "gonzalez",
        "wilson",
        "anderson",
        "thomas",
        "taylor",
        "moore",
        "jackson",
        "martin",
        "lee",
        "perez",
        "thompson",
        "white",
        "harris",
        "sanchez",
        "clark",
        "ramirez",
        "lewis",
        "robinson",
        "walker",
        "young",
        "allen",
        "king",
        "wright",
        "scott",
        "torres",
        "nguyen",
        "hill",
        "flores",
        "green",
        "adams",
        "nelson",
        "baker",
        "hall",
        "rivera",
        "campbell",
        "mitchell",
        "carter",
        "roberts",
        "page",
        "pitt",
        "jolie",
        "cruise",
        "hanks",
        "dicaprio",
        "clooney",
        "streep",
        "washington",
        "freeman",
        "ford",
        "schwarzenegger",
        "stallone",
        "willis",
        "gibson",
        "murray",
        "murphy",
        "lawrence",
        "stone",
        "watson",
        "portman",
        "kidman",
        "blanchett",
        "theron",
        "hathaway",
        "winslet",
        "bullock",
        "aniston",
        "roberts",
        "fitzgerald",
        "hemingway",
        "shakespeare",
        "dickens",
        "twain",
        "spielberg",
        "scorsese",
        "tarantino",
        "nolan",
        "kubrick",
        "hitchcock",
        "musk",
        "bezos",
        "gates",
        "jobs",
        "zuckerberg",
        "buffett",
        "cook",
    }

    # ファーストネームが西洋人名なら対象外
    first_name = parts[0].lower()
    if first_name in western_first_names:
        return False

    # ラストネームが西洋人名なら対象外
    last_name = parts[-1].lower()
    if last_name in western_surnames:
        return False

    # 日本人名によくある特徴をチェック
    japanese_surname_endings = [
        # 日本人の姓によくある末尾（より広範なパターン）
        r"(moto|mura|shima|kawa|yama|saki|zaki|gawa|hara|uchi|wara|"
        r"naka|mori|tani|oka|naga|hashi|matsu|sugi|ishi|ike|ueda|ota|"
        r"inoue|kimura|hayashi|yamamoto|watanabe|takahashi|tanaka|ito|"
        r"suzuki|yamada|sato|kobayashi|kato|yoshida|sasaki|yamaguchi|"
        r"matsumoto|inoue|kondo|fukuda|nishi|kitamura|"
        # 追加：より多くの姓パターン
        r"oguri|yoshizawa|imada|yokohama|yamazaki|hashimoto|"
        r"aragaki|nagano|komatsu|suda|ayase|"
        r"wada|honda|goto|fujita|okada|hasegawa|murakami|"
        r"nakamura|ishikawa|maeda|ogawa|okamoto|maruyama|"
        r"morita|nishimura|fujiwara|aoki|sakamoto|fukushima|"
        r"endo|sakai|shimizu|yamaguchi|sakurai|arai|takeda|"
        r"ueno|harada|kojima|ichikawa|miyamoto|kuroda|"
        r"takagi|matsuda|ishida|sugiyama|oishi|hirano|ozawa|"
        r"kawasaki|mizuno|tamura|yamauchi|imai|nakata|naito|"
        r"fujimoto|kawaguchi|matsui|kaneko|miyazaki|uchida|"
        r"ohno|sawada|kubo|kikuchi|sugawara|hirata|furukawa)$",
    ]

    japanese_given_name_endings = [
        # 日本人の名前によくある末尾（より広範なパターン）
        r"(ko|ro|ta|to|ya|ki|mi|ri|ka|na|ma|shi|ji|chi|go|zo|"
        r"suke|hiro|aki|ichi|kazu|taro|jiro|hei|bei|nosuke|"
        r"yuki|nori|masa|hide|yoshi|taka|nobu|tetsu|shin|ken|"
        r"ryu|sei|mei|rei|ai|yui|sakura|hana|miku|saki|nana|rina|"
        # 追加：より多くの日本人名パターン
        r"ryo|sho|shu|shun|jun|kei|yui|rui|sui|kai|rai|sora|"
        r"mio|rio|aoi|yua|runa|mina|hina|mana|sana|kana|rina|"
        r"keiko|yoko|akiko|junko|tomoko|noriko|haruko|sachiko|"
        r"haruka|ayaka|sayaka|asuka|madoka|chiaki|misaki|mizuki|"
        r"takeshi|makoto|hiroshi|satoshi|katsumi|atsushi|kazuya|"
        r"naoya|tomoya|yuya|takuya|tatsuya|shinya|junya|atsuya)$",
    ]

    # 姓がマッチするかチェック
    first_part_lower = parts[0].lower()
    surname_match = any(re.search(p, first_part_lower) for p in japanese_surname_endings)

    # 名がマッチするかチェック
    last_part_lower = parts[-1].lower()
    given_name_match = any(re.search(p, last_part_lower) for p in japanese_given_name_endings)

    # 姓または名のいずれかが日本人名パターンにマッチすればTrue
    return surname_match or given_name_match


def classify_name_type(name: str) -> str:
    """
    名前のタイプを分類

    Args:
        name: 人物名

    Returns:
        'romanized_japanese': 日本人名のローマ字表記
        'artist_name': アーティスト名（英語芸名）
        'western_name': 西洋人名
        'unknown': 判定不可
    """
    if not is_english_name(name):
        return "not_english"

    # 日本人名のローマ字表記パターン
    if is_romanized_japanese_name(name):
        return "romanized_japanese"

    # 全大文字または1単語 → アーティスト名の可能性
    if name.isupper() or " " not in name:
        return "artist_name"

    # Firstname Lastname 形式でローマ字パターンに該当しない → 西洋人名
    parts = name.split()
    if len(parts) >= 2 and all(p[0].isupper() for p in parts if p):
        return "western_name"

    return "unknown"


def extract_keep_english_names() -> Set[str]:
    """
    GROUP_MEMBER_MAPとSOLO_ARTISTSから英語名維持リストを自動生成

    Returns:
        英語名を維持すべきアーティスト名のセット
    """
    keep_names = set()

    # GROUP_MEMBER_MAPから英語名を抽出
    for name in GROUP_MEMBER_MAP.keys():
        if is_english_name(name):
            keep_names.add(name)

    # SOLO_ARTISTSから英語名を抽出
    for name in SOLO_ARTISTS:
        if is_english_name(name):
            keep_names.add(name)

    # GROUP_ENTITIESから英語名を抽出
    for name in GROUP_ENTITIES:
        if is_english_name(name):
            keep_names.add(name)

    # 追加の手動リスト（GROUP_MEMBER_MAPに登録されていない可能性のあるアーティスト）
    additional_keep = {
        # YouTuber
        "HIKAKIN",
        "SEIKIN",
        "Fischer's",
        # ヒップホップ/ラッパー
        "KREVA",
        "Zeebra",
        "KOHH",
        "Awich",
        "BAD HOP",
        "PUNPEE",
        # DJ/音楽プロデューサー
        "DJ KRUSH",
        "Nujabes",
        "tofubeats",
        "m-flo",
        # ファッション/クリエイター
        "NIGO",
        "KENZO",
        "MIKIKO",
        # K-POP/アジアポップ
        "DA PUMP",
        "BTS",
        "IU",
        "BLACKPINK",
        "TWICE",
        "EXO",
        "NCT",
        # ジャニーズ
        "KinKi Kids",
        "Hey! Say! JUMP",
        "SixTONES",
        "Snow Man",
        "King & Prince",
        "Kis-My-Ft2",
        "NEWS",
        "KAT-TUN",
        "A.B.C-Z",
        # 日本のロック/ポップバンド・グループ
        "X JAPAN",
        "GLAY",
        "LUNA SEA",
        "BABYMETAL",
        "globe",
        "TRF",
        "B'z",
        "ZARD",
        "WANDS",
        "DREAMS COME TRUE",
        "SEKAI NO OWARI",
        "Mrs. GREEN APPLE",
        "ONE OK ROCK",
        "MAN WITH A MISSION",
        "UVERworld",
        "Alexandros",
        "RADWIMPS",
        "GReeeeN",
        "supercell",
        "ClariS",
        "fripSide",
        "Kalafina",
        "Linked Horizon",
        "BUMP OF CHICKEN",
        "ASIAN KUNG-FU GENERATION",
        "Spitz",
        "L'Arc~en~Ciel",
        "L'Arc〜en〜Ciel",
        "NMB48",
        "AC/DC",
        # 日本のソロアーティスト（英語芸名）
        "Aimyon",
        "Fukase",
        "Ayase",
        "SAM",
        "Toshl",
        "Shelly",
        "Vaundy",
        "imase",
        "Mackenyu",
        "AI",
        "Reol",
        "Eve",
        "Superfly",
        "MISIA",
        "aiko",
        "Ado",
        "YOASOBI",
        "back number",
        # V系/ビジュアル系
        "MALICE MIZER",
        "DIR EN GREY",
        "the GazettE",
        "MUCC",
        # CHAGE and ASKA / ソロアーティスト
        "ASKA",
        "CHAGE",
        "UA",
        "DAOKO",
        "IKKO",
        "Aimer",
        "Rintaro",
        "PEACH-PIT",
        "ONE",
        "CLAMP",
        "aiiko",
        # バンド
        "ORANGE RANGE",
        "THE BLUE HEARTS",
        "SADS",
        # その他
        "BENI",
        "May J.",
        "Sowelu",
        "BoA",
        "JUJU",
        "miwa",
    }

    keep_names.update(additional_keep)

    return keep_names


# ========================================
# 分類ロジック
# ========================================


class EnglishNameDetector:
    """英語表記人物名の検出・分類クラス"""

    def __init__(self, csv_path: str):
        """
        Args:
            csv_path: MASTER_EPISODES_CURRENT.csvのパス
        """
        self.csv_path = csv_path
        self.df = pd.read_csv(csv_path, encoding="utf-8-sig")
        self.keep_english_names = extract_keep_english_names()

        # 結果格納用
        self.to_translate: List[Dict] = []  # 日本語化対象
        self.keep_english: List[Dict] = []  # 英語名維持
        self.review_required: List[Dict] = []  # レビュー必要
        self.all_english: List[Dict] = []  # 全英語表記

    def detect_all(self) -> Dict:
        """
        全人物を検出・分類

        Returns:
            検出結果のサマリー辞書
        """
        # ユニークな人物を抽出
        unique_persons = self.df.drop_duplicates("person_id")[
            ["person_id", "person_name", "category", "person_type"]
        ].copy()

        # 各人物を分類
        for _, row in unique_persons.iterrows():
            person_name = row["person_name"]

            if not is_english_name(person_name):
                continue

            person_data = {
                "person_id": row["person_id"],
                "person_name": person_name,
                "category": row.get("category", ""),
                "person_type": row.get("person_type", "REAL"),
                "is_pure_english": is_pure_english_name(person_name),
            }

            self.all_english.append(person_data)

            # 分類
            classification = self._classify(person_name, person_data)
            person_data["classification"] = classification
            name_type = person_data.get("name_type", "")
            person_data["reason"] = self._get_classification_reason(person_name, classification, name_type)

            if classification == "keep_english":
                self.keep_english.append(person_data)
            elif classification == "to_translate":
                self.to_translate.append(person_data)
            else:  # review_required
                self.review_required.append(person_data)

        return self._get_summary()

    def _classify(self, person_name: str, person_data: Dict) -> str:
        """
        人物を分類

        Args:
            person_name: 人物名
            person_data: 人物データ辞書

        Returns:
            分類結果（'keep_english', 'to_translate', 'review_required'）
        """
        # 1. KEEP_ENGLISH_NAMESリストに存在 → 英語名維持
        if person_name in self.keep_english_names:
            person_data["name_type"] = "artist_name"
            return "keep_english"

        # 大文字小文字を無視して比較
        for keep_name in self.keep_english_names:
            if person_name.lower() == keep_name.lower():
                person_data["name_type"] = "artist_name"
                return "keep_english"

        # 2. 名前タイプを分類
        name_type = classify_name_type(person_name)
        person_data["name_type"] = name_type

        # 3. 架空キャラクター → レビュー必要（特殊扱い）
        if person_data.get("person_type", "").upper() == "FICTIONAL":
            return "review_required"

        # 4. 名前タイプに基づく分類
        if name_type == "romanized_japanese":
            # 日本人名のローマ字表記 → 日本語化対象（漢字に変換）
            return "to_translate"
        elif name_type == "artist_name":
            # 英語芸名（1単語・全大文字など）→ レビュー必要（判断が必要）
            return "review_required"
        elif name_type == "western_name":
            # 西洋人名 → 日本語化対象（カタカナに変換）
            return "to_translate"
        elif name_type == "unknown":
            # 判定不可 → レビュー必要
            return "review_required"

        # 5. 純粋な英語名（海外有名人の可能性大）→ 日本語化対象
        if is_pure_english_name(person_name):
            return "to_translate"

        # 6. その他 → レビュー必要
        return "review_required"

    def _get_classification_reason(self, person_name: str, classification: str, name_type: str = "") -> str:
        """分類理由を取得"""
        if classification == "keep_english":
            if person_name in GROUP_MEMBER_MAP:
                group = GROUP_MEMBER_MAP[person_name]
                return f"GROUP_MEMBER_MAP登録済み（{group}）"
            elif person_name in SOLO_ARTISTS:
                return "SOLO_ARTISTS登録済み"
            elif person_name in GROUP_ENTITIES:
                return "GROUP_ENTITIES登録済み"
            else:
                return "追加維持リストに登録"
        elif classification == "to_translate":
            if name_type == "romanized_japanese":
                return "日本人名のローマ字表記（漢字変換対象）"
            elif name_type == "western_name":
                return "西洋人名（カタカナ変換対象）"
            else:
                return "純粋な英語名（海外有名人の可能性）"
        else:  # review_required
            if name_type == "artist_name":
                return "英語芸名の可能性（1単語/全大文字）- 要確認"
            elif name_type == "unknown":
                return "名前タイプ判定不可 - 人間レビュー推奨"
            else:
                return "自動判定不可（人間レビュー推奨）"

    def _get_summary(self) -> Dict:
        """検出結果のサマリーを取得"""
        # 名前タイプの内訳を集計
        name_type_counts = {}
        for item in self.all_english:
            name_type = item.get("name_type", "unknown")
            name_type_counts[name_type] = name_type_counts.get(name_type, 0) + 1

        return {
            "timestamp": datetime.now().isoformat(),
            "total_persons": len(self.df["person_id"].unique()),
            "english_name_count": len(self.all_english),
            "english_name_ratio": len(self.all_english) / len(self.df["person_id"].unique()) * 100,
            "classification": {
                "to_translate": len(self.to_translate),
                "keep_english": len(self.keep_english),
                "review_required": len(self.review_required),
            },
            "name_type_breakdown": name_type_counts,
            "keep_english_list_size": len(self.keep_english_names),
        }

    def export_results(self, output_dir: str):
        """
        結果をファイルに出力

        Args:
            output_dir: 出力ディレクトリパス
        """
        os.makedirs(output_dir, exist_ok=True)

        # 1. サマリーレポート（JSON）
        summary = self._get_summary()
        summary["keep_english_names"] = sorted(list(self.keep_english_names))

        report_path = os.path.join(output_dir, "english_names_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"✅ レポート出力: {report_path}")

        # 2. 日本語化対象（CSV）
        if self.to_translate:
            to_translate_path = os.path.join(output_dir, "to_translate.csv")
            pd.DataFrame(self.to_translate).to_csv(to_translate_path, index=False, encoding="utf-8-sig")
            print(f"✅ 日本語化対象出力: {to_translate_path} ({len(self.to_translate)}件)")

        # 3. 英語名維持（CSV）
        if self.keep_english:
            keep_english_path = os.path.join(output_dir, "keep_english.csv")
            pd.DataFrame(self.keep_english).to_csv(keep_english_path, index=False, encoding="utf-8-sig")
            print(f"✅ 英語名維持出力: {keep_english_path} ({len(self.keep_english)}件)")

        # 4. レビュー必要（CSV）
        if self.review_required:
            review_required_path = os.path.join(output_dir, "review_required.csv")
            pd.DataFrame(self.review_required).to_csv(review_required_path, index=False, encoding="utf-8-sig")
            print(f"✅ レビュー必要出力: {review_required_path} ({len(self.review_required)}件)")

        # 5. 全英語表記（CSV）
        if self.all_english:
            all_english_path = os.path.join(output_dir, "all_english_names.csv")
            pd.DataFrame(self.all_english).to_csv(all_english_path, index=False, encoding="utf-8-sig")
            print(f"✅ 全英語表記出力: {all_english_path} ({len(self.all_english)}件)")


def main():
    parser = argparse.ArgumentParser(description="英語表記人物名の検出・分類")
    parser.add_argument("--csv-path", default="preserved/data/MASTER_EPISODES_CURRENT.csv", help="入力CSVファイルパス")
    parser.add_argument("--output-dir", default="output/name_detection", help="出力ディレクトリ")

    args = parser.parse_args()

    # パスの解決
    project_root = Path(__file__).parent.parent
    csv_path = project_root / args.csv_path
    output_dir = project_root / args.output_dir

    if not csv_path.exists():
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        sys.exit(1)

    print("=" * 60)
    print("英語表記人物名の検出・分類")
    print("=" * 60)
    print(f"入力: {csv_path}")
    print(f"出力: {output_dir}")
    print()

    # 検出実行
    detector = EnglishNameDetector(str(csv_path))
    summary = detector.detect_all()

    # 結果表示
    print("=" * 60)
    print("検出結果サマリー")
    print("=" * 60)
    print(f"総人物数: {summary['total_persons']:,}")
    print(f"英語表記人物数: {summary['english_name_count']:,} ({summary['english_name_ratio']:.1f}%)")
    print()
    print("分類結果:")
    print(f"  - 日本語化対象: {summary['classification']['to_translate']:,}件")
    print(f"  - 英語名維持: {summary['classification']['keep_english']:,}件")
    print(f"  - レビュー必要: {summary['classification']['review_required']:,}件")
    print()
    print("名前タイプ内訳:")
    for name_type, count in sorted(summary.get("name_type_breakdown", {}).items()):
        print(f"  - {name_type}: {count:,}件")
    print()
    print(f"KEEP_ENGLISH_NAMESリストサイズ: {summary['keep_english_list_size']}件")
    print()

    # サンプル表示
    if detector.to_translate:
        print("=" * 60)
        print("日本語化対象サンプル（最初の15件）")
        print("=" * 60)
        for item in detector.to_translate[:15]:
            name_type = item.get("name_type", "unknown")
            print(f"  {item['person_name']} [{name_type}] - {item['reason']}")

    if detector.keep_english:
        print()
        print("=" * 60)
        print("英語名維持サンプル（最初の10件）")
        print("=" * 60)
        for item in detector.keep_english[:10]:
            print(f"  {item['person_name']} - {item['reason']}")

    if detector.review_required:
        print()
        print("=" * 60)
        print("レビュー必要サンプル（最初の10件）")
        print("=" * 60)
        for item in detector.review_required[:10]:
            name_type = item.get("name_type", "unknown")
            print(f"  {item['person_name']} [{name_type}] - {item['reason']}")

    # ファイル出力
    print()
    print("=" * 60)
    print("ファイル出力")
    print("=" * 60)
    detector.export_results(str(output_dir))

    print()
    print("✅ 検出完了")


if __name__ == "__main__":
    main()
