import XCTest

/// メインタブ画面のPage Object
struct MainTabPage {
    let app: XCUIApplication

    // MARK: - Tab Elements

    var timeLimitTab: XCUIElement {
        app.tabBars.buttons["タイムリミット"]
    }

    var favoritesTab: XCUIElement {
        app.tabBars.buttons["お気に入り"]
    }

    var profileTab: XCUIElement {
        app.tabBars.buttons["プロファイル"]
    }

    var settingsTab: XCUIElement {
        app.tabBars.buttons["設定"]
    }

    var aboutTab: XCUIElement {
        app.tabBars.buttons["About"]
    }

    // MARK: - Verification

    /// CI環境用タイムアウト時間（シミュレータの遅延を考慮）
    private static let ciTimeout: TimeInterval = 30

    /// タブバーが表示されているか
    var isDisplayed: Bool {
        app.tabBars.firstMatch.waitForExistence(timeout: Self.ciTimeout)
    }

    // MARK: - Actions

    func selectTimeLimit() {
        timeLimitTab.tap()
    }

    func selectFavorites() {
        favoritesTab.tap()
    }

    func selectProfile() {
        profileTab.tap()
    }

    func selectSettings() {
        settingsTab.tap()
    }

    func selectAbout() {
        aboutTab.tap()
    }
}
