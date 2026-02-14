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
        XCTAssertTrue(mainTab.isFavoritesSelected, "お気に入りタブが選択されるべき")

        mainTab.selectProfile()
        XCTAssertTrue(mainTab.isProfileSelected, "プロファイルタブが選択されるべき")

        mainTab.selectSettings()
        XCTAssertTrue(mainTab.isSettingsSelected, "設定タブが選択されるべき")

        mainTab.selectAbout()
        XCTAssertTrue(mainTab.isAboutSelected, "Aboutタブが選択されるべき")

        mainTab.selectTimeLimit()
        XCTAssertTrue(mainTab.isTimeLimitSelected, "タイムリミットタブが選択されるべき")
    }

    // MARK: - タブ初期表示テスト

    func testInitialTabIsTimeLimit() {
        XCTAssertTrue(mainTab.isDisplayed, "メインタブが表示されるべき")
        XCTAssertTrue(mainTab.isTimeLimitSelected, "初期タブはタイムリミットであるべき")
    }

}
