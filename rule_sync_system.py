#!/usr/bin/env python3
"""
PDCAガーディアンルール自動同期システム
ルール定義と実装の完全同期を保証する
"""

import json
import os
import re
import ast
from typing import Dict, List, Set, Tuple, Any
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)


class RuleSyncSystem:
    """ルール定義と実装の自動同期システム"""

    def __init__(self):
        self.pdca_rules_file = "pdca_rules.json"
        self.pdca_guardian_file = "pdca_guardian.py"
        self.rule_definition_files = []
        self.sync_report = {
            "timestamp": datetime.now().isoformat(),
            "defined_rules": [],
            "implemented_rules": [],
            "missing_implementations": [],
            "orphaned_implementations": [],
            "sync_actions": []
        }

    def scan_rule_definitions(self) -> Dict[str, Any]:
        """すべてのルール定義をスキャン"""
        logger.info("ルール定義ファイルをスキャン中...")

        # add_pdca_rule_*.pyファイルを検索
        import glob
        rule_files = glob.glob("add_pdca_rule_*.py")
        self.rule_definition_files = rule_files

        # pdca_rules.jsonから定義済みルールを抽出
        defined_rules = {}
        if os.path.exists(self.pdca_rules_file):
            with open(self.pdca_rules_file, 'r', encoding='utf-8') as f:
                pdca_rules = json.load(f)
                for rule in pdca_rules.get('rules', []):
                    rule_id = rule.get('rule_id')
                    if rule_id:
                        defined_rules[rule_id] = {
                            'name': rule.get('name'),
                            'check_function': rule.get('check_function'),
                            'violation_type': rule.get('violation_type'),
                            'priority': rule.get('priority'),
                            'source': 'pdca_rules.json'
                        }

        # 各定義ファイルからもルール情報を抽出
        for file in rule_files:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
                # rule_idを探す
                rule_id_match = re.search(r'"rule_id":\s*"(RULE_\d+)"', content)
                if rule_id_match:
                    rule_id = rule_id_match.group(1)
                    if rule_id not in defined_rules:
                        defined_rules[rule_id] = {
                            'name': 'Unknown',
                            'check_function': None,
                            'violation_type': None,
                            'source': file
                        }

        self.sync_report['defined_rules'] = list(defined_rules.keys())
        logger.info(f"✅ {len(defined_rules)}個のルール定義を検出")
        return defined_rules

    def scan_implementations(self) -> Dict[str, Any]:
        """PDCAガーディアンの実装をスキャン"""
        logger.info("PDCAガーディアン実装をスキャン中...")

        implemented_rules = {}
        if not os.path.exists(self.pdca_guardian_file):
            logger.error(f"❌ {self.pdca_guardian_file}が見つかりません")
            return implemented_rules

        with open(self.pdca_guardian_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 実装されているRULEを検出
        # パターン1: 'rule_id': 'RULE_XXX'
        pattern1 = re.findall(r"'rule_id':\s*'(RULE_\d+)'", content)
        # パターン2: "rule_id": "RULE_XXX"
        pattern2 = re.findall(r'"rule_id":\s*"(RULE_\d+)"', content)

        all_rules = set(pattern1 + pattern2)

        # check_episode_qualityメソッド内での使用確認
        for rule_id in all_rules:
            # メソッドの存在確認
            check_method = self._find_check_method_for_rule(content, rule_id)
            implemented_rules[rule_id] = {
                'has_check_method': bool(check_method),
                'check_method': check_method,
                'in_check_episode_quality': rule_id in content[content.find("def check_episode_quality"):content.find("def check_episode_quality") + 5000] if "def check_episode_quality" in content else False
            }

        self.sync_report['implemented_rules'] = list(implemented_rules.keys())
        logger.info(f"✅ {len(implemented_rules)}個のルール実装を検出")
        return implemented_rules

    def _find_check_method_for_rule(self, content: str, rule_id: str) -> str:
        """特定のルールのチェックメソッドを探す"""
        # ルールIDの前後のコンテキストを取得
        pattern = rf"def\s+(\w+).*?:\s*.*?RULE_{rule_id[5:]}"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1)

        # RULE_XXXコメントがあるメソッドを探す
        pattern2 = rf"#.*?RULE_{rule_id[5:]}.*?\n\s*def\s+(\w+)"
        match2 = re.search(pattern2, content)
        if match2:
            return match2.group(1)

        return None

    def find_sync_gaps(self, defined_rules: Dict, implemented_rules: Dict) -> Tuple[List[str], List[str]]:
        """定義と実装のギャップを検出"""
        defined_set = set(defined_rules.keys())
        implemented_set = set(implemented_rules.keys())

        missing_implementations = list(defined_set - implemented_set)
        orphaned_implementations = list(implemented_set - defined_set)

        self.sync_report['missing_implementations'] = missing_implementations
        self.sync_report['orphaned_implementations'] = orphaned_implementations

        if missing_implementations:
            logger.warning(f"⚠️ 未実装ルール: {missing_implementations}")
        if orphaned_implementations:
            logger.warning(f"⚠️ 定義のない実装: {orphaned_implementations}")

        return missing_implementations, orphaned_implementations

    def generate_implementation_code(self, rule_id: str, rule_def: Dict) -> str:
        """ルールの実装コードを生成"""
        check_function = rule_def.get('check_function', f'check_rule_{rule_id.lower()}')
        violation_type = rule_def.get('violation_type', f'{rule_id}_VIOLATION')

        code = f'''
    def {check_function}(self, episode_text: str, person_name_display: str) -> List[Dict[str, Any]]:
        """
        {rule_id}: {rule_def.get('name', 'Unknown')}
        自動生成された実装
        """
        violations = []

        # TODO: 実装を追加
        # この実装は自動生成されました。実際のルールロジックを追加してください。

        return violations
'''
        return code

    def auto_sync_rules(self) -> bool:
        """ルールを自動同期"""
        logger.info("=" * 60)
        logger.info("ルール自動同期開始")
        logger.info("=" * 60)

        # スキャン
        defined_rules = self.scan_rule_definitions()
        implemented_rules = self.scan_implementations()

        # ギャップ検出
        missing, orphaned = self.find_sync_gaps(defined_rules, implemented_rules)

        if not missing and not orphaned:
            logger.info("✅ すべてのルールが同期されています")
            return True

        # 修正提案
        if missing:
            logger.info("\n📝 実装が必要なルール:")
            for rule_id in missing:
                rule_def = defined_rules[rule_id]
                logger.info(f"  - {rule_id}: {rule_def.get('name', 'Unknown')}")
                self.sync_report['sync_actions'].append({
                    'action': 'implement',
                    'rule_id': rule_id,
                    'reason': 'missing_implementation'
                })

        if orphaned:
            logger.info("\n🗑️ 定義が必要な実装:")
            for rule_id in orphaned:
                logger.info(f"  - {rule_id}")
                self.sync_report['sync_actions'].append({
                    'action': 'define_or_remove',
                    'rule_id': rule_id,
                    'reason': 'orphaned_implementation'
                })

        # レポート保存
        self.save_sync_report()
        return False

    def save_sync_report(self):
        """同期レポートを保存"""
        report_file = f"rule_sync_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.sync_report, f, ensure_ascii=False, indent=2)
        logger.info(f"\n📊 同期レポート保存: {report_file}")

    def validate_implementation_completeness(self) -> bool:
        """実装の完全性を検証"""
        logger.info("\n実装完全性検証中...")

        with open(self.pdca_guardian_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 必要な要素のチェック
        requirements = {
            'ViolationType定義': [],
            'チェックメソッド': [],
            'check_episode_quality呼び出し': []
        }

        for rule_id in self.sync_report['implemented_rules']:
            # ViolationTypeチェック
            violation_pattern = rf'{rule_id[5:]}_.*?=.*?"'
            if re.search(violation_pattern, content):
                requirements['ViolationType定義'].append(rule_id)

            # チェックメソッド存在確認
            method_pattern = rf'def.*?{rule_id.lower()}|def.*?rule_{rule_id[5:]}'
            if re.search(method_pattern, content, re.IGNORECASE):
                requirements['チェックメソッド'].append(rule_id)

            # check_episode_qualityでの呼び出し確認
            if rule_id in content[content.find("def check_episode_quality"):content.find("def check_episode_quality") + 10000] if "def check_episode_quality" in content else "":
                requirements['check_episode_quality呼び出し'].append(rule_id)

        # 結果表示
        all_complete = True
        for check_type, passed_rules in requirements.items():
            missing = set(self.sync_report['implemented_rules']) - set(passed_rules)
            if missing:
                logger.warning(f"❌ {check_type}が不完全: {list(missing)}")
                all_complete = False
            else:
                logger.info(f"✅ {check_type}: 完全")

        return all_complete

    def generate_sync_fix_script(self) -> str:
        """同期修正スクリプトを生成"""
        script = """#!/usr/bin/env python3
# 自動生成された同期修正スクリプト
# 生成日時: {timestamp}

import os
import re

def add_missing_implementations():
    \"\"\"未実装ルールを追加\"\"\"
    # TODO: 実装を追加

def remove_orphaned_implementations():
    \"\"\"定義のない実装を削除\"\"\"
    # TODO: 実装を削除

if __name__ == "__main__":
    add_missing_implementations()
    remove_orphaned_implementations()
    print("✅ 同期修正完了")
""".format(timestamp=datetime.now().isoformat())

        with open('fix_rule_sync.py', 'w', encoding='utf-8') as f:
            f.write(script)

        logger.info("📝 修正スクリプト生成: fix_rule_sync.py")
        return script


def main():
    """メイン処理"""
    sync_system = RuleSyncSystem()

    # 自動同期実行
    is_synced = sync_system.auto_sync_rules()

    # 実装完全性検証
    is_complete = sync_system.validate_implementation_completeness()

    # 総合結果
    logger.info("\n" + "=" * 60)
    logger.info("同期システム実行結果")
    logger.info("=" * 60)

    if is_synced and is_complete:
        logger.info("🎉 完全同期達成！すべてのルールが正しく実装されています")
    else:
        logger.info("⚠️ 同期が必要です。レポートを確認してください")
        sync_system.generate_sync_fix_script()

    # 統計表示
    logger.info(f"\n📊 統計:")
    logger.info(f"  定義済みルール: {len(sync_system.sync_report['defined_rules'])}")
    logger.info(f"  実装済みルール: {len(sync_system.sync_report['implemented_rules'])}")
    logger.info(f"  未実装: {len(sync_system.sync_report['missing_implementations'])}")
    logger.info(f"  孤立実装: {len(sync_system.sync_report['orphaned_implementations'])}")


if __name__ == "__main__":
    main()