# セッション記録・復元システム

Claude Code/Cursorのクラッシュに備えた自動セッション記録・復元システム

## 🎯 概要

このシステムは、Claude Code/Cursorがクラッシュした際に作業内容を失わないよう、以下を自動的に記録します:

- ユーザーのプロンプト
- アシスタントの応答
- セッション状態（現在のタスク、TODOリスト等）
- コンテキスト情報

## 📁 ディレクトリ構造

```
.session/
├── README.md                    # このファイル
├── STATUS.md                    # 現在のセッション状態
├── SESSION_LOG.md               # 会話履歴
├── serena_memory.json          # Serenaメモリストア
├── auto_commit.log             # Git自動コミットログ
├── snapshots/                  # スナップショット
│   ├── YYYYMMDD_HHMMSS.md     # タイムスタンプ付きスナップショット
│   └── latest.md -> (最新へのリンク)
└── recovery/                   # 復元ポイント
    └── last_stable.json        # 最後の安定状態
```

## 🚀 自動記録の仕組み

### 1. リアルタイム記録（フックベース）

`~/.claude/hooks/` に統合されたフックが、ユーザーのプロンプトとアシスタントの応答を自動記録:

- **user-prompt-submit-hook**: プロンプト送信時に記録
- **completion-hook**: 応答完了時に記録

### 2. 3層バックアップ

#### Layer 1: ファイルベース記録
- `STATUS.md`: 現在のセッション状態
- `SESSION_LOG.md`: 完全な会話履歴

#### Layer 2: Serenaメモリ
- 構造化されたセッションデータ
- 意思決定履歴、ブロッカー管理
- 高速な読み書きアクセス

#### Layer 3: Git自動コミット
- **5分間隔**: launchdによる自動実行
- .session/配下の変更を自動コミット
- タイムスタンプ付きコミットメッセージ

## 🔄 復元方法

### クイック復元（推奨）

```bash
# 対話的復元UI
python3 scripts/session_recovery.py
```

対話的UIで以下から選択:
1. ファイルベース復元
2. Serenaメモリ復元
3. スナップショット復元
4. すべて表示

### 個別復元

#### Serenaメモリから復元
```bash
python3 scripts/session_recovery.py restore-serena
```

#### ファイルから復元
```bash
python3 scripts/session_recovery.py restore-file
```

#### 復元ポイント一覧
```bash
python3 scripts/session_recovery.py list
```

### 手動確認

#### STATUS.mdを確認
```bash
cat .session/STATUS.md
```

現在のセッション状態、最後のプロンプト、TODOリストを確認できます。

#### SESSION_LOG.mdを確認
```bash
cat .session/SESSION_LOG.md
# または最新10エントリのみ
tail -n 50 .session/SESSION_LOG.md
```

完全な会話履歴を確認できます。

#### スナップショットを確認
```bash
# 最新のスナップショット
cat .session/snapshots/latest.md

# すべてのスナップショット
ls -lt .session/snapshots/
```

## ⚙️ システム管理

### Git自動コミット

#### 状態確認
```bash
launchctl list | grep com.session.autocommit
```

#### 開始
```bash
launchctl load ~/Library/LaunchAgents/com.session.autocommit.plist
```

#### 停止
```bash
launchctl unload ~/Library/LaunchAgents/com.session.autocommit.plist
```

#### ログ確認
```bash
tail -f .session/auto_commit.log
```

### Serenaメモリ管理

#### サマリー表示
```bash
python3 scripts/serena_memory_integration.py summary
```

#### すべてのメモリキー表示
```bash
python3 scripts/serena_memory_integration.py list
```

#### 特定のメモリを読み取り
```bash
python3 scripts/serena_memory_integration.py read latest_session
```

## 🔧 トラブルシューティング

### ❌ Git自動コミットが動作しない

**確認**:
```bash
launchctl list | grep com.session.autocommit
```

**修正**:
```bash
./scripts/setup_auto_commit.sh
```

### ❌ STATUS.mdが更新されない

**確認**:
```bash
python3 scripts/session_recorder.py prompt "テスト"
cat .session/STATUS.md
```

### ❌ Serenaメモリが空

**確認**:
```bash
cat .session/serena_memory.json
```

**修正**: セッション記録を実行すると自動的に作成されます
```bash
python3 scripts/session_recorder.py prompt "テストプロンプト"
```

### ❌ 復元できない

**対処法**:

1. 最新のGitコミットから復元
```bash
git log --oneline | head -10
git show <commit-hash>:.session/STATUS.md
```

2. スナップショットから復元
```bash
cat .session/snapshots/latest.md
```

3. Serenaメモリから復元
```bash
python3 scripts/session_recovery.py restore-serena
```

## 📊 メンテナンス

### 古いチェックポイントの削除

Serenaメモリから7日以上前のチェックポイントを削除:
```python
from scripts.serena_memory_integration import SerenaMemoryManager
from pathlib import Path

manager = SerenaMemoryManager(Path.cwd())
deleted = manager.cleanup_old_checkpoints(keep_days=7)
print(f"削除したチェックポイント: {deleted}件")
```

### ログファイルのクリーンアップ

```bash
# 古いログをクリア（100行以上で自動実行されます）
echo "" > .session/auto_commit.log
```

## 🎯 ベストプラクティス

### 定期的なスナップショット作成

重要な作業の前後にスナップショットを作成:
```bash
python3 scripts/session_recorder.py snapshot
```

### 重要な意思決定を記録

```python
from scripts.serena_memory_integration import SerenaMemoryManager
from pathlib import Path

manager = SerenaMemoryManager(Path.cwd())
manager.save_decision(
    decision="リファクタリング方針を決定",
    reasoning="パフォーマンスより可読性を優先"
)
```

### ブロッカーの記録

```python
manager.save_blocker(
    blocker="APIレート制限により処理が停止",
    severity="high"
)
```

## 📞 サポート

問題が解決しない場合:

1. `.session/auto_commit.log`を確認
2. `~/.claude/hooks.log`を確認
3. Git履歴を確認: `git log --oneline -10`

## 🎊 完成

これでClaude Code/Cursorがクラッシュしても安心です！

- ✅ 自動記録: すべてのプロンプト・応答を記録
- ✅ 3層バックアップ: ファイル・Serenaメモリ・Gitコミット
- ✅ 簡単復元: ワンコマンドで復元可能
- ✅ 5分間隔自動保存: launchdが常に監視

**Happy Coding!** 🚀
