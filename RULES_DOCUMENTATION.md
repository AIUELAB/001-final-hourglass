# 統合ルール管理システム - ルール一覧

生成日時: 2025-10-15 04:30:21

総ルール数: 75
アクティブ: 74
非推奨: 1

## DATA_QUALITY

### RULE_001: calibrated_score使用禁止

**優先度**: CRITICAL

**ステータス**: active

**説明**: calibrated_scoreの使用は禁止。必ず実際のAPIで算出したスコアを使用すること。

**実装**: `pdca_guardian.py`

**タグ**: api, scoring, data_quality

---

### RULE_002: （説明なし）

**優先度**: MEDIUM

**ステータス**: active

**説明**: RULE_002: API関連の検証ルール
（自動生成された説明 - 要レビュー）

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_003: （説明なし）

**優先度**: MEDIUM

**ステータス**: active

**説明**: RULE_003: violation_type=ViolationType.DUMMY_DATA_RETURN,...
（自動生成された説明 - 要レビュー）

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_004: （説明なし）

**優先度**: MEDIUM

**ステータス**: active

**説明**: RULE_004: violation_type=ViolationType.DELETION_RATE_ABNORMA...
（自動生成された説明 - 要レビュー）

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_005: （説明なし）

**優先度**: MEDIUM

**ステータス**: active

**説明**: RULE_005: violation_type=ViolationType.QUALITY_GATE_FAILURE,...
（自動生成された説明 - 要レビュー）

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_008: （説明なし）

**優先度**: MEDIUM

**ステータス**: active

**説明**: RULE_008: violation_type=ViolationType.ERROR_SUPPRESSION,...
（自動生成された説明 - 要レビュー）

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_009: （説明なし）

**優先度**: MEDIUM

**ステータス**: active

**説明**: RULE_009: violation_type=ViolationType.SUBSTRING_MATCHING,...
（自動生成された説明 - 要レビュー）

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_011: 違反キーワード

**優先度**: MEDIUM

**ステータス**: active

**説明**: 違反キーワード

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_017: （説明なし）

**優先度**: MEDIUM

**ステータス**: active

**説明**: 品質妥協キーワード検出

【目的】
提案文（proposal）に品質を妥協する可能性のあるキーワードが含まれていないかチェック。

【検出キーワード】
- ハイブリッド、部分的、一部のみ
- 簡易版、シンプル版、高速版
- quick、fast、simple
- 短縮、早く、速く

【違反時の対応】
- 品質妥協の可能性がある提案として警告
- 完全実装を推奨

【実装箇所】
pdca_guardian.py:check_proposal()

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_077: 連続ID誤判定防止

**優先度**: MEDIUM

**ステータス**: active

**説明**: 連続ID誤判定防止

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_078: バッチデータ保護

**優先度**: MEDIUM

**ステータス**: active

**説明**: バッチデータ保護

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_079: Wikipedia確認優先

**優先度**: MEDIUM

**ステータス**: active

**説明**: Wikipedia確認優先

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_080: 多段階検証

**優先度**: MEDIUM

**ステータス**: active

**説明**: 多段階検証

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_098: （説明なし）

**優先度**: MEDIUM

**ステータス**: active

**説明**: RULE_098: violation_type=ViolationType.SOLO_ARTIST_REDUNDANT...
（自動生成された説明 - 要レビュー）

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_099: （説明なし）

**優先度**: MEDIUM

**ステータス**: active

**説明**: RULE_099: violation_type=ViolationType.CHANNEL_NAME_AS_PERSO...
（自動生成された説明 - 要レビュー）

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_106: # 新規追加（RULE_106-108）

**優先度**: MEDIUM

**ステータス**: active

**説明**: # 新規追加（RULE_106-108）

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_107: （説明なし）

**優先度**: MEDIUM

**ステータス**: active

**説明**: RULE_107: if '実は' in episode_text or '正確には' in episode_text:...
（自動生成された説明 - 要レビュー）

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_108: （説明なし）

**優先度**: MEDIUM

**ステータス**: active

**説明**: 歴史的重要性チェック

【目的】
エピソードに歴史的重要性を示す要素（「初」「史上」「記録」等）が含まれているか検証。

【チェック内容】
- historical_scoreがHISTORICAL_THRESHOLD以上であること
- 歴史的重要性を示すキーワードの存在確認

【歴史的キーワード例】
- 初、史上、記録、革命、歴史的
- 前代未聞、画期的、伝説的

【違反時の対応】
- ViolationType.EPISODE_MISSING_HISTORICAL_SIGNIFICANCE
- "歴史的重要性を示す要素が不足しています"

【実装箇所】
pdca_guardian.py:_check_historical_significance()

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_112: -114: 生涯ハイライトルール（v3.0）

**優先度**: MEDIUM

**ステータス**: active

**説明**: -114: 生涯ハイライトルール（v3.0）

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_113: （説明なし）

**優先度**: MEDIUM

**ステータス**: active

**説明**: 世界的偉業チェック

【目的】
世界的に重要な人物（is_globally_significant=True）のエピソードに、グローバルな偉業が含まれているか確認。

【チェック基準】
- impact_result['details']['global'] >= 10
- 世界的に重要な人物の場合は必須

【グローバル偉業の例】
- オリンピック金メダル
- ノーベル賞受賞
- 世界記録樹立
- 国際的な賞の受賞

【違反時の対応】
- ViolationType.EPISODE_GLOBAL_ACHIEVEMENT_MISSING
- "世界的に重要な人物なのに、グローバルな偉業が含まれていません"

【実装箇所】
pdca_guardian.py:_check_global_achievement()

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_116: （説明なし）

**優先度**: MEDIUM

**ステータス**: active

**説明**: 具体性チェック

【目的】
エピソードテキストに具体的な要素（作品名、数値、固有名詞、イベント）が含まれているか検証。

【検出要素】
1. 作品名: 「」『』で囲まれた部分
   - 例: 「ドラゴンボール」『スラムダンク』

2. 数値: 数字+単位
   - 例: 1998年、100万人、3位、50億円

3. 固有名詞: 大文字始まり/カタカナ3文字以上
   - 例: Tokyo、オリンピック

4. イベントキーワード:
   - 優勝、受賞、発表、公演、開催、出演、登場

【違反基準】
- 具体的要素が2つ未満の場合

【実装箇所】
pdca_guardian.py:_check_concreteness()

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_117: （説明なし）

**優先度**: MEDIUM

**ステータス**: active

**説明**: 感銘要素チェック

【目的】
エピソードに人々を感銘させる要素が含まれているか、6つのカテゴリから検証。

【6つの感銘カテゴリ】
1. achievement（実績）: 優勝、受賞、MVP、金メダル、世界一
2. challenge（挑戦）: 挑戦、困難、逆境、苦労、壁
3. emotion（感情）: 感動、涙、感謝、喜び、熱意
4. milestone（転機）: デビュー、転機、独立、結婚、引退
5. historical（歴史性）: 初、史上、革命、歴史的、伝説
6. relationship（人間関係）: 出会い、別れ、仲間、師匠、ライバル

【チェック基準】
- 最低2つのカテゴリから要素を含むこと
- 各カテゴリに複数のキーワードを定義

【違反時の対応】
- 感銘要素が不足している旨を警告
- 具体的にどのカテゴリが不足しているか提示

【実装箇所】
pdca_guardian.py:_check_impact_elements()

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_122: データベースエントリ欠落チェック

**優先度**: MEDIUM

**ステータス**: active

**説明**: データベースエントリ欠落チェック

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_123: 出力途中切断チェック

**優先度**: MEDIUM

**ステータス**: active

**説明**: 出力途中切断チェック

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_124: 教育的文脈欠落チェック

**優先度**: MEDIUM

**ステータス**: active

**説明**: 教育的文脈欠落チェック

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_125: CSVエスケープエラーチェック

**優先度**: MEDIUM

**ステータス**: active

**説明**: CSVエスケープエラーチェック

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_126: データ鮮度チェック

**優先度**: MEDIUM

**ステータス**: active

**説明**: データ鮮度チェック

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_127: より良い選択肢の存在チェック

**優先度**: MEDIUM

**ステータス**: active

**説明**: より良い選択肢の存在チェック

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_131: -133: 功績主体性ルール (v3.5) - 功績の正確な帰属

**優先度**: MEDIUM

**ステータス**: active

**説明**: -133: 功績主体性ルール (v3.5) - 功績の正確な帰属

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_132: （説明なし）

**優先度**: MEDIUM

**ステータス**: active

**説明**: RULE_132: 'type': ViolationType.ACHIEVEMENT_PRIORITY_ERROR.v...
（自動生成された説明 - 要レビュー）

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_133: （説明なし）

**優先度**: MEDIUM

**ステータス**: active

**説明**: RULE_133: 'type': ViolationType.MANUAL_CREATION_DETECTED.val...
（自動生成された説明 - 要レビュー）

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_134: （説明なし）

**優先度**: MEDIUM

**ステータス**: active

**説明**: RULE_134: 'type': ViolationType.GROUP_ENTITY_PROHIBITED.valu...
（自動生成された説明 - 要レビュー）

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_135: （説明なし）

**優先度**: MEDIUM

**ステータス**: active

**説明**: RULE_135: 'type': ViolationType.GROUP_MEMBER_SPLIT_REQUIRED....
（自動生成された説明 - 要レビュー）

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_136: （説明なし）

**優先度**: MEDIUM

**ステータス**: active

**説明**: RULE_136: 'type': ViolationType.LOW_FAME_THRESHOLD.value,...
（自動生成された説明 - 要レビュー）

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_137: 主観的表現の検出

**優先度**: MEDIUM

**ステータス**: active

**説明**: 主観的表現の検出

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_138: 価値判断の検出

**優先度**: MEDIUM

**ステータス**: active

**説明**: 価値判断の検出

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_139: 定型文の検出

**優先度**: MEDIUM

**ステータス**: active

**説明**: 定型文の検出

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_140: 感動価値不足

**優先度**: MEDIUM

**ステータス**: active

**説明**: 感動価値不足

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_141: オリンピック・世界大会の軽視

**優先度**: MEDIUM

**ステータス**: active

**説明**: オリンピック・世界大会の軽視

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_142: ドラマ性欠如

**優先度**: MEDIUM

**ステータス**: active

**説明**: ドラマ性欠如

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_143: 共感可能性不足

**優先度**: MEDIUM

**ステータス**: active

**説明**: 共感可能性不足

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_144: ストーリー性の確保

**優先度**: MEDIUM

**ステータス**: active

**説明**: ストーリー性の確保

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_145: コンテキストの豊富化

**優先度**: MEDIUM

**ステータス**: active

**説明**: コンテキストの豊富化

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_146: 共感性の最大化

**優先度**: MEDIUM

**ステータス**: active

**説明**: 共感性の最大化

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_147: 意味付けの明確化

**優先度**: MEDIUM

**ステータス**: active

**説明**: 意味付けの明確化

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_148: 最も重要な瞬間を優先

**優先度**: HIGH

**ステータス**: active

**説明**: 最も重要な瞬間を優先

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_149: 年齢制約より価値を重視

**優先度**: MEDIUM

**ステータス**: active

**説明**: 年齢制約より価値を重視

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_150: 複数年齢候補の比較評価

**優先度**: MEDIUM

**ステータス**: active

**説明**: 複数年齢候補の比較評価

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_152: 文末表現チェック

**優先度**: MEDIUM

**ステータス**: active

**説明**: 文末表現チェック

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_153: 節目重要度チェック

**優先度**: HIGH

**ステータス**: active

**説明**: 節目重要度チェック

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_155: 最年少・最年長記録優先

**優先度**: MEDIUM

**ステータス**: active

**説明**: 最年少・最年長記録優先

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_156: インパクト最大化年齢選択

**優先度**: MEDIUM

**ステータス**: active

**説明**: インパクト最大化年齢選択

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_157: 文化現象優先

**優先度**: MEDIUM

**ステータス**: active

**説明**: 文化現象優先

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_158: 社会貢献評価

**優先度**: MEDIUM

**ステータス**: active

**説明**: 社会貢献評価

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_159: 3軸バランス

**優先度**: MEDIUM

**ステータス**: active

**説明**: 3軸バランス

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_163: 教育的価値確保

**優先度**: MEDIUM

**ステータス**: active

**説明**: 教育的価値確保

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_164: 日付ノイズ違反 (v5.7)

**優先度**: MEDIUM

**ステータス**: active

**説明**: 日付ノイズ違反 (v5.7)

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_165: 動詞・形容詞終了

**優先度**: MEDIUM

**ステータス**: active

**説明**: 動詞・形容詞終了

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_167: ファクトチェック

**優先度**: MEDIUM

**ステータス**: active

**説明**: ファクトチェック

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_168: 品質優先原則

**優先度**: MEDIUM

**ステータス**: active

**説明**: 品質優先原則

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_169: （説明なし）

**優先度**: MEDIUM

**ステータス**: active

**説明**: バッチ処理個別検証

【目的】
バッチ処理時に各エピソードを個別検証し、品質保証を行う。

【検証項目】
1. 重複検出:
   - 各エピソードの先頭50文字をキーとして重複チェック
   - 重複が検出された場合はエラー

2. エピソード数検証:
   - 最低7件のエピソードが必要
   - 7件未満の場合はcritical違反

3. 個別品質チェック:
   - 各エピソードが他のルールに準拠しているか確認

【違反時の対応】
- 重複: duplicate_episode違反を記録
- 数不足: episode_count_insufficient（severity: critical）

【実装箇所】
pdca_guardian.py:check_batch_individual_verification()

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

## EPISODE_FORMAT

### FORMAT_001: エピソード文字数範囲チェック

**優先度**: HIGH

**ステータス**: active

**説明**: エピソードは132-250文字の範囲内であること
（2025-10-02更新: 文字数範囲を132-250に統一）
（2025-10-02更新: 文字数範囲を132-250に統一）

**実装**: `episode_guardian.py`

---

### RULE_101: # エピソード関連の違反タイプ（RULE_101-108）

**優先度**: LOW

**ステータス**: active

**説明**: エピソード関連の違反タイプ（RULE_101-108のカテゴリヘッダー）

**実装**: `pdca_guardian.py`

**タグ**: category_header, organizational

---

### RULE_115: -117: エピソード品質ルール (v3.1)

**優先度**: MEDIUM

**ステータス**: active

**説明**: -117: エピソード品質ルール (v3.1)

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_121: エピソードテキスト不完全チェック

**優先度**: MEDIUM

**ステータス**: active

**説明**: エピソードテキスト不完全チェック

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_151: 文字数制限チェック（132-250文字）

**優先度**: MEDIUM

**ステータス**: active

**説明**: 文字数制限チェック

【標準範囲】
最小: 132文字
最大: 250文字

【更新履歴】
- 2025-09-22: 最小値を150から132に緩和
- 2025-10-02: FORMAT_001/RULE_160と完全統一

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_160: 文字数制限（132-250）

**優先度**: MEDIUM

**ステータス**: active

**説明**: 文字数制限（150-250）
（2025-10-02更新: 文字数範囲を132-250に統一）
（2025-10-02更新: 文字数範囲を132-250に統一）

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

## EPISODE_CONTENT

### RULE_100: クレジット管理の永久化

**優先度**: HIGH

**ステータス**: active

**説明**: すべてのエピソードとCSV出力に開発クレジットを付与すること。

**実装**: `pdca_guardian.py`

**タグ**: credit, metadata

---

### RULE_118: -120: 事実正確性ルール (v3.2) - ハルシネーション防止

**優先度**: MEDIUM

**ステータス**: active

**説明**: -120: 事実正確性ルール (v3.2) - ハルシネーション防止

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_161: 客観的事実主義

**優先度**: MEDIUM

**ステータス**: active

**説明**: 客観的事実主義

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_162: 具体的描写義務

**優先度**: MEDIUM

**ステータス**: active

**説明**: 具体的描写義務

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_166: 事実優先原則

**優先度**: MEDIUM

**ステータス**: active

**説明**: 事実優先原則

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

---

### RULE_171: 括弧内ワード重複防止

**優先度**: CRITICAL

**ステータス**: active

**説明**: 名前の横に括弧が付いた場合、その括弧内ワードはエピソード本文に使用されないこと。

【目的】
- グループメンバーや架空キャラクターの名前表示時に、括弧内のグループ名/作品名がエピソード本文に重複出現することを防ぐ
- 視覚的な冗長性を排除し、読みやすさを向上させる

【適用対象】
1. **グループメンバー**
   - 例: `あなたと同じ30歳のとき、髙比良くるま(令和ロマン)は`
   - エピソード本文に「令和ロマン」という文字列を含んではいけない

2. **架空キャラクター**
   - 例: `あなたと同じ19歳のとき、モンキー・D・ルフィ（ONE PIECE）は`
   - エピソード本文に「ONE PIECE」という文字列を含んではいけない

【チェックロジック】
```python
def check_bracket_word_duplication(person_name, group_or_work_name, episode_text):
    # 括弧内ワードがエピソード本文に存在するか
    if group_or_work_name and group_or_work_name in episode_text:
        return {
            'valid': False,
            'violation': 'RULE_171',
            'message': f'括弧内ワード「{group_or_work_name}」がエピソード本文に重複'
        }
    return {'valid': True}
```

【違反例】
❌ **違反**: `YOSHIKI(X JAPAN)` の場合
```
あなたと同じ23歳のとき、YOSHIKI(X JAPAN)は
XJAPANとして「BLUEBLOOD」でメジャーデビューを果たした。
                ^^^^^^ 違反！括弧内「X JAPAN」と重複
```

✅ **正解**:
```
あなたと同じ23歳のとき、YOSHIKI(X JAPAN)は
「BLUEBLOOD」でメジャーデビューを果たした。
ビジュアル系ロックという新ジャンルを確立...
```

【適用タイミング】
- エピソード生成時の最終検証
- 既存エピソードの修正時
- Episode Guardian による自動チェック

【関連ルール】
- ENTITY_TYPE_001: グループ名の個人誤登録防止
- FORMAT_001: エピソード形式統一


**実装**: `episode_guardian.py` - `check_bracket_word_duplication()`

**タグ**: episode_format, group_name, work_title, duplication_prevention, readability

---

## ENTITY_TYPE

### ENTITY_TYPE_001: グループ名の個人誤登録防止

**優先度**: CRITICAL

**ステータス**: active

**説明**: グループ名個人化チェック

【目的】
グループ名が個人（person）として誤って登録されていないかチェック。

【チェック項目】
1. entity_type が 'person' でperson_nameにグループ名が使用されていないか
2. person_name_display でグループ名を正しく表記しているか
3. 複数人組のグループを個人として扱っていないか

【元のルール】
- ENTITY_TYPE_001: グループ名個人化チェック

【目的】
グループ名が個人（person）として誤って登録されていないか...
- RULE_154: グループ名個人化チェック...

（2025-10-02統合: ENTITY_TYPE_001とRULE_154を統合）


**実装**: `episode_guardian.py`

---

### RULE_154: グループ名個人化チェック

**優先度**: MEDIUM

**ステータス**: deprecated

**説明**: グループ名個人化チェック

**実装**: `pdca_guardian.py`

**タグ**: pdca, migrated

⚠️ このルールは `ENTITY_TYPE_001` に置き換えられました

---
