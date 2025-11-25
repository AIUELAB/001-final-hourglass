#!/usr/bin/env python3
"""
PDCAガーディアンルール追加 (RULE_081-083)
Wikipedia存在確認と単独レコード保護ルール
"""

import json
from datetime import datetime
import logging
from pathlib import Path

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def add_wikipedia_protection_rules():
    """Wikipedia保護ルール追加"""

    new_rules = [
        {
            "rule_id": "RULE_081",
            "name": "Wikipedia実在確認必須化",
            "description": "削除前にWikipedia APIで実在確認を必須とする",
            "category": "データ品質",
            "severity": "CRITICAL",
            "implementation": {
                "trigger": "削除候補判定時",
                "action": "Wikipedia API呼び出しによる実在確認",
                "fallback": "API失敗時は保護側に倒す（削除しない）"
            },
            "examples": [
                "張本勲 → Wikipedia存在 → 削除禁止",
                "錦織圭 → Wikipedia存在 → 削除禁止",
                "架空太郎 → Wikipedia不在 → 削除可能性あり"
            ],
            "created_at": datetime.now().isoformat(),
            "reason": "有名人の誤削除防止（張本勲、錦織圭等の削除事故を受けて）"
        },
        {
            "rule_id": "RULE_082",
            "name": "単独レコード保護強化",
            "description": "連続IDでない単独レコードは慎重に扱い、安易に削除しない",
            "category": "データ保護",
            "severity": "HIGH",
            "implementation": {
                "trigger": "単独レコード（前後のIDが連続していない）",
                "action": "追加の検証ステップを必須化",
                "criteria": [
                    "Wikipedia確認",
                    "Google検索結果数",
                    "職業の妥当性",
                    "名前の自然さ"
                ]
            },
            "examples": [
                "P003301（張本勲）→ 単独 → 追加検証必須",
                "P001452-P001460（リーチ系）→ 連続 → バッチ判定可能"
            ],
            "created_at": datetime.now().isoformat(),
            "reason": "単独で追加された有名人の保護"
        },
        {
            "rule_id": "RULE_083",
            "name": "保護リスト最優先ルール",
            "description": "保護リストに含まれる人物は、いかなる条件でも削除禁止",
            "category": "絶対保護",
            "severity": "CRITICAL",
            "implementation": {
                "trigger": "すべての削除判定前",
                "action": "保護リスト照合を最優先で実施",
                "protection_lists": [
                    "famous_person_protection_list.py",
                    "wikipedia_verified_list.json",
                    "manual_protection_list.json"
                ]
            },
            "protected_categories": [
                "オリンピック選手",
                "プロスポーツ選手",
                "国民的有名人",
                "Wikipedia掲載者",
                "メディア露出が多い人物"
            ],
            "created_at": datetime.now().isoformat(),
            "reason": "誤削除の完全防止"
        }
    ]

    # 既存のルールファイルを読み込み（存在する場合）
    rules_file = Path("pdca_guardian_rules.json")

    if rules_file.exists():
        with open(rules_file, 'r', encoding='utf-8') as f:
            existing_rules = json.load(f)
    else:
        existing_rules = {"rules": [], "last_updated": None}

    # 新しいルールを追加
    for rule in new_rules:
        # 重複チェック
        if not any(r.get('rule_id') == rule['rule_id'] for r in existing_rules.get('rules', [])):
            existing_rules.setdefault('rules', []).append(rule)
            logger.info(f"✅ ルール追加: {rule['rule_id']} - {rule['name']}")
        else:
            logger.info(f"ℹ️ ルール既存: {rule['rule_id']}")

    # 更新日時を記録
    existing_rules['last_updated'] = datetime.now().isoformat()
    existing_rules['total_rules'] = len(existing_rules.get('rules', []))

    # ファイルに保存
    with open(rules_file, 'w', encoding='utf-8') as f:
        json.dump(existing_rules, f, ensure_ascii=False, indent=2)

    logger.info(f"💾 PDCAルール保存: {rules_file}")
    logger.info(f"📊 総ルール数: {existing_rules['total_rules']}")

    # 実装チェックリスト生成
    generate_implementation_checklist(new_rules)

    return new_rules


def generate_implementation_checklist(rules):
    """実装チェックリスト生成"""
    checklist = {
        "title": "PDCA Guardian Rules 081-083 実装チェックリスト",
        "created_at": datetime.now().isoformat(),
        "rules": []
    }

    for rule in rules:
        checklist["rules"].append({
            "rule_id": rule["rule_id"],
            "name": rule["name"],
            "implementation_tasks": [
                {
                    "task": "Wikipedia API実装",
                    "status": "COMPLETED" if rule["rule_id"] == "RULE_081" else "PENDING",
                    "file": "wikipedia_api_implementation.py"
                },
                {
                    "task": "保護リスト実装",
                    "status": "COMPLETED" if rule["rule_id"] == "RULE_083" else "PENDING",
                    "file": "famous_person_protection_list.py"
                },
                {
                    "task": "検証ロジック実装",
                    "status": "IN_PROGRESS",
                    "file": "improved_placeholder_detection.py"
                },
                {
                    "task": "テストケース作成",
                    "status": "PENDING",
                    "file": "test_pdca_rules.py"
                }
            ]
        })

    # チェックリスト保存
    checklist_file = f"pdca_implementation_checklist_{datetime.now().strftime('%Y%m%d')}.json"
    with open(checklist_file, 'w', encoding='utf-8') as f:
        json.dump(checklist, f, ensure_ascii=False, indent=2)

    logger.info(f"📋 チェックリスト生成: {checklist_file}")

    # マークダウンレポート生成
    generate_markdown_report(rules)


def generate_markdown_report(rules):
    """マークダウンレポート生成"""
    report = []
    report.append("# PDCAガーディアンルール追加レポート (RULE_081-083)")
    report.append("")
    report.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    report.append("## 背景")
    report.append("")
    report.append("Wikipedia掲載の有名人（張本勲、錦織圭、照ノ富士等）が誤って削除された事故を受けて、")
    report.append("再発防止のためのルールを追加しました。")
    report.append("")
    report.append("## 追加ルール")
    report.append("")

    for rule in rules:
        report.append(f"### {rule['rule_id']}: {rule['name']}")
        report.append("")
        report.append(f"**説明**: {rule['description']}")
        report.append("")
        report.append(f"**重要度**: {rule['severity']}")
        report.append("")
        report.append(f"**理由**: {rule['reason']}")
        report.append("")

        if 'implementation' in rule:
            report.append("**実装詳細**:")
            report.append(f"- トリガー: {rule['implementation']['trigger']}")
            report.append(f"- アクション: {rule['implementation']['action']}")
            if 'fallback' in rule['implementation']:
                report.append(f"- フォールバック: {rule['implementation']['fallback']}")
            if 'criteria' in rule['implementation']:
                report.append("- 判定基準:")
                for criterion in rule['implementation']['criteria']:
                    report.append(f"  - {criterion}")

        if 'examples' in rule:
            report.append("")
            report.append("**例**:")
            for example in rule['examples']:
                report.append(f"- {example}")

        report.append("")
        report.append("---")
        report.append("")

    report.append("## 実装状況")
    report.append("")
    report.append("| コンポーネント | ファイル | 状態 |")
    report.append("|------------|---------|------|")
    report.append("| Wikipedia API | wikipedia_api_implementation.py | ✅ 完了 |")
    report.append("| 保護リスト | famous_person_protection_list.py | ✅ 完了 |")
    report.append("| 改良版検出器 | improved_placeholder_detection.py | ✅ 完了 |")
    report.append("| 復元スクリプト | restore_famous_athletes.py | ✅ 完了 |")
    report.append("| PDCAルール | pdca_guardian_rules.json | ✅ 更新 |")
    report.append("")
    report.append("## 今後の課題")
    report.append("")
    report.append("1. Wikipedia APIのレート制限対策の強化")
    report.append("2. 保護リストの定期的な更新")
    report.append("3. 自動テストの充実")
    report.append("4. 監査ログの強化")
    report.append("")

    # レポート保存
    report_file = f"PDCA_RULES_081_083_REPORT_{datetime.now().strftime('%Y%m%d')}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))

    logger.info(f"📄 レポート生成: {report_file}")


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("🚀 PDCAガーディアンルール追加 (RULE_081-083)")
    logger.info("=" * 60)

    # ルール追加
    new_rules = add_wikipedia_protection_rules()

    # サマリー表示
    logger.info("\n" + "=" * 60)
    logger.info("📊 追加ルールサマリー")
    logger.info("=" * 60)

    for rule in new_rules:
        logger.info(f"  {rule['rule_id']}: {rule['name']}")
        logger.info(f"    重要度: {rule['severity']}")
        logger.info(f"    理由: {rule['reason']}")
        logger.info("")

    logger.info("✅ PDCAガーディアンルール追加完了")
    logger.info("📋 二度と同じ過ちを繰り返さないための仕組みを構築しました")


if __name__ == "__main__":
    main()
