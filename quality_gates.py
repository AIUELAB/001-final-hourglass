#!/usr/bin/env python3
"""
品質ゲートシステム - コード実行前の自動検証
すべてのスクリプト実行前に品質チェックを強制
"""

import os
import sys
import json
import ast
import logging
import traceback
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
from enum import Enum
import importlib.util
import subprocess
from priority_japanese_config import get_japanese_priority, get_priority_display

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GateStatus(Enum):
    """ゲートステータス"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


class QualityGate:
    """品質ゲート基底クラス"""
    
    def __init__(self, name: str, priority: str = "HIGH"):
        self.name = name
        self.priority = priority
        self.status = GateStatus.SKIPPED
        self.message = ""
        self.details = {}
    
    def check(self, context: Dict[str, Any]) -> GateStatus:
        """ゲートチェック実行"""
        raise NotImplementedError
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            "name": self.name,
            "priority": self.priority,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": datetime.now().isoformat()
        }


class SystemReadinessGate(QualityGate):
    """システム準備確認ゲート"""
    
    def __init__(self):
        super().__init__("システム準備確認", "CRITICAL")
    
    def check(self, context: Dict[str, Any]) -> GateStatus:
        """API設定と依存関係をチェック"""
        try:
            issues = []
            
            # 環境変数チェック
            env_file = Path(".env")
            if not env_file.exists():
                issues.append(".envファイルが存在しません")
            else:
                with open(env_file) as f:
                    env_content = f.read()
                    
                required_apis = [
                    "SERPAPI_KEY",  # 修正: 正しいキー名
                    "BRAVE_API_KEY", 
                    "YOUTUBE_API_KEY",
                    "NEWS_API_KEY"
                ]
                
                for api in required_apis:
                    if api not in env_content:
                        issues.append(f"{api}が設定されていません")
            
            # プロジェクトメモリ確認
            memory_file = Path("project_memory.json")
            if not memory_file.exists():
                issues.append("project_memory.jsonが存在しません")
            
            # 保護リスト確認
            if not Path("textbook_person_protector.py").exists():
                issues.append("教科書人物保護リストが存在しません")
            
            if issues:
                self.message = f"システム準備不足: {', '.join(issues)}"
                self.details = {"issues": issues}
                self.status = GateStatus.FAILED
                return self.status
            
            self.message = "システム準備完了"
            self.status = GateStatus.PASSED
            return self.status
            
        except Exception as e:
            self.message = f"システムチェック中にエラー: {str(e)}"
            self.status = GateStatus.FAILED
            return self.status


class NoCalibrationScoreGate(QualityGate):
    """calibrated_score使用禁止ゲート"""
    
    def __init__(self):
        super().__init__("calibrated_score使用禁止", "CRITICAL")
    
    def check(self, context: Dict[str, Any]) -> GateStatus:
        """calibrated_scoreの使用を検出"""
        try:
            script_path = context.get("script_path")
            if not script_path:
                self.status = GateStatus.SKIPPED
                return self.status
            
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'calibrated_score' in content:
                # ASTで詳細解析
                tree = ast.parse(content)
                violations = []
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Str) and 'calibrated_score' in node.s:
                        violations.append(f"行{node.lineno}: 文字列内にcalibrated_score")
                    elif isinstance(node, ast.Name) and node.id == 'calibrated_score':
                        violations.append(f"行{node.lineno}: 変数名calibrated_score")
                
                if violations:
                    self.message = f"calibrated_scoreの使用を検出: {len(violations)}箇所"
                    self.details = {"violations": violations}
                    self.status = GateStatus.FAILED
                    return self.status
            
            self.message = "calibrated_scoreの使用なし"
            self.status = GateStatus.PASSED
            return self.status
            
        except Exception as e:
            self.message = f"チェック中にエラー: {str(e)}"
            self.status = GateStatus.FAILED
            return self.status


class APIUsageGate(QualityGate):
    """API使用確認ゲート"""
    
    def __init__(self):
        super().__init__("API使用確認", "HIGH")
    
    def check(self, context: Dict[str, Any]) -> GateStatus:
        """API使用の確認"""
        try:
            script_path = context.get("script_path")
            if not script_path:
                self.status = GateStatus.SKIPPED
                return self.status
            
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # API使用パターンを検出
            api_patterns = [
                'serpapi',
                'brave_search',
                'youtube_api',
                'news_api',
                'requests.get',
                'aiohttp'
            ]
            
            api_found = []
            for pattern in api_patterns:
                if pattern.lower() in content.lower():
                    api_found.append(pattern)
            
            # 認識システムの場合はAPI必須
            if 'recognition' in script_path.lower() or 'score' in script_path.lower():
                if not api_found:
                    self.message = "認識システムなのにAPI使用が検出されません"
                    self.status = GateStatus.FAILED
                    return self.status
            
            if api_found:
                self.message = f"API使用確認: {', '.join(api_found)}"
                self.details = {"apis": api_found}
                self.status = GateStatus.PASSED
            else:
                self.message = "API使用なし（簡易版の可能性）"
                self.status = GateStatus.WARNING
            
            return self.status
            
        except Exception as e:
            self.message = f"チェック中にエラー: {str(e)}"
            self.status = GateStatus.FAILED
            return self.status


class ProtectionListGate(QualityGate):
    """保護リスト確認ゲート"""
    
    def __init__(self):
        super().__init__("保護リスト確認", "HIGH")
    
    def check(self, context: Dict[str, Any]) -> GateStatus:
        """十分な保護リストの確認"""
        try:
            script_path = context.get("script_path")
            if not script_path:
                self.status = GateStatus.SKIPPED
                return self.status
            
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 削除や認識に関するスクリプトの場合
            if any(word in script_path.lower() for word in ['delete', 'remove', 'recognition', 'score']):
                # 保護リストのサイズチェック
                if 'protected_names' in content:
                    # 簡易的なカウント
                    import re
                    matches = re.findall(r"'[^']+'\s*,", content)
                    protected_count = len(matches)
                    
                    if protected_count < 50:
                        self.message = f"保護リストが不十分: {protected_count}名のみ"
                        self.details = {"count": protected_count, "minimum": 50}
                        self.status = GateStatus.WARNING
                        return self.status
                    else:
                        self.message = f"十分な保護リスト: {protected_count}名"
                        self.status = GateStatus.PASSED
                        return self.status
                
                # textbook_person_protectorのインポート確認
                if 'textbook_person_protector' in content:
                    self.message = "教科書人物保護リストを使用"
                    self.status = GateStatus.PASSED
                    return self.status
                
                self.message = "保護リストが見つかりません"
                self.status = GateStatus.WARNING
                return self.status
            
            self.status = GateStatus.SKIPPED
            return self.status
            
        except Exception as e:
            self.message = f"チェック中にエラー: {str(e)}"
            self.status = GateStatus.FAILED
            return self.status


class ErrorHandlingGate(QualityGate):
    """エラーハンドリング確認ゲート"""
    
    def __init__(self):
        super().__init__("エラーハンドリング", "MEDIUM")
    
    def check(self, context: Dict[str, Any]) -> GateStatus:
        """適切なエラーハンドリングの確認"""
        try:
            script_path = context.get("script_path")
            if not script_path:
                self.status = GateStatus.SKIPPED
                return self.status
            
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # try-exceptブロックの解析
            bare_excepts = []
            proper_handlers = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    if node.type is None:  # bare except
                        bare_excepts.append(node.lineno)
                    else:
                        proper_handlers.append(node.lineno)
            
            if bare_excepts:
                self.message = f"裸のexcept節を検出: {len(bare_excepts)}箇所"
                self.details = {"bare_excepts": bare_excepts}
                self.status = GateStatus.WARNING
            elif proper_handlers:
                self.message = f"適切なエラーハンドリング: {len(proper_handlers)}箇所"
                self.status = GateStatus.PASSED
            else:
                self.message = "エラーハンドリングなし"
                self.status = GateStatus.WARNING
            
            return self.status
            
        except Exception as e:
            self.message = f"チェック中にエラー: {str(e)}"
            self.status = GateStatus.FAILED
            return self.status


class NoSimpleFallbackGate(QualityGate):
    """シンプル版・高速版・簡易版への移行禁止ゲート"""
    
    def __init__(self):
        super().__init__("品質妥協版禁止", "CRITICAL")
    
    def check(self, context: Dict[str, Any]) -> GateStatus:
        """シンプル版・高速版・簡易版の検出"""
        try:
            script_path = context.get("script_path")
            if not script_path:
                self.status = GateStatus.SKIPPED
                return self.status
            
            # ファイル名チェック
            filename = Path(script_path).name.lower()
            forbidden_patterns = [
                'simple_', 'simplified_', 'シンプル',
                'fast_', 'quick_', '高速', 'rapid_',
                '簡易', 'lite_', 'minimal_', 'basic_'
            ]
            
            for pattern in forbidden_patterns:
                if pattern in filename:
                    self.message = f"品質妥協版のファイル名を検出: {pattern} in {filename}"
                    self.details = {"detected_pattern": pattern, "filename": filename}
                    self.status = GateStatus.FAILED
                    return self.status
            
            # ファイル内容チェック
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 危険なコメントパターン
            dangerous_comments = [
                '簡易版', 'シンプル版', '高速版',
                'simplified version', 'simple version', 'fast version',
                'quick implementation', 'temporary solution',
                'fallback', 'mock implementation'
            ]
            
            for pattern in dangerous_comments:
                if pattern.lower() in content.lower():
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        if pattern.lower() in line.lower():
                            self.message = f"品質妥協パターンを検出: '{pattern}' at line {i}"
                            self.details = {"pattern": pattern, "line": i}
                            self.status = GateStatus.FAILED
                            return self.status
            
            # API fallback検出
            if 'if not' in content and ('api' in content.lower() or 'key' in content.lower()):
                # APIキー不在時の処理を詳細チェック
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if 'if not' in line and any(x in line.lower() for x in ['api', 'key', '_key']):
                        # 次の数行をチェック
                        for j in range(i, min(i+5, len(lines))):
                            if 'return' in lines[j]:
                                # 誤検出防止: ==, !=, len() の比較は除外
                                if ('== 0' in lines[j] or '!= 0' in lines[j] or 
                                    'len(' in lines[j] or '> 0' in lines[j] or '< 0' in lines[j]):
                                    continue
                                # ダミーデータ返却の検出（より厳密に）
                                if ('return 0' in lines[j] or 'return []' in lines[j] or 
                                    'return {}' in lines[j] or "return ''" in lines[j] or 
                                    'return ""' in lines[j]):
                                    self.message = f"API障害時のダミーデータ返却を検出: line {j+1}"
                                    self.details = {"line": j+1, "code": lines[j].strip()}
                                    self.status = GateStatus.FAILED
                                    return self.status
            
            self.message = "品質妥協版なし - 品質担保優先"
            self.status = GateStatus.PASSED
            return self.status
            
        except Exception as e:
            self.message = f"チェック中にエラー: {str(e)}"
            self.status = GateStatus.FAILED
            return self.status


class TimeEstimationGate(QualityGate):
    """時間見積もり品質ゲート（RULE_015実装）"""
    
    def __init__(self):
        super().__init__("時間見積もり妥当性", "CRITICAL")
    
    def check(self, context: Dict[str, Any]) -> GateStatus:
        """時間見積もりの妥当性チェック"""
        try:
            script_path = context.get("script_path")
            if not script_path:
                self.status = GateStatus.SKIPPED
                return self.status
            
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 危険な時間短縮パターン
            dangerous_patterns = [
                # 処理時間の大幅短縮を示唆するパターン
                (r'(\d+)時間.*?(\d+)分', 'hours_to_minutes'),
                (r'(\d+)倍.*?高速', 'unrealistic_speedup'),
                (r'処理時間.*?90%.*?削減', 'extreme_reduction'),
                (r'(\d+)分で完了', 'unrealistic_completion'),
                
                # 品質妥協を示すパターン
                (r'効率.*?優先', 'efficiency_over_quality'),
                (r'時間.*?短縮', 'time_reduction_focus'),
                (r'クイック.*?処理', 'quick_processing'),
                (r'部分的.*?実行', 'partial_execution')
            ]
            
            violations = []
            lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                for pattern, violation_type in dangerous_patterns:
                    import re
                    if re.search(pattern, line, re.IGNORECASE):
                        violations.append({
                            "line": i,
                            "type": violation_type,
                            "text": line.strip()[:100]
                        })
            
            # 処理時間に関するコメントの検証
            time_comments = []
            for i, line in enumerate(lines, 1):
                if '#' in line:
                    comment = line[line.index('#'):].strip()
                    if any(word in comment.lower() for word in ['時間', 'hour', 'minute', '分', '処理時間']):
                        time_comments.append({
                            "line": i,
                            "comment": comment[:100]
                        })
            
            # 判定
            if violations:
                self.message = f"非現実的な時間見積もりを検出: {len(violations)}箇所"
                self.details = {"violations": violations[:5]}  # 最初の5件
                self.status = GateStatus.FAILED
            elif time_comments:
                # 時間に関するコメントがある場合は詳細チェック
                quality_mentioned = any('品質' in c['comment'] or 'quality' in c['comment'].lower() 
                                       for c in time_comments)
                if not quality_mentioned:
                    self.message = "時間見積もりに品質保証への言及なし"
                    self.details = {"time_comments": time_comments[:3]}
                    self.status = GateStatus.WARNING
                else:
                    self.message = "時間見積もりは品質優先で適切"
                    self.status = GateStatus.PASSED
            else:
                self.message = "時間見積もりチェック完了"
                self.status = GateStatus.PASSED
            
            return self.status
            
        except Exception as e:
            self.message = f"チェック中にエラー: {str(e)}"
            self.status = GateStatus.FAILED
            return self.status


class QualityGateSystem:
    """品質ゲートシステム統合"""
    
    def __init__(self):
        self.gates = [
            SystemReadinessGate(),
            NoCalibrationScoreGate(),
            NoSimpleFallbackGate(),  # CRITICAL: 品質妥協版禁止
            TimeEstimationGate(),     # CRITICAL: 時間見積もり妥当性
            APIUsageGate(),
            ProtectionListGate(),
            ErrorHandlingGate()
        ]
        self.results = []
        self.passed = False
    
    def check_script(self, script_path: str) -> Tuple[bool, List[Dict]]:
        """スクリプトの品質チェック"""
        logger.info(f"🔍 品質ゲートチェック開始: {script_path}")
        
        context = {
            "script_path": script_path,
            "timestamp": datetime.now().isoformat()
        }
        
        critical_failed = False
        high_failed = False
        warnings = []
        
        for gate in self.gates:
            status = gate.check(context)
            result = gate.to_dict()
            self.results.append(result)
            
            if status == GateStatus.FAILED:
                if gate.priority == "CRITICAL":
                    critical_failed = True
                    logger.error(f"❌ {get_priority_display('CRITICAL')}: {gate.name} - {gate.message}")
                elif gate.priority == "HIGH":
                    high_failed = True
                    logger.error(f"❌ {get_priority_display('HIGH')}: {gate.name} - {gate.message}")
                else:
                    logger.warning(f"⚠️ {get_priority_display(gate.priority)}: {gate.name} - {gate.message}")
            elif status == GateStatus.WARNING:
                warnings.append(gate.name)
                logger.warning(f"⚠️ {gate.name} - {gate.message}")
            elif status == GateStatus.PASSED:
                logger.info(f"✅ {gate.name} - {gate.message}")
        
        # 総合判定
        if critical_failed:
            self.passed = False
            logger.error(f"🚫 品質ゲート失敗: {get_priority_display('CRITICAL')}違反あり")
        elif high_failed:
            self.passed = False
            logger.error(f"🚫 品質ゲート失敗: {get_priority_display('HIGH')}違反あり")
        else:
            self.passed = True
            if warnings:
                logger.warning(f"✅ 品質ゲート通過（警告{len(warnings)}件）")
            else:
                logger.info("✨ 品質ゲート完全通過")
        
        return self.passed, self.results
    
    def save_report(self, output_path: str = "quality_gate_report.json"):
        """レポート保存"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "passed": self.passed,
            "gates": self.results,
            "summary": {
                "total": len(self.results),
                "passed": sum(1 for r in self.results if r["status"] == "passed"),
                "failed": sum(1 for r in self.results if r["status"] == "failed"),
                "warnings": sum(1 for r in self.results if r["status"] == "warning"),
                "skipped": sum(1 for r in self.results if r["status"] == "skipped")
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📄 レポート保存: {output_path}")
        return report


def enforce_quality_gates(script_path: str) -> bool:
    """品質ゲート強制実行"""
    gate_system = QualityGateSystem()
    passed, results = gate_system.check_script(script_path)
    
    if not passed:
        logger.error("=" * 60)
        logger.error("品質ゲート違反により実行を停止します")
        logger.error("以下の問題を修正してください:")
        
        for result in results:
            if result["status"] == "failed":
                logger.error(f"  - {result['name']}: {result['message']}")
        
        logger.error("=" * 60)
        
        # レポート保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"quality_gate_failure_{timestamp}.json"
        gate_system.save_report(report_path)
        
        return False
    
    return True


def wrap_script_execution(script_path: str):
    """スクリプト実行のラッパー"""
    # 品質ゲートチェック
    if not enforce_quality_gates(script_path):
        sys.exit(1)
    
    # スクリプト実行
    logger.info(f"🚀 スクリプト実行開始: {script_path}")
    
    try:
        # スクリプトをモジュールとして読み込み
        spec = importlib.util.spec_from_file_location("__main__", script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        logger.info("✅ スクリプト実行完了")
        
    except Exception as e:
        logger.error(f"❌ スクリプト実行中にエラー: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    # テスト実行
    test_script = "apply_recognition_simple.py"
    
    if Path(test_script).exists():
        logger.info(f"🧪 品質ゲートテスト: {test_script}")
        gate_system = QualityGateSystem()
        passed, results = gate_system.check_script(test_script)
        
        # レポート出力
        report = gate_system.save_report()
        
        print("\n" + "=" * 60)
        print("品質ゲートサマリー:")
        print(f"  総合判定: {'✅ PASSED' if passed else '❌ FAILED'}")
        print(f"  通過: {report['summary']['passed']}")
        print(f"  失敗: {report['summary']['failed']}")
        print(f"  警告: {report['summary']['warnings']}")
        print(f"  スキップ: {report['summary']['skipped']}")
        print("=" * 60)
    else:
        logger.warning(f"テストファイルが見つかりません: {test_script}")