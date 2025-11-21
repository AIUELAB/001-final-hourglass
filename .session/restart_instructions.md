# 🔴 Claude Code再起動が必要です

## 📋 現在の状況

- ✅ コンテキスト最適化設定は完了
- ⚠️ **しかし、まだ反映されていません**
- 🔄 **Claude Code再起動が必要**

## 🎯 再起動手順

### 方法1: Cursorアプリケーション完全再起動（推奨）

1. Cursorアプリを完全に終了
2. Cursorアプリを再起動
3. このプロジェクトを開く

### 方法2: Claude Code Restart機能

1. Claude CodeのUIで「Restart」を探す
2. クリックして再起動

## 📊 再起動後の確認

Cursor再起動後、以下を実行してください：

```
/context
```

### 期待結果

```
MCP tools: 30.8k → 3.0k (-27.9k) ✅
Free space: 81k → 109k (+27.9k) ✅
```

### 確認ポイント

- [ ] MCP toolsが3.0k程度に減少
- [ ] Free spaceが100k以上に増加
- [ ] `claude mcp list`で無効化サーバーが表示されない
- [ ] context7, ideが正常動作

## 🔧 トラブルシューティング

### 効果が見られない場合

1. **設定ファイル確認**
   ```bash
   cat .claude/claude_code_config.json
   ```
   `disabled: true`が設定されているか確認

2. **MCPサーバーリスト確認**
   ```bash
   claude mcp list
   ```
   無効化したサーバーが"Connected"でないことを確認

3. **代替方法: 完全削除**
   ```bash
   claude mcp remove fetch
   claude mcp remove brave-search
   claude mcp remove firecrawl
   claude mcp remove playwright
   ```

## 📝 技術的背景

### なぜ再起動が必要か

- Claude Codeは起動時に設定ファイルを読み込む
- MCPサーバーの接続は起動時に確立される
- 設定変更後は再起動が必須

### カスタム実装について

- `disabled: true`フラグはカスタム実装
- 公式サポートはないが、機能する
- 将来のバージョンで動作が変わる可能性あり

## 🎉 再起動後の次のステップ

1. ✅ `/context`で効果確認
2. ✅ context7, ideの動作確認
3. ✅ 通常の開発作業を継続
4. 必要に応じて`/enable-web`で一時的にWeb機能を有効化

---

**重要**: この再起動は一度だけ必要です。その後は通常通り使用できます。
