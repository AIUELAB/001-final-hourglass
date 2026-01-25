#!/usr/bin/env python3
"""
全エピソード監査スクリプト（dry-run）
- メタ説明、未来予測、推測、重複を検出
- 分類結果をレポート出力
"""

import pandas as pd
import re
import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import sys

# 親ディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))
from episode_quality_system.template_blocker import TemplateBlocker

# データファイルパス
DATA_FILE = Path(__file__).parent.parent / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = Path(__file__).parent.parent / "reports"


class ProhibitedPatternDetector:
    """禁止パターン検出器"""

    def __init__(self):
        self.template_blocker = TemplateBlocker()

        # 未来予測パターン（ミッションで指定）
        self.future_patterns = [
            (r"今後.*?だろう", "未来予測"),
            (r"今後.*?でしょう", "未来予測"),
            (r"〜する予定", "予定表現"),
            (r"する予定", "予定表現"),
            (r"予定(です|だ|である)", "予定表現"),
            (r"まだ到来していない", "未到達表現"),
            (r"まだ到達していない", "未到達表現"),
            (r"この年齢はまだ", "未到達表現"),
            (r"〜を迎えます", "未来形"),
            (r"迎えることになります", "未来形"),
            (r"〜歳を迎え", "未来形（文脈依存）"),
            (r"(する|なる)ことになる", "未来予測"),
            (r"(する|なる)はずだ", "推測"),
            (r"(今後|将来).*?(予想|予測|見込)", "未来予測"),
            (r"\d{4}年.*?(予定|見込)", "未来予定"),
        ]

        # 推測パターン
        self.speculation_patterns = [
            (r"かもしれない", "推測"),
            (r"かもしれません", "推測"),
            (r"と見られている", "推測"),
            (r"と見られて", "推測"),
            (r"と推測される", "推測"),
            (r"と思われる", "推測"),
            (r"と考えられる", "推測"),
            (r"おそらく", "推測"),
            (r"可能性がある", "推測"),
            (r"だろうと", "推測"),
            (r"ではないか", "推測"),
            (r"ではないだろうか", "推測"),
        ]

        # メタ説明パターン（追加）
        self.meta_patterns = [
            (r"として知られる", "メタ説明"),
            (r"として知られて", "メタ説明"),
            (r"として有名", "メタ説明"),
            (r"で知られる", "メタ説明"),
            (r"代表作(は|として)", "メタ説明"),
            (r"人気を博した", "メタ説明"),
            (r"注目を集めた", "メタ説明"),
            (r"話題(を|と)なった", "メタ説明"),
            (r"として活躍", "メタ説明"),
            (r"として名を馳せ", "メタ説明"),
            (r"広く認知され", "メタ説明"),
            (r"〜という異名", "メタ説明"),
            (r"という異名", "メタ説明"),
            (r"異名を持つ", "メタ説明"),
            # お断り系
            (r"申し訳ございません", "お断り"),
            (r"申し訳ありません", "お断り"),
            (r"生成することができません", "お断り"),
            (r"エピソードはありません", "お断り"),
            (r"情報がありません", "お断り"),
            # 架空キャラメタ
            (r"架空の(キャラクター|人物)", "メタ説明"),
            (r"実在しない", "メタ説明"),
            (r"フィクション(として|である)", "メタ説明"),
        ]

    def detect_violations(self, episode_text: str, person_type: str = None) -> dict:
        """
        エピソードの違反を検出

        Returns:
            {
                'has_violation': bool,
                'violation_types': list,
                'details': list of (pattern, matched_text, type)
            }
        """
        if pd.isna(episode_text) or not episode_text:
            return {"has_violation": True, "violation_types": ["EMPTY"], "details": []}

        violations = []
        violation_types = set()

        # 1. TemplateBlockerによるチェック
        should_block, tb_violations = self.template_blocker.check_episode(episode_text, person_type)
        if tb_violations:
            for v in tb_violations:
                violations.append((v.pattern, v.matched_text, v.type.value))
                violation_types.add(v.type.value)

        # 2. 未来予測チェック
        for pattern, vtype in self.future_patterns:
            matches = re.finditer(pattern, episode_text)
            for m in matches:
                violations.append((pattern, m.group(), f"未来予測:{vtype}"))
                violation_types.add("未来予測")

        # 3. 推測チェック
        for pattern, vtype in self.speculation_patterns:
            matches = re.finditer(pattern, episode_text)
            for m in matches:
                violations.append((pattern, m.group(), f"推測:{vtype}"))
                violation_types.add("推測")

        # 4. メタ説明チェック（追加パターン）
        for pattern, vtype in self.meta_patterns:
            matches = re.finditer(pattern, episode_text)
            for m in matches:
                violations.append((pattern, m.group(), f"メタ説明:{vtype}"))
                violation_types.add("メタ説明")

        return {"has_violation": len(violations) > 0, "violation_types": list(violation_types), "details": violations}


def detect_duplicates(df: pd.DataFrame) -> dict:
    """重複エピソード検出（person_id + age）"""

    # person_id + age でグループ化
    if "person_id" not in df.columns:
        # person_nameで代用
        df["_key"] = df["person_name"].astype(str) + "_" + df["age"].astype(str)
    else:
        df["_key"] = df["person_id"].astype(str) + "_" + df["age"].astype(str)

    duplicates = []
    duplicate_groups = df.groupby("_key").filter(lambda x: len(x) > 1)

    if len(duplicate_groups) > 0:
        for key, group in df.groupby("_key"):
            if len(group) > 1:
                duplicates.append(
                    {
                        "key": key,
                        "count": len(group),
                        "episode_ids": group["episode_id"].tolist(),
                        "person_name": group["person_name"].iloc[0],
                        "age": group["age"].iloc[0],
                    }
                )

    # 一時カラム削除
    if "_key" in df.columns:
        df.drop("_key", axis=1, inplace=True)

    return {
        "total_duplicate_groups": len(duplicates),
        "total_duplicate_episodes": sum(d["count"] for d in duplicates),
        "examples": duplicates[:20],  # 最大20例
    }


def run_audit(dry_run: bool = True):
    """全件監査を実行"""

    print("=" * 70)
    print("📋 エピソード品質監査（Phase 1: 全件スキャン）")
    print("=" * 70)

    # データ読み込み
    print(f"\n📂 データ読み込み: {DATA_FILE}")
    df = pd.read_csv(DATA_FILE, encoding="utf-8-sig")
    total = len(df)
    print(f"   総エピソード数: {total:,}件")

    # 検出器初期化
    detector = ProhibitedPatternDetector()

    # 結果格納
    results = {
        "timestamp": datetime.now().isoformat(),
        "total_episodes": total,
        "dry_run": dry_run,
        "categories": {
            "OK": {"count": 0, "examples": []},
            "META": {"count": 0, "examples": []},
            "FUTURE": {"count": 0, "examples": []},
            "SPECULATION": {"count": 0, "examples": []},
            "TEMPLATE": {"count": 0, "examples": []},
            "EMPTY": {"count": 0, "examples": []},
            "DUPLICATE": {"count": 0, "examples": []},
        },
        "violation_details": defaultdict(list),
        "by_person_type": {"REAL": defaultdict(int), "FICTIONAL": defaultdict(int)},
    }

    # 全件スキャン
    print("\n🔍 全件スキャン中...")

    ng_episodes = []

    for idx, row in df.iterrows():
        episode_id = row.get("episode_id", f"row_{idx}")
        episode_text = row.get("episode_text", "")
        person_type = row.get("person_type", "REAL")
        person_name = row.get("person_name", "")
        age = row.get("age", "")

        # 違反検出
        result = detector.detect_violations(episode_text, person_type)

        if result["has_violation"]:
            # カテゴリ分類
            categories_hit = set()

            for vtype in result["violation_types"]:
                if "EMPTY" in vtype:
                    categories_hit.add("EMPTY")
                elif "未来予測" in vtype:
                    categories_hit.add("FUTURE")
                elif "推測" in vtype:
                    categories_hit.add("SPECULATION")
                elif "メタ" in vtype or "META" in vtype.upper():
                    categories_hit.add("META")
                elif "定型文" in vtype or "TEMPLATE" in vtype.upper():
                    categories_hit.add("TEMPLATE")
                else:
                    # その他はTEMPLATEに分類
                    categories_hit.add("TEMPLATE")

            # 各カテゴリにカウント
            for cat in categories_hit:
                results["categories"][cat]["count"] += 1
                results["by_person_type"][person_type if person_type in ["REAL", "FICTIONAL"] else "REAL"][cat] += 1

                # 代表例（各カテゴリ最大10件）
                if len(results["categories"][cat]["examples"]) < 10:
                    results["categories"][cat]["examples"].append(
                        {
                            "episode_id": episode_id,
                            "person_name": person_name,
                            "age": age,
                            "person_type": person_type,
                            "text_preview": episode_text[:200] if episode_text else "",
                            "violations": result["details"][:5],  # 最大5件の違反詳細
                        }
                    )

            ng_episodes.append(
                {
                    "episode_id": episode_id,
                    "person_name": person_name,
                    "age": age,
                    "categories": list(categories_hit),
                    "violation_count": len(result["details"]),
                }
            )
        else:
            results["categories"]["OK"]["count"] += 1
            results["by_person_type"][person_type if person_type in ["REAL", "FICTIONAL"] else "REAL"]["OK"] += 1

        # 進捗表示
        if (idx + 1) % 2000 == 0:
            print(f"   {idx + 1:,}/{total:,} 処理完了...")

    # 重複検出
    print("\n🔍 重複検出中...")
    dup_result = detect_duplicates(df)
    results["categories"]["DUPLICATE"]["count"] = dup_result["total_duplicate_groups"]
    results["categories"]["DUPLICATE"]["examples"] = dup_result["examples"]
    results["duplicate_info"] = dup_result

    # レポート出力
    print("\n" + "=" * 70)
    print("📊 監査結果サマリー")
    print("=" * 70)

    ok_count = results["categories"]["OK"]["count"]
    ng_count = total - ok_count

    print("\n【総合】")
    print(f"  ✅ OK（違反なし）: {ok_count:,}件 ({ok_count / total * 100:.1f}%)")
    print(f"  ❌ NG（要修正）  : {ng_count:,}件 ({ng_count / total * 100:.1f}%)")

    print("\n【NGカテゴリ内訳】")
    for cat, data in results["categories"].items():
        if cat == "OK":
            continue
        count = data["count"]
        if count > 0:
            print(f"  {cat}: {count:,}件 ({count / total * 100:.2f}%)")

    print("\n【person_type別】")
    for ptype, counts in results["by_person_type"].items():
        total_ptype = sum(counts.values())
        if total_ptype > 0:
            ok_ptype = counts.get("OK", 0)
            print(f"  {ptype}: OK {ok_ptype:,}/{total_ptype:,} ({ok_ptype / total_ptype * 100:.1f}%)")

    print("\n【重複エピソード】")
    print(f"  重複グループ数: {dup_result['total_duplicate_groups']:,}")
    print(f"  重複エピソード数: {dup_result['total_duplicate_episodes']:,}")

    # 代表例出力
    print("\n" + "-" * 70)
    print("📝 カテゴリ別代表例")
    print("-" * 70)

    for cat in ["META", "FUTURE", "SPECULATION", "TEMPLATE", "EMPTY"]:
        examples = results["categories"][cat]["examples"]
        if examples:
            print(f"\n【{cat}】({results['categories'][cat]['count']:,}件)")
            for i, ex in enumerate(examples[:3], 1):
                print(f"  {i}. {ex['episode_id']} - {ex['person_name']}（{ex['age']}歳）")
                if ex.get("violations"):
                    for v in ex["violations"][:2]:
                        print(f"     → {v[2]}: 「{v[1][:30]}...」")

    # JSONレポート保存
    REPORT_DIR.mkdir(exist_ok=True)
    report_path = REPORT_DIR / f"prohibited_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    # シリアライズ用に変換
    serializable_results = {
        "timestamp": results["timestamp"],
        "total_episodes": results["total_episodes"],
        "dry_run": results["dry_run"],
        "summary": {"ok_count": ok_count, "ng_count": ng_count, "ok_rate": ok_count / total * 100},
        "categories": {k: {"count": v["count"], "examples": v["examples"]} for k, v in results["categories"].items()},
        "by_person_type": {k: dict(v) for k, v in results["by_person_type"].items()},
        "duplicate_info": results["duplicate_info"],
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(serializable_results, f, ensure_ascii=False, indent=2)

    print(f"\n📄 レポート保存: {report_path}")

    # NG一覧CSV出力
    if ng_episodes:
        ng_csv_path = REPORT_DIR / f"prohibited_episodes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        ng_df = pd.DataFrame(ng_episodes)
        ng_df.to_csv(ng_csv_path, index=False, encoding="utf-8-sig")
        print(f"📄 NG一覧CSV保存: {ng_csv_path}")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="禁止パターン検出（全件監査）")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Dry-run mode（デフォルト）")
    parser.add_argument("--execute", action="store_true", help="実行モード（将来の拡張用）")

    args = parser.parse_args()

    run_audit(dry_run=not args.execute)
