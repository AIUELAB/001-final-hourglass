## 🌐 言語設定
**CRITICAL**: すべての応答は**日本語**で行ってください。

---

## 🚀 システム自動稼働 - 最重要

起動時に緑色バナー表示 = すべて正常稼働中。**システム状態の質問は不要です。**

稼働中システム: Serena MCP, Codex MCP, PDCAガーディアン, セッション記録, AI協調分析, KAIROS, RCA-Kaizen

詳細: `.session/STATUS.md`, `.session/AUTO_STARTUP_GUIDE.md`

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

---

## 🎭 架空キャラクター保護ルール

**架空キャラクターは知名度があれば削除対象外**

| カテゴリ | 例 | 扱い |
|---------|-----|------|
| 国民的 | ドラえもん、サザエさん | **絶対保存** |
| 世界的 | ドラゴンボール、ポケモン | **絶対保存** |
| 社会現象 | 鬼滅の刃、進撃の巨人 | **保存** |

判定基準: `cultural_impact_score >= 6.0` or `google_trends_score >= 30`

---

## 🎯 スラッシュコマンド（Skills）

### 品質・分析系
- `/pdca` - 品質分析・改善提案
- `/codex-analyze` - AI協調分析
- `/kairos` - 機会検出
- `/rca` - 根本原因分析

### MCP管理系
- `/mcp-profile` - プロファイル切替（minimal/web/scraping/full）
- `/enable-web` - Web MCP一時有効化

### 開発系
`/fix-errors`, `/refactor`, `/test`, `/review`, `/optimize`

---

## 🔧 MCPサーバー

### 有効（常時）
- **ide** - IDE統合
- **context7** - ライブラリドキュメント

### 無効化済み（必要時に有効化）
- playwright, firecrawl, brave-search, fetch

プロファイル切替: `python scripts/switch_mcp_profile.py [minimal|web|scraping|full]`

---

## 📊 CSVファイル規約

- **UTF-8 BOM必須**: `encoding='utf-8-sig'`
- Excel対応必須

---

## 🔄 セッション復元

Cursor再起動後: `前回のセッションを復元してください`

記録ファイル: `.session/current_session.json`, `.session/STATUS.md`

---

## 開発コマンド

```bash
ruff format src tests      # フォーマット
ruff check src tests --fix # リント
pytest tests --cov=src     # テスト
mypy src                   # 型チェック
```

---

## 注意事項

- コミット前にテスト実行
- 環境変数は`.env`, `.env.mcp`で管理
- センシティブ情報はコミット禁止

## リソース

- 詳細セットアップ: `docs/SETUP.md`
- MCP詳細: `docs/MCP_SERVERS.md`
- [MCP Documentation](https://modelcontextprotocol.io/)
