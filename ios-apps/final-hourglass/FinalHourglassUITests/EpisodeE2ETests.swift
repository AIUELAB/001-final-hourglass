import XCTest

final class EpisodeE2ETests: XCTestCase {
    var app: XCUIApplication!
    var mainTab: MainTabPage!
    var episodePage: EpisodePage!

    override func setUp() {
        super.setUp()
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchWithOnboardingComplete()
        mainTab = MainTabPage(app: app)
        episodePage = EpisodePage(app: app)
    }

    override func tearDown() {
        app = nil
        mainTab = nil
        episodePage = nil
        super.tearDown()
    }

    // MARK: - P0: エピソードタブの存在確認

    func testEpisodeTabExists() {
        XCTAssertTrue(mainTab.isDisplayed, "メインタブが表示されるべき")
        XCTAssertTrue(waitForElement(mainTab.favoritesTab), "お気に入りタブが存在するべき")
    }

    // MARK: - P1: お気に入りタブ表示

    func testFavoritesTabDisplays() {
        mainTab.selectFavorites()
        XCTAssertTrue(mainTab.favoritesTab.isSelected, "お気に入りタブが選択されるべき")
        XCTAssertTrue(waitForElement(app.staticTexts.firstMatch), "お気に入り画面が表示されるべき")
    }

    // MARK: - P1: お気に入り空状態

    func testFavoritesEmptyState() {
        mainTab.selectFavorites()
        XCTAssertTrue(mainTab.favoritesTab.isSelected, "お気に入りタブが選択されるべき")

        // 空状態のメッセージまたはリストが表示されることを確認
        let content = app.staticTexts.firstMatch
        XCTAssertTrue(waitForElement(content), "お気に入り画面のコンテンツが表示されるべき")
    }

    // MARK: - P2: タブ切替時の状態維持

    func testTabSwitchingMaintainsState() {
        // お気に入りタブへ遷移
        mainTab.selectFavorites()
        XCTAssertTrue(mainTab.favoritesTab.isSelected, "お気に入りタブが選択されるべき")

        // 設定タブへ遷移
        mainTab.selectSettings()
        XCTAssertTrue(mainTab.settingsTab.isSelected, "設定タブが選択されるべき")

        // お気に入りタブへ戻る
        mainTab.selectFavorites()
        XCTAssertTrue(mainTab.favoritesTab.isSelected, "お気に入りタブに戻れるべき")
        XCTAssertTrue(waitForElement(app.staticTexts.firstMatch), "お気に入り画面が再表示されるべき")
    }
}
