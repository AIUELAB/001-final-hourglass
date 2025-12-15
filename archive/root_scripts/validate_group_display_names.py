#!/usr/bin/env python3
"""
グループメンバー表示名検証スクリプト
PDCAガーディアンルール084-086に基づく包括的検証
"""

import pandas as pd
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
import re

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GroupDisplayNameValidator:
    """グループメンバー表示名検証クラス"""

    def __init__(self):
        """初期化"""
        self.violations = []
        self.statistics = {
            'total_checked': 0,
            'comedians_checked': 0,
            'musicians_checked': 0,
            'youtubers_checked': 0,
            'violations_found': 0,
            'groups_without_db_entry': set(),
            'members_without_groups': [],
            'format_violations': [],
            'inconsistent_groups': []
        }

        # グループデータベース読み込み
        self.load_groups_database()

        # 検証対象の職業カテゴリ
        self.group_occupations = {
            'comedian': ['お笑い芸人', 'コメディアン', '漫才師', 'コント師'],
            'musician': ['歌手', 'ミュージシャン', 'アーティスト', 'バンドメンバー', 'アイドル'],
            'youtuber': ['YouTuber', 'ユーチューバー', '配信者']
        }

    def load_groups_database(self):
        """グループデータベース読み込み"""
        groups_file = Path('groups_database.json')

        if groups_file.exists():
            with open(groups_file, 'r', encoding='utf-8') as f:
                self.groups_db = json.load(f)
                logger.info(f"📂 グループデータベース読み込み: {len(self.groups_db)}グループ")
        else:
            self.groups_db = {}
            logger.warning("⚠️ groups_database.jsonが見つかりません")

        # メンバー名 → グループ名の逆引き辞書作成
        self.member_to_group = {}
        for group_name, group_info in self.groups_db.items():
            if 'members' in group_info:
                for member in group_info['members']:
                    if member not in self.member_to_group:
                        self.member_to_group[member] = []
                    self.member_to_group[member].append(group_name)

    def validate_display_format(self, display_name: str) -> Dict:
        """
        表示名フォーマットの検証

        Returns:
            検証結果の辞書
        """
        result = {
            'valid': True,
            'has_group': False,
            'group_name': None,
            'base_name': None,
            'issues': []
        }

        # 括弧のパターンチェック
        if '（' in display_name and '）' in display_name:
            # 全角括弧あり
            match = re.match(r'^(.+?)（(.+?)）$', display_name)
            if match:
                result['base_name'] = match.group(1).strip()
                result['group_name'] = match.group(2).strip()
                result['has_group'] = True
            else:
                result['valid'] = False
                result['issues'].append('括弧の位置が不正')

        elif '(' in display_name and ')' in display_name:
            # 半角括弧（ルール違反）
            result['valid'] = False
            result['issues'].append('半角括弧使用（全角必須）')

        # 複数括弧のチェック
        if display_name.count('（') > 1 or display_name.count('）') > 1:
            result['valid'] = False
            result['issues'].append('複数の括弧が存在')

        # 括弧の対応チェック
        if display_name.count('（') != display_name.count('）'):
            result['valid'] = False
            result['issues'].append('括弧の対応が不正')

        return result

    def check_group_consistency(self, person_name: str, display_name: str, occupation: str) -> List[str]:
        """
        グループの整合性チェック

        Returns:
            違反内容のリスト
        """
        violations = []

        # フォーマット検証
        format_result = self.validate_display_format(display_name)

        # グループメンバーの可能性がある職業か
        is_group_occupation = any(
            occ in occupation for category in self.group_occupations.values()
            for occ in category
        )

        if is_group_occupation:
            # データベースでグループ確認
            known_groups = self.member_to_group.get(person_name, [])

            if known_groups:
                # 既知のグループメンバー
                if not format_result['has_group']:
                    violations.append(f"グループメンバーなのに括弧なし（{', '.join(known_groups)}）")
                elif format_result['group_name'] not in known_groups:
                    violations.append(f"グループ名不一致（DB: {', '.join(known_groups)} vs 表示: {format_result['group_name']}）")

            elif format_result['has_group']:
                # グループ名があるがDBに未登録
                self.statistics['groups_without_db_entry'].add(format_result['group_name'])
                violations.append(f"グループ「{format_result['group_name']}」がデータベース未登録")

        # フォーマットエラー
        if not format_result['valid']:
            violations.extend(format_result['issues'])

        return violations

    def validate_dataframe(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """
        DataFrameの包括的検証

        Returns:
            (検証済みDataFrame, 統計情報)
        """
        logger.info("🔍 表示名検証開始")

        for idx, row in df.iterrows():
            self.statistics['total_checked'] += 1

            person_id = str(row.get('person_id', '')).strip()
            person_name = str(row.get('person_name', '')).strip()
            display_name = str(row.get('person_name_display', '')).strip()
            occupation = str(row.get('occupation', '')).strip()

            # 職業カテゴリ別カウント
            if any(occ in occupation for occ in self.group_occupations['comedian']):
                self.statistics['comedians_checked'] += 1
            elif any(occ in occupation for occ in self.group_occupations['musician']):
                self.statistics['musicians_checked'] += 1
            elif any(occ in occupation for occ in self.group_occupations['youtuber']):
                self.statistics['youtubers_checked'] += 1

            # 整合性チェック
            violations = self.check_group_consistency(person_name, display_name, occupation)

            if violations:
                self.statistics['violations_found'] += 1
                self.violations.append({
                    'person_id': person_id,
                    'person_name': person_name,
                    'display_name': display_name,
                    'occupation': occupation,
                    'violations': violations
                })

                logger.warning(f"❌ {person_id}: {person_name} - {', '.join(violations)}")

        return df, self.statistics

    def generate_report(self):
        """検証レポート生成"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'statistics': {
                'total_checked': self.statistics['total_checked'],
                'violations_found': self.statistics['violations_found'],
                'violation_rate': f"{(self.statistics['violations_found'] / max(self.statistics['total_checked'], 1)) * 100:.2f}%",
                'comedians_checked': self.statistics['comedians_checked'],
                'musicians_checked': self.statistics['musicians_checked'],
                'youtubers_checked': self.statistics['youtubers_checked'],
                'groups_without_db': list(self.statistics['groups_without_db_entry'])
            },
            'violations': self.violations,
            'pdca_rules_validated': [
                'RULE_084: グループメンバー表示名検証',
                'RULE_085: グループデータベース完全性チェック',
                'RULE_086: 新規追加時の自動グループ検出'
            ]
        }

        # JSON形式で保存
        report_file = f"group_display_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"📝 検証レポート保存: {report_file}")

        # マークダウンレポート生成
        self.generate_markdown_report()

        return report

    def generate_markdown_report(self):
        """マークダウン形式のレポート生成"""
        report = []
        report.append("# グループメンバー表示名検証レポート")
        report.append("")
        report.append(f"検証日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # サマリー
        report.append("## 📊 検証サマリー")
        report.append("")
        report.append(f"- **総チェック数**: {self.statistics['total_checked']}件")
        report.append(f"- **違反検出数**: {self.statistics['violations_found']}件")
        violation_rate = (self.statistics['violations_found'] / max(self.statistics['total_checked'], 1)) * 100
        report.append(f"- **違反率**: {violation_rate:.2f}%")
        report.append("")

        # カテゴリ別統計
        report.append("### カテゴリ別チェック数")
        report.append("")
        report.append(f"- お笑い芸人: {self.statistics['comedians_checked']}件")
        report.append(f"- ミュージシャン: {self.statistics['musicians_checked']}件")
        report.append(f"- YouTuber: {self.statistics['youtubers_checked']}件")
        report.append("")

        # データベース未登録グループ
        if self.statistics['groups_without_db_entry']:
            report.append("## ⚠️ データベース未登録グループ")
            report.append("")
            for group in sorted(self.statistics['groups_without_db_entry']):
                report.append(f"- {group}")
            report.append("")

        # 違反詳細
        if self.violations:
            report.append("## ❌ 違反詳細")
            report.append("")
            report.append("| Person ID | 名前 | 表示名 | 職業 | 違反内容 |")
            report.append("|-----------|------|--------|------|----------|")

            for v in self.violations[:50]:  # 最初の50件のみ表示
                violations_str = '<br>'.join(v['violations'])
                report.append(f"| {v['person_id']} | {v['person_name']} | {v['display_name']} | {v['occupation']} | {violations_str} |")

            if len(self.violations) > 50:
                report.append("")
                report.append(f"*他 {len(self.violations) - 50}件の違反があります（詳細はJSONレポート参照）*")
        else:
            report.append("## ✅ 違反なし")
            report.append("")
            report.append("すべてのグループメンバーの表示名が正しい形式です。")

        report.append("")
        report.append("## 🛡️ 検証済みPDCAルール")
        report.append("")
        report.append("- RULE_084: グループメンバー表示名検証")
        report.append("- RULE_085: グループデータベース完全性チェック")
        report.append("- RULE_086: 新規追加時の自動グループ検出")
        report.append("")

        # 推奨アクション
        report.append("## 📋 推奨アクション")
        report.append("")

        if self.statistics['groups_without_db_entry']:
            report.append("1. **データベース更新**: 未登録グループをgroups_database.jsonに追加")

        if self.violations:
            report.append("2. **表示名修正**: 違反が検出された表示名を修正")
            report.append("3. **再検証**: 修正後に再度このスクリプトを実行")
        else:
            report.append("1. **定期監視**: 週次でこのスクリプトを実行して品質維持")

        report.append("")

        # レポート保存
        report_file = f"GROUP_DISPLAY_VALIDATION_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))

        logger.info(f"📄 マークダウンレポート生成: {report_file}")

    def suggest_fixes(self) -> List[Dict]:
        """修正提案の生成"""
        suggestions = []

        for violation in self.violations:
            suggestion = {
                'person_id': violation['person_id'],
                'person_name': violation['person_name'],
                'current_display': violation['display_name'],
                'suggested_display': None,
                'reason': []
            }

            # データベースからグループを検索
            known_groups = self.member_to_group.get(violation['person_name'], [])

            if known_groups:
                # 既知のグループメンバー
                suggestion['suggested_display'] = f"{violation['person_name']}（{known_groups[0]}）"
                suggestion['reason'].append(f"データベースに基づくグループ: {known_groups[0]}")
            else:
                # グループ不明の場合
                format_result = self.validate_display_format(violation['display_name'])
                if format_result['has_group']:
                    # 括弧はあるがフォーマットエラー
                    suggestion['suggested_display'] = f"{violation['person_name']}（{format_result['group_name']}）"
                    suggestion['reason'].append("フォーマット修正（全角括弧）")
                else:
                    # グループ不明
                    suggestion['suggested_display'] = violation['person_name']
                    suggestion['reason'].append("グループ不明のため名前のみ")

            suggestions.append(suggestion)

        return suggestions


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("🚀 グループメンバー表示名検証開始")
    logger.info("=" * 60)

    # 最新のCSVファイルを探す
    csv_files = list(Path('.').glob('ultra_think_*.csv'))
    if not csv_files:
        logger.error("❌ CSVファイルが見つかりません")
        return

    # 最新のファイルを使用
    csv_file = max(csv_files, key=lambda x: x.stat().st_mtime)
    logger.info(f"📂 データ読み込み: {csv_file}")

    df = pd.read_csv(csv_file)

    # 検証実行
    validator = GroupDisplayNameValidator()
    df_validated, stats = validator.validate_dataframe(df)

    # レポート生成
    report = validator.generate_report()

    # 修正提案生成
    if validator.violations:
        suggestions = validator.suggest_fixes()

        # 修正提案をファイル保存
        suggestions_file = f"group_display_fix_suggestions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(suggestions_file, 'w', encoding='utf-8') as f:
            json.dump(suggestions, f, ensure_ascii=False, indent=2)

        logger.info(f"💡 修正提案保存: {suggestions_file}")

    # サマリー表示
    logger.info("\n" + "=" * 60)
    logger.info("📊 検証結果サマリー")
    logger.info("=" * 60)
    logger.info(f"  総チェック数: {stats['total_checked']}")
    logger.info(f"  違反検出数: {stats['violations_found']}")
    logger.info(f"  違反率: {(stats['violations_found'] / max(stats['total_checked'], 1)) * 100:.2f}%")

    if stats['groups_without_db_entry']:
        logger.info(f"\n  ⚠️ データベース未登録グループ: {len(stats['groups_without_db_entry'])}件")
        for group in list(stats['groups_without_db_entry'])[:5]:
            logger.info(f"    - {group}")
        if len(stats['groups_without_db_entry']) > 5:
            logger.info(f"    ... 他 {len(stats['groups_without_db_entry']) - 5}件")

    if stats['violations_found'] == 0:
        logger.info("\n✅ すべてのグループメンバーの表示名が正しい形式です")
    else:
        logger.info(f"\n❌ {stats['violations_found']}件の違反が検出されました")
        logger.info("📋 詳細はレポートファイルを確認してください")

    logger.info("\n✅ グループメンバー表示名検証完了")


if __name__ == "__main__":
    main()
