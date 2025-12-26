#!/usr/bin/env python3
"""
エンティティ誤採用の総合検知スクリプト。

検知ルール:
1. 基本概念QID（Q番号 < 1000）
2. 架空キャラで高sitelinks
3. 短名前で高スコア
4. Google検索異常値
5. シグナル間不整合
6. PV/sitelinks比率異常
"""

import csv
import sqlite3
from dataclasses import dataclass
from pathlib import Path

DB_PATH = Path("data/cache/fame_score.db")
CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")

# 一般名詞・地名・宗教用語（曖昧性の高い名前）
AMBIGUOUS_NAMES = {
    # 宗教
    "マドンナ",
    "ジーザス",
    "モーゼ",
    "ブッダ",
    "クリシュナ",
    # 地名
    "ワシントン",
    "リンカーン",
    "ジャクソン",
    "マディソン",
    "モンロー",
    # 一般名詞（英語）
    "ONE",
    "ken",
    "MAX",
    "JOY",
    "LOVE",
    "ZERO",
    "ACE",
    # 一般名詞（日本語）
    "愛",
    "光",
    "翼",
    "海",
    "空",
    "風",
    "雪",
    "桜",
    "蓮",
    # 神話
    "アポロ",
    "アテナ",
    "ゼウス",
    "ヘラ",
    "アレス",
    "ポセイドン",
}

# 検証済みエンティティ（person_id: wikidata_id）
# 曖昧名前でも正しいマッピングであることが確認済み
VERIFIED_ENTITIES = {
    "P64A6504": "Q1744",  # マドンナ (歌手)
    "PB883441": "Q34201",  # ゼウス (ギリシア神話)
    "PF6B0D8E": "Q37122",  # アテナ (ギリシア神話)
    "PF632FA6": "Q1361450",  # ken (L'Arc〜en〜Ciel)
    "PBC21E64": "Q11237288",  # ONE (漫画家)
}


@dataclass
class DetectionResult:
    """検知結果"""

    person_id: str
    person_name: str
    person_type: str
    wikidata_id: str
    sitelinks: int
    multi_lang_pv: int
    google_hits: int
    fame_score: float
    issues: list
    severity: str  # critical, high, medium, low
    recommended_action: str


def get_qid_number(wikidata_id: str) -> int:
    """QIDから数値部分を取得"""
    if not wikidata_id:
        return 999999
    try:
        return int(wikidata_id[1:])
    except (ValueError, IndexError):
        return 999999


def load_data():
    """キャッシュDBとCSVからデータを読み込み"""
    # キャッシュDB
    cache = {}
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        """
        SELECT person_id, person_name, wikidata_id, sitelinks, multi_lang_pv,
               inlinks, google_hits, fame_score_v3
        FROM fame_cache
        """
    )
    for row in cursor:
        cache[row[0]] = {
            "person_id": row[0],
            "person_name": row[1],
            "wikidata_id": row[2],
            "sitelinks": row[3] or 0,
            "multi_lang_pv": row[4] or 0,
            "inlinks": row[5] or 0,
            "google_hits": row[6],
            "fame_score_v3": row[7] or 0,
        }
    conn.close()

    # CSV（person_type取得）
    csv_data = {}
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row.get("person_id", "")
            if pid and pid not in csv_data:
                csv_data[pid] = {
                    "person_type": row.get("person_type", "REAL"),
                    "category": row.get("category", ""),
                    "work_title": row.get("work_title", ""),
                }

    return cache, csv_data


def detect_issues(cache_entry: dict, csv_entry: dict) -> DetectionResult:
    """エントリの問題を検知"""
    issues = []
    person_id = cache_entry["person_id"]
    person_name = cache_entry["person_name"]
    wikidata_id = cache_entry["wikidata_id"]
    sitelinks = cache_entry["sitelinks"]
    multi_lang_pv = cache_entry["multi_lang_pv"]
    google_hits = cache_entry["google_hits"]
    fame_score = cache_entry["fame_score_v3"]
    person_type = csv_entry.get("person_type", "REAL")

    # Rule 1: 基本概念QID（人物以外のみフラグ）
    # 高sitelinks + REAL = 正しいマッピングの可能性高（有名人は早期登録でQ番号小）
    qnum = get_qid_number(wikidata_id)
    is_likely_correct_mapping = (
        person_type == "REAL" and sitelinks >= 150  # 有名人は多言語展開
    )

    if wikidata_id and qnum < 100 and not is_likely_correct_mapping:
        # Q < 100 は基本概念の可能性が高い（Q5=human, Q6=country等）
        issues.append(f"基本概念QID({wikidata_id}): Q番号が非常に小さい")
    elif wikidata_id and qnum < 500 and not is_likely_correct_mapping:
        # Q < 500 でsitelinkも低い場合のみ疑わしい
        if sitelinks < 50:
            issues.append(f"基本概念QID疑い({wikidata_id}): 要確認")

    # Rule 2: 架空キャラで高sitelinks
    # 有名キャラ（ミッキーマウス等）は高sitelinkも正常なので閾値を上げる
    if person_type == "FICTIONAL":
        if sitelinks > 200:
            issues.append(f"架空キャラ高sitelinks({sitelinks}): 要確認")
        elif sitelinks > 150:
            issues.append(f"架空キャラ中sitelinks({sitelinks}): 有名キャラか確認")

    # Rule 3: 短名前で高スコア（無効化 - 誤検知100%のため）
    # 日本語では有名人を短い名前で呼ぶことが多く、実用的な価値がない
    # 例: 釈迦、孔子、ゴッホ、バッハ等は全て正しいマッピング
    # name_len = len(person_name.strip())
    # if name_len <= 2 and fame_score > 400:
    #     issues.append(f"短名前({name_len}文字)高スコア({fame_score:.0f})")
    # elif name_len <= 3 and fame_score > 500:
    #     issues.append(f"短名前({name_len}文字)高スコア({fame_score:.0f})")

    # Rule 4: Google検索異常値
    if google_hits:
        if google_hits > 1_000_000_000:  # 10億以上
            issues.append(f"Google検索異常({google_hits:,}): 一般名詞混入の可能性大")
        elif google_hits > 100_000_000:  # 1億以上
            issues.append(f"Google検索高値({google_hits:,}): 曖昧性の可能性")
        elif google_hits > 20_000_000 and sitelinks < 100:
            issues.append(f"Google検索不整合: hits={google_hits:,} vs sitelinks={sitelinks}")

    # Rule 5: 曖昧な名前（検証済みエンティティは除外）
    if person_name in AMBIGUOUS_NAMES:
        verified_qid = VERIFIED_ENTITIES.get(person_id)
        if not (verified_qid and verified_qid == wikidata_id):
            issues.append("曖昧名前: 一般名詞/地名/宗教用語と同名")

    # Rule 6: PV/sitelinks比率異常（閾値を上げて誤検知を減らす）
    # 日本人有名人は日本語PVが高いがsitelinksが少ないことがある（正常）
    if sitelinks > 0 and sitelinks < 30:  # sitelinks少ない場合のみチェック
        pv_per_sl = multi_lang_pv / sitelinks
        if pv_per_sl > 200000:  # 閾値を引き上げ
            issues.append(f"PV/sitelinks比率高({pv_per_sl:.0f}): 要確認")

    # Rule 7: Wikidataなしで高スコア
    if not wikidata_id and fame_score > 300:
        issues.append(f"Wikidataなし高スコア({fame_score:.0f})")

    # 重要度判定
    if any("基本概念QID(" in i for i in issues) or any("異常" in i for i in issues):
        severity = "critical"
    elif any("高sitelinks" in i for i in issues) or any("一般名詞" in i for i in issues):
        severity = "high"
    elif issues:
        severity = "medium"
    else:
        severity = "none"

    # 推奨アクション
    if severity == "critical":
        action = "wikidata_id/google_hitsをNULL化してスコア再計算"
    elif severity == "high":
        action = "Wikidata P31を確認し、誤りなら修正"
    elif severity == "medium":
        action = "手動確認推奨"
    else:
        action = "問題なし"

    return DetectionResult(
        person_id=person_id,
        person_name=person_name,
        person_type=person_type,
        wikidata_id=wikidata_id or "",
        sitelinks=sitelinks,
        multi_lang_pv=multi_lang_pv,
        google_hits=google_hits or 0,
        fame_score=fame_score,
        issues=issues,
        severity=severity,
        recommended_action=action,
    )


def main():
    print("=== エンティティ誤採用 総合検知 ===\n")

    cache, csv_data = load_data()
    print(f"キャッシュエントリ数: {len(cache)}")

    results = []
    for pid, cache_entry in cache.items():
        csv_entry = csv_data.get(pid, {})
        result = detect_issues(cache_entry, csv_entry)
        if result.issues:
            results.append(result)

    # 重要度でソート
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "none": 4}
    results.sort(key=lambda r: (severity_order.get(r.severity, 4), -r.fame_score))

    # 統計
    critical_count = sum(1 for r in results if r.severity == "critical")
    high_count = sum(1 for r in results if r.severity == "high")
    medium_count = sum(1 for r in results if r.severity == "medium")

    print(f"\n検知結果: {len(results)}件の問題を発見")
    print(f"  - Critical: {critical_count}件")
    print(f"  - High: {high_count}件")
    print(f"  - Medium: {medium_count}件")

    # Critical表示
    if critical_count > 0:
        print(f"\n{'=' * 60}")
        print(f"=== CRITICAL ({critical_count}件) ===")
        print(f"{'=' * 60}")
        for r in results:
            if r.severity == "critical":
                print(f"\n[{r.person_id}] {r.person_name} ({r.person_type})")
                print(f"  wikidata: {r.wikidata_id}, sitelinks: {r.sitelinks}")
                print(f"  google_hits: {r.google_hits:,}, score: {r.fame_score:.1f}")
                for issue in r.issues:
                    print(f"  ⚠️ {issue}")
                print(f"  → {r.recommended_action}")

    # High表示
    if high_count > 0:
        print(f"\n{'=' * 60}")
        print(f"=== HIGH ({high_count}件) ===")
        print(f"{'=' * 60}")
        for r in results:
            if r.severity == "high":
                print(f"\n[{r.person_id}] {r.person_name} ({r.person_type})")
                print(f"  wikidata: {r.wikidata_id}, score: {r.fame_score:.1f}")
                for issue in r.issues:
                    print(f"  ⚠️ {issue}")

    # Medium（概要のみ）
    if medium_count > 0:
        print(f"\n{'=' * 60}")
        print(f"=== MEDIUM ({medium_count}件) - 概要 ===")
        print(f"{'=' * 60}")
        for r in results[:30]:  # 最初の30件のみ
            if r.severity == "medium":
                print(f"  [{r.person_id}] {r.person_name}: {r.issues[0]}")

    # レポート保存
    report_path = Path("src/reports/entity_mismatch_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("エンティティ誤採用検知レポート\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"検知結果: {len(results)}件\n")
        f.write(f"  - Critical: {critical_count}件\n")
        f.write(f"  - High: {high_count}件\n")
        f.write(f"  - Medium: {medium_count}件\n\n")

        for r in results:
            f.write(f"[{r.severity.upper()}] {r.person_id} | {r.person_name}\n")
            f.write(f"  type: {r.person_type}, wikidata: {r.wikidata_id}\n")
            f.write(f"  sitelinks: {r.sitelinks}, pv: {r.multi_lang_pv}, score: {r.fame_score:.1f}\n")
            for issue in r.issues:
                f.write(f"  - {issue}\n")
            f.write(f"  Action: {r.recommended_action}\n\n")

    print(f"\n✓ 詳細レポート保存: {report_path}")


if __name__ == "__main__":
    main()
