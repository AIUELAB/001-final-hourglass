import XCTest

final class OnboardingE2ETests: XCTestCase {
    var app: XCUIApplication!
    var onboardingPage: OnboardingPage!

    override func setUp() {
        super.setUp()
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchForTesting()
        onboardingPage = OnboardingPage(app: app)
    }

    override func tearDown() {
        app = nil
        onboardingPage = nil
        super.tearDown()
    }

    // MARK: - P0: オンボーディング完走テスト

    func testOnboardingFullFlow() {
        // 扉ページが表示されている
        XCTAssertTrue(onboardingPage.openDoorButtonExists,
                       "扉を開くボタンが表示されるべき")

        // 全ステップを通過
        onboardingPage.completeAllSteps()

        // メインタブが表示される
        let mainTab = MainTabPage(app: app)
        XCTAssertTrue(mainTab.isDisplayed, "オンボーディング完了後にメインタブが表示されるべき")
    }

    // MARK: - 扉ページ表示テスト

    func testDoorPageDisplaysCorrectly() {
        // 扉を開くボタンが存在する
        XCTAssertTrue(onboardingPage.openDoorButtonExists,
                       "扉を開くボタンが表示されるべき")

        // アプリタイトルが表示されている
        let title = app.staticTexts["最期の砂時計"]
        XCTAssertTrue(waitForElement(title, timeout: 30), "タイトルが表示されるべき")
    }

    // MARK: - 扉を開くとStep 1に遷移

    func testOpenDoorNavigatesToBirthday() {
        // まず扉を開くボタンが存在することを確認
        guard onboardingPage.openDoorButtonExists else {
            XCTFail("扉を開くボタンが見つかりません")
            return
        }

        onboardingPage.openDoor()

        // 生年月日ステップに遷移（「生年月日を刻む」または「生年月日」を含むテキストを検索）
        let birthdayText = app.staticTexts.matching(
            NSPredicate(format: "label CONTAINS '生年月日'")
        ).firstMatch
        XCTAssertTrue(waitForElement(birthdayText, timeout: 30),
                       "扉を開いた後、生年月日入力が表示されるべき")
    }
}
