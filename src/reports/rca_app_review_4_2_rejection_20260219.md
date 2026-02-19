# RCA: App Store 4.2リジェクション分析レポート

**作成日**: 2026年2月19日
**対象アプリ**: 最期の砂時計 v1.0 (ビルド 1.0.7 build 44)
**リジェクション日**: 2026年2月17日
**審査環境**: iPhone 17 Pro Max
**違反ガイドライン**: 4.2 - Design: Minimum Functionality

---

## 📋 背景

### リジェクション詳細
- **Apple審査官のコメント**:
  > "The usefulness of the app is limited by the minimal functionality it currently provides."

- **アプリ規模**:
  - ネイティブSwiftUIアプリ（Webラッパーではない）
  - 93ファイル、19,312行のコード
  - 完全実装済みの機能が複数存在

### 問題の本質
審査官に「機能が少ない」と判断されたが、実際には以下が実装済みだった:
- 571行の完全実装済みHealthDashboard UI
- 6カテゴリの健康スコア分析
- エピソードデータベース（Supabase経由）
- お気に入り機能
- プロフィール・設定画面

しかし、これらが**審査官に見えない/届かない状態**だった。

---

## 🔍 根本原因分析（5項目）

### 1. HealthDashboardが到達不可能（CRITICAL）

**問題**:
- 571行の完全実装済みUIがタブとして登録されていなかった
- コード内に `// periphery:ignore:all - 将来使用予定` とコメントされ、未使用扱い
- 健康スコア分析（6カテゴリ）が審査官に一切見えなかった

**影響**:
- アプリの主要機能の1つが完全に隠蔽された状態
- 審査官は「3タブだけのシンプルなアプリ」と認識

**証拠**:
```swift
// MainTabView.swift (修正前)
// HealthDashboardViewは存在するが、タブ定義に含まれていない
```

---

### 2. エピソードがSupabase完全依存（HIGH）

**問題**:
- 初回起動時/オフライン時、わずか9個のハードコードされたフォールバックパターンのみ表示
- 審査官の環境でSupabase接続が不安定だった可能性
- コンテンツが「スカスカ」に見えた

**影響**:
- データベース機能が審査官に伝わらなかった
- 「最小限の機能性」と判断される要因

**現行のフォールバック階層** (修正前):
```
Supabase → Cache → 9個のハードコードパターン
```

---

### 3. メイン画面の情報密度が低い（HIGH）

**問題**:
- 表示内容: 残り時間 + 死亡予定日 + 砂時計 + 進捗バー + エピソード1件
- 1画面で完結してしまい、「これだけ?」という印象

**影響**:
- アプリの深さが伝わらない
- スクロール不要 = コンテンツ不足に見える

---

### 4. お気に入りタブが初回起動時に空（MEDIUM）

**問題**:
- 「お気に入りはまだありません」メッセージのみ
- 使い方のガイドなし

**影響**:
- タブの1/3が実質的に空白
- 機能が少ない印象を強化

---

### 5. ドラマティックアニメーションが毎回再生（MEDIUM）

**問題**:
- 6.5秒のドラマティックシーケンスがタブ切り替えごとに再生
- スキップ機能なし

**影響**:
- 審査官が他機能を探索しにくい
- 待ち時間でイライラ → 「使いにくい」と判断される可能性

---

## ✅ 対策実施（5ステップ）

### Step 1: HealthDashboardを第2タブとして追加

**実装内容**:
```swift
// MainTabView.swift
// 6タブレイアウト: タイムリミット → 健康 → お気に入り → プロフィール → 設定 → About
TabView(selection: $selectedTab) {
    LifeResultView()
        .tabItem { Label("タイムリミット", systemImage: "hourglass") }
        .tag(Tab.lifeResult)

    HealthDashboardView()  // ← 新規追加
        .tabItem { Label("健康", systemImage: "heart.fill") }
        .tag(Tab.health)

    // ... 以下既存タブ
}
```

**修正ファイル**:
- `Views/Main/MainTabView.swift`
- `Views/HealthDashboard/HealthDashboardView.swift` (`periphery:ignore` 削除)

**効果**:
- 571行の完全実装UIが審査官に見える
- 6カテゴリ健康分析が利用可能に

---

### Step 2: ドラマティックシーケンスのスキップ機能追加

**実装内容**:
```swift
// LifeResultView.swift
@AppStorage("hasSeenDramaticSequence") private var hasSeenDramaticSequence = false

.onAppear {
    if !hasSeenDramaticSequence {
        // 初回のみドラマティックシーケンスを再生
        showDramaticSequence()
        hasSeenDramaticSequence = true
    }
}
```

**修正ファイル**:
- `Views/LifeResult/LifeResultView.swift`

**効果**:
- 2回目以降の訪問でアニメーションスキップ
- 審査官が他機能を探索しやすくなる

---

### Step 3: bundled_episodes.jsonでオフラインフォールバック強化

**実装内容**:
- 41件のエピソードを含むJSONファイルをリソースに追加
- 新しいフォールバック階層:
```
Supabase → Cache → Bundled (41件) → Hardcoded (9件)
```

**追加ファイル**:
- `FinalHourglass/Resources/bundled_episodes.json` (新規)

**修正ファイル**:
- `Managers/EpisodeManager.swift`

**効果**:
- 初回起動・オフライン時でも41件のエピソードが表示
- データベース機能の実質性が伝わる

---

### Step 4: お気に入り空状態の改善

**実装内容**:
```swift
// FavoriteEpisodesView.swift
VStack(spacing: 24) {
    Image(systemName: "star.fill")
        .font(.system(size: 64))

    Text("お気に入りはまだありません")
        .font(.title2)

    // 4ステップガイド追加
    VStack(alignment: .leading, spacing: 12) {
        GuideStep(number: 1, text: "「タイムリミット」タブでエピソードを表示")
        GuideStep(number: 2, text: "気になるエピソードをタップ")
        GuideStep(number: 3, text: "詳細画面で ⭐ をタップ")
        GuideStep(number: 4, text: "ここに保存されます")
    }
}
```

**修正ファイル**:
- `Views/Favorites/FavoriteEpisodesView.swift`

**効果**:
- 空状態でも使い方が明確に
- 機能のガイダンスを提供

---

### Step 5: メイン画面に健康サマリーカード追加

**実装内容**:
```swift
// HealthSummaryCard.swift (新規コンポーネント)
// - 健康スコア円グラフ
// - 改善ポイントTop 3
// - 「詳しく見る」リンク（健康タブへ遷移）
```

**追加ファイル**:
- `Views/Components/HealthSummaryCard.swift` (新規)

**修正ファイル**:
- `Views/LifeResult/LifeResultView.swift`

**効果**:
- メイン画面の情報密度向上
- 健康機能への導線確保
- スクロール可能なコンテンツを提供

---

## 🛡️ 再発防止策

### リリース前チェックリスト

1. **機能登録確認**:
   - [ ] 実装済み機能が全てMainTabViewに登録されているか
   - [ ] `periphery:ignore` コメントがないか確認

2. **オフライン体験テスト**:
   - [ ] 機内モードで起動
   - [ ] 初回起動時のコンテンツ量確認
   - [ ] フォールバックデータが適切に表示されるか

3. **初回起動体験チェック**:
   - [ ] 全タブに意味のあるコンテンツが存在するか
   - [ ] 空状態に適切なガイダンスがあるか

4. **審査官視点でのレビュー**:
   - [ ] 機能一覧を外部の人間に説明して「少ない」と言われないか
   - [ ] 各タブを順番に見て、使い方が自明か

---

## 📁 変更ファイル一覧

| ファイル | 対策ステップ | 変更内容 |
|---------|------------|---------|
| `Views/Main/MainTabView.swift` | Step 1 | 健康タブ追加（6タブレイアウト） |
| `Views/HealthDashboard/HealthDashboardView.swift` | Step 1 | `periphery:ignore` 削除 |
| `Views/LifeResult/LifeResultView.swift` | Step 2, 5 | アニメスキップ + 健康カード追加 |
| `Managers/EpisodeManager.swift` | Step 3 | bundled JSON読み込み実装 |
| `Resources/bundled_episodes.json` | Step 3 | 41件のエピソード（新規） |
| `Views/Favorites/FavoriteEpisodesView.swift` | Step 4 | 4ステップガイド追加 |
| `Views/Components/HealthSummaryCard.swift` | Step 5 | 健康サマリーカード（新規） |

---

## ✅ 検証結果

### ビルド検証
- **環境**: Xcode、iPhone 17 Pro シミュレータ
- **結果**: ✅ PASSED

### 機能検証

| 検証項目 | 結果 | 備考 |
|---------|------|------|
| 6タブ全て表示・遷移可能 | ✅ PASSED | タイムリミット/健康/お気に入り/プロフィール/設定/About |
| オフライン時に41件のエピソード表示 | ✅ PASSED | bundled_episodes.json 読み込み成功 |
| 健康サマリーカードがメイン画面に表示 | ✅ PASSED | スコア円グラフ + Top 3 改善点 |
| ドラマティックシーケンスが2回目以降スキップ | ✅ PASSED | `hasSeenDramaticSequence` フラグ動作確認 |
| お気に入り空状態に4ステップガイド表示 | ✅ PASSED | 使い方が明確に |

---

## 📊 影響度評価

### Before (リジェクション時)
- **タブ数**: 3タブ（健康タブが隠蔽）
- **初回起動エピソード数**: 9件（ハードコードのみ）
- **メイン画面情報密度**: 低（1画面完結）
- **ドラマティックアニメ**: 毎回6.5秒再生

### After (対策実施後)
- **タブ数**: 6タブ（全機能が可視化）
- **初回起動エピソード数**: 41件（bundled JSON）
- **メイン画面情報密度**: 中〜高（健康カード追加でスクロール可能に）
- **ドラマティックアニメ**: 初回のみ、2回目以降スキップ

---

## 🎯 期待される審査結果

### 4.2リジェクション要因の解消

| リジェクション要因 | 対策 | 解消度 |
|------------------|------|--------|
| 機能が少ない（実際は隠蔽） | 健康タブ追加 | ✅ 100% |
| コンテンツがスカスカ | bundled 41件 + 健康カード | ✅ 100% |
| 探索しにくい | アニメスキップ | ✅ 100% |
| 空状態が多い | お気に入りガイド | ✅ 100% |

### 次回審査で審査官が目にするもの
1. **6つの機能的なタブ** （vs 3タブ）
2. **41件のエピソード** （vs 9件）
3. **健康スコア分析** （完全に見えなかった → 可視化）
4. **スクロール可能なメイン画面** （vs 1画面完結）
5. **使い方ガイド付き空状態** （vs 「ありません」のみ）

---

## 📝 教訓

### What Went Wrong
- **実装済み機能がタブに登録されていない** という致命的な見落とし
- オフライン/初回起動のテストが不十分
- 審査官視点でのレビューが欠如

### What Went Right
- ネイティブアプリの基盤は十分に堅牢（93ファイル、19,312行）
- 修正箇所は限定的（7ファイルのみ）
- 対策実施で審査官体験が大幅改善

### Key Takeaway
> **「実装した ≠ 審査官に見える」**
> 機能は実装だけでなく、**登録・表示・導線設計**まで完遂して初めて完成する。

---

## 🔄 次回アクション

1. **再ビルド・TestFlight配信** (build 45)
2. **App Store再申請**
3. **審査待機中**: オフライン体験の継続改善
4. **承認後**: ユーザーフィードバック収集

---

**作成者**: Claude Code (Sonnet 4.5)
**レビュー**: ─
**承認**: ─
**文書バージョン**: 1.0
