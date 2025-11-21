# Web検索・スクレイピング機能を有効化

コンテキスト効率化のため、以下のMCPサーバーは通常無効化されています：
- brave-search (Web検索)
- firecrawl (高度なスクレイピング)
- playwright (ブラウザ自動化)
- fetch (Web取得)

## 一時的に有効化する手順

1. `.claude/claude_code_config.json`を編集
2. 必要なサーバーの`"disabled": true`を`"disabled": false`に変更
3. Claude Codeを再起動

## 使用後の再無効化

使用後は必ず無効化してコンテキストを節約してください。

1. `.claude/claude_code_config.json`を編集
2. `"disabled": false`を`"disabled": true`に戻す
3. Claude Codeを再起動
