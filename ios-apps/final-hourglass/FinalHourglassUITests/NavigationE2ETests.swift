import XCTest

final class NavigationE2ETests: XCTestCase {
    var app: XCUIApplication!
    var mainTab: MainTabPage!

    override func setUp() {
        super.setUp()
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchWithOnboardingComplete()
        mainTab = MainTabPage(app: app)
    }

    override func tearDown() {
        app = nil
        mainTab = nil
        super.tearDown()
    }

    // MARK: - P0: タブナビゲーション

    func testTabNavigation() {
        // メインタブが表示される
        XCTAssertTrue(mainTab.isDisplayed, "メインタブが表示されるべき")

        // 各タブに遷移
        mainTab.selectFavorites()
        XCTAssertTrue(mainTab.favoritesTab.isSelected, "お気に入りタブが選択されるべき")

        mainTab.selectProfile()
        XCTAssertTrue(mainTab.profileTab.isSelected, "プロファイルタブが選択されるべき")

        mainTab.selectSettings()
        XCTAssertTrue(mainTab.settingsTab.isSelected, "設定タブが選択されるべき")

        mainTab.selectAbout()
        XCTAssertTrue(mainTab.aboutTab.isSelected, "Aboutタブが選択されるべき")

        mainTab.selectTimeLimit()
        XCTAssertTrue(mainTab.timeLimitTab.isSelected, "タイムリミットタブが選択されるべき")
    }

    // MARK: - タブ初期表示テスト

    func testInitialTabIsTimeLimit() {
        XCTAssertTrue(mainTab.isDisplayed, "メインタブが表示されるべき")
        XCTAssertTrue(mainTab.timeLimitTab.isSelected, "初期タブはタイムリミットであるべき")
    }
}
