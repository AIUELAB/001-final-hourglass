#!/usr/bin/env python3
"""
名前クレンジング検出スクリプト

7パターンの名前問題を検出し、信頼度スコアに基づいて分類する。

パターン:
A: グループ・個人名 (嵐・大野智) - HIGH
B: グループ 個人名 (コムドット やまと) - HIGH
C: カテゴリ・人名 (俳優・三船敏郎) - HIGH
D: 組織役職人名 (アマゾン元社長ジャスパー・チャン) - MEDIUM
E: キャラ『作品』 (孫悟空『ドラゴンボール』) - HIGH
F: 人名（説明） (きんさんぎんさん（成田きん）) - MEDIUM
G: グループ連結 (B'z稲葉浩志) - MEDIUM

信頼度閾値:
- >= 0.85: 自動修正
- 0.6 - 0.85: 確認待ちキュー
- < 0.6: 手動レビュー必須

使用方法:
    python scripts/name_cleansing_detector.py [--execute] [--report-only]
"""

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple

import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.group_master import GROUP_ENTITIES, GROUP_MEMBER_MAP

# ========================================
# 定数
# ========================================

CSV_PATH = "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = "reports"

# カテゴリプレフィックス（60種類）
CATEGORY_PREFIXES = {
    # 芸能・エンタメ
    "俳優",
    "女優",
    "歌手",
    "アイドル",
    "タレント",
    "芸人",
    "お笑い芸人",
    "声優",
    "ナレーター",
    "司会者",
    "DJ",
    "ラッパー",
    "ダンサー",
    "モデル",
    "グラビアアイドル",
    "AV女優",
    "YouTuber",
    "VTuber",
    "配信者",
    "インフルエンサー",
    # 音楽
    "ミュージシャン",
    "作曲家",
    "作詞家",
    "編曲家",
    "指揮者",
    "ピアニスト",
    "ギタリスト",
    "ドラマー",
    "ベーシスト",
    "バイオリニスト",
    # スポーツ
    "野球選手",
    "サッカー選手",
    "バスケ選手",
    "テニス選手",
    "ゴルファー",
    "プロレスラー",
    "格闘家",
    "力士",
    "騎手",
    "レーサー",
    "水泳選手",
    "陸上選手",
    "スケーター",
    "スキーヤー",
    # 文化・芸術
    "作家",
    "小説家",
    "漫画家",
    "イラストレーター",
    "画家",
    "写真家",
    "映画監督",
    "脚本家",
    "演出家",
    "アニメーター",
    "デザイナー",
    "建築家",
    "彫刻家",
    # 学術・専門
    "学者",
    "研究者",
    "教授",
    "博士",
    "科学者",
    "物理学者",
    "経済学者",
    "哲学者",
    "医師",
    "弁護士",
    # ビジネス・政治
    "実業家",
    "経営者",
    "社長",
    "会長",
    "CEO",
    "創業者",
    "政治家",
    "首相",
    "大統領",
    "議員",
}

# 除外リスト（外国人名で中点が含まれるが連結名ではないもの）
EXCLUDE_FROM_CONCATENATION = {
    # 俳優・女優
    "オードリー・ヘプバーン",
    "マリリン・モンロー",
    "ジャッキー・チェン",
    "ブルース・リー",
    "ジェット・リー",
    "トム・クルーズ",
    "トム・ハンクス",
    "ブラッド・ピット",
    "レオナルド・ディカプリオ",
    "ジョニー・デップ",
    "ロバート・デ・ニーロ",
    "アル・パチーノ",
    "クリント・イーストウッド",
    "メリル・ストリープ",
    "ジュリア・ロバーツ",
    "アンジェリーナ・ジョリー",
    "スカーレット・ヨハンソン",
    "ナタリー・ポートマン",
    "エマ・ワトソン",
    "キアヌ・リーブス",
    "ニコラス・ケイジ",
    "ウィル・スミス",
    "デンゼル・ワシントン",
    "サミュエル・L・ジャクソン",
    "モーガン・フリーマン",
    # 音楽
    "マイケル・ジャクソン",
    "エルヴィス・プレスリー",
    "スティービー・ワンダー",
    "ボブ・ディラン",
    "エリック・クラプトン",
    "ポール・サイモン",
    "エルトン・ジョン",
    "デヴィッド・ボウイ",
    "フレディ・マーキュリー",
    "ジミ・ヘンドリックス",
    "カート・コバーン",
    "エド・シーラン",
    "テイラー・スウィフト",
    "アリアナ・グランデ",
    "レディー・ガガ",
    "セリーヌ・ディオン",
    "マドンナ・ルイーズ・チッコーネ",
    # スポーツ
    "マイケル・ジョーダン",
    "レブロン・ジェームズ",
    "コービー・ブライアント",
    "タイガー・ウッズ",
    "ロジャー・フェデラー",
    "ラファエル・ナダル",
    "クリスティアーノ・ロナウド",
    "リオネル・メッシ",
    "ネイマール・ジュニオール",
    "デビッド・ベッカム",
    "ウサイン・ボルト",
    "マイク・タイソン",
    "モハメド・アリ",
    "フロイド・メイウェザー",
    # 実業家・政治家
    "スティーブ・ジョブズ",
    "ビル・ゲイツ",
    "イーロン・マスク",
    "マーク・ザッカーバーグ",
    "ジェフ・ベゾス",
    "ウォーレン・バフェット",
    "ドナルド・トランプ",
    "バラク・オバマ",
    "ジョー・バイデン",
    "ウラジーミル・プーチン",
    "ウィンストン・チャーチル",
    "マーガレット・サッチャー",
    # 学者・科学者
    "アルベルト・アインシュタイン",
    "スティーブン・ホーキング",
    "アイザック・ニュートン",
    "チャールズ・ダーウィン",
    "マリー・キュリー",
    # 作家・芸術家
    "ウィリアム・シェイクスピア",
    "パブロ・ピカソ",
    "レオナルド・ダ・ヴィンチ",
    "ヴィンセント・ファン・ゴッホ",
    "クロード・モネ",
    "アンディ・ウォーホル",
    # 映画監督
    "スティーブン・スピルバーグ",
    "クリストファー・ノーラン",
    "マーティン・スコセッシ",
    "クエンティン・タランティーノ",
    "ジェームズ・キャメロン",
    "リドリー・スコット",
    # アニメ・ゲーム
    "ウォルト・ディズニー",
    # その他著名人
    "マザー・テレサ",
    "マハトマ・ガンジー",
    "ネルソン・マンデラ",
    "マーティン・ルーサー・キング",
    "アンネ・フランク",
    # 日本語表記のアーティスト
    "フレディー・マーキュリー",  # 表記ゆれ
}

# 役職・肩書
ROLE_TITLES = {
    "社長",
    "会長",
    "CEO",
    "代表",
    "創業者",
    "元社長",
    "元会長",
    "監督",
    "コーチ",
    "選手",
    "元選手",
    "オーナー",
    "教授",
    "博士",
    "先生",
    "師匠",
    "首相",
    "大統領",
    "総理",
    "議員",
    "知事",
    "市長",
}


class ConfidenceLevel(Enum):
    """信頼度レベル"""

    HIGH = "high"  # >= 0.85: 自動修正
    MEDIUM = "medium"  # 0.6 - 0.85: 確認待ち
    LOW = "low"  # < 0.6: 手動レビュー


@dataclass
class DetectionResult:
    """検出結果"""

    episode_id: str
    person_id: str
    person_name: str
    pattern_type: str  # A, B, C, D, E, F, G
    pattern_name: str
    detected_parts: Dict[str, str]  # group, individual, category, etc.
    confidence: float
    confidence_level: ConfidenceLevel
    suggested_fix: str
    row_index: int


class NameCleansingDetector:
    """7パターン名前クレンジング検出器"""

    def __init__(self, csv_path: str = CSV_PATH):
        self.csv_path = csv_path
        self.df = pd.read_csv(csv_path)
        self.results: List[DetectionResult] = []

    def detect_all(self) -> List[DetectionResult]:
        """全パターンを検出"""
        self.results = []

        for idx, row in self.df.iterrows():
            person_name = str(row.get("person_name", "")).strip()
            if not person_name:
                continue

            # 除外リストチェック
            if person_name in EXCLUDE_FROM_CONCATENATION:
                continue

            # 各パターンを順番に検出
            result = None
            result = result or self._detect_pattern_a(row, idx, person_name)
            result = result or self._detect_pattern_b(row, idx, person_name)
            result = result or self._detect_pattern_c(row, idx, person_name)
            result = result or self._detect_pattern_d(row, idx, person_name)
            result = result or self._detect_pattern_e(row, idx, person_name)
            result = result or self._detect_pattern_f(row, idx, person_name)
            result = result or self._detect_pattern_g(row, idx, person_name)

            if result:
                self.results.append(result)

        return self.results

    def _detect_pattern_a(self, row: pd.Series, idx: int, name: str) -> Optional[DetectionResult]:
        """パターンA: グループ・個人名 (中点区切り)"""
        delimiters = ["・", "･", "/"]

        for delim in delimiters:
            if delim in name:
                parts = name.split(delim, 1)
                if len(parts) == 2:
                    left, right = parts[0].strip(), parts[1].strip()

                    # 左側がGROUP_ENTITIESに含まれる
                    if left in GROUP_ENTITIES:
                        return self._create_result(
                            row, idx, name, "A", "グループ・個人名", {"group": left, "individual": right}, 0.95, right
                        )

                    # 右側がGROUP_MEMBER_MAPに含まれ、左がそのグループ
                    if right in GROUP_MEMBER_MAP:
                        expected_group = GROUP_MEMBER_MAP[right]
                        if left == expected_group or expected_group in left:
                            return self._create_result(
                                row,
                                idx,
                                name,
                                "A",
                                "グループ・個人名",
                                {"group": left, "individual": right},
                                0.90,
                                right,
                            )

        return None

    def _detect_pattern_b(self, row: pd.Series, idx: int, name: str) -> Optional[DetectionResult]:
        """パターンB: グループ 個人名 (スペース区切り)"""
        # 全角・半角スペースで分割
        for delim in [" ", "　"]:
            if delim in name:
                parts = name.split(delim, 1)
                if len(parts) == 2:
                    left, right = parts[0].strip(), parts[1].strip()

                    # 左側がGROUP_ENTITIESに含まれる
                    if left in GROUP_ENTITIES:
                        return self._create_result(
                            row, idx, name, "B", "グループ 個人名", {"group": left, "individual": right}, 0.90, right
                        )

                    # 右側がGROUP_MEMBER_MAPに含まれ、左がそのグループ
                    if right in GROUP_MEMBER_MAP:
                        expected_group = GROUP_MEMBER_MAP[right]
                        if left == expected_group or expected_group in left:
                            return self._create_result(
                                row,
                                idx,
                                name,
                                "B",
                                "グループ 個人名",
                                {"group": left, "individual": right},
                                0.85,
                                right,
                            )

        return None

    def _detect_pattern_c(self, row: pd.Series, idx: int, name: str) -> Optional[DetectionResult]:
        """パターンC: カテゴリ・人名"""
        delimiters = ["・", "･", "：", ":"]

        for delim in delimiters:
            if delim in name:
                parts = name.split(delim, 1)
                if len(parts) == 2:
                    left, right = parts[0].strip(), parts[1].strip()

                    if left in CATEGORY_PREFIXES:
                        return self._create_result(
                            row, idx, name, "C", "カテゴリ・人名", {"category": left, "individual": right}, 0.95, right
                        )

        return None

    def _detect_pattern_d(self, row: pd.Series, idx: int, name: str) -> Optional[DetectionResult]:
        """パターンD: 組織役職人名"""
        # 役職パターンを検索
        for role in ROLE_TITLES:
            if role in name:
                # 役職の位置を特定
                role_idx = name.find(role)
                if role_idx > 0:
                    # 組織名 + 役職 + 人名
                    org = name[:role_idx].strip()
                    after_role = name[role_idx + len(role) :].strip()

                    # 日本語助詞「の」「・」を除去
                    after_role = after_role.lstrip("の・")

                    if org and after_role and self._looks_like_name(after_role):
                        return self._create_result(
                            row,
                            idx,
                            name,
                            "D",
                            "組織役職人名",
                            {"organization": org, "role": role, "individual": after_role},
                            0.70,
                            after_role,
                        )

        return None

    def _detect_pattern_e(self, row: pd.Series, idx: int, name: str) -> Optional[DetectionResult]:
        """パターンE: キャラ『作品』"""
        # 『』で囲まれた作品名を検出
        match = re.search(r"^(.+?)『(.+?)』$", name)
        if match:
            character = match.group(1).strip()
            work = match.group(2).strip()
            if character and work:
                return self._create_result(
                    row, idx, name, "E", "キャラ『作品』", {"character": character, "work_title": work}, 0.90, character
                )

        # 「」バージョン
        match = re.search(r"^(.+?)「(.+?)」$", name)
        if match:
            character = match.group(1).strip()
            work = match.group(2).strip()
            if character and work:
                return self._create_result(
                    row, idx, name, "E", "キャラ「作品」", {"character": character, "work_title": work}, 0.90, character
                )

        return None

    def _detect_pattern_f(self, row: pd.Series, idx: int, name: str) -> Optional[DetectionResult]:
        """パターンF: 人名（説明）"""
        # （）で囲まれた説明を検出
        match = re.search(r"^(.+?)（(.+?)）$", name)
        if match:
            main_name = match.group(1).strip()
            description = match.group(2).strip()
            if main_name and description:
                # 説明が人名っぽいかチェック（本名など）
                confidence = 0.75 if self._looks_like_name(description) else 0.60
                return self._create_result(
                    row,
                    idx,
                    name,
                    "F",
                    "人名（説明）",
                    {"main_name": main_name, "description": description},
                    confidence,
                    main_name,
                )

        # ()バージョン
        match = re.search(r"^(.+?)\((.+?)\)$", name)
        if match:
            main_name = match.group(1).strip()
            description = match.group(2).strip()
            if main_name and description:
                confidence = 0.70 if self._looks_like_name(description) else 0.55
                return self._create_result(
                    row,
                    idx,
                    name,
                    "F",
                    "人名(説明)",
                    {"main_name": main_name, "description": description},
                    confidence,
                    main_name,
                )

        return None

    def _detect_pattern_g(self, row: pd.Series, idx: int, name: str) -> Optional[DetectionResult]:
        """パターンG: グループ連結 (区切り文字なし)"""
        # GROUP_ENTITIESの名前が先頭に含まれていて、その後に名前が続く
        for group in sorted(GROUP_ENTITIES, key=len, reverse=True):
            if name.startswith(group) and len(name) > len(group):
                individual = name[len(group) :]
                # 個人名っぽいかチェック
                if self._looks_like_name(individual):
                    # GROUP_MEMBER_MAPにあればより高い信頼度
                    if individual in GROUP_MEMBER_MAP:
                        expected = GROUP_MEMBER_MAP[individual]
                        if expected == group:
                            return self._create_result(
                                row,
                                idx,
                                name,
                                "G",
                                "グループ連結",
                                {"group": group, "individual": individual},
                                0.85,
                                individual,
                            )
                    # なくても検出（低い信頼度）
                    return self._create_result(
                        row,
                        idx,
                        name,
                        "G",
                        "グループ連結",
                        {"group": group, "individual": individual},
                        0.65,
                        individual,
                    )

        return None

    def _looks_like_name(self, text: str) -> bool:
        """人名っぽいかどうかを判定"""
        # 簡易チェック: 2-10文字、ひらがな/カタカナ/漢字を含む
        if not text or len(text) < 2 or len(text) > 15:
            return False
        # 数字のみは除外
        if text.isdigit():
            return False
        # 日本語文字を含む
        has_japanese = bool(re.search(r"[ぁ-んァ-ン一-龥]", text))
        return has_japanese

    def _create_result(
        self,
        row: pd.Series,
        idx: int,
        name: str,
        pattern_type: str,
        pattern_name: str,
        detected_parts: Dict[str, str],
        confidence: float,
        suggested_fix: str,
    ) -> DetectionResult:
        """検出結果を生成"""
        if confidence >= 0.85:
            level = ConfidenceLevel.HIGH
        elif confidence >= 0.60:
            level = ConfidenceLevel.MEDIUM
        else:
            level = ConfidenceLevel.LOW

        return DetectionResult(
            episode_id=str(row.get("episode_id", "")),
            person_id=str(row.get("person_id", "")),
            person_name=name,
            pattern_type=pattern_type,
            pattern_name=pattern_name,
            detected_parts=detected_parts,
            confidence=confidence,
            confidence_level=level,
            suggested_fix=suggested_fix,
            row_index=idx,
        )

    def apply_fixes(self, auto_only: bool = True) -> Tuple[int, int, int]:
        """修正を適用"""
        fixed_auto = 0
        fixed_review = 0
        skipped = 0

        for result in self.results:
            should_fix = False
            if result.confidence_level == ConfidenceLevel.HIGH:
                should_fix = True
                fixed_auto += 1
            elif result.confidence_level == ConfidenceLevel.MEDIUM and not auto_only:
                should_fix = True
                fixed_review += 1
            else:
                skipped += 1

            if should_fix:
                # 名前を修正
                self.df.at[result.row_index, "person_name"] = result.suggested_fix

                # グループ情報を更新
                if "group" in result.detected_parts:
                    self.df.at[result.row_index, "group_name"] = result.detected_parts["group"]
                    self.df.at[result.row_index, "is_group_member"] = True

                # 作品名を更新（パターンE）
                if "work_title" in result.detected_parts:
                    self.df.at[result.row_index, "work_title"] = result.detected_parts["work_title"]

        return fixed_auto, fixed_review, skipped

    def save_csv(self) -> None:
        """CSVを保存"""
        self.df.to_csv(self.csv_path, index=False, encoding="utf-8-sig")

    def generate_report(self) -> Dict:
        """レポートを生成"""
        by_pattern = {}
        by_level = {"high": [], "medium": [], "low": []}

        for r in self.results:
            # パターン別
            if r.pattern_type not in by_pattern:
                by_pattern[r.pattern_type] = []
            by_pattern[r.pattern_type].append(asdict(r))

            # 信頼度別
            by_level[r.confidence_level.value].append(asdict(r))

        return {
            "timestamp": datetime.now().isoformat(),
            "total_detected": len(self.results),
            "summary": {
                "by_pattern": {p: len(items) for p, items in by_pattern.items()},
                "by_confidence": {
                    "high_auto": len(by_level["high"]),
                    "medium_review": len(by_level["medium"]),
                    "low_manual": len(by_level["low"]),
                },
            },
            "by_pattern": by_pattern,
            "by_confidence": by_level,
        }


def main():
    parser = argparse.ArgumentParser(description="7パターン名前クレンジング検出")
    parser.add_argument("--execute", action="store_true", help="自動修正を実行")
    parser.add_argument("--execute-all", action="store_true", help="確認待ちも含めて修正")
    parser.add_argument("--report-only", action="store_true", help="レポートのみ生成")
    parser.add_argument("--csv", default=CSV_PATH, help="対象CSVファイル")
    args = parser.parse_args()

    print("=" * 70)
    print("7パターン名前クレンジング検出")
    print("=" * 70)

    detector = NameCleansingDetector(args.csv)

    print(f"\n📂 CSV読み込み: {args.csv}")
    print(f"   総レコード数: {len(detector.df):,}")

    print("\n🔍 7パターン検出中...")
    results = detector.detect_all()

    # パターン別集計
    pattern_counts = {}
    level_counts = {"high": 0, "medium": 0, "low": 0}
    for r in results:
        pattern_counts[r.pattern_type] = pattern_counts.get(r.pattern_type, 0) + 1
        level_counts[r.confidence_level.value] += 1

    print(f"\n📊 検出結果: 合計 {len(results)}件")
    print("\n   【パターン別】")
    pattern_names = {
        "A": "グループ・個人名",
        "B": "グループ 個人名",
        "C": "カテゴリ・人名",
        "D": "組織役職人名",
        "E": "キャラ『作品』",
        "F": "人名（説明）",
        "G": "グループ連結",
    }
    for p in ["A", "B", "C", "D", "E", "F", "G"]:
        count = pattern_counts.get(p, 0)
        if count > 0:
            print(f"      {p}: {pattern_names[p]}: {count}件")

    print("\n   【信頼度別】")
    print(f"      ✅ HIGH (自動修正): {level_counts['high']}件")
    print(f"      ⚠️  MEDIUM (確認待ち): {level_counts['medium']}件")
    print(f"      ❌ LOW (手動レビュー): {level_counts['low']}件")

    # サンプル表示
    if results:
        print("\n   【検出サンプル (最大10件)】")
        for r in results[:10]:
            print(f"      {r.episode_id}: [{r.pattern_type}] {r.person_name}")
            print(f"         → {r.suggested_fix} (信頼度: {r.confidence:.2f})")
        if len(results) > 10:
            print(f"      ... 他 {len(results) - 10}件")

    # レポート生成
    report = detector.generate_report()
    os.makedirs(REPORT_DIR, exist_ok=True)
    report_path = os.path.join(REPORT_DIR, f"name_cleansing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n📄 レポート: {report_path}")

    if args.report_only:
        print("\n⚠️  --report-only モード: 修正は実行しません")
        return

    if not args.execute and not args.execute_all:
        print("\n💡 修正を実行するには --execute (自動のみ) または --execute-all オプションを追加")
        return

    # 修正実行
    print("\n🔧 修正実行中...")

    # バックアップ
    backup_path = args.csv.replace(".csv", f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    detector.df.to_csv(backup_path, index=False, encoding="utf-8-sig")
    print(f"   💾 バックアップ: {backup_path}")

    auto_only = not args.execute_all
    fixed_auto, fixed_review, skipped = detector.apply_fixes(auto_only=auto_only)

    detector.save_csv()
    print("   ✅ CSV更新完了")

    print("\n📊 修正結果:")
    print(f"   ├─ 自動修正: {fixed_auto}件")
    print(f"   ├─ 確認後修正: {fixed_review}件")
    print(f"   └─ スキップ: {skipped}件")

    print("\n✅ 完了")


if __name__ == "__main__":
    main()
