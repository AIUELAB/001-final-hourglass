---
description: Tool Runner SDK - Advanced Tool Use (Beta) デモ実行
---

# Tool Runner SDK デモ

Anthropic Advanced Tool Use (Beta) 機能のデモを実行します。

## 使用方法

```
/tool-runner [demo_number]
```

## 引数

- `1` - 基本的なツール使用（手動ループ）
- `2` - Tool Use Examples（パラメータ精度向上）
- `3` - Tool Search Tool（動的ツール発見）
- `4` - 並列ツール実行
- `5` - 統合エージェント
- `all` - すべて実行
- 引数なし - インタラクティブメニュー

---

## 実行指示

$ARGUMENTS に基づいて `examples/tool_runner_sdk_examples.py` を実行してください。

### 引数が指定されている場合

```bash
echo "$ARGUMENTS" | python examples/tool_runner_sdk_examples.py
```

### 引数が空または "all" の場合

```bash
echo "a" | python examples/tool_runner_sdk_examples.py
```

### 実行後

結果を日本語で要約し、以下を報告してください：

1. **実行したデモ**: どのデモが実行されたか
2. **ツール呼び出し**: 何のツールが何回呼び出されたか
3. **イテレーション数**: 完了までのループ回数
4. **最終結果**: Claudeの回答内容

### エラー時

- `ANTHROPIC_API_KEY` が未設定の場合は設定方法を案内
- ベータ機能エラーの場合はフォールバック動作を説明

---

## 機能説明

| 機能 | ベータヘッダー | 効果 |
|------|---------------|------|
| Tool Use Examples | `advanced-tool-use-2025-11-20` | パラメータ精度 72%→90% |
| Tool Search Tool | 同上 | コンテキスト 55K→8.7K |
| Programmatic Calling | 不要 | トークン 37%削減 |
