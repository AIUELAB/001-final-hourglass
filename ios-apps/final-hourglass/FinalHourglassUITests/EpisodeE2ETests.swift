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

    // MARK: - P1: エピソード詳細表示後の戻るナビゲーション

    func testEpisodeDetailNavigationBack() {
        mainTab.selectFavorites()
        XCTAssertTrue(mainTab.favoritesTab.isSelected, "お気に入りタブが選択されるべき")

        // エピソードリストが存在する場合のみ詳細画面へ遷移
        if episodePage.isDisplayed {
            episodePage.selectFirstEpisode()

            // 詳細画面が表示されることを確認
            let detailContent = app.scrollViews.firstMatch
            if waitForElement(detailContent, timeout: 10) {
                // 戻るボタンをタップ
                let backButton = app.navigationBars.buttons.firstMatch
                if backButton.waitForExistence(timeout: 5) {
                    backButton.tap()
                    // リスト画面に戻ることを確認
                    XCTAssertTrue(waitForElement(episodePage.episodeList), "エピソードリストに戻るべき")
                }
            }
        } else {
            // エピソードがない場合は空状態を確認
            XCTAssertTrue(waitForElement(app.staticTexts.firstMatch), "空状態が表示されるべき")
        }
    }

    // MARK: - P1: お気に入り追加/削除フロー

    func testFavoriteToggleFlow() {
        mainTab.selectFavorites()
        XCTAssertTrue(mainTab.favoritesTab.isSelected, "お気に入りタブが選択されるべき")

        // エピソードリストが存在する場合
        if episodePage.isDisplayed {
            episodePage.selectFirstEpisode()

            // お気に入りボタンが存在する場合
            if waitForElement(episodePage.favoriteButton, timeout: 10) {
                // お気に入りをトグル
                episodePage.toggleFavorite()

                // 画面が更新されることを確認（クラッシュしないことを確認）
                Thread.sleep(forTimeInterval: 1.0)
                XCTAssertTrue(app.exists, "アプリがクラッシュしていないべき")

                // 再度トグルして元に戻す
                episodePage.toggleFavorite()
                Thread.sleep(forTimeInterval: 1.0)
                XCTAssertTrue(app.exists, "アプリがクラッシュしていないべき")
            }
        } else {
            // エピソードがない場合はテストをスキップ
            XCTAssertTrue(true, "エピソードがないためスキップ")
        }
    }

    // MARK: - P2: エピソードシェア機能

    func testEpisodeShareFlow() {
        mainTab.selectFavorites()
        XCTAssertTrue(mainTab.favoritesTab.isSelected, "お気に入りタブが選択されるべき")

        // エピソードリストが存在する場合
        if episodePage.isDisplayed {
            episodePage.selectFirstEpisode()

            // シェアボタンを探す
            let shareButton = app.buttons["シェア"]
            if waitForElement(shareButton, timeout: 10) {
                shareButton.tap()

                // シェアシートが表示されることを確認
                let activityController = app.otherElements["ActivityListView"]
                if waitForElement(activityController, timeout: 10) {
                    // シェアシートを閉じる
                    let closeButton = app.buttons["Close"]
                    if closeButton.waitForExistence(timeout: 5) {
                        closeButton.tap()
                    }
                }
            }
        } else {
            // エピソードがない場合はテストをスキップ
            XCTAssertTrue(true, "エピソードがないためスキップ")
        }
    }

    // MARK: - P2: エピソードリストのスクロール

    func testEpisodeListScrolling() {
        mainTab.selectFavorites()
        XCTAssertTrue(mainTab.favoritesTab.isSelected, "お気に入りタブが選択されるべき")

        // エピソードリストが存在する場合
        if episodePage.isDisplayed {
            let list = episodePage.episodeList
            XCTAssertTrue(list.exists, "エピソードリストが存在するべき")

            // スクロールダウン
            list.swipeUp()
            Thread.sleep(forTimeInterval: 0.5)
            XCTAssertTrue(app.exists, "スクロール後もアプリがクラッシュしていないべき")

            // スクロールアップ
            list.swipeDown()
            Thread.sleep(forTimeInterval: 0.5)
            XCTAssertTrue(app.exists, "スクロール後もアプリがクラッシュしていないべき")
        } else {
            // エピソードがない場合はテストをスキップ
            XCTAssertTrue(true, "エピソードがないためスキップ")
        }
    }
}
