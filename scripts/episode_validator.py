#!/usr/bin/env python3
"""
エピソード品質バリデーター

生成されたエピソードのミスや問題を自動検出するシステム。

検出項目:
1. フォーマット違反（「あなたと同じN歳のとき」形式）
2. 年齢不整合（本文中の年齢と登録年齢の不一致）
3. 人物名不整合（本文に人物名が含まれていない）
4. メタ表現（架空キャラの「実在しません」等）
5. プレースホルダー・未完成テキスト
6. 文字数異常（短すぎ/長すぎ）
7. 重複エピソード

使用方法:
    # 新規生成エピソードをチェック
    python scripts/episode_validator.py --source pipeline_staging

    # マスターCSV全体をチェック
    python scripts/episode_validator.py --source master

    # 特定エピソードをチェック
    python scripts/episode_validator.py --episode EP-123456

    # 問題を自動修正（可能な場合）
    python scripts/episode_validator.py --source pipeline_staging --fix
"""

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# CSVパス
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
STAGING_CSV = PROJECT_ROOT / "generated" / "pipeline_staging.csv"
REPORT_DIR = PROJECT_ROOT / "reports"


# =============================================================================
# 検出パターン定義
# =============================================================================

# フォーマットパターン
FORMAT_PATTERN = re.compile(r"^あなたと同じ(\d+)歳のとき[、, ]?(.+?)(?:は|が)")

# メタ表現パターン（架空キャラ用）
META_PATTERNS = [
    (re.compile(r"架空の"), "「架空の」という表現"),
    (re.compile(r"フィクション"), "「フィクション」という表現"),
    (re.compile(r"実在しない"), "「実在しない」という表現"),
    (re.compile(r"存在しません"), "「存在しません」という表現"),
    (re.compile(r"申し訳"), "「申し訳」という表現"),
    (
        re.compile(r"(?:公式な?|正式な?)(?:記録|描写|設定)(?:は|が)(?:ない|ありません|存在しない)"),
        "公式記録がないという表現",
    ),
    (
        re.compile(r"(?:実際の|現実の)(?:エピソード|出来事)(?:は|が)(?:ない|ありません)"),
        "実際のエピソードがないという表現",
    ),
]

# プレースホルダーパターン
PLACEHOLDER_PATTERNS = [
    (re.compile(r"\[.*?\]"), "角括弧のプレースホルダー"),
    (re.compile(r"\{.*?\}"), "波括弧のプレースホルダー"),
    (re.compile(r"TODO|FIXME|XXX", re.IGNORECASE), "TODO/FIXME"),
    (re.compile(r"〇〇|○○|××|■■"), "伏字"),
    (re.compile(r"\.{3,}"), "省略記号の連続"),
]

# 文字数しきい値
MIN_CHARS = 100
MAX_CHARS = 500


@dataclass
class ValidationIssue:
    """検出された問題"""

    episode_id: str
    person_name: str
    age: str
    issue_type: str
    severity: str  # CRITICAL, WARNING, INFO
    message: str
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """バリデーション結果"""

    total_checked: int = 0
    issues: List[ValidationIssue] = field(default_factory=list)

    def add_issue(self, issue: ValidationIssue):
        self.issues.append(issue)

    def summary(self) -> Dict:
        by_type = defaultdict(int)
        by_severity = defaultdict(int)
        for issue in self.issues:
            by_type[issue.issue_type] += 1
            by_severity[issue.severity] += 1

        return {
            "total_checked": self.total_checked,
            "total_issues": len(self.issues),
            "by_severity": dict(by_severity),
            "by_type": dict(by_type),
            "critical_count": by_severity.get("CRITICAL", 0),
            "warning_count": by_severity.get("WARNING", 0),
            "info_count": by_severity.get("INFO", 0),
        }


def check_format(episode: Dict) -> Optional[ValidationIssue]:
    """フォーマットチェック"""
    text = episode.get("episode_text", "")
    episode_id = episode.get("episode_id", "unknown")
    person_name = episode.get("person_name", "")
    age = episode.get("age", "")

    if not text:
        return ValidationIssue(
            episode_id=episode_id,
            person_name=person_name,
            age=age,
            issue_type="empty_text",
            severity="CRITICAL",
            message="エピソードテキストが空です",
        )

    match = FORMAT_PATTERN.match(text)
    if not match:
        return ValidationIssue(
            episode_id=episode_id,
            person_name=person_name,
            age=age,
            issue_type="format_violation",
            severity="CRITICAL",
            message="「あなたと同じN歳のとき、[人物名]は」形式で始まっていません",
            suggestion=f"「あなたと同じ{age}歳のとき、{person_name}は」で始めてください",
        )

    return None


def check_age_consistency(episode: Dict) -> Optional[ValidationIssue]:
    """年齢整合性チェック"""
    text = episode.get("episode_text", "")
    episode_id = episode.get("episode_id", "unknown")
    person_name = episode.get("person_name", "")
    age = episode.get("age", "")

    if not age or not text:
        return None

    match = FORMAT_PATTERN.match(text)
    if match:
        text_age = match.group(1)
        if text_age != str(age):
            return ValidationIssue(
                episode_id=episode_id,
                person_name=person_name,
                age=age,
                issue_type="age_mismatch",
                severity="CRITICAL",
                message=f"年齢不整合: 登録年齢={age}歳、本文中={text_age}歳",
                suggestion=f"本文の年齢を{age}歳に修正してください",
            )

    return None


def check_name_in_text(episode: Dict) -> Optional[ValidationIssue]:
    """人物名が本文に含まれているかチェック"""
    text = episode.get("episode_text", "")
    episode_id = episode.get("episode_id", "unknown")
    person_name = episode.get("person_name", "")
    age = episode.get("age", "")

    if not person_name or not text:
        return None

    # 人物名の正規化（括弧内の別名も考慮）
    name_variants = [person_name]

    # 括弧内の別名を抽出
    paren_match = re.search(r"[（(](.+?)[）)]", person_name)
    if paren_match:
        name_variants.append(paren_match.group(1))
        name_variants.append(re.sub(r"[（(].+?[）)]", "", person_name).strip())

    # スペースで分割した部分名も追加
    for variant in list(name_variants):
        parts = re.split(r"[\s・]", variant)
        if len(parts) > 1:
            name_variants.extend(parts)

    # いずれかの名前バリエーションが含まれているかチェック
    text_lower = text.lower()
    found = any(v.lower() in text_lower for v in name_variants if len(v) >= 2)

    if not found:
        return ValidationIssue(
            episode_id=episode_id,
            person_name=person_name,
            age=age,
            issue_type="name_not_in_text",
            severity="CRITICAL",
            message=f"人物名「{person_name}」が本文に含まれていません",
            suggestion="本文に正しい人物名を含めてください",
        )

    return None


def check_name_mismatch(episode: Dict) -> Optional[ValidationIssue]:
    """
    本文冒頭の人物名と登録人物名の整合性チェック

    「あなたと同じN歳のとき、[人物名]は」の[人物名]部分が
    登録されているperson_nameと一致するかを検証する。

    これにより、別の人物についてのエピソードが誤って登録されているケースを検出する。
    """
    text = episode.get("episode_text", "")
    episode_id = episode.get("episode_id", "unknown")
    person_name = episode.get("person_name", "")
    age = episode.get("age", "")

    if not person_name or not text:
        return None

    # 本文から人物名を抽出
    match = re.search(r"あなたと同じ\d+歳のとき[、, ]?\s*([^はがをにで、,]+?)(?:は|が)", text)
    if not match:
        return None  # フォーマット違反は別チェックで検出

    text_name = match.group(1).strip()

    # 名前の正規化
    def normalize(name: str) -> str:
        name = re.sub(r"[（(][^)）]+[)）]", "", name)
        name = re.sub(r"(さん|氏|君|様|先生|博士|教授)$", "", name)
        return name.strip().replace(" ", "").replace("　", "")

    pn = normalize(person_name)
    tn = normalize(text_name)

    # 完全一致
    if pn == tn:
        return None

    # 部分一致（許容）
    if len(pn) >= 2 and len(tn) >= 2:
        if pn in tn or tn in pn:
            return None

    # 文字の重複率チェック
    pn_chars = set(pn)
    tn_chars = set(tn)
    common = pn_chars & tn_chars
    if len(common) >= 2 and len(common) / max(len(pn_chars), len(tn_chars)) >= 0.5:
        return None

    # 不一致 - 深刻な問題
    return ValidationIssue(
        episode_id=episode_id,
        person_name=person_name,
        age=age,
        issue_type="name_content_mismatch",
        severity="CRITICAL",
        message=f"名前-内容不整合: 登録名=「{person_name}」、本文内=「{text_name}」",
        suggestion="エピソード内容と登録人物名が一致していません。再生成または削除が必要です。",
    )


def check_meta_expressions(episode: Dict) -> List[ValidationIssue]:
    """メタ表現チェック（架空キャラ用）"""
    issues = []
    text = episode.get("episode_text", "")
    episode_id = episode.get("episode_id", "unknown")
    person_name = episode.get("person_name", "")
    age = episode.get("age", "")
    person_type = episode.get("person_type", "REAL")

    # 架空キャラの場合のみチェック
    if person_type != "FICTIONAL":
        return issues

    for pattern, description in META_PATTERNS:
        if pattern.search(text):
            issues.append(
                ValidationIssue(
                    episode_id=episode_id,
                    person_name=person_name,
                    age=age,
                    issue_type="meta_expression",
                    severity="CRITICAL",
                    message=f"メタ表現を検出: {description}",
                    suggestion="架空キャラのエピソードはフィクションとして自然に記述してください",
                )
            )

    return issues


def check_placeholders(episode: Dict) -> List[ValidationIssue]:
    """プレースホルダーチェック"""
    issues = []
    text = episode.get("episode_text", "")
    episode_id = episode.get("episode_id", "unknown")
    person_name = episode.get("person_name", "")
    age = episode.get("age", "")

    for pattern, description in PLACEHOLDER_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            issues.append(
                ValidationIssue(
                    episode_id=episode_id,
                    person_name=person_name,
                    age=age,
                    issue_type="placeholder",
                    severity="WARNING",
                    message=f"プレースホルダーを検出: {description} ({matches[:3]})",
                    suggestion="具体的な内容に置き換えてください",
                )
            )

    return issues


def check_length(episode: Dict) -> Optional[ValidationIssue]:
    """文字数チェック"""
    text = episode.get("episode_text", "")
    episode_id = episode.get("episode_id", "unknown")
    person_name = episode.get("person_name", "")
    age = episode.get("age", "")

    length = len(text)

    if length < MIN_CHARS:
        return ValidationIssue(
            episode_id=episode_id,
            person_name=person_name,
            age=age,
            issue_type="too_short",
            severity="WARNING",
            message=f"文字数不足: {length}字 (最小{MIN_CHARS}字)",
            suggestion="より詳細なエピソードに拡張してください",
        )

    if length > MAX_CHARS:
        return ValidationIssue(
            episode_id=episode_id,
            person_name=person_name,
            age=age,
            issue_type="too_long",
            severity="INFO",
            message=f"文字数超過: {length}字 (最大{MAX_CHARS}字)",
            suggestion="簡潔に要約してください",
        )

    return None


def check_duplicates(episodes: List[Dict]) -> List[ValidationIssue]:
    """重複チェック"""
    issues = []
    seen_texts = {}

    for ep in episodes:
        text = ep.get("episode_text", "")
        episode_id = ep.get("episode_id", "unknown")
        person_name = ep.get("person_name", "")
        age = ep.get("age", "")

        # テキストの正規化（空白除去）
        normalized = re.sub(r"\s+", "", text)

        if normalized in seen_texts:
            original_id = seen_texts[normalized]
            issues.append(
                ValidationIssue(
                    episode_id=episode_id,
                    person_name=person_name,
                    age=age,
                    issue_type="duplicate",
                    severity="CRITICAL",
                    message=f"重複エピソード: {original_id}と同一内容",
                    suggestion="重複を削除するか、異なるエピソードに書き換えてください",
                )
            )
        else:
            seen_texts[normalized] = episode_id

    return issues


def validate_episode(episode: Dict) -> List[ValidationIssue]:
    """単一エピソードをバリデーション"""
    issues = []

    # フォーマットチェック
    issue = check_format(episode)
    if issue:
        issues.append(issue)

    # 年齢整合性
    issue = check_age_consistency(episode)
    if issue:
        issues.append(issue)

    # 人物名チェック
    issue = check_name_in_text(episode)
    if issue:
        issues.append(issue)

    # 名前-内容整合性チェック（ミスマッチ検出）
    issue = check_name_mismatch(episode)
    if issue:
        issues.append(issue)

    # メタ表現
    issues.extend(check_meta_expressions(episode))

    # プレースホルダー
    issues.extend(check_placeholders(episode))

    # 文字数
    issue = check_length(episode)
    if issue:
        issues.append(issue)

    return issues


def validate_episodes(episodes: List[Dict]) -> ValidationResult:
    """複数エピソードをバリデーション"""
    result = ValidationResult(total_checked=len(episodes))

    # 個別チェック
    for ep in episodes:
        issues = validate_episode(ep)
        for issue in issues:
            result.add_issue(issue)

    # 重複チェック
    dup_issues = check_duplicates(episodes)
    for issue in dup_issues:
        result.add_issue(issue)

    return result


def load_episodes(source: str) -> List[Dict]:
    """エピソードを読み込み"""
    if source == "master":
        csv_path = MASTER_CSV
    elif source == "pipeline_staging":
        csv_path = STAGING_CSV
    else:
        csv_path = Path(source)

    if not csv_path.exists():
        print(f"❌ ファイルが見つかりません: {csv_path}")
        return []

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def print_report(result: ValidationResult):
    """レポートを表示"""
    print("=" * 70)
    print("🔍 エピソード品質バリデーションレポート")
    print("=" * 70)

    summary = result.summary()
    print("\n📊 サマリ:")
    print(f"  チェック件数: {summary['total_checked']}")
    print(f"  問題検出数: {summary['total_issues']}")
    print(f"    🚨 CRITICAL: {summary['critical_count']}")
    print(f"    ⚠️  WARNING: {summary['warning_count']}")
    print(f"    ℹ️  INFO: {summary['info_count']}")

    if summary["by_type"]:
        print("\n📋 問題種別:")
        for issue_type, count in sorted(summary["by_type"].items(), key=lambda x: -x[1]):
            print(f"    {issue_type}: {count}件")

    # 詳細表示（CRITICALのみ）
    critical_issues = [i for i in result.issues if i.severity == "CRITICAL"]
    if critical_issues:
        print(f"\n🚨 CRITICAL問題 ({len(critical_issues)}件):")
        for issue in critical_issues[:20]:  # 最大20件表示
            print(f"\n  [{issue.episode_id}] {issue.person_name} ({issue.age}歳)")
            print(f"    問題: {issue.message}")
            if issue.suggestion:
                print(f"    対処: {issue.suggestion}")

    if len(critical_issues) > 20:
        print(f"\n  ... 他 {len(critical_issues) - 20}件")

    print()


def main():
    parser = argparse.ArgumentParser(description="エピソード品質バリデーター")
    parser.add_argument(
        "--source", type=str, default="pipeline_staging", help="チェック対象 (master, pipeline_staging, またはCSVパス)"
    )
    parser.add_argument("--episode", type=str, help="特定エピソードIDをチェック")
    parser.add_argument("--output", type=str, help="JSONレポート出力先")
    parser.add_argument("--fix", action="store_true", help="自動修正を試みる（未実装）")
    args = parser.parse_args()

    # エピソード読み込み
    episodes = load_episodes(args.source)

    if not episodes:
        print("❌ チェック対象のエピソードがありません")
        sys.exit(1)

    # 特定エピソードフィルター
    if args.episode:
        episodes = [e for e in episodes if e.get("episode_id") == args.episode]
        if not episodes:
            print(f"❌ エピソードが見つかりません: {args.episode}")
            sys.exit(1)

    print(f"📋 {len(episodes)}件のエピソードをチェック中...")

    # バリデーション実行
    result = validate_episodes(episodes)

    # レポート表示
    print_report(result)

    # JSON出力
    if args.output:
        output_path = Path(args.output)
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "source": args.source,
            "summary": result.summary(),
            "issues": [
                {
                    "episode_id": i.episode_id,
                    "person_name": i.person_name,
                    "age": i.age,
                    "issue_type": i.issue_type,
                    "severity": i.severity,
                    "message": i.message,
                    "suggestion": i.suggestion,
                }
                for i in result.issues
            ],
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        print(f"📝 レポート保存: {output_path}")

    # 終了コード
    if result.summary()["critical_count"] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
