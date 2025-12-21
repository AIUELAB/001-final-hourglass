# AI 振る舞い・運用ルール

## 🚀 システム自動稼働 - 最重要

起動時に緑色バナー表示 = すべて正常稼働中。**システム状態の質問は不要です。**

稼働中システム: Serena MCP, Codex MCP, PDCAガーディアン, セッション記録, AI協調分析, KAIROS, RCA-Kaizen

詳細: `.session/STATUS.md`, `.session/AUTO_STARTUP_GUIDE.md`

---

## 🛡️ Claude Code 運用ガードレール（バッチ/長時間タスク）

**目的**: 会話ログ肥大化（`/compact`不能）や `Error: Request timed out` を予防し、長時間ジョブを安全に完走する。

- **出力上限**: 会話に貼るコマンド出力は最大20行（目安2,000文字）。超える場合はログファイルへ保存し、会話には「要点3行 + ログパス」のみ残す。
- **ログ化（必須）**: 長時間/大量出力コマンドは必ず `tee` で `src/reports/logs/` に保存する。
  - 例: `mkdir -p src/reports/logs && <COMMAND> 2>&1 | tee src/reports/logs/<task>_$(date +%Y%m%d_%H%M%S).log`
- **進捗監視**: `tail`/`grep` を会話でループ連打しない（監視コマンドを提示するだけにし、貼り付けは最小限にする）。
- **途中耐性（推奨）**: バッチLLM評価は `scripts/batch_llm_evaluate_runner.py` を使い、5分ごとのチェックポイント保存（`--checkpoint-seconds 300`）で途中落ちに備える。
- **Context low / Timeout**: `Context low` や `Error: Request timed out` が出たら追加出力を止め、`src/reports/run_status.md` に「引き継ぎ（目的/コマンド/ログ/生成物/次手順）」を書いて終了する（`/compact` 連打は禁止）。
- **機密情報**: APIキー/トークン/個人情報は会話にもログにも出さない（`echo`/`cat` 等で表示しない）。
- **MCPプロファイル**: 通常は `minimal` 推奨。Web検索等が必要なときだけ `web/scraping/full` に切替（切替後はClaude Code/Cursor再起動が必要）。`/mcp-profile` を参照。

---

## 🔴 品質優先原則（Quality-First）

### 絶対禁止
- ダミーデータでの処理継続
- プレースホルダーコードの本番使用
- 品質検証なしの出力

### 必須事項
- **Fail-Fast原則**: エラーは早期に顕在化
- **品質ゲート**: API応答率>95%, 削除率10-20%, ダミーデータ=0
- **トランザクション**: 全成功 or 全ロールバック
