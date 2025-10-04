#!/usr/bin/env python3
"""
強化版Quality Gateシステム
PDCAルールの強制適用メカニズムを強化し、例外なくすべての操作を監視
"""

import pandas as pd
from datetime import datetime
import sys
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from src.fact_checker import FactChecker, FactCheckResult
from pdca_guardian import PDCAGuardian

class GateStatus(Enum):
    """ゲート通過ステータス"""
    BLOCKED = "blocked"          # 完全ブロック
    WARNING = "warning"          # 警告付き通過
    PASSED = "passed"           # 通過

@dataclass
class GateCheckResult:
    """ゲートチェック結果"""
    status: GateStatus
    violations: List[str]
    critical_issues: List[str]
    recommendations: List[str]
    score: float

class EnhancedQualityGate:
    """
    強化版Quality Gateシステム
    すべてのCSV操作を監視し、品質基準を満たさない操作をブロック
    """

    # シングルトンパターンで唯一のインスタンスを保証
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.fact_checker = FactChecker()
            self.pdca_guardian = PDCAGuardian()
            self.blocked_operations = []
            self.approved_operations = []
            self._initialized = True
            self._lock_file = '.quality_gate_lock'

            print("🔒 Enhanced Quality Gate System 初期化完了")
            print("  すべてのCSV操作は監視下に置かれます")

    def acquire_lock(self) -> bool:
        """排他ロックを取得"""
        if os.path.exists(self._lock_file):
            print("⚠️ 別のQuality Gate処理が実行中です")
            return False

        with open(self._lock_file, 'w') as f:
            f.write(str(os.getpid()))
        return True

    def release_lock(self):
        """排他ロックを解放"""
        if os.path.exists(self._lock_file):
            os.remove(self._lock_file)

    def check_episode(self, episode_data: Dict) -> GateCheckResult:
        """
        単一エピソードの品質チェック
        PDCAルール156個すべてを適用
        """
        violations = []
        critical_issues = []
        recommendations = []

        person_name = episode_data.get('person_name', '')
        episode_text = episode_data.get('episode_text', '')
        episode_age = episode_data.get('episode_age', 0)

        # 1. 必須フィールドチェック
        required_fields = ['person_name', 'episode_age', 'episode_text']
        for field in required_fields:
            if not episode_data.get(field):
                critical_issues.append(f"必須フィールド '{field}' が欠落")

        # 2. 文字数チェック（RULE_151）
        text_length = len(episode_text)
        if text_length < 132:
            violations.append(f"RULE_151: 文字数不足 ({text_length} < 132)")
        elif text_length > 250:
            violations.append(f"RULE_151: 文字数超過 ({text_length} > 250)")

        # 3. ファクトチェック
        fact_report = self.fact_checker.check_episode(
            person_id=episode_data.get('person_id', 'P000'),
            person_name=person_name,
            episode_text=episode_text,
            birth_year=None
        )

        if fact_report.result == FactCheckResult.INCORRECT:
            critical_issues.append("事実誤認が検出されました")
        elif fact_report.result == FactCheckResult.SUSPICIOUS:
            violations.append("疑わしい内容が含まれています")

        # 4. PDCAルール適用
        pdca_violations = self.pdca_guardian.check_episode_quality(
            episode_text, episode_age, person_name
        )

        for violation in pdca_violations:
            rule_id = violation.get('rule_id', 'UNKNOWN')
            message = violation.get('message', '')
            severity = violation.get('severity', 'medium')

            if severity == 'critical':
                critical_issues.append(f"{rule_id}: {message}")
            else:
                violations.append(f"{rule_id}: {message}")

        # 5. 重複防止チェック（RULE_115）
        # ここでは既存データとの照合が必要

        # スコア計算
        base_score = 100.0
        score_deductions = {
            'critical': 50,
            'violation': 10,
            'warning': 5
        }

        score = base_score
        score -= len(critical_issues) * score_deductions['critical']
        score -= len(violations) * score_deductions['violation']
        score = max(0, score)

        # ステータス判定
        if critical_issues:
            status = GateStatus.BLOCKED
        elif score < 60:
            status = GateStatus.WARNING
        else:
            status = GateStatus.PASSED

        return GateCheckResult(
            status=status,
            violations=violations,
            critical_issues=critical_issues,
            recommendations=recommendations,
            score=score
        )

    def check_csv_operation(self, operation_type: str, file_path: str, data: pd.DataFrame) -> bool:
        """
        CSV操作の監視と制御

        Args:
            operation_type: 'read', 'write', 'merge', 'delete'
            file_path: 対象ファイルパス
            data: 操作対象データ

        Returns:
            bool: 操作の許可/拒否
        """
        print(f"\n🔍 Quality Gate Check: {operation_type} on {file_path}")

        if operation_type == 'write' or operation_type == 'merge':
            # 書き込み/マージ操作は厳格にチェック

            # 1. 重複チェック
            duplicates = data[data.duplicated(['person_name'], keep=False)]
            if len(duplicates) > 0:
                print(f"❌ BLOCKED: {len(duplicates)}件の重複エピソードが検出されました")
                self.blocked_operations.append({
                    'timestamp': datetime.now().isoformat(),
                    'operation': operation_type,
                    'file': file_path,
                    'reason': f'重複エピソード: {duplicates["person_name"].unique().tolist()}'
                })
                return False

            # 2. 各エピソードの品質チェック
            blocked_count = 0
            warning_count = 0

            for idx, row in data.iterrows():
                result = self.check_episode(row.to_dict())

                if result.status == GateStatus.BLOCKED:
                    blocked_count += 1
                    print(f"  ❌ {row['person_name']}: ブロック（スコア: {result.score:.1f}）")
                    for issue in result.critical_issues:
                        print(f"     - {issue}")
                elif result.status == GateStatus.WARNING:
                    warning_count += 1

            if blocked_count > 0:
                print(f"\n❌ 操作をブロック: {blocked_count}件の重大な問題が検出されました")
                return False

            if warning_count > 0:
                print(f"\n⚠️ 警告: {warning_count}件の軽微な問題が検出されました")

        # 操作を承認
        print(f"✅ 操作を承認: {file_path}")
        self.approved_operations.append({
            'timestamp': datetime.now().isoformat(),
            'operation': operation_type,
            'file': file_path,
            'episodes': len(data)
        })

        return True

    def enforce_single_entry_point(self):
        """
        単一エントリーポイントの強制
        直接的なCSV操作を検出して警告
        """
        # 環境変数でQuality Gateの使用を強制
        if not os.environ.get('QUALITY_GATE_ACTIVE'):
            print("⚠️ 警告: Quality Gateを経由しない操作が検出されました")
            print("  すべてのCSV操作はEnhancedQualityGateを使用してください")

    def generate_audit_report(self):
        """監査レポートの生成"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f'quality_gate_audit_{timestamp}.json'

        report = {
            'timestamp': timestamp,
            'blocked_operations': self.blocked_operations,
            'approved_operations': self.approved_operations,
            'statistics': {
                'total_blocked': len(self.blocked_operations),
                'total_approved': len(self.approved_operations)
            }
        }

        import json
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"📋 監査レポート生成: {report_file}")
        return report_file

# グローバルインスタンス（シングルトン）
quality_gate = EnhancedQualityGate()

def safe_csv_write(df: pd.DataFrame, file_path: str) -> bool:
    """
    Quality Gate経由の安全なCSV書き込み

    使用例:
        if safe_csv_write(df, 'output.csv'):
            print("書き込み成功")
        else:
            print("品質基準を満たしていません")
    """
    global quality_gate

    # Quality Gateのチェック
    if not quality_gate.check_csv_operation('write', file_path, df):
        return False

    # ロック取得
    if not quality_gate.acquire_lock():
        return False

    try:
        # CSV書き込み
        with open(file_path, 'w', encoding='utf-8-sig') as f:
            df.to_csv(f, index=False)
        print(f"✅ {file_path} への書き込み完了")
        return True
    finally:
        # ロック解放
        quality_gate.release_lock()

def safe_csv_merge(dfs: List[pd.DataFrame], output_path: str) -> Optional[pd.DataFrame]:
    """
    Quality Gate経由の安全なCSVマージ
    """
    global quality_gate

    # マージ前のチェック
    merged_df = pd.concat(dfs, ignore_index=True)

    if not quality_gate.check_csv_operation('merge', output_path, merged_df):
        return None

    # 重複除去
    merged_df = merged_df.drop_duplicates(subset=['person_name'], keep='first')

    # 最終チェックと書き込み
    if safe_csv_write(merged_df, output_path):
        return merged_df

    return None

def main():
    """デモンストレーション"""
    print("="*70)
    print("🛡️ Enhanced Quality Gate System デモ")
    print("="*70)

    # テスト用データ
    test_data = pd.DataFrame([
        {
            'person_name': 'テスト太郎',
            'episode_age': 30,
            'episode_text': 'これはテストエピソードです。' * 10,  # 150文字程度
            'quality_score': 8.0
        }
    ])

    # Quality Gate経由で書き込みテスト
    print("\n📝 テスト: Quality Gate経由の書き込み")
    if safe_csv_write(test_data, 'test_output.csv'):
        print("  成功！")
    else:
        print("  ブロックされました")

    # 監査レポート生成
    report_file = quality_gate.generate_audit_report()
    print(f"\n✅ 監査レポート: {report_file}")

if __name__ == "__main__":
    main()