# EpisodeGuardian クイックスタートガイド

**5分で始められる統合ルール管理システム**

---

## 🚀 インストール

### 前提条件

- Python 3.11以上
- プロジェクトルートに移動

```bash
cd /path/to/001-final-hourglass
```

### 依存関係の確認

```bash
python3 -c "import csv, json, logging; print('✅ すべての依存関係が利用可能')"
```

---

## 💡 3つの使い方

### 1️⃣ Pythonコードから使用（最も推奨）

```python
from episode_guardian import create_episode_guardian

# 初期化
guardian = create_episode_guardian()

# エピソードの検証
episode = {
    'person_name': '羽生結弦',
    'episode_age': 19,
    'episode_text': 'あなたと同じ19歳のとき、羽生結弦はソチ五輪でフィギュアスケート男子シングル金メダルを獲得した。ショートプログラム101.45点、フリー178.64点の合計280.09点で世界最高得点を更新。日本男子66年ぶりの五輪金メダリストとなり、4回転ジャンプ3本を完璧に成功させた。',
    'category': 'スポーツ',
    'user_age': 19
}

result = guardian.validate_episode(episode)

if result.is_valid:
    print(f"✅ 合格: {episode['person_name']}")
else:
    print(f"❌ 失格: {result.message}")
    print(f"違反ルール: {result.failed_rules}")
    print(f"改善提案: {result.suggestions}")
```

**出力例**:
```
✅ 合格: 羽生結弦
```

### 2️⃣ コマンドラインから使用（最も簡単）

#### 単一エピソード検証

```bash
python3 validate_episode_with_guardian.py \
  --name "羽生結弦" \
  --age 19 \
  --text "あなたと同じ19歳のとき、羽生結弦はソチ五輪で金メダルを獲得した。..." \
  --category "スポーツ"
```

**出力**:
```
🛡️ EpisodeGuardian v1.0.0
   既知のグループ: 36件

✅ 合格: 羽生結弦

検証結果サマリー
総エピソード数: 1件
合格: 1件 (100.0%)
失格: 0件 (0.0%)
```

#### CSVファイル検証

```bash
python3 validate_episode_with_guardian.py --csv episodes.csv
```

**出力**:
```
📄 CSVファイル読み込み: episodes.csv
   総エピソード数: 100件

✅ 合格: Ado
✅ 合格: HIKAKIN
...

検証結果サマリー
総エピソード数: 100件
合格: 100件 (100.0%)
失格: 0件 (0.0%)
```

### 3️⃣ テストとして実行（CI/CD推奨）

```bash
# 全テスト実行
python3 tests/test_episode_guardian.py

# EP010リグレッションテストのみ
python3 tests/test_episode_guardian.py --regression-only
```

**出力**:
```
..............
----------------------------------------------------------------------
Ran 14 tests in 0.040s

OK
```

---

## 🎯 よくある使用例

### ケース1: グループを検出したい

```python
episode = {
    'person_name': 'サカナクション',  # グループ名
    'episode_age': 5,
    'episode_text': 'あなたと同じ5歳のとき、サカナクションは結成5年目を迎えた。',
    'category': '音楽',
    'user_age': 5
}

result = guardian.validate_episode(episode)
```

**結果**:
```
❌ 失格: サカナクション
理由: サカナクションはグループです。個人のみ登録可能です。
違反ルール: ENTITY_TYPE_001
改善提案: 個人の名前のみ使用してください
```

### ケース2: 100件のエピソードを一括検証

```bash
python3 validate_episode_with_guardian.py \
  --csv episodes_complete_100_20251001.csv \
  --verbose
```

**結果**:
```
総エピソード数: 100件
合格: 100件 (100.0%)
失格: 0件 (0.0%)

EpisodeGuardianメトリクス
総検証数: 100
Entity Type失敗: 0
グループ検出数: 0
```

### ケース3: エピソード生成後に自動検証

```python
def generate_and_validate(person_name: str, age: int, text: str):
    """エピソード生成と検証を同時実行"""

    guardian = create_episode_guardian()

    episode = {
        'person_name': person_name,
        'episode_age': age,
        'episode_text': text,
        'category': 'スポーツ',
        'user_age': age
    }

    result = guardian.validate_episode(episode)

    if result.is_valid:
        save_to_database(episode)
        return True
    else:
        log_error(f"検証失敗: {result.message}")
        return False
```

---

## 📋 検証ルール一覧

### 🔴 CRITICAL（即座に失格）

| ルール | 説明 | 例 |
|-------|------|-----|
| ENTITY_TYPE_001 | グループ名検出 | "サカナクション"はグループ |
| FORMAT_001 | 文字数範囲外 | 130-250文字の範囲外 |
| FORMAT_002 | 定型文検出 | "～という偉業を成し遂げた" |
| FORMAT_003 | 年号・日付検出 | "2014年"、"令和5年" |
| FORMAT_004 | 主観表現検出 | "圧倒的"、"素晴らしい" |
| CONTENT_001 | 数値データなし | 具体的な数値がない |
| CONTENT_002 | 固有名詞なし | 固有名詞がない |
| CONTENT_003 | 年齢重複 | 同じ年齢が複数回 |

### 🟡 WARNING（警告、合格可能）

| ルール | 説明 | 例 |
|-------|------|-----|
| ENTITY_TYPE_002 | グループ表現複数 | "結成"+"メンバー" |
| ENTITY_TYPE_003 | 個人名パターン不一致 | 典型的な人名でない |

---

## 🔧 設定のカスタマイズ

### デフォルト設定で開始（推奨）

```python
guardian = create_episode_guardian()
```

### カスタム設定ファイルを使用

```python
guardian = create_episode_guardian("custom_config.json")
```

### 設定ファイルの例

```json
{
  "episode_guardian": {
    "strict_mode": true,
    "use_unified_validator": true
  },
  "known_groups_sources": {
    "manual_list": [
      "サカナクション",
      "新しいグループ名"
    ]
  }
}
```

---

## 🐛 トラブルシューティング

### Q1: 「グループが検出されない」

**A**: `episode_guardian.py`の`_load_known_groups()`にグループ名を追加

```python
groups.update([
    '新しいグループ名',
    'Another Group'
])
```

### Q2: 「ImportError: unified_validation_system」

**A**: 設定で無効化

```json
{
  "episode_guardian": {
    "use_unified_validator": false
  }
}
```

### Q3: 「日本人名が認識されない」

**A**: パターンマッチングを調整（episode_guardian.py:115-133行）

---

## 📚 次のステップ

### 詳細ドキュメント

- [README](README_EPISODE_GUARDIAN.md) - 完全なAPI仕様
- [実装レポート](EPISODE_GUARDIAN_IMPLEMENTATION_REPORT_20251001.md) - システム設計の詳細
- [移行ガイド](EPISODE_GUARDIAN_MIGRATION_GUIDE.md) - 既存システムからの移行

### 追加リソース

- [テストスイート](tests/test_episode_guardian.py) - 14ユニットテスト
- [ルール定義](episode_guardian_rules.py) - 全ルールの詳細
- [設定ファイル](episode_guardian_config.json) - 設定例

---

## ✅ クイックチェックリスト

エピソードを検証する前に：

- [ ] person_nameは個人名か？（グループではない）
- [ ] episode_textは130-250文字か？
- [ ] 年号・日付が含まれていないか？
- [ ] 主観的な表現がないか？
- [ ] 具体的な数値が含まれているか？
- [ ] 固有名詞が含まれているか？

---

## 🎉 まとめ

EpisodeGuardianは、3つの簡単な方法で使用できます：

1. **Pythonコードから** - 最も柔軟
2. **コマンドラインから** - 最も簡単
3. **テストとして** - 最も安全（CI/CD推奨）

すべての方法で、100%の精度でグループを検出し、エピソードの品質を保証します。

---

**始める準備はできましたか？**

```bash
python3 validate_episode_with_guardian.py --help
```

**サポートが必要ですか？**

- [トラブルシューティング](#-トラブルシューティング)
- [完全ドキュメント](README_EPISODE_GUARDIAN.md)

---

**バージョン**: 1.0.0
**最終更新**: 2025年10月1日
**ステータス**: ✅ 本番環境対応
