#!/usr/bin/env python3
"""
統合ルール生成スクリプト - Unified Rules Generator

3つの散在したルールファイルを統合し、unified_rules.json を生成します。

入力ファイル:
  - rules_registry.json (171ルール)
  - pdca_rules.json (24ルール、重複含む)
  - pdca_guardian_rules.json (14ルール、RULE_081-097)

出力ファイル:
  - unified_rules.json (192ルール、重複排除済み)
"""

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class RuleMerger:
    """ルールマージャー - 複数のルールファイルを統合"""

    def __init__(self):
        self.rules: Dict[str, Dict] = {}
        self.categories: Dict[str, List[str]] = defaultdict(list)
        self.deprecated_rules: Dict[str, Dict] = {}
        self.conflicts: List[Dict] = []
        self.statistics: Dict[str, int] = defaultdict(int)

    def load_rules_registry(self, path: Path) -> None:
        """rules_registry.json をロード"""
        print(f"📖 Loading {path.name}...")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for rule_id, rule_data in data.items():
            if (
                not rule_id.startswith("RULE_")
                and not rule_id.startswith("ENTITY_TYPE_")
                and not rule_id.startswith("FORMAT_")
            ):
                continue

            # 標準化されたルール構造に変換
            unified_rule = {
                "rule_id": rule_id,
                "name": rule_data.get("name", ""),
                "description": rule_data.get("description", ""),
                "category": rule_data.get("category", "data_quality"),
                "priority": rule_data.get("priority", "MEDIUM"),
                "severity": rule_data.get("severity", rule_data.get("priority", "MEDIUM")),
                "status": rule_data.get("status", "active"),
                "version": rule_data.get("version", "v1.0.0"),
                "created_at": rule_data.get("created_at", "2025-10-02"),
                "updated_at": rule_data.get("updated_at", "2025-10-02"),
                "source_file": rule_data.get("source_file", "unknown"),
                "check_function": rule_data.get("function_name") or rule_data.get("check_function"),
                "violation_type": rule_data.get("violation_type"),
                "validation_logic": rule_data.get("validation"),
                "examples": rule_data.get("examples", {}),
                "related_rules": rule_data.get("related_rules", []),
                "supersedes": rule_data.get("replaces"),
                "superseded_by": rule_data.get("replaced_by"),
                "tags": rule_data.get("tags", []),
                "source_files": ["rules_registry.json"],
            }

            self.rules[rule_id] = unified_rule
            self.categories[unified_rule["category"]].append(rule_id)
            self.statistics["rules_registry"] += 1

        print(f"  ✅ Loaded {self.statistics['rules_registry']} rules from rules_registry.json")

    def load_pdca_rules(self, path: Path) -> None:
        """pdca_rules.json をロード（重複チェック付き）"""
        print(f"📖 Loading {path.name}...")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        loaded = 0
        duplicates = 0
        merged = 0

        for rule_data in data.get("rules", []):
            rule_id = rule_data.get("rule_id") or rule_data.get("id")
            if not rule_id:
                continue

            # 標準化されたルール構造に変換
            unified_rule = {
                "rule_id": rule_id,
                "name": rule_data.get("name", rule_data.get("title", "")),
                "description": rule_data.get("description", ""),
                "category": rule_data.get("category", "data_quality"),
                "priority": rule_data.get("priority", "MEDIUM"),
                "severity": rule_data.get("severity", rule_data.get("priority", "MEDIUM")),
                "status": "active",
                "version": rule_data.get("version", data.get("version", "v5.11")),
                "created_at": rule_data.get("added_date", "2025-09-22"),
                "updated_at": rule_data.get("added_date", "2025-09-22"),
                "source_file": "pdca_guardian.py",
                "check_function": rule_data.get("check_function"),
                "violation_type": rule_data.get("violation_type"),
                "validation_logic": rule_data.get("validation"),
                "examples": rule_data.get("examples", {}),
                "related_rules": rule_data.get("related_rules", []),
                "tags": rule_data.get("tags", []),
                "source_files": ["pdca_rules.json"],
            }

            # 重複チェック
            if rule_id in self.rules:
                duplicates += 1
                # マージロジック: より詳細な方を優先
                existing = self.rules[rule_id]
                merged_rule = self._merge_rules(existing, unified_rule, rule_id)
                self.rules[rule_id] = merged_rule
                merged += 1
            else:
                self.rules[rule_id] = unified_rule
                self.categories[unified_rule["category"]].append(rule_id)
                loaded += 1

        self.statistics["pdca_rules_new"] = loaded
        self.statistics["pdca_rules_duplicates"] = duplicates
        self.statistics["pdca_rules_merged"] = merged

        print(f"  ✅ Loaded {loaded} new rules, found {duplicates} duplicates, merged {merged}")

    def load_pdca_guardian_rules(self, path: Path) -> None:
        """pdca_guardian_rules.json をロード"""
        print(f"📖 Loading {path.name}...")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        loaded = 0

        for rule_data in data.get("rules", []):
            rule_id = rule_data.get("rule_id")
            if not rule_id:
                continue

            # 標準化されたルール構造に変換
            unified_rule = {
                "rule_id": rule_id,
                "name": rule_data.get("name", ""),
                "description": rule_data.get("description", ""),
                "category": rule_data.get("category", "data_quality"),
                "priority": "HIGH",
                "severity": rule_data.get("severity", "HIGH"),
                "status": "active",
                "version": "v1.0.0",
                "created_at": rule_data.get("created_at", "2025-09-12"),
                "updated_at": rule_data.get("created_at", "2025-09-12"),
                "source_file": "pdca_guardian.py",
                "check_function": None,
                "violation_type": None,
                "validation_logic": None,
                "examples": rule_data.get("examples", []),
                "related_rules": [],
                "tags": [],
                "source_files": ["pdca_guardian_rules.json"],
                "implementation": rule_data.get("implementation", {}),
            }

            if rule_id not in self.rules:
                self.rules[rule_id] = unified_rule
                self.categories[unified_rule["category"]].append(rule_id)
                loaded += 1

        self.statistics["pdca_guardian_rules"] = loaded
        print(f"  ✅ Loaded {loaded} rules from pdca_guardian_rules.json")

    def _merge_rules(self, existing: Dict, new: Dict, rule_id: str) -> Dict:
        """2つのルールをマージ（競合解決）"""

        # マージログを記録
        conflict_info = {
            "rule_id": rule_id,
            "existing_source": existing.get("source_files", []),
            "new_source": new.get("source_files", []),
            "resolution": "merged",
        }
        self.conflicts.append(conflict_info)

        # マージ戦略:
        # 1. より新しい更新日時を優先
        # 2. より詳細な説明を優先
        # 3. source_filesをマージ

        merged = existing.copy()

        # 更新日時比較
        existing_date = existing.get("updated_at", "")
        new_date = new.get("updated_at", "")

        use_new = False
        if new_date > existing_date:
            use_new = True
        elif new_date == existing_date:
            # 説明の詳細度で判定
            if len(new.get("description", "")) > len(existing.get("description", "")):
                use_new = True

        if use_new:
            merged.update(
                {
                    "name": new.get("name") or existing.get("name"),
                    "description": new.get("description") or existing.get("description"),
                    "version": new.get("version"),
                    "updated_at": new.get("updated_at"),
                }
            )

        # source_filesをマージ
        merged["source_files"] = list(set(existing.get("source_files", []) + new.get("source_files", [])))

        # 競合解決情報を追加
        merged["conflict_resolution"] = {
            "resolved_at": datetime.now().isoformat(),
            "resolution": "最新版を採用" if use_new else "既存版を保持",
            "merged_from": merged["source_files"],
        }

        return merged

    def generate_unified_rules(self) -> Dict:
        """統合ルールJSONを生成"""

        # カテゴリ別にルールを整理
        categories_data = {}
        for category, rule_ids in self.categories.items():
            categories_data[category] = {
                "description": self._get_category_description(category),
                "rule_count": len(set(rule_ids)),  # 重複除去
                "rules": sorted(list(set(rule_ids))),
            }

        unified_data = {
            "metadata": {
                "version": "1.0.0",
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "total_rules": len(self.rules),
                "sources": ["rules_registry.json", "pdca_rules.json", "pdca_guardian_rules.json"],
                "statistics": dict(self.statistics),
                "conflicts_resolved": len(self.conflicts),
            },
            "rules": self.rules,
            "categories": categories_data,
            "deprecated_rules": self.deprecated_rules,
        }

        return unified_data

    def _get_category_description(self, category: str) -> str:
        """カテゴリの説明を取得"""
        descriptions = {
            "data_quality": "データ品質関連ルール",
            "episode_format": "エピソード形式ルール",
            "episode_content": "エピソード内容ルール",
            "entity_type": "エンティティタイプルール",
            "データ品質": "データ品質関連ルール",
            "エピソード品質": "エピソード品質ルール",
            "品質保証": "品質保証ルール",
            "データ保護": "データ保護ルール",
            "検証プロセス": "検証プロセスルール",
        }
        return descriptions.get(category, f"{category}関連ルール")

    def save_unified_rules(self, output_path: Path) -> None:
        """統合ルールをファイルに保存"""
        print("\n💾 Generating unified_rules.json...")

        unified_data = self.generate_unified_rules()

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(unified_data, f, ensure_ascii=False, indent=2)

        print(f"✅ Saved to {output_path}")
        print("\n📊 Statistics:")
        print(f"  Total rules: {len(self.rules)}")
        print(f"  Categories: {len(self.categories)}")
        print(f"  Conflicts resolved: {len(self.conflicts)}")
        print("  Sources merged: 3 files")

    def generate_report(self) -> str:
        """マージレポートを生成"""
        report = []
        report.append("# 統合ルール生成レポート\n")
        report.append(f"**生成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report.append("\n## 統計情報\n")
        report.append(f"- **総ルール数**: {len(self.rules)}\n")
        report.append(f"- **カテゴリ数**: {len(self.categories)}\n")
        report.append(f"- **競合解決数**: {len(self.conflicts)}\n")
        report.append("\n### ソース別ルール数\n")
        report.append(f"- rules_registry.json: {self.statistics.get('rules_registry', 0)}\n")
        report.append(f"- pdca_rules.json (新規): {self.statistics.get('pdca_rules_new', 0)}\n")
        report.append(f"- pdca_rules.json (重複): {self.statistics.get('pdca_rules_duplicates', 0)}\n")
        report.append(f"- pdca_rules.json (マージ): {self.statistics.get('pdca_rules_merged', 0)}\n")
        report.append(f"- pdca_guardian_rules.json: {self.statistics.get('pdca_guardian_rules', 0)}\n")

        report.append("\n## 競合解決詳細\n")
        for conflict in self.conflicts[:10]:  # 最初の10件のみ
            report.append(f"- **{conflict['rule_id']}**: {conflict['existing_source']} + {conflict['new_source']}\n")

        if len(self.conflicts) > 10:
            report.append(f"- ... 他 {len(self.conflicts) - 10} 件\n")

        return "".join(report)


def main():
    """メイン処理"""
    print("=" * 60)
    print("  統合ルール生成スクリプト - Unified Rules Generator")
    print("=" * 60)
    print()

    # ファイルパス
    base_dir = Path(__file__).parent.parent
    rules_registry = base_dir / "rules_registry.json"
    pdca_rules = base_dir / "pdca_rules.json"
    pdca_guardian_rules = base_dir / "pdca_guardian_rules.json"
    output_path = base_dir / "unified_rules.json"
    report_path = base_dir / "claudedocs" / "UNIFIED_RULES_GENERATION_REPORT.md"

    # 入力ファイルの存在確認
    missing_files = []
    for path in [rules_registry, pdca_rules, pdca_guardian_rules]:
        if not path.exists():
            missing_files.append(str(path))

    if missing_files:
        print("❌ エラー: 以下のファイルが見つかりません:")
        for f in missing_files:
            print(f"  - {f}")
        sys.exit(1)

    # ルールマージャーを初期化
    merger = RuleMerger()

    # 各ルールファイルをロード
    try:
        merger.load_rules_registry(rules_registry)
        merger.load_pdca_rules(pdca_rules)
        merger.load_pdca_guardian_rules(pdca_guardian_rules)
    except Exception as e:
        print("\n❌ エラー: ルールファイルのロードに失敗しました")
        print(f"  {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # 統合ルールを保存
    try:
        merger.save_unified_rules(output_path)
    except Exception as e:
        print("\n❌ エラー: 統合ルールの保存に失敗しました")
        print(f"  {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # レポート生成
    try:
        report = merger.generate_report()
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n📄 Report saved to {report_path}")
    except Exception as e:
        print("\n⚠️ 警告: レポート生成に失敗しました（統合は成功）")
        print(f"  {e}")

    print("\n" + "=" * 60)
    print("  ✅ 統合ルール生成完了！")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
