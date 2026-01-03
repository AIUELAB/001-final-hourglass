#!/usr/bin/env python3
"""
人物名・人物ID名寄せ統合スクリプト

別名（山中教授、マンデラ、ホリエモン）を正規表記（山中伸弥、ネルソン・マンデラ、堀江貴文）に統合し、
person_idを一元化する。

使用方法:
    # ドライラン（変更せずに影響範囲を確認）
    python scripts/merge_person_aliases.py --dry-run

    # 本番実行
    python scripts/merge_person_aliases.py --execute

作成日: 2025-12-15
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


class PersonAliasMerger:
    """人物名別名統合クラス"""

    # 統合ペア定義: alias → canonical
    ALIAS_PAIRS = {
        "山中教授": "山中伸弥",
        "マンデラ": "ネルソン・マンデラ",
        "ホリエモン": "堀江貴文",
    }

    def __init__(self, csv_path: str, dry_run: bool = True):
        """
        初期化

        Args:
            csv_path: マスターCSVのパス
            dry_run: ドライランモード（Trueの場合は変更せず影響範囲のみ確認）
        """
        self.csv_path = Path(csv_path)
        self.dry_run = dry_run
        self.df: Optional[pd.DataFrame] = None
        self.df_original: Optional[pd.DataFrame] = None
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": dry_run,
            "csv_path": str(csv_path),
            "pairs": [],
            "summary": {},
            "status": "initialized",
        }

    def load_csv(self) -> None:
        """CSVファイルを読み込む"""
        print(f"📂 CSV読み込み: {self.csv_path}")
        try:
            self.df = pd.read_csv(self.csv_path, encoding="utf-8-sig")
            self.df_original = self.df.copy()
            print(f"  レコード数: {len(self.df):,}件")
            print(f"  ユニークperson_id数: {self.df['person_id'].nunique():,}件")
            print(f"  ユニークperson_name数: {self.df['person_name'].nunique():,}件")
        except Exception as e:
            self.results["status"] = "error"
            self.results["error_message"] = f"CSV読み込みエラー: {e}"
            raise

    def analyze_before_state(self) -> Dict[str, Dict]:
        """統合前の状態を分析"""
        print("\n📊 Before統計:")
        before_stats = {}

        for alias, canonical in self.ALIAS_PAIRS.items():
            alias_df = self.df[self.df["person_name"] == alias]
            canonical_df = self.df[self.df["person_name"] == canonical]

            alias_count = len(alias_df)
            canonical_count = len(canonical_df)

            alias_id = alias_df["person_id"].iloc[0] if alias_count > 0 else None
            canonical_id = canonical_df["person_id"].iloc[0] if canonical_count > 0 else None

            print(f'  「{alias}」: {alias_count}件 (ID: {alias_id or "N/A"})')
            print(f'  「{canonical}」: {canonical_count}件 (ID: {canonical_id or "N/A"})')

            before_stats[alias] = {
                "alias": alias,
                "canonical": canonical,
                "alias_count": alias_count,
                "canonical_count": canonical_count,
                "alias_id": alias_id,
                "canonical_id": canonical_id,
            }

        return before_stats

    def merge_person_names(self) -> Dict[str, int]:
        """person_nameフィールドの統合（完全一致）"""
        print("\n🔄 person_name統合処理中...")
        replacements = {}

        for alias, canonical in self.ALIAS_PAIRS.items():
            mask = self.df["person_name"] == alias
            count = mask.sum()

            if count > 0:
                if not self.dry_run:
                    self.df.loc[mask, "person_name"] = canonical
                print(f"  「{alias}」→「{canonical}」: {count}件置換")
                replacements[alias] = count
            else:
                print(f"  「{alias}」: データなし")
                replacements[alias] = 0

        return replacements

    def merge_episode_texts(self) -> Dict[str, List[Dict]]:
        """episode_textフィールドの統合（単語境界考慮）"""
        print("\n🔄 episode_text統合処理中...")
        text_replacements = {}

        for alias, canonical in self.ALIAS_PAIRS.items():
            # 単語境界を考慮した正規表現パターン
            # 日本語の文字（ひらがな、カタカナ、漢字、記号）の前後にはマッチしない
            pattern = rf"(?<![ァ-ヶ一-龠々ー・]){re.escape(alias)}(?![ァ-ヶ一-龠々ー・])"

            # 置換対象のエピソードを検出
            mask = self.df["episode_text"].str.contains(pattern, na=False, regex=True)
            affected_episodes = self.df[mask].copy()

            replacements_list = []
            for idx, row in affected_episodes.iterrows():
                original_text = row["episode_text"]
                new_text = re.sub(pattern, canonical, original_text)

                if original_text != new_text:
                    if not self.dry_run:
                        self.df.at[idx, "episode_text"] = new_text

                    replacements_list.append(
                        {
                            "episode_id": row["episode_id"],
                            "person_name": row["person_name"],
                            "original_snippet": self._get_snippet(original_text, alias),
                            "new_snippet": self._get_snippet(new_text, canonical),
                        }
                    )

            if replacements_list:
                print(f"  「{alias}」→「{canonical}」: {len(replacements_list)}箇所置換")
            else:
                print(f"  「{alias}」: データなし")

            text_replacements[alias] = replacements_list

        return text_replacements

    def _get_snippet(self, text: str, keyword: str, context_chars: int = 50) -> str:
        """キーワード周辺のスニペットを抽出"""
        try:
            idx = text.find(keyword)
            if idx == -1:
                return ""
            start = max(0, idx - context_chars)
            end = min(len(text), idx + len(keyword) + context_chars)
            snippet = text[start:end]
            return f"...{snippet}..."
        except Exception:
            return ""

    def merge_person_ids(self, before_stats: Dict[str, Dict]) -> Dict[str, Dict]:
        """person_idの統合（エピソード数が多い方を代表）"""
        print("\n🔄 person_id統合処理中...")
        id_merges = {}

        for alias, canonical in self.ALIAS_PAIRS.items():
            stats = before_stats[alias]
            alias_count = stats["alias_count"]
            canonical_count = stats["canonical_count"]
            alias_id = stats["alias_id"]
            canonical_id = stats["canonical_id"]

            if alias_count == 0 or alias_id is None:
                print(f"  「{alias}」: データなし（スキップ）")
                id_merges[alias] = {"skipped": True, "reason": "no_alias_data"}
                continue

            if canonical_count == 0 or canonical_id is None:
                print(f"  「{canonical}」: データなし（スキップ）")
                id_merges[alias] = {"skipped": True, "reason": "no_canonical_data"}
                continue

            # 代表IDを選定（エピソード数が多い方）
            if canonical_count >= alias_count:
                representative_id = canonical_id
                deprecated_id = alias_id
            else:
                representative_id = alias_id
                deprecated_id = canonical_id

            # person_idを統合
            mask = self.df["person_id"] == deprecated_id
            merged_count = mask.sum()

            if merged_count > 0:
                if not self.dry_run:
                    self.df.loc[mask, "person_id"] = representative_id
                print(f"  {deprecated_id} → {representative_id}: {merged_count}件統合")

            id_merges[alias] = {
                "skipped": False,
                "representative_id": representative_id,
                "deprecated_id": deprecated_id,
                "merged_count": merged_count,
            }

        return id_merges

    def save_csv(self) -> None:
        """変更後のCSVを保存"""
        if self.dry_run:
            print("\n⚠️  ドライランモード: CSVは保存されません")
            return

        print(f"\n💾 CSV保存中: {self.csv_path}")
        try:
            self.df.to_csv(self.csv_path, index=False, encoding="utf-8-sig")
            print("✅ 保存完了")
        except Exception as e:
            self.results["status"] = "error"
            self.results["error_message"] = f"CSV保存エラー: {e}"
            raise

    def generate_report(
        self,
        before_stats: Dict,
        person_name_replacements: Dict,
        text_replacements: Dict,
        id_merges: Dict,
    ) -> None:
        """処理結果レポートを生成"""
        print("\n" + "=" * 70)
        print("📊 処理結果")
        print("=" * 70)

        total_person_name = sum(person_name_replacements.values())
        total_episode_text = sum(len(v) for v in text_replacements.values())
        total_person_ids = sum(m["merged_count"] for m in id_merges.values() if not m.get("skipped", False))

        print(f"  person_name置換: {total_person_name}件")
        print(f"  episode_text置換: {total_episode_text}箇所")
        print(f"  person_id統合: {total_person_ids}件")

        self.results["summary"] = {
            "total_person_name_replaced": total_person_name,
            "total_episode_text_replaced": total_episode_text,
            "total_person_ids_merged": total_person_ids,
            "total_records": len(self.df),
            "unique_person_ids": self.df["person_id"].nunique(),
            "unique_person_names": self.df["person_name"].nunique(),
        }

        # ペア別詳細
        for alias, canonical in self.ALIAS_PAIRS.items():
            pair_result = {
                "alias": alias,
                "canonical": canonical,
                "before": before_stats[alias],
                "person_name_replacements": person_name_replacements.get(alias, 0),
                "episode_text_replacements": text_replacements.get(alias, []),
                "episode_text_total_replacements": len(text_replacements.get(alias, [])),
                "person_id_merge": id_merges.get(alias, {}),
                "status": "success" if person_name_replacements.get(alias, 0) >= 0 else "error",
            }
            self.results["pairs"].append(pair_result)

            print(f"\n📋 「{alias}」→「{canonical}」")
            if not id_merges[alias].get("skipped", False):
                print(f'  代表person_id: {id_merges[alias]["representative_id"]}')
            print(f"  person_name置換: {person_name_replacements.get(alias, 0)}件")
            print(f"  episode_text置換: {len(text_replacements.get(alias, []))}箇所")
            if not id_merges[alias].get("skipped", False):
                print(f'  person_id統合: {id_merges[alias]["merged_count"]}件')

        self.results["status"] = "success"

    def _convert_to_json_serializable(self, obj):
        """pandasのint64など、JSONシリアライズできない型を変換"""
        import numpy as np

        if isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_to_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_json_serializable(item) for item in obj]
        else:
            return obj

    def save_report(self) -> str:
        """レポートをJSONで保存"""
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)

        mode = "dryrun" if self.dry_run else "executed"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = reports_dir / f"person_alias_merge_{mode}_{timestamp}.json"

        # JSONシリアライズ可能な形式に変換
        serializable_results = self._convert_to_json_serializable(self.results)

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(serializable_results, f, ensure_ascii=False, indent=2)

        print(f"\n📄 レポート保存: {report_path}")
        return str(report_path)

    def run(self) -> Dict:
        """統合処理を実行"""
        print("=" * 70)
        print(f"🔧 人物名・人物ID名寄せ統合 {'(dry-run)' if self.dry_run else '(execute)'}")
        print("=" * 70)
        print(f"  実行日時: {self.results['timestamp']}")
        print()

        try:
            # 1. CSV読み込み
            self.load_csv()

            # 2. Before状態の分析
            before_stats = self.analyze_before_state()

            # 3. person_name統合
            person_name_replacements = self.merge_person_names()

            # 4. episode_text統合
            text_replacements = self.merge_episode_texts()

            # 5. person_id統合
            id_merges = self.merge_person_ids(before_stats)

            # 6. CSV保存（本番モードのみ）
            self.save_csv()

            # 7. レポート生成
            self.generate_report(
                before_stats,
                person_name_replacements,
                text_replacements,
                id_merges,
            )

            # 8. レポート保存
            self.save_report()

            print("\n✅ 完了")
            return self.results

        except Exception as e:
            print(f"\n❌ エラー: {e}")
            self.results["status"] = "error"
            self.results["error_message"] = str(e)
            self.save_report()
            raise


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description="人物名・人物ID名寄せ統合スクリプト",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # ドライラン（影響範囲の確認のみ）
  python scripts/merge_person_aliases.py --dry-run

  # 本番実行
  python scripts/merge_person_aliases.py --execute
        """,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ドライランモード（変更せずに影響範囲を確認）",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="本番実行モード（実際に変更を適用）",
    )
    parser.add_argument(
        "--csv-path",
        type=str,
        default="preserved/data/MASTER_EPISODES_CURRENT.csv",
        help="マスターCSVのパス（デフォルト: preserved/data/MASTER_EPISODES_CURRENT.csv）",
    )

    args = parser.parse_args()

    # dry-runとexecuteのどちらも指定されていない場合はエラー
    if not args.dry_run and not args.execute:
        parser.error("--dry-run または --execute のいずれかを指定してください")

    # 両方指定された場合はエラー
    if args.dry_run and args.execute:
        parser.error("--dry-run と --execute は同時に指定できません")

    # 統合処理実行
    merger = PersonAliasMerger(csv_path=args.csv_path, dry_run=args.dry_run)
    merger.run()


if __name__ == "__main__":
    main()
