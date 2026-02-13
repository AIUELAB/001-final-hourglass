import XCTest

/// 設定画面のPage Object
struct SettingsPage {
    let app: XCUIApplication

    /// CI環境用のタイムアウト時間
    private static let ciTimeout: TimeInterval = 30

    // MARK: - Elements

    var settingsTitle: XCUIElement {
        app.navigationBars["設定"].firstMatch
    }

    var bgmVolumeSlider: XCUIElement {
        app.sliders["BGM音量"].firstMatch
    }

    var hapticToggle: XCUIElement {
        // UIが「振動フィードバック」に変更されたため、複数のパターンで検索
        // MysticalToggleはカスタムトグルなので、テキストラベルで検索
        let vibrationText = app.staticTexts["振動フィードバック"]
        if vibrationText.exists {
            return vibrationText
        }
        // フォールバック: 旧名称
        return app.staticTexts["触覚フィードバック"].firstMatch
    }

    var reminderToggle: XCUIElement {
        // MysticalToggleを使用しているため、テキストラベルで検索
        let reminderText = app.staticTexts["リマインダー"]
        if reminderText.exists {
            return reminderText
        }
        return app.staticTexts["リマインダー"].firstMatch
    }

    /// 振動フィードバック行が存在するか（テスト用）
    var hapticRowExists: Bool {
        app.staticTexts["振動フィードバック"].waitForExistence(timeout: Self.ciTimeout)
    }

    /// リマインダー行が存在するか（テスト用）
    var reminderRowExists: Bool {
        app.staticTexts["リマインダー"].waitForExistence(timeout: Self.ciTimeout)
    }

    var dataResetButton: XCUIElement {
        app.buttons["データリセット"].firstMatch
    }

    var shareSection: XCUIElement {
        // 「共有」はセクションヘッダーのText、「その他の方法で共有」は実際のボタン
        app.buttons["その他の方法で共有"].firstMatch
    }

    /// 共有セクションが存在するかどうか（セクションヘッダーまたは共有ボタンで確認）
    var shareButton: XCUIElement {
        // UIが更新され「共有」ボタンがなくなったため、代わりに存在する要素を探す
        // 「その他の方法で共有」ボタンまたは「Xに投稿」ボタンを探す
        let otherShareButton = app.buttons["その他の方法で共有"]
        if otherShareButton.exists {
            return otherShareButton
        }
        return app.buttons["Xに投稿"].firstMatch
    }

    var cacheSettingsButton: XCUIElement {
        // キャッシュ設定はUIから削除されたため、存在しない要素を返す
        // テスト側でスキップする
        app.buttons["キャッシュ設定"].firstMatch
    }

    /// キャッシュ設定が存在するか（テスト用）
    var cacheSettingsExists: Bool {
        app.buttons["キャッシュ設定"].waitForExistence(timeout: 5)
    }

    // MARK: - Verification

    /// 設定画面が表示されているか
    var isDisplayed: Bool {
        // まずナビゲーションバーを確認、なければ設定タブが選択されているか確認
        let navBarExists = settingsTitle.waitForExistence(timeout: Self.ciTimeout)
        if navBarExists { return true }

        // フォールバック: 設定タブが選択されているか確認
        let settingsTab = app.tabBars.buttons["設定"]
        if settingsTab.exists { return settingsTab.isSelected }
        // iPad フォールバック: タブコンテンツの accessibilityIdentifier で判定
        return app.otherElements["tab_settings"].waitForExistence(timeout: 3)
    }

    // MARK: - Actions

    func toggleHaptic() {
        hapticToggle.tap()
    }

    func toggleReminder() {
        reminderToggle.tap()
    }
}
