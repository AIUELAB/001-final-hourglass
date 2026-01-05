# RCA: ダッシュボードpersonMap集計フィールド欠落問題

## 発生日時
2026-01-05

## 問題概要
超総合スコア（super_total_score）を追加したが、ダッシュボードのランキングで低知名度人物（SHELLY）がTop 3に表示された。

## 根本原因
`preserved/episode_database_dashboard_v10.html`の`updateRankingTable()`関数内で、人物ごとに集計する`personMap`に新しいスコアフィールド`super_total_score`を追加し忘れた。

```javascript
// 問題のあったコード（super_total_scoreが欠落）
personMap.set(name, {
    person_name: name,
    fame_score: ep.fame_score || 0,
    celebrity_score_v2: ep.celebrity_score_v2 || 0,
    // super_total_score がない！
});
```

結果として`getDisplayScore(p)`が`p.super_total_score`を参照した際に`undefined`（= 0）が返り、ソートが正しく機能しなかった。

## 修正内容
1. `personMap`に`super_total_score`フィールドを追加
2. 同一人物の複数エピソードがある場合、最大値を採用するロジックを追加

```javascript
personMap.set(name, {
    // ...
    super_total_score: ep.super_total_score || 0,  // 追加
});

// 同一人物の場合、最大値を採用
if ((ep.super_total_score || 0) > existing.super_total_score) {
    existing.super_total_score = ep.super_total_score || 0;
}
```

## 再発防止策

### 1. 検証スクリプト追加
`scripts/validation/dashboard_ranking_integrity.py`
- personMapにすべての必須フィールドが含まれているかチェック
- CSVとダッシュボードのTop N人物が一致するかチェック
- 低知名度人物がTop Nに入っていないかチェック

### 2. 開発ルール
新しいスコアフィールドをダッシュボードに追加する際のチェックリスト：
1. [ ] `update_dashboard_v10.py`の`load_csv_data()`にフィールド追加
2. [ ] HTMLの`personMap.set()`にフィールド追加
3. [ ] HTMLの同一人物更新ロジックにフィールド追加
4. [ ] `getDisplayScore()`にフィールド追加
5. [ ] スコアモードUI（modeInfo）にフィールド追加
6. [ ] スコア表示フォーマット対応
7. [ ] `dashboard_ranking_integrity.py`で検証実行

## 影響範囲
- 修正前: SHELLYがTop 3に誤表示
- 修正後: 大江健三郎がTop 1、大谷翔平がTop 10入り

## 関連ファイル
- `preserved/episode_database_dashboard_v10.html`
- `scripts/update_dashboard_v10.py`
- `scripts/validation/dashboard_ranking_integrity.py`（新規）
