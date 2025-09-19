#!/usr/bin/env python3
"""
統合PDCAマネジメントシステム - 次世代品質管理プラットフォーム
リアルタイム監視、自動違反検出、予測分析、自動修正提案を統合
"""

import os
import json
import logging
import asyncio
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, deque
import hashlib
import time
import re

# 外部ライブラリ
import pandas as pd
import numpy as np
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# プロジェクト内インポート
from priority_japanese_config import get_japanese_priority, get_priority_display

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SystemStatus(Enum):
    """システムステータス"""
    INITIALIZING = "初期化中"
    MONITORING = "監視中"
    ANALYZING = "分析中"
    CORRECTING = "修正中"
    ALERT = "警告"
    ERROR = "エラー"


class ViolationSeverity(Enum):
    """違反深刻度"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class ViolationEvent:
    """違反イベント"""
    id: str
    timestamp: datetime
    rule_id: str
    severity: ViolationSeverity
    file_path: Optional[str]
    line_number: Optional[int]
    description: str
    suggested_fix: Optional[str]
    auto_fixable: bool = False
    fixed: bool = False


@dataclass
class ComplianceMetrics:
    """コンプライアンスメトリクス"""
    timestamp: datetime
    compliance_rate: float
    total_rules: int
    violations_count: int
    critical_violations: int
    auto_fixed_count: int
    trend: str  # "improving", "stable", "declining"
    prediction_next_24h: float


class PDCAManagementSystem:
    """
    統合PDCAマネジメントシステム
    
    リアルタイム監視、違反検出、自動修正、予測分析を提供
    """
    
    def __init__(self, config_path: str = "pdca_config.json"):
        """初期化"""
        self.config_path = Path(config_path)
        self.project_memory_path = Path("project_memory.json")
        self.status = SystemStatus.INITIALIZING
        
        # データストア
        self.project_memory = self._load_project_memory()
        self.violations_history = deque(maxlen=1000)
        self.metrics_history = deque(maxlen=100)
        self.real_time_alerts = []
        
        # 監視対象
        self.monitored_files = set()
        self.monitored_patterns = []
        
        # スレッド管理
        self.monitoring_thread = None
        self.analysis_thread = None
        self.observer = None
        
        # メトリクス
        self.current_metrics = None
        self.initialize_metrics()
        
        logger.info("="*60)
        logger.info("🚀 統合PDCAマネジメントシステム起動")
        logger.info("="*60)
        
    def _load_project_memory(self) -> Dict:
        """プロジェクトメモリ読み込み"""
        if self.project_memory_path.exists():
            with open(self.project_memory_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "permanent_rules": [],
            "failed_patterns": [],
            "success_patterns": [],
            "quality_metrics": {}
        }
    
    def initialize_metrics(self):
        """メトリクス初期化"""
        self.current_metrics = ComplianceMetrics(
            timestamp=datetime.now(),
            compliance_rate=self._calculate_compliance_rate(),
            total_rules=len(self.project_memory.get("permanent_rules", [])),
            violations_count=0,
            critical_violations=0,
            auto_fixed_count=0,
            trend="stable",
            prediction_next_24h=0.0
        )
    
    def _calculate_compliance_rate(self) -> float:
        """コンプライアンス率計算"""
        rules = self.project_memory.get("permanent_rules", [])
        if not rules:
            return 100.0
        
        total_violations = sum(len(rule.get("violations", [])) for rule in rules)
        critical_violations = sum(
            len(rule.get("violations", [])) 
            for rule in rules 
            if rule.get("priority") == "CRITICAL"
        )
        
        # クリティカル違反は重み付けを高くする
        weighted_violations = total_violations + (critical_violations * 2)
        max_score = len(rules) * 10  # 各ルール最大10点
        
        if max_score == 0:
            return 100.0
        
        compliance_rate = max(0, (max_score - weighted_violations * 5) / max_score * 100)
        return round(compliance_rate, 2)
    
    # ===============================
    # リアルタイム監視エンジン
    # ===============================
    
    class FileChangeHandler(FileSystemEventHandler):
        """ファイル変更ハンドラー"""
        
        def __init__(self, system):
            self.system = system
            
        def on_modified(self, event):
            if not event.is_directory:
                self.system.handle_file_change(event.src_path)
        
        def on_created(self, event):
            if not event.is_directory:
                self.system.handle_file_change(event.src_path)
    
    def start_monitoring(self, paths: List[str] = None):
        """リアルタイム監視開始"""
        if paths is None:
            paths = ["."]
        
        self.status = SystemStatus.MONITORING
        logger.info("🔍 リアルタイム監視を開始します")
        
        # ファイル監視設定
        self.observer = Observer()
        handler = self.FileChangeHandler(self)
        
        for path in paths:
            self.observer.schedule(handler, path, recursive=True)
        
        self.observer.start()
        logger.info(f"📁 監視対象: {paths}")
    
    def handle_file_change(self, file_path: str):
        """ファイル変更処理"""
        file_path = Path(file_path)
        
        # 除外パターン
        exclude_patterns = [
            r'\.git/', r'__pycache__/', r'\.pyc$', 
            r'backup_', r'\.log$', r'\.json$'
        ]
        
        for pattern in exclude_patterns:
            if re.search(pattern, str(file_path)):
                return
        
        # Pythonファイルの場合は違反チェック
        if file_path.suffix == '.py':
            logger.info(f"📝 ファイル変更検出: {file_path}")
            violations = self.check_file_violations(file_path)
            
            if violations:
                self.handle_violations(violations)
    
    def check_file_violations(self, file_path: Path) -> List[ViolationEvent]:
        """ファイル違反チェック"""
        violations = []
        
        if not file_path.exists():
            return violations
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # ルールベースチェック
            for rule in self.project_memory.get("permanent_rules", []):
                violation = self._check_rule_violation(rule, content, lines, file_path)
                if violation:
                    violations.append(violation)
            
        except Exception as e:
            logger.error(f"ファイルチェックエラー: {file_path} - {e}")
        
        return violations
    
    def _check_rule_violation(self, rule: Dict, content: str, lines: List[str], 
                            file_path: Path) -> Optional[ViolationEvent]:
        """個別ルール違反チェック"""
        
        # RULE_001: calibrated_score使用禁止
        if rule.get("id") == "RULE_001":
            if "calibrated_score" in content:
                for i, line in enumerate(lines, 1):
                    if "calibrated_score" in line:
                        return ViolationEvent(
                            id=f"V{int(time.time()*1000)}",
                            timestamp=datetime.now(),
                            rule_id="RULE_001",
                            severity=ViolationSeverity.CRITICAL,
                            file_path=str(file_path),
                            line_number=i,
                            description="calibrated_scoreの使用が検出されました",
                            suggested_fix="calibrated_scoreを削除し、適切な評価方法を使用してください",
                            auto_fixable=True
                        )
        
        # RULE_012: person_name_display必須
        elif rule.get("id") == "RULE_012":
            if "person_name" in content and "person_name_display" not in content:
                return ViolationEvent(
                    id=f"V{int(time.time()*1000)}",
                    timestamp=datetime.now(),
                    rule_id="RULE_012",
                    severity=ViolationSeverity.CRITICAL,
                    file_path=str(file_path),
                    line_number=None,
                    description="person_name_displayフィールドが欠落しています",
                    suggested_fix="person_name_displayフィールドを追加してください",
                    auto_fixable=False
                )
        
        # RULE_014: 単一実装原則
        elif rule.get("id") == "RULE_014":
            file_name = file_path.stem
            if "dashboard" in file_name.lower():
                # 同じ機能の複数実装をチェック
                similar_files = list(file_path.parent.glob("*dashboard*.py"))
                if len(similar_files) > 1:
                    return ViolationEvent(
                        id=f"V{int(time.time()*1000)}",
                        timestamp=datetime.now(),
                        rule_id="RULE_014",
                        severity=ViolationSeverity.HIGH,
                        file_path=str(file_path),
                        line_number=None,
                        description=f"重複実装の可能性: {[f.name for f in similar_files]}",
                        suggested_fix="機能を統合し、単一の実装にしてください",
                        auto_fixable=False
                    )
        
        return None
    
    def handle_violations(self, violations: List[ViolationEvent]):
        """違反処理"""
        for violation in violations:
            # 履歴に追加
            self.violations_history.append(violation)
            
            # リアルタイムアラート
            if violation.severity in [ViolationSeverity.CRITICAL, ViolationSeverity.HIGH]:
                self.send_alert(violation)
            
            # 自動修正可能な場合
            if violation.auto_fixable:
                self.attempt_auto_fix(violation)
            
            # メトリクス更新
            self.update_metrics(violation)
    
    def send_alert(self, violation: ViolationEvent):
        """アラート送信"""
        alert_msg = f"""
        🚨 違反検出アラート
        ━━━━━━━━━━━━━━━━━━━━
        ルール: {violation.rule_id}
        深刻度: {violation.severity.value}
        ファイル: {violation.file_path}
        説明: {violation.description}
        ━━━━━━━━━━━━━━━━━━━━
        """
        logger.error(alert_msg)
        self.real_time_alerts.append({
            "timestamp": violation.timestamp.isoformat(),
            "violation": asdict(violation)
        })
    
    def attempt_auto_fix(self, violation: ViolationEvent):
        """自動修正試行"""
        if not violation.auto_fixable or not violation.file_path:
            return
        
        logger.info(f"🔧 自動修正を試行: {violation.rule_id}")
        
        try:
            file_path = Path(violation.file_path)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # RULE_001の自動修正: calibrated_scoreを削除
            if violation.rule_id == "RULE_001":
                # calibrated_scoreを含む行をコメントアウト
                lines = content.split('\n')
                fixed_lines = []
                
                for line in lines:
                    if 'calibrated_score' in line and not line.strip().startswith('#'):
                        fixed_lines.append(f"# PDCA_AUTO_FIX: {line}  # calibrated_score使用禁止")
                    else:
                        fixed_lines.append(line)
                
                # バックアップ作成
                backup_path = file_path.with_suffix(f'.backup_{int(time.time())}')
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # 修正内容を書き込み
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(fixed_lines))
                
                violation.fixed = True
                self.current_metrics.auto_fixed_count += 1
                logger.info(f"✅ 自動修正完了: {violation.file_path}")
                
        except Exception as e:
            logger.error(f"自動修正失敗: {e}")
    
    def monitor_thought_patterns(self, thought_text: str = None, file_path: str = None) -> Dict[str, Any]:
        """思考パターン監視機能（RULE_016, RULE_017実装）
        
        AIの提案や思考プロセスをリアルタイムで監視し、
        品質妥協パターンを検出する。
        
        Args:
            thought_text: 監視対象のテキスト（提案、説明、コメント等）
            file_path: 監視対象のファイルパス
        
        Returns:
            検出結果と改善提案
        """
        violations = []
        patterns = {
            "quality_compromise": [
                r"ハイブリッド(方式|アプローチ|版)",
                r"部分的(に|な)?(処理|実装|実行)",
                r"(一部|上位\d+[件名]?)のみ",
                r"(簡易|簡単|シンプル|高速|クイック)版",
                r"\d+分(で|に)完了",
                r"時間(を)?短縮",
                r"効率(を)?優先"
            ],
            "unrealistic_time": [
                r"(\d+)時間.*(\d+)分",  # 時間から分への大幅短縮
                r"5倍以上.*高速化",
                r"処理時間.*90%.*削減"
            ],
            "missing_quality_checks": [
                r"^(?!.*品質).*$",  # 品質への言及なし
                r"^(?!.*検証).*$",  # 検証への言及なし
                r"^(?!.*テスト).*$"  # テストへの言及なし
            ]
        }
        
        # テキスト監視
        if thought_text:
            for pattern_type, patterns_list in patterns.items():
                for pattern in patterns_list:
                    if re.search(pattern, thought_text, re.IGNORECASE | re.MULTILINE):
                        violations.append({
                            "type": pattern_type,
                            "pattern": pattern,
                            "text": thought_text[:100] + "...",
                            "severity": "HIGH" if pattern_type == "quality_compromise" else "MEDIUM"
                        })
        
        # ファイル監視
        if file_path and Path(file_path).exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # コメント内の思考パターン検出
                comment_patterns = [
                    r'#\s*TODO:.*(?:later|簡易|暫定)',
                    r'#\s*FIXME:.*(?:時間がない|後で)',
                    r'""".*(?:簡易版|暫定実装).*"""'
                ]
                
                for pattern in comment_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
                    for match in matches:
                        violations.append({
                            "type": "quality_compromise_comment",
                            "file": file_path,
                            "comment": match[:100],
                            "severity": "MEDIUM"
                        })
            
            except Exception as e:
                logger.error(f"思考パターン監視エラー: {e}")
        
        # 分析結果
        result = {
            "monitored_at": datetime.now().isoformat(),
            "violations_found": len(violations),
            "violations": violations,
            "quality_score": 100 - (len(violations) * 10),  # 違反ごとに10点減点
            "recommendations": []
        }
        
        # 改善提案生成
        if violations:
            result["recommendations"] = [
                "✅ 品質優先の実装方針を維持してください",
                "✅ 処理時間の見積もりは現実的に（5-8時間）",
                "✅ すべての提案に品質保証プロセスを含める",
                "✅ API活用とデータ検証を必須とする"
            ]
            
            # 違反をログに記録
            logger.warning(f"🧠 思考パターン違反検出: {len(violations)}件")
            for v in violations:
                logger.warning(f"  - {v['type']}: {v.get('pattern', v.get('comment', ''))[:50]}")
        
        return result
    
    def update_metrics(self, violation: ViolationEvent):
        """メトリクス更新"""
        self.current_metrics.violations_count += 1
        
        if violation.severity == ViolationSeverity.CRITICAL:
            self.current_metrics.critical_violations += 1
        
        # コンプライアンス率再計算
        self.current_metrics.compliance_rate = self._calculate_compliance_rate()
        
        # トレンド分析
        if len(self.metrics_history) >= 3:
            recent_rates = [m.compliance_rate for m in list(self.metrics_history)[-3:]]
            if all(recent_rates[i] < recent_rates[i+1] for i in range(len(recent_rates)-1)):
                self.current_metrics.trend = "declining"
            elif all(recent_rates[i] > recent_rates[i+1] for i in range(len(recent_rates)-1)):
                self.current_metrics.trend = "improving"
            else:
                self.current_metrics.trend = "stable"
    
    # ===============================
    # 予測分析エンジン
    # ===============================
    
    def predict_future_violations(self) -> Dict:
        """将来の違反予測"""
        if len(self.violations_history) < 10:
            return {"prediction": "insufficient_data"}
        
        # 時系列分析
        recent_violations = list(self.violations_history)[-50:]
        hourly_counts = defaultdict(int)
        
        for v in recent_violations:
            hour = v.timestamp.hour
            hourly_counts[hour] += 1
        
        # 次の24時間の予測
        current_hour = datetime.now().hour
        predicted_violations = 0
        
        for i in range(24):
            hour = (current_hour + i) % 24
            predicted_violations += hourly_counts.get(hour, 0) * 0.8  # 減衰係数
        
        self.current_metrics.prediction_next_24h = round(predicted_violations, 1)
        
        return {
            "next_24h_violations": predicted_violations,
            "high_risk_hours": sorted(hourly_counts.items(), key=lambda x: x[1], reverse=True)[:3],
            "trend": self.current_metrics.trend
        }
    
    # ===============================
    # レポート生成エンジン
    # ===============================
    
    def generate_realtime_dashboard(self) -> str:
        """リアルタイムダッシュボード生成"""
        
        # 最新のメトリクス取得
        recent_violations = list(self.violations_history)[-10:]
        predictions = self.predict_future_violations()
        
        html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDCA リアルタイムダッシュボード</title>
    <meta http-equiv="refresh" content="5">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: #333;
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1600px;
            margin: 0 auto;
        }}
        
        .header {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.2);
        }}
        
        .title {{
            font-size: 2.5em;
            color: #1e3c72;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        
        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            border-radius: 30px;
            font-size: 0.9em;
            font-weight: 600;
        }}
        
        .status-monitoring {{
            background: linear-gradient(135deg, #00b09b, #96c93d);
            color: white;
        }}
        
        .status-alert {{
            background: linear-gradient(135deg, #f2994a, #f2c94c);
            color: white;
            animation: pulse 2s infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.7; }}
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .metric-card {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            position: relative;
            overflow: hidden;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}
        
        .metric-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.15);
        }}
        
        .metric-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        }}
        
        .metric-label {{
            color: #666;
            font-size: 0.9em;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .metric-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #1e3c72;
            margin-bottom: 10px;
        }}
        
        .metric-trend {{
            font-size: 0.9em;
            padding: 5px 12px;
            border-radius: 20px;
            display: inline-block;
        }}
        
        .trend-up {{
            background: #d4f4dd;
            color: #28a745;
        }}
        
        .trend-down {{
            background: #ffd4d4;
            color: #dc3545;
        }}
        
        .trend-stable {{
            background: #e6f3ff;
            color: #007bff;
        }}
        
        .chart-container {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        
        .violations-list {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        
        .violation-item {{
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 10px;
            border-left: 4px solid;
            background: #f8f9fa;
            transition: transform 0.2s ease;
        }}
        
        .violation-item:hover {{
            transform: translateX(5px);
        }}
        
        .violation-critical {{
            border-left-color: #dc3545;
            background: #fff5f5;
        }}
        
        .violation-high {{
            border-left-color: #ffc107;
            background: #fffdf5;
        }}
        
        .violation-medium {{
            border-left-color: #17a2b8;
            background: #f0faff;
        }}
        
        .compliance-bar {{
            width: 100%;
            height: 40px;
            background: #f0f0f0;
            border-radius: 20px;
            overflow: hidden;
            position: relative;
            margin-top: 20px;
        }}
        
        .compliance-fill {{
            height: 100%;
            background: linear-gradient(90deg, #00b09b 0%, #96c93d 100%);
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            transition: width 1s ease;
        }}
        
        .real-time-indicator {{
            display: inline-block;
            width: 10px;
            height: 10px;
            background: #00ff00;
            border-radius: 50%;
            animation: blink 1s infinite;
            margin-left: 10px;
        }}
        
        @keyframes blink {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.3; }}
        }}
        
        .prediction-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-top: 20px;
        }}
        
        .auto-fix-badge {{
            background: #28a745;
            color: white;
            padding: 3px 8px;
            border-radius: 5px;
            font-size: 0.8em;
            margin-left: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="title">
                🚀 PDCA リアルタイムダッシュボード
                <span class="real-time-indicator"></span>
            </h1>
            <div class="status-badge status-{self.status.value.lower()}">
                <span>ステータス: {self.status.value}</span>
            </div>
            <p style="margin-top: 10px; color: #666;">
                最終更新: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
            </p>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">コンプライアンス率</div>
                <div class="metric-value">{self.current_metrics.compliance_rate}%</div>
                <div class="compliance-bar">
                    <div class="compliance-fill" style="width: {self.current_metrics.compliance_rate}%">
                        {self.current_metrics.compliance_rate}%
                    </div>
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">総違反数</div>
                <div class="metric-value">{self.current_metrics.violations_count}</div>
                <div class="metric-trend trend-{'up' if self.current_metrics.trend == 'declining' else 'down'}">
                    Critical: {self.current_metrics.critical_violations}
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">自動修正</div>
                <div class="metric-value">{self.current_metrics.auto_fixed_count}</div>
                <div class="metric-trend trend-up">
                    成功率: {round(self.current_metrics.auto_fixed_count / max(1, self.current_metrics.violations_count) * 100, 1)}%
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">24時間予測</div>
                <div class="metric-value">{self.current_metrics.prediction_next_24h}</div>
                <div class="metric-trend trend-stable">
                    トレンド: {self.current_metrics.trend}
                </div>
            </div>
        </div>
        
        <div class="chart-container">
            <h2>📊 違反トレンド分析</h2>
            <div class="prediction-box">
                <strong>🔮 予測分析:</strong><br>
                次の24時間で約 {predictions.get('next_24h_violations', 0):.0f} 件の違反が予想されます。<br>
                高リスク時間帯: {', '.join([f"{h[0]}時" for h in predictions.get('high_risk_hours', [])])}
            </div>
        </div>
        
        <div class="violations-list">
            <h2>🚨 最近の違反 (リアルタイム更新)</h2>
            {''.join([self._format_violation_html(v) for v in recent_violations])}
        </div>
    </div>
    
    <script>
        // 5秒ごとに自動更新
        setTimeout(() => {{
            location.reload();
        }}, 5000);
    </script>
</body>
</html>
        """
        
        return html_content
    
    def _format_violation_html(self, violation: ViolationEvent) -> str:
        """違反HTML形式化"""
        severity_class = {
            ViolationSeverity.CRITICAL: "violation-critical",
            ViolationSeverity.HIGH: "violation-high",
            ViolationSeverity.MEDIUM: "violation-medium"
        }.get(violation.severity, "violation-medium")
        
        auto_fix_badge = '<span class="auto-fix-badge">自動修正済み</span>' if violation.fixed else ''
        
        return f"""
        <div class="violation-item {severity_class}">
            <strong>ルール {violation.rule_id}</strong> - {violation.severity.value}
            {auto_fix_badge}
            <br>
            <small>{violation.timestamp.strftime('%H:%M:%S')}</small> - {violation.description}
            {f'<br>ファイル: {violation.file_path}' if violation.file_path else ''}
        </div>
        """
    
    def save_dashboard(self, output_path: str = "pdca_realtime_dashboard.html"):
        """ダッシュボード保存"""
        html_content = self.generate_realtime_dashboard()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"📊 リアルタイムダッシュボード生成: {output_path}")
        return output_path
    
    def get_status_report(self) -> Dict:
        """ステータスレポート取得"""
        return {
            "status": self.status.value,
            "metrics": asdict(self.current_metrics) if self.current_metrics else {},
            "recent_violations": [asdict(v) for v in list(self.violations_history)[-10:]],
            "alerts": self.real_time_alerts[-5:],
            "predictions": self.predict_future_violations()
        }
    
    def stop_monitoring(self):
        """監視停止"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
        
        logger.info("🛑 監視を停止しました")


def main():
    """メイン処理"""
    system = PDCAManagementSystem()
    
    # リアルタイム監視開始
    system.start_monitoring(["."])
    
    # 初回ダッシュボード生成
    dashboard_path = system.save_dashboard()
    
    # ステータスレポート
    status = system.get_status_report()
    
    print("\n" + "="*60)
    print("🚀 統合PDCAマネジメントシステム - 起動完了")
    print("="*60)
    print(f"📊 コンプライアンス率: {status['metrics'].get('compliance_rate', 0)}%")
    print(f"🔍 監視ステータス: {status['status']}")
    print(f"📈 トレンド: {status['metrics'].get('trend', 'stable')}")
    print(f"🔮 24時間予測: {status['predictions'].get('next_24h_violations', 0):.0f} 件")
    print("="*60)
    print(f"🌐 ダッシュボード: {dashboard_path}")
    print("📡 リアルタイム監視中... (Ctrl+C で停止)")
    print("="*60)
    
    try:
        # ブラウザで開く
        import webbrowser
        webbrowser.open(f"file://{Path(dashboard_path).absolute()}")
        
        # 監視継続
        while True:
            time.sleep(5)
            # 定期的にダッシュボード更新
            system.save_dashboard()
            
    except KeyboardInterrupt:
        print("\n⏹️  監視を停止します...")
        system.stop_monitoring()


if __name__ == "__main__":
    main()