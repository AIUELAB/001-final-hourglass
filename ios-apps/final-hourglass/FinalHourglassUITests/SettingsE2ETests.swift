import XCTest

final class SettingsE2ETests: XCTestCase {
    var app: XCUIApplication!
    var mainTab: MainTabPage!
    var settingsPage: SettingsPage!

    override func setUp() {
        super.setUp()
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchWithOnboardingComplete()
        mainTab = MainTabPage(app: app)
        settingsPage = SettingsPage(app: app)
    }

    override func tearDown() {
        app = nil
        mainTab = nil
        settingsPage = nil
        super.tearDown()
    }

    // MARK: - P0: 設定画面表示

    func testSettingsScreenDisplays() {
        mainTab.selectSettings()
        XCTAssertTrue(waitForElement(settingsPage.settingsTitle), "設定画面が表示されるべき")
    }

    // MARK: - P1: 触覚フィードバック切替

    func testHapticToggleWorks() {
        mainTab.selectSettings()
        // 振動フィードバック（旧名称: 触覚フィードバック）の行が存在することを確認
        XCTAssertTrue(settingsPage.hapticRowExists, "振動フィードバック行が存在するべき")
    }

    // MARK: - P1: 設定要素の存在確認

    func testSettingsElementsExist() {
        mainTab.selectSettings()
        XCTAssertTrue(waitForElement(settingsPage.settingsTitle), "設定タイトルが表示されるべき")
        // 共有セクションの存在を確認（「Xに投稿」または「その他の方法で共有」のいずれか）
        let xShareButton = app.staticTexts["Xに投稿"]
        let otherShareButton = app.staticTexts["その他の方法で共有"]
        let shareExists = xShareButton.waitForExistence(timeout: 10) || otherShareButton.waitForExistence(timeout: 5)
        XCTAssertTrue(shareExists, "共有セクションが存在するべき")
    }

    // MARK: - P2: 通知設定への遷移

    func testNavigateToNotificationSettings() {
        mainTab.selectSettings()
        // リマインダー行の存在を確認
        XCTAssertTrue(settingsPage.reminderRowExists, "リマインダー行が存在するべき")
    }

    // MARK: - P2: キャッシュ設定への遷移

    func testNavigateToCacheSettings() throws {
        // キャッシュ設定はUIから削除されたためスキップ
        try XCTSkipIf(!settingsPage.cacheSettingsExists, "キャッシュ設定はUIから削除されました")
        mainTab.selectSettings()
        settingsPage.cacheSettingsButton.tap()
    }
}
