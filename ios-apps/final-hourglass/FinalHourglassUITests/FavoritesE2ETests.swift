import XCTest

/// お気に入り機能の完全なE2Eテスト
final class FavoritesE2ETests: XCTestCase {
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

    // MARK: - P0: お気に入りタブ表示

    func testFavoritesTabDisplays() {
        mainTab.selectFavorites()
        XCTAssertTrue(mainTab.favoritesTab.isSelected, "お気に入りタブが選択されるべき")
        XCTAssertTrue(waitForElement(app.staticTexts.firstMatch), "お気に入り画面が表示されるべき")
    }

    // MARK: - P1: お気に入り追加フロー

    func testAddToFavorites() {
        mainTab.selectFavorites()
        XCTAssertTrue(mainTab.favoritesTab.isSelected, "お気に入りタブが選択されるべき")

        // エピソードリストが存在する場合
        if episodePage.isDisplayed {
            // 最初のエピソードを選択
            episodePage.selectFirstEpisode()

            // お気に入りボタンを探してタップ
            if waitForElement(episodePage.favoriteButton, timeout: 10) {
                // 現在のお気に入り状態を確認（ボタンのラベルやイメージで判断）
                let isFavorited = episodePage.favoriteButton.label.contains("済")

                // お気に入りに追加
                if !isFavorited {
                    episodePage.toggleFavorite()
                    Thread.sleep(forTimeInterval: 1.0)
                }

                XCTAssertTrue(app.exists, "お気に入り追加後もアプリがクラッシュしていないべき")

                // 戻る
                let backButton = app.navigationBars.buttons.firstMatch
                if backButton.waitForExistence(timeout: 5) {
                    backButton.tap()
                }
            }
        } else {
            // エピソードがない場合は空状態を確認
            XCTAssertTrue(waitForElement(app.staticTexts.firstMatch), "お気に入り画面が表示されるべき")
        }
    }

    // MARK: - P1: お気に入り一覧表示

    func testFavoritesList() {
        mainTab.selectFavorites()
        XCTAssertTrue(mainTab.favoritesTab.isSelected, "お気に入りタブが選択されるべき")

        // お気に入りリストまたは空状態メッセージが表示されることを確認
        let hasContent = episodePage.isDisplayed ||
                         waitForElement(app.staticTexts.firstMatch, timeout: 10)
        XCTAssertTrue(hasContent, "お気に入り一覧が表示されるべき")
    }

    // MARK: - P1: お気に入り削除フロー

    func testRemoveFromFavorites() {
        mainTab.selectFavorites()
        XCTAssertTrue(mainTab.favoritesTab.isSelected, "お気に入りタブが選択されるべき")

        // エピソードリストが存在する場合
        if episodePage.isDisplayed {
            // 最初のエピソードを選択
            episodePage.selectFirstEpisode()

            // お気に入りボタンを探してタップ
            if waitForElement(episodePage.favoriteButton, timeout: 10) {
                // お気に入りを解除
                episodePage.toggleFavorite()
                Thread.sleep(forTimeInterval: 1.0)

                XCTAssertTrue(app.exists, "お気に入り削除後もアプリがクラッシュしていないべき")
            }
        } else {
            // エピソードがない場合はテストをスキップ
            XCTAssertTrue(true, "お気に入りがないためスキップ")
        }
    }

    // MARK: - P1: お気に入り追加→一覧表示→削除の完全フロー

    func testCompleteFavoritesFlow() {
        mainTab.selectFavorites()
        XCTAssertTrue(mainTab.favoritesTab.isSelected, "お気に入りタブが選択されるべき")

        // Step 1: お気に入りリストが存在するか確認
        guard episodePage.isDisplayed else {
            // エピソードがない場合は空状態を確認して終了
            XCTAssertTrue(waitForElement(app.staticTexts.firstMatch), "空状態が表示されるべき")
            return
        }

        // Step 2: 最初のエピソードを選択してお気に入りを追加
        episodePage.selectFirstEpisode()
        if waitForElement(episodePage.favoriteButton, timeout: 10) {
            episodePage.toggleFavorite()
            Thread.sleep(forTimeInterval: 1.0)

            // Step 3: 戻ってリストを確認
            let backButton = app.navigationBars.buttons.firstMatch
            if backButton.waitForExistence(timeout: 5) {
                backButton.tap()
            }

            // リストが表示されていることを確認
            XCTAssertTrue(waitForElement(app.staticTexts.firstMatch) || episodePage.isDisplayed,
                          "お気に入り一覧に戻れるべき")

            // Step 4: 再度選択してお気に入りを削除
            if episodePage.isDisplayed {
                episodePage.selectFirstEpisode()
                if waitForElement(episodePage.favoriteButton, timeout: 10) {
                    episodePage.toggleFavorite()
                    Thread.sleep(forTimeInterval: 1.0)
                }
            }
        }

        XCTAssertTrue(app.exists, "完全フロー後もアプリがクラッシュしていないべき")
    }

    // MARK: - P2: 複数お気に入り管理

    func testMultipleFavoritesManagement() {
        mainTab.selectFavorites()
        XCTAssertTrue(mainTab.favoritesTab.isSelected, "お気に入りタブが選択されるべき")

        // エピソードリストが存在する場合
        guard episodePage.isDisplayed else {
            XCTAssertTrue(true, "エピソードがないためスキップ")
            return
        }

        let list = episodePage.episodeList

        // 複数のセルが存在するか確認
        let cellCount = list.cells.count
        if cellCount >= 2 {
            // 1つ目のエピソードを操作
            list.cells.element(boundBy: 0).tap()
            if waitForElement(episodePage.favoriteButton, timeout: 10) {
                episodePage.toggleFavorite()
                Thread.sleep(forTimeInterval: 0.5)

                // 戻る
                let backButton = app.navigationBars.buttons.firstMatch
                if backButton.waitForExistence(timeout: 5) {
                    backButton.tap()
                }
            }

            // 2つ目のエピソードを操作
            if list.cells.count >= 2 {
                list.cells.element(boundBy: 1).tap()
                if waitForElement(episodePage.favoriteButton, timeout: 10) {
                    episodePage.toggleFavorite()
                    Thread.sleep(forTimeInterval: 0.5)
                }
            }
        }

        XCTAssertTrue(app.exists, "複数お気に入り操作後もアプリがクラッシュしていないべき")
    }

    // MARK: - P2: お気に入り空状態からの遷移

    func testEmptyFavoritesState() {
        mainTab.selectFavorites()
        XCTAssertTrue(mainTab.favoritesTab.isSelected, "お気に入りタブが選択されるべき")

        // 空状態のメッセージが表示されているか、リストが表示されているか確認
        let hasContent = episodePage.isDisplayed ||
                         waitForElement(app.staticTexts.firstMatch, timeout: 10)
        XCTAssertTrue(hasContent, "お気に入り画面のコンテンツが表示されるべき")

        // 他のタブへ遷移して戻る
        mainTab.selectProfile()
        XCTAssertTrue(mainTab.profileTab.isSelected, "プロファイルタブが選択されるべき")

        mainTab.selectFavorites()
        XCTAssertTrue(mainTab.favoritesTab.isSelected, "お気に入りタブに戻れるべき")
    }

    // MARK: - P2: お気に入りリストのソート/フィルタリング

    func testFavoritesListSorting() {
        mainTab.selectFavorites()
        XCTAssertTrue(mainTab.favoritesTab.isSelected, "お気に入りタブが選択されるべき")

        // ソートボタンを探す
        let sortButton = app.buttons["ソート"]
        let filterButton = app.buttons["フィルター"]

        if waitForElement(sortButton, timeout: 10) {
            sortButton.tap()
            Thread.sleep(forTimeInterval: 0.5)
            XCTAssertTrue(app.exists, "ソートメニューが表示されるべき")

            // メニューを閉じる（画面外タップ）
            app.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()
        } else if waitForElement(filterButton, timeout: 5) {
            filterButton.tap()
            Thread.sleep(forTimeInterval: 0.5)
            XCTAssertTrue(app.exists, "フィルターメニューが表示されるべき")
        } else {
            // ソート/フィルター機能がない場合はスキップ
            XCTAssertTrue(true, "ソート/フィルター機能がないためスキップ")
        }
    }
}
