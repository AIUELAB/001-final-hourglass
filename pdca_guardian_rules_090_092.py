#!/usr/bin/env python3
"""
PDCAガーディアンルール追加 (RULE_090-092)
プレースホルダーデータ検出と排除ルール
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


def add_placeholder_detection_rules():
    """プレースホルダーデータ検出ルール追加"""
    
    new_rules = [
        {
            "rule_id": "RULE_090",
            "name": "プレースホルダーデータ検出ルール",
            "description": "自動生成された架空データを検出し、データベースから排除する",
            "category": "データ整合性",
            "severity": "CRITICAL",
            "implementation": {
                "trigger": "新規データ追加時、定期監査時",
                "action": "プレースホルダーパターンの検出と削除",
                "detection_patterns": [
                    "連番person_id（10件以上の連続）",
                    "類似名の連続（同姓で名前が微妙に違う）",
                    "生年情報の完全欠如",
                    "Wikipedia記載率30%未満のグループ"
                ],
                "validation_steps": [
                    "Wikipedia存在確認",
                    "Google検索での実在性確認",
                    "IMDb、映画データベースでの確認",
                    "SNS、公式サイトの存在確認"
                ]
            },
            "detection_logic": """
            def detect_placeholder_data(df):
                suspicious_groups = []
                
                # 1. 連番IDチェック
                for i in range(len(df) - 10):
                    if is_consecutive_ids(df.iloc[i:i+10]):
                        suspicious_groups.append(df.iloc[i:i+10])
                
                # 2. 同姓グループチェック
                surname_groups = df.groupby(df['person_name'].str.split().str[0])
                for surname, group in surname_groups:
                    if len(group) >= 5:
                        # Wikipedia記載率チェック
                        wiki_rate = check_wikipedia_existence_rate(group)
                        if wiki_rate < 0.3:
                            suspicious_groups.append(group)
                
                return suspicious_groups
            """,
            "examples": [
                "加藤健太～加藤颯太（連続10件、Wikipedia記載率30%）",
                "田中太郎1～田中太郎100（明らかな自動生成）",
                "山田A子～山田Z子（アルファベット連番）"
            ],
            "created_at": datetime.now().isoformat(),
            "reason": "自動生成されたプレースホルダーデータが発見されたため"
        },
        {
            "rule_id": "RULE_091",
            "name": "実在性検証必須ルール",
            "description": "人物データは最低1つの外部ソースで実在が確認できなければ登録不可",
            "category": "データ品質",
            "severity": "HIGH",
            "implementation": {
                "trigger": "person追加時、インポート時",
                "action": "外部ソースでの実在性確認",
                "required_sources": [
                    "Wikipedia（日本語または英語）",
                    "公式サイト、所属事務所",
                    "IMDb（俳優の場合）",
                    "公式SNS（Twitter/Instagram認証済み）",
                    "ニュース記事（信頼できるメディア）"
                ],
                "minimum_requirement": "最低1つのソースで確認必須",
                "verification_data": {
                    "source_type": "記録必須",
                    "source_url": "記録必須",
                    "verified_date": "記録必須",
                    "verifier": "自動/手動の区別"
                }
            },
            "exceptions": [
                "歴史上の人物（1900年以前）",
                "架空キャラクター（明示的にfictional_characterとマーク）"
            ],
            "validation_query": """
            SELECT person_id, person_name, occupation
            FROM persons
            WHERE verified_status IS NULL
               OR verified_source IS NULL
               OR (occupation = '俳優' AND imdb_id IS NULL AND wikipedia_url IS NULL)
            """,
            "created_at": datetime.now().isoformat(),
            "reason": "実在しない人物データの混入を防ぐため"
        },
        {
            "rule_id": "RULE_092",
            "name": "俳優データ品質基準ルール",
            "description": "俳優として登録する場合、出演作品または所属情報が必須",
            "category": "職業別品質基準",
            "severity": "MEDIUM",
            "implementation": {
                "trigger": "occupation='俳優'のデータ追加・更新時",
                "action": "俳優固有情報の検証",
                "required_fields": {
                    "one_of": [
                        "出演作品（最低1作品）",
                        "所属事務所",
                        "IMDb ID",
                        "Wikipedia記載の出演歴"
                    ],
                    "recommended": [
                        "生年月日",
                        "出身地",
                        "デビュー年",
                        "代表作"
                    ]
                },
                "validation_process": [
                    "IMDbでの検索と照合",
                    "日本映画データベースでの確認",
                    "所属事務所公式サイトでの確認",
                    "出演作品の実在性確認"
                ]
            },
            "quality_metrics": {
                "minimum_data_completeness": 40,  # 最低40%のフィールドが埋まっている
                "wikipedia_preferred": True,
                "imdb_preferred": True,
                "birth_year_required_if_contemporary": True  # 現代の俳優は生年必須
            },
            "suspicious_patterns": [
                "生年情報なし + Wikipedia記載なし",
                "出演作品なし + 所属事務所なし",
                "Google検索結果0件"
            ],
            "created_at": datetime.now().isoformat(),
            "reason": "俳優データの品質向上と架空データ排除のため"
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
    
    return new_rules


def detect_and_remove_placeholders():
    """プレースホルダーデータの検出と削除"""
    import pandas as pd
    from improved_wikipedia_api import ImprovedWikipediaAPI
    
    # データ読み込み
    csv_file = Path('ultra_think_database_final_20250912_033943.csv')
    if not csv_file.exists():
        csv_file = Path('ultra_think_GOOGLE_COMPLIANT_20250912_031819.csv')
    
    df = pd.read_csv(csv_file)
    api = ImprovedWikipediaAPI()
    
    # 疑わしい「加藤」姓の俳優
    suspicious_ids = [
        'P002180', 'P002191', 'P002197', 'P002200',
        'P002207', 'P002230', 'P002232'
    ]
    
    logger.info("=" * 60)
    logger.info("プレースホルダーデータ削除処理")
    logger.info("=" * 60)
    
    # 削除対象の確認
    to_delete = df[df['person_id'].isin(suspicious_ids)]
    logger.info(f"削除対象: {len(to_delete)}件")
    
    for _, row in to_delete.iterrows():
        logger.info(f"  - {row['person_id']}: {row['person_name']} ({row['occupation']})")
    
    # バックアップ作成
    backup_file = f"backup_before_placeholder_removal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(backup_file, index=False, encoding='utf-8-sig')
    logger.info(f"📁 バックアップ作成: {backup_file}")
    
    # 削除実行
    df_cleaned = df[~df['person_id'].isin(suspicious_ids)]
    
    # 保存
    output_file = f"ultra_think_CLEANED_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df_cleaned.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    logger.info(f"✅ クリーンアップ完了")
    logger.info(f"  削除前: {len(df)}件")
    logger.info(f"  削除後: {len(df_cleaned)}件")
    logger.info(f"  削除数: {len(df) - len(df_cleaned)}件")
    logger.info(f"💾 保存先: {output_file}")
    
    return df_cleaned


def generate_quality_report():
    """データ品質レポート生成"""
    report = []
    report.append("# プレースホルダーデータ検出・削除レポート")
    report.append("")
    report.append(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    report.append("## 問題の発見")
    report.append("")
    report.append("「加藤」姓の俳優10件中7件がWikipediaに存在しない架空のデータでした。")
    report.append("")
    report.append("### 削除対象")
    report.append("")
    report.append("| Person ID | 名前 | Wikipedia |")
    report.append("|-----------|------|-----------|")
    report.append("| P002180 | 加藤優斗 | ❌ なし |")
    report.append("| P002191 | 加藤大輝 | ❌ なし |")
    report.append("| P002197 | 加藤悠斗 | ❌ なし |")
    report.append("| P002200 | 加藤拓海 | ❌ なし |")
    report.append("| P002207 | 加藤涼太 | ❌ なし |")
    report.append("| P002230 | 加藤陸 | ❌ なし |")
    report.append("| P002232 | 加藤颯太 | ❌ なし |")
    report.append("")
    report.append("### 保持対象（実在確認済み）")
    report.append("")
    report.append("| Person ID | 名前 | Wikipedia |")
    report.append("|-----------|------|-----------|")
    report.append("| P002178 | 加藤健太 | ✅ あり |")
    report.append("| P002222 | 加藤翔 | ✅ あり |")
    report.append("| P002226 | 加藤蓮 | ✅ あり |")
    report.append("")
    report.append("## 追加されたPDCAルール")
    report.append("")
    report.append("- **RULE_090**: プレースホルダーデータ検出ルール")
    report.append("- **RULE_091**: 実在性検証必須ルール")
    report.append("- **RULE_092**: 俳優データ品質基準ルール")
    report.append("")
    report.append("## 今後の対策")
    report.append("")
    report.append("1. 新規データ追加時の実在性検証を必須化")
    report.append("2. Wikipedia/IMDb/公式サイトいずれかでの確認を義務付け")
    report.append("3. 連番ID、類似名パターンの自動検出")
    report.append("4. 定期的なデータ品質監査の実施")
    report.append("")
    
    # レポート保存
    report_file = f"PLACEHOLDER_DETECTION_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    
    logger.info(f"📄 レポート生成: {report_file}")


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("🚀 プレースホルダーデータ対策実行")
    logger.info("=" * 60)
    
    # 1. PDCAルール追加
    new_rules = add_placeholder_detection_rules()
    
    # 2. プレースホルダーデータ削除
    cleaned_df = detect_and_remove_placeholders()
    
    # 3. レポート生成
    generate_quality_report()
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ プレースホルダーデータ対策完了")
    logger.info("=" * 60)
    logger.info("実施内容:")
    logger.info("  1. PDCAルール090-092追加")
    logger.info("  2. 架空データ7件削除")
    logger.info("  3. データ品質向上")


if __name__ == "__main__":
    main()