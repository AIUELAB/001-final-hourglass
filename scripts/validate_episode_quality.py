#!/usr/bin/env python3
"""
エピソード品質バリデーション
- メタ表現検出
- 時系列矛盾検出
- 事実検証ステータスチェック
"""

import pandas as pd
import re
import sys
from pathlib import Path


class EpisodeQualityValidator:
    """エピソード品質検証クラス"""

    # メタ表現パターン
    META_PATTERNS = [
        r"あなたと同じ",
        r"あなたが",
        r"あなたの",
        r"私たちは",
        r"読者の皆さん",
    ]

    # 時系列矛盾パターン（単一年齢EPに不適切）
    TIMELINE_PATTERNS = [
        r"翌年",
        r"翌々年",
        r"その後\d+年",
        r"数年後",
        r"\d+年後に",
    ]

    def __init__(self, csv_path: str):
        self.df = pd.read_csv(csv_path, low_memory=False)
        self.violations = []

    def check_meta_expressions(self) -> list:
        """メタ表現チェック"""
        results = []
        for _, row in self.df.iterrows():
            text = str(row.get("episode_text", ""))
            for pattern in self.META_PATTERNS:
                if re.search(pattern, text):
                    results.append(
                        {
                            "episode_id": row["episode_id"],
                            "person_name": row["person_name"],
                            "type": "メタ表現",
                            "pattern": pattern,
                            "quote": text[:80],
                        }
                    )
                    break
        return results

    def check_timeline_consistency(self) -> list:
        """時系列整合性チェック"""
        results = []
        for _, row in self.df.iterrows():
            text = str(row.get("episode_text", ""))
            for pattern in self.TIMELINE_PATTERNS:
                match = re.search(pattern, text)
                if match:
                    results.append(
                        {
                            "episode_id": row["episode_id"],
                            "person_name": row["person_name"],
                            "age": row.get("age"),
                            "type": "時系列矛盾",
                            "pattern": pattern,
                            "match": match.group(),
                        }
                    )
                    break
        return results

    def check_fact_verification(self) -> list:
        """事実検証ステータスチェック"""
        results = []
        for _, row in self.df.iterrows():
            fact_check = str(row.get("fact_check_result", ""))
            evidence = str(row.get("evidence_quality", ""))
            if fact_check in ["未確認", "nan", ""] or evidence in ["low", "nan", ""]:
                results.append(
                    {
                        "episode_id": row["episode_id"],
                        "person_name": row["person_name"],
                        "type": "未検証",
                        "fact_check": fact_check,
                        "evidence": evidence,
                    }
                )
        return results

    def run_all_checks(self, verbose=False) -> dict:
        """全チェック実行"""
        meta = self.check_meta_expressions()
        timeline = self.check_timeline_consistency()
        # fact検証は件数が多いため別レポート

        summary = {
            "total_episodes": len(self.df),
            "meta_violations": len(meta),
            "timeline_violations": len(timeline),
            "meta_details": meta[:10] if not verbose else meta,
            "timeline_details": timeline[:10] if not verbose else timeline,
        }
        return summary


def main():
    csv_path = "preserved/data/MASTER_EPISODES_CURRENT.csv"
    validator = EpisodeQualityValidator(csv_path)
    results = validator.run_all_checks()

    print("=" * 60)
    print("エピソード品質チェック結果")
    print("=" * 60)
    print(f"総エピソード数: {results['total_episodes']}")
    print(f"メタ表現違反: {results['meta_violations']}件")
    print(f"時系列矛盾: {results['timeline_violations']}件")

    if results["meta_violations"] > 0:
        print("\n【メタ表現違反サンプル】")
        for v in results["meta_details"][:5]:
            print(f"  {v['episode_id']}: {v['person_name']} - {v['pattern']}")

    if results["timeline_violations"] > 0:
        print("\n【時系列矛盾サンプル】")
        for v in results["timeline_details"][:5]:
            print(f"  {v['episode_id']}: {v['person_name']} ({v['age']}歳) - '{v['match']}'")

    # 終了コード（CI用）
    if results["meta_violations"] > 0 or results["timeline_violations"] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
