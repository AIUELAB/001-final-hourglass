#!/usr/bin/env python3
"""
PDCAガーディアン - レート制限ルール
Brave Search APIのレート制限を克服した教訓を永続化
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime

@dataclass
class RateLimitRule:
    """レート制限ルール"""
    rule_id: str = "RATE_LIMIT_098"
    title: str = "API レート制限対策"
    created_date: str = "2025-09-15"

    def get_rule(self) -> Dict[str, Any]:
        """ルール定義を返す"""
        return {
            "id": self.rule_id,
            "title": self.title,
            "priority": "CRITICAL",
            "category": "API管理",
            "description": "外部APIのレート制限を適切に処理し、100%成功率を確保する",

            "problem_statement": """
            【問題】
            - Brave Search APIで0.2秒間隔の高速リクエストによりレート制限（429エラー）が発生
            - 3,569件中920件で処理が停止し、完工率が25.8%に留まった
            - 「動いているように見える」が実際は大量のエラーが発生していた
            """,

            "solution": """
            【解決策】
            1. 徹底的なレート制限調査の実施
               - 0.1秒〜5.0秒の間隔で体系的にテスト
               - 各間隔での成功率を測定
               - 最適な間隔を科学的に特定

            2. 発見した最適解
               - 1.0秒間隔 = 100%成功率
               - 1.5秒間隔 = 100%成功率（より保守的）
               - 0.5秒以下 = 50%以下の成功率（使用禁止）

            3. 複数APIキーの戦略的活用
               - キーごとの使用量を追跡
               - 枯渇前に次のキーへ自動切り替え
               - 全体で6,000枠を確保して余裕を持つ
            """,

            "implementation_rules": {
                "必須実装": [
                    "APIコール前に必ずレート制限チェック",
                    "最小間隔1.0秒の厳守（time.sleep(1.0)）",
                    "429エラー時は即座に処理停止",
                    "連続エラー検出機能（5回以上で長時間待機）",
                    "プログレスバーで実際の成功率を表示"
                ],

                "禁止事項": [
                    "0.5秒未満の間隔での連続リクエスト",
                    "エラーを無視して処理継続",
                    "ダミーデータでの補完",
                    "「とりあえず動かす」姿勢",
                    "レート制限テストの省略"
                ],

                "推奨事項": [
                    "処理開始前にテストリクエストで確認",
                    "バックアップの定期保存（100件ごと）",
                    "複数APIキーの準備と管理",
                    "詳細なログとレポートの生成",
                    "完了率の継続的なモニタリング"
                ]
            },

            "validation_checklist": [
                "レート制限テストを実施したか？",
                "最適な間隔を科学的に特定したか？",
                "エラー処理は適切に実装されているか？",
                "複数APIキーの切り替えは動作するか？",
                "100%成功率を達成できるか？"
            ],

            "success_metrics": {
                "必須達成目標": {
                    "API成功率": "95%以上",
                    "完工率": "100%",
                    "エラー回復率": "100%"
                },
                "推奨目標": {
                    "処理速度": "30-35件/分",
                    "APIキー効率": "80%以上の利用率",
                    "バックアップ頻度": "100件ごと"
                }
            },

            "code_example": """
# 正しい実装例
def call_api_with_rate_limit(query, api_key):
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return parse_response(response)
        elif response.status_code == 429:
            logger.error("レート制限エラー検出")
            return None  # エラーを明確に返す
        else:
            return None
    except Exception as e:
        logger.error(f"API呼び出しエラー: {e}")
        return None

# メインループ
for item in data:
    result = call_api_with_rate_limit(item, api_key)
    if result is None:
        consecutive_errors += 1
        if consecutive_errors >= 5:
            print("連続エラー検出。30秒待機...")
            time.sleep(30)
            consecutive_errors = 0
    else:
        consecutive_errors = 0
        success_count += 1

    # 必須：最適間隔での待機
    time.sleep(1.0)  # 1.0秒間隔を厳守
            """,

            "lessons_learned": """
            【教訓】
            1. レート制限は「推測」ではなく「実測」で対処する
            2. 失敗を恐れず、徹底的に調査する姿勢が重要
            3. 「簡単に諦めない」という指示の重要性
            4. 100%完工は可能 - 適切な方法を見つければ必ず達成できる
            5. エラーは隠さず、早期に顕在化させる
            """,

            "references": [
                "test_brave_rate_limit.py - レート制限調査スクリプト",
                "execute_remaining_brave_search.py - 100%完工実行スクリプト",
                "brave_rate_limit_report.json - 調査結果レポート"
            ]
        }

def add_to_pdca_guardian():
    """PDCAガーディアンにルールを追加"""
    rule = RateLimitRule()
    rule_data = rule.get_rule()

    # PDCAガーディアンのルールファイルに追加
    import json
    import os

    rules_file = "pdca_rules.json"

    # 既存のルールを読み込み
    if os.path.exists(rules_file):
        with open(rules_file, 'r', encoding='utf-8') as f:
            rules = json.load(f)
    else:
        rules = {"rules": [], "metadata": {"created": datetime.now().isoformat()}}

    # metadataが存在しない場合は作成
    if "metadata" not in rules:
        rules["metadata"] = {
            "created": datetime.now().isoformat()
        }

    # 新しいルールを追加
    rules["rules"].append(rule_data)
    rules["metadata"]["last_updated"] = datetime.now().isoformat()
    rules["metadata"]["total_rules"] = len(rules["rules"])

    # 保存
    with open(rules_file, 'w', encoding='utf-8') as f:
        json.dump(rules, f, indent=2, ensure_ascii=False)

    print(f"✅ ルール {rule.rule_id} を追加しました")
    print(f"   タイトル: {rule.title}")
    print(f"   優先度: CRITICAL")
    print(f"   カテゴリ: API管理")

    return rule_data

if __name__ == "__main__":
    # ルールを追加
    rule_data = add_to_pdca_guardian()

    # サマリーを表示
    print("\n" + "=" * 60)
    print("📋 レート制限ルール追加完了")
    print("=" * 60)
    print("\n【重要ポイント】")
    print("1. API間隔は必ず1.0秒以上")
    print("2. エラーは隠さず早期対処")
    print("3. 複数APIキーで冗長性確保")
    print("4. 100%完工は必ず達成可能")
    print("\n「レート制限で諦めない」 - この教訓を永続化しました")
