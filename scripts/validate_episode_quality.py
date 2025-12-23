#!/usr/bin/env python3
"""
エピソード品質バリデーション
- メタ表現検出
- 時系列矛盾検出
- 事実検証ステータスチェック
- 具体性欠如検出（抽象表現のみのエピソード）
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

    # 抽象表現パターン（具体性欠如の指標）
    ABSTRACT_PATTERNS = [
        r"大きな困難",
        r"様々な問題",
        r"新たな挑戦",
        r"困難に直面",
        r"諦めることなく",
        r"見事に.*乗り越え",
        r"柔軟な発想",
        r"自らの.*を活かして",
        r"緊密なコミュニケーション",
        r"情熱と挑戦心",
        r"解決策を見出し",
        r"新たな.*を生み出し",
        r"経験を活かして",
        r"難局を乗り越え",
        r"創造性.*活かして",
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

    def check_specificity(self) -> list:
        """具体性欠如チェック（抽象表現が多く具体情報がない）"""
        results = []
        for _, row in self.df.iterrows():
            text = str(row.get("episode_text", ""))
            if pd.isna(row.get("episode_text")):
                continue

            # 抽象表現カウント
            abstract_count = sum(1 for p in self.ABSTRACT_PATTERNS if re.search(p, text))

            # 具体情報の有無
            has_work = bool(re.search(r"[「『].*?[」』]", text))
            has_year = bool(re.search(r"(19|20)\d{2}年", text))
            has_number = bool(re.search(r"\d+億|\d+万|\d+%|\d+本|\d+回|\d+位|\d+円", text))

            # 抽象表現3つ以上 AND 具体情報なし = 低品質
            if abstract_count >= 3 and not (has_work or has_year or has_number):
                results.append(
                    {
                        "episode_id": row["episode_id"],
                        "person_name": row["person_name"],
                        "age": row.get("age"),
                        "type": "具体性欠如",
                        "abstract_count": abstract_count,
                        "text_preview": text[:100],
                    }
                )
        return results

    def run_all_checks(self, verbose=False) -> dict:
        """全チェック実行"""
        meta = self.check_meta_expressions()
        timeline = self.check_timeline_consistency()
        specificity = self.check_specificity()
        # fact検証は件数が多いため別レポート

        summary = {
            "total_episodes": len(self.df),
            "meta_violations": len(meta),
            "timeline_violations": len(timeline),
            "specificity_violations": len(specificity),
            "meta_details": meta[:10] if not verbose else meta,
            "timeline_details": timeline[:10] if not verbose else timeline,
            "specificity_details": specificity if not verbose else specificity,
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
    print(f"具体性欠如: {results['specificity_violations']}件")

    if results["meta_violations"] > 0:
        print("\n【メタ表現違反サンプル】")
        for v in results["meta_details"][:5]:
            print(f"  {v['episode_id']}: {v['person_name']} - {v['pattern']}")

    if results["timeline_violations"] > 0:
        print("\n【時系列矛盾サンプル】")
        for v in results["timeline_details"][:5]:
            print(f"  {v['episode_id']}: {v['person_name']} ({v['age']}歳) - '{v['match']}'")

    if results["specificity_violations"] > 0:
        print("\n【具体性欠如（削除推奨）】")
        for v in results["specificity_details"]:
            print(f"  {v['episode_id']}: {v['person_name']} - 抽象表現{v['abstract_count']}個")

    # 終了コード（CI用）- 具体性欠如があれば失敗
    if results["specificity_violations"] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
