# 曖昧な名前問題の解決提案書

## 現状の問題

### 1. 村上問題の詳細
- **P003625**: 村上（所属グループ不明）
- **P003626**: 村上（所属グループ不明）

2つの「村上」エントリが存在し、以下の可能性があります：
- マヂカルラブリーの村上
- Aマッソのむらきゃみ（旧：村上）※2024年2月改名
- その他の村上

### 2. データ不足による特定困難
現在のデータ構造では、以下の情報が不足しているため特定が困難：
- 生年月日の欠落
- 相方情報の欠落
- 所属事務所情報の欠落
- 活動期間情報の欠落

## 即座に実施可能な解決策

### 1. 手動調査による特定（短期的解決）

```python
# 調査手法
1. P003625とP003626の周辺データを確認
2. 登録時期（conversion_date）から推定
3. original_batch_idから文脈を推定
4. recognition_scoreから知名度を推定
```

### 2. コンテキスト分析による推定

```python
# 推定ロジック
if recognition_score >= 70:
    # 高知名度 → マヂカルラブリーの可能性大（M-1優勝）
    likely_group = "マヂカルラブリー"
elif metadata.contains("ワタナベ"):
    # ワタナベエンターテインメント → Aマッソ
    likely_group = "Aマッソ"
```

## 中長期的な解決策

### 1. データ構造の改善

#### 新規フィールドの追加
```csv
person_id,person_name,person_name_display,group_id,partner_ids,agency,wikipedia_url,birth_date
P003625,村上,村上（マヂカルラブリー）,G_MAGICAL,P_NODA,吉本興業,https://ja.wikipedia.org/wiki/村上_(マヂカルラブリー),1980-XX-XX
```

#### 必須フィールド
1. **group_id**: グループの一意識別子
2. **partner_ids**: 相方のperson_id（複数可）
3. **agency**: 所属事務所
4. **wikipedia_url**: 一意の識別に使用
5. **birth_date**: 同名人物の区別

### 2. 命名規則の標準化

#### グループメンバーの表記ルール
```
# 基本形式
{芸名}（{グループ名}）

# 改名した場合
{現在の芸名}（{グループ名}）
例: むらきゃみ（Aマッソ）

# 同名が存在する場合
{芸名}（{グループ名}）＋追加識別子
例: 村上（マヂカルラブリー・M-1優勝）
```

### 3. PDCAガーディアンルールの追加

```python
def check_ambiguous_names(self, csv_file: str) -> List[RuleViolation]:
    """
    Rule 101: 曖昧な名前検出ルール

    同名の芸人が複数存在する場合の検証
    """
    violations = []

    # 既知の曖昧な名前リスト
    ambiguous_names = ['村上', '田中', '山田', '佐藤', '鈴木']

    df = pd.read_csv(csv_file)
    for idx, row in df.iterrows():
        if row['person_name'] in ambiguous_names:
            if '（' not in str(row['person_name_display']):
                violations.append(
                    RuleViolation(
                        rule_id="RULE_101",
                        severity="HIGH",
                        description=f"曖昧な名前にグループ名なし: {row['person_name']}",
                        suggested_fix="グループ名を追加してください"
                    )
                )

    return violations
```

## 実装計画

### Phase 1: 即座対応（1日）
1. ✅ 曖昧な名前解決システムの作成
2. ⬜ P003625, P003626の手動調査と特定
3. ⬜ 特定結果に基づく修正スクリプト実行

### Phase 2: 短期改善（1週間）
1. ⬜ group_idフィールドの追加
2. ⬜ partner_idsフィールドの追加
3. ⬜ 既存データへの後方適用

### Phase 3: 中期改善（1ヶ月）
1. ⬜ Wikipedia連携による自動識別
2. ⬜ 所属事務所データベースの構築
3. ⬜ 改名履歴管理システムの実装

### Phase 4: 長期改善（3ヶ月）
1. ⬜ AI/MLによる文脈理解と自動分類
2. ⬜ 外部APIとの連携（芸能事務所DB等）
3. ⬜ リアルタイム重複検出システム

## 品質保証メトリクス

### 目標値
- 曖昧な名前の解決率: 95%以上
- 誤分類率: 1%未満
- 手動介入必要率: 5%未満

### 測定方法
```python
# 品質チェック
def measure_ambiguity_resolution():
    total_ambiguous = count_ambiguous_names()
    resolved = count_resolved_names()
    resolution_rate = resolved / total_ambiguous * 100

    return {
        'resolution_rate': resolution_rate,
        'unresolved_count': total_ambiguous - resolved,
        'manual_intervention_needed': count_manual_cases()
    }
```

## リスクと対策

### リスク
1. **誤った特定**: 同名異人を間違えて分類
2. **データ損失**: 修正時の誤削除
3. **互換性問題**: 新フィールド追加による既存システムへの影響

### 対策
1. **多重確認**: 複数の情報源での照合
2. **バックアップ**: すべての修正前にバックアップ作成
3. **段階的移行**: 新旧フィールドの並行運用期間設定

## 結論

現在の「村上」問題は、データ構造の限界による根本的な課題です。短期的には手動調査と修正で対応しつつ、中長期的にはデータ構造の改善とシステム的な解決が必要です。

特に重要なのは：
1. **一意識別子の導入**（group_id, partner_ids）
2. **命名規則の標準化**
3. **自動検証システムの構築**

これらの実装により、今後同様の問題の発生を防止できます。
