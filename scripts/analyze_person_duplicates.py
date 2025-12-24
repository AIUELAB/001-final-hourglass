#!/usr/bin/env python3
"""
同一人物候補クラスターの分析スクリプト
- 入力ファイルをパースしてクラスター化
- マスターCSVと照合してエピソード件数を確認
- 統合計画レポートを生成
"""

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd

# パス設定
MASTER_CSV = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
INPUT_FILE = Path("/Users/admin/Desktop/同一人物.txt")
REPORT_DIR = Path("src/reports")


def parse_input_file(filepath: Path) -> list[dict]:
    """入力ファイルをパースしてクラスターリストを返す"""
    clusters = []
    current_cluster = []

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("-----"):
            if current_cluster:
                clusters.append(current_cluster)
                current_cluster = []
            continue

        # PERSON_ID と名前を抽出（タブ区切り）
        parts = line.split("\t")
        if len(parts) >= 1:
            # IDのみの行
            pid = parts[0].strip()
            if pid.startswith("P") and len(pid) >= 7:
                # 次の行で名前を取得することを期待
                current_cluster.append({"person_id": pid, "person_name": None})
            elif current_cluster and current_cluster[-1]["person_name"] is None:
                # 前のIDに対する名前
                current_cluster[-1]["person_name"] = line.strip()

    if current_cluster:
        clusters.append(current_cluster)

    # 有効なクラスターのみ返す（2つ以上のIDがあるもの）
    valid_clusters = []
    for cluster in clusters:
        # 名前がないエントリを除去
        valid_entries = [e for e in cluster if e["person_name"]]
        if len(valid_entries) >= 2:
            valid_clusters.append(valid_entries)

    return valid_clusters


def analyze_clusters(clusters: list[dict], df: pd.DataFrame) -> list[dict]:
    """クラスターを分析して統計情報を付与"""
    results = []

    # person_id -> 件数のマップ
    person_counts = df.groupby("person_id").size().to_dict()
    # person_id -> person_nameのマップ（CSV内での名前）
    person_names_csv = df.groupby("person_id")["person_name"].first().to_dict()
    # person_id -> fame_scoreのマップ
    if "fame_score" in df.columns:
        person_fame = df.groupby("person_id")["fame_score"].first().to_dict()
    else:
        person_fame = {}

    for idx, cluster in enumerate(clusters, 1):
        cluster_info = {
            "cluster_id": idx,
            "entries": [],
            "total_episodes": 0,
            "analysis": {},
        }

        for entry in cluster:
            pid = entry["person_id"]
            name_input = entry["person_name"]
            name_csv = person_names_csv.get(pid, "（CSV未登録）")
            episode_count = person_counts.get(pid, 0)
            fame = person_fame.get(pid, 0)

            cluster_info["entries"].append(
                {
                    "person_id": pid,
                    "name_input": name_input,
                    "name_csv": name_csv,
                    "episode_count": episode_count,
                    "fame_score": fame,
                    "exists_in_csv": pid in person_counts,
                }
            )
            cluster_info["total_episodes"] += episode_count

        # 分析：最も件数が多いIDを「正」候補に
        if cluster_info["entries"]:
            sorted_entries = sorted(
                cluster_info["entries"], key=lambda x: (x["episode_count"], x["fame_score"]), reverse=True
            )
            primary = sorted_entries[0]
            cluster_info["analysis"] = {
                "recommended_primary_id": primary["person_id"],
                "recommended_name": primary["name_csv"] if primary["exists_in_csv"] else primary["name_input"],
                "ids_to_merge": [e["person_id"] for e in sorted_entries[1:]],
                "merge_episode_count": sum(e["episode_count"] for e in sorted_entries[1:]),
            }

        results.append(cluster_info)

    return results


def categorize_clusters(results: list[dict]) -> dict:
    """クラスターをカテゴリ別に分類"""
    categories = {
        "high_priority": [],  # 両方ともCSVに存在し、統合が必要
        "single_exists": [],  # 片方のみCSV存在（削除済み等）
        "none_exists": [],  # どちらもCSVに存在しない
        "exception_candidates": [],  # 例外候補（芸名/本名分離など）
    }

    # 例外パターン（芸名/本名で分離維持すべきケース）
    exception_patterns = [
        ("北野武", "ビートたけし"),
        ("森田一義", "タモリ"),
        ("千原浩史", "千原ジュニア"),
    ]

    for result in results:
        entries = result["entries"]
        exists_count = sum(1 for e in entries if e["exists_in_csv"])

        # 例外チェック
        names = {e["name_input"] for e in entries}
        is_exception = False
        for name1, name2 in exception_patterns:
            if name1 in names and name2 in names:
                is_exception = True
                break

        if is_exception:
            categories["exception_candidates"].append(result)
        elif exists_count == 0:
            categories["none_exists"].append(result)
        elif exists_count == 1:
            categories["single_exists"].append(result)
        else:
            categories["high_priority"].append(result)

    return categories


def generate_report(results: list[dict], categories: dict) -> str:
    """レポートを生成"""
    report = []
    report.append("=" * 70)
    report.append("PERSON ID 重複統合 ドライラン分析レポート")
    report.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 70)
    report.append("")

    # サマリー
    report.append("## サマリー")
    report.append(f"- 総クラスター数: {len(results)}")
    report.append(f"- 高優先度（両方存在）: {len(categories['high_priority'])} クラスター")
    report.append(f"- 片方のみ存在: {len(categories['single_exists'])} クラスター")
    report.append(f"- どちらも不在: {len(categories['none_exists'])} クラスター")
    report.append(f"- 例外候補（分離維持）: {len(categories['exception_candidates'])} クラスター")
    report.append("")

    # 影響エピソード数
    total_merge_episodes = sum(r["analysis"].get("merge_episode_count", 0) for r in categories["high_priority"])
    report.append(f"- 統合対象エピソード数（高優先度のみ）: {total_merge_episodes} 件")
    report.append("")

    # 高優先度クラスターの詳細
    report.append("=" * 70)
    report.append("## 高優先度クラスター（統合必要）")
    report.append("=" * 70)

    for r in categories["high_priority"][:50]:  # 上位50件
        report.append("")
        report.append(f"### クラスター #{r['cluster_id']}")
        for e in r["entries"]:
            status = "✓" if e["exists_in_csv"] else "✗"
            report.append(
                f"  {status} {e['person_id']} | {e['name_input']} | "
                f"エピソード: {e['episode_count']}件 | fame: {e['fame_score']}"
            )
        analysis = r["analysis"]
        report.append(f"  → 推奨正ID: {analysis['recommended_primary_id']}")
        report.append(f"  → 推奨名: {analysis['recommended_name']}")
        report.append(f"  → 統合対象: {analysis['ids_to_merge']}")

    # 例外候補
    if categories["exception_candidates"]:
        report.append("")
        report.append("=" * 70)
        report.append("## 例外候補（分離維持検討）")
        report.append("=" * 70)
        for r in categories["exception_candidates"]:
            report.append("")
            report.append(f"### クラスター #{r['cluster_id']}")
            for e in r["entries"]:
                report.append(f"  - {e['person_id']} | {e['name_input']} | エピソード: {e['episode_count']}件")
            report.append("  ⚠️ 芸名/本名の分離維持を検討")

    return "\n".join(report)


def main():
    print("同一人物候補クラスター分析を開始...")

    # 入力ファイル読み込み
    clusters = parse_input_file(INPUT_FILE)
    print(f"入力ファイルから {len(clusters)} クラスターを抽出")

    # マスターCSV読み込み
    df = pd.read_csv(MASTER_CSV, low_memory=False)
    print(f"マスターCSV: {len(df)} レコード, {df['person_id'].nunique()} 人物")

    # 分析実行
    results = analyze_clusters(clusters, df)
    categories = categorize_clusters(results)

    # レポート生成
    report = generate_report(results, categories)

    # レポート保存
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"person_duplicate_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    # JSON形式でも保存（後続処理用）
    json_path = REPORT_DIR / "person_duplicate_clusters.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "generated_at": datetime.now().isoformat(),
                "summary": {
                    "total_clusters": len(results),
                    "high_priority": len(categories["high_priority"]),
                    "single_exists": len(categories["single_exists"]),
                    "none_exists": len(categories["none_exists"]),
                    "exception_candidates": len(categories["exception_candidates"]),
                },
                "clusters": results,
                "categories": {k: [c["cluster_id"] for c in v] for k, v in categories.items()},
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\nレポート保存: {report_path}")
    print(f"JSON保存: {json_path}")

    # 要約出力
    print("\n" + "=" * 50)
    print("【分析結果サマリー】")
    print(f"総クラスター: {len(results)}")
    print(f"高優先度: {len(categories['high_priority'])} 件")
    print(f"例外候補: {len(categories['exception_candidates'])} 件")
    print("=" * 50)


if __name__ == "__main__":
    main()
