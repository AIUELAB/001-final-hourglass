#!/usr/bin/env python3
"""
Rule Violation Detector - ルール違反検出システム
コードやデータを分析してプロジェクトルール違反を自動検出
"""

import ast
import re
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Detection:
    """検出結果"""
    rule_id: str
    violation_type: str
    file_path: str
    line_number: Optional[int]
    column: Optional[int]
    code_snippet: Optional[str]
    severity: str
    message: str
    fix_suggestion: str


class RuleViolationDetector:
    """
    ルール違反検出器
    
    静的解析とパターンマッチングで
    プロジェクトルール違反を自動検出
    """
    
    def __init__(self, memory_file: str = "project_memory.json"):
        """初期化"""
        self.memory = self._load_project_memory(memory_file)
        self.detections: List[Detection] = []
        
        # 検出パターン定義
        self.patterns = self._define_patterns()
        
        logger.info("🔍 Rule Violation Detector 初期化完了")
    
    def _load_project_memory(self, memory_file: str) -> Dict:
        """プロジェクトメモリ読み込み"""
        path = Path(memory_file)
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _define_patterns(self) -> Dict[str, Dict]:
        """検出パターン定義"""
        return {
            # calibrated_score使用
            "calibrated_score_usage": {
                "pattern": r"calibrated_score",
                "exclude_pattern": r"^\s*#",  # コメント行は除外
                "rule_id": "RULE_001",
                "violation_type": "calibrated_score使用",
                "severity": "CRITICAL",
                "message": "calibrated_scoreの使用が検出されました（信頼性なし）",
                "fix": "calibrated_scoreを使用せず、APIベースの評価を実装してください"
            },
            
            # ダミーデータ返却
            "dummy_data_return": {
                "pattern": r"return\s*\{\s*['\"]results['\"]\s*:\s*0\s*,\s*['\"]data['\"]\s*:\s*\[\s*\]\s*\}",
                "rule_id": "RULE_003",
                "violation_type": "ダミーデータ返却",
                "severity": "CRITICAL",
                "message": "ダミーデータを返却するコードが検出されました",
                "fix": "SystemNotReadyError等の例外を発生させて処理を停止してください"
            },
            
            # 空リスト返却
            "empty_list_return": {
                "pattern": r"return\s+\[\s*\](?!\s*#\s*OK)",
                "rule_id": "RULE_003",
                "violation_type": "空データ返却",
                "severity": "HIGH",
                "message": "空リストを返却するコードが検出されました",
                "fix": "適切なエラーハンドリングを実装してください"
            },
            
            # エラー隠蔽
            "error_suppression": {
                "pattern": r"except.*:\s*\n\s*pass",
                "rule_id": "RULE_008",
                "violation_type": "エラー隠蔽",
                "severity": "HIGH",
                "message": "エラーを握りつぶすコードが検出されました",
                "fix": "適切なロギングとエラーハンドリングを実装してください"
            },
            
            # 部分文字列マッチング
            "substring_matching": {
                "pattern": r"if\s+.*\s+in\s+.*name",
                "rule_id": "RULE_009",
                "violation_type": "部分文字列マッチング",
                "severity": "HIGH",
                "message": "名前の部分文字列マッチングが検出されました",
                "fix": "完全一致（==）を使用してください"
            },
            
            # UTF-8のみ（BOMなし）
            "utf8_without_bom": {
                "pattern": r"encoding\s*=\s*['\"]utf-8['\"](?!\s*-sig)",
                "rule_id": "RULE_010",
                "violation_type": "UTF-8 BOM未使用",
                "severity": "MEDIUM",
                "message": "UTF-8 BOMなしのエンコーディングが検出されました",
                "fix": "encoding='utf-8-sig'を使用してExcel互換性を確保してください"
            },
            
            # API未使用の簡易版
            "simple_version_without_api": {
                "pattern": r"(簡易版|simple|シンプル|quick).*(?!api|API)",
                "rule_id": "RULE_002",
                "violation_type": "API未使用",
                "severity": "HIGH",
                "message": "APIを使用しない簡易版の実装が検出されました",
                "fix": "利用可能なAPIを活用してください"
            }
        }
    
    def detect_in_file(self, file_path: str) -> List[Detection]:
        """
        ファイル内の違反検出
        
        Args:
            file_path: 検査対象ファイル
            
        Returns:
            検出リスト
        """
        detections = []
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.warning(f"ファイルが存在しません: {file_path}")
            return detections
        
        # Pythonファイルの場合はAST解析も実施
        if file_path.suffix == '.py':
            detections.extend(self._detect_with_ast(file_path))
        
        # パターンマッチング
        detections.extend(self._detect_with_patterns(file_path))
        
        # CSVファイルの場合はデータ検証
        if file_path.suffix == '.csv':
            detections.extend(self._detect_in_csv(file_path))
        
        self.detections.extend(detections)
        return detections
    
    def _detect_with_ast(self, file_path: Path) -> List[Detection]:
        """AST解析による検出"""
        detections = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source, filename=str(file_path))
            
            # ASTビジターで解析
            visitor = ASTViolationVisitor(str(file_path))
            visitor.visit(tree)
            detections.extend(visitor.detections)
            
        except SyntaxError as e:
            logger.warning(f"構文エラー: {file_path} - {e}")
        except Exception as e:
            logger.error(f"AST解析エラー: {file_path} - {e}")
        
        return detections
    
    def _detect_with_patterns(self, file_path: Path) -> List[Detection]:
        """パターンマッチングによる検出"""
        detections = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_no, line in enumerate(lines, 1):
                for pattern_name, pattern_info in self.patterns.items():
                    # 除外パターンチェック
                    if 'exclude_pattern' in pattern_info:
                        if re.match(pattern_info['exclude_pattern'], line):
                            continue
                    
                    # パターンマッチング
                    match = re.search(pattern_info['pattern'], line)
                    if match:
                        detections.append(Detection(
                            rule_id=pattern_info['rule_id'],
                            violation_type=pattern_info['violation_type'],
                            file_path=str(file_path),
                            line_number=line_no,
                            column=match.start(),
                            code_snippet=line.strip(),
                            severity=pattern_info['severity'],
                            message=pattern_info['message'],
                            fix_suggestion=pattern_info['fix']
                        ))
        
        except Exception as e:
            logger.error(f"パターン検出エラー: {file_path} - {e}")
        
        return detections
    
    def _detect_in_csv(self, file_path: Path) -> List[Detection]:
        """CSVデータの検証"""
        detections = []
        
        try:
            # CSV読み込み
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            
            # calibrated_scoreカラムチェック
            if 'calibrated_score' in df.columns:
                detections.append(Detection(
                    rule_id="RULE_001",
                    violation_type="calibrated_scoreカラム存在",
                    file_path=str(file_path),
                    line_number=None,
                    column=None,
                    code_snippet=None,
                    severity="HIGH",
                    message="CSVにcalibrated_scoreカラムが含まれています",
                    fix_suggestion="calibrated_scoreカラムを削除してください"
                ))
            
            # 削除率チェック
            if 'deletion_action' in df.columns:
                deletion_rate = (df['deletion_action'].str.contains('削除').sum() / len(df))
                if deletion_rate < 0.10 or deletion_rate > 0.20:
                    detections.append(Detection(
                        rule_id="RULE_004",
                        violation_type="削除率異常",
                        file_path=str(file_path),
                        line_number=None,
                        column=None,
                        code_snippet=None,
                        severity="HIGH",
                        message=f"削除率が範囲外です: {deletion_rate:.1%}",
                        fix_suggestion="削除基準を見直してください"
                    ))
            
            # 有名人チェック
            if 'person_name' in df.columns and 'new_recognition_score' in df.columns:
                celebrities = ['HIKAKIN', 'ヒカキン', '大谷翔平', 'Ado']
                for celeb in celebrities:
                    celeb_rows = df[df['person_name'].str.contains(celeb, na=False)]
                    if not celeb_rows.empty:
                        min_score = celeb_rows['new_recognition_score'].min()
                        if min_score < 7.0:
                            detections.append(Detection(
                                rule_id="RULE_005",
                                violation_type="有名人スコア異常",
                                file_path=str(file_path),
                                line_number=None,
                                column=None,
                                code_snippet=None,
                                severity="CRITICAL",
                                message=f"{celeb}のスコアが低すぎます: {min_score}",
                                fix_suggestion="スコアリングアルゴリズムを修正してください"
                            ))
        
        except Exception as e:
            logger.error(f"CSV検証エラー: {file_path} - {e}")
        
        return detections
    
    def detect_in_directory(self, directory: str, extensions: List[str] = ['.py', '.csv']) -> List[Detection]:
        """
        ディレクトリ内の全ファイルを検査
        
        Args:
            directory: 検査対象ディレクトリ
            extensions: 検査対象拡張子
            
        Returns:
            全検出結果
        """
        detections = []
        dir_path = Path(directory)
        
        if not dir_path.exists():
            logger.error(f"ディレクトリが存在しません: {directory}")
            return detections
        
        # ファイル走査
        for ext in extensions:
            for file_path in dir_path.glob(f"**/*{ext}"):
                # 除外パス
                if any(skip in str(file_path) for skip in ['venv', '__pycache__', '.git']):
                    continue
                
                logger.info(f"検査中: {file_path}")
                file_detections = self.detect_in_file(str(file_path))
                detections.extend(file_detections)
        
        return detections
    
    def generate_report(self) -> str:
        """検出レポート生成"""
        if not self.detections:
            return "✅ 違反は検出されませんでした"
        
        report = []
        report.append("="*60)
        report.append("🚨 ルール違反検出レポート")
        report.append("="*60)
        report.append(f"検出数: {len(self.detections)}件\n")
        
        # 重要度別集計
        severity_count = {}
        for detection in self.detections:
            severity_count[detection.severity] = severity_count.get(detection.severity, 0) + 1
        
        report.append("## 重要度別集計")
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            if severity in severity_count:
                report.append(f"- {severity}: {severity_count[severity]}件")
        
        report.append("\n## 詳細")
        
        # CRITICAL から順に表示
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            severity_detections = [d for d in self.detections if d.severity == severity]
            if severity_detections:
                report.append(f"\n### {severity}")
                for detection in severity_detections[:10]:  # 最大10件
                    report.append(f"\n📍 {detection.file_path}")
                    if detection.line_number:
                        report.append(f"   行: {detection.line_number}")
                    report.append(f"   種類: {detection.violation_type}")
                    report.append(f"   説明: {detection.message}")
                    report.append(f"   修正: {detection.fix_suggestion}")
                    if detection.code_snippet:
                        report.append(f"   コード: {detection.code_snippet[:50]}...")
        
        report.append("\n" + "="*60)
        return "\n".join(report)


class ASTViolationVisitor(ast.NodeVisitor):
    """AST解析による違反検出ビジター"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.detections = []
    
    def visit_Attribute(self, node):
        """属性アクセスをチェック"""
        # calibrated_score へのアクセス
        if hasattr(node, 'attr') and node.attr == 'calibrated_score':
            self.detections.append(Detection(
                rule_id="RULE_001",
                violation_type="calibrated_score属性アクセス",
                file_path=self.file_path,
                line_number=node.lineno if hasattr(node, 'lineno') else None,
                column=node.col_offset if hasattr(node, 'col_offset') else None,
                code_snippet=None,
                severity="CRITICAL",
                message="calibrated_score属性へのアクセスが検出されました",
                fix_suggestion="calibrated_scoreを使用しないでください"
            ))
        
        self.generic_visit(node)
    
    def visit_Return(self, node):
        """return文をチェック"""
        # 空リスト返却
        if isinstance(node.value, ast.List) and len(node.value.elts) == 0:
            self.detections.append(Detection(
                rule_id="RULE_003",
                violation_type="空リスト返却",
                file_path=self.file_path,
                line_number=node.lineno if hasattr(node, 'lineno') else None,
                column=node.col_offset if hasattr(node, 'col_offset') else None,
                code_snippet=None,
                severity="HIGH",
                message="空リストを返却するコードが検出されました",
                fix_suggestion="適切なエラーハンドリングを実装してください"
            ))
        
        # 空辞書返却
        if isinstance(node.value, ast.Dict) and len(node.value.keys) == 0:
            self.detections.append(Detection(
                rule_id="RULE_003",
                violation_type="空辞書返却",
                file_path=self.file_path,
                line_number=node.lineno if hasattr(node, 'lineno') else None,
                column=node.col_offset if hasattr(node, 'col_offset') else None,
                code_snippet=None,
                severity="HIGH",
                message="空辞書を返却するコードが検出されました",
                fix_suggestion="適切なエラーハンドリングを実装してください"
            ))
        
        self.generic_visit(node)
    
    def visit_ExceptHandler(self, node):
        """例外ハンドラをチェック"""
        # except: pass パターン
        if node.body and len(node.body) == 1:
            if isinstance(node.body[0], ast.Pass):
                self.detections.append(Detection(
                    rule_id="RULE_008",
                    violation_type="エラー隠蔽",
                    file_path=self.file_path,
                    line_number=node.lineno if hasattr(node, 'lineno') else None,
                    column=node.col_offset if hasattr(node, 'col_offset') else None,
                    code_snippet=None,
                    severity="HIGH",
                    message="except: pass パターンが検出されました",
                    fix_suggestion="適切なエラーハンドリングを実装してください"
                ))
        
        self.generic_visit(node)


def main():
    """メイン実行"""
    detector = RuleViolationDetector()
    
    # テスト実行
    logger.info("\n" + "="*60)
    logger.info("ルール違反検出テスト")
    logger.info("="*60)
    
    # 1. 問題のあるファイルをチェック
    test_files = [
        "apply_recognition_simple.py",
        "削除候補/deletion_SUMMARY_20250906_215814.md"
    ]
    
    for file in test_files:
        if Path(file).exists():
            logger.info(f"\n検査中: {file}")
            detections = detector.detect_in_file(file)
            if detections:
                logger.info(f"✅ {len(detections)}件の違反を検出")
                for detection in detections[:3]:  # 最初の3件
                    logger.info(f"  - {detection.violation_type}: 行{detection.line_number}")
    
    # 2. レポート生成
    report = detector.generate_report()
    print("\n" + report)
    
    logger.info("\n✅ 違反検出テスト完了")


if __name__ == "__main__":
    main()