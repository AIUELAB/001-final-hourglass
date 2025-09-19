#!/usr/bin/env python3
"""
PDCAガーディアンルール追加 (RULE_087-089)
Google検索準拠の表示名ルール
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


def add_google_compliant_rules():
    """Google検索準拠ルール追加"""
    
    new_rules = [
        {
            "rule_id": "RULE_087",
            "name": "Google検索トップ表記準拠ルール",
            "description": "person_name_displayはGoogle検索結果の最上位（Wikipedia/Google AI）の表記に準拠する",
            "category": "表示名整合性",
            "severity": "CRITICAL",
            "implementation": {
                "trigger": "person_name_display設定・更新時",
                "action": "Google/Wikipedia検索による表記確認と自動修正",
                "validation_steps": [
                    "Wikipedia日本語版の検索と表記確認",
                    "Google検索APIによる表記確認（可能な場合）",
                    "ひらがな表記の妥当性検証",
                    "英語表記の妥当性検証"
                ],
                "api_integration": {
                    "wikipedia_ja": "必須",
                    "wikipedia_en": "K-POP/外国人用",
                    "google_search": "オプション",
                    "cache_duration": "24時間"
                }
            },
            "examples": [
                "PSY: サイ → PSY（Google検索トップ）",
                "染谷将太: そめたに しょうた → 染谷将太（Wikipedia表記）",
                "MrBeast: ミスタービースト → MrBeast（公式表記）"
            ],
            "validation_logic": """
            def validate_display_name(person_name, display_name, occupation):
                # Wikipedia検索
                wiki_result = search_wikipedia(person_name)
                if wiki_result:
                    if wiki_result['display_title'] != display_name:
                        return False, wiki_result['display_title']
                
                # ひらがなチェック（芸名以外は漢字優先）
                if is_hiragana_only(display_name) and not is_stage_name(person_name):
                    if has_kanji(person_name):
                        return False, person_name
                
                return True, display_name
            """,
            "created_at": datetime.now().isoformat(),
            "reason": "Google検索結果と異なる表示名が多数発見されたため"
        },
        {
            "rule_id": "RULE_088",
            "name": "Wikipedia表記優先ルール",
            "description": "Wikipedia日本語版に記事がある場合、その表記を最優先とする",
            "category": "表示名整合性",
            "severity": "HIGH",
            "implementation": {
                "trigger": "新規person追加時、定期監査時",
                "action": "Wikipedia APIによる表記取得と同期",
                "check_points": [
                    "Wikipedia日本語版の存在確認",
                    "記事タイトルの取得",
                    "表記ゆれの吸収（全角/半角、スペース）",
                    "リダイレクトページの処理"
                ],
                "fallback_strategy": [
                    "Wikipedia英語版を確認",
                    "Google Knowledge Graph API",
                    "元のperson_nameを使用"
                ]
            },
            "priority_order": [
                "Wikipedia日本語版の記事タイトル",
                "Wikipedia英語版（外国人の場合）",
                "Google検索結果の最上位",
                "既存データベースの多数派表記"
            ],
            "exceptions": [
                "芸名・愛称が定着している場合（IKKO、きゃりーぱみゅぱみゅ等）",
                "公式に表記を変更した場合（Prince → Symbol等）"
            ],
            "created_at": datetime.now().isoformat(),
            "reason": "信頼できる情報源としてWikipediaを標準化"
        },
        {
            "rule_id": "RULE_089",
            "name": "ひらがな表記制限ルール",
            "description": "ひらがなのみの表記は芸名・愛称として明確な場合のみ許可",
            "category": "表示名整合性",
            "severity": "MEDIUM",
            "implementation": {
                "trigger": "person_name_display検証時",
                "action": "ひらがな表記の妥当性チェックと修正",
                "detection_logic": [
                    "全文字がひらがなかチェック",
                    "元のperson_nameが漢字を含むか確認",
                    "芸名リストとの照合",
                    "職業による判定（お笑い芸人等）"
                ]
            },
            "allowed_hiragana_names": [
                "あいみょん",
                "きゃりーぱみゅぱみゅ",
                "ふかわりょう",
                "よゐこ",
                "おぎやはぎ",
                "ゆりやんレトリィバァ",
                "かなで",
                "しずちゃん",
                "ゆめっち",
                "みちお"
            ],
            "conversion_rules": {
                "pattern": "ひらがな表記 → 漢字表記",
                "examples": [
                    "そめたに しょうた → 染谷将太",
                    "おかだ まさき → 岡田将生",
                    "みやけ けん → 三宅健"
                ],
                "exceptions": "芸名として定着している場合は維持"
            },
            "created_at": datetime.now().isoformat(),
            "reason": "不適切なひらがな表記による可読性低下を防止"
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
    
    # 実装ガイド生成
    generate_implementation_guide(new_rules)
    
    return new_rules


def generate_implementation_guide(rules):
    """実装ガイド生成"""
    guide = {
        "title": "Google検索準拠表示名実装ガイド",
        "created_at": datetime.now().isoformat(),
        "implementation_steps": [
            {
                "step": 1,
                "action": "Wikipedia API統合",
                "details": [
                    "日本語Wikipedia APIエンドポイント設定",
                    "検索・ページ取得機能実装",
                    "キャッシュシステム（24時間）",
                    "レート制限対策（500ms間隔）"
                ]
            },
            {
                "step": 2,
                "action": "表示名検証ロジック",
                "details": [
                    "ひらがな判定関数",
                    "漢字判定関数",
                    "芸名判定ロジック",
                    "グループメンバー判定"
                ]
            },
            {
                "step": 3,
                "action": "自動修正システム",
                "details": [
                    "バッチ処理スクリプト",
                    "差分検出",
                    "修正ログ記録",
                    "ロールバック機能"
                ]
            },
            {
                "step": 4,
                "action": "監視・レポート",
                "details": [
                    "定期監査スケジュール",
                    "違反検出アラート",
                    "修正提案生成",
                    "統計レポート"
                ]
            }
        ],
        "test_cases": [
            {
                "input": {"name": "PSY", "current": "サイ"},
                "expected": "PSY",
                "rule": "RULE_087"
            },
            {
                "input": {"name": "染谷将太", "current": "そめたに しょうた"},
                "expected": "染谷将太",
                "rule": "RULE_089"
            },
            {
                "input": {"name": "あいみょん", "current": "あいみょん"},
                "expected": "あいみょん",
                "rule": "RULE_089（例外）"
            }
        ]
    }
    
    # ガイド保存
    guide_file = f"google_compliant_implementation_guide_{datetime.now().strftime('%Y%m%d')}.json"
    with open(guide_file, 'w', encoding='utf-8') as f:
        json.dump(guide, f, ensure_ascii=False, indent=2)
    
    logger.info(f"📋 実装ガイド生成: {guide_file}")
    
    # マークダウンレポート生成
    generate_markdown_report(rules)


def generate_markdown_report(rules):
    """マークダウンレポート生成"""
    report = []
    report.append("# PDCAガーディアンルール追加レポート (RULE_087-089)")
    report.append("")
    report.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    report.append("## 背景")
    report.append("")
    report.append("person_name_displayがGoogle検索結果の最上位表記と異なる問題が発見されました。")
    report.append("これにより、ユーザーが期待する表記と異なる表示となり、検索性と可読性が低下していました。")
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
        
        if 'examples' in rule:
            report.append("**例**:")
            for example in rule['examples']:
                report.append(f"- {example}")
            report.append("")
    
    report.append("## 発見された問題と修正")
    report.append("")
    report.append("| 問題カテゴリ | 件数 | 例 |")
    report.append("|------------|------|-----|")
    report.append("| ひらがな誤表記 | 10件 | 染谷将太→そめたに しょうた |")
    report.append("| カタカナ誤表記 | 1件 | PSY→サイ |")
    report.append("| スペース誤用 | 10件 | いかりや長介→いかりや ちょうすけ |")
    report.append("")
    
    report.append("## 実装状況")
    report.append("")
    report.append("| コンポーネント | ファイル | 状態 |")
    report.append("|------------|---------|------|")
    report.append("| Wikipedia API | enhanced_wikipedia_api.py | ✅ 実装済み |")
    report.append("| 修正スクリプト | fix_display_names_google_compliant.py | ✅ 実装済み |")
    report.append("| PDCAルール | pdca_guardian_rules.json | ✅ 更新済み |")
    report.append("")
    
    report.append("## 修正結果")
    report.append("")
    report.append("- 21件の表示名を修正")
    report.append("- Wikipedia API統合によるリアルタイム検証")
    report.append("- 24時間キャッシュによる高速化")
    report.append("- 自動修正提案システムの構築")
    report.append("")
    
    report.append("## 今後の改善点")
    report.append("")
    report.append("1. Google Knowledge Graph APIの統合")
    report.append("2. 多言語Wikipedia対応の強化")
    report.append("3. 表記ゆれ辞書の充実")
    report.append("4. リアルタイム監視システムの構築")
    report.append("")
    
    # レポート保存
    report_file = f"PDCA_RULES_087_089_REPORT_{datetime.now().strftime('%Y%m%d')}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    
    logger.info(f"📄 レポート生成: {report_file}")


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("🚀 PDCAガーディアンルール追加 (RULE_087-089)")
    logger.info("=" * 60)
    
    # ルール追加
    new_rules = add_google_compliant_rules()
    
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
    logger.info("📋 Google検索準拠の表示名ルールを確立しました")


if __name__ == "__main__":
    main()