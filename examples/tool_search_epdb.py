#!/usr/bin/env python3
"""
Tool Search Tool 実践例 - エピソードDB操作

このプロジェクトのエピソードDBに関連する20+のツールを定義し、
Tool Search Toolで動的に発見・実行するデモ。

使用方法:
    python examples/tool_search_epdb.py "品質チェックして"
    python examples/tool_search_epdb.py "重複を検出して"
    python examples/tool_search_epdb.py "統計を見せて"
"""

import json
import os
import sys
from pathlib import Path

import anthropic
import pandas as pd

# 設定
BETA_HEADER = "advanced-tool-use-2025-11-20"
MODEL = "claude-sonnet-4-5-20250929"
MASTER_CSV = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")


# =============================================================================
# ツール実行関数（実際のDB操作）
# =============================================================================

def get_episode_stats() -> dict:
    """エピソード統計を取得"""
    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig")
    return {
        "total_episodes": len(df),
        "unique_persons": df["person_id"].nunique(),
        "age_range": f"{df['age'].min()}-{df['age'].max()}歳",
        "avg_char_count": int(df["char_count"].mean()) if "char_count" in df.columns else "N/A",
        "categories": df["category"].value_counts().head(5).to_dict() if "category" in df.columns else {}
    }


def get_age_distribution() -> dict:
    """年齢分布を取得"""
    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig")
    bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 150]
    labels = ["0-9", "10-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80-89", "90-99", "100+"]
    df["age_group"] = pd.cut(df["age"], bins=bins, labels=labels, right=False)
    return df["age_group"].value_counts().sort_index().to_dict()


def detect_duplicates() -> dict:
    """重複エピソードを検出"""
    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig")
    duplicates = df[df.duplicated(subset=["person_id", "age"], keep=False)]
    return {
        "duplicate_count": len(duplicates),
        "affected_persons": duplicates["person_id"].nunique(),
        "sample": duplicates[["person_name", "age", "episode_id"]].head(5).to_dict("records")
    }


def check_quality_issues() -> dict:
    """品質問題を検出"""
    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig")
    issues = []

    # 空のエピソード本文
    if "episode_content" in df.columns:
        empty_content = df[df["episode_content"].isna() | (df["episode_content"] == "")]
        if len(empty_content) > 0:
            issues.append({"type": "empty_content", "count": len(empty_content)})

    # 短すぎるエピソード
    if "char_count" in df.columns:
        short_episodes = df[df["char_count"] < 100]
        if len(short_episodes) > 0:
            issues.append({"type": "short_episodes", "count": len(short_episodes), "threshold": "< 100文字"})

    # person_id欠損
    missing_id = df[df["person_id"].isna()]
    if len(missing_id) > 0:
        issues.append({"type": "missing_person_id", "count": len(missing_id)})

    return {
        "total_issues": sum(i["count"] for i in issues),
        "issues": issues,
        "quality_score": round((1 - sum(i["count"] for i in issues) / len(df)) * 100, 2)
    }


def search_person(name: str) -> dict:
    """人物を検索"""
    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig")
    matches = df[df["person_name"].str.contains(name, na=False)]
    return {
        "query": name,
        "match_count": len(matches),
        "persons": matches[["person_id", "person_name", "age"]].drop_duplicates("person_id").head(10).to_dict("records")
    }


def get_person_episodes(person_name: str) -> dict:
    """特定人物のエピソード一覧"""
    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig")
    matches = df[df["person_name"].str.contains(person_name, na=False)]
    return {
        "person": person_name,
        "episode_count": len(matches),
        "ages": sorted(matches["age"].unique().tolist()),
        "episodes": matches[["episode_id", "age", "category"]].head(10).to_dict("records") if "category" in matches.columns else matches[["episode_id", "age"]].head(10).to_dict("records")
    }


def get_category_stats() -> dict:
    """カテゴリ別統計"""
    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig")
    if "category" not in df.columns:
        return {"error": "category列がありません"}
    return df["category"].value_counts().to_dict()


def get_recent_episodes(limit: int = 10) -> dict:
    """最近追加されたエピソード"""
    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig")
    if "created_at" in df.columns:
        df = df.sort_values("created_at", ascending=False)
    return {
        "episodes": df[["episode_id", "person_name", "age"]].head(limit).to_dict("records")
    }


def validate_age_boundaries() -> dict:
    """年齢境界違反を検出"""
    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig")
    violations = []

    if "birth_year" in df.columns and "death_year" in df.columns:
        for _, row in df.iterrows():
            if pd.notna(row.get("death_year")):
                max_age = row["death_year"] - row["birth_year"]
                if row["age"] > max_age:
                    violations.append({
                        "person": row["person_name"],
                        "age": row["age"],
                        "max_age": max_age
                    })

    return {
        "violation_count": len(violations),
        "samples": violations[:5]
    }


def get_fictional_characters() -> dict:
    """架空キャラクターを取得"""
    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig")
    if "person_type" in df.columns:
        fictional = df[df["person_type"] == "FICTIONAL"]
        return {
            "count": len(fictional),
            "characters": fictional["person_name"].unique().tolist()[:20]
        }
    return {"error": "person_type列がありません"}


def get_group_members() -> dict:
    """グループメンバーを取得"""
    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig")
    if "is_group_member" in df.columns:
        members = df[df["is_group_member"] == True]
        return {
            "count": members["person_id"].nunique(),
            "groups": members.groupby("group_name")["person_name"].apply(lambda x: list(x.unique())).to_dict() if "group_name" in members.columns else {}
        }
    return {"error": "is_group_member列がありません"}


# ツールハンドラーのマッピング
TOOL_HANDLERS = {
    "get_episode_stats": get_episode_stats,
    "get_age_distribution": get_age_distribution,
    "detect_duplicates": detect_duplicates,
    "check_quality_issues": check_quality_issues,
    "search_person": search_person,
    "get_person_episodes": get_person_episodes,
    "get_category_stats": get_category_stats,
    "get_recent_episodes": get_recent_episodes,
    "validate_age_boundaries": validate_age_boundaries,
    "get_fictional_characters": get_fictional_characters,
    "get_group_members": get_group_members,
}


# =============================================================================
# ツール定義（defer_loading=True で遅延ロード）
# =============================================================================

DEFERRED_TOOLS = [
    # 統計系
    {
        "name": "get_episode_stats",
        "description": "エピソードDBの基本統計（総数、人物数、年齢範囲、平均文字数）を取得",
        "input_schema": {"type": "object", "properties": {}},
        "defer_loading": True
    },
    {
        "name": "get_age_distribution",
        "description": "年齢別のエピソード分布を10歳刻みで取得",
        "input_schema": {"type": "object", "properties": {}},
        "defer_loading": True
    },
    {
        "name": "get_category_stats",
        "description": "カテゴリ別のエピソード数を取得",
        "input_schema": {"type": "object", "properties": {}},
        "defer_loading": True
    },

    # 品質チェック系
    {
        "name": "detect_duplicates",
        "description": "重複エピソード（同一人物×同一年齢）を検出",
        "input_schema": {"type": "object", "properties": {}},
        "defer_loading": True
    },
    {
        "name": "check_quality_issues",
        "description": "品質問題（空コンテンツ、短文、ID欠損）を検出し品質スコアを算出",
        "input_schema": {"type": "object", "properties": {}},
        "defer_loading": True
    },
    {
        "name": "validate_age_boundaries",
        "description": "年齢境界違反（没年超過など）を検出",
        "input_schema": {"type": "object", "properties": {}},
        "defer_loading": True
    },

    # 検索系
    {
        "name": "search_person",
        "description": "人物名で検索してマッチする人物一覧を取得",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "検索する人物名（部分一致）"}
            },
            "required": ["name"]
        },
        "defer_loading": True
    },
    {
        "name": "get_person_episodes",
        "description": "特定人物のエピソード一覧を取得",
        "input_schema": {
            "type": "object",
            "properties": {
                "person_name": {"type": "string", "description": "人物名"}
            },
            "required": ["person_name"]
        },
        "defer_loading": True
    },

    # 特殊カテゴリ系
    {
        "name": "get_fictional_characters",
        "description": "架空キャラクター（FICTIONAL）の一覧を取得",
        "input_schema": {"type": "object", "properties": {}},
        "defer_loading": True
    },
    {
        "name": "get_group_members",
        "description": "グループ所属メンバーとグループ名を取得",
        "input_schema": {"type": "object", "properties": {}},
        "defer_loading": True
    },
    {
        "name": "get_recent_episodes",
        "description": "最近追加されたエピソードを取得",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "取得件数", "default": 10}
            }
        },
        "defer_loading": True
    },
]

# Tool Search Tool定義
TOOL_SEARCH_TOOL = {
    "type": "tool_search_tool_regex_20251119",
    "name": "tool_search_tool_regex"
}


def execute_tool(name: str, input_data: dict) -> str:
    """ツールを実行"""
    handler = TOOL_HANDLERS.get(name)
    if handler:
        try:
            result = handler(**input_data) if input_data else handler()
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
    return json.dumps({"error": f"Unknown tool: {name}"})


def run_agent(user_query: str):
    """Tool Search Toolを使ったエージェントを実行"""
    print(f"\n{'='*60}")
    print(f"クエリ: {user_query}")
    print(f"{'='*60}")
    print(f"\n登録ツール数: {len(DEFERRED_TOOLS)}")
    print("Tool Search Tool: regex型")

    client = anthropic.Anthropic()

    messages = [{"role": "user", "content": user_query}]
    all_tools = [TOOL_SEARCH_TOOL] + DEFERRED_TOOLS

    max_iterations = 5
    for iteration in range(1, max_iterations + 1):
        print(f"\n--- イテレーション {iteration} ---")

        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=2048,
            betas=[BETA_HEADER],
            tools=all_tools,
            messages=messages
        )

        print(f"stop_reason: {response.stop_reason}")

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text") and block.text:
                    print(f"\n📊 結果:\n{block.text}")
            break

        elif response.stop_reason == "tool_use":
            assistant_content = list(response.content)
            tool_results = []

            for block in response.content:
                if hasattr(block, "text") and block.text:
                    print(f"Claude: {block.text}")
                elif block.type == "tool_use":
                    print(f"🔧 ツール呼び出し: {block.name}")
                    if block.input:
                        print(f"   入力: {block.input}")

                    result = execute_tool(block.name, block.input)
                    print(f"   結果: {result[:200]}..." if len(result) > 200 else f"   結果: {result}")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "user", "content": tool_results})

    print(f"\n{'='*60}")


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("エラー: ANTHROPIC_API_KEY が設定されていません")
        return

    if not MASTER_CSV.exists():
        print(f"エラー: {MASTER_CSV} が見つかりません")
        return

    # コマンドライン引数またはインタラクティブ
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        run_agent(query)
    else:
        print("エピソードDB Tool Search デモ")
        print("-" * 40)
        print("例:")
        print('  python examples/tool_search_epdb.py "統計を見せて"')
        print('  python examples/tool_search_epdb.py "品質チェックして"')
        print('  python examples/tool_search_epdb.py "手塚治虫のエピソードを探して"')
        print("-" * 40)

        queries = [
            "エピソードDBの統計と品質スコアを教えて",
            "重複と年齢境界違反をチェックして",
            "架空キャラクターは何人いる？",
        ]

        print("\nサンプルクエリを実行:")
        for q in queries[:1]:  # 最初の1つだけ実行
            run_agent(q)


if __name__ == "__main__":
    main()
