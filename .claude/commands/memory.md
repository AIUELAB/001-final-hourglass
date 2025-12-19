# Memory MCP操作委譲（コンテキスト節約）

Memory MCP操作をサブエージェントに委譲して実行します。
Knowledge Graphベースの長期記憶・セッション間情報保持が可能です。

## 使用方法

```
/memory <操作内容>
```

## 例

```
/memory ユーザーの好みを記録: Pythonが好き、VSCodeを使用
/memory プロジェクトの重要な決定事項を保存
/memory "エピソードDB"に関連する情報を検索
/memory 全ての記憶を表示
/memory "山田太郎"というエンティティを作成
```

## 実行指示

以下のTask toolを使用してサブエージェントに委譲してください：

```
Task tool:
  subagent_type: "general-purpose"
  prompt: |
    Memory MCPを使用して以下の操作を実行してください。

    操作: $ARGUMENTS

    利用可能なツール:
    - create_entities: エンティティ作成
    - create_relations: エンティティ間の関係作成
    - add_observations: エンティティに観察事項を追加
    - read_graph: 全Knowledge Graphを読み込み
    - search_nodes: ノード検索
    - open_nodes: 特定ノードを開く
    - delete_entities: エンティティ削除
    - delete_relations: 関係削除

    結果を簡潔にまとめて返してください。
```

## Knowledge Graphの構造

| 要素 | 説明 | 例 |
|------|------|-----|
| **Entity** | 主要ノード | 人物、プロジェクト、概念 |
| **Relation** | エンティティ間の関係 | "uses", "prefers", "created" |
| **Observation** | エンティティの詳細情報 | "Pythonが得意", "VSCodeを使用" |

## 保存場所

```
.memory/knowledge.jsonl
```

## メリット

- セッション間で情報が永続化
- 親セッションのコンテキスト消費: 0
- ユーザーの好み・プロジェクト情報を記憶
