#!/usr/bin/env python3
"""
LLM創作禁止パターン違反エピソードの検出・削除スクリプト

架空キャラクター(FICTIONAL)のエピソードから、LLMが創作しがちな
現実世界の要素を含むエピソードを検出し、削除（フラグ付け）する

Usage:
    # ドライラン（対象件数の確認）
    python scripts/fix/fix_llm_pattern_violations.py --dry-run

    # 実行
    python scripts/fix/fix_llm_pattern_violations.py
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ファイルパス
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORTS_DIR = PROJECT_ROOT / "src" / "reports"

# 違反パターン定義
VIOLATION_PATTERNS = {
    "実在テック人物言及": r"スティーブ・ジョブズ|イーロン・マスク|ビル・ゲイツ|マーク・ザッカーバーグ|ジェフ・ベゾス|ティム・クック|サンダー・ピチャイ|ウォーレン・バフェット|スティーブ・ウォズニアック|ラリー・ペイジ|セルゲイ・ブリン",
    "金融活動付与": r"株式投資|資産運用|ファンド運用|配当金|利回り|ポートフォリオ|デイトレード|IPO|上場企業|証券会社|株価|金融市場|ヘッジファンド",
    "引退設定付与": r"退職後|引退後|定年後|第二の人生|セカンドキャリア|老後の|引退した|引退を宣言",
    "現実的売上数字": r"[0-9０-９]+万ドル|[0-9０-９]+億ドル|興行収入|年商[0-9０-９]|売上高[0-9０-９]|ドルの収益|ドルを稼",
    "映画業界役職付与": r"映画監督として|プロデューサーとして活動|ディレクターとして|映画プロデューサー|映画制作会社",
    "エンタメ業界活動": r"芸能事務所|レコード会社|音楽プロデューサー|テレビ局との|メジャーレーベル|レコードレーベル",
    "スタジオ活動": r"スタジオ設立|スタジオを設立|アニメスタジオ|制作スタジオ|レコーディングスタジオ|撮影スタジオ",
}


def detect_violations(text: str) -> list[str]:
    """
    テキストから違反パターンを検出

    Returns:
        検出された違反パターン名のリスト
    """
    if pd.isna(text) or not text:
        return []

    violations = []
    for pattern_name, pattern in VIOLATION_PATTERNS.items():
        if re.search(pattern, str(text), re.IGNORECASE):
            violations.append(pattern_name)
    return violations


def main():
    dry_run = "--dry-run" in sys.argv

    print("=" * 60)
    print("LLM創作禁止パターン違反エピソード検出・削除")
    print("=" * 60)

    if dry_run:
        print("[MODE] ドライラン（実際の更新はスキップ）")
    else:
        print("[MODE] 実行モード")
    print()

    # CSVを読み込む
    print(f"[INFO] CSV読み込み中: {MASTER_CSV}")
    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig", low_memory=False)
    print(f"[INFO] 総エピソード数: {len(df):,}")

    # FICTIONALのみ対象
    fictional_mask = df["person_type"] == "FICTIONAL"
    fictional_count = fictional_mask.sum()
    print(f"[INFO] 架空キャラ数: {fictional_count:,}")
    print()

    # 違反パターン検出
    print("[STEP] 違反パターン検出中...")

    # 各エピソードの違反を検出
    df["_violations"] = df.apply(
        lambda row: detect_violations(row["episode_text"]) if row["person_type"] == "FICTIONAL" else [], axis=1
    )

    # 違反があるエピソードを特定
    df["_has_violation"] = df["_violations"].apply(lambda x: len(x) > 0)
    violation_mask = df["_has_violation"] & fictional_mask

    violation_count = violation_mask.sum()
    print(f"[RESULT] 違反エピソード数: {violation_count:,}")
    print()

    # パターン別の統計
    print("[STATS] パターン別検出件数:")
    pattern_stats = {}
    for pattern_name in VIOLATION_PATTERNS.keys():
        count = df[fictional_mask]["_violations"].apply(lambda x: pattern_name in x).sum()
        pattern_stats[pattern_name] = count
        print(f"  - {pattern_name}: {count}件")
    print()

    # 違反エピソードの詳細リスト作成
    violation_details = []
    violation_df = df[violation_mask]

    for _, row in violation_df.iterrows():
        age_val = row.get("age", "")
        if pd.notna(age_val):
            try:
                age_val = int(age_val)
            except (ValueError, TypeError):
                age_val = str(age_val)
        else:
            age_val = ""

        detail = {
            "episode_id": str(row["episode_id"]),
            "person_name": str(row.get("person_name", "")),
            "work_title": str(row.get("work_title", "")),
            "age": age_val,
            "violations": list(row["_violations"]),
            "episode_text_preview": str(row.get("episode_text", ""))[:200],
        }
        violation_details.append(detail)

    # サンプル表示
    print("[SAMPLE] 違反エピソードサンプル（最初の10件）:")
    for detail in violation_details[:10]:
        print(f"  EP: {detail['episode_id']} | {detail['person_name']} ({detail['work_title']})")
        print(f"      違反: {', '.join(detail['violations'])}")
        print(f"      Text: {detail['episode_text_preview'][:80]}...")
        print()

    if dry_run:
        print("[DRY-RUN] 実際の更新はスキップしました")

        # 一時カラムを削除
        df.drop(columns=["_violations", "_has_violation"], inplace=True)
        return

    # 実際の修正処理
    print("[EXEC] 違反エピソードを修正中...")

    # episode_authenticityカラムがなければ追加
    if "episode_authenticity" not in df.columns:
        df["episode_authenticity"] = ""

    # 違反エピソードの処理
    # episode_textを空文字に設定し、episode_authenticityにフラグを設定
    df.loc[violation_mask, "episode_text"] = ""
    df.loc[violation_mask, "episode_authenticity"] = "llm_pattern_violation"

    # 一時カラムを削除
    df.drop(columns=["_violations", "_has_violation"], inplace=True)

    # CSVを保存
    print(f"[SAVE] CSV保存中: {MASTER_CSV}")
    df.to_csv(MASTER_CSV, index=False, encoding="utf-8-sig")
    print("[DONE] CSV更新完了")

    # レポート保存
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d")
    report_path = REPORTS_DIR / f"llm_pattern_violation_fix_report_{timestamp}.json"

    # pattern_statsをintに変換
    pattern_stats_int = {k: int(v) for k, v in pattern_stats.items()}

    report = {
        "timestamp": datetime.now().isoformat(),
        "total_episodes": int(len(df)),
        "fictional_episodes": int(fictional_count),
        "violation_count": int(violation_count),
        "pattern_stats": pattern_stats_int,
        "violations": violation_details,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"[REPORT] レポート保存: {report_path}")
    print()
    print("=" * 60)
    print(f"[SUMMARY] {violation_count:,}件の違反エピソードを修正しました")
    print("=" * 60)


if __name__ == "__main__":
    main()
