#!/usr/bin/env python3
"""
重複人物の検出・統合スクリプト

機能:
1. 正規化による完全一致検出
2. 類似度による近似一致検出
3. 属性ベースの検証
4. 重複人物の統合

Usage:
    python scripts/merge_duplicate_persons.py [--dry-run] [--execute] [--threshold 0.85]
"""

import argparse
import json
import os
import re
import shutil
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))


# ========================================
# 定数
# ========================================

PROJECT_ROOT = Path(__file__).parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "data" / "backups"
OUTPUT_DIR = PROJECT_ROOT / "output" / "duplicate_detection"


# ========================================
# 名前正規化
# ========================================


def normalize_name(name: str) -> str:
    """
    人物名を正規化

    処理:
    - NFKC正規化（全角→半角、etc）
    - 小文字化
    - 中点・スペース統一
    - 前後空白削除

    Args:
        name: 元の名前

    Returns:
        正規化された名前
    """
    if not name or pd.isna(name):
        return ""

    name = str(name)

    # NFKC正規化
    name = unicodedata.normalize("NFKC", name)

    # 小文字化
    name = name.lower()

    # 中点類の統一（・、·、・、‧ → ・）
    name = re.sub(r"[・·‧]", "・", name)

    # スペース統一
    name = re.sub(r"\s+", " ", name)

    # 前後空白削除
    name = name.strip()

    return name


def remove_honorifics(name: str) -> str:
    """
    敬称・接尾辞を除去

    Args:
        name: 名前

    Returns:
        敬称除去後の名前
    """
    # 日本語敬称
    honorifics = ["さん", "くん", "君", "ちゃん", "様", "氏", "先生", "博士"]
    for h in honorifics:
        if name.endswith(h):
            name = name[: -len(h)]

    return name.strip()


# ========================================
# 類似度計算
# ========================================


def calculate_similarity(name1: str, name2: str) -> float:
    """
    2つの名前の類似度を計算

    Args:
        name1: 名前1
        name2: 名前2

    Returns:
        類似度（0.0-1.0）
    """
    return SequenceMatcher(None, name1, name2).ratio()


def are_similar_names(name1: str, name2: str, threshold: float = 0.85) -> bool:
    """
    2つの名前が類似しているか判定

    Args:
        name1: 名前1
        name2: 名前2
        threshold: 類似度閾値

    Returns:
        類似していればTrue
    """
    # 正規化
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)

    # 完全一致
    if n1 == n2:
        return True

    # 類似度計算
    return calculate_similarity(n1, n2) >= threshold


# ========================================
# 重複検出
# ========================================


class DuplicateDetector:
    """重複人物検出クラス"""

    def __init__(self, csv_path: str, similarity_threshold: float = 0.85):
        """
        Args:
            csv_path: MASTER CSVパス
            similarity_threshold: 類似度閾値
        """
        self.csv_path = csv_path
        self.threshold = similarity_threshold
        self.df = pd.read_csv(csv_path, encoding="utf-8-sig")

        # 人物データ抽出
        self.persons = self._extract_persons()

        # 重複候補
        self.exact_duplicates: List[Dict] = []  # 完全一致
        self.similar_duplicates: List[Dict] = []  # 類似一致
        self.all_duplicates: List[Dict] = []  # 全重複

    def _extract_persons(self) -> Dict[str, Dict]:
        """
        ユニークな人物を抽出

        Returns:
            {person_id: {person_name, category, birth_year, episode_count}} の辞書
        """
        persons = {}

        # エピソード数をカウント
        episode_counts = self.df.groupby("person_id").size().to_dict()

        # ユニーク人物を抽出
        unique_df = self.df.drop_duplicates("person_id")

        for _, row in unique_df.iterrows():
            person_id = row["person_id"]
            persons[person_id] = {
                "person_id": person_id,
                "person_name": row["person_name"],
                "category": row.get("category", ""),
                "birth_year": row.get("birth_year", None),
                "person_type": row.get("person_type", "REAL"),
                "episode_count": episode_counts.get(person_id, 0),
            }

        return persons

    def detect_exact_duplicates(self) -> List[Dict]:
        """
        正規化による完全一致重複を検出

        Returns:
            重複グループのリスト
        """
        # 正規化名でグループ化
        normalized_groups = defaultdict(list)

        for person_id, data in self.persons.items():
            norm_name = normalize_name(data["person_name"])
            if norm_name:
                normalized_groups[norm_name].append(data)

        # 2人以上のグループを抽出
        duplicates = []
        for norm_name, persons in normalized_groups.items():
            if len(persons) >= 2:
                # エピソード数が最多の人物を正規IDに
                persons_sorted = sorted(persons, key=lambda x: x["episode_count"], reverse=True)
                canonical = persons_sorted[0]
                others = persons_sorted[1:]

                duplicates.append(
                    {
                        "type": "exact",
                        "normalized_name": norm_name,
                        "canonical": canonical,
                        "duplicates": others,
                        "confidence": 1.0,
                    }
                )

        self.exact_duplicates = duplicates
        return duplicates

    def detect_similar_duplicates(self) -> List[Dict]:
        """
        類似度による近似一致重複を検出

        Returns:
            重複候補のリスト
        """
        persons_list = list(self.persons.values())
        n = len(persons_list)
        similar = []

        # 完全一致で検出済みのIDを除外
        exact_ids = set()
        for dup in self.exact_duplicates:
            exact_ids.add(dup["canonical"]["person_id"])
            for d in dup["duplicates"]:
                exact_ids.add(d["person_id"])

        # 全ペア比較（O(n^2)だが人物数は数千程度なので許容）
        for i in range(n):
            p1 = persons_list[i]
            if p1["person_id"] in exact_ids:
                continue

            n1 = normalize_name(p1["person_name"])
            if not n1:
                continue

            for j in range(i + 1, n):
                p2 = persons_list[j]
                if p2["person_id"] in exact_ids:
                    continue

                n2 = normalize_name(p2["person_name"])
                if not n2:
                    continue

                # 類似度計算
                sim = calculate_similarity(n1, n2)

                if sim >= self.threshold and sim < 1.0:  # 完全一致は除外
                    # 属性で追加検証
                    attr_score = self._attribute_similarity(p1, p2)
                    combined_score = (sim * 0.7) + (attr_score * 0.3)

                    if combined_score >= self.threshold:
                        # エピソード数が多い方を正規IDに
                        if p1["episode_count"] >= p2["episode_count"]:
                            canonical, duplicate = p1, p2
                        else:
                            canonical, duplicate = p2, p1

                        similar.append(
                            {
                                "type": "similar",
                                "canonical": canonical,
                                "duplicate": duplicate,
                                "name_similarity": sim,
                                "attribute_similarity": attr_score,
                                "confidence": combined_score,
                            }
                        )

        # 信頼度でソート
        similar.sort(key=lambda x: x["confidence"], reverse=True)
        self.similar_duplicates = similar
        return similar

    def _attribute_similarity(self, p1: Dict, p2: Dict) -> float:
        """
        属性ベースの類似度を計算

        Args:
            p1: 人物1データ
            p2: 人物2データ

        Returns:
            属性類似度（0.0-1.0）
        """
        score = 0.0
        checks = 0

        # カテゴリ一致
        cat1 = str(p1.get("category", "")).strip()
        cat2 = str(p2.get("category", "")).strip()
        if cat1 and cat2:
            checks += 1
            if cat1 == cat2:
                score += 1.0

        # 生年一致
        by1 = p1.get("birth_year")
        by2 = p2.get("birth_year")
        if by1 and by2 and not pd.isna(by1) and not pd.isna(by2):
            checks += 1
            if abs(float(by1) - float(by2)) <= 1:  # 1年以内の誤差を許容
                score += 1.0

        # person_type一致
        pt1 = str(p1.get("person_type", "")).upper()
        pt2 = str(p2.get("person_type", "")).upper()
        if pt1 and pt2:
            checks += 1
            if pt1 == pt2:
                score += 1.0

        return score / checks if checks > 0 else 0.5

    def detect_all(self) -> Dict:
        """
        全重複を検出

        Returns:
            検出結果サマリー
        """
        print("🔍 完全一致重複を検出中...")
        exact = self.detect_exact_duplicates()
        print(f"  検出: {len(exact)}グループ")

        print("🔍 類似一致重複を検出中...")
        similar = self.detect_similar_duplicates()
        print(f"  検出: {len(similar)}ペア")

        # 全重複をマージ
        self.all_duplicates = []

        # 完全一致
        for dup in exact:
            for d in dup["duplicates"]:
                self.all_duplicates.append(
                    {
                        "type": "exact",
                        "canonical_id": dup["canonical"]["person_id"],
                        "canonical_name": dup["canonical"]["person_name"],
                        "duplicate_id": d["person_id"],
                        "duplicate_name": d["person_name"],
                        "confidence": dup["confidence"],
                    }
                )

        # 類似一致
        for dup in similar:
            self.all_duplicates.append(
                {
                    "type": "similar",
                    "canonical_id": dup["canonical"]["person_id"],
                    "canonical_name": dup["canonical"]["person_name"],
                    "duplicate_id": dup["duplicate"]["person_id"],
                    "duplicate_name": dup["duplicate"]["person_name"],
                    "confidence": dup["confidence"],
                    "name_similarity": dup["name_similarity"],
                }
            )

        return self._get_summary()

    def _get_summary(self) -> Dict:
        """検出結果サマリーを取得"""
        return {
            "timestamp": datetime.now().isoformat(),
            "total_persons": len(self.persons),
            "exact_duplicate_groups": len(self.exact_duplicates),
            "similar_duplicate_pairs": len(self.similar_duplicates),
            "total_duplicates": len(self.all_duplicates),
            "threshold": self.threshold,
        }

    def export_results(self, output_dir: str):
        """結果をファイルに出力"""
        os.makedirs(output_dir, exist_ok=True)

        # 全重複CSV
        if self.all_duplicates:
            df = pd.DataFrame(self.all_duplicates)
            csv_path = os.path.join(output_dir, "duplicates.csv")
            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            print(f"✅ 重複CSV: {csv_path}")

        # サマリーJSON
        summary = self._get_summary()
        json_path = os.path.join(output_dir, "duplicate_summary.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"✅ サマリーJSON: {json_path}")


# ========================================
# 重複統合
# ========================================


class DuplicateMerger:
    """重複人物統合クラス"""

    def __init__(self, csv_path: str, duplicates: List[Dict]):
        """
        Args:
            csv_path: MASTER CSVパス
            duplicates: 重複リスト
        """
        self.csv_path = csv_path
        self.duplicates = duplicates
        self.df = pd.read_csv(csv_path, encoding="utf-8-sig")
        self.merge_log: List[Dict] = []

    def merge_all(self, dry_run: bool = True, min_confidence: float = 0.9) -> Dict:
        """
        全重複を統合

        Args:
            dry_run: ドライランモード
            min_confidence: 最小信頼度

        Returns:
            統合結果サマリー
        """
        merged = 0
        skipped = 0

        for dup in self.duplicates:
            confidence = dup.get("confidence", 0)

            if confidence < min_confidence:
                skipped += 1
                continue

            canonical_id = dup["canonical_id"]
            duplicate_id = dup["duplicate_id"]

            if not dry_run:
                # person_idを正規IDに更新
                self.df.loc[self.df["person_id"] == duplicate_id, "person_id"] = canonical_id

            self.merge_log.append(
                {
                    "canonical_id": canonical_id,
                    "canonical_name": dup["canonical_name"],
                    "merged_id": duplicate_id,
                    "merged_name": dup["duplicate_name"],
                    "confidence": confidence,
                    "type": dup["type"],
                }
            )
            merged += 1

        summary = {
            "timestamp": datetime.now().isoformat(),
            "merged": merged,
            "skipped": skipped,
            "min_confidence": min_confidence,
            "dry_run": dry_run,
        }

        if not dry_run and merged > 0:
            # バックアップ作成
            os.makedirs(BACKUP_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = BACKUP_DIR / f"MASTER_EPISODES_CURRENT_{timestamp}_pre_merge.csv"
            shutil.copy(self.csv_path, backup_path)
            print(f"📦 バックアップ作成: {backup_path}")

            # CSVを更新
            self.df.to_csv(self.csv_path, index=False, encoding="utf-8-sig")
            print(f"✅ MASTER CSV更新: {self.csv_path}")

        return summary

    def export_merge_log(self, output_dir: str):
        """マージログを出力"""
        os.makedirs(output_dir, exist_ok=True)

        if self.merge_log:
            df = pd.DataFrame(self.merge_log)
            csv_path = os.path.join(output_dir, "merge_log.csv")
            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            print(f"✅ マージログ: {csv_path}")


# ========================================
# メイン処理
# ========================================


def main():
    parser = argparse.ArgumentParser(description="重複人物の検出・統合")
    parser.add_argument("--csv-path", default=str(MASTER_CSV), help="MASTER CSVパス")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR), help="出力ディレクトリ")
    parser.add_argument("--threshold", type=float, default=0.85, help="類似度閾値 (default: 0.85)")
    parser.add_argument("--min-confidence", type=float, default=0.90, help="統合の最小信頼度 (default: 0.90)")
    parser.add_argument("--detect-only", action="store_true", help="検出のみ（統合しない）")
    parser.add_argument("--dry-run", action="store_true", help="ドライランモード")
    parser.add_argument("--execute", action="store_true", help="実際に統合を実行")

    args = parser.parse_args()

    # ドライランがデフォルト
    dry_run = not args.execute

    print("=" * 60)
    print("重複人物 検出・統合スクリプト")
    print("=" * 60)
    print(f"入力: {args.csv_path}")
    print(f"出力: {args.output_dir}")
    print(f"類似度閾値: {args.threshold}")
    print(f"統合信頼度閾値: {args.min_confidence}")
    print(f"モード: {'検出のみ' if args.detect_only else '検出+統合'}")
    if not args.detect_only:
        print(f"実行モード: {'ドライラン' if dry_run else '実行'}")
    print()

    # 検出
    detector = DuplicateDetector(args.csv_path, args.threshold)
    summary = detector.detect_all()

    # 結果表示
    print()
    print("=" * 60)
    print("検出結果サマリー")
    print("=" * 60)
    print(f"総人物数: {summary['total_persons']:,}")
    print(f"完全一致グループ: {summary['exact_duplicate_groups']:,}")
    print(f"類似一致ペア: {summary['similar_duplicate_pairs']:,}")
    print(f"総重複数: {summary['total_duplicates']:,}")

    # サンプル表示
    if detector.exact_duplicates:
        print()
        print("=" * 60)
        print("完全一致サンプル（最初の5グループ）")
        print("=" * 60)
        for dup in detector.exact_duplicates[:5]:
            print(f"  正規: {dup['canonical']['person_name']} ({dup['canonical']['episode_count']}ep)")
            for d in dup["duplicates"]:
                print(f"    → {d['person_name']} ({d['episode_count']}ep)")

    if detector.similar_duplicates:
        print()
        print("=" * 60)
        print("類似一致サンプル（最初の5ペア）")
        print("=" * 60)
        for dup in detector.similar_duplicates[:5]:
            print(f"  {dup['canonical']['person_name']} ↔ {dup['duplicate']['person_name']}")
            print(f"    類似度: {dup['name_similarity']:.2f}, 信頼度: {dup['confidence']:.2f}")

    # ファイル出力
    print()
    print("=" * 60)
    print("ファイル出力")
    print("=" * 60)
    detector.export_results(args.output_dir)

    # 統合（検出のみでない場合）
    if not args.detect_only and detector.all_duplicates:
        print()
        print("=" * 60)
        print("重複統合")
        print("=" * 60)

        merger = DuplicateMerger(args.csv_path, detector.all_duplicates)
        merge_summary = merger.merge_all(dry_run=dry_run, min_confidence=args.min_confidence)

        print(f"統合件数: {merge_summary['merged']:,}")
        print(f"スキップ: {merge_summary['skipped']:,}")

        merger.export_merge_log(args.output_dir)

    print()
    print("✅ 処理完了")

    if not args.detect_only and dry_run:
        print()
        print("💡 実際に統合するには --execute オプションを付けて再実行してください")


if __name__ == "__main__":
    main()
