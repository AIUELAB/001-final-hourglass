#!/usr/bin/env python3
"""
PDCAダッシュボードを更新して新しいルールを反映
"""

import json
from datetime import datetime
from pathlib import Path

def update_dashboard():
    """PDCAダッシュボードHTMLを更新"""
    
    # project_memory.jsonを読み込む
    with open('project_memory.json', 'r', encoding='utf-8') as f:
        memory = json.load(f)
    
    # 統計を計算
    total_rules = len(memory['permanent_rules'])
    critical_rules = sum(1 for r in memory['permanent_rules'] if r['priority'] == 'CRITICAL')
    total_violations = sum(len(r['violations']) for r in memory['permanent_rules'])
    recent_rules = [r for r in memory['permanent_rules'] if r['date'] == '2025-09-07']
    
    # HTMLを生成
    html_content = '''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDCA Dashboard - Ultra Think Project</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }
        
        .dashboard {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        h1 {
            color: white;
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        
        .last-updated {
            color: white;
            text-align: center;
            margin-bottom: 20px;
            opacity: 0.9;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .metric-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        
        .metric-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.15);
        }
        
        .metric-value {
            font-size: 3em;
            font-weight: bold;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 10px 0;
        }
        
        .metric-label {
            color: #666;
            font-size: 1.1em;
            margin-bottom: 10px;
        }
        
        .metric-change {
            font-size: 0.9em;
            padding: 5px 10px;
            border-radius: 20px;
            display: inline-block;
            margin-top: 10px;
        }
        
        .positive {
            background: #d4f4dd;
            color: #28a745;
        }
        
        .negative {
            background: #ffd4d4;
            color: #dc3545;
        }
        
        .neutral {
            background: #f0f0f0;
            color: #666;
        }
        
        .section {
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        .section h2 {
            color: #333;
            margin-bottom: 20px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        
        .rule-list {
            list-style: none;
        }
        
        .rule-item {
            padding: 15px;
            margin-bottom: 10px;
            border-left: 4px solid #667eea;
            background: #f8f9fa;
            border-radius: 5px;
            transition: all 0.3s ease;
        }
        
        .rule-item:hover {
            background: #e9ecef;
            transform: translateX(5px);
        }
        
        .rule-critical {
            border-left-color: #dc3545;
        }
        
        .rule-high {
            border-left-color: #ffc107;
        }
        
        .rule-medium {
            border-left-color: #28a745;
        }
        
        .rule-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .rule-id {
            font-weight: bold;
            color: #667eea;
        }
        
        .rule-priority {
            padding: 3px 10px;
            border-radius: 15px;
            font-size: 0.85em;
            font-weight: bold;
        }
        
        .priority-critical {
            background: #dc3545;
            color: white;
        }
        
        .priority-high {
            background: #ffc107;
            color: #333;
        }
        
        .priority-medium {
            background: #28a745;
            color: white;
        }
        
        .rule-content {
            color: #555;
            line-height: 1.6;
        }
        
        .rule-date {
            color: #999;
            font-size: 0.9em;
            margin-top: 5px;
        }
        
        .violation-count {
            background: #ff6b6b;
            color: white;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.85em;
            margin-left: 10px;
        }
        
        .new-badge {
            background: #4CAF50;
            color: white;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.75em;
            margin-left: 5px;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.6; }
            100% { opacity: 1; }
        }
    </style>
</head>
<body>
    <div class="dashboard">
        <h1>🛡️ PDCA Guardian Dashboard</h1>
        <p class="last-updated">最終更新: ''' + datetime.now().strftime('%Y年%m月%d日 %H:%M:%S') + '''</p>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">総ルール数</div>
                <div class="metric-value">''' + str(total_rules) + '''</div>
                <span class="metric-change positive">+2 今日追加</span>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">CRITICAL ルール</div>
                <div class="metric-value">''' + str(critical_rules) + '''</div>
                <span class="metric-change negative">要注意</span>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">総違反検出数</div>
                <div class="metric-value">''' + str(total_violations) + '''</div>
                <span class="metric-change neutral">監視中</span>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">成功パターン</div>
                <div class="metric-value">''' + str(len(memory['success_patterns'])) + '''</div>
                <span class="metric-change positive">学習済み</span>
            </div>
        </div>
        
        <div class="section">
            <h2>📌 最新追加ルール（2025-09-07）</h2>
            <ul class="rule-list">'''
    
    # 最新ルールを追加
    for rule in recent_rules:
        priority_class = f"priority-{rule['priority'].lower()}"
        rule_class = f"rule-{rule['priority'].lower()}"
        
        html_content += f'''
                <li class="rule-item {rule_class}">
                    <div class="rule-header">
                        <span class="rule-id">{rule['id']}</span>
                        <div>
                            <span class="rule-priority {priority_class}">{rule['priority']}</span>
                            <span class="new-badge">NEW</span>
                            {f'<span class="violation-count">違反 {len(rule["violations"])}</span>' if rule['violations'] else ''}
                        </div>
                    </div>
                    <div class="rule-content">
                        <strong>{rule['rule']}</strong><br>
                        <small>{rule['context']}</small>
                    </div>
                    <div class="rule-date">追加日: {rule['date']} | ソース: {rule['source']}</div>
                </li>'''
    
    html_content += '''
            </ul>
        </div>
        
        <div class="section">
            <h2>🔴 CRITICAL ルール一覧</h2>
            <ul class="rule-list">'''
    
    # CRITICALルールを表示
    for rule in memory['permanent_rules']:
        if rule['priority'] == 'CRITICAL':
            html_content += f'''
                <li class="rule-item rule-critical">
                    <div class="rule-header">
                        <span class="rule-id">{rule['id']}</span>
                        <div>
                            <span class="rule-priority priority-critical">CRITICAL</span>
                            {f'<span class="violation-count">違反 {len(rule["violations"])}</span>' if rule['violations'] else ''}
                        </div>
                    </div>
                    <div class="rule-content">
                        <strong>{rule['rule']}</strong><br>
                        <small>{rule['enforcement']}</small>
                    </div>
                    <div class="rule-date">追加日: {rule['date']}</div>
                </li>'''
    
    html_content += '''
            </ul>
        </div>
        
        <div class="section">
            <h2>📊 重要な変更履歴</h2>
            <ul class="rule-list">
                <li class="rule-item">
                    <div class="rule-header">
                        <span class="rule-id">2025-09-07</span>
                        <span class="rule-priority priority-critical">重要更新</span>
                    </div>
                    <div class="rule-content">
                        <strong>person_name_displayフィールド必須化</strong><br>
                        <small>知名度評価システムの基準フィールドとして、person_name_displayを必須化。
                        person_name_ja、occupation、nationalityも付随して必須フィールドに設定。</small>
                    </div>
                </li>
            </ul>
        </div>
    </div>
</body>
</html>'''
    
    # HTMLファイルを保存
    with open('pdca_dashboard.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("✅ PDCAダッシュボードを更新しました")
    print(f"   総ルール数: {total_rules}")
    print(f"   CRITICALルール: {critical_rules}")
    print(f"   新規追加ルール: {len(recent_rules)}")
    print(f"   ファイル: pdca_dashboard.html")

if __name__ == "__main__":
    update_dashboard()