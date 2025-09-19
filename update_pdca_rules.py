#!/usr/bin/env python3
"""
PDCAガーディアンシステムに新しいルールを追加
特別カテゴリ評価に関するルール（RULE_036-040）
"""

import json
from datetime import datetime
from pathlib import Path

def add_special_category_rules():
    """特別カテゴリ評価に関するルールを追加"""
    
    # project_memory.jsonを読み込み
    memory_file = Path("project_memory.json")
    with open(memory_file, 'r', encoding='utf-8') as f:
        memory = json.load(f)
    
    # 新しいルールを追加
    new_rules = [
        {
            "id": "RULE_036",
            "date": "2025-09-10",
            "source": "ユーザー指摘（特別カテゴリ評価）",
            "rule": "教科書掲載人物は最低スコア7.0、世界史的重要人物は9.0を保証",
            "priority": "CRITICAL",
            "category": "データ品質",
            "context": "ガンジー(P000439)が3.0点という深刻な問題を防止",
            "violations": [],
            "enforcement": "special_category_evaluator.pyの教科書掲載人物リストで判定",
            "description": "教科書に載っている人物は削除対象にしてはいけない"
        },
        {
            "id": "RULE_037",
            "date": "2025-09-10",
            "source": "ユーザー指摘（スポーツ功績）",
            "rule": "オリンピック金メダリストは最低スコア7.0を保証",
            "priority": "CRITICAL",
            "category": "データ品質",
            "context": "松本薫(P003743)のような金メダリストが3.0点になる問題を防止",
            "violations": [],
            "enforcement": "オリンピック関連キーワードの検出と最低スコア適用",
            "description": "日本人の金メダリストは削除対象にすべきではない"
        },
        {
            "id": "RULE_038",
            "date": "2025-09-10",
            "source": "ユーザー指摘（エンターテインメント）",
            "rule": "M-1優勝者は7.0、決勝進出者は6.0の最低スコアを保証",
            "priority": "CRITICAL",
            "category": "データ品質",
            "context": "斎藤司(P003405)、ランジャタイ等のお笑い芸人が低評価になる問題を防止",
            "violations": [],
            "enforcement": "M-1関連の実績を持つ芸人のリストで判定",
            "description": "M-1の決勝に行っている人物は削除対象にすべきではない"
        },
        {
            "id": "RULE_039",
            "date": "2025-09-10",
            "source": "ユーザー指摘（YouTube/SNS）",
            "rule": "登録者100万人以上のYouTuberは最低スコア6.0を保証",
            "priority": "CRITICAL",
            "category": "データ品質",
            "context": "カンタ(水溜りボンド)(P000417)等の人気YouTuberが低評価になる問題を防止",
            "violations": [],
            "enforcement": "主要YouTuberリストと登録者数基準で判定",
            "description": "チャンネル登録者数100万人以上の主要メンバーは削除対象にすべきではない"
        },
        {
            "id": "RULE_040",
            "date": "2025-09-10",
            "source": "ユーザー指摘（削除しきい値）",
            "rule": "削除しきい値を3.0から4.0に引き上げ",
            "priority": "CRITICAL",
            "category": "データ品質",
            "context": "より慎重な削除判定を行うため、しきい値を4.0未満に変更",
            "violations": [],
            "enforcement": "recognition_score < 4.0で削除対象と判定",
            "description": "削除基準をより厳格にして、誤削除を防止"
        }
    ]
    
    # ルールを追加
    for rule in new_rules:
        memory["permanent_rules"].append(rule)
    
    # quality_metricsも更新
    memory["quality_metrics"]["deletion_threshold"] = {
        "value": 4.0,
        "action": "4.0未満のスコアで削除対象"
    }
    
    memory["quality_metrics"]["special_category_minimum"] = {
        "textbook_figures": 7.0,
        "world_historical": 9.0,
        "olympic_gold": 7.0,
        "m1_champion": 7.0,
        "m1_finalist": 6.0,
        "youtube_1m": 6.0,
        "famous_band": 6.0,
        "action": "各カテゴリの最低スコアを保証"
    }
    
    # 最終更新日時を更新
    memory["metadata"]["last_updated"] = datetime.now().isoformat()
    
    # 改善ログに追加
    memory["improvement_log"].append({
        "date": datetime.now().isoformat(),
        "type": "ルール追加",
        "description": "RULE_036-040: 特別カテゴリ評価ルール追加",
        "priority": "CRITICAL",
        "reason": "ガンジー、松本薫、斎藤司等の重要人物が低評価になる問題を発見",
        "impact": "教育・スポーツ・エンタメ・YouTube分野の人物を適切に保護"
    })
    
    # ファイルに保存
    with open(memory_file, 'w', encoding='utf-8') as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)
    
    print("✅ PDCAルール追加完了（RULE_036-040）")
    print("追加されたルール:")
    for rule in new_rules:
        print(f"  - {rule['id']}: {rule['rule']}")

if __name__ == "__main__":
    add_special_category_rules()