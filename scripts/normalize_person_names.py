#!/usr/bin/env python3
"""
人物名正規化スクリプト

機能:
1. 肩書/所属/関係性の混入パターンを検出
2. 高信頼度のものは自動修正
3. 低信頼度のものは保留してレビュー用レポート出力

使用方法:
    # ドライラン（検出のみ）
    python scripts/normalize_person_names.py --dry-run

    # 自動修正実行（信頼度≥0.85）
    python scripts/normalize_person_names.py --execute

    # LLM検証付き
    python scripts/normalize_person_names.py --use-llm --execute

    # 特定パターンのみ処理
    python scripts/normalize_person_names.py --pattern TITLE_ROLE --dry-run

環境変数:
    ANTHROPIC_API_KEY: LLM検証を使用する場合に必要
"""

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Anthropic API（オプション）
try:
    import anthropic

    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

# ========================================
# 定数定義
# ========================================

CSV_PATH = PROJECT_ROOT / "preserved" / "MASTER_EPISODES_CURRENT.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"

# 西洋人名のファーストネーム（誤分割防止）
WESTERN_FIRST_NAMES = {
    # アルファベット順（一般的なカタカナ表記）
    "アーサー",
    "アイザック",
    "アガサ",
    "アダム",
    "アドルフ",
    "アラン",
    "アルバート",
    "アルフレッド",
    "アレクサンダー",
    "アンソニー",
    "アンディ",
    "アンドリュー",
    "イーロン",
    "ウィリアム",
    "エディ",
    "エドガー",
    "エドワード",
    "エマ",
    "エミリー",
    "エリザベス",
    "エリック",
    "エルトン",
    "オードリー",
    "オスカー",
    "カール",
    "キース",
    "クリス",
    "クリストファー",
    "グレン",
    "ケビン",
    "ジェームズ",
    "ジェーン",
    "ジェフ",
    "ジミー",
    "ジャック",
    "ジャン",
    "ジョージ",
    "ジョセフ",
    "ジョナサン",
    "ジョン",
    "スティーブ",
    "スティーブン",
    "ダニエル",
    "チャールズ",
    "チャック",
    "ティム",
    "デイビッド",
    "デイヴ",
    "トーマス",
    "トム",
    "ナタリー",
    "ニール",
    "ニコラス",
    "ニック",
    "ハリー",
    "バート",
    "パトリック",
    "ビル",
    "フィリップ",
    "フランク",
    "フレディ",
    "フレデリック",
    "ブライアン",
    "ブルース",
    "ヘンリー",
    "ベン",
    "ベンジャミン",
    "ボブ",
    "ポール",
    "マーク",
    "マーティン",
    "マイク",
    "マイケル",
    "マシュー",
    "マックス",
    "マリー",
    "ミック",
    "レイ",
    "リチャード",
    "リンダ",
    "ルイ",
    "レオナルド",
    "ロジャー",
    "ロバート",
    "ロン",
    "ロナルド",
    # イニシャル
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
    "K",
    "L",
    "M",
    "N",
    "O",
    "P",
    "Q",
    "R",
    "S",
    "T",
    "U",
    "V",
    "W",
    "X",
    "Y",
    "Z",
    # 藤子・F・不二雄対策
    "藤子",
}

# 肩書/役職パターン
TITLE_KEYWORDS = [
    "創業者",
    "設立者",
    "創始者",
    "会長",
    "社長",
    "CEO",
    "副社長",
    "元CEO",
    "元会長",
    "元社長",
    "現会長",
    "共同開発者",
    "共同創業者",
]

# 職業パターン
PROFESSION_KEYWORDS = [
    "落語家",
    "声優",
    "作詞家",
    "作曲家",
    "漫画家",
    "陶芸家",
    "書道家",
    "華道家",
    "俳人",
    "能楽師",
    "漆芸家",
    "版画家",
    "日本画家",
    "現代美術家",
    "作庭家",
    "音楽家",
    "オペラ歌手",
    "コメディアン",
]

# スポーツカテゴリ
SPORT_KEYWORDS = [
    "野球",
    "サッカー",
    "柔道",
    "競泳",
    "体操",
    "陸上",
    "テニス",
    "ゴルフ",
    "フィギュア",
    "スノーボード",
    "スケート",
    "卓球",
    "相撲",
    "バスケ",
    "ラグビー",
    "バレーボール",
    "マラソン",
    "水泳飛込み",
    "女子レスリング",
    "アイスホッケー",
]

# リーグ/組織
LEAGUE_KEYWORDS = [
    "NBA",
    "NFL",
    "F1",
    "UFC",
    "NHL",
    "MLB",
]

# 関係性パターン
RELATIONSHIP_KEYWORDS = [
    "の息子",
    "の娘",
    "の弟子",
    "の後継者",
    "の兄弟",
    "の孫",
    "の妻",
    "の夫",
    "の同僚",
]

# 企業/組織名（所属パターン）
COMPANY_KEYWORDS = [
    "CD Projekt",
    "Epic Games",
    "Rockstar",
    "Ubisoft",
    "Electronic Arts",
    "アリババ",
    "テスラ",
    "スペースX",
    "フェイスブック",
    "フェデックス",
    "バークシャー・ハサウェイ",
    "ソフトバンク",
    "ファーストリテイリング",
    "セブンイレブン",
    "キーエンス",
    "ソニー",
    "パナソニック",
    "任天堂",
    "カプコン",
    "スクウェア・エニックス",
    "バンダイナムコ",
    "理化学研究所",
    "島津製作所",
    "青山学院大学",
    "前田建設工業",
    "楽天",
    "福岡ソフトバンクホークス",
    "レアル・マドリード",
    "マンチェスター・シティ",
    "バルセロナ",
]

# チーム名（スポーツチーム）
TEAM_KEYWORDS = [
    "レアル・マドリリード",
    "レアル・マドリード",
    "マンチェスター・シティ",
    "バルセロナ",
]


@dataclass
class NormalizationResult:
    """正規化結果"""

    original_name: str
    normalized_name: str
    title: Optional[str]
    affiliation: Optional[str]
    pattern_type: str
    confidence: float
    requires_review: bool
    match_detail: str  # マッチした詳細


class PersonNameNormalizer:
    """人物名正規化エンジン"""

    def __init__(self, min_confidence: float = 0.85, use_llm: bool = False):
        self.min_confidence = min_confidence
        self.use_llm = use_llm
        self.anthropic_client = None

        if use_llm and HAS_ANTHROPIC:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if api_key:
                self.anthropic_client = anthropic.Anthropic(api_key=api_key)

    def is_western_name(self, name: str) -> bool:
        """西洋人名パターンかどうか判定"""
        if "・" not in name:
            return False

        # 関係性キーワードを含む場合は西洋人名ではない
        for rel in RELATIONSHIP_KEYWORDS:
            if rel in name:
                return False

        parts = name.split("・")
        first_part = parts[0]

        # ファーストネームリストに含まれる
        if first_part in WESTERN_FIRST_NAMES:
            return True

        # 全部カタカナ（西洋人名の可能性）
        if self._is_all_katakana(name.replace("・", "")):
            # 2パート以上で、最初のパートが長い（3文字以上）
            if len(parts) >= 2 and len(first_part) >= 3:
                return True

        return False

    def _is_all_katakana(self, text: str) -> bool:
        """全てカタカナかどうか"""
        for char in text:
            if not ("\u30a0" <= char <= "\u30ff" or char in "ー・"):
                return False
        return True

    def normalize(self, person_name: str) -> Optional[NormalizationResult]:
        """人物名を正規化"""
        if not person_name or pd.isna(person_name):
            return None

        # 西洋人名チェック
        if self.is_western_name(person_name):
            return None

        # パターンマッチング（優先度順）
        result = self._match_affiliation_prefix(person_name)
        if result:
            return result

        result = self._match_sport_prefix(person_name)
        if result:
            return result

        result = self._match_profession_prefix(person_name)
        if result:
            return result

        result = self._match_title_role(person_name)
        if result:
            return result

        result = self._match_relationship(person_name)
        if result:
            return result

        result = self._match_team_member(person_name)
        if result:
            return result

        result = self._match_league_prefix(person_name)
        if result:
            return result

        return None

    def _match_affiliation_prefix(self, name: str) -> Optional[NormalizationResult]:
        """会社・人物 形式の検出"""
        for company in COMPANY_KEYWORDS:
            # 会社・人物 形式
            pattern = f"^{re.escape(company)}・(.+)$"
            match = re.match(pattern, name)
            if match:
                person = match.group(1)
                return NormalizationResult(
                    original_name=name,
                    normalized_name=person,
                    title=None,
                    affiliation=company,
                    pattern_type="AFFILIATION_PREFIX",
                    confidence=0.95,
                    requires_review=False,
                    match_detail=f"会社「{company}」を分離",
                )

            # 会社人物 形式（区切りなし）
            if name.startswith(company) and len(name) > len(company):
                person = name[len(company) :]
                # 次の文字がカタカナか漢字ならマッチ
                if person and (self._is_all_katakana(person[0]) or "\u4e00" <= person[0] <= "\u9fff"):
                    return NormalizationResult(
                        original_name=name,
                        normalized_name=person,
                        title=None,
                        affiliation=company,
                        pattern_type="AFFILIATION_PREFIX",
                        confidence=0.90,
                        requires_review=False,
                        match_detail=f"会社「{company}」を分離（区切りなし）",
                    )

        return None

    def _match_sport_prefix(self, name: str) -> Optional[NormalizationResult]:
        """スポーツ人物 形式の検出"""
        for sport in SPORT_KEYWORDS:
            # スポーツ・人物 形式
            pattern = f"^{re.escape(sport)}・(.+)$"
            match = re.match(pattern, name)
            if match:
                person = match.group(1)
                return NormalizationResult(
                    original_name=name,
                    normalized_name=person,
                    title=sport,
                    affiliation=None,
                    pattern_type="SPORT_PREFIX",
                    confidence=0.90,
                    requires_review=False,
                    match_detail=f"スポーツ「{sport}」を分離",
                )

            # スポーツ人物 形式（区切りなし）
            if name.startswith(sport) and len(name) > len(sport):
                person = name[len(sport) :]
                if person and ("\u4e00" <= person[0] <= "\u9fff"):  # 漢字で始まる
                    return NormalizationResult(
                        original_name=name,
                        normalized_name=person,
                        title=sport,
                        affiliation=None,
                        pattern_type="SPORT_PREFIX",
                        confidence=0.90,
                        requires_review=False,
                        match_detail=f"スポーツ「{sport}」を分離（区切りなし）",
                    )

        return None

    def _match_profession_prefix(self, name: str) -> Optional[NormalizationResult]:
        """職業・人物 形式の検出"""
        for profession in PROFESSION_KEYWORDS:
            # 職業・人物 形式
            pattern = f"^{re.escape(profession)}[・\s]?(.+)$"
            match = re.match(pattern, name)
            if match:
                person = match.group(1)
                if person and person != name:
                    return NormalizationResult(
                        original_name=name,
                        normalized_name=person,
                        title=profession,
                        affiliation=None,
                        pattern_type="PROFESSION_PREFIX",
                        confidence=0.90,
                        requires_review=False,
                        match_detail=f"職業「{profession}」を分離",
                    )

        return None

    def _match_title_role(self, name: str) -> Optional[NormalizationResult]:
        """肩書人物 形式の検出"""
        for title_kw in TITLE_KEYWORDS:
            # 会社創業者人物 形式
            pattern = f"^(.+?){re.escape(title_kw)}(.+)$"
            match = re.match(pattern, name)
            if match:
                company = match.group(1)
                person = match.group(2)

                # 人物名が短すぎる場合はスキップ
                if len(person) < 2:
                    continue

                return NormalizationResult(
                    original_name=name,
                    normalized_name=person,
                    title=title_kw,
                    affiliation=company if company else None,
                    pattern_type="TITLE_ROLE",
                    confidence=0.85,
                    requires_review=False,
                    match_detail=f"肩書「{title_kw}」を分離、所属「{company}」",
                )

        return None

    def _match_relationship(self, name: str) -> Optional[NormalizationResult]:
        """関係性人物 形式の検出"""
        for rel in RELATIONSHIP_KEYWORDS:
            pattern = f"^(.+){re.escape(rel)}(.+)$"
            match = re.match(pattern, name)
            if match:
                related_person = match.group(1)
                person = match.group(2)

                # 人物名が短すぎる場合はスキップ
                if len(person) < 2:
                    continue

                return NormalizationResult(
                    original_name=name,
                    normalized_name=person,
                    title=f"{related_person}{rel}",
                    affiliation=None,
                    pattern_type="RELATIONSHIP",
                    confidence=0.85,  # LLM検証で信頼度を確保
                    requires_review=False,
                    match_detail=f"関係性「{related_person}{rel}」を分離",
                )

        return None

    def _match_team_member(self, name: str) -> Optional[NormalizationResult]:
        """チーム・人物 形式の検出"""
        for team in TEAM_KEYWORDS:
            pattern = f"^{re.escape(team)}[・\s]?(.+)$"
            match = re.match(pattern, name)
            if match:
                person = match.group(1)
                return NormalizationResult(
                    original_name=name,
                    normalized_name=person,
                    title=None,
                    affiliation=team,
                    pattern_type="TEAM_MEMBER",
                    confidence=0.75,
                    requires_review=True,
                    match_detail=f"チーム「{team}」を分離",
                )

        return None

    def _match_league_prefix(self, name: str) -> Optional[NormalizationResult]:
        """リーグ・人物 形式の検出"""
        for league in LEAGUE_KEYWORDS:
            pattern = f"^{re.escape(league)}[・\s]?(.+)$"
            match = re.match(pattern, name)
            if match:
                person = match.group(1)
                return NormalizationResult(
                    original_name=name,
                    normalized_name=person,
                    title=None,
                    affiliation=league,
                    pattern_type="LEAGUE_PREFIX",
                    confidence=0.90,
                    requires_review=False,
                    match_detail=f"リーグ「{league}」を分離",
                )

        return None

    def verify_with_llm(self, result: NormalizationResult) -> NormalizationResult:
        """LLMで正規化結果を検証"""
        if not self.anthropic_client:
            return result

        prompt = f"""以下の人物名の正規化結果を検証してください。

元の名前: {result.original_name}
正規化後の名前: {result.normalized_name}
抽出された肩書: {result.title}
抽出された所属: {result.affiliation}
パターン: {result.pattern_type}

以下の形式でJSON形式で回答してください:
{{
    "is_correct": true/false,
    "corrected_name": "修正後の名前（修正不要ならnull）",
    "reason": "判断理由"
}}
"""

        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )

            # レスポンスからJSON抽出
            text = response.content[0].text
            # JSON部分を抽出
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                if not data.get("is_correct") and data.get("corrected_name"):
                    result.normalized_name = data["corrected_name"]
                    result.match_detail += f" [LLM修正: {data.get('reason', '')}]"
                elif data.get("is_correct"):
                    result.confidence = min(result.confidence + 0.05, 1.0)
                    result.requires_review = False
        except Exception as e:
            print(f"  ⚠️ LLM検証エラー: {e}")

        return result

    def batch_normalize(self, df: pd.DataFrame) -> dict:
        """バッチ処理"""
        results = {
            "auto_fixed": [],
            "requires_review": [],
            "skipped": [],
            "by_pattern": {},
        }

        unique_names = df["person_name"].dropna().unique()
        print(f"  ユニーク人物名: {len(unique_names)}件")

        for name in unique_names:
            result = self.normalize(name)

            if result is None:
                results["skipped"].append(name)
            elif result.confidence >= self.min_confidence and not result.requires_review:
                # LLM検証
                if self.use_llm and self.anthropic_client:
                    result = self.verify_with_llm(result)

                results["auto_fixed"].append(result)

                # パターン別集計
                if result.pattern_type not in results["by_pattern"]:
                    results["by_pattern"][result.pattern_type] = []
                results["by_pattern"][result.pattern_type].append(result)
            else:
                results["requires_review"].append(result)

        return results


def save_report(results: dict, output_path: Path):
    """レポートを保存"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "auto_fixed_count": len(results["auto_fixed"]),
            "requires_review_count": len(results["requires_review"]),
            "skipped_count": len(results["skipped"]),
        },
        "by_pattern": {k: len(v) for k, v in results["by_pattern"].items()},
        "auto_fixed": [asdict(r) for r in results["auto_fixed"]],
        "requires_review": [asdict(r) for r in results["requires_review"]],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def apply_normalizations(df: pd.DataFrame, results: List[NormalizationResult]) -> pd.DataFrame:
    """正規化結果をDataFrameに適用"""
    for result in results:
        mask = df["person_name"] == result.original_name

        if mask.sum() > 0:
            # 元の名前を保存
            df.loc[mask, "name_raw"] = result.original_name
            # 正規化された名前
            df.loc[mask, "person_name"] = result.normalized_name
            # 肩書
            if result.title:
                df.loc[mask, "title"] = result.title
            # 所属
            if result.affiliation:
                df.loc[mask, "affiliation"] = result.affiliation

    return df


def main():
    parser = argparse.ArgumentParser(description="人物名正規化")
    parser.add_argument("--dry-run", action="store_true", help="検出のみ（変更なし）")
    parser.add_argument("--execute", action="store_true", help="変更を実行")
    parser.add_argument("--use-llm", action="store_true", help="LLM検証を使用")
    parser.add_argument("--min-confidence", type=float, default=0.85, help="最小信頼度")
    parser.add_argument("--pattern", type=str, help="特定パターンのみ処理")
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("⚠️ --dry-run または --execute を指定してください")
        return

    dry_run = not args.execute

    print("=" * 70)
    print(f"🔧 人物名正規化 {'(dry-run)' if dry_run else '(実行)'}")
    print("=" * 70)
    print(f"  実行日時: {datetime.now().isoformat()}")
    print(f"  最小信頼度: {args.min_confidence}")
    print(f"  LLM検証: {'有効' if args.use_llm else '無効'}")

    # CSV読み込み
    print(f"\n📂 CSV読み込み: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"  レコード数: {len(df)}件")

    # 正規化エンジン初期化
    normalizer = PersonNameNormalizer(
        min_confidence=args.min_confidence,
        use_llm=args.use_llm,
    )

    # バッチ処理
    print("\n🔍 パターン検出中...")
    results = normalizer.batch_normalize(df)

    # 結果表示
    print("\n" + "=" * 70)
    print("📊 検出結果")
    print("=" * 70)
    print(f"  自動修正対象: {len(results['auto_fixed'])}件")
    print(f"  要レビュー: {len(results['requires_review'])}件")
    print(f"  スキップ: {len(results['skipped'])}件")

    print("\n📋 パターン別内訳:")
    for pattern, items in results["by_pattern"].items():
        print(f"  {pattern}: {len(items)}件")

    # 自動修正例を表示
    if results["auto_fixed"]:
        print("\n✅ 自動修正例（先頭10件）:")
        for r in results["auto_fixed"][:10]:
            print(f"  「{r.original_name}」→「{r.normalized_name}」")
            print(f"    肩書: {r.title}, 所属: {r.affiliation}, 信頼度: {r.confidence:.2f}")

    # 要レビュー例を表示
    if results["requires_review"]:
        print("\n⚠️ 要レビュー例（先頭10件）:")
        for r in results["requires_review"][:10]:
            print(f"  「{r.original_name}」→「{r.normalized_name}」")
            print(f"    パターン: {r.pattern_type}, 信頼度: {r.confidence:.2f}")

    # レポート保存
    REPORTS_DIR.mkdir(exist_ok=True)
    report_path = (
        REPORTS_DIR
        / f"name_normalization_{'dryrun' if dry_run else 'executed'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    save_report(results, report_path)
    print(f"\n📄 レポート保存: {report_path}")

    # 実行
    if not dry_run:
        print("\n💾 変更を適用中...")
        df = apply_normalizations(df, results["auto_fixed"])
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"  保存完了: {len(df)}件")

    print("\n✅ 完了")


if __name__ == "__main__":
    main()
