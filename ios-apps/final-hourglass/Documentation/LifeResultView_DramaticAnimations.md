# LifeResultView ドラマチック演出実装ガイド

## 実装完了内容（Phase 1）

### 🎭 運命の扉エフェクト
画面遷移時に黒い扉が開く演出を実装：
- 左右から黒い扉が画面を覆う
- 1.5秒かけて扉が開く
- 扉が開くと同時に結果画面が現れる

### 🌟 段階的リビール演出
各要素が順番に表示される演出：

1. **砂時計の出現** (1.0秒後)
   - 画面の3倍サイズで出現
   - スプリングアニメーションで適正サイズに縮小
   - 光輪エフェクトも連動

2. **残り時間** (2.5秒後)
   - フェードイン + スケールアニメーション
   - 数字が0からカウントアップ（1秒間）
   - 年数と日数が同時にカウント

3. **死亡予定日** (3.5秒後)
   - フェードイン + スケールアニメーション
   - 年が現在年からカウントアップ（1.5秒間）
   - 赤いグラデーションで強調

4. **進捗率** (4.5秒後)
   - プログレスバーが0%から実際の値まで増加
   - パーセンテージ表示も連動

5. **偉人エピソード** (5.5秒後)
   - フェードイン + スケールアニメーション

6. **最後の問いかけ** (6.5秒後)
   - 下からスライドイン + フェード

## 実装技術詳細

### State管理
```swift
// 表示制御
@State private var showIntro = true
@State private var showRemainingTime = false
@State private var showDeathDate = false
@State private var showHourglass = false
@State private var showProgress = false
@State private var showEpisode = false
@State private var showFinalMessage = false

// アニメーション値
@State private var hourglassScale: CGFloat = 3.0
@State private var hourglassOpacity: Double = 0.0
@State private var doorOffset: CGFloat = 0
@State private var countUpYears: Int = 0
@State private var countUpDays: Int = 0
@State private var deathYearCount: Int = 0
@State private var progressValue: Double = 0.0
```

### アニメーション技法
- `withAnimation`: 基本的なアニメーション
- `animation(_:value:)`: 値の変化に応じたアニメーション
- `DispatchQueue.main.asyncAfter`: タイミング制御
- `spring`: バウンス効果のあるアニメーション

## 今後の拡張案（Phase 2, 3）

### Phase 2: 視覚エフェクト
1. **パーティクルエフェクト**
   - 星屑が数字を形成
   - 光の粒子が浮遊

2. **ブラー→フォーカス**
   - 初期表示時に全体をブラー
   - 徐々にクリアに

3. **光のエフェクト**
   - 扉の隙間から光が漏れる
   - 数字の周りに光のパルス

### Phase 3: インタラクティブ要素
1. **スワイプで砂を落とす**
2. **タップで詳細表示**
3. **長押しでエピソード変更**

## 使用方法

実装済みのLifeResultViewは、通常通り使用できます：
```swift
NavigationLink(destination: LifeResultView()) {
    Text("結果を見る")
}
```

演出は自動的に開始され、ユーザーの操作は不要です。

## パフォーマンス考慮事項

- アニメーションは軽量で、古いデバイスでも問題なく動作
- 扉のエフェクトは`ignoresSafeArea()`で全画面表示
- カウントアップは30ステップで滑らかな動きを実現

## カスタマイズ可能な項目

- アニメーションのタイミング（各DispatchQueueの遅延時間）
- アニメーションの持続時間（duration値）
- 初期スケール値（hourglassScale）
- イージング関数（easeOut, easeInOut, spring等）
