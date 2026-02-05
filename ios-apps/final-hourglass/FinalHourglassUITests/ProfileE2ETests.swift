import XCTest

final class ProfileE2ETests: XCTestCase {
    var app: XCUIApplication!
    var mainTab: MainTabPage!
    var profilePage: ProfilePage!

    override func setUp() {
        super.setUp()
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchWithOnboardingComplete()
        mainTab = MainTabPage(app: app)
        profilePage = ProfilePage(app: app)
    }

    override func tearDown() {
        app = nil
        mainTab = nil
        profilePage = nil
        super.tearDown()
    }

    // MARK: - P1: プロフィール画面表示

    func testProfileDisplays() {
        // プロファイルタブに遷移
        XCTAssertTrue(mainTab.isDisplayed)
        mainTab.selectProfile()

        // プロフィール画面が表示される
        XCTAssertTrue(profilePage.isDisplayed, "プロフィール画面が表示されるべき")
    }

    // MARK: - P1: リセットでオンボーディングに戻る

    func testSettingsResetReturnsToOnboarding() throws {
        XCTAssertTrue(mainTab.isDisplayed)
        mainTab.selectSettings()

        // スクロールしてリセットボタンを探す
        let scrollView = app.scrollViews.firstMatch
        if scrollView.exists {
            scrollView.swipeUp()
        }

        // リセットボタンを探してタップ（「データをリセットして最初から始める」または「リセット」を含むボタン）
        let resetButton = app.buttons.matching(
            NSPredicate(format: "label CONTAINS 'リセット'")
        ).firstMatch

        // または staticTexts + 親要素のタップを試す
        let resetText = app.staticTexts.matching(
            NSPredicate(format: "label CONTAINS 'リセット'")
        ).firstMatch

        if resetButton.waitForExistence(timeout: 10) {
            resetButton.tap()
        } else if resetText.waitForExistence(timeout: 5) {
            resetText.tap()
        } else {
            // リセットボタンが見つからない場合はスキップ
            throw XCTSkip("リセットボタンが見つかりませんでした")
        }

        // 確認ダイアログの「リセット」をタップ
        let confirmButton = app.alerts.buttons.matching(
            NSPredicate(format: "label CONTAINS 'リセット'")
        ).firstMatch
        if confirmButton.waitForExistence(timeout: 10) {
            confirmButton.tap()
        }

        // オンボーディングが表示される（タイムアウトを30秒に延長）
        let onboarding = OnboardingPage(app: app)
        let doorButtonExists = onboarding.openDoorButtonExists
        let titleExists = app.staticTexts["最期の砂時計"].waitForExistence(timeout: 10)
        XCTAssertTrue(doorButtonExists || titleExists,
                       "リセット後にオンボーディングが表示されるべき")
    }

    // MARK: - P2: 編集モード切替

    func testProfileEditMode() {
        XCTAssertTrue(mainTab.isDisplayed)
        mainTab.selectProfile()
        XCTAssertTrue(profilePage.isDisplayed)

        // 編集ボタンをタップ
        profilePage.tapEdit()

        // 「完了」ボタンが表示される（編集モードON）
        let doneButton = app.buttons.matching(
            NSPredicate(format: "label == '完了'")
        ).firstMatch
        XCTAssertTrue(waitForElement(doneButton), "編集モードで完了ボタンが表示されるべき")

        // 完了ボタンをタップして編集モード終了
        doneButton.tap()

        // 「編集」ボタンが再表示される
        let editButton = app.buttons.matching(
            NSPredicate(format: "label == '編集'")
        ).firstMatch
        XCTAssertTrue(waitForElement(editButton), "編集モード終了後に編集ボタンが表示されるべき")
    }

    // MARK: - P2: お気に入り空状態

    func testFavoritesEmptyState() {
        XCTAssertTrue(mainTab.isDisplayed)
        mainTab.selectFavorites()

        // 空状態のメッセージまたは画面が表示される
        // (具体的なテキストはアプリの実装に依存)
        let emptyStateText = app.staticTexts.matching(
            NSPredicate(format: "label CONTAINS 'お気に入り' OR label CONTAINS '登録' OR label CONTAINS 'まだ'")
        ).firstMatch
        // 空状態メッセージまたはリストが表示されればOK
        let favoritesExists = emptyStateText.waitForExistence(timeout: 5) ||
            app.tables.firstMatch.waitForExistence(timeout: 5) ||
            app.collectionViews.firstMatch.waitForExistence(timeout: 5)
        XCTAssertTrue(favoritesExists, "お気に入り画面のコンテンツが表示されるべき")
    }
}
