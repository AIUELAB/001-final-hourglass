#!/usr/bin/env python3
"""
PDCA Guardian System Update - Phase 1
5つの新しいCRITICALルールを追加して過去の失敗を防止
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any


def load_project_memory() -> Dict[str, Any]:
    """プロジェクトメモリをロード"""
    memory_path = "project_memory.json"
    if not os.path.exists(memory_path):
        raise FileNotFoundError(f"{memory_path} が見つかりません")
    
    with open(memory_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_project_memory(memory: Dict[str, Any]) -> None:
    """プロジェクトメモリを保存"""
    memory['metadata']['last_updated'] = datetime.now().isoformat()
    
    with open("project_memory.json", 'w', encoding='utf-8') as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)


def add_new_rules(memory: Dict[str, Any]) -> Dict[str, Any]:
    """5つの新しいCRITICALルールを追加"""
    
    new_rules = [
        {
            "id": "RULE_019",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "source": "ユーザー要求分析",
            "rule": "品質優先絶対原則 - 月間1,500人以下の段階的拡張",
            "priority": "CRITICAL",
            "context": "年間20,000人目標は品質を保ちながら月1,100人ペースで達成、品質のための時間とコストは必要投資",
            "violations": [],
            "enforcement": "月間1,500人を超える急速拡張計画を検出したら即座に警告、品質検証なしの大量追加を防止"
        },
        {
            "id": "RULE_020",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "source": "品質保証要求",
            "rule": "段階的品質検証の必須化 - 100人チェックポイント",
            "priority": "CRITICAL",
            "context": "100人ごとに品質検証を実施、問題があれば即座に修正してから続行",
            "violations": [],
            "enforcement": "100人処理するごとに自動停止、削除率・有名人スコアを確認、異常があれば処理中断"
        },
        {
            "id": "RULE_021",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "source": "API制限学習",
            "rule": "APIレート制限の事前調査と遵守",
            "priority": "CRITICAL",
            "context": "SerpAPI無料版100/時間、有料版でも制限あり、事前にレート制限を確認してから実装",
            "violations": [],
            "enforcement": "API使用前に必ずレート制限を調査、制限を超える計画は即座に修正"
        },
        {
            "id": "RULE_022",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "source": "持続可能性原則",
            "rule": "年間計画の遵守 - 無理な短期目標の禁止",
            "priority": "CRITICAL",
            "context": "20,000人は年間目標、今月中に達成する必要なし、品質と持続可能性を優先",
            "violations": [],
            "enforcement": "短期間での大量処理計画を検出したら警告、年間ペースでの計画立案を強制"
        },
        {
            "id": "RULE_023",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "source": "Fail-Fast原則",
            "rule": "ダミーデータ返却の完全禁止",
            "priority": "CRITICAL",
            "context": "API障害時はダミーデータで継続せず、エラーとして正直に報告",
            "violations": [],
            "enforcement": "return 0、return []、mock data等を検出したら即座にSystemNotReadyErrorを発生"
        }
    ]
    
    # 既存のルールリストに追加
    existing_ids = {rule['id'] for rule in memory['permanent_rules']}
    
    for rule in new_rules:
        if rule['id'] not in existing_ids:
            memory['permanent_rules'].append(rule)
            print(f"✅ {rule['id']}: {rule['rule'][:50]}... を追加しました")
        else:
            print(f"⚠️ {rule['id']} は既に存在します")
    
    return memory


def update_quality_metrics(memory: Dict[str, Any]) -> Dict[str, Any]:
    """品質メトリクスを更新"""
    
    # 新しいメトリクスを追加
    new_metrics = {
        "monthly_addition_limit": {
            "value": 1500,
            "action": "月間1,500人を超える場合は品質レビュー必須"
        },
        "checkpoint_interval": {
            "value": 100,
            "action": "100人ごとに品質検証チェックポイント"
        },
        "api_rate_compliance": {
            "value": True,
            "action": "APIレート制限を超える場合は処理を分割"
        },
        "yearly_target": {
            "value": 20000,
            "monthly_pace": 1100,
            "action": "年間ペースを維持、急速拡張は禁止"
        },
        "dummy_data_tolerance": {
            "value": 0,
            "action": "ダミーデータは1件も許容しない"
        }
    }
    
    # 既存のメトリクスに追加
    for key, value in new_metrics.items():
        if key not in memory['quality_metrics']:
            memory['quality_metrics'][key] = value
            print(f"📊 品質メトリクス '{key}' を追加しました")
    
    return memory


def add_failed_patterns(memory: Dict[str, Any]) -> Dict[str, Any]:
    """失敗パターンを追加"""
    
    new_failed_patterns = [
        {
            "id": "FAIL_007",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "pattern": "APIレート制限の無視",
            "description": "レート制限を考慮せずに大量のAPI呼び出しを実行",
            "consequence": "429エラーで処理失敗、1.7%の成功率",
            "prevention": "事前にAPIレート制限を調査、適切な待機時間を設定"
        },
        {
            "id": "FAIL_008",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "pattern": "名前ベースのML判定",
            "description": "人物の名前パターンから知名度を推測",
            "consequence": "名前と知名度の因果関係は薄く、不正確な判定",
            "prevention": "客観的なWikipediaデータやトレンドデータを使用"
        },
        {
            "id": "FAIL_009",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "pattern": "サンプリング戦略の誤用",
            "description": "上位500人のみを処理して全体を推測",
            "consequence": "各人物の独立したパラメータを無視",
            "prevention": "全4,701人を個別に評価"
        }
    ]
    
    existing_fail_ids = {p['id'] for p in memory.get('failed_patterns', [])}
    
    for pattern in new_failed_patterns:
        if pattern['id'] not in existing_fail_ids:
            memory['failed_patterns'].append(pattern)
            print(f"❌ 失敗パターン {pattern['id']}: {pattern['pattern']} を追加しました")
    
    return memory


def main():
    """メイン処理"""
    print("=" * 60)
    print("PDCA Guardian System Update - Phase 1")
    print("5つの新しいCRITICALルールを追加")
    print("=" * 60)
    print()
    
    try:
        # プロジェクトメモリをロード
        print("📂 プロジェクトメモリをロード中...")
        memory = load_project_memory()
        print(f"✅ 現在のルール数: {len(memory['permanent_rules'])}")
        print()
        
        # 新しいルールを追加
        print("🔧 新しいCRITICALルールを追加中...")
        memory = add_new_rules(memory)
        print()
        
        # 品質メトリクスを更新
        print("📊 品質メトリクスを更新中...")
        memory = update_quality_metrics(memory)
        print()
        
        # 失敗パターンを追加
        print("❌ 失敗パターンを追加中...")
        memory = add_failed_patterns(memory)
        print()
        
        # 改善ログを追加
        improvement_entry = {
            "date": datetime.now().isoformat(),
            "type": "ルール追加",
            "description": "RULE_019-023: Wikipedia中心の知名度評価システム用ルール追加",
            "priority": "CRITICAL",
            "reason": "APIレート制限問題とML判定の不正確さを解決",
            "impact": "客観的で持続可能な知名度評価システムの実現"
        }
        memory['improvement_log'].append(improvement_entry)
        
        # 保存
        print("💾 プロジェクトメモリを保存中...")
        save_project_memory(memory)
        print(f"✅ 更新完了！ 新しいルール数: {len(memory['permanent_rules'])}")
        print()
        
        # サマリー
        print("=" * 60)
        print("📋 追加されたCRITICALルール:")
        print("  - RULE_019: 品質優先絶対原則（月間1,500人以下）")
        print("  - RULE_020: 100人チェックポイントでの品質検証")
        print("  - RULE_021: APIレート制限の事前調査と遵守")
        print("  - RULE_022: 年間計画の遵守（無理な短期目標禁止）")
        print("  - RULE_023: ダミーデータ返却の完全禁止")
        print("=" * 60)
        print()
        print("✅ Phase 1 完了！")
        print("次は Phase 2: Wikipedia中心の知名度評価システムの実装です")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {str(e)}")
        raise


if __name__ == "__main__":
    main()