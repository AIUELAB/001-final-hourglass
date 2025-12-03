#!/usr/bin/env python3
"""
MasterUpdater - マスタデータ自動更新機能

機能:
1. 新エンティティ検出
2. グループ分散ルール自動提案
3. 更新適用（信頼度閾値付き）
4. 変更差分表示
5. バックアップ自動作成
"""

import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.group_master import (
    GROUP_ENTITIES,
    GROUP_MEMBER_MAP,
    DISPERSION_RULES,
    DispersionStrategy,
)


@dataclass
class NewEntity:
    """検出された新エンティティ"""

    name: str
    entity_type: str  # "group" or "member"
    detected_in: str  # エピソードID
    confidence: float
    suggested_action: str


@dataclass
class RuleProposal:
    """ルール提案"""

    group_name: str
    strategy: str
    members: list[str]
    confidence: float
    reason: str


class MasterUpdater:
    """マスタデータ更新クラス"""

    # グループ名パターン（日本語）
    GROUP_PATTERNS = [
        r".*グループ$",
        r".*バンド$",
        r".*ユニット$",
        r".*コンビ$",
        r".*トリオ$",
        r".*48$",
        r".*46$",
        r".*坂$",
    ]

    # メンバー連結パターン
    CONCAT_SEPARATORS = ["・", "（", "(", "／", "/"]

    def __init__(self, csv_path: str, min_confidence: float = 0.9):
        """
        初期化

        Args:
            csv_path: MASTER CSVパス
            min_confidence: 最小信頼度（デフォルト0.9）
        """
        self.csv_path = csv_path
        self.min_confidence = min_confidence
        self.df = pd.read_csv(csv_path)

    def detect_new_entities(self) -> list[NewEntity]:
        """
        新エンティティを検出

        Returns:
            新エンティティリスト
        """
        entities = []

        # 既知のグループ・メンバー
        known_groups = GROUP_ENTITIES
        known_members = set(GROUP_MEMBER_MAP.keys())

        for _, row in self.df.iterrows():
            person_name = str(row.get("person_name", ""))
            if not person_name or pd.isna(person_name):
                continue

            # 1. グループ名パターンに一致するが未登録
            for pattern in self.GROUP_PATTERNS:
                if re.match(pattern, person_name) and person_name not in known_groups:
                    entities.append(
                        NewEntity(
                            name=person_name,
                            entity_type="group",
                            detected_in=row.get("episode_id", "unknown"),
                            confidence=0.7,
                            suggested_action="GROUP_ENTITIESに追加し、DISPERSION_RULESを定義",
                        )
                    )
                    break

            # 2. 連結パターンで未知のグループを検出
            for sep in self.CONCAT_SEPARATORS:
                if sep in person_name:
                    parts = person_name.split(sep)
                    if len(parts) >= 2:
                        potential_group = parts[0].rstrip("）)")
                        if potential_group not in known_groups and len(potential_group) > 1:
                            entities.append(
                                NewEntity(
                                    name=potential_group,
                                    entity_type="group",
                                    detected_in=row.get("episode_id", "unknown"),
                                    confidence=0.5,
                                    suggested_action="GROUP_ENTITIESに追加検討",
                                )
                            )
                    break

        # 重複除去
        seen = set()
        unique_entities = []
        for e in entities:
            if e.name not in seen:
                seen.add(e.name)
                unique_entities.append(e)

        return unique_entities

    def propose_dispersion_rules(self) -> list[RuleProposal]:
        """
        分散ルールを提案

        Returns:
            ルール提案リスト
        """
        proposals = []

        # DISPERSION_RULES未定義のグループを検出
        undefined_groups = GROUP_ENTITIES - set(DISPERSION_RULES.keys())

        for group in undefined_groups:
            # GROUP_MEMBER_MAPから関連メンバーを収集
            members = [name for name, g in GROUP_MEMBER_MAP.items() if g == group]

            if members:
                # メンバー数に応じて戦略を提案
                if len(members) <= 5:
                    strategy = "ALL"
                    reason = f"メンバー{len(members)}名で全員分散が適切"
                else:
                    strategy = "REPRESENTATIVE"
                    reason = f"メンバー{len(members)}名で代表者分散を推奨"

                proposals.append(
                    RuleProposal(
                        group_name=group,
                        strategy=strategy,
                        members=members[:5],  # 最大5名
                        confidence=0.8,
                        reason=reason,
                    )
                )
            else:
                proposals.append(
                    RuleProposal(
                        group_name=group,
                        strategy="REPRESENTATIVE",
                        members=[],
                        confidence=0.3,
                        reason="メンバー情報なし、手動定義が必要",
                    )
                )

        return proposals

    def generate_diff(self, proposals: list[RuleProposal]) -> str:
        """
        変更差分を生成

        Args:
            proposals: ルール提案リスト

        Returns:
            差分文字列
        """
        lines = ["# Proposed Changes to group_master.py", ""]

        for p in proposals:
            if p.confidence >= self.min_confidence:
                lines.append(f"# {p.group_name} ({p.reason})")
                lines.append(f'"{p.group_name}": DispersionRule(')
                lines.append(f"    strategy=DispersionStrategy.{p.strategy},")
                lines.append(f"    members={p.members},")
                lines.append(f"    max_members={min(len(p.members), 3)},")
                lines.append("),")
                lines.append("")

        return "\n".join(lines)

    def apply_updates(self, proposals: list[RuleProposal], dry_run: bool = True) -> dict:
        """
        更新を適用

        Args:
            proposals: ルール提案リスト
            dry_run: ドライランモード

        Returns:
            適用結果
        """
        applied = []
        skipped = []

        for p in proposals:
            if p.confidence >= self.min_confidence:
                applied.append(
                    {
                        "group": p.group_name,
                        "strategy": p.strategy,
                        "members": p.members,
                        "confidence": p.confidence,
                    }
                )
            else:
                skipped.append(
                    {
                        "group": p.group_name,
                        "confidence": p.confidence,
                        "reason": f"信頼度 {p.confidence:.1%} < {self.min_confidence:.1%}",
                    }
                )

        result = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": dry_run,
            "applied": applied,
            "skipped": skipped,
            "diff": self.generate_diff(proposals),
        }

        if not dry_run and applied:
            # バックアップ作成
            group_master_path = Path(__file__).parent.parent / "group_master.py"
            backup_dir = Path(__file__).parent.parent.parent / "data" / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"group_master_{timestamp}.py.bak"
            shutil.copy(group_master_path, backup_path)
            result["backup_path"] = str(backup_path)

            # 注: 実際のファイル更新は手動で行う（安全のため）
            result["note"] = "ファイル更新は手動で行ってください。差分を参照してください。"

        return result


def main():
    """テスト実行"""
    import argparse

    parser = argparse.ArgumentParser(description="MasterUpdater")
    parser.add_argument(
        "--csv",
        default="preserved/data/MASTER_EPISODES_CURRENT.csv",
        help="対象CSVファイル",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.9,
        help="最小信頼度（デフォルト0.9）",
    )
    parser.add_argument(
        "--detect-only",
        action="store_true",
        help="検出のみ（更新提案しない）",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="更新を適用（要バックアップ確認）",
    )

    args = parser.parse_args()

    updater = MasterUpdater(args.csv, args.min_confidence)

    print("=" * 60)
    print("MasterUpdater - マスタデータ自動更新")
    print("=" * 60)

    # 新エンティティ検出
    print("\n🔍 新エンティティ検出...")
    entities = updater.detect_new_entities()
    print(f"  検出: {len(entities)}件")

    if entities:
        print("\n  新エンティティ:")
        for e in entities[:10]:
            print(f"    [{e.entity_type}] {e.name} (信頼度: {e.confidence:.1%})")
            print(f"      → {e.suggested_action}")
        if len(entities) > 10:
            print(f"    ... 他{len(entities) - 10}件")

    if args.detect_only:
        return

    # ルール提案
    print("\n🔧 分散ルール提案...")
    proposals = updater.propose_dispersion_rules()
    print(f"  提案: {len(proposals)}件")

    if proposals:
        high_conf = [p for p in proposals if p.confidence >= args.min_confidence]
        low_conf = [p for p in proposals if p.confidence < args.min_confidence]

        if high_conf:
            print(f"\n  高信頼度提案 ({len(high_conf)}件):")
            for p in high_conf[:5]:
                print(f"    {p.group_name}: {p.strategy} → {p.members}")
                print(f"      理由: {p.reason}")

        if low_conf:
            print(f"\n  低信頼度提案 ({len(low_conf)}件、手動確認推奨):")
            for p in low_conf[:5]:
                print(f"    {p.group_name}: 信頼度 {p.confidence:.1%}")

    # 更新適用
    if args.apply:
        print("\n📝 更新適用...")
        result = updater.apply_updates(proposals, dry_run=False)
        print(f"  適用: {len(result['applied'])}件")
        print(f"  スキップ: {len(result['skipped'])}件")
        if "backup_path" in result:
            print(f"  バックアップ: {result['backup_path']}")
    else:
        print("\n📝 差分プレビュー:")
        diff = updater.generate_diff(proposals)
        print(diff[:500] if len(diff) > 500 else diff)
        if len(diff) > 500:
            print("... (省略)")

        print("\n💡 実際に適用するには --apply オプションを使用してください")


if __name__ == "__main__":
    main()
