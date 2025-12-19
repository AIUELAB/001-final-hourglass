# MCP操作汎用委譲（コンテキスト節約）

任意のMCP操作をサブエージェントに委譲して実行します。
親セッションのコンテキストを節約しながら、MCP機能をフル活用できます。

## 使用方法

```
/delegate <MCP名> <操作内容>
```

## 例

```
/delegate github PRの一覧を取得
/delegate serena クラス定義を検索
/delegate context7 Anthropic SDKのドキュメント
/delegate sequential-thinking 複雑な問題を分析
```

## 実行指示

以下のTask toolを使用してサブエージェントに委譲してください：

```
Task tool:
  subagent_type: "general-purpose"
  prompt: |
    以下のMCP操作を実行してください。

    MCP: $MCP_NAME
    操作: $OPERATION

    結果を簡潔にまとめて返してください。
```

## 対応MCP一覧

| MCP | 推定トークン | 主な機能 |
|-----|-------------|---------|
| github | ~15k | リポジトリ操作、Issue、PR |
| serena | ~20k | セマンティックコード操作 |
| context7 | ~1.8k | ライブラリドキュメント |
| sequential-thinking | ~1.5k | 段階的思考分析 |
| ide | ~1.3k | IDE統合、診断 |

## コンテキスト節約効果

| パターン | 消費トークン |
|---------|-------------|
| 直接MCP使用 | 44.9k（全MCP定義がロード） |
| 委譲パターン | 結果のみ（数百〜数千） |

## ショートカット

よく使う操作は専用スキルを使用:
- `/gh` - GitHub操作
- `/serena` - Serena操作
