#!/usr/bin/env python3
"""
EPUP: LLM分類審査で「invalid」と判定されたエピソードの修正・再生成スクリプト

Usage:
    # 1. 修正・再生成対象の抽出と統計表示
    python scripts/fix/fix_invalid_fictional_episodes.py analyze

    # 2. 修正可能なエピソードを自動修正
    python scripts/fix/fix_invalid_fictional_episodes.py fix [--dry-run]

    # 3. 再生成用JSONLを生成
    python scripts/fix/fix_invalid_fictional_episodes.py generate-jsonl [--output PATH]

    # 4. 再生成結果を適用
    python scripts/fix/fix_invalid_fictional_episodes.py apply --batch-id <batch_id>
"""

import argparse
import json
import logging
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ファイルパス
CLASSIFICATION_RESULTS = PROJECT_ROOT / "src" / "reports" / "fictional_llm_classification_results.csv"
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
WORK_SETTINGS_MASTER = PROJECT_ROOT / "preserved" / "data" / "fictional_work_settings_master.json"
OUTPUT_DIR = PROJECT_ROOT / "src" / "reports"
BACKUP_DIR = PROJECT_ROOT / "preserved" / "backups"


# =============================================================================
# 自動修正パターン定義
# =============================================================================


class AutoFixPatterns:
    """修正可能な問題の自動修正パターン"""

    # 年号置換パターン（西暦年号 → 汎用表現）
    YEAR_PATTERNS = [
        # 具体的な西暦年 → 「ある年」
        (r"(\d{4})年(?!代)", "ある年"),
        # 「XXXX年代」は残す
        # 「XX世紀」は残す
    ]

    # 年号置換の除外条件（約X年前、X歳のとき等は残す）
    YEAR_EXCLUDE_PATTERNS = [
        r"約\d+年前",
        r"\d+年(前|後|間)",
        r"\d+歳の(とき|頃)",
    ]

    # 現実企業名の汎用化パターン
    COMPANY_PATTERNS = [
        (r"(?:株式会社)?ディズニー(?:・[ア-ン]+)?", "王国"),
        (r"(?:株式会社)?スクウェア・エニックス", "ゲーム制作会社"),
        (r"(?:株式会社)?バンダイナムコ", "玩具会社"),
        (r"(?:株式会社)?任天堂", "ゲーム会社"),
        (r"(?:株式会社)?ソニー(?:・[ア-ン]+)?", "大企業"),
        (r"(?:株式会社)?Apple(?:社)?", "技術企業"),
        (r"(?:株式会社)?Google(?:社)?", "情報企業"),
        (r"ブロードウェイ", "王都の劇場街"),
        (r"ハリウッド", "映画の都"),
        (r"アカデミー賞", "大賞"),
        (r"ゴールデングローブ賞", "名誉賞"),
    ]

    # メタ表現削除パターン
    META_PATTERNS = [
        r"は架空の(キャラクター|人物|存在)であり[^。]*。",
        r"実在(しない|の人物ではない)[^。]*。",
        r"エピソード(は|が)存在しません[^。]*。",
        r"公式(な|の)?描写は.*存在しない[^。]*。",
        r"『[^』]+』(の|という)?(アニメ|漫画|映画|作品)[^。]*。",
        r"原作では[^。]*描かれていない[^。]*。",
    ]

    # 現実人物名削除パターン（作品外の実在人物）
    REAL_PEOPLE_PATTERNS = [
        r"(?:手塚治虫|宮崎駿|庵野秀明|鳥山明|尾田栄一郎|岸本斉史|吾峠呼世晴)[^、。]*[、。]",
    ]


def load_classification_results() -> pd.DataFrame:
    """分類結果CSVを読み込む"""
    if not CLASSIFICATION_RESULTS.exists():
        logger.error(f"分類結果ファイルが見つかりません: {CLASSIFICATION_RESULTS}")
        sys.exit(1)
    return pd.read_csv(CLASSIFICATION_RESULTS, encoding="utf-8-sig")


def load_master_csv() -> pd.DataFrame:
    """マスターCSVを読み込む"""
    if not MASTER_CSV.exists():
        logger.error(f"マスターCSVが見つかりません: {MASTER_CSV}")
        sys.exit(1)
    return pd.read_csv(MASTER_CSV, encoding="utf-8-sig")


def load_work_settings() -> Dict[str, Any]:
    """作品設定マスターを読み込む"""
    if not WORK_SETTINGS_MASTER.exists():
        logger.warning(f"作品設定マスターが見つかりません: {WORK_SETTINGS_MASTER}")
        return {"works": {}}
    with open(WORK_SETTINGS_MASTER, "r", encoding="utf-8") as f:
        return json.load(f)


def backup_master_csv() -> Path:
    """マスターCSVのバックアップを作成"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"MASTER_EPISODES_CURRENT_{timestamp}.csv"
    shutil.copy2(MASTER_CSV, backup_path)
    logger.info(f"バックアップ作成: {backup_path}")
    return backup_path


# =============================================================================
# 分析機能
# =============================================================================


def cmd_analyze(args: argparse.Namespace) -> None:
    """
    分類結果を分析し、統計情報を表示
    """
    logger.info("=== 分類結果分析 ===")

    df = load_classification_results()
    _ = load_master_csv()  # 将来の拡張用に読み込み（現在未使用）

    # 基本統計
    total = len(df)
    logger.info(f"総エピソード数: {total:,}")

    # authenticityの分布
    authenticity_counts = df["authenticity"].value_counts()
    logger.info("\n【authenticity分布】")
    for auth, count in authenticity_counts.items():
        pct = count / total * 100
        logger.info(f"  {auth}: {count:,} ({pct:.1f}%)")

    # fixabilityの分布
    fixability_counts = df["fixability"].value_counts(dropna=False)
    logger.info("\n【fixability分布】")
    for fix, count in fixability_counts.items():
        fix_label = fix if pd.notna(fix) and fix else "(空白)"  # type: ignore[arg-type]
        pct = count / total * 100
        logger.info(f"  {fix_label}: {count:,} ({pct:.1f}%)")

    # issues の分布
    logger.info("\n【issues分布（上位20）】")
    issues_expanded = df["issues"].dropna().str.split("|").explode()
    issues_counts = issues_expanded.value_counts().head(20)
    for issue, count in issues_counts.items():
        logger.info(f"  {issue}: {count:,}")

    # 修正対象の詳細
    fixable_df = df[df["fixability"] == "fixable"]
    regenerate_df = df[df["fixability"] == "regenerate"]
    invalid_df = df[df["authenticity"] == "invalid"]

    logger.info("\n【対象件数サマリ】")
    logger.info(f"  自動修正対象 (fixable): {len(fixable_df):,}")
    logger.info(f"  再生成対象 (regenerate): {len(regenerate_df):,}")
    logger.info(f"  invalid判定: {len(invalid_df):,}")

    # 作品別の分布（上位10）
    logger.info("\n【作品別・修正対象（上位10）】")
    work_fixable = fixable_df["work_title"].value_counts().head(10)  # type: ignore[union-attr]
    for work, count in work_fixable.items():
        logger.info(f"  {work}: {count:,}")

    logger.info("\n【作品別・再生成対象（上位10）】")
    work_regenerate = regenerate_df["work_title"].value_counts().head(10)  # type: ignore[union-attr]
    for work, count in work_regenerate.items():
        logger.info(f"  {work}: {count:,}")

    # サンプル表示
    if args.show_samples:
        logger.info("\n【fixableサンプル（3件）】")
        for _, row in fixable_df.head(3).iterrows():
            logger.info(f"  {row['episode_id']}: {row['person_name']} ({row['work_title']})")
            logger.info(f"    issues: {row['issues']}")
            issue_details = str(row.get("issue_details", ""))
            if issue_details and issue_details != "nan":
                logger.info(f"    details: {issue_details[:100]}...")

        logger.info("\n【regenerateサンプル（3件）】")
        for _, row in regenerate_df.head(3).iterrows():
            logger.info(f"  {row['episode_id']}: {row['person_name']} ({row['work_title']})")
            logger.info(f"    issues: {row['issues']}")
            issue_details = str(row.get("issue_details", ""))
            if issue_details and issue_details != "nan":
                logger.info(f"    details: {issue_details[:100]}...")


# =============================================================================
# 自動修正機能
# =============================================================================


def auto_fix_episode(episode_text: str, issues: str, work_title: str) -> Tuple[str, List[str]]:  # noqa: ARG001
    """
    修正可能な問題を自動修正

    Args:
        episode_text: エピソードテキスト
        issues: 問題カテゴリ（パイプ区切り）
        work_title: 作品タイトル（将来の拡張用）

    Returns:
        (修正後テキスト, 適用した修正のリスト)
    """
    _ = work_title  # 将来の作品別修正ルール用
    fixed_text = episode_text
    applied_fixes = []

    # 年号修正（reality_mixingまたはworld_setting_violation時）
    if "reality_mixing" in issues or "world_setting_violation" in issues:
        for pattern, replacement in AutoFixPatterns.YEAR_PATTERNS:
            # 除外パターンをチェック
            temp_text = fixed_text
            for exclude in AutoFixPatterns.YEAR_EXCLUDE_PATTERNS:
                temp_text = re.sub(exclude, "___KEEP___", temp_text)

            # 年号を置換
            if re.search(pattern, temp_text):
                # 元のテキストで実際に置換
                new_text = re.sub(pattern, replacement, fixed_text)
                if new_text != fixed_text:
                    applied_fixes.append(f"年号置換: {pattern} → {replacement}")
                    fixed_text = new_text

    # 企業名・現実参照の修正（reality_mixing時）
    if "reality_mixing" in issues:
        for pattern, replacement in AutoFixPatterns.COMPANY_PATTERNS:
            if re.search(pattern, fixed_text, re.IGNORECASE):
                new_text = re.sub(pattern, replacement, fixed_text, flags=re.IGNORECASE)
                if new_text != fixed_text:
                    applied_fixes.append(f"企業名汎用化: {pattern} → {replacement}")
                    fixed_text = new_text

    # メタ表現削除（meta_expression時）
    if "meta_expression" in issues:
        for pattern in AutoFixPatterns.META_PATTERNS:
            if re.search(pattern, fixed_text):
                new_text = re.sub(pattern, "", fixed_text)
                if new_text != fixed_text:
                    applied_fixes.append(f"メタ表現削除: {pattern}")
                    fixed_text = new_text

    # 現実人物名削除
    if "reality_mixing" in issues:
        for pattern in AutoFixPatterns.REAL_PEOPLE_PATTERNS:
            if re.search(pattern, fixed_text):
                new_text = re.sub(pattern, "", fixed_text)
                if new_text != fixed_text:
                    applied_fixes.append(f"現実人物名削除: {pattern}")
                    fixed_text = new_text

    # 空白の正規化
    fixed_text = re.sub(r"\s+", " ", fixed_text).strip()
    fixed_text = re.sub(r"。\s*。", "。", fixed_text)

    return fixed_text, applied_fixes


def cmd_fix(args: argparse.Namespace) -> None:
    """
    修正可能なエピソードを自動修正
    """
    logger.info("=== 自動修正処理 ===")

    # データ読み込み
    class_df = load_classification_results()
    master_df = load_master_csv()

    # fixable対象を抽出
    fixable_df = class_df[class_df["fixability"] == "fixable"].copy()
    logger.info(f"修正対象: {len(fixable_df):,}件")

    if len(fixable_df) == 0:
        logger.info("修正対象がありません")
        return

    # バックアップ
    if not args.dry_run:
        backup_master_csv()

    # 修正処理
    fixed_count = 0
    fix_log = []
    updated_episode_ids = set()

    for _, row in fixable_df.iterrows():
        episode_id = row["episode_id"]
        issues = str(row.get("issues", ""))
        work_title = str(row.get("work_title", ""))

        # マスターCSVから元のエピソードを取得
        master_row = master_df[master_df["episode_id"] == episode_id]
        if master_row.empty:
            logger.warning(f"マスターCSVにエピソードが見つかりません: {episode_id}")
            continue

        original_text = str(master_row.iloc[0].get("episode_text", ""))
        if not original_text or original_text == "nan":
            continue

        # 自動修正実行
        fixed_text, applied_fixes = auto_fix_episode(original_text, issues, work_title)

        if applied_fixes and fixed_text != original_text:
            fixed_count += 1
            updated_episode_ids.add(episode_id)

            log_entry = {
                "episode_id": episode_id,
                "person_name": row.get("person_name"),
                "work_title": work_title,
                "issues": issues,
                "applied_fixes": applied_fixes,
                "original_length": len(original_text),
                "fixed_length": len(fixed_text),
            }
            fix_log.append(log_entry)

            if not args.dry_run:
                # マスターCSVを更新
                master_df.loc[master_df["episode_id"] == episode_id, "episode_text"] = fixed_text
                # episode_authenticityフィールドを追加（存在しない場合）
                if "episode_authenticity" not in master_df.columns:
                    master_df["episode_authenticity"] = ""
                master_df.loc[master_df["episode_id"] == episode_id, "episode_authenticity"] = "fixed"

            if args.verbose and fixed_count <= 10:
                logger.info(f"\n[{episode_id}] {row.get('person_name')} ({work_title})")
                logger.info(f"  修正内容: {', '.join(applied_fixes)}")
                if args.show_diff:
                    logger.info(f"  変更前: {original_text[:100]}...")
                    logger.info(f"  変更後: {fixed_text[:100]}...")

    logger.info(f"\n修正完了: {fixed_count:,}件")

    # 修正ログを保存
    log_path = OUTPUT_DIR / f"auto_fix_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(fix_log, f, ensure_ascii=False, indent=2)
    logger.info(f"修正ログ保存: {log_path}")

    # マスターCSV保存
    if not args.dry_run and fixed_count > 0:
        master_df.to_csv(MASTER_CSV, index=False, encoding="utf-8-sig")
        logger.info(f"マスターCSV更新完了: {MASTER_CSV}")
    elif args.dry_run:
        logger.info("(dry-run: 実際の更新はスキップ)")


# =============================================================================
# 再生成JSONL生成機能
# =============================================================================

# 再生成用システムプロンプト
REGENERATION_SYSTEM_PROMPT = """あなたは物語世界のエピソード生成AIです。以下のルールを絶対に守ってください。

【絶対遵守ルール】
1. すべての文を常体（だ・である調）で終えてください
2. 主語は人物名または「彼/彼女」を使用してください
3. 「私は」「私の」「私が」は絶対に使用しないでください
4. 冒頭は必ず「あなたと同じX歳のとき、[人物名]は」形式で開始してください

【作品世界観ルール】
5. 現実世界の西暦年号（1900年、2000年など）は絶対に使用しないでください
6. 作品の世界観・時代設定に沿った表現のみを使用してください
7. 「『作品名』」や「アニメ」「漫画」「映画」などのメタ的表現は禁止です
8. キャラクターは作品世界内の実在人物として扱ってください

【重要】
9. 原作で描かれていないシーンは創作しないでください
10. 不明な場合は「具体的なエピソードが存在しない」と回答してください
11. 現実の企業名、人物名、商品名は使用禁止です

【品質基準】
- 作品内の具体的なイベント・場所・人物を2つ以上
- 固有名詞を3つ以上
- 250〜350文字で完結"""


def get_regeneration_prompt(
    person_name: str,
    age: int,
    work_title: str,
    issue_details: str,
    work_settings: Optional[Dict[str, Any]] = None,
) -> str:
    """再生成用プロンプトを生成"""

    era_info = ""
    if work_settings:
        era_setting = work_settings.get("era_setting", "")
        custom_year_note = work_settings.get("custom_year_note", "")
        if era_setting:
            era_info = f"\n- 時代設定: {era_setting}"
        if custom_year_note:
            era_info += f"\n- 年号ルール: {custom_year_note}"

    return f"""# エピソード再生成タスク

## 対象キャラクター
- 人物名: {person_name}
- 年齢: {age}歳
- 作品: {work_title}{era_info}

## 問題点
以下の問題が検出されたため、再生成が必要です:
{issue_details}

## 要求
{person_name}が{age}歳のときの、作品世界観に忠実なエピソードを生成してください。

## 必須条件
1. 冒頭: 「あなたと同じ{age}歳のとき、{person_name}は」
2. 常体（だ・である調）で記述
3. 原作で描かれた事実のみを使用
4. 現実世界の要素は一切使用しない
5. メタ的表現は禁止

## 該当シーンがない場合
原作で{age}歳時点の描写がない場合は、以下のように回答してください:
「該当年齢のエピソードは原作に存在しません」

## 出力
エピソードテキストのみを出力してください（250〜350文字）。"""


def cmd_generate_jsonl(args: argparse.Namespace) -> None:
    """
    再生成が必要なエピソードのBatch API用JSONLを生成
    """
    logger.info("=== 再生成JSONL生成 ===")

    # データ読み込み
    class_df = load_classification_results()
    master_df = load_master_csv()
    work_settings_data = load_work_settings()
    work_settings = work_settings_data.get("works", {})

    # regenerate対象を抽出
    regenerate_df = class_df[class_df["fixability"] == "regenerate"].copy()
    logger.info(f"再生成対象: {len(regenerate_df):,}件")

    if len(regenerate_df) == 0:
        logger.info("再生成対象がありません")
        return

    # JSONL生成
    requests = []
    for _, row in regenerate_df.iterrows():
        episode_id = row["episode_id"]
        person_name = str(row.get("person_name", ""))
        work_title = str(row.get("work_title", ""))
        issue_details = str(row.get("issue_details", ""))

        # マスターCSVから年齢を取得
        master_row = master_df[master_df["episode_id"] == episode_id]
        if master_row.empty:
            logger.warning(f"マスターCSVにエピソードが見つかりません: {episode_id}")
            continue

        age = master_row.iloc[0].get("age", 0)
        try:
            age = int(float(age)) if pd.notna(age) else 0
        except (ValueError, TypeError):
            age = 0

        # 作品設定を取得
        ws = work_settings.get(work_title, None)

        # プロンプト生成
        user_prompt = get_regeneration_prompt(
            person_name=person_name,
            age=age,
            work_title=work_title,
            issue_details=issue_details,
            work_settings=ws,
        )

        # Batch APIリクエスト形式
        request = {
            "custom_id": episode_id,
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": REGENERATION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 600,
            },
        }
        requests.append(request)

    # JSONL出力
    output_path = args.output or (OUTPUT_DIR / f"regenerate_requests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for req in requests:
            f.write(json.dumps(req, ensure_ascii=False) + "\n")

    logger.info(f"JSONL生成完了: {output_path}")
    logger.info(f"リクエスト数: {len(requests):,}件")

    # バッチ送信コマンドを表示
    logger.info("\n【Batch API送信コマンド】")
    logger.info(f"openai api batches create --file {output_path} --endpoint /v1/chat/completions")


# =============================================================================
# 再生成結果適用機能
# =============================================================================


def cmd_apply(args: argparse.Namespace) -> None:
    """
    再生成結果をマスターCSVに適用
    """
    logger.info("=== 再生成結果適用 ===")

    batch_id = args.batch_id
    if not batch_id:
        logger.error("--batch-id を指定してください")
        return

    # 結果ファイルを探す
    result_patterns = [
        OUTPUT_DIR / f"batch_{batch_id}_results.jsonl",
        OUTPUT_DIR / f"regenerate_results_{batch_id}.jsonl",
        Path(batch_id),  # 直接パス指定の場合
    ]

    result_file = None
    for pattern in result_patterns:
        if pattern.exists():
            result_file = pattern
            break

    if not result_file:
        logger.error(f"結果ファイルが見つかりません: {batch_id}")
        logger.info("以下のコマンドで結果を取得してください:")
        logger.info(
            f"  openai api batches retrieve {batch_id} --output-file {OUTPUT_DIR}/batch_{batch_id}_results.jsonl"
        )
        return

    logger.info(f"結果ファイル: {result_file}")

    # 結果を読み込み
    results = []
    with open(result_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                results.append(json.loads(line))

    logger.info(f"結果件数: {len(results):,}")

    # バックアップ
    if not args.dry_run:
        backup_master_csv()

    # マスターCSV読み込み
    master_df = load_master_csv()

    # episode_authenticityカラムを追加（なければ）
    if "episode_authenticity" not in master_df.columns:
        master_df["episode_authenticity"] = ""

    # 結果を適用
    applied_count = 0
    skipped_count = 0
    error_count = 0

    for result in results:
        episode_id = result.get("custom_id", "")

        # 結果を取得
        response = result.get("response", {})
        body = response.get("body", {})
        choices = body.get("choices", [])

        if not choices:
            logger.warning(f"[{episode_id}] 結果なし")
            error_count += 1
            continue

        new_text = choices[0].get("message", {}).get("content", "").strip()

        # 「該当シーンなし」の場合はスキップ
        if "該当年齢のエピソード" in new_text and "存在しません" in new_text:
            logger.info(f"[{episode_id}] 該当シーンなし - スキップ")
            skipped_count += 1
            continue

        # 品質チェック
        if len(new_text) < 100:
            logger.warning(f"[{episode_id}] テキストが短すぎる ({len(new_text)}文字)")
            error_count += 1
            continue

        # マスターCSVを更新
        mask = master_df["episode_id"] == episode_id
        if mask.sum() == 0:
            logger.warning(f"[{episode_id}] マスターCSVにエピソードが見つかりません")
            error_count += 1
            continue

        if not args.dry_run:
            master_df.loc[mask, "episode_text"] = new_text
            master_df.loc[mask, "episode_authenticity"] = "regenerated"

        applied_count += 1

        if args.verbose:
            logger.info(f"[{episode_id}] 適用完了 ({len(new_text)}文字)")

    logger.info("\n適用結果:")
    logger.info(f"  適用: {applied_count:,}")
    logger.info(f"  スキップ: {skipped_count:,}")
    logger.info(f"  エラー: {error_count:,}")

    # マスターCSV保存
    if not args.dry_run and applied_count > 0:
        master_df.to_csv(MASTER_CSV, index=False, encoding="utf-8-sig")
        logger.info(f"マスターCSV更新完了: {MASTER_CSV}")
    elif args.dry_run:
        logger.info("(dry-run: 実際の更新はスキップ)")


# =============================================================================
# メイン
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="LLM分類審査で「invalid」と判定されたエピソードの修正・再生成",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 分析
  python scripts/fix/fix_invalid_fictional_episodes.py analyze --show-samples

  # 自動修正（dry-run）
  python scripts/fix/fix_invalid_fictional_episodes.py fix --dry-run --verbose

  # 自動修正（実行）
  python scripts/fix/fix_invalid_fictional_episodes.py fix

  # 再生成JSONL生成
  python scripts/fix/fix_invalid_fictional_episodes.py generate-jsonl

  # 再生成結果適用
  python scripts/fix/fix_invalid_fictional_episodes.py apply --batch-id batch_xxxxx
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="コマンド")

    # analyze
    p_analyze = subparsers.add_parser("analyze", help="分類結果を分析")
    p_analyze.add_argument("--show-samples", action="store_true", help="サンプルを表示")

    # fix
    p_fix = subparsers.add_parser("fix", help="修正可能なエピソードを自動修正")
    p_fix.add_argument("--dry-run", action="store_true", help="実際の更新をスキップ")
    p_fix.add_argument("--verbose", "-v", action="store_true", help="詳細表示")
    p_fix.add_argument("--show-diff", action="store_true", help="変更差分を表示")

    # generate-jsonl
    p_jsonl = subparsers.add_parser("generate-jsonl", help="再生成用JSONLを生成")
    p_jsonl.add_argument("--output", "-o", type=str, help="出力ファイルパス")

    # apply
    p_apply = subparsers.add_parser("apply", help="再生成結果をマスターCSVに適用")
    p_apply.add_argument("--batch-id", type=str, required=True, help="Batch ID または結果ファイルパス")
    p_apply.add_argument("--dry-run", action="store_true", help="実際の更新をスキップ")
    p_apply.add_argument("--verbose", "-v", action="store_true", help="詳細表示")

    args = parser.parse_args()

    if args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "fix":
        cmd_fix(args)
    elif args.command == "generate-jsonl":
        cmd_generate_jsonl(args)
    elif args.command == "apply":
        cmd_apply(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
