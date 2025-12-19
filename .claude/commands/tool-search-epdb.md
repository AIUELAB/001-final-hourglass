---
description: Tool Search - エピソードDB操作（動的ツール発見）
---

# Tool Search エピソードDB

Tool Search Tool（β版）を使って、11のDB操作ツールから動的に発見・実行します。

## 使用方法

```
/tool-search-epdb [クエリ]
```

## クエリ例

| クエリ | 発見されるツール |
|--------|-----------------|
| 統計を見せて | `get_episode_stats` |
| 品質チェックして | `check_quality_issues` |
| 重複を検出して | `detect_duplicates` |
| 年齢分布を見せて | `get_age_distribution` |
| 架空キャラクターは？ | `get_fictional_characters` |
| 手塚治虫を検索 | `search_person` |
| グループメンバー一覧 | `get_group_members` |

## 登録ツール（11種）

**統計系:** get_episode_stats, get_age_distribution, get_category_stats
**品質系:** detect_duplicates, check_quality_issues, validate_age_boundaries
**検索系:** search_person, get_person_episodes
**特殊系:** get_fictional_characters, get_group_members, get_recent_episodes

---

## 実行指示

$ARGUMENTS をクエリとして `examples/tool_search_epdb.py` を実行してください。

### 引数がある場合

```bash
python examples/tool_search_epdb.py "$ARGUMENTS"
```

### 引数がない場合

デフォルトクエリ「エピソードDBの統計と品質スコアを教えて」を実行:

```bash
python examples/tool_search_epdb.py "エピソードDBの統計と品質スコアを教えて"
```

### 実行後

結果を日本語で要約し、以下を報告:

1. **発見されたツール**: Tool Searchが選んだツール名
2. **ツール実行結果**: 各ツールの出力
3. **最終回答**: Claudeの分析結果

### エラー時

- `ANTHROPIC_API_KEY` 未設定 → 設定方法を案内
- CSVファイル未検出 → パスを確認
