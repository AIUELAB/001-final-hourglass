#!/usr/bin/env python3
"""
エピソード完全性ゲート - 必須フィールド充填チェック + 派生フィールド自動補完

EPUPシステムの再発防止策:
- 新規エピソード追加前に必須フィールドの充填を検証
- 欠損があればエピソードを拒否
- 派生フィールド（年代、5軸スコア）は自動補完

RCA-20260106: 年代・5軸スコア欠損問題の再発防止
- 年代: ageから自動計算
- 総合品質: (記憶性 + 生成品質) / 2
- 感情インパクト: (共感性 + 意外性) / 2
- composite_score_5axis: 5軸平均

Usage:
    # 単一エピソード検証
    python scripts/validation/episode_completeness_gate.py --episode-id EP-xxx

    # 全エピソード検証
    python scripts/validation/episode_completeness_gate.py --all

    # 新規エピソードJSONを検証
    python scripts/validation/episode_completeness_gate.py --json '{"episode_id": "...", ...}'

    # 派生フィールドを自動補完して検証
    python scripts/validation/episode_completeness_gate.py --json '...' --auto-fill
"""

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
CSV_PATH = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"

# 必須フィールド定義
REQUIRED_FIELDS = {
    # 基本情報
    "episode_id": "エピソードID",
    "person_id": "人物ID",
    "person_name": "人物名",
    "age": "年齢",
    "category": "カテゴリ",
    "episode_type": "エピソードタイプ",
    "episode_text": "エピソードテキスト",
    # 7軸スコア（必須）
    "記憶性スコア": "記憶性スコア",
    "共感性スコア": "共感性スコア",
    "意外性スコア": "意外性スコア",
    "生成品質スコア": "生成品質スコア",
    "教育的価値": "教育的価値",
    "ストーリー品質": "ストーリー品質",
    "事実密度": "事実密度",
}

# 数値フィールド（0以上の値が必要）
# 注意: ageはperson_type=FICTIONALの場合は上限なし（神話キャラ等）
NUMERIC_FIELDS = {
    "age": (0, 150, "年齢"),  # FICTIONAL以外の上限
    "記憶性スコア": (1, 10, "記憶性スコア"),
    "共感性スコア": (1, 10, "共感性スコア"),
    "意外性スコア": (1, 10, "意外性スコア"),
    "生成品質スコア": (1, 10, "生成品質スコア"),
    "教育的価値": (1, 10, "教育的価値"),
    "ストーリー品質": (1, 10, "ストーリー品質"),
    "事実密度": (1, 10, "事実密度"),
}

# 架空キャラは年齢上限なし
AGE_UNLIMITED_PERSON_TYPES = {"FICTIONAL"}

# エピソードタイプの有効値
VALID_EPISODE_TYPES = {"転機", "達成", "死去", "挑戦", "キャリア", "革新", "創業", "失敗", "復帰"}


def age_to_nendai(age_str: str) -> str:
    """年齢から年代ラベルを生成（EPUP再発防止）"""
    try:
        age = float(age_str)
        if age >= 60:
            return "60歳以上"
        elif age >= 50:
            return "50代"
        elif age >= 40:
            return "40代"
        elif age >= 30:
            return "30代"
        elif age >= 20:
            return "20代"
        elif age >= 10:
            return "10代"
        elif age >= 1:
            return "幼少期"
        else:
            return ""
    except (ValueError, TypeError):
        return ""


def auto_fill_derived_fields(episode: dict) -> dict:
    """
    派生フィールドを自動補完（EPUP再発防止）

    補完対象:
    - 年代: ageから計算
    - 総合品質: (記憶性 + 生成品質) / 2
    - 感情インパクト: (共感性 + 意外性) / 2
    - composite_score_5axis: 5軸平均
    """
    filled = episode.copy()

    # 年代の補完
    if not filled.get("年代", "").strip() and filled.get("age", "").strip():
        filled["年代"] = age_to_nendai(filled["age"])

    # 7軸スコアを取得
    mem = float(filled.get("記憶性スコア", 0) or 0)
    gen = float(filled.get("生成品質スコア", 0) or 0)
    emp = float(filled.get("共感性スコア", 0) or 0)
    sur = float(filled.get("意外性スコア", 0) or 0)
    edu = float(filled.get("教育的価値", 0) or 0)
    story = float(filled.get("ストーリー品質", 0) or 0)
    fact = float(filled.get("事実密度", 0) or 0)

    # 5軸スコアの補完
    if not filled.get("総合品質", "").strip() and mem and gen:
        filled["総合品質"] = f"{(mem + gen) / 2:.2f}"

    if not filled.get("感情インパクト", "").strip() and emp and sur:
        filled["感情インパクト"] = f"{(emp + sur) / 2:.2f}"

    # composite_score_5axisの補完
    if not filled.get("composite_score_5axis", "").strip():
        overall = float(filled.get("総合品質", 0) or 0)
        emotional = float(filled.get("感情インパクト", 0) or 0)
        if overall and emotional and edu and story and fact:
            filled["composite_score_5axis"] = f"{(overall + emotional + edu + story + fact) / 5:.2f}"

    return filled


@dataclass
class ValidationResult:
    """検証結果"""

    passed: bool
    errors: list[str]
    warnings: list[str]
    episode_id: str = ""


def validate_episode(episode: dict, auto_fill: bool = False) -> ValidationResult:
    """
    エピソードの完全性を検証

    Args:
        episode: エピソードデータ
        auto_fill: Trueの場合、派生フィールドを自動補完してから検証
    """
    # 自動補完オプション
    if auto_fill:
        episode = auto_fill_derived_fields(episode)

    errors = []
    warnings = []
    episode_id = episode.get("episode_id", "unknown")

    # 1. 必須フィールド存在チェック
    for field, label in REQUIRED_FIELDS.items():
        val = episode.get(field)
        if val is None or str(val).strip() == "":
            errors.append(f"必須フィールド欠損: {label} ({field})")

    # 2. 数値フィールド範囲チェック
    person_type = episode.get("person_type", "")
    for field, (min_val, max_val, label) in NUMERIC_FIELDS.items():
        val = episode.get(field)
        if val is not None and str(val).strip() != "":
            try:
                num_val = float(val)
                # 架空キャラは年齢上限なし
                if field == "age" and person_type in AGE_UNLIMITED_PERSON_TYPES:
                    if num_val < min_val:
                        errors.append(f"範囲外: {label}={num_val} (最小: {min_val})")
                elif num_val < min_val or num_val > max_val:
                    errors.append(f"範囲外: {label}={num_val} (期待: {min_val}-{max_val})")
            except (ValueError, TypeError):
                errors.append(f"数値変換エラー: {label}={val}")

    # 3. エピソードタイプ有効性チェック
    ep_type = episode.get("episode_type", "")
    if ep_type and ep_type not in VALID_EPISODE_TYPES:
        errors.append(f"無効なエピソードタイプ: {ep_type} (有効: {', '.join(VALID_EPISODE_TYPES)})")

    # 4. エピソードテキスト最小長チェック
    text = episode.get("episode_text", "")
    if len(text) < 50:
        errors.append(f"エピソードテキストが短すぎます: {len(text)}文字 (最小: 50文字)")

    # 5. 警告: 推奨フィールド
    recommended = ["composite_score", "episode_fame_v6", "super_total_score"]
    for field in recommended:
        val = episode.get(field)
        if val is None or str(val).strip() == "" or val == 0:
            warnings.append(f"推奨フィールド未設定: {field}")

    return ValidationResult(
        passed=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        episode_id=episode_id,
    )


def validate_all_episodes() -> list[ValidationResult]:
    """全エピソードを検証"""
    results = []
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            result = validate_episode(row)
            if not result.passed:
                results.append(result)
    return results


def main():
    parser = argparse.ArgumentParser(description="エピソード完全性ゲート")
    parser.add_argument("--episode-id", help="検証するエピソードID")
    parser.add_argument("--all", action="store_true", help="全エピソードを検証")
    parser.add_argument("--json", help="検証するエピソードJSON")
    parser.add_argument("--strict", action="store_true", help="警告もエラーとして扱う")
    parser.add_argument(
        "--auto-fill",
        action="store_true",
        help="派生フィールド（年代、5軸スコア）を自動補完してから検証",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("🔍 エピソード完全性ゲート")
    print("=" * 60)

    if args.json:
        # JSON入力を検証
        episode = json.loads(args.json)
        result = validate_episode(episode, auto_fill=args.auto_fill)
        if result.passed:
            print(f"✅ 検証成功: {result.episode_id}")
        else:
            print(f"❌ 検証失敗: {result.episode_id}")
            for err in result.errors:
                print(f"   エラー: {err}")
        for warn in result.warnings:
            print(f"   警告: {warn}")
        return 0 if result.passed and not (args.strict and result.warnings) else 1

    elif args.episode_id:
        # 特定エピソードを検証
        with open(CSV_PATH, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("episode_id") == args.episode_id:
                    result = validate_episode(row)
                    if result.passed:
                        print(f"✅ 検証成功: {result.episode_id}")
                    else:
                        print(f"❌ 検証失敗: {result.episode_id}")
                        for err in result.errors:
                            print(f"   エラー: {err}")
                    for warn in result.warnings:
                        print(f"   警告: {warn}")
                    return 0 if result.passed else 1
        print(f"❌ エピソードが見つかりません: {args.episode_id}")
        return 1

    elif args.all:
        # 全エピソード検証
        failed_results = validate_all_episodes()
        total = sum(1 for _ in open(CSV_PATH, encoding="utf-8-sig")) - 1  # ヘッダー除く

        print("\n📊 検証結果:")
        print(f"   総エピソード数: {total:,}")
        print(f"   検証成功: {total - len(failed_results):,}")
        print(f"   検証失敗: {len(failed_results):,}")

        if failed_results:
            print("\n❌ 失敗エピソード:")
            for result in failed_results[:10]:
                print(f"   {result.episode_id}:")
                for err in result.errors:
                    print(f"      - {err}")
            if len(failed_results) > 10:
                print(f"   ... 他 {len(failed_results) - 10} 件")

        return 0 if not failed_results else 1

    else:
        # デフォルト: 全検証
        args.all = True
        return main()


if __name__ == "__main__":
    sys.exit(main())
