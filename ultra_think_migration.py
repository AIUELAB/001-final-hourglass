#!/usr/bin/env python3
"""
🔄 Ultra Think Migration Script
既存のultra_think_*.pyファイルをUnifiedDataCollectionGateway経由に移行

このスクリプトは既存のultra_thinkファイルを分析し、
バリデーションをバイパスしている箇所を検出して修正します。
"""

import ast
import os
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import shutil
from datetime import datetime

class UltraThinkMigrator:
    """Ultra Thinkファイルの移行システム"""

    def __init__(self):
        self.backup_dir = Path("ultra_think_backups")
        self.backup_dir.mkdir(exist_ok=True)

        # バリデーションバイパスパターン
        self.bypass_patterns = [
            r"csv\.writer\(",
            r"csv\.DictWriter\(",
            r"\.to_csv\(",
            r"open\([^,]+,\s*['\"]w['\"]",  # 直接ファイル書き込み
            r"with\s+open\([^,]+,\s*['\"]w['\"]",
            r"DataFrame\.to_csv",
            r"writerow\(",
            r"writerows\("
        ]

        # 修正が必要なファイルのリスト
        self.files_to_migrate = []

    def analyze_file(self, filepath: Path) -> Dict:
        """ファイルを分析してバリデーションバイパスを検出"""

        issues = {
            'file': filepath.name,
            'direct_csv_writes': [],
            'missing_validation': [],
            'bypass_locations': []
        }

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')

        # パターンマッチング
        for i, line in enumerate(lines, 1):
            for pattern in self.bypass_patterns:
                if re.search(pattern, line):
                    issues['bypass_locations'].append({
                        'line': i,
                        'code': line.strip(),
                        'pattern': pattern
                    })

        # バリデーション呼び出しの確認
        validation_calls = [
            'PDCAGuardian',
            'OptimizedValidationSystem',
            'UnifiedValidationSystem',
            'validate_person',
            'check_validation'
        ]

        has_validation = any(val in content for val in validation_calls)
        if not has_validation:
            issues['missing_validation'].append('No validation system detected')

        return issues

    def generate_migration_code(self, filepath: Path) -> str:
        """既存ファイルを移行するための新しいコードを生成"""

        template = '''#!/usr/bin/env python3
"""
{filename} - Migrated to use UnifiedDataCollectionGateway
Migration Date: {date}
Original file backed up to: {backup_path}
"""

import sys
import os
from pathlib import Path

# UnifiedDataCollectionGatewayをインポート
sys.path.append(str(Path(__file__).parent))
from unified_data_collection_gateway import UnifiedDataCollectionGateway, ValidationLevel
from character_type_classifier import CharacterTypeClassifier

# 元のインポート（必要なもののみ保持）
{original_imports}

class Migrated{classname}:
    """バリデーション統合版の{classname}"""

    def __init__(self):
        # 統合ゲートウェイを初期化
        self.gateway = UnifiedDataCollectionGateway(
            validation_level=ValidationLevel.STANDARD
        )
        self.classifier = CharacterTypeClassifier()

        # 元の初期化コード（必要に応じて）
        {original_init}

    def add_person(self, person_name: str, **kwargs):
        """
        人物追加メソッド（バリデーション統合版）

        すべての人物追加は必ずゲートウェイを通過します。
        """
        # キャラクタータイプを判定
        classification = self.classifier.classify(
            person_name,
            occupation=kwargs.get('occupation'),
            category=kwargs.get('category')
        )

        # エンティティタイプを設定
        if classification.character_type == 'fictional_character':
            kwargs['entity_type'] = 'fictional_character'
            kwargs['work_name'] = classification.work_name
        else:
            kwargs['entity_type'] = 'person'

        # ゲートウェイ経由で追加（バリデーション実行）
        success, person_data, report = self.gateway.add_person(
            person_name=person_name,
            **kwargs
        )

        if not success:
            print(f"❌ バリデーション失敗: {{person_name}}")
            print(f"   違反: {{report.violations}}")
            return None

        print(f"✅ 追加成功: {{person_name}} (スコア: {{person_data.name_recognition:.1f}})")
        return person_data

    def save_to_csv(self, output_path: str = None):
        """
        CSVファイルに保存（バリデーション済みデータのみ）
        """
        if output_path is None:
            output_path = "ultra_think_validated_{{timestamp}}.csv"

        # ゲートウェイから検証済みデータを取得
        self.gateway.export_to_csv(output_path)
        print(f"💾 検証済みデータを保存: {{output_path}}")

        # バリデーションレポートも出力
        report_path = output_path.replace('.csv', '_validation_report.json')
        self.gateway.export_validation_report(report_path)
        print(f"📊 バリデーションレポート: {{report_path}}")

# メイン処理
if __name__ == "__main__":
    migrated = Migrated{classname}()

    # 元のファイルの処理ロジックをここに移植
    # ただし、すべてのデータ追加はmigrated.add_person()を使用
    {main_logic}
'''

        # ファイル名からクラス名を生成
        classname = self._generate_classname(filepath.name)

        # テンプレートを埋める
        migration_code = template.format(
            filename=filepath.name,
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            backup_path=self.backup_dir / f"{filepath.name}.backup",
            original_imports=self._extract_imports(filepath),
            classname=classname,
            original_init="# TODO: 元の初期化コードを移植",
            main_logic="# TODO: 元のメイン処理を移植",
            timestamp=datetime.now().strftime("%Y%m%d_%H%M%S")
        )

        return migration_code

    def _generate_classname(self, filename: str) -> str:
        """ファイル名からクラス名を生成"""
        # ultra_think_xxx.py -> XxxMigrated
        name = filename.replace('ultra_think_', '').replace('.py', '')
        parts = name.split('_')
        return ''.join(p.capitalize() for p in parts)

    def _extract_imports(self, filepath: Path) -> str:
        """元ファイルからインポート文を抽出"""
        imports = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('import ') or line.startswith('from '):
                    # CSVとファイル直接書き込み関連は除外
                    if 'csv' not in line and 'pandas' not in line:
                        imports.append(line.strip())
        return '\n'.join(imports)

    def migrate_file(self, filepath: Path, dry_run: bool = False):
        """単一ファイルを移行"""

        print(f"\n🔄 移行処理: {filepath.name}")

        # 1. バックアップ作成
        backup_path = self.backup_dir / f"{filepath.name}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if not dry_run:
            shutil.copy2(filepath, backup_path)
            print(f"  📦 バックアップ: {backup_path}")

        # 2. 分析
        issues = self.analyze_file(filepath)
        print(f"  🔍 検出された問題:")
        print(f"     - 直接CSV書き込み: {len(issues['bypass_locations'])}箇所")
        print(f"     - バリデーション欠如: {len(issues['missing_validation'])}箇所")

        # 3. 新しいコード生成
        new_code = self.generate_migration_code(filepath)

        # 4. ファイル更新
        if not dry_run:
            # 移行版として新しいファイルを作成
            migrated_path = filepath.parent / f"{filepath.stem}_migrated.py"
            with open(migrated_path, 'w', encoding='utf-8') as f:
                f.write(new_code)
            print(f"  ✅ 移行版作成: {migrated_path}")
        else:
            print(f"  🔸 ドライラン - 実際の変更は行いません")

        return issues

    def scan_and_migrate_all(self, dry_run: bool = False):
        """すべてのultra_think_*.pyファイルをスキャンして移行"""

        print("🔎 Ultra Thinkファイルをスキャン中...")

        # ultra_think_*.pyファイルを検索
        ultra_files = list(Path('.').glob('ultra_think_*.py'))

        # 除外するファイル
        exclude_patterns = [
            '_migrated.py',
            '_backup.py',
            'ultra_think_migration.py'  # このファイル自身
        ]

        target_files = []
        for f in ultra_files:
            if not any(pattern in f.name for pattern in exclude_patterns):
                target_files.append(f)

        print(f"📋 対象ファイル: {len(target_files)}個")

        # 各ファイルを処理
        all_issues = []
        for filepath in target_files:
            issues = self.migrate_file(filepath, dry_run=dry_run)
            all_issues.append(issues)

        # サマリー表示
        self._display_summary(all_issues)

    def _display_summary(self, all_issues: List[Dict]):
        """移行サマリーを表示"""

        print("\n" + "="*60)
        print("📊 移行サマリー")
        print("="*60)

        total_bypasses = sum(len(i['bypass_locations']) for i in all_issues)
        total_missing = sum(len(i['missing_validation']) for i in all_issues)

        print(f"検出された問題:")
        print(f"  - 直接CSV書き込み: {total_bypasses}箇所")
        print(f"  - バリデーション欠如: {total_missing}ファイル")

        print("\n最も問題が多いファイル:")
        sorted_issues = sorted(all_issues,
                              key=lambda x: len(x['bypass_locations']),
                              reverse=True)
        for issue in sorted_issues[:5]:
            if issue['bypass_locations']:
                print(f"  - {issue['file']}: {len(issue['bypass_locations'])}箇所")

        print("\n📌 次のステップ:")
        print("1. 生成された_migrated.pyファイルを確認")
        print("2. TODOセクションに元のロジックを移植")
        print("3. テスト実行して動作確認")
        print("4. 問題なければ元のファイルを置き換え")


def demonstrate_single_file_migration():
    """単一ファイルの移行デモンストレーション"""

    print("🎯 Ultra Think移行デモンストレーション")
    print("="*60)

    # 最もシンプルなファイルを選んで移行
    target_file = Path("ultra_think_auto_calibrated_person_adder.py")

    if not target_file.exists():
        print(f"❌ ファイルが見つかりません: {target_file}")
        return

    migrator = UltraThinkMigrator()

    # ドライラン実行
    print(f"\n1️⃣ ドライラン実行（変更なし）")
    migrator.migrate_file(target_file, dry_run=True)

    # 実際の移行
    print(f"\n2️⃣ 実際の移行実行")
    user_input = input("実行しますか？ (y/n): ")

    if user_input.lower() == 'y':
        migrator.migrate_file(target_file, dry_run=False)
        print("\n✨ 移行完了！")
        print(f"新しいファイル: {target_file.stem}_migrated.py")
    else:
        print("⏸️ 移行をキャンセルしました")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--all':
        # すべてのファイルを移行
        migrator = UltraThinkMigrator()

        if '--dry-run' in sys.argv:
            migrator.scan_and_migrate_all(dry_run=True)
        else:
            migrator.scan_and_migrate_all(dry_run=False)
    else:
        # デモンストレーション
        demonstrate_single_file_migration()