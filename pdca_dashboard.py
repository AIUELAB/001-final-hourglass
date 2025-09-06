#!/usr/bin/env python3
"""
PDCA ダッシュボードシステム - 改善サイクルの可視化と追跡
すべてのPDCAサイクル、違反、改善履歴を一元管理
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd
from collections import defaultdict
from priority_japanese_config import get_japanese_priority, get_priority_display, get_priority_html

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PDCADashboard:
    """PDCAダッシュボードクラス"""
    
    def __init__(self):
        self.project_memory_path = Path("project_memory.json")
        self.quality_reports_dir = Path("quality_reports")
        self.quality_reports_dir.mkdir(exist_ok=True)
        
        # データソース
        self.project_memory = self._load_project_memory()
        self.violation_history = []
        self.improvement_history = []
        self.cycle_metrics = defaultdict(list)
    
    def _load_project_memory(self) -> Dict:
        """プロジェクトメモリを読み込み"""
        if self.project_memory_path.exists():
            with open(self.project_memory_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def analyze_violations(self) -> Dict:
        """違反分析"""
        violations_summary = {
            "total_violations": 0,
            "by_severity": defaultdict(int),
            "by_rule": defaultdict(int),
            "by_file": defaultdict(int),
            "recent_violations": [],
            "recurring_patterns": []
        }
        
        # プロジェクトメモリから違反履歴を抽出
        if "permanent_rules" in self.project_memory:
            for rule in self.project_memory["permanent_rules"]:
                if "violations" in rule and rule["violations"]:
                    for violation in rule["violations"]:
                        violations_summary["total_violations"] += 1
                        violations_summary["by_severity"][rule["priority"]] += 1
                        violations_summary["by_rule"][rule["id"]] += 1
                        
                        # 最近の違反
                        if "date" in violation:
                            violations_summary["recent_violations"].append({
                                "rule_id": rule["id"],
                                "date": violation["date"],
                                "type": violation.get("type", "Unknown"),
                                "description": violation.get("description", "")
                            })
        
        # 再発パターンの検出
        if violations_summary["by_rule"]:
            for rule_id, count in violations_summary["by_rule"].items():
                if count >= 2:
                    violations_summary["recurring_patterns"].append({
                        "rule_id": rule_id,
                        "count": count,
                        "severity": "HIGH"
                    })
        
        return violations_summary
    
    def analyze_improvements(self) -> Dict:
        """改善分析"""
        improvements = {
            "success_patterns": [],
            "failed_patterns": [],
            "improvement_rate": 0,
            "cycles_completed": 0,
            "average_cycle_time": 0
        }
        
        # 成功パターン
        if "success_patterns" in self.project_memory:
            improvements["success_patterns"] = self.project_memory["success_patterns"]
        
        # 失敗パターン
        if "failed_patterns" in self.project_memory:
            improvements["failed_patterns"] = self.project_memory["failed_patterns"]
        
        # 改善率計算
        total_patterns = len(improvements["success_patterns"]) + len(improvements["failed_patterns"])
        if total_patterns > 0:
            improvements["improvement_rate"] = (
                len(improvements["success_patterns"]) / total_patterns * 100
            )
        
        return improvements
    
    def generate_metrics(self) -> Dict:
        """メトリクス生成"""
        metrics = {
            "quality_scores": {},
            "api_usage": {},
            "protection_coverage": {},
            "compliance_rate": 0
        }
        
        # 品質メトリクス
        if "quality_metrics" in self.project_memory:
            metrics["quality_scores"] = self.project_memory["quality_metrics"]
        
        # コンプライアンス率
        violations = self.analyze_violations()
        if violations["total_violations"] > 0:
            critical_violations = violations["by_severity"].get("CRITICAL", 0)
            metrics["compliance_rate"] = max(0, 100 - (critical_violations * 10))
        else:
            metrics["compliance_rate"] = 100
        
        return metrics
    
    def generate_html_dashboard(self) -> str:
        """HTMLダッシュボード生成"""
        violations = self.analyze_violations()
        improvements = self.analyze_improvements()
        metrics = self.generate_metrics()
        
        html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDCA Dashboard - Ultra Think Project</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        
        .dashboard {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        h1 {{
            color: white;
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .metric-card {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }}
        
        .metric-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.15);
        }}
        
        .metric-value {{
            font-size: 3em;
            font-weight: bold;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 10px 0;
        }}
        
        .metric-label {{
            color: #666;
            font-size: 1.1em;
            margin-bottom: 10px;
        }}
        
        .metric-change {{
            font-size: 0.9em;
            padding: 5px 10px;
            border-radius: 20px;
            display: inline-block;
            margin-top: 10px;
        }}
        
        .positive {{
            background: #d4f4dd;
            color: #28a745;
        }}
        
        .negative {{
            background: #ffd4d4;
            color: #dc3545;
        }}
        
        .neutral {{
            background: #f0f0f0;
            color: #666;
        }}
        
        .section {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        
        .section-title {{
            font-size: 1.8em;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}
        
        .violations-list {{
            list-style: none;
            padding: 0;
        }}
        
        .violation-item {{
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #dc3545;
            background: #fff5f5;
            border-radius: 5px;
        }}
        
        .violation-critical {{
            border-left-color: #dc3545;
            background: #ffe0e0;
        }}
        
        .violation-high {{
            border-left-color: #ffc107;
            background: #fff9e6;
        }}
        
        .violation-medium {{
            border-left-color: #17a2b8;
            background: #e6f7ff;
        }}
        
        .success-pattern {{
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #28a745;
            background: #f0fff4;
            border-radius: 5px;
        }}
        
        .failed-pattern {{
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #dc3545;
            background: #fff5f5;
            border-radius: 5px;
        }}
        
        .progress-bar {{
            width: 100%;
            height: 30px;
            background: #f0f0f0;
            border-radius: 15px;
            overflow: hidden;
            margin: 20px 0;
        }}
        
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            border-radius: 15px;
            transition: width 0.5s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }}
        
        .timestamp {{
            text-align: center;
            color: white;
            margin-top: 30px;
            font-size: 0.9em;
        }}
        
        .chart-container {{
            height: 300px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="dashboard">
        <h1>🎯 PDCA Dashboard - Ultra Think Project</h1>
        
        <!-- メトリクスカード -->
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">コンプライアンス率</div>
                <div class="metric-value">{metrics['compliance_rate']}%</div>
                <div class="metric-change {'positive' if metrics['compliance_rate'] >= 90 else 'negative'}">
                    {'✅ 良好' if metrics['compliance_rate'] >= 90 else '⚠️ 改善必要'}
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">総違反数</div>
                <div class="metric-value">{violations['total_violations']}</div>
                <div class="metric-change negative">
                    {get_priority_display('CRITICAL')}: {violations['by_severity'].get('CRITICAL', 0)}
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">改善率</div>
                <div class="metric-value">{improvements['improvement_rate']:.1f}%</div>
                <div class="metric-change {'positive' if improvements['improvement_rate'] >= 50 else 'negative'}">
                    成功: {len(improvements['success_patterns'])}
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">保護ルール数</div>
                <div class="metric-value">{len(self.project_memory.get('permanent_rules', []))}</div>
                <div class="metric-change neutral">
                    アクティブ
                </div>
            </div>
        </div>
        
        <!-- 違反セクション -->
        <div class="section">
            <h2 class="section-title">🚨 違反状況</h2>
            
            <div class="progress-bar">
                <div class="progress-fill" style="width: {100 - violations['total_violations'] * 5}%">
                    健全性: {100 - violations['total_violations'] * 5}%
                </div>
            </div>
            
            <h3>最近の違反</h3>
            <ul class="violations-list">
                {self._generate_violation_items(violations['recent_violations'][:5])}
            </ul>
            
            <h3>再発パターン</h3>
            <ul class="violations-list">
                {self._generate_recurring_patterns(violations['recurring_patterns'])}
            </ul>
        </div>
        
        <!-- 改善パターンセクション -->
        <div class="section">
            <h2 class="section-title">📈 改善パターン</h2>
            
            <h3>✅ 成功パターン</h3>
            {self._generate_success_patterns(improvements['success_patterns'])}
            
            <h3>❌ 失敗パターン</h3>
            {self._generate_failed_patterns(improvements['failed_patterns'])}
        </div>
        
        <!-- ルール一覧セクション -->
        <div class="section">
            <h2 class="section-title">📋 アクティブルール</h2>
            {self._generate_rules_table()}
        </div>
        
        <div class="timestamp">
            最終更新: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
        </div>
    </div>
</body>
</html>
        """
        
        return html_content
    
    def _generate_violation_items(self, violations: List) -> str:
        """違反アイテムHTML生成"""
        if not violations:
            return "<li>違反なし ✅</li>"
        
        html = ""
        for v in violations:
            severity_class = "violation-critical"
            html += f"""
                <li class="violation-item {severity_class}">
                    <strong>{v.get('type', 'Unknown')}</strong><br>
                    {v.get('description', '')}
                    <br><small>{v.get('date', '')}</small>
                </li>
            """
        return html
    
    def _generate_recurring_patterns(self, patterns: List) -> str:
        """再発パターンHTML生成"""
        if not patterns:
            return "<li>再発パターンなし ✅</li>"
        
        html = ""
        for p in patterns:
            html += f"""
                <li class="violation-item violation-high">
                    <strong>ルール {p['rule_id']}</strong>: {p['count']}回発生
                </li>
            """
        return html
    
    def _generate_success_patterns(self, patterns: List) -> str:
        """成功パターンHTML生成"""
        if not patterns:
            return "<p>成功パターンがまだありません</p>"
        
        html = ""
        for p in patterns:
            html += f"""
                <div class="success-pattern">
                    <strong>{p.get('pattern', '')}</strong><br>
                    {p.get('description', '')}<br>
                    結果: {p.get('result', '')}
                </div>
            """
        return html
    
    def _generate_failed_patterns(self, patterns: List) -> str:
        """失敗パターンHTML生成"""
        if not patterns:
            return "<p>失敗パターンがまだありません</p>"
        
        html = ""
        for p in patterns:
            html += f"""
                <div class="failed-pattern">
                    <strong>{p.get('pattern', '')}</strong><br>
                    {p.get('description', '')}<br>
                    影響: {p.get('consequence', '')}
                </div>
            """
        return html
    
    def _generate_rules_table(self) -> str:
        """ルールテーブルHTML生成"""
        rules = self.project_memory.get("permanent_rules", [])
        
        if not rules:
            return "<p>ルールが定義されていません</p>"
        
        html = """
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr style="background: #f0f0f0;">
                    <th style="padding: 10px; text-align: left;">ID</th>
                    <th style="padding: 10px; text-align: left;">ルール</th>
                    <th style="padding: 10px; text-align: left;">優先度</th>
                    <th style="padding: 10px; text-align: left;">違反数</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for rule in rules:
            violation_count = len(rule.get("violations", []))
            priority = rule.get("priority", "")
            priority_color = {
                "CRITICAL": "#dc3545",
                "HIGH": "#ffc107",
                "MEDIUM": "#17a2b8"
            }.get(priority, "#666")
            
            html += f"""
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #ddd;">
                        {rule.get('id', '')}
                    </td>
                    <td style="padding: 10px; border-bottom: 1px solid #ddd;">
                        {rule.get('rule', '')}
                    </td>
                    <td style="padding: 10px; border-bottom: 1px solid #ddd;">
                        <span style="color: {priority_color}; font-weight: bold;">
                            {get_priority_display(priority)}
                        </span>
                    </td>
                    <td style="padding: 10px; border-bottom: 1px solid #ddd;">
                        {violation_count}
                    </td>
                </tr>
            """
        
        html += """
            </tbody>
        </table>
        """
        
        return html
    
    def save_dashboard(self, output_path: str = "pdca_dashboard.html"):
        """ダッシュボードを保存"""
        html_content = self.generate_html_dashboard()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"📊 ダッシュボード生成: {output_path}")
        return output_path
    
    def generate_json_report(self) -> Dict:
        """JSON形式のレポート生成"""
        violations = self.analyze_violations()
        improvements = self.analyze_improvements()
        metrics = self.generate_metrics()
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "violations": violations,
            "improvements": improvements,
            "metrics": metrics,
            "rules": self.project_memory.get("permanent_rules", []),
            "validation_checkpoints": self.project_memory.get("validation_checkpoints", [])
        }
        
        # レポート保存
        report_path = self.quality_reports_dir / f"pdca_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📄 JSONレポート生成: {report_path}")
        return report


def main():
    """メイン処理"""
    dashboard = PDCADashboard()
    
    # HTMLダッシュボード生成
    html_path = dashboard.save_dashboard()
    
    # JSONレポート生成
    json_report = dashboard.generate_json_report()
    
    # サマリー出力
    violations = dashboard.analyze_violations()
    improvements = dashboard.analyze_improvements()
    metrics = dashboard.generate_metrics()
    
    print("\n" + "=" * 60)
    print("📊 PDCA ダッシュボードサマリー")
    print("=" * 60)
    print(f"📈 コンプライアンス率: {metrics['compliance_rate']}%")
    print(f"🚨 総違反数: {violations['total_violations']}")
    print(f"   - {get_priority_display('CRITICAL')}: {violations['by_severity'].get('CRITICAL', 0)}")
    print(f"   - {get_priority_display('HIGH')}: {violations['by_severity'].get('HIGH', 0)}")
    print(f"   - {get_priority_display('MEDIUM')}: {violations['by_severity'].get('MEDIUM', 0)}")
    print(f"✅ 成功パターン: {len(improvements['success_patterns'])}")
    print(f"❌ 失敗パターン: {len(improvements['failed_patterns'])}")
    print(f"📊 改善率: {improvements['improvement_rate']:.1f}%")
    print("=" * 60)
    print(f"🌐 HTMLダッシュボード: {html_path}")
    print(f"📄 JSONレポート: quality_reports/")
    print("=" * 60)
    
    # ブラウザで開く（オプション）
    import webbrowser
    try:
        webbrowser.open(f"file://{Path(html_path).absolute()}")
        print("🌐 ブラウザでダッシュボードを開きました")
    except:
        print(f"📂 ダッシュボードは {html_path} に保存されています")


if __name__ == "__main__":
    main()