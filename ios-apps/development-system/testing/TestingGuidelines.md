# iOS App Store 準拠テストガイドライン

## テスト実行環境設定

### 必要なテスト環境
- **物理デバイス**: iPhone SE (第2世代), iPhone 14, iPhone 14 Plus, iPhone 14 Pro Max
- **iPadデバイス**: iPad (第9世代), iPad Pro 12.9インチ
- **Simulators**: iOS 15.0, 16.0, 17.0 各最新版
- **テストアカウント**: Sandbox環境用テストアカウント

### テスト実行チェックリスト

#### Phase 1: 基本機能テスト (必須)
- [ ] **アプリ起動テスト**: 3秒以内に起動完了
- [ ] **メモリ使用量テスト**: 200MB以下を維持
- [ ] **バックグラウンド復帰テスト**: データ保持確認
- [ ] **ネットワーク切断テスト**: 適切なエラー表示
- [ ] **権限要求テスト**: 理由説明の明確性
- [ ] **クラッシュテスト**: 異常終了なし

#### Phase 2: App Store Guidelines準拠テスト (必須)
- [ ] **プライバシー同意フロー**: Guidelines 5.1.1
- [ ] **データ収集透明性**: Guidelines 5.1.2
- [ ] **App Tracking Transparency**: iOS 14.5+
- [ ] **アプリ内課金フロー**: Guidelines 3.1.1
- [ ] **コンテンツモデレーション**: Guidelines 1.2
- [ ] **年齢制限適合性**: Guidelines 1.2

#### Phase 3: パフォーマンステスト (推奨)
- [ ] **起動時間測定**: XCTApplicationLaunchMetric
- [ ] **スクロールパフォーマンス**: XCTOSSignpostMetric
- [ ] **メモリパフォーマンス**: XCTMemoryMetric
- [ ] **バッテリー消費測定**: XCTCPUMetric
- [ ] **ネットワーク効率**: データ使用量測定

#### Phase 4: アクセシビリティテスト (必須)
- [ ] **VoiceOver対応**: すべてのUI要素
- [ ] **Dynamic Type対応**: 文字サイズ変更
- [ ] **カラーコントラスト**: WCAG AA準拠
- [ ] **スイッチコントロール**: 代替操作方法

#### Phase 5: セキュリティテスト (必須)
- [ ] **データ暗号化**: 機密データ保護
- [ ] **キーチェーン使用**: 認証情報保護
- [ ] **HTTPSのみ通信**: ATS準拠
- [ ] **証明書ピニング**: 通信セキュリティ

## テストシナリオ詳細

### 1. 起動・終了テスト

```swift
func testAppLaunchScenarios() {
    // コールドスタート（初回起動）
    testColdStart()
    
    // ウォームスタート（バックグラウンドから復帰）
    testWarmStart()
    
    // メモリ不足時の起動
    testLowMemoryLaunch()
}

private func testColdStart() {
    let app = XCUIApplication()
    let startTime = CFAbsoluteTimeGetCurrent()
    
    app.launch()
    
    let mainScreen = app.otherElements["MainScreen"]
    let exists = mainScreen.waitForExistence(timeout: 3.0)
    let launchTime = CFAbsoluteTimeGetCurrent() - startTime
    
    XCTAssertTrue(exists, "メイン画面が表示されませんでした")
    XCTAssertLessThan(launchTime, 3.0, "起動時間が3秒を超えました: \(launchTime)")
}
```

### 2. メモリ管理テスト

```swift
func testMemoryManagement() {
    let app = XCUIApplication()
    app.launch()
    
    // 初期メモリ使用量の記録
    let initialMemory = getMemoryUsage().resident
    
    // 大量のデータを処理
    performMemoryIntensiveTask()
    
    // メモリ使用量の確認
    let currentMemory = getMemoryUsage().resident
    let memoryIncrease = currentMemory - initialMemory
    
    XCTAssertLessThan(memoryIncrease, 100_000_000, "メモリ使用量の増加が100MBを超えました")
    
    // メモリ解放の確認
    performMemoryCleanup()
    Thread.sleep(forTimeInterval: 2.0)
    
    let finalMemory = getMemoryUsage().resident
    XCTAssertLessThan(finalMemory - initialMemory, 50_000_000, "メモリが適切に解放されていません")
}
```

### 3. ネットワークテスト

```swift
func testNetworkScenarios() {
    // オンライン状態でのテスト
    testOnlineMode()
    
    // オフライン状態でのテスト
    testOfflineMode()
    
    // 低速ネットワークでのテスト
    testSlowNetwork()
    
    // 断続的接続でのテスト
    testIntermittentConnection()
}

private func testOfflineMode() {
    let app = XCUIApplication()
    app.launch()
    
    // ネットワーク接続を無効にした状態をシミュレート
    simulateNetworkUnavailable()
    
    let refreshButton = app.buttons["更新"]
    refreshButton.tap()
    
    // 適切なエラーメッセージの表示確認
    let errorAlert = app.alerts.element
    XCTAssertTrue(errorAlert.waitForExistence(timeout: 5.0))
    XCTAssertTrue(errorAlert.staticTexts["接続エラー"].exists)
    
    // 再試行ボタンの存在確認
    XCTAssertTrue(errorAlert.buttons["再試行"].exists)
}
```

### 4. データ整合性テスト

```swift
func testDataIntegrity() {
    let app = XCUIApplication()
    app.launch()
    
    // テストデータの作成
    createTestData()
    
    // アプリをバックグラウンドに移行
    XCUIDevice.shared.press(.home)
    Thread.sleep(forTimeInterval: 5.0)
    
    // メモリ警告をシミュレート
    simulateMemoryWarning()
    
    // アプリを再度フォアグラウンドに
    app.activate()
    
    // データの整合性確認
    XCTAssertTrue(verifyTestData(), "バックグラウンド移行後にデータが破損しました")
}
```

## パフォーマンス測定基準

### App Store Review Guidelines推奨値
- **起動時間**: 3秒以内
- **メモリ使用量**: 200MB以下（標準的なアプリ）
- **バッテリー消費**: 1時間使用で5%以下
- **ネットワーク使用量**: 必要最小限
- **ストレージ使用量**: アプリサイズ + データで500MB以下

### 測定ツールと方法

#### 1. Xcode Instruments
```bash
# メモリリークの検出
instruments -t Leaks -D leak_results.trace YourApp.app

# 時間プロファイリング
instruments -t "Time Profiler" -D time_profile.trace YourApp.app

# エネルギー診断
instruments -t "Energy Log" -D energy_log.trace YourApp.app
```

#### 2. XCTest Performance Metrics
```swift
func testPerformanceMetrics() {
    measure(metrics: [
        XCTApplicationLaunchMetric(),
        XCTMemoryMetric(),
        XCTCPUMetric(),
        XCTStorageMetric(),
        XCTClockMetric()
    ]) {
        performCriticalOperation()
    }
}
```

### 3. カスタム測定実装
```swift
class PerformanceMonitor {
    static func measureExecutionTime<T>(_ operation: () -> T) -> (result: T, time: TimeInterval) {
        let startTime = CFAbsoluteTimeGetCurrent()
        let result = operation()
        let endTime = CFAbsoluteTimeGetCurrent()
        return (result, endTime - startTime)
    }
    
    static func getCurrentMemoryUsage() -> Int64 {
        var info = mach_task_basic_info()
        var count = mach_msg_type_number_t(MemoryLayout<mach_task_basic_info>.size)/4
        
        let result = withUnsafeMutablePointer(to: &info) {
            $0.withMemoryRebound(to: integer_t.self, capacity: 1) {
                task_info(mach_task_self_, task_flavor_t(MACH_TASK_BASIC_INFO), $0, &count)
            }
        }
        
        return result == KERN_SUCCESS ? Int64(info.resident_size) : 0
    }
}
```

## エラーハンドリングテスト

### 必須エラーシナリオ
1. **ネットワークエラー**
   - 接続なし
   - タイムアウト
   - サーバーエラー (4xx, 5xx)

2. **リソース不足エラー**
   - メモリ不足
   - ストレージ不足
   - バッテリー低下

3. **権限エラー**
   - カメラアクセス拒否
   - 位置情報アクセス拒否
   - 写真ライブラリアクセス拒否

4. **データエラー**
   - 無効なデータ形式
   - 破損したファイル
   - 同期エラー

### エラーハンドリング評価基準
```swift
func evaluateErrorHandling() -> Bool {
    let criteria = [
        isUserFriendlyErrorMessage(),
        hasRecoveryOptions(),
        doesNotCrashOnError(),
        logsErrorsProperly(),
        showsProgressIndicators()
    ]
    
    return criteria.allSatisfy { $0 }
}

private func isUserFriendlyErrorMessage() -> Bool {
    // エラーメッセージが分かりやすい言葉で書かれているか
    // 技術的な詳細を含んでいないか
    return true
}

private func hasRecoveryOptions() -> Bool {
    // 「再試行」「キャンセル」「設定を開く」などの選択肢があるか
    return true
}
```

## 自動化されたテスト実行

### CI/CD統合
```yaml
# GitHub Actions例
name: iOS App Store Compliance Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Xcode
        uses: maxim-lobanov/setup-xcode@v1
        with:
          xcode-version: latest-stable
      
      - name: Run Unit Tests
        run: |
          xcodebuild test \
            -scheme YourApp \
            -destination 'platform=iOS Simulator,name=iPhone 14' \
            -testPlan UnitTests
      
      - name: Run UI Tests
        run: |
          xcodebuild test \
            -scheme YourApp \
            -destination 'platform=iOS Simulator,name=iPhone 14' \
            -testPlan UITests
      
      - name: Run Performance Tests
        run: |
          xcodebuild test \
            -scheme YourApp \
            -destination 'platform=iOS Simulator,name=iPhone 14' \
            -testPlan PerformanceTests
```

### テストレポート生成
```bash
# テスト結果の生成
xcrun xccov view --report --json DerivedData/YourApp/Logs/Test/*.xcresult > coverage.json

# パフォーマンスレポートの生成
xcrun xctrace export --input performance.trace --output performance_report.xml
```

## テスト結果の評価基準

### 合格基準
- **Unit Tests**: 90%以上のパス率
- **UI Tests**: 95%以上のパス率
- **Performance Tests**: 全項目で基準値クリア
- **Memory Tests**: メモリリークなし
- **Security Tests**: 全項目パス

### 不合格時の対応
1. **即座に修正が必要な問題**
   - クラッシュ
   - メモリリーク
   - セキュリティ脆弱性

2. **リリース前に修正が必要な問題**
   - パフォーマンス基準未達
   - アクセシビリティ未対応
   - エラーハンドリング不備

3. **改善推奨の問題**
   - UIの使いやすさ
   - レスポンス時間
   - バッテリー効率

## 継続的改善

### テストカバレッジの監視
```swift
// XCTest coverage報告
func generateCoverageReport() {
    // テストカバレッジ80%以上を目標
    let coverageThreshold = 0.8
    let currentCoverage = getCurrentCoverage()
    
    XCTAssertGreaterThanOrEqual(currentCoverage, coverageThreshold,
                                "テストカバレッジが\(coverageThreshold * 100)%を下回っています")
}
```

### 定期的なテスト見直し
- **月次**: テスト結果の分析とトレンド確認
- **四半期**: テスト戦略の見直し
- **リリース前**: 全テストの実行と結果検証
- **リリース後**: 実際の使用状況とテスト予想の比較