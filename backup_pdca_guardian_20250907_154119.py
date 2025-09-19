#!/usr/bin/env python3
"""
PDCA Guardian System - プロジェクトルール永続適用システム
PDCAサイクルの監視と違反防止を行う品質保証システム

このシステムはプロジェクトの品質を守る最後の砦として機能します。
過去の失敗を記憶し、同じ過ちを二度と繰り返さないよう監視します。
"""

import json
import os
import sys
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import hashlib
import traceback

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)


class Priority(Enum):
    """ルール優先度"""
    CRITICAL = "CRITICAL"  # 違反したら即座に停止
    HIGH = "HIGH"          # 重要な警告
    MEDIUM = "MEDIUM"      # 通常の警告
    LOW = "LOW"            # 情報レベル


class ViolationType(Enum):
    """違反タイプ"""
    CALIBRATED_SCORE_USAGE = "calibrated_score使用"
    API_NOT_USED = "API未使用"
    DUMMY_DATA_RETURN = "ダミーデータ返却"
    QUALITY_GATE_FAILURE = "品質ゲート違反"
    DELETION_RATE_ABNORMAL = "削除率異常"
    PROTECTION_LIST_INSUFFICIENT = "保護リスト不足"
    ERROR_SUPPRESSION = "エラー隠蔽"
    SUBSTRING_MATCHING = "部分文字列マッチング"
    MISSING_DISPLAY_NAME_FIELD = "person_name_displayフィールド欠落"
    INCOMPLETE_PERSON_FIELDS = "必須フィールド不完全"
    DASHBOARD_UPDATE_FAILURE = "ダッシュボード更新失敗"
    DUAL_IMPLEMENTATION_CONFLICT = "二重実装による競合"


@dataclass
class RuleViolation:
    """ルール違反情報"""
    rule_id: str
    violation_type: ViolationType
    description: str
    file_path: Optional[str]
    line_number: Optional[int]
    severity: Priority
    timestamp: datetime = field(default_factory=datetime.now)
    suggested_fix: Optional[str] = None


@dataclass
class PDCACycle:
    """PDCAサイクル記録"""
    cycle_id: str
    plan: Dict[str, Any]
    do: Dict[str, Any]
    check: Dict[str, Any]
    act: Dict[str, Any]
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str = "in_progress"
    violations: List[RuleViolation] = field(default_factory=list)


class PDCAGuardian:
    """
    PDCA監視システム
    
    プロジェクトルールの永続的適用と
    品質保証を実現する統合管理システム
    """
    
    def __init__(self, memory_file: str = "project_memory.json"):
        """初期化"""
        self.memory_file = Path(memory_file)
        self.memory = self._load_memory()
        self.current_cycle: Optional[PDCACycle] = None
        self.violation_count = 0
        
        logger.info("="*60)
        logger.info("🛡️ PDCA Guardian System 起動")
        logger.info("="*60)
        logger.info(f"📚 永続ルール数: {len(self.memory['permanent_rules'])}")
        logger.info(f"❌ 過去の失敗パターン: {len(self.memory['failed_patterns'])}")
        logger.info(f"✅ 成功パターン: {len(self.memory['success_patterns'])}")
    
    def _load_memory(self) -> Dict:
        """プロジェクトメモリ読み込み"""
        if self.memory_file.exists():
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logger.warning(f"⚠️ {self.memory_file} が見つかりません。新規作成します。")
            return self._initialize_memory()
    
    def _initialize_memory(self) -> Dict:
        """メモリ初期化"""
        return {
            "metadata": {
                "version": "1.0.0",
                "created": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            },
            "permanent_rules": [],
            "quality_metrics": {},
            "failed_patterns": [],
            "success_patterns": [],
            "pdca_history": [],
            "improvement_log": []
        }
    
    def _save_memory(self):
        """メモリ永続化"""
        self.memory['metadata']['last_updated'] = datetime.now().isoformat()
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            json.dump(self.memory, f, ensure_ascii=False, indent=2, default=str)
    
    # ========== PDCAサイクル管理 ==========
    
    def start_pdca_cycle(self, plan: Dict[str, Any]) -> str:
        """
        新しいPDCAサイクル開始
        
        Args:
            plan: 計画内容
            
        Returns:
            サイクルID
        """
        cycle_id = self._generate_cycle_id()
        
        self.current_cycle = PDCACycle(
            cycle_id=cycle_id,
            plan=plan,
            do={},
            check={},
            act={},
            started_at=datetime.now()
        )
        
        logger.info(f"\n🔄 PDCAサイクル開始: {cycle_id}")
        logger.info(f"📋 Plan: {plan.get('description', 'No description')}")
        
        # 事前チェック
        violations = self.check_plan_compliance(plan)
        if violations:
            self._handle_violations(violations)
        
        return cycle_id
    
    def _generate_cycle_id(self) -> str:
        """サイクルID生成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_part = hashlib.md5(os.urandom(16)).hexdigest()[:8]
        return f"PDCA_{timestamp}_{random_part}"
    
    def update_do_phase(self, implementation: Dict[str, Any]):
        """Do フェーズ更新"""
        if not self.current_cycle:
            logger.error("❌ アクティブなPDCAサイクルがありません")
            return
        
        self.current_cycle.do = implementation
        logger.info(f"🔨 Do: {implementation.get('action', 'No action')}")
        
        # 実装中チェック
        self.validate_implementation(implementation)
    
    def update_check_phase(self, verification: Dict[str, Any]):
        """Check フェーズ更新"""
        if not self.current_cycle:
            return
        
        self.current_cycle.check = verification
        logger.info(f"🔍 Check: {verification.get('result', 'No result')}")
        
        # 結果検証
        self.verify_results(verification)
    
    def update_act_phase(self, improvement: Dict[str, Any]):
        """Act フェーズ更新"""
        if not self.current_cycle:
            return
        
        self.current_cycle.act = improvement
        self.current_cycle.completed_at = datetime.now()
        self.current_cycle.status = "completed"
        
        logger.info(f"📈 Act: {improvement.get('action', 'No action')}")
        
        # 履歴に追加
        self._save_cycle_to_history()
        
        # 学習と改善
        self._learn_from_cycle()
    
    def _save_cycle_to_history(self):
        """サイクルを履歴に保存"""
        if not self.current_cycle:
            return
        
        cycle_data = {
            "cycle_id": self.current_cycle.cycle_id,
            "plan": self.current_cycle.plan,
            "do": self.current_cycle.do,
            "check": self.current_cycle.check,
            "act": self.current_cycle.act,
            "started_at": self.current_cycle.started_at.isoformat(),
            "completed_at": self.current_cycle.completed_at.isoformat() if self.current_cycle.completed_at else None,
            "status": self.current_cycle.status,
            "violations": [self._violation_to_dict(v) for v in self.current_cycle.violations]
        }
        
        self.memory['pdca_history'].append(cycle_data)
        
        # 最新10件のみ保持
        if len(self.memory['pdca_history']) > 10:
            self.memory['pdca_history'] = self.memory['pdca_history'][-10:]
        
        self._save_memory()
    
    def _violation_to_dict(self, violation: RuleViolation) -> Dict:
        """違反オブジェクトを辞書に変換"""
        return {
            "rule_id": violation.rule_id,
            "violation_type": violation.violation_type.value,
            "description": violation.description,
            "file_path": violation.file_path,
            "line_number": violation.line_number,
            "severity": violation.severity.value,
            "timestamp": violation.timestamp.isoformat(),
            "suggested_fix": violation.suggested_fix
        }
    
    def _learn_from_cycle(self):
        """サイクルから学習"""
        if not self.current_cycle:
            return
        
        # 違反があった場合は失敗パターンに追加
        if self.current_cycle.violations:
            for violation in self.current_cycle.violations:
                self._add_failed_pattern(violation)
        
        # 成功した場合は成功パターンに追加
        elif self.current_cycle.status == "completed":
            self._add_success_pattern()
    
    def _add_failed_pattern(self, violation: RuleViolation):
        """失敗パターン追加"""
        pattern = {
            "id": f"FAIL_{len(self.memory['failed_patterns']) + 1:03d}",
            "date": datetime.now().isoformat(),
            "pattern": violation.violation_type.value,
            "description": violation.description,
            "consequence": "品質問題発生",
            "prevention": violation.suggested_fix or "ルールの徹底"
        }
        
        self.memory['failed_patterns'].append(pattern)
        self._save_memory()
    
    def _add_success_pattern(self):
        """成功パターン追加"""
        if not self.current_cycle:
            return
        
        pattern = {
            "id": f"SUCCESS_{len(self.memory['success_patterns']) + 1:03d}",
            "date": datetime.now().isoformat(),
            "pattern": self.current_cycle.plan.get('description', ''),
            "description": "PDCAサイクル成功完了",
            "result": self.current_cycle.check.get('result', ''),
            "reusable": True
        }
        
        self.memory['success_patterns'].append(pattern)
        self._save_memory()
    
    # ========== ルールチェック機能 ==========
    
    def check_plan_compliance(self, plan: Dict[str, Any]) -> List[RuleViolation]:
        """計画のルール準拠チェック"""
        violations = []
        
        # calibrated_score使用チェック
        if 'calibrated_score' in str(plan):
            violations.append(RuleViolation(
                rule_id="RULE_001",
                violation_type=ViolationType.CALIBRATED_SCORE_USAGE,
                description="計画にcalibrated_scoreの使用が含まれています",
                file_path=None,
                line_number=None,
                severity=Priority.CRITICAL,
                suggested_fix="calibrated_scoreを完全に除外してください"
            ))
        
        # API使用チェック
        if plan.get('use_apis', True) is False:
            violations.append(RuleViolation(
                rule_id="RULE_002",
                violation_type=ViolationType.API_NOT_USED,
                description="APIを使用しない計画です",
                file_path=None,
                line_number=None,
                severity=Priority.CRITICAL,
                suggested_fix="利用可能なAPIを必ず使用してください"
            ))
        
        return violations
    
    def validate_implementation(self, implementation: Dict[str, Any]) -> List[RuleViolation]:
        """実装の妥当性検証"""
        violations = []
        
        code = implementation.get('code', '')
        file_path = implementation.get('file_path', '')
        
        # ダミーデータ返却チェック
        if "return {'results': 0, 'data': []}" in code or "return []" in code:
            violations.append(RuleViolation(
                rule_id="RULE_003",
                violation_type=ViolationType.DUMMY_DATA_RETURN,
                description="ダミーデータを返却するコードが検出されました",
                file_path=file_path,
                line_number=None,
                severity=Priority.CRITICAL,
                suggested_fix="エラーを発生させて処理を停止してください"
            ))
        
        # エラー隠蔽チェック
        if "except:" in code and "pass" in code:
            violations.append(RuleViolation(
                rule_id="RULE_008",
                violation_type=ViolationType.ERROR_SUPPRESSION,
                description="エラーを握りつぶすコードが検出されました",
                file_path=file_path,
                line_number=None,
                severity=Priority.HIGH,
                suggested_fix="適切なエラーハンドリングを実装してください"
            ))
        
        # 部分文字列マッチングチェック
        if "if protected in name" in code:
            violations.append(RuleViolation(
                rule_id="RULE_009",
                violation_type=ViolationType.SUBSTRING_MATCHING,
                description="部分文字列マッチングが検出されました",
                file_path=file_path,
                line_number=None,
                severity=Priority.HIGH,
                suggested_fix="完全一致（==）を使用してください"
            ))
        
        if violations:
            self._handle_violations(violations)
        
        return violations
    
    def verify_results(self, results: Dict[str, Any]) -> bool:
        """結果の妥当性検証"""
        violations = []
        
        # 削除率チェック
        deletion_rate = results.get('deletion_rate', 0)
        if deletion_rate < 0.10 or deletion_rate > 0.20:
            violations.append(RuleViolation(
                rule_id="RULE_004",
                violation_type=ViolationType.DELETION_RATE_ABNORMAL,
                description=f"削除率が異常です: {deletion_rate:.1%}",
                file_path=None,
                line_number=None,
                severity=Priority.HIGH,
                suggested_fix="削除基準を見直してください"
            ))
        
        # 有名人スコアチェック
        celebrity_scores = results.get('celebrity_scores', {})
        for name, score in celebrity_scores.items():
            if name in ["HIKAKIN", "ヒカキン", "大谷翔平"] and score < 7.0:
                violations.append(RuleViolation(
                    rule_id="RULE_005",
                    violation_type=ViolationType.QUALITY_GATE_FAILURE,
                    description=f"{name}のスコアが低すぎます: {score}",
                    file_path=None,
                    line_number=None,
                    severity=Priority.CRITICAL,
                    suggested_fix="スコアリングアルゴリズムを修正してください"
                ))
        
        if violations:
            self._handle_violations(violations)
            return False
        
        return True
    
    def _handle_violations(self, violations: List[RuleViolation]):
        """違反処理"""
        if not violations:
            return
        
        logger.error("="*60)
        logger.error("🚨 ルール違反が検出されました！")
        logger.error("="*60)
        
        critical_count = 0
        
        for violation in violations:
            # 現在のサイクルに違反を追加
            if self.current_cycle:
                self.current_cycle.violations.append(violation)
            
            # ログ出力
            emoji = {
                Priority.CRITICAL: "🔴",
                Priority.HIGH: "🟡",
                Priority.MEDIUM: "🟠",
                Priority.LOW: "🔵"
            }.get(violation.severity, "⚪")
            
            logger.error(f"\n{emoji} [{violation.severity.value}] {violation.violation_type.value}")
            logger.error(f"   規則: {violation.rule_id}")
            logger.error(f"   説明: {violation.description}")
            if violation.file_path:
                logger.error(f"   場所: {violation.file_path}:{violation.line_number}")
            if violation.suggested_fix:
                logger.error(f"   修正案: {violation.suggested_fix}")
            
            if violation.severity == Priority.CRITICAL:
                critical_count += 1
            
            # メモリに違反を記録
            self._record_violation(violation)
        
        # CRITICALがあれば処理停止
        if critical_count > 0:
            logger.error("\n❌ CRITICAL違反のため処理を停止します")
            raise SystemError(f"CRITICAL違反が{critical_count}件検出されました。処理を中止します。")
    
    def _record_violation(self, violation: RuleViolation):
        """違反をメモリに記録"""
        # 該当ルールを探す
        for rule in self.memory['permanent_rules']:
            if rule['id'] == violation.rule_id:
                if 'violations' not in rule:
                    rule['violations'] = []
                
                rule['violations'].append({
                    "date": violation.timestamp.isoformat(),
                    "type": violation.violation_type.value,
                    "description": violation.description
                })
                
                # 最新5件のみ保持
                if len(rule['violations']) > 5:
                    rule['violations'] = rule['violations'][-5:]
                
                break
        
        self._save_memory()
    
    # ========== ファイルチェック機能 ==========
    
    def check_file(self, file_path: str) -> List[RuleViolation]:
        """
        ファイルのルール違反チェック
        
        Args:
            file_path: チェック対象ファイル
            
        Returns:
            違反リスト
        """
        violations = []
        
        if not os.path.exists(file_path):
            logger.warning(f"⚠️ ファイルが存在しません: {file_path}")
            return violations
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
        
        # 各行をチェック
        for i, line in enumerate(lines, 1):
            # calibrated_score使用チェック
            if 'calibrated_score' in line and not line.strip().startswith('#'):
                violations.append(RuleViolation(
                    rule_id="RULE_001",
                    violation_type=ViolationType.CALIBRATED_SCORE_USAGE,
                    description="calibrated_scoreの使用が検出されました",
                    file_path=file_path,
                    line_number=i,
                    severity=Priority.CRITICAL,
                    suggested_fix="calibrated_scoreを使用しないでください"
                ))
            
            # ダミーデータチェック
            if "return {'results': 0" in line or "return []" in line:
                if "raise" not in lines[max(0, i-3):i]:  # 前3行にraiseがない
                    violations.append(RuleViolation(
                        rule_id="RULE_003",
                        violation_type=ViolationType.DUMMY_DATA_RETURN,
                        description="ダミーデータ返却が検出されました",
                        file_path=file_path,
                        line_number=i,
                        severity=Priority.CRITICAL,
                        suggested_fix="エラーを発生させてください"
                    ))
            
            # エラー隠蔽チェック
            if "except:" in line:
                # 次の数行をチェック
                for j in range(i, min(i+5, len(lines))):
                    if "pass" in lines[j]:
                        violations.append(RuleViolation(
                            rule_id="RULE_008",
                            violation_type=ViolationType.ERROR_SUPPRESSION,
                            description="エラー隠蔽が検出されました",
                            file_path=file_path,
                            line_number=i,
                            severity=Priority.HIGH,
                            suggested_fix="適切なエラーハンドリングを実装してください"
                        ))
                        break
        
        return violations
    
    # ========== レポート生成 ==========
    
    def generate_report(self) -> str:
        """PDCAレポート生成"""
        report = []
        report.append("="*60)
        report.append("📊 PDCA Guardian Report")
        report.append("="*60)
        report.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # ルール違反統計
        report.append("## 📋 ルール違反統計")
        total_violations = 0
        for rule in self.memory['permanent_rules']:
            violation_count = len(rule.get('violations', []))
            if violation_count > 0:
                total_violations += violation_count
                report.append(f"- {rule['id']}: {violation_count}件")
                report.append(f"  {rule['rule']}")
        
        if total_violations == 0:
            report.append("✅ 違反なし")
        
        report.append("")
        
        # 最近のPDCAサイクル
        report.append("## 🔄 最近のPDCAサイクル")
        if self.memory['pdca_history']:
            for cycle in self.memory['pdca_history'][-3:]:
                report.append(f"\n### {cycle['cycle_id']}")
                report.append(f"- Plan: {cycle['plan'].get('description', 'N/A')}")
                report.append(f"- Do: {cycle['do'].get('action', 'N/A')}")
                report.append(f"- Check: {cycle['check'].get('result', 'N/A')}")
                report.append(f"- Act: {cycle['act'].get('action', 'N/A')}")
                report.append(f"- 違反: {len(cycle.get('violations', []))}件")
        else:
            report.append("履歴なし")
        
        report.append("")
        
        # 改善提案
        report.append("## 💡 改善提案")
        if self.memory['failed_patterns']:
            report.append("最近の失敗パターンに基づく提案:")
            for pattern in self.memory['failed_patterns'][-3:]:
                report.append(f"- {pattern['pattern']}: {pattern['prevention']}")
        
        report.append("")
        report.append("="*60)
        
        return "\n".join(report)
    
    # ========== 品質ゲート ==========
    
    def quality_gate_check(self, metrics: Dict[str, Any]) -> bool:
        """
        品質ゲートチェック
        
        Args:
            metrics: 測定メトリクス
            
        Returns:
            合格/不合格
        """
        passed = True
        
        # API応答率チェック
        api_rate = metrics.get('api_response_rate', 0)
        if api_rate < 0.95:
            logger.error(f"❌ API応答率が基準未満: {api_rate:.1%} < 95%")
            passed = False
        
        # 削除率チェック
        deletion_rate = metrics.get('deletion_rate', 0)
        if not (0.10 <= deletion_rate <= 0.20):
            logger.error(f"❌ 削除率が範囲外: {deletion_rate:.1%}")
            passed = False
        
        # ダミーデータチェック
        dummy_count = metrics.get('dummy_data_count', 0)
        if dummy_count > 0:
            logger.error(f"❌ ダミーデータが検出されました: {dummy_count}件")
            passed = False
        
        # 有名人スコアチェック
        celebrity_scores = metrics.get('celebrity_scores', {})
        for name in ["HIKAKIN", "大谷翔平", "Ado"]:
            if name in celebrity_scores and celebrity_scores[name] < 7.0:
                logger.error(f"❌ {name}のスコアが低すぎます: {celebrity_scores[name]}")
                passed = False
        
        if passed:
            logger.info("✅ 品質ゲート通過")
        else:
            logger.error("❌ 品質ゲート不合格")
        
        return passed


def main():
    """メイン実行"""
    guardian = PDCAGuardian()
    
    # テスト: PDCAサイクル実行
    logger.info("\n" + "="*60)
    logger.info("テスト実行")
    logger.info("="*60)
    
    # 1. 良いサイクル
    logger.info("\n### 良いPDCAサイクルの例")
    cycle_id = guardian.start_pdca_cycle({
        "description": "複数APIを統合した知名度評価システム",
        "use_apis": True,
        "multi_api_integration": True
    })
    
    guardian.update_do_phase({
        "action": "ultimate_recognition_system.pyの実装",
        "code": "score = api_result['score']",
        "file_path": "ultimate_recognition_system.py"
    })
    
    guardian.update_check_phase({
        "result": "成功",
        "deletion_rate": 0.15,
        "celebrity_scores": {"HIKAKIN": 8.5, "大谷翔平": 9.0}
    })
    
    guardian.update_act_phase({
        "action": "本番環境へのデプロイ準備"
    })
    
    # 2. 悪いサイクル（違反あり）
    logger.info("\n### 違反のあるPDCAサイクルの例")
    try:
        cycle_id = guardian.start_pdca_cycle({
            "description": "簡易版知名度評価",
            "use_apis": False,  # 違反！
            "calibrated_score": True  # 違反！
        })
    except SystemError as e:
        logger.info(f"期待通りエラー: {e}")
    
    # 3. ファイルチェック
    logger.info("\n### ファイルチェックの例")
    test_file = "apply_recognition_simple.py"
    if os.path.exists(test_file):
        violations = guardian.check_file(test_file)
        if violations:
            logger.info(f"✅ {len(violations)}件の違反を検出")
    
    # 4. レポート生成
    logger.info("\n### レポート生成")
    report = guardian.generate_report()
    print(report)
    
    # 5. 品質ゲートチェック
    logger.info("\n### 品質ゲートチェック")
    metrics = {
        "api_response_rate": 0.98,
        "deletion_rate": 0.15,
        "dummy_data_count": 0,
        "celebrity_scores": {
            "HIKAKIN": 8.5,
            "大谷翔平": 9.2,
            "Ado": 8.0
        }
    }
    
    if guardian.quality_gate_check(metrics):
        logger.info("✅ 品質基準をクリア")
    else:
        logger.error("❌ 品質基準未達")
    
    logger.info("\n✅ PDCAガーディアンのテスト完了")


if __name__ == "__main__":
    main()