#!/usr/bin/env python3
"""
Wikidataマッピングのバリデーションスクリプト。

異常なマッピングを検出:
1. 架空キャラクターで高sitelinks（>150）
2. Q番号が非常に小さい（<1000）
3. 短名前（≤3文字）で高スコア（>500）
"""

import csv
import sqlite3
from dataclasses import dataclass
from pathlib import Path

DB_PATH = Path("data/cache/fame_score.db")
CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")

# 閾値
FICTIONAL_HIGH_SITELINKS = 100
BASIC_CONCEPT_QID = 1000
SHORT_NAME_LENGTH = 3
SHORT_NAME_HIGH_SCORE = 400


@dataclass
class SuspiciousEntry:
    """疑わしいエントリ"""

    person_id: str
    person_name: str
    person_type: str
    wikidata_id: str
    sitelinks: int
    fame_score: float
    issue_type: str
    severity: str  # "high", "medium", "low"


def load_csv_data() -> dict:
    """CSVから人物データを読み込み"""
    persons = {}
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row.get("person_id", "")
            if pid and pid not in persons:
                persons[pid] = {
                    "person_id": pid,
                    "person_name": row.get("person_name", ""),
                    "person_type": row.get("person_type", "REAL"),
                    "work_title": row.get("work_title", ""),
                    "category": row.get("category", ""),
                }
    return persons


def load_cache_data() -> dict:
    """キャッシュDBからデータを読み込み"""
    cache = {}
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        """
        SELECT person_id, person_name, wikidata_id, sitelinks, fame_score_v3
        FROM fame_cache
        WHERE wikidata_id IS NOT NULL
        """
    )
    for row in cursor:
        cache[row[0]] = {
            "person_id": row[0],
            "person_name": row[1],
            "wikidata_id": row[2],
            "sitelinks": row[3] or 0,
            "fame_score_v3": row[4] or 0,
        }
    conn.close()
    return cache


def get_qid_number(wikidata_id: str) -> int:
    """QIDから数値部分を取得"""
    try:
        return int(wikidata_id[1:])
    except (ValueError, IndexError):
        return 999999


def detect_suspicious_mappings() -> list[SuspiciousEntry]:
    """異常なWikidataマッピングを検出"""
    suspicious = []

    csv_data = load_csv_data()
    cache_data = load_cache_data()

    for pid, cache in cache_data.items():
        csv_info = csv_data.get(pid, {})
        person_type = csv_info.get("person_type", "REAL")
        person_name = cache["person_name"]
        wikidata_id = cache["wikidata_id"]
        sitelinks = cache["sitelinks"]
        fame_score = cache["fame_score_v3"]

        # パターン1: 架空キャラクターで高sitelinks
        if person_type == "FICTIONAL" and sitelinks > FICTIONAL_HIGH_SITELINKS:
            suspicious.append(
                SuspiciousEntry(
                    person_id=pid,
                    person_name=person_name,
                    person_type=person_type,
                    wikidata_id=wikidata_id,
                    sitelinks=sitelinks,
                    fame_score=fame_score,
                    issue_type=f"高sitelinks（{sitelinks}）架空キャラ",
                    severity="high",
                )
            )

        # パターン2: Q番号が非常に小さい
        qnum = get_qid_number(wikidata_id)
        if qnum < BASIC_CONCEPT_QID:
            suspicious.append(
                SuspiciousEntry(
                    person_id=pid,
                    person_name=person_name,
                    person_type=person_type,
                    wikidata_id=wikidata_id,
                    sitelinks=sitelinks,
                    fame_score=fame_score,
                    issue_type=f"基本概念QID（{wikidata_id}）",
                    severity="high" if qnum < 500 else "medium",
                )
            )

        # パターン3: 短い名前で高スコア
        name_len = len(person_name.strip())
        if name_len <= SHORT_NAME_LENGTH and fame_score > SHORT_NAME_HIGH_SCORE:
            suspicious.append(
                SuspiciousEntry(
                    person_id=pid,
                    person_name=person_name,
                    person_type=person_type,
                    wikidata_id=wikidata_id,
                    sitelinks=sitelinks,
                    fame_score=fame_score,
                    issue_type=f"短名前（{name_len}文字）高スコア",
                    severity="medium",
                )
            )

    return suspicious


def main():
    print("=== Wikidataマッピング バリデーション ===\n")

    suspicious = detect_suspicious_mappings()

    if not suspicious:
        print("✓ 異常なマッピングは検出されませんでした")
        return

    # 重複排除（同一person_idで複数の問題がある場合）
    unique_entries = {}
    for entry in suspicious:
        key = entry.person_id
        if key not in unique_entries:
            unique_entries[key] = entry
        else:
            # より重要な問題を優先
            if entry.severity == "high" and unique_entries[key].severity != "high":
                unique_entries[key] = entry

    suspicious = list(unique_entries.values())

    # 重要度でソート
    severity_order = {"high": 0, "medium": 1, "low": 2}
    suspicious.sort(key=lambda x: (severity_order.get(x.severity, 3), -x.fame_score))

    print(f"⚠️ {len(suspicious)}件の疑わしいマッピングを検出\n")

    # 重要度別に表示
    high_count = sum(1 for s in suspicious if s.severity == "high")
    medium_count = sum(1 for s in suspicious if s.severity == "medium")

    if high_count > 0:
        print(f"=== 高優先度 ({high_count}件) ===")
        for entry in suspicious:
            if entry.severity == "high":
                print(f"  [{entry.person_id}] {entry.person_name} ({entry.person_type})")
                print(f"    wikidata: {entry.wikidata_id}, sitelinks: {entry.sitelinks}, score: {entry.fame_score:.1f}")
                print(f"    問題: {entry.issue_type}")
                print()

    if medium_count > 0:
        print(f"=== 中優先度 ({medium_count}件) ===")
        for entry in suspicious:
            if entry.severity == "medium":
                print(f"  [{entry.person_id}] {entry.person_name}: {entry.issue_type}")

    # サマリー
    print("\n=== サマリー ===")
    print(f"高優先度: {high_count}件")
    print(f"中優先度: {medium_count}件")

    if high_count > 0:
        print("\n⚠️ 高優先度の問題を確認してください")
    else:
        print("\n✓ 高優先度の問題はありません")


if __name__ == "__main__":
    main()
