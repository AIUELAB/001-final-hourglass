#!/usr/bin/env python3
"""
グループ/コンビ名検出バリデーター

新規エピソード追加時に、person_nameがグループ/コンビ名でないことを検証する。
エピソードは個人専用であり、グループ/コンビには「年齢」が存在しないため禁止。

使用例:
    # 全体スキャン
    python scripts/validators/group_name_validator.py

    # 特定の名前をチェック
    python scripts/validators/group_name_validator.py --check "博多華丸・大吉"

    # CI/pre-commit用（違反があればexit 1）
    python scripts/validators/group_name_validator.py --strict
"""

import argparse
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

# ============================================
# 個人名の例外リスト（グループ名パターンに一致するが個人）
# ============================================
INDIVIDUAL_EXCEPTIONS = {
    # グループ名と同名だが個人
    "藤子・F・不二雄",  # 藤本弘の個人ペンネーム（1987年コンビ解消後）
    "アインシュタイン",  # アルベルト・アインシュタイン（物理学者）※お笑いコンビと同名
    "Ado",  # 歌手（個人）
    "Vaundy",  # 歌手（個人）
    "きゃりーぱみゅぱみゅ",  # 歌手（個人）
    "CLAMP",  # 漫画家グループだが、個人名として使用される場合あり
    "クイーン",  # 個人名に含まれる場合あり
    # グループプレフィックスパターンに一致するが個人
    "オードリー・ヘプバーン",
    "オードリー・タン",
    "ナイナイ・ジャイン",
    "ダウンタウン・アビー",  # 作品名だが念のため
    # 企業名プレフィックスと同形だが個人
    "ソニー・ロリンズ",  # ジャズサックス奏者（Sonny Rollins）
}

# ============================================
# 既知のグループ/コンビ名ブラックリスト
# ============================================
KNOWN_GROUP_NAMES = {
    # お笑いコンビ
    "ダウンタウン",
    "ナインティナイン",
    "ナイナイ",
    "とんねるず",
    "ウッチャンナンチャン",
    "爆笑問題",
    "さまぁ〜ず",
    "くりぃむしちゅー",
    "オードリー",
    "サンドウィッチマン",
    "千鳥",
    "かまいたち",
    "ミルクボーイ",
    "見取り図",
    # "アインシュタイン",  # 物理学者と同名のため除外
    "霜降り明星",
    "EXIT",
    "ぺこぱ",
    "マヂカルラブリー",
    "錦鯉",
    "ウエストランド",
    "博多華丸・大吉",
    "中川家",
    "麒麟",
    "ココリコ",
    "よゐこ",
    "雨上がり決死隊",
    "フットボールアワー",
    "チュートリアル",
    "ブラックマヨネーズ",
    "トータルテンボス",
    "タカアンドトシ",
    "NON STYLE",
    "パンクブーブー",
    "笑い飯",
    "スリムクラブ",
    "銀シャリ",
    "和牛",
    "ジャルジャル",
    "アンタッチャブル",
    "おぎやはぎ",
    "バナナマン",
    "東京03",
    "ハライチ",
    "三四郎",
    "さらば青春の光",
    "ニューヨーク",
    "インパルス",
    "ロンドンブーツ1号2号",
    "ロンブー",
    "今田東野",  # 今田耕司・東野幸治のコンビ
    "品川庄司",
    "次長課長",
    "キングコング",
    "オリエンタルラジオ",
    "オリラジ",
    "ピース",
    "南海キャンディーズ",
    "フルーツポンチ",
    "NON STYLE",
    "スピードワゴン",
    "ハリセンボン",
    "森三中",
    "北陽",
    "友近・ゆりやん",
    "阿佐ヶ谷姉妹",
    "メイプル超合金",
    "ゆにばーす",
    "ガンバレルーヤ",
    "中田カウス・ボタン",
    "林家ペー・パー子",
    "B&B",
    "ツービート",
    "紳助・竜介",
    "ザ・ぼんち",
    "オール阪神・巨人",
    "今いくよ・くるよ",
    "宮川大助・花子",
    "海原千里・万里",
    "かしまし娘",
    "大木こだま・ひびき",
    # 音楽グループ
    "チェッカーズ",
    "ワンダイレクション",
    "One Direction",
    "ビートルズ",
    "The Beatles",
    "ローリング・ストーンズ",
    "ザ・ローリング・ストーンズ",
    "ワム!",
    "Wham!",
    "クイーン",
    "レッド・ツェッペリン",
    "ピンク・フロイド",
    "U2",
    "コールドプレイ",
    "マルーン5",
    "BTS",
    "BLACKPINK",
    "TWICE",
    "NiziU",
    "乃木坂46",
    "櫻坂46",
    "日向坂46",
    "AKB48",
    "SKE48",
    "NMB48",
    "HKT48",
    "EXILE",
    "三代目J Soul Brothers",
    "GENERATIONS",
    "THE RAMPAGE",
    "嵐",
    "SMAP",
    "TOKIO",
    "V6",
    "KinKi Kids",
    "関ジャニ∞",
    "Hey! Say! JUMP",
    "Kis-My-Ft2",
    "Sexy Zone",
    "King & Prince",
    "Snow Man",
    "SixTONES",
    "なにわ男子",
    "光GENJI",  # 1980年代ジャニーズグループ
    "ダフト・パンク",
    "Daft Punk",
    "BAD HOP",
    "サカナクション",
    "RADWIMPS",
    "BUMP OF CHICKEN",
    "Mr.Children",
    "ミスチル",
    "スピッツ",
    "サザンオールスターズ",
    "サザン",
    "DREAMS COME TRUE",
    "ドリカム",
    "B'z",
    "スキマスイッチ",  # 音楽デュオ（大橋卓弥・常田真太郎）
    "L'Arc〜en〜Ciel",
    "ラルク",
    "X JAPAN",
    "GLAY",
    "LUNA SEA",
    "THE YELLOW MONKEY",
    "イエモン",
    "Perfume",
    "BABYMETAL",
    "きゃりーぱみゅぱみゅ",
    "YOASOBI",
    "King Gnu",
    "Official髭男dism",
    "ヒゲダン",
    "緑黄色社会",
    "マカロニえんぴつ",
    "Vaundy",
    # "Ado",  # 個人歌手のため除外
    # プロレス/格闘技タッグ
    "クラッシュ・ギャルズ",
    "ビューティ・ペア",
    "極悪同盟",
    "天龍源一郎・阿修羅原",
    "ロード・ウォリアーズ",
    # 漫画家ユニット
    "ゆでたまご",
    "藤子不二雄",
    "藤子・F・不二雄",
    "ゲッサン",
    "CLAMP",
    # その他
    "ローレル&ハーディ",
    "サイモン&ガーファンクル",
    "ホール&オーツ",
    "ボン・ジョヴィ",  # ロックバンド（個人名はジョン・ボン・ジョヴィ）
}

# ============================================
# グループプレフィックスパターン
# 「グループ名・個人名」形式を検出
# ============================================
GROUP_PREFIXES = [
    "ココリコ・",
    "麒麟・",
    "ナイナイ・",
    "森三中・",
    "ダウンタウン・",
    "ナインティナイン・",
    "とんねるず・",
    "ウッチャンナンチャン・",
    "爆笑問題・",
    "さまぁ〜ず・",
    "くりぃむしちゅー・",
    "オードリー・",
    "サンドウィッチマン・",
    "千鳥・",
    "かまいたち・",
    "吉本新喜劇・",
    "見取り図・",
    "霜降り明星・",
    "ぺこぱ・",
    "錦鯉・",
    "中川家・",
    "よゐこ・",
    "雨上がり決死隊・",
    "フットボールアワー・",
    "チュートリアル・",
    "ブラックマヨネーズ・",
    "アンタッチャブル・",
    "おぎやはぎ・",
    "バナナマン・",
    "ハライチ・",
    "インパルス・",
    "ロンブー・",
    "品川庄司・",
    "キングコング・",
    "オリラジ・",
    "南海キャンディーズ・",
    "ハリセンボン・",
    "阿佐ヶ谷姉妹・",
    # 音楽グループ（ソロ活動者がいる）
    "チェッカーズ・",
    "光GENJI・",
    "少年隊・",
    "シブがき隊・",
    "男闘呼組・",
    "SMAP・",
    "嵐・",
    "TOKIO・",
    "V6・",
    "関ジャニ∞・",
    "KinKi Kids・",
    "モーニング娘。・",
    "AKB48・",
    "乃木坂46・",
    "EXILE・",
    "三代目・",
]

# ============================================
# 組織名プレフィックスパターン（中点なし）
# 「組織名+個人名」形式を検出
# ============================================
ORGANIZATION_PREFIXES = [
    # 歴史的組織
    "新選組",
    # 職業・肩書き（人物名の前に付けてはいけない）
    "狂言師",
    "歌舞伎役者",
    "落語家",
    # アイドルグループ
    "AKB48",
    "乃木坂46",
    "櫻坂46",
    "日向坂46",
    # 芸能事務所
    "ジャニーズ",
    "吉本興業",
    "松竹芸能",
    "ワタナベ",
    # 企業名（役職付き人物名に使われがち）
    "日本電産",
    "キヤノン",
    "サントリー",
    "ユニクロ",
    "トヨタ",
    "ソニー",
    "パナソニック",
    "ソフトバンク",
    "楽天",
    "ファーストリテイリング",
    "任天堂",
]

# ============================================
# 企業名プレフィックスパターン（中点あり）
# 「企業名・人物名」形式を検出
# ============================================
COMPANY_PREFIXES = [
    "コナミ・",
    "フェイスブック・",
    "Facebook・",
    "グーグル・",
    "Google・",
    "アップル・",
    "Apple・",
    "マイクロソフト・",
    "Microsoft・",
    "アマゾン・",
    "Amazon・",
    "テスラ・",
    "Tesla・",
]

# ============================================
# 疑わしいパターン（警告レベル）
# ヒューリスティックで未知のグループ名を事前検出
# ============================================
SUSPICIOUS_PATTERNS = [
    # 「名前・名前」形式（コンビ名の可能性）
    r"^[ぁ-んァ-ン一-龥]{2,6}・[ぁ-んァ-ン一-龥]{2,6}$",
    # 「&」を含む（デュオ/コンビの可能性）
    r"[&＆]",
    # 数字付きグループ名パターン
    r"(AKB|SKE|NMB|HKT|STU|NGT)\d+",
    r"(乃木坂|櫻坂|日向坂|欅坂)\d+",
    # 「〇〇ズ」「〇〇ーズ」パターン（グループ名の可能性）
    r"ーズ$",
]

# ============================================
# 高度なヒューリスティックパターン（Layer 2強化）
# 構造的分析で未知パターンを検出
# ============================================
HEURISTIC_PATTERNS = {
    # パターンA: 日本グループ・個人名形式
    # 例: 「チェッカーズ・藤井フミヤ」「SMAP・木村拓哉」
    # 除外: 全カタカナ（外国人名）
    "group_individual": {
        "pattern": r"^(?![ァ-ヶー]+・[ァ-ヶー]+$)([ァ-ヶー\w]+)・([一-龥]{1,2}[一-龥ぁ-んァ-ヶー]{1,4})$",
        "description": "グループ名・個人名形式の可能性",
    },
    # パターンB: 職業接尾辞パターン
    # 例: 「狂言師野村万之丞」「落語家桂三枝」
    "job_title_prefix": {
        "pattern": r"^(狂言|歌舞伎|能|落語|漫才|漫談|講談|浪曲|奇術|手品)(師|家)([一-龥]{2,6})$",
        "description": "職業名+個人名形式の可能性",
    },
    # パターンC: 企業サフィックスパターン
    # 例: 「日本電産永守重信」
    "company_suffix": {
        "pattern": r"^(.+(?:電産|電機|電気|重工|商事|物産|製作所|工業|銀行|証券|保険|建設|不動産))([一-龥]{2,6})$",
        "description": "企業名+個人名形式の可能性",
    },
    # パターンD: 役職プレフィックス
    # 例: 「ユニクロ海外事業責任者玉塚元一」
    "role_prefix": {
        "pattern": r"^.+(社長|会長|CEO|代表|責任者|部長|専務|常務|取締役)([一-龥]{2,6})$",
        "description": "役職名+個人名形式の可能性",
    },
}


class GroupNameValidator:
    """グループ/コンビ名検出バリデーター"""

    def __init__(self, csv_path: str = "preserved/data/MASTER_EPISODES_CURRENT.csv"):
        self.csv_path = csv_path
        if Path(csv_path).exists():
            self.df = pd.read_csv(csv_path, low_memory=False)
        else:
            self.df = None

    def is_group_name(self, name: str) -> tuple[bool, str]:
        """
        名前がグループ/コンビ名かどうかを判定

        Returns:
            (is_group, reason): グループ名ならTrue、理由も返す
        """
        if pd.isna(name):
            return False, ""

        name = str(name).strip()

        # 0. 例外リストにある場合はスキップ（個人として許可）
        if name in INDIVIDUAL_EXCEPTIONS:
            return False, ""

        # 1. 既知のグループ名との完全一致
        if name in KNOWN_GROUP_NAMES:
            return True, f"既知のグループ/コンビ名: {name}"

        # 2. グループプレフィックスパターン
        for prefix in GROUP_PREFIXES:
            if name.startswith(prefix):
                return True, f"グループプレフィックス形式: {prefix}..."

        # 3. 組織名プレフィックスパターン（中点なし）
        for org in ORGANIZATION_PREFIXES:
            if name.startswith(org) and len(name) > len(org):
                # 組織名そのものではなく、組織名+個人名の形式
                return True, f"組織名プレフィックス形式: {org}..."

        # 4. 企業名プレフィックスパターン（中点あり）
        for company in COMPANY_PREFIXES:
            if name.startswith(company):
                return True, f"企業名プレフィックス形式: {company}..."

        # 5. 部分一致は誤検出が多いため削除
        # （例：「アレキサンダー・マックイーン」が「クイーン」と誤検出される）

        return False, ""

    def is_suspicious_name(self, name: str) -> tuple[bool, str]:
        """
        疑わしい名前パターンを検出（警告レベル）

        Returns:
            (is_suspicious, reason): 疑わしい場合True、理由も返す
        """
        if pd.isna(name):
            return False, ""

        name = str(name).strip()

        # 例外リストにある場合はスキップ
        if name in INDIVIDUAL_EXCEPTIONS:
            return False, ""

        # 基本パターン検出
        for pattern in SUSPICIOUS_PATTERNS:
            if re.search(pattern, name):
                return True, f"疑わしいパターン: {pattern}"

        # 高度なヒューリスティックパターン検出 (Layer 2強化)
        for key, config in HEURISTIC_PATTERNS.items():
            if re.search(config["pattern"], name):
                return True, f"[{key}] {config['description']}"

        return False, ""

    def validate_name(self, name: str) -> dict:
        """
        単一の名前を検証

        Returns:
            検証結果の辞書
        """
        is_group, group_reason = self.is_group_name(name)
        is_suspicious, suspicious_reason = self.is_suspicious_name(name)

        return {
            "name": name,
            "is_group": is_group,
            "group_reason": group_reason,
            "is_suspicious": is_suspicious,
            "suspicious_reason": suspicious_reason,
            "severity": "ERROR" if is_group else ("WARNING" if is_suspicious else "OK"),
        }

    def validate_all(self) -> dict:
        """
        マスターCSV内の全person_nameを検証

        Returns:
            検証結果の辞書
        """
        if self.df is None:
            return {"error": "CSVファイルが見つかりません"}

        unique_names = self.df["person_name"].dropna().unique()
        errors = []
        warnings = []

        for name in unique_names:
            result = self.validate_name(name)
            if result["is_group"]:
                # person_idとepisode_id情報も取得
                episodes = self.df[self.df["person_name"] == name]
                result["person_id"] = episodes["person_id"].iloc[0] if len(episodes) > 0 else None
                result["episode_count"] = len(episodes)
                result["episode_ids"] = episodes["episode_id"].tolist()[:5]  # 最大5件
                errors.append(result)
            elif result["is_suspicious"]:
                warnings.append(result)

        return {
            "timestamp": datetime.now().isoformat(),
            "total_unique_names": len(unique_names),
            "error_count": len(errors),
            "warning_count": len(warnings),
            "errors": errors,
            "warnings": warnings[:10],  # 警告は最大10件
            "status": "FAIL" if errors else ("WARNING" if warnings else "PASS"),
        }

    def suggest_individual_name(self, group_name: str) -> Optional[str]:
        """
        グループ名から個人名を推測（可能な場合）

        例: "ココリコ・田中直樹" → "田中直樹"
        """
        for prefix in GROUP_PREFIXES:
            if group_name.startswith(prefix):
                return group_name[len(prefix) :]
        return None


def main():
    parser = argparse.ArgumentParser(description="グループ/コンビ名検出バリデーター")
    parser.add_argument("--check", type=str, help="特定の名前をチェック")
    parser.add_argument("--strict", action="store_true", help="違反があればexit 1")
    parser.add_argument("--verbose", action="store_true", help="詳細出力")
    args = parser.parse_args()

    validator = GroupNameValidator()

    if args.check:
        # 特定の名前をチェック
        result = validator.validate_name(args.check)
        if result["is_group"]:
            print(f"❌ グループ/コンビ名: {args.check}")
            print(f"   理由: {result['group_reason']}")
            suggestion = validator.suggest_individual_name(args.check)
            if suggestion:
                print(f"   推奨: {suggestion}")
            return 1
        elif result["is_suspicious"]:
            print(f"⚠️  疑わしい名前: {args.check}")
            print(f"   理由: {result['suspicious_reason']}")
            return 0
        else:
            print(f"✅ OK: {args.check}")
            return 0

    # 全体スキャン
    result = validator.validate_all()

    print("=" * 60)
    print("グループ/コンビ名チェック")
    print("=" * 60)
    print(f"ユニーク人物名数: {result['total_unique_names']}")
    print(f"エラー (グループ名): {result['error_count']}件")
    print(f"警告 (疑わしい): {result['warning_count']}件")
    print(f"ステータス: {result['status']}")

    if result["errors"]:
        print("\n【エラー: グループ/コンビ名検出】")
        for err in result["errors"][:10]:
            print(f"  ❌ {err['name']} ({err['episode_count']}件)")
            print(f"     理由: {err['group_reason']}")
            suggestion = validator.suggest_individual_name(err["name"])
            if suggestion:
                print(f"     推奨: → {suggestion}")

    if args.verbose and result["warnings"]:
        print("\n【警告: 疑わしいパターン】")
        for warn in result["warnings"][:5]:
            print(f"  ⚠️  {warn['name']}")
            print(f"     理由: {warn['suspicious_reason']}")

    if args.strict and result["error_count"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    exit(main())
