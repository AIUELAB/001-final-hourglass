import XCTest

/// fastlane snapshot用スクリーンショット撮影テスト
///
/// App Store Connect提出用の各画面スクリーンショットを自動生成する。
/// 使用方法: `bundle exec fastlane screenshots`
///
/// 注意: SnapshotHelper.swift をUITestターゲットに追加する必要がある
/// （`bundle exec fastlane snapshot init` で生成 → Xcodeで追加）
final class SnapshotUITests: XCTestCase {

    private var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = true
        app = XCUIApplication()
        setupSnapshot(app)
    }

    override func tearDownWithError() throws {
        app = nil
        try super.tearDownWithError()
    }

    // MARK: - Helpers

    private func launchForSnapshot() {
        app.launchArguments = ["-UITest_ResetState", "-UITest_DisableAnimations"]
        app.launch()
        _ = app.wait(for: .runningForeground, timeout: 10)
        Thread.sleep(forTimeInterval: 2.0)
    }

    private func launchWithOnboardingSkipped() {
        app.launchArguments = [
            "-UITest_ResetState",
            "-UITest_SkipOnboarding",
            "-UITest_DisableAnimations"
        ]
        app.launch()
        _ = app.wait(for: .runningForeground, timeout: 10)
        Thread.sleep(forTimeInterval: 2.0)
    }

    // MARK: - Screenshot Tests

    func test01_Onboarding() {
        launchForSnapshot()
        snapshot("01_Onboarding")
    }

    func test02_TimeLimit() {
        launchWithOnboardingSkipped()
        let mainTab = MainTabPage(app: app)
        XCTAssertTrue(mainTab.isDisplayed, "タブバーが表示されていること")
        mainTab.selectTimeLimit()
        Thread.sleep(forTimeInterval: 1.0)
        snapshot("02_TimeLimit")
    }

    func test03_Favorites() {
        launchWithOnboardingSkipped()
        let mainTab = MainTabPage(app: app)
        XCTAssertTrue(mainTab.isDisplayed, "タブバーが表示されていること")
        mainTab.selectFavorites()
        Thread.sleep(forTimeInterval: 1.0)
        snapshot("03_Favorites")
    }

    func test04_Profile() {
        launchWithOnboardingSkipped()
        let mainTab = MainTabPage(app: app)
        XCTAssertTrue(mainTab.isDisplayed, "タブバーが表示されていること")
        mainTab.selectProfile()
        Thread.sleep(forTimeInterval: 1.0)
        snapshot("04_Profile")
    }

    func test05_Settings() {
        launchWithOnboardingSkipped()
        let mainTab = MainTabPage(app: app)
        XCTAssertTrue(mainTab.isDisplayed, "タブバーが表示されていること")
        mainTab.selectSettings()
        Thread.sleep(forTimeInterval: 1.0)
        snapshot("05_Settings")
    }
}
