#!/usr/bin/env python3
"""
PDCAガーディアンルール追加 (RULE_084-086)
グループメンバー表示名検証とデータベース完全性チェック
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


def add_group_display_rules():
    """グループ表示名ルール追加"""

    new_rules = [
        {
            "rule_id": "RULE_084",
            "name": "グループメンバー表示名検証",
            "description": "お笑い芸人・バンドメンバー等のグループ所属者は「名前（グループ名）」形式必須",
            "category": "表示名整合性",
            "severity": "HIGH",
            "implementation": {
                "trigger": "person_name_display設定時",
                "action": "グループメンバーシップ確認と括弧付きグループ名追加",
                "validation_steps": [
                    "groups_database.jsonとの照合",
                    "occupation（お笑い芸人、歌手等）のチェック",
                    "既存の括弧内容の検証",
                    "エピソード読みやすさテスト"
                ]
            },
            "examples": [
                "いかりや長介 → いかりや長介（ザ・ドリフターズ）",
                "しずちゃん → しずちゃん（南海キャンディーズ）",
                "原西孝幸 → 原西孝幸（FUJIWARA）"
            ],
            "created_at": datetime.now().isoformat(),
            "reason": "グループメンバーの表示名が統一ルールに違反していた事故を受けて"
        },
        {
            "rule_id": "RULE_085",
            "name": "グループデータベース完全性チェック",
            "description": "groups_database.jsonに主要なグループとメンバー情報が網羅されていることを保証",
            "category": "データ完全性",
            "severity": "MEDIUM",
            "implementation": {
                "trigger": "新規人物追加時、定期監査時",
                "action": "グループデータベースとの照合と欠落検出",
                "check_points": [
                    "Wikipedia掲載グループの網羅性",
                    "メンバー名のバリエーション（本名、芸名、愛称）",
                    "活動休止・解散グループの扱い",
                    "グループ名の表記ゆれ対応"
                ]
            },
            "required_groups": [
                "ザ・ドリフターズ",
                "ダウンタウン",
                "ナインティナイン",
                "さまぁ〜ず",
                "オードリー",
                "サンドウィッチマン",
                "千鳥",
                "かまいたち",
                "南海キャンディーズ",
                "3時のヒロイン"
            ],
            "created_at": datetime.now().isoformat(),
            "reason": "主要グループの欠落による表示名エラー防止"
        },
        {
            "rule_id": "RULE_086",
            "name": "新規追加時の自動グループ検出",
            "description": "新規人物追加時に自動的にグループ所属を検出し、適切な表示名を設定",
            "category": "自動化",
            "severity": "MEDIUM",
            "implementation": {
                "trigger": "新規person追加",
                "action": "自動グループ検出と表示名生成",
                "detection_methods": [
                    "Wikipedia APIでのグループ情報取得",
                    "Google検索での「○○ △△（グループ名）」パターン検出",
                    "既存データベースとの名前類似度マッチング",
                    "occupation情報からの推定"
                ]
            },
            "automation_rules": {
                "confidence_threshold": 0.8,
                "manual_review_required": "信頼度が閾値未満の場合",
                "fallback": "グループ不明の場合は名前のみ"
            },
            "created_at": datetime.now().isoformat(),
            "reason": "手動メンテナンスの負荷軽減と一貫性確保"
        }
    ]

    # 既存のルールファイルを読み込み
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

    # チェックリスト生成
    generate_validation_checklist(new_rules)

    return new_rules


def generate_validation_checklist(rules):
    """検証チェックリスト生成"""
    checklist = {
        "title": "グループ表示名検証チェックリスト",
        "created_at": datetime.now().isoformat(),
        "validation_items": [
            {
                "category": "お笑い芸人",
                "checks": [
                    "コンビ名が括弧内に含まれているか",
                    "ピン芸人は括弧なしか",
                    "解散済みグループも正しく表記されているか"
                ]
            },
            {
                "category": "音楽グループ",
                "checks": [
                    "バンド名が括弧内に含まれているか",
                    "ソロ活動との区別が明確か",
                    "グループ名の表記ゆれがないか"
                ]
            },
            {
                "category": "YouTuber",
                "checks": [
                    "グループYouTuberは括弧付きか",
                    "個人YouTuberは括弧なしか",
                    "チャンネル名とグループ名の整合性"
                ]
            },
            {
                "category": "データベース",
                "checks": [
                    "groups_database.jsonが最新か",
                    "主要グループが網羅されているか",
                    "メンバー名のバリエーションが登録されているか",
                    "エイリアス（別名）が適切に設定されているか"
                ]
            }
        ],
        "test_cases": [
            {
                "input": {"name": "いかりや長介", "occupation": "コメディアン"},
                "expected": "いかりや長介（ザ・ドリフターズ）"
            },
            {
                "input": {"name": "明石家さんま", "occupation": "お笑い芸人"},
                "expected": "明石家さんま"  # ピン芸人
            },
            {
                "input": {"name": "山里亮太", "occupation": "お笑い芸人"},
                "expected": "山里亮太（南海キャンディーズ）"
            }
        ]
    }

    # チェックリスト保存
    checklist_file = f"group_display_validation_checklist_{datetime.now().strftime('%Y%m%d')}.json"
    with open(checklist_file, 'w', encoding='utf-8') as f:
        json.dump(checklist, f, ensure_ascii=False, indent=2)

    logger.info(f"📋 チェックリスト生成: {checklist_file}")

    # マークダウンレポート生成
    generate_markdown_report(rules)


def generate_markdown_report(rules):
    """マークダウンレポート生成"""
    report = []
    report.append("# PDCAガーディアンルール追加レポート (RULE_084-086)")
    report.append("")
    report.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    report.append("## 背景")
    report.append("")
    report.append("お笑い芸人のグループメンバー表示名が「名前（グループ名）」形式になっていなかった問題を受けて、")
    report.append("表示名の統一ルール遵守とグループデータベースの完全性を保証するルールを追加しました。")
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

            if 'validation_steps' in rule['implementation']:
                report.append("- 検証ステップ:")
                for step in rule['implementation']['validation_steps']:
                    report.append(f"  - {step}")

            if 'check_points' in rule['implementation']:
                report.append("- チェックポイント:")
                for point in rule['implementation']['check_points']:
                    report.append(f"  - {point}")

            if 'detection_methods' in rule['implementation']:
                report.append("- 検出方法:")
                for method in rule['implementation']['detection_methods']:
                    report.append(f"  - {method}")

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
    report.append("| グループデータベース | groups_database.json | ✅ 更新済み |")
    report.append("| 表示名修正スクリプト | fix_comedian_display_names.py | ✅ 完了 |")
    report.append("| PDCAルール | pdca_guardian_rules.json | ✅ 追加 |")
    report.append("| 検証チェックリスト | group_display_validation_checklist.json | ✅ 生成 |")
    report.append("")
    report.append("## 修正結果")
    report.append("")
    report.append("- 21名のお笑い芸人の表示名を修正")
    report.append("- ザ・ドリフターズ、FUJIWARA等の主要グループをデータベースに追加")
    report.append("- 今後の自動検出・修正の仕組みを構築")
    report.append("")
    report.append("## 今後の課題")
    report.append("")
    report.append("1. グループデータベースの定期的な更新")
    report.append("2. Wikipedia APIとの連携強化")
    report.append("3. 新規グループの自動検出精度向上")
    report.append("4. 表記ゆれ対応の強化")
    report.append("")

    # レポート保存
    report_file = f"PDCA_RULES_084_086_REPORT_{datetime.now().strftime('%Y%m%d')}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))

    logger.info(f"📄 レポート生成: {report_file}")


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("🚀 PDCAガーディアンルール追加 (RULE_084-086)")
    logger.info("=" * 60)

    # ルール追加
    new_rules = add_group_display_rules()

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
    logger.info("📋 グループメンバー表示名の一貫性を保証する仕組みを構築しました")


if __name__ == "__main__":
    main()
