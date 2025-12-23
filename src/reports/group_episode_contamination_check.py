#!/usr/bin/env python3
"""
グループエピソード混入検出スクリプト

人物エピソードにグループ（団体/ユニット/組織/作品名など）が
混入していないかを包括的に検出する。

検出パターン:
A: is_group_member=True なのに group_name が空（または逆）
B: 同一person_id で group_name/is_group_member が不整合
C: person_name が団体パターン（末尾: グループ/劇団/楽団/会社等）
D: person_name に「・」区切りで組織・個人が混在
E: person_name が作品名/道具名（ブラックリスト照合）
F: GROUP_ENTITIES に登録されている名前が person_name に存在

Usage:
    python src/reports/group_episode_contamination_check.py
"""

import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

# プロジェクトルート
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.group_master import GROUP_ENTITIES, GROUP_MEMBER_MAP

# 団体を示す末尾パターン（日本語）
ORG_SUFFIXES_JA = (
    "グループ",
    "劇団",
    "合唱団",
    "楽団",
    "オーケストラ",
    "吹奏楽団",
    "会社",
    "株式会社",
    "有限会社",
    "合同会社",
    "スタジオ",
    "プロダクション",
    "チーム",
    "委員会",
    "実行委員会",
    "学園",
    "大学",
    "高校",
    "中学",
    "小学校",
    "協会",
    "財団",
    "法人",
    "機構",
    "研究所",
    "研究室",
    "ラボ",
    "クラブ",
    "サークル",
    "同好会",
    "連盟",
    "連合",
    "組合",
    "事務所",
    "工房",
    "アトリエ",
    "ファクトリー",
    "バンド",
    "ユニット",
    "デュオ",
    "トリオ",
    "カルテット",
    "座",
    "一座",
    "劇場",
    "シアター",
)

# 団体を示す末尾パターン（英語）
ORG_SUFFIXES_EN = (
    "Inc.",
    "Inc",
    "Corp.",
    "Corp",
    "Co.",
    "Co",
    "Ltd.",
    "Ltd",
    "LLC",
    "LLP",
    "Group",
    "Team",
    "Studio",
    "Studios",
    "Production",
    "Productions",
    "Records",
    "Entertainment",
    "Foundation",
    "Association",
    "Institute",
    "Laboratory",
    "Lab",
    "Club",
    "Orchestra",
    "Band",
    "Ensemble",
    "University",
    "College",
    "School",
    "Academy",
)

# 除外パターン（個人名に見える末尾）
EXCLUDE_PERSON_SUFFIXES = ("太郎", "次郎", "三郎", "一郎", "子", "美", "香", "恵")


def _match_org_suffix(name: str) -> str | None:
    """団体サフィックスにマッチするか判定"""
    for suffix in ORG_SUFFIXES_JA:
        if name.endswith(suffix):
            return suffix
    for suffix in ORG_SUFFIXES_EN:
        if name.endswith(suffix) or name.endswith(f" {suffix}"):
            return suffix
    return None


def load_csv() -> pd.DataFrame:
    """マスターCSV読み込み"""
    csv_path = project_root / "preserved/data/MASTER_EPISODES_CURRENT.csv"
    return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)


def check_pattern_a(df: pd.DataFrame) -> list[dict[str, Any]]:
    """A: is_group_member=True なのに group_name が空（または逆）"""
    issues: list[dict[str, Any]] = []

    # ベクトル化: is_member フラグ
    is_member_col = df["is_group_member"].fillna("").astype(str).str.upper() == "TRUE"

    # ベクトル化: has_group フラグ
    group_name_col = df["group_name"].fillna("").astype(str).str.strip()
    has_group_col = (group_name_col != "") & (group_name_col.str.lower() != "nan")

    # A1: is_member=True かつ has_group=False
    mask_a1 = is_member_col & ~has_group_col
    if mask_a1.any():
        a1_rows = df.loc[mask_a1, ["episode_id", "person_id", "person_name"]].copy()
        a1_rows["is_group_member"] = True
        a1_rows["group_name"] = group_name_col[mask_a1]
        a1_rows["pattern"] = "A1"
        a1_rows["description"] = "is_group_member=True but group_name is empty"
        issues.extend(a1_rows.to_dict("records"))

    # A2: has_group=True かつ is_member=False
    mask_a2 = has_group_col & ~is_member_col
    if mask_a2.any():
        a2_rows = df.loc[mask_a2, ["episode_id", "person_id", "person_name"]].copy()
        a2_rows["is_group_member"] = False
        a2_rows["group_name"] = group_name_col[mask_a2]
        a2_rows["pattern"] = "A2"
        a2_rows["description"] = "group_name exists but is_group_member=False"
        issues.extend(a2_rows.to_dict("records"))

    return issues


def check_pattern_b(df: pd.DataFrame) -> list[dict[str, Any]]:
    """B: 同一person_id で group_name/is_group_member が不整合"""
    issues: list[dict[str, Any]] = []

    # 前処理: 有効な person_id のみ抽出
    df_valid = df[df["person_id"].notna() & (df["person_id"].astype(str) != "nan")].copy()
    if df_valid.empty:
        return issues

    # ベクトル化: 列の正規化
    df_valid["_person_id"] = df_valid["person_id"].astype(str)
    df_valid["_group_name"] = df_valid["group_name"].fillna("").astype(str).replace("", "(empty)")
    df_valid["_is_member"] = df_valid["is_group_member"].fillna("").astype(str).str.upper() == "TRUE"

    # groupby で集約
    grouped = df_valid.groupby("_person_id").agg(
        person_name=("person_name", "first"),
        group_names=("_group_name", lambda x: set(x)),
        is_members=("_is_member", lambda x: set(x.astype(str))),
        episode_count=("episode_id", "count"),
    )

    # 不整合検出: group_names または is_members に複数の値がある
    inconsistent = grouped[(grouped["group_names"].apply(len) > 1) | (grouped["is_members"].apply(len) > 1)]

    for person_id, row in inconsistent.iterrows():
        issues.append(
            {
                "pattern": "B",
                "description": "Inconsistent group_name/is_group_member for same person_id",
                "person_id": person_id,
                "person_name": row["person_name"],
                "group_names": list(row["group_names"]),
                "is_members": list(row["is_members"]),
                "episode_count": row["episode_count"],
            }
        )

    return issues


def check_pattern_c(df: pd.DataFrame) -> list:
    """C: person_name が団体パターン（末尾: グループ/劇団/楽団/会社等）"""
    issues = []

    # ユニーク名とエピソード数を事前計算
    name_counts = df["person_name"].value_counts()
    unique_names = df.drop_duplicates(subset=["person_name"])[["person_name", "person_id", "episode_id"]]

    for _, row in unique_names.iterrows():
        person_name = str(row["person_name"]) if pd.notna(row["person_name"]) else ""
        if not person_name:
            continue

        matched_suffix = _match_org_suffix(person_name)
        if not matched_suffix:
            continue

        # 除外パターン（個人名に見える）
        if any(person_name.endswith(ep) for ep in EXCLUDE_PERSON_SUFFIXES):
            continue

        issues.append(
            {
                "pattern": "C",
                "description": f"Organization suffix detected: {matched_suffix}",
                "person_name": person_name,
                "person_id": row["person_id"],
                "episode_id": row["episode_id"],
                "matched_suffix": matched_suffix,
                "episode_count": name_counts.get(person_name, 0),
            }
        )

    return issues


def check_pattern_d(df: pd.DataFrame) -> list:
    """D: person_name に「・」区切りで組織・個人が混在"""
    issues = []

    # 組織を示すキーワード
    org_keywords = [
        "スタジオ",
        "STUDIO",
        "Studio",
        "プロダクション",
        "Production",
        "レコード",
        "Records",
        "エンターテイメント",
        "Entertainment",
        "ミュージック",
        "Music",
        "アニメーション",
        "Animation",
        "ピクチャーズ",
        "Pictures",
        "フィルム",
        "Films",
        "Film",
        "ゲームス",
        "Games",
        "ソフト",
        "Soft",
        "出版",
        "Publishing",
        "放送",
        "Broadcasting",
        "TV",
        "テレビ",
    ]

    separators = ["・", "／", "/", "｜", "|"]

    # ユニーク名で処理（drop_duplicates使用）
    unique_names = df.drop_duplicates(subset=["person_name"])[["person_name", "person_id", "episode_id"]]

    for _, row in unique_names.iterrows():
        person_name = str(row["person_name"]) if pd.notna(row["person_name"]) else ""
        if not person_name:
            continue

        for sep in separators:
            if sep in person_name:
                parts = person_name.split(sep)
                matched = False
                for part in parts:
                    for kw in org_keywords:
                        if kw.lower() in part.lower():
                            issues.append(
                                {
                                    "pattern": "D",
                                    "description": f"Organization+Person mixed: contains '{kw}'",
                                    "person_name": person_name,
                                    "person_id": row["person_id"],
                                    "episode_id": row["episode_id"],
                                    "separator": sep,
                                    "matched_keyword": kw,
                                }
                            )
                            matched = True
                            break
                    if matched:
                        break
                if matched:
                    break

    return issues


def check_pattern_e(df: pd.DataFrame) -> list:
    """E: person_name が作品名/道具名（ブラックリスト照合）"""
    issues = []

    # 道具/作品名パターン
    item_patterns = [
        r".*ギプス$",
        r".*マシン$",
        r".*装置$",
        r".*アイテム$",
        r".*グッズ$",
        r".*ツール$",
        r".*ロボット$",
        r".*メカ$",
        r".*システム$",
        r".*プログラム$",
        r".*アプリ$",
        r".*ソフトウェア$",
    ]

    # 作品名パターン
    work_patterns = [
        r"^「.+」$",  # カギ括弧で囲まれた作品名
        r"^『.+』$",  # 二重カギ括弧
        r".*（アニメ）$",
        r".*（映画）$",
        r".*（ドラマ）$",
        r".*（漫画）$",
        r".*（小説）$",
        r".*（ゲーム）$",
    ]

    all_patterns = item_patterns + work_patterns

    # ユニーク名で処理（drop_duplicates使用）
    unique_names = df.drop_duplicates(subset=["person_name"])[["person_name", "person_id", "episode_id"]]

    for _, row in unique_names.iterrows():
        person_name = str(row["person_name"]) if pd.notna(row["person_name"]) else ""
        if not person_name:
            continue

        for pattern in all_patterns:
            if re.match(pattern, person_name):
                issues.append(
                    {
                        "pattern": "E",
                        "description": f"Item/Work name pattern: {pattern}",
                        "person_name": person_name,
                        "person_id": row["person_id"],
                        "episode_id": row["episode_id"],
                        "matched_pattern": pattern,
                    }
                )
                break

    return issues


def check_pattern_f(df: pd.DataFrame) -> list:
    """F: GROUP_ENTITIES に登録されている名前が person_name に存在"""
    issues = []

    unique_names = df["person_name"].dropna().unique()

    for name in unique_names:
        if name in GROUP_ENTITIES:
            sample = df[df["person_name"] == name].iloc[0]
            issues.append(
                {
                    "pattern": "F",
                    "description": "Name exists in GROUP_ENTITIES (should not be person)",
                    "person_name": name,
                    "person_id": sample.get("person_id", ""),
                    "episode_id": sample.get("episode_id", ""),
                    "episode_count": len(df[df["person_name"] == name]),
                }
            )

    return issues


def check_pattern_g(df: pd.DataFrame) -> list:
    """G: GROUP_MEMBER_MAPに登録されているがis_group_member=Falseの人物"""
    issues = []

    unique_names = df["person_name"].dropna().unique()

    for name in unique_names:
        if name in GROUP_MEMBER_MAP:
            expected_group = GROUP_MEMBER_MAP[name]
            rows = df[df["person_name"] == name]

            for _, row in rows.iterrows():
                is_member = str(row.get("is_group_member", "")).upper() == "TRUE"
                group_name = str(row.get("group_name", "")) if pd.notna(row.get("group_name")) else ""

                if not is_member or group_name != expected_group:
                    issues.append(
                        {
                            "pattern": "G",
                            "description": f"GROUP_MEMBER_MAP mismatch: expected group='{expected_group}'",
                            "person_name": name,
                            "person_id": row.get("person_id", ""),
                            "episode_id": row.get("episode_id", ""),
                            "expected_group": expected_group,
                            "actual_group": group_name,
                            "is_group_member": is_member,
                        }
                    )
                    break  # 1件だけ報告

    return issues


def _run_pattern_check(
    df: pd.DataFrame,
    pattern_id: str,
    pattern_name: str,
    check_func,
    sample_formatter,
) -> dict:
    """パターンチェックを実行し結果を返す"""
    issues = check_func(df)
    print(f"\n[{pattern_id}] {pattern_name}: {len(issues)}件")
    for issue in issues[:3]:
        print(f"    - {sample_formatter(issue)}")
    return {
        "name": pattern_name,
        "count": len(issues),
        "samples": issues[:10],
    }


def _print_summary(results: dict) -> None:
    """サマリーを出力"""
    print("\n" + "=" * 70)
    print("サマリー")
    print("=" * 70)
    for pattern, data in results["patterns"].items():
        status = "✅" if data["count"] == 0 else "⚠️"
        print(f"  {status} [{pattern}] {data['name']}: {data['count']}件")


def _save_report(results: dict) -> Path:
    """レポートをJSONファイルに保存"""
    report_path = project_root / "reports" / f"group_contamination_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n📄 レポート保存: {report_path}")
    return report_path


def main():
    print("=" * 70)
    print("グループエピソード混入検出")
    print("=" * 70)
    print(f"実行時刻: {datetime.now().isoformat()}")

    # CSV読み込み
    df = load_csv()
    print(f"\n総レコード数: {len(df):,}")
    print(f"ユニーク人物数: {df['person_name'].nunique():,}")

    # 結果初期化
    results = {
        "timestamp": datetime.now().isoformat(),
        "total_records": len(df),
        "unique_persons": df["person_name"].nunique(),
        "patterns": {},
    }

    print("\n" + "-" * 70)
    print("検出実行中...")
    print("-" * 70)

    # パターン定義 (id, name, check_func, formatter)
    pattern_checks = [
        (
            "A",
            "is_group_member/group_name 不整合",
            check_pattern_a,
            lambda i: f"{i['person_name']} ({i['pattern']}): {i['description']}",
        ),
        ("B", "同一person_idで不整合", check_pattern_b, lambda i: f"{i['person_name']} (groups={i['group_names']})"),
        ("C", "団体名パターン検出", check_pattern_c, lambda i: f"{i['person_name']} (suffix={i['matched_suffix']})"),
        ("D", "組織・個人混在", check_pattern_d, lambda i: f"{i['person_name']} (keyword={i['matched_keyword']})"),
        ("E", "作品名/道具名パターン", check_pattern_e, lambda i: f"{i['person_name']}"),
        ("F", "GROUP_ENTITIES混入", check_pattern_f, lambda i: f"{i['person_name']} (episodes={i['episode_count']})"),
        (
            "G",
            "GROUP_MEMBER_MAP不整合",
            check_pattern_g,
            lambda i: f"{i['person_name']} (expected={i['expected_group']})",
        ),
    ]

    for pattern_id, pattern_name, check_func, formatter in pattern_checks:
        results["patterns"][pattern_id] = _run_pattern_check(df, pattern_id, pattern_name, check_func, formatter)

    _print_summary(results)
    _save_report(results)

    return results


if __name__ == "__main__":
    main()
