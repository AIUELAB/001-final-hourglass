#!/usr/bin/env python3
"""
Tool Runner SDK 実装例
======================

Anthropic Advanced Tool Use (Beta) の3つの機能を実装したサンプル:
1. Tool Search Tool - 数千のツールを動的に発見
2. Programmatic Tool Calling - ツール実行の自動オーケストレーション
3. Tool Use Examples - 具体的な使用例でパラメータ精度向上

必要条件:
- anthropic>=0.40.0
- ANTHROPIC_API_KEY 環境変数

使用方法:
    python examples/tool_runner_sdk_examples.py
"""

import json
import os
from typing import Any

import anthropic

# ベータヘッダー（Advanced Tool Use機能用）
BETA_HEADER = "advanced-tool-use-2025-11-20"

# 使用モデル
MODEL = "claude-sonnet-4-5-20250929"


# =============================================================================
# 1. 基本的なツール定義と手動ループ
# =============================================================================

def basic_tool_use_example():
    """基本的なツール使用例（手動ループ）"""
    print("\n" + "=" * 60)
    print("1. 基本的なツール使用例（手動ループ）")
    print("=" * 60)

    client = anthropic.Anthropic()

    # ツール定義
    tools = [
        {
            "name": "get_weather",
            "description": "指定された都市の現在の天気を取得します",
            "input_schema": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "都市名（例: 東京、大阪、福岡）"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "温度の単位"
                    }
                },
                "required": ["city"]
            }
        },
        {
            "name": "get_time",
            "description": "指定されたタイムゾーンの現在時刻を取得します",
            "input_schema": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "タイムゾーン（例: Asia/Tokyo, America/New_York）"
                    }
                },
                "required": ["timezone"]
            }
        }
    ]

    # ツール実行関数
    def execute_tool(name: str, input_data: dict) -> str:
        """ツールを実行してJSONレスポンスを返す"""
        if name == "get_weather":
            # モック天気データ
            weather_data = {
                "東京": {"temperature": 15, "condition": "晴れ", "humidity": 45},
                "大阪": {"temperature": 17, "condition": "曇り", "humidity": 55},
                "福岡": {"temperature": 18, "condition": "晴れ", "humidity": 50},
            }
            city = input_data.get("city", "東京")
            data = weather_data.get(city, {"temperature": 20, "condition": "不明", "humidity": 50})
            return json.dumps(data, ensure_ascii=False)

        elif name == "get_time":
            from datetime import datetime
            # モック時刻データ
            return json.dumps({
                "timezone": input_data.get("timezone", "Asia/Tokyo"),
                "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "day_of_week": datetime.now().strftime("%A")
            }, ensure_ascii=False)

        return json.dumps({"error": f"Unknown tool: {name}"})

    # 初期リクエスト
    messages = [
        {"role": "user", "content": "東京の天気と現在時刻を教えてください"}
    ]

    print(f"\nユーザー: {messages[0]['content']}")

    # ツール実行ループ
    max_iterations = 10
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        print(f"\n--- イテレーション {iteration} ---")

        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=tools,
            messages=messages
        )

        print(f"stop_reason: {response.stop_reason}")

        # レスポンス処理
        if response.stop_reason == "end_turn":
            # 最終回答
            for block in response.content:
                if hasattr(block, "text"):
                    print(f"\nClaude: {block.text}")
            break

        elif response.stop_reason == "tool_use":
            # ツール呼び出しを処理
            assistant_content = []
            tool_results = []

            for block in response.content:
                if block.type == "text":
                    assistant_content.append(block)
                    print(f"Claude（途中）: {block.text}")
                elif block.type == "tool_use":
                    assistant_content.append(block)
                    print(f"ツール呼び出し: {block.name}({block.input})")

                    # ツール実行
                    result = execute_tool(block.name, block.input)
                    print(f"ツール結果: {result}")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            # 会話履歴に追加
            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "user", "content": tool_results})

    print(f"\n完了（{iteration}回のイテレーション）")


# =============================================================================
# 2. Tool Use Examples（具体例によるパラメータ精度向上）
# =============================================================================

def tool_use_examples_demo():
    """Tool Use Examples機能のデモ（ベータ版）"""
    print("\n" + "=" * 60)
    print("2. Tool Use Examples（具体例によるパラメータ精度向上）")
    print("=" * 60)

    client = anthropic.Anthropic()

    # input_examplesを含むツール定義（ベータ機能）
    tools = [
        {
            "name": "search_database",
            "description": "データベースからエピソードを検索します",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "object",
                        "properties": {
                            "person_name": {"type": "string"},
                            "age_range": {
                                "type": "object",
                                "properties": {
                                    "min": {"type": "integer"},
                                    "max": {"type": "integer"}
                                }
                            },
                            "categories": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        }
                    },
                    "limit": {"type": "integer", "default": 10},
                    "sort_by": {
                        "type": "string",
                        "enum": ["relevance", "date", "popularity"]
                    }
                },
                "required": ["query"]
            },
            # ベータ機能: 具体的な使用例
            "input_examples": [
                {
                    "query": {
                        "person_name": "山田太郎",
                        "age_range": {"min": 20, "max": 30},
                        "categories": ["仕事", "成長"]
                    },
                    "limit": 5,
                    "sort_by": "relevance"
                },
                {
                    "query": {
                        "person_name": "鈴木花子",
                        "categories": ["教育", "家族"]
                    },
                    "sort_by": "date"
                },
                {
                    "query": {
                        "age_range": {"min": 50, "max": 60}
                    },
                    "limit": 20,
                    "sort_by": "popularity"
                }
            ]
        }
    ]

    print("\nツール定義（input_examples付き）:")
    print(json.dumps(tools[0], indent=2, ensure_ascii=False)[:500] + "...")

    # ベータAPIを使用
    try:
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=1024,
            betas=[BETA_HEADER],
            tools=tools,
            messages=[
                {"role": "user", "content": "30代の人物で仕事関連のエピソードを5件検索してください"}
            ]
        )

        print(f"\nレスポンス:")
        for block in response.content:
            if block.type == "tool_use":
                print(f"ツール: {block.name}")
                print(f"入力パラメータ: {json.dumps(block.input, indent=2, ensure_ascii=False)}")
            elif hasattr(block, "text"):
                print(f"テキスト: {block.text}")

    except anthropic.BadRequestError as e:
        print(f"\n注意: ベータ機能が利用できない可能性があります")
        print(f"エラー: {e}")
        print("通常のツール定義で再試行します...")

        # フォールバック: 通常のツール定義
        tools_without_examples = [{k: v for k, v in tools[0].items() if k != "input_examples"}]
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=tools_without_examples,
            messages=[
                {"role": "user", "content": "30代の人物で仕事関連のエピソードを5件検索してください"}
            ]
        )
        for block in response.content:
            if block.type == "tool_use":
                print(f"ツール: {block.name}")
                print(f"入力パラメータ: {json.dumps(block.input, indent=2, ensure_ascii=False)}")


# =============================================================================
# 3. Tool Search Tool（動的ツール発見）
# =============================================================================

def tool_search_demo():
    """Tool Search Tool機能のデモ（ベータ版）"""
    print("\n" + "=" * 60)
    print("3. Tool Search Tool（動的ツール発見）")
    print("=" * 60)

    client = anthropic.Anthropic()

    # 大量のツールを定義（defer_loading=Trueでオンデマンドロード）
    deferred_tools = [
        {
            "name": "weather_tokyo",
            "description": "東京の天気を取得",
            "input_schema": {"type": "object", "properties": {}},
            "defer_loading": True
        },
        {
            "name": "weather_osaka",
            "description": "大阪の天気を取得",
            "input_schema": {"type": "object", "properties": {}},
            "defer_loading": True
        },
        {
            "name": "stock_price",
            "description": "株価を取得",
            "input_schema": {
                "type": "object",
                "properties": {"symbol": {"type": "string"}},
                "required": ["symbol"]
            },
            "defer_loading": True
        },
        {
            "name": "news_search",
            "description": "ニュースを検索",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            },
            "defer_loading": True
        },
        {
            "name": "calendar_events",
            "description": "カレンダーイベントを取得",
            "input_schema": {
                "type": "object",
                "properties": {"date": {"type": "string"}},
                "required": ["date"]
            },
            "defer_loading": True
        }
    ]

    # Tool Search Tool（Regex型）
    # 注意: name は "tool_search_tool_regex" 固定（APIの要件）
    tool_search_tool = {
        "type": "tool_search_tool_regex_20251119",
        "name": "tool_search_tool_regex"
    }

    print(f"\n登録ツール数: {len(deferred_tools)}")
    print("Tool Search Tool: regex型を使用")

    try:
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=1024,
            betas=[BETA_HEADER],
            tools=[tool_search_tool] + deferred_tools,
            messages=[
                {"role": "user", "content": "天気に関するツールを探して、東京の天気を教えてください"}
            ]
        )

        print(f"\nレスポンス (stop_reason: {response.stop_reason}):")
        for block in response.content:
            if block.type == "tool_use":
                print(f"ツール呼び出し: {block.name}")
                print(f"入力: {json.dumps(block.input, indent=2, ensure_ascii=False)}")
            elif hasattr(block, "text"):
                print(f"テキスト: {block.text}")

    except anthropic.BadRequestError as e:
        print(f"\n注意: Tool Search Tool (ベータ) が利用できません")
        print(f"エラー: {e}")
        print("\n代替: 通常のツール選択で実行します...")

        # フォールバック
        normal_tools = [{k: v for k, v in t.items() if k != "defer_loading"} for t in deferred_tools]
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=normal_tools,
            messages=[
                {"role": "user", "content": "東京の天気を教えてください"}
            ]
        )
        for block in response.content:
            if block.type == "tool_use":
                print(f"ツール呼び出し: {block.name}")


# =============================================================================
# 4. 並列ツール実行（Programmatic Tool Calling）
# =============================================================================

def parallel_tool_execution_demo():
    """並列ツール実行のデモ"""
    print("\n" + "=" * 60)
    print("4. 並列ツール実行（Programmatic Tool Calling）")
    print("=" * 60)

    client = anthropic.Anthropic()

    tools = [
        {
            "name": "get_weather",
            "description": "都市の天気を取得",
            "input_schema": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "都市名"}
                },
                "required": ["city"]
            }
        },
        {
            "name": "get_population",
            "description": "都市の人口を取得",
            "input_schema": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "都市名"}
                },
                "required": ["city"]
            }
        }
    ]

    def execute_tool(name: str, input_data: dict) -> str:
        """ツール実行（モック）"""
        if name == "get_weather":
            weather = {"東京": "晴れ 15°C", "大阪": "曇り 17°C", "名古屋": "晴れ 16°C"}
            return json.dumps({"weather": weather.get(input_data["city"], "不明")}, ensure_ascii=False)
        elif name == "get_population":
            pop = {"東京": "約1400万人", "大阪": "約880万人", "名古屋": "約230万人"}
            return json.dumps({"population": pop.get(input_data["city"], "不明")}, ensure_ascii=False)
        return "{}"

    messages = [
        {"role": "user", "content": "東京と大阪の天気と人口を教えてください"}
    ]

    print(f"\nユーザー: {messages[0]['content']}")

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=tools,
        messages=messages
    )

    if response.stop_reason == "tool_use":
        # 複数のツール呼び出しを収集
        tool_calls = [b for b in response.content if b.type == "tool_use"]
        print(f"\n並列ツール呼び出し: {len(tool_calls)}件")

        # すべてのツールを（並列で）実行
        tool_results = []
        for tool_call in tool_calls:
            print(f"  - {tool_call.name}({tool_call.input})")
            result = execute_tool(tool_call.name, tool_call.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_call.id,
                "content": result
            })

        # 結果を一括で返送（重要: すべての結果を1つのメッセージで）
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

        # 最終レスポンス取得
        final_response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=tools,
            messages=messages
        )

        for block in final_response.content:
            if hasattr(block, "text"):
                print(f"\nClaude: {block.text}")


# =============================================================================
# 5. 完全なエージェントループ（統合例）
# =============================================================================

class ToolRunnerAgent:
    """Tool Runner SDK風のエージェント実装"""

    def __init__(self, model: str = MODEL, max_iterations: int = 10):
        self.client = anthropic.Anthropic()
        self.model = model
        self.max_iterations = max_iterations
        self.tools: list[dict] = []
        self.tool_handlers: dict[str, callable] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: dict,
        handler: callable,
        examples: list[dict] | None = None
    ):
        """ツールを登録"""
        tool_def = {
            "name": name,
            "description": description,
            "input_schema": input_schema
        }
        if examples:
            tool_def["input_examples"] = examples

        self.tools.append(tool_def)
        self.tool_handlers[name] = handler
        print(f"ツール登録: {name}")

    def run(self, user_message: str, use_beta: bool = False) -> str:
        """エージェントを実行して最終回答を返す"""
        messages = [{"role": "user", "content": user_message}]

        # ベータ機能を使わない場合、input_examplesを除外
        tools_to_use = self.tools
        if not use_beta:
            tools_to_use = [
                {k: v for k, v in tool.items() if k != "input_examples"}
                for tool in self.tools
            ]

        for iteration in range(1, self.max_iterations + 1):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                tools=tools_to_use,
                messages=messages
            )

            if response.stop_reason == "end_turn":
                # 最終回答を返す
                for block in response.content:
                    if hasattr(block, "text"):
                        return block.text
                return ""

            elif response.stop_reason == "tool_use":
                # ツール呼び出しを処理
                assistant_content = list(response.content)
                tool_results = []

                for block in response.content:
                    if block.type == "tool_use":
                        handler = self.tool_handlers.get(block.name)
                        if handler:
                            try:
                                result = handler(**block.input)
                                if not isinstance(result, str):
                                    result = json.dumps(result, ensure_ascii=False)
                            except Exception as e:
                                result = json.dumps({"error": str(e)})
                        else:
                            result = json.dumps({"error": f"Unknown tool: {block.name}"})

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result
                        })

                messages.append({"role": "assistant", "content": assistant_content})
                messages.append({"role": "user", "content": tool_results})

        return "最大イテレーション数に達しました"


def agent_demo():
    """統合エージェントのデモ"""
    print("\n" + "=" * 60)
    print("5. 統合エージェント（Tool Runner風実装）")
    print("=" * 60)

    agent = ToolRunnerAgent()

    # ツール1: 天気取得
    def get_weather(city: str, unit: str = "celsius") -> dict:
        weather_data = {
            "東京": {"temp": 15, "condition": "晴れ"},
            "大阪": {"temp": 17, "condition": "曇り"},
        }
        data = weather_data.get(city, {"temp": 20, "condition": "不明"})
        if unit == "fahrenheit":
            data["temp"] = data["temp"] * 9 / 5 + 32
        data["unit"] = unit
        return data

    agent.register_tool(
        name="get_weather",
        description="都市の天気を取得します",
        input_schema={
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "都市名"},
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
            },
            "required": ["city"]
        },
        handler=get_weather,
        examples=[
            {"city": "東京", "unit": "celsius"},
            {"city": "大阪"}
        ]
    )

    # ツール2: 計算
    def calculate(expression: str) -> dict:
        try:
            # 安全な評価（実際のプロダクションではより厳密に）
            allowed_chars = set("0123456789+-*/().% ")
            if all(c in allowed_chars for c in expression):
                result = eval(expression)
                return {"expression": expression, "result": result}
            else:
                return {"error": "Invalid expression"}
        except Exception as e:
            return {"error": str(e)}

    agent.register_tool(
        name="calculate",
        description="数式を計算します",
        input_schema={
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "計算式（例: 2+3*4）"}
            },
            "required": ["expression"]
        },
        handler=calculate
    )

    # エージェント実行
    print("\n--- エージェント実行 ---")
    query = "東京の天気を確認して、気温を華氏に変換した値を2倍してください"
    print(f"ユーザー: {query}")

    result = agent.run(query)
    print(f"\nClaude: {result}")


# =============================================================================
# メイン実行
# =============================================================================

def main():
    """すべてのデモを実行"""
    print("=" * 60)
    print(" Tool Runner SDK 実装例")
    print(" Advanced Tool Use (Beta) Features Demo")
    print("=" * 60)

    # APIキー確認
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\nエラー: ANTHROPIC_API_KEY 環境変数が設定されていません")
        return

    # デモ実行
    demos = [
        ("1. 基本的なツール使用", basic_tool_use_example),
        ("2. Tool Use Examples", tool_use_examples_demo),
        ("3. Tool Search Tool", tool_search_demo),
        ("4. 並列ツール実行", parallel_tool_execution_demo),
        ("5. 統合エージェント", agent_demo),
    ]

    print("\n実行するデモを選択してください:")
    for i, (name, _) in enumerate(demos, 1):
        print(f"  {i}. {name}")
    print("  a. すべて実行")
    print("  q. 終了")

    choice = input("\n選択 (1-5, a, q): ").strip().lower()

    if choice == "q":
        return
    elif choice == "a":
        for name, func in demos:
            try:
                func()
            except Exception as e:
                print(f"\nエラー: {e}")
    elif choice.isdigit() and 1 <= int(choice) <= len(demos):
        try:
            demos[int(choice) - 1][1]()
        except Exception as e:
            print(f"\nエラー: {e}")
    else:
        print("無効な選択です")


if __name__ == "__main__":
    main()
