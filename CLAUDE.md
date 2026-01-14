# CLAUDE.md - Claude Code 運用ガイド

## 🌐 言語設定
**すべての応答は日本語で行ってください。**

---

## 🎯 運用モード

**あなたはマネージャーでagentオーケストレーターです**

- あなたは絶対に実装せず、全てsubagentやtask agentに委託すること
- タスクは超細分化し、PDCAサイクルを構築すること

---

## 🚀 システム状態
起動時に緑色バナー = 正常稼働。状態確認不要。
詳細: `.session/STATUS.md`

---

## 🛡️ 運用ガードレール

- **出力上限**: コマンド出力は20行以下。超過時は `src/reports/logs/` に保存
- **ログ化**: 長時間コマンドは `tee` で保存
- **機密情報**: APIキー/トークンは表示禁止
- **Timeout時**: `src/reports/run_status.md` に引き継ぎ記載

---

## 🔴 品質原則

**禁止**: ダミーデータ継続、プレースホルダー本番使用、検証なし出力
**必須**: Fail-Fast、品質ゲート（API応答>95%）、トランザクション整合性

---

## 🎭 EPUP（エピソード生成）ルール

| ルール | 概要 | 詳細/ツール |
|--------|------|-------------|
| 架空キャラ保護 | 知名度ある架空キャラは保存 | `cultural_impact_score >= 6.0` |
| 年齢境界 | birth〜death年の範囲内のみ | `detect_age_boundary_violations.py` |
| 禁止表現 | メタ的表現禁止 | `fix_fictional_meta_episodes.py` |
| 人物名正規化 | 正規表記使用 | `normalize_person_names.py` |
| グループ所属 | 不整合自動検出 | `sync_group_from_master.py` |
| **同一年齢重複禁止** | 同一人物・同一年齢で類似内容禁止 | `same_age_duplicate_gate.py` |
| 回顧・抽象ペナルティ | 具体的事象がないEPはスコア抑制 | `episode_fame_v6/scorer.py` |
| **重要度スコア整合性** | 具体的偉業 > 物語的転機でimportance評価 | `validate_importance_score.py` |
| **象徴的業績カバレッジ** | 重要人物は必須業績エピソードを持つこと | `audit_iconic_achievements.py` |
| **架空キャラ時代整合性** | 歴史設定作品に現代年号禁止 | `fictional_episode_validator.py` |
| **架空キャラ名形式** | フルネーム「{姓}{名}」形式必須 | `fictional_episode_validator.py` |
| **作品内事実検証** | キャラ-アーク整合性チェック | `fictional_episode_validator.py` |

### 同一年齢重複禁止詳細（EPUP原則: 1人1年齢1エピソード）
- **原則**: 同一人物（person_id）× 同一年齢（age）で複数エピソードを生成しない
- **生成時防止**: SAGE orchestrator step 2.5 で事前チェック（API呼び出し前）
- **書き込み時防止**: SafeCSVWriter._check_duplicate() でEPUP違反を検出
- **検証ゲート**: `python scripts/validation/same_age_duplicate_gate.py`
- **解決ツール**: `python scripts/validation/same_age_duplicate_resolver.py`
- **重複発見時**: composite_score最高のエピソードを残し、他を削除

### 象徴的業績カバレッジ詳細
- **マスターデータ**: `preserved/data/iconic_achievements_master.json`
- **監査コマンド**: `python scripts/validation/audit_iconic_achievements.py`
- **欠落検出時**: 該当エピソードを手動追加
- **新規人物追加時**: マスターデータに必須業績を定義

### 架空キャラクター品質ルール詳細【RCA-20260115】
**原因**: EP-260112002753253523（栗花落カナヲ）で発見された3つの品質問題
1. 時代設定違反: 大正時代設定の鬼滅の刃に「2019年」を使用
2. 名前形式違反: 「カナヲ（栗花落）」→「栗花落カナヲ」が正しい
3. 作品事実虚偽: カナヲは無限列車編に登場しない

**架空キャラ時代整合性チェック**:
- **対象作品**: 歴史設定作品（鬼滅の刃=大正、るろうに剣心=明治、進撃の巨人=独自年号など）
- **禁止**: 現代西暦年号（1900年〜2026年）の使用
- **検証**: `python scripts/validation/fictional_episode_validator.py`
- **修正**: `python scripts/fix/fix_fictional_era_violations.py --execute`

**名前形式ルール**:
- **正しい形式**: 「栗花落カナヲ」（フルネーム）
- **禁止形式**: 「カナヲ（栗花落）」「カナヲ」（名のみ）

**作品設定マッピング** (`scripts/validation/fictional_episode_validator.py`):
| 作品 | 時代設定 | 禁止年号 |
|------|----------|----------|
| 鬼滅の刃 | 大正時代 | 1900年〜2026年 |
| るろうに剣心 | 明治時代 | 1900年〜2026年 |
| 進撃の巨人 | 独自年号 | 1900年〜2026年 |
| ONE PIECE | 架空世界 | 1900年〜2026年 |
| NARUTO | 架空世界 | 1900年〜2026年 |

### ダッシュボード表示完全性（EPUP原則: 全フィールド埋充）【RCA-20260110】
- **原則**: ダッシュボードに表示するエピソードは全必須フィールドが埋まっていること
- **必須フィールド**: 8軸スコア全項目 + episode_fame_v6 + episode_fame_tier_v6 + 基本情報
- **検証ゲート**: `python scripts/validation/dashboard_completeness_gate.py`
- **書き込み時防止**: SafeCSVWriter で完全性チェック（厳格モード）
- **修復ツール**: `python scripts/fix/fill_missing_dashboard_fields.py`
- **根本原因**: process_batch_results.py でiconic_score/fame_score_v3が未設定だった

### エピソードタブ初期ソート（EPUP原則: 超総合スコア降順）【RCA-20260110】
- **原則**: エピソードタブは常に`super_total_score`降順でソートされて表示される
- **対象箇所**: ダッシュボードHTML内の以下3箇所で`applyCurrentSort()`を呼び出し
  - 初期表示時（`filteredEpisodes = [...allEpisodes]`の後）
  - `applyFilters()`実行後
  - `clearFilters()`実行後
- **根本原因1**: `currentSort`変数は設定されていたが、初期化/フィルター後にソートが適用されていなかった
- **根本原因2**: CSV読み込み後の値が文字列のため、辞書順ソートになっていた（"620457" > "1032666"）
- **根本原因3**: DOMContentLoadedハンドラで`handleSort('episode_id')`が呼ばれ、初期ソートを上書きしていた
- **必須対策**: 数値フィールドは必ず`parseFloat()`/`parseInt()`で変換してからソート
- **禁止事項**: DOMContentLoaded内で`handleSort()`を呼ばない（`initEpisodeList()`が既にソート適用済み）
- **ヘルパー関数**: `applyCurrentSort()` - 現在のソート状態をfilteredEpisodesに適用

---

## 🔄 MCP運用

### 操作委譲（コンテキスト節約）
| コマンド | 用途 | 節約 |
|---------|------|------|
| `/gh` | GitHub操作 | ~15k tokens |
| `/serena` | Serena操作 | ~20k tokens |

### プロファイル切替
```bash
python scripts/switch_mcp_profile.py [minimal|web|full]
```

---

## 📁 データ運用

| 対象 | 正規パス | 禁止 |
|------|----------|------|
| マスターCSV | `preserved/data/MASTER_EPISODES_CURRENT.csv` | 他場所での複製 |
| ダッシュボード | `preserved/episode_database_dashboard_v*.html` | ルート直下作成 |

### ダッシュボード更新ルール【RCA-20260110】
**🚨 重要**: ダッシュボード更新には必ず `scripts/update_dashboard_v10.py` を使用すること
- ✅ **使用する**: `python scripts/update_dashboard_v10.py`
- ❌ **使用禁止**: `update_dashboard_v11.py`（アーカイブ済み、ダークテーマ版を生成してしまう）
- **正しいレイアウト**: 白壁・青フレーム「エピソードメインデータベース v11」
- **間違ったレイアウト**: ダークテーマ「Phase 27: 軽量化版」

---

## 🔀 Git標準フロー

```bash
git pull origin main
git add . && git commit -m "type: 説明"
git push origin main
```

コミット形式: `fix:` `feat:` `docs:` `chore:`

---

## 📊 Batch API進捗表示ルール

**必須**: Batch API処理中は常に進捗バーで状況を視覚化する

### 進捗バーフォーマット
```
╔════════════════════════════════════════════════════════════════╗
║           Batch API リアルタイム進捗                           ║
╚════════════════════════════════════════════════════════════════╝

  📦 Batch ID: msgbatch_XXXXX...

  ┌────────────────────────────────────────────────────────┐
  │  ████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
  └────────────────────────────────────────────────────────┘

  ⏳ ステータス: 処理中 (in_progress) / ✅ 完了 (ended)

  ┌─────────────────┬─────────────────┬─────────────────┐
  │    📊 総数      │   ✅ 成功       │   ❌ 失敗       │
  ├─────────────────┼─────────────────┼─────────────────┤
  │      500 件     │      XXX 件     │        X 件     │
  └─────────────────┴─────────────────┴─────────────────┘
```

### 表示タイミング
- `turbo_cli status` 実行時
- `turbo_cli retrieve` 実行前
- バッチ完了確認時

---

## 🛠️ 開発コマンド

```bash
ruff format src tests && ruff check src tests --fix
pytest tests --cov=src
mypy src
```

---

## 📚 詳細ドキュメント

- セットアップ: `docs/SETUP.md`
- Git/MCP: `docs/GIT_MCP_WORKFLOW.md`
- 人物名: `docs/PERSON_NAME_VALIDATION_WORKFLOW.md`
- ダッシュボード: `docs/EPISODE_DB_STARTUP_GUIDE.md`
- MCP: `docs/MCP_SERVERS.md`
