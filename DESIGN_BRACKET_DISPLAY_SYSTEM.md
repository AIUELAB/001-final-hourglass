# グループ名・作品名括弧表示システム設計書

**作成日**: 2025-10-02
**バージョン**: v1.0

---

## 📋 要件定義

### 1. 基本要件

**目的**: エピソードテキストで人物名の横に所属グループ名または作品名を括弧表示

**例**:
```
あなたと同じ30歳のとき、髙比良くるま(令和ロマン)は...
あなたと同じ19歳のとき、モンキー・D・ルフィ(ONE PIECE)は...
```

### 2. 表示ルール

#### 2.1 括弧を付ける条件

| カテゴリ | 条件 | 例 |
|---------|------|-----|
| **架空キャラクター** | 常に作品名を表示 | モンキー・D・ルフィ(ONE PIECE) |
| **漫才コンビ/グループ** | 活動中 & グループが有名 | 又吉直樹(ピース)、松本人志(ダウンタウン) |
| **バンドメンバー** | 活動中 & バンドが有名 | - |
| **YouTuberグループ** | 活動中 & グループが有名 | - |

#### 2.2 括弧を付けない条件（実在人物）

- ✅ グループ解散済み（例: X JAPAN、SMAP）
- ✅ グループ活動休止中
- ✅ 本人の知名度 > グループの知名度（例: HIKAKIN、YOSHIKI）
- ✅ ソロ活動がメイン

#### 2.3 重複排除ルール

**重要**: 括弧内のワード（グループ名・作品名）はエピソード本文に使用しない

**Before**:
```
あなたと同じ23歳のとき、YOSHIKI(X JAPAN)はX JAPANとして「BLUE BLOOD」でメジャーデビューを果たした。
```

**After**:
```
あなたと同じ23歳のとき、YOSHIKI(X JAPAN)は「BLUE BLOOD」でメジャーデビューを果たした。
```

---

## 🗄️ データベース設計

### 新規カラムの追加

```sql
ALTER TABLE persons ADD COLUMN entity_type TEXT DEFAULT 'real_person';
ALTER TABLE persons ADD COLUMN group_affiliation TEXT;
ALTER TABLE persons ADD COLUMN primary_work TEXT;
ALTER TABLE persons ADD COLUMN show_group_in_bracket BOOLEAN DEFAULT 0;
ALTER TABLE persons ADD COLUMN group_status TEXT;
ALTER TABLE persons ADD COLUMN fame_level TEXT;
ALTER TABLE persons ADD COLUMN bracket_display_text TEXT;
```

### カラム定義

| カラム名 | 型 | 説明 | 例 |
|---------|---|------|-----|
| `entity_type` | TEXT | 人物の種類 | "real_person", "fictional_character" |
| `group_affiliation` | TEXT | 所属グループ名（複数の場合カンマ区切り） | "ダウンタウン", "X JAPAN" |
| `primary_work` | TEXT | 架空キャラクターの作品名 | "ONE PIECE", "鬼滅の刃" |
| `show_group_in_bracket` | BOOLEAN | 括弧表示フラグ | 1 (表示), 0 (非表示) |
| `group_status` | TEXT | グループ活動状態 | "active", "disbanded", "hiatus" |
| `fame_level` | TEXT | 知名度比較 | "personal_more_famous", "group_more_famous", "equal" |
| `bracket_display_text` | TEXT | 実際に表示する括弧内テキスト | "ダウンタウン", "ONE PIECE" |

---

## 🔧 ルールエンジン設計

### クラス構造

```python
class BracketDisplayEngine:
    """括弧表示判定エンジン"""

    def __init__(self):
        self.rules = self._load_rules()

    def should_show_bracket(self, person_data: Dict) -> Tuple[bool, Optional[str]]:
        """
        括弧表示判定

        Args:
            person_data: 人物データ

        Returns:
            (表示フラグ, 括弧内テキスト)
        """
        pass

    def apply_display_format(self, person_name: str, bracket_text: Optional[str]) -> str:
        """
        表示形式の適用

        Args:
            person_name: 人物名
            bracket_text: 括弧内テキスト

        Returns:
            フォーマット済み文字列（例: "松本人志(ダウンタウン)"）
        """
        pass

    def remove_bracket_word_from_text(self, text: str, bracket_word: str) -> str:
        """
        エピソード本文から括弧内ワードを除去

        Args:
            text: エピソードテキスト
            bracket_word: 括弧内ワード

        Returns:
            除去後のテキスト
        """
        pass
```

### 判定ロジック（フローチャート）

```
START
  ↓
entity_type == "fictional_character"?
  ├─ YES → 常に表示 (primary_work)
  └─ NO → 実在人物の判定へ
       ↓
  group_affiliation が存在?
    ├─ NO → 表示しない
    └─ YES → 次へ
         ↓
  group_status == "active"?
    ├─ NO → 表示しない
    └─ YES → 次へ
         ↓
  fame_level in ["group_more_famous", "equal"]?
    ├─ NO → 表示しない
    └─ YES → 次へ
         ↓
  category に応じた最終判定
    ├─ お笑い芸人 → 表示
    ├─ ミュージシャン → 表示
    ├─ YouTuber → 表示
    └─ その他 → ケースバイケース
```

---

## 📊 データ収集戦略

### 優先順位付きデータ収集

#### Priority 1: 架空キャラクター（100%確実）

**データソース**:
- Wikipedia API（日本語版）
- MCP Context7（アニメ・漫画データベース）

**収集項目**:
- `entity_type` = "fictional_character"
- `primary_work` = 作品名
- `show_group_in_bracket` = 1

**例**:
```python
{
    "person_name": "モンキー・D・ルフィ",
    "entity_type": "fictional_character",
    "primary_work": "ONE PIECE",
    "show_group_in_bracket": 1,
    "bracket_display_text": "ONE PIECE"
}
```

#### Priority 2: お笑い芸人（漫才コンビ・トリオ）

**データソース**:
- Wikipedia API（日本語版）
- MCP Brave Search（"◯◯ 所属グループ 漫才"）

**収集項目**:
- `group_affiliation` = コンビ名/グループ名
- `group_status` = 活動状態の調査
- `fame_level` = 知名度比較

**判定基準**:
```python
# 現役コンビで活動中
if group_status == "active":
    # 最近のテレビ出演頻度を比較
    # コンビ名での出演 > 個人名での出演 → "group_more_famous"
    show_group_in_bracket = 1
```

**例**:
```python
{
    "person_name": "又吉直樹",
    "entity_type": "real_person",
    "category": "お笑い芸人",
    "group_affiliation": "ピース",
    "group_status": "active",
    "fame_level": "equal",
    "show_group_in_bracket": 1,
    "bracket_display_text": "ピース"
}
```

#### Priority 3: バンドメンバー

**データソース**:
- MusicBrainz API
- Wikipedia API

**判定基準**:
```python
# 解散済みバンドは表示しない
if group_status == "disbanded":
    show_group_in_bracket = 0

# 本人のソロ活動が有名な場合は表示しない
if fame_level == "personal_more_famous":
    show_group_in_bracket = 0
```

**除外例**:
```python
{
    "person_name": "YOSHIKI",
    "group_affiliation": "X JAPAN",
    "group_status": "disbanded",  # 1997年解散
    "fame_level": "personal_more_famous",  # YOSHIKIブランドが強い
    "show_group_in_bracket": 0
}
```

#### Priority 4: YouTuberグループ

**データソース**:
- YouTube Data API
- Wikipedia API

**判定基準**:
```python
# グループチャンネル登録者数 vs 個人チャンネル登録者数
if personal_subscribers > group_subscribers * 2:
    fame_level = "personal_more_famous"
    show_group_in_bracket = 0
```

**除外例**:
```python
{
    "person_name": "HIKAKIN",
    "group_affiliation": "HIKAKIN & SEIKIN",
    "group_status": "active",
    "fame_level": "personal_more_famous",  # HIKAKIN個人チャンネル圧倒的
    "show_group_in_bracket": 0
}
```

---

## 🔄 エピソード生成フロー

### 改修前（現在）

```
1. 人物データ取得
2. エピソード生成プロンプト作成
3. LLM呼び出し
4. エピソードテキスト生成
5. 品質検証
```

### 改修後

```
1. 人物データ取得
2. 括弧表示判定 ← 新規
   ├─ should_show_bracket() 呼び出し
   └─ bracket_display_text 取得
3. エピソード生成プロンプト作成
   ├─ 人物名を "名前(グループ名)" に変更 ← 新規
   └─ システムプロンプトに「括弧内ワード使用禁止」を追加 ← 新規
4. LLM呼び出し
5. エピソードテキスト生成
6. 品質検証
7. 後処理: 括弧内ワードの除去確認 ← 新規
```

### プロンプト改修例

**Before**:
```
あなたは著名人のエピソード作成の専門家です。
{person_name}の{age}歳時点のエピソードを生成してください。
```

**After**:
```
あなたは著名人のエピソード作成の専門家です。
{formatted_name}の{age}歳時点のエピソードを生成してください。

【重要な制約】
- 名前に括弧が付いている場合、括弧内のワード（グループ名・作品名）をエピソード本文では使用しないでください
- 例: "松本人志(ダウンタウン)" → エピソード内で「ダウンタウン」という単語を使わない
```

---

## 🧪 テスト戦略

### Unit Test

```python
class TestBracketDisplayEngine:
    """括弧表示エンジンのテスト"""

    def test_fictional_character_always_show(self):
        """架空キャラクターは常に表示"""
        data = {
            "person_name": "モンキー・D・ルフィ",
            "entity_type": "fictional_character",
            "primary_work": "ONE PIECE"
        }
        show, text = engine.should_show_bracket(data)
        assert show == True
        assert text == "ONE PIECE"

    def test_disbanded_band_not_show(self):
        """解散バンドは表示しない"""
        data = {
            "person_name": "YOSHIKI",
            "entity_type": "real_person",
            "group_affiliation": "X JAPAN",
            "group_status": "disbanded"
        }
        show, text = engine.should_show_bracket(data)
        assert show == False

    def test_active_comedian_show(self):
        """現役お笑いコンビは表示"""
        data = {
            "person_name": "又吉直樹",
            "entity_type": "real_person",
            "category": "お笑い芸人",
            "group_affiliation": "ピース",
            "group_status": "active",
            "fame_level": "equal"
        }
        show, text = engine.should_show_bracket(data)
        assert show == True
        assert text == "ピース"

    def test_remove_bracket_word_from_text(self):
        """括弧内ワードの除去"""
        text = "ダウンタウンとして活躍した"
        result = engine.remove_bracket_word_from_text(text, "ダウンタウン")
        assert "ダウンタウン" not in result
```

### Integration Test

```python
def test_full_episode_generation_with_bracket():
    """括弧付きエピソード生成の統合テスト"""

    person_data = {
        "person_name": "松本人志",
        "age": 31,
        "group_affiliation": "ダウンタウン",
        "show_group_in_bracket": 1,
        "bracket_display_text": "ダウンタウン"
    }

    episode = generate_episode(person_data)

    # 検証1: 人物名に括弧が付いている
    assert "松本人志(ダウンタウン)" in episode

    # 検証2: エピソード本文に「ダウンタウン」が含まれていない
    # （人物名部分を除外して検証）
    text_without_name = episode.replace("松本人志(ダウンタウン)", "")
    assert "ダウンタウン" not in text_without_name
```

---

## 📈 実装スケジュール

### Phase 1: データベース拡張（2日）

- [ ] SQLスキーマ修正
- [ ] マイグレーションスクリプト作成
- [ ] データバックアップ

### Phase 2: データ収集（3日）

- [ ] 架空キャラクターの自動判定・収集
- [ ] お笑い芸人のグループ情報収集
- [ ] バンドメンバーの活動状態調査
- [ ] YouTuberグループの登録者数比較

### Phase 3: ルールエンジン実装（2日）

- [ ] BracketDisplayEngine クラス実装
- [ ] 判定ロジックの実装
- [ ] ワード除去ロジックの実装
- [ ] Unit Test作成

### Phase 4: エピソード生成改修（2日）

- [ ] プロンプト修正
- [ ] 生成ロジック改修
- [ ] 後処理追加
- [ ] Integration Test作成

### Phase 5: テストとファクトチェック（2日）

- [ ] 全体テスト実行
- [ ] 100エピソードでの検証
- [ ] PDCA Guardian統合
- [ ] ドキュメント整備

**合計**: 11日間

---

## 🎯 成功基準

### 定量基準

| メトリクス | 目標値 |
|----------|--------|
| 架空キャラクター正解率 | 100% |
| お笑い芸人グループ正解率 | 95%以上 |
| バンドメンバー正解率 | 90%以上 |
| ワード重複率（括弧内ワードがエピソード本文に出現） | 0% |

### 定性基準

- ✅ ユーザーが直感的に理解できる表記
- ✅ グループ名表示が自然（違和感なし）
- ✅ ファクトチェックで問題なし

---

## 🔄 運用とメンテナンス

### 定期更新タスク

- **月次**: グループ活動状態の更新（解散・活動休止の確認）
- **四半期**: 知名度比較の再評価
- **年次**: 新規グループ・作品の追加

### モニタリング

- 括弧表示エピソードの生成数
- ワード重複検出数（アラート対象）
- ユーザーフィードバック

---

**作成者**: Claude Code
**バージョン**: v1.0
**最終更新**: 2025-10-02
