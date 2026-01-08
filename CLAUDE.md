# CLAUDE.md - Claude Code 運用ガイド

## 🌐 言語設定
**すべての応答は日本語で行ってください。**

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

---

## 🔀 Git標準フロー

```bash
git pull origin main
git add . && git commit -m "type: 説明"
git push origin main
```

コミット形式: `fix:` `feat:` `docs:` `chore:`

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
