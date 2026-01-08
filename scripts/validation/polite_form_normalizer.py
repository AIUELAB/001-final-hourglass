#!/usr/bin/env python3
"""
丁寧語漏れ検知・修正スクリプト

機能:
1. エピソード本文の常体（丁寧語漏れ）を検出
2. 安全な変換ルールで自動修正
3. dry-run/execute モード対応
4. バックアップ・ログ出力

使用法:
    python scripts/validation/polite_form_normalizer.py --dry-run
    python scripts/validation/polite_form_normalizer.py --execute
"""

import argparse
import json
import re
import shutil
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved" / "data" / "backups"
REPORTS_DIR = PROJECT_ROOT / "src" / "reports"
LOGS_DIR = PROJECT_ROOT / "src" / "reports" / "logs"


@dataclass
class TransformRule:
    """変換ルール"""

    name: str
    pattern: str  # 検出用正規表現
    replacement: str  # 置換文字列（$1等のグループ参照可）
    priority: int = 0  # 優先度（高い方が先に適用）
    risk_level: str = "low"  # low/medium/high


@dataclass
class DetectionResult:
    """検出結果"""

    episode_id: str
    person_name: str
    original_text: str
    issues: list[dict] = field(default_factory=list)
    fixed_text: Optional[str] = None


@dataclass
class NormalizationStats:
    """正規化統計"""

    total_episodes: int = 0
    scanned_episodes: int = 0
    episodes_with_issues: int = 0
    total_issues: int = 0
    issues_by_pattern: dict = field(default_factory=dict)
    fixed_episodes: int = 0
    fixed_issues: int = 0


class PoliteFormNormalizer:
    """丁寧語正規化エンジン"""

    # 変換ルール（優先度順）
    TRANSFORM_RULES = [
        # === 安全な変換（文末のみ） ===
        # 〜ていた。 → 〜ていました。
        TransformRule(
            name="ていた→ていました",
            pattern=r"ていた。",
            replacement="ていました。",
            priority=100,
            risk_level="low",
        ),
        # 〜でいた。 → 〜でいました。
        TransformRule(
            name="でいた→でいました",
            pattern=r"でいた。",
            replacement="でいました。",
            priority=99,
            risk_level="low",
        ),
        # 〜だった。 → 〜でした。
        TransformRule(
            name="だった→でした",
            pattern=r"だった。",
            replacement="でした。",
            priority=98,
            risk_level="low",
        ),
        # 〜のだ。 → 〜のです。
        TransformRule(
            name="のだ→のです",
            pattern=r"のだ。",
            replacement="のです。",
            priority=97,
            risk_level="low",
        ),
        # 〜たんだ。 → 〜たんです。 (説明の「んだ」のみ)
        TransformRule(
            name="たんだ→たんです",
            pattern=r"たんだ。",
            replacement="たんです。",
            priority=96,
            risk_level="low",
        ),
        # 〜るんだ。 → 〜るんです。
        TransformRule(
            name="るんだ→るんです",
            pattern=r"るんだ。",
            replacement="るんです。",
            priority=95,
            risk_level="low",
        ),
        # 〜のである。 → 〜のです。
        TransformRule(
            name="のである→のです",
            pattern=r"のである。",
            replacement="のです。",
            priority=95,
            risk_level="low",
        ),
        # 〜である。 → 〜です。
        TransformRule(
            name="である→です",
            pattern=r"である。",
            replacement="です。",
            priority=94,
            risk_level="low",
        ),
        # === 中リスク変換（動詞活用） ===
        # 〜かった。 → 〜かったです。 (形容詞過去)
        TransformRule(
            name="かった→かったです",
            pattern=r"かった。",
            replacement="かったです。",
            priority=80,
            risk_level="medium",
        ),
        # 〜なかった。 → 〜ませんでした。
        TransformRule(
            name="なかった→ありませんでした",
            pattern=r"なかった。",
            replacement="ありませんでした。",
            priority=79,
            risk_level="medium",
        ),
        # === 安全な「わった」変換（ホワイトリスト） ===
        # Phase 1: 検証済みの安全パターン（〜わる系動詞）
        TransformRule(
            name="終わった→終わりました",
            pattern=r"終わった。",
            replacement="終わりました。",
            priority=90,
            risk_level="low",
        ),
        TransformRule(
            name="変わった→変わりました",
            pattern=r"変わった。",
            replacement="変わりました。",
            priority=90,
            risk_level="low",
        ),
        TransformRule(
            name="伝わった→伝わりました",
            pattern=r"伝わった。",
            replacement="伝わりました。",
            priority=90,
            risk_level="low",
        ),
        TransformRule(
            name="関わった→関わりました",
            pattern=r"関わった。",
            replacement="関わりました。",
            priority=90,
            risk_level="low",
        ),
        TransformRule(
            name="加わった→加わりました",
            pattern=r"加わった。",
            replacement="加わりました。",
            priority=90,
            risk_level="low",
        ),
        TransformRule(
            name="備わった→備わりました",
            pattern=r"備わった。",
            replacement="備わりました。",
            priority=90,
            risk_level="low",
        ),
        TransformRule(
            name="携わった→携わりました",
            pattern=r"携わった。",
            replacement="携わりました。",
            priority=90,
            risk_level="low",
        ),
        TransformRule(
            name="交わった→交わりました",
            pattern=r"交わった。",
            replacement="交わりました。",
            priority=90,
            risk_level="low",
        ),
        # Phase 2: 追加のわ行動詞（データから確認済み）
        TransformRule(
            name="味わった→味わいました",
            pattern=r"味わった。",
            replacement="味わいました。",
            priority=90,
            risk_level="low",
        ),
        TransformRule(
            name="こだわった→こだわりました",
            pattern=r"こだわった。",
            replacement="こだわりました。",
            priority=90,
            risk_level="low",
        ),
        TransformRule(
            name="賑わった→賑わいました",
            pattern=r"賑わった。",
            replacement="賑わいました。",
            priority=90,
            risk_level="low",
        ),
        TransformRule(
            name="教わった→教わりました",
            pattern=r"教わった。",
            replacement="教わりました。",
            priority=90,
            risk_level="low",
        ),
        # Phase 3: ワ行五段動詞（〜う → 〜いました）
        TransformRule(
            name="振るった→振るいました",
            pattern=r"振るった。",
            replacement="振るいました。",
            priority=91,
            risk_level="low",
        ),
        TransformRule(
            name="ためらった→ためらいました",
            pattern=r"ためらった。",
            replacement="ためらいました。",
            priority=91,
            risk_level="low",
        ),
        TransformRule(
            name="もらった→もらいました",
            pattern=r"もらった。",
            replacement="もらいました。",
            priority=91,
            risk_level="low",
        ),
        TransformRule(
            name="食らった→食らいました",
            pattern=r"食らった。",
            replacement="食らいました。",
            priority=91,
            risk_level="low",
        ),
        # === 五段動詞過去形（高リスク - 慎重に適用） ===
        # 〜った。 → 〜りました。 (走った、取った、作った等)
        # Note: 上記ホワイトリストが優先適用される
        TransformRule(
            name="った→りました",
            pattern=r"([らりるれろわをん])った。",
            replacement=r"\1りました。",
            priority=50,
            risk_level="high",
        ),
        # 〜いた。 → 〜きました。 (書いた、聞いた等)
        # ただし「ていた」は除外済み
        TransformRule(
            name="いた→きました",
            pattern=r"(?<!て)(?<!で)([かきくけこ])いた。",
            replacement=r"\1きました。",
            priority=49,
            risk_level="high",
        ),
        # 〜した。 → 〜しました。 (話した、愛した等)
        TransformRule(
            name="した→しました",
            pattern=r"(?<!ま)(?<!で)した。",
            replacement="しました。",
            priority=48,
            risk_level="medium",
        ),
    ]

    def __init__(self, csv_path: Path = MASTER_CSV):
        self.csv_path = csv_path
        self.stats = NormalizationStats()

    def _protect_quotes(self, text: str) -> tuple[str, list[str]]:
        """引用（「」）を一時的にプレースホルダーに置換"""
        quotes = []
        pattern = r"「[^」]*」"

        def replace_quote(match):
            quotes.append(match.group(0))
            return f"__QUOTE_{len(quotes) - 1}__"

        protected = re.sub(pattern, replace_quote, text)
        return protected, quotes

    def _restore_quotes(self, text: str, quotes: list[str]) -> str:
        """プレースホルダーを引用に復元"""
        for i, quote in enumerate(quotes):
            text = text.replace(f"__QUOTE_{i}__", quote)
        return text

    def detect_issues(self, text: str) -> list[dict]:
        """テキスト内の丁寧語漏れを検出"""
        issues = []

        # 引用を保護
        protected_text, _ = self._protect_quotes(text)

        # 文に分割
        sentences = [s.strip() + "。" for s in re.split(r"[。]", protected_text) if s.strip()]

        for sent in sentences:
            for rule in self.TRANSFORM_RULES:
                if re.search(rule.pattern, sent):
                    # 該当箇所を抽出
                    match = re.search(rule.pattern, sent)
                    if match:
                        issues.append(
                            {
                                "rule_name": rule.name,
                                "pattern": rule.pattern,
                                "matched": match.group(0),
                                "sentence_preview": sent[-60:] if len(sent) > 60 else sent,
                                "risk_level": rule.risk_level,
                            }
                        )
                    break  # 1文につき1パターンのみ検出

        return issues

    def transform_text(self, text: str, max_risk: str = "medium", dry_run: bool = True) -> tuple[str, list[dict]]:
        """テキストを丁寧語に変換"""
        changes = []

        # 引用を保護
        protected_text, quotes = self._protect_quotes(text)

        # リスクレベルフィルタ
        risk_levels = {"low": 1, "medium": 2, "high": 3}
        max_risk_level = risk_levels.get(max_risk, 2)

        # ルールを優先度順に適用
        sorted_rules = sorted(self.TRANSFORM_RULES, key=lambda r: -r.priority)

        transformed = protected_text
        for rule in sorted_rules:
            if risk_levels.get(rule.risk_level, 1) > max_risk_level:
                continue  # リスクが高すぎるルールはスキップ

            # 変換前に検出
            matches = list(re.finditer(rule.pattern, transformed))
            if matches:
                for match in matches:
                    changes.append(
                        {
                            "rule_name": rule.name,
                            "before": match.group(0),
                            "after": re.sub(rule.pattern, rule.replacement, match.group(0)),
                            "position": match.start(),
                        }
                    )

                # 実際の変換
                if not dry_run:
                    transformed = re.sub(rule.pattern, rule.replacement, transformed)

        # 引用を復元
        result = self._restore_quotes(transformed, quotes) if not dry_run else text

        return result, changes

    def scan_all(self, limit: Optional[int] = None) -> list[DetectionResult]:
        """全エピソードをスキャン"""
        df = pd.read_csv(self.csv_path, encoding="utf-8-sig", low_memory=False)
        self.stats.total_episodes = len(df)

        results = []

        for idx, row in df.iterrows():
            if limit and idx >= limit:
                break

            episode_id = row.get("episode_id", "")
            person_name = row.get("person_name", "")
            text = str(row.get("episode_text", "") or "")

            if not text:
                continue

            self.stats.scanned_episodes += 1
            issues = self.detect_issues(text)

            if issues:
                self.stats.episodes_with_issues += 1
                self.stats.total_issues += len(issues)

                for issue in issues:
                    rule_name = issue["rule_name"]
                    self.stats.issues_by_pattern[rule_name] = self.stats.issues_by_pattern.get(rule_name, 0) + 1

                results.append(
                    DetectionResult(
                        episode_id=episode_id,
                        person_name=person_name,
                        original_text=text,
                        issues=issues,
                    )
                )

        return results

    def execute(self, max_risk: str = "medium", dry_run: bool = True) -> dict:
        """修正を実行"""
        # バックアップ作成
        if not dry_run:
            self._create_backup()

        df = pd.read_csv(self.csv_path, encoding="utf-8-sig", low_memory=False)
        self.stats.total_episodes = len(df)

        changes_log = []
        fixed_count = 0
        total_changes = 0

        for idx, row in df.iterrows():
            episode_id = row.get("episode_id", "")
            text = str(row.get("episode_text", "") or "")

            if not text:
                continue

            self.stats.scanned_episodes += 1

            transformed, changes = self.transform_text(text, max_risk=max_risk, dry_run=dry_run)

            if changes:
                self.stats.episodes_with_issues += 1
                total_changes += len(changes)

                if not dry_run:
                    df.at[idx, "episode_text"] = transformed
                    fixed_count += 1

                changes_log.append(
                    {
                        "episode_id": episode_id,
                        "changes": changes[:5],  # 最大5件の変更を記録
                        "total_changes": len(changes),
                    }
                )

        # 保存
        if not dry_run:
            df.to_csv(self.csv_path, index=False, encoding="utf-8-sig")
            self.stats.fixed_episodes = fixed_count
            self.stats.fixed_issues = total_changes

        return {
            "dry_run": dry_run,
            "max_risk": max_risk,
            "total_episodes": self.stats.total_episodes,
            "scanned": self.stats.scanned_episodes,
            "episodes_with_issues": self.stats.episodes_with_issues,
            "total_changes": total_changes,
            "fixed_episodes": fixed_count if not dry_run else 0,
            "changes_sample": changes_log[:20],  # 最大20件
        }

    def _create_backup(self):
        """バックアップ作成"""
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"MASTER_BACKUP_polite_{timestamp}.csv"
        shutil.copy(self.csv_path, backup_path)
        print(f"バックアップ作成: {backup_path}")
        return backup_path

    def generate_report(self, results: list[DetectionResult]) -> dict:
        """検出レポート生成"""
        report = {
            "report_id": f"POLITE-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_episodes": self.stats.total_episodes,
                "scanned_episodes": self.stats.scanned_episodes,
                "episodes_with_issues": self.stats.episodes_with_issues,
                "issue_rate": f"{self.stats.episodes_with_issues / self.stats.scanned_episodes * 100:.1f}%"
                if self.stats.scanned_episodes
                else "N/A",
                "total_issues": self.stats.total_issues,
            },
            "issues_by_pattern": dict(sorted(self.stats.issues_by_pattern.items(), key=lambda x: -x[1])),
            "sample_issues": [
                {
                    "episode_id": r.episode_id,
                    "person_name": r.person_name,
                    "issues": r.issues[:3],
                }
                for r in results[:20]
            ],
        }
        return report


def validate_single(text: str) -> list[str]:
    """単一テキストの検証（ゲート用）"""
    normalizer = PoliteFormNormalizer()
    issues = normalizer.detect_issues(text)
    return [f"{i['rule_name']}: {i['matched']}" for i in issues]


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="丁寧語漏れ検知・修正")
    parser.add_argument("--dry-run", action="store_true", help="ドライランモード（変更なし）")
    parser.add_argument("--execute", action="store_true", help="実行モード（変更あり）")
    parser.add_argument("--scan-only", action="store_true", help="検知のみ（修正なし）")
    parser.add_argument(
        "--max-risk",
        choices=["low", "medium", "high"],
        default="medium",
        help="適用するルールの最大リスクレベル",
    )
    parser.add_argument("--limit", type=int, help="スキャン件数制限")
    parser.add_argument("--output", type=str, help="レポート出力先")
    args = parser.parse_args()

    print("=== 丁寧語漏れ検知・修正 ===\n")

    normalizer = PoliteFormNormalizer()

    if args.scan_only:
        # 検知のみ
        print("スキャン中...")
        results = normalizer.scan_all(limit=args.limit)
        report = normalizer.generate_report(results)

        print(f"\n総エピソード: {report['summary']['total_episodes']}")
        print(f"問題検出: {report['summary']['episodes_with_issues']}件 ({report['summary']['issue_rate']})")
        print(f"総問題数: {report['summary']['total_issues']}")
        print("\nパターン別:")
        for pattern, count in list(report["issues_by_pattern"].items())[:10]:
            print(f"  {pattern}: {count}件")

        # レポート保存
        if args.output:
            output_path = Path(args.output)
        else:
            REPORTS_DIR.mkdir(parents=True, exist_ok=True)
            output_path = REPORTS_DIR / f"polite_form_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\nレポート保存: {output_path}")

    elif args.execute:
        # 実行モード
        print(f"実行モード（max_risk={args.max_risk}）")
        print("修正実行中...")
        result = normalizer.execute(max_risk=args.max_risk, dry_run=False)

        print("\n修正完了:")
        print(f"  対象: {result['episodes_with_issues']}件")
        print(f"  変更: {result['total_changes']}箇所")
        print(f"  修正済: {result['fixed_episodes']}件")

        # ログ保存
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        log_path = LOGS_DIR / f"polite_fix_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\nログ保存: {log_path}")

    else:
        # デフォルト: dry-run
        print(f"ドライランモード（max_risk={args.max_risk}）")
        print("シミュレーション中...")
        result = normalizer.execute(max_risk=args.max_risk, dry_run=True)

        print("\n結果（dry-run）:")
        print(f"  対象: {result['episodes_with_issues']}件")
        print(f"  変更予定: {result['total_changes']}箇所")

        print("\n変更サンプル（最大10件）:")
        for item in result["changes_sample"][:10]:
            print(f"  {item['episode_id']}:")
            for ch in item["changes"][:2]:
                print(f"    {ch['before']} → {ch['after']}")

        print("\n実行するには: python scripts/validation/polite_form_normalizer.py --execute")


if __name__ == "__main__":
    main()
