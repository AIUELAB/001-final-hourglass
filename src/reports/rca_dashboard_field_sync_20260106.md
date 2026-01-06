# RCA-Kaizen分析レポート: ダッシュボードv10 フィールド同期問題

**日付**: 2026-01-06
**分析者**: Claude Code
**ステータス**: 完了・対策実装済み

---

## 問題概要

ダッシュボードv10で以下の2つの問題が発生:

1. **作成日が全て「記録無し」と表示**
2. **エピソードタイプが英語のまま表示**

---

## 5 Whys分析

### 問題1: generation_timestamp 表示不具合

| Why | 質問 | 回答 |
|-----|------|------|
| 1 | なぜ作成日が表示されなかった？ | CSVパース時にgeneration_timestampが読み込まれていなかった |
| 2 | なぜ読み込まれていなかった？ | CSVパースのreturnオブジェクトに含まれていなかった |
| 3 | なぜ含まれていなかった？ | 新機能追加時に表示部分のみ修正しCSVパースを修正し忘れた |
| 4 | なぜ修正し忘れた？ | 2つのデータソース（埋め込みJSON/CSVパース）の存在を認識していなかった |
| 5 | **なぜ認識していなかった？** | **データフロー図・チェックリストが存在しなかった** |

### 問題2: episode_type 翻訳不具合

| Why | 質問 | 回答 |
|-----|------|------|
| 1 | なぜ英語のまま表示された？ | テンプレートで`${ep.episode_type}`を直接表示していた |
| 2 | なぜ翻訳関数を使わなかった？ | getTypeLabel()（翻訳用）が存在しなかった |
| 3 | なぜ関数がなかった？ | 初期実装時に日本語表示を想定していなかった |
| 4 | なぜ想定していなかった？ | 表示フィールド追加時の標準チェックリストがなかった |
| 5 | **なぜチェックリストがなかった？** | **UI表示の設計ガイドラインが文書化されていなかった** |

---

## 根本原因

両問題に共通する根本原因:

1. **データフローの不透明性**
   - 埋め込みJSON と CSVパース の2系統が存在
   - どちらが使われるか条件が不明確

2. **チェックリストの不在**
   - 新フィールド追加時の標準手順がない
   - 修正すべき箇所が明示されていない

3. **翻訳ガイドラインの不在**
   - どのフィールドが翻訳必要か不明
   - 翻訳マッピングが分散

---

## 実施した対策

### 短期対策（即時実施）

| # | 対策 | 成果物 |
|---|------|--------|
| 1 | generation_timestamp をCSVパースに追加 | `episode_database_dashboard_v10.html` 修正 |
| 2 | getTypeLabel() 翻訳関数追加 | `episode_database_dashboard_v10.html` 修正 |
| 3 | episode_type を update_dashboard_v10.py に追加 | `update_dashboard_v10.py` 修正 |

### 中期対策（再発防止）

| # | 対策 | 成果物 |
|---|------|--------|
| 4 | データフロー図の作成 | `docs/DASHBOARD_DATA_FLOW.md` |
| 5 | フィールド追加チェックリストの作成 | `docs/DASHBOARD_DATA_FLOW.md` 内 |
| 6 | 自動検証スクリプトの作成 | `scripts/validation/verify_dashboard_fields.py` |
| 7 | 回帰テストの追加 | `tests/test_dashboard_field_sync.py` |

---

## 検証結果

```
============================================================
🔍 ダッシュボードv10 フィールド整合性検証
============================================================
🔎 必須フィールドの存在確認...
   ✅ episode_id
   ✅ person_id
   ✅ generation_timestamp
   ✅ episode_type
   ... (全31フィールド合格)

🌐 翻訳関数の確認...
   ✅ episode_type → getTypeLabel()
```

**テスト結果**: 68/68 合格

---

## 今後の運用

### フィールド追加時の手順

```bash
# Step 1: チェックリスト確認
cat docs/DASHBOARD_DATA_FLOW.md

# Step 2: 3箇所を同時に修正
# - scripts/update_dashboard_v10.py
# - preserved/episode_database_dashboard_v10.html (CSVパース)
# - preserved/episode_database_dashboard_v10.html (テンプレート)

# Step 3: 検証
python scripts/validation/verify_dashboard_fields.py

# Step 4: テスト
python -m pytest tests/test_dashboard_field_sync.py -v

# Step 5: ダッシュボード更新
python scripts/update_dashboard_v10.py
```

---

## 効果予測

| 指標 | Before | After |
|------|--------|-------|
| フィールド追加時のバグ発生率 | 高 | 低（チェックリストで防止） |
| 検出までの時間 | ユーザー報告待ち | CI/CDで即時検出 |
| 修正コスト | 高（調査時間含む） | 低（チェックリストで特定容易） |

---

## 関連ドキュメント

- [データフロー図・チェックリスト](../../docs/DASHBOARD_DATA_FLOW.md)
- [検証スクリプト](../../scripts/validation/verify_dashboard_fields.py)
- [回帰テスト](../../tests/test_dashboard_field_sync.py)
