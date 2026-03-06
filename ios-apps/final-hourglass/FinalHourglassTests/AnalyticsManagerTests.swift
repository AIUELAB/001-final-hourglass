import XCTest
@testable import FinalHourglass

final class AnalyticsManagerTests: XCTestCase {

    // MARK: - Singleton

    func testSharedInstance() {
        let instance = AnalyticsManager.shared
        XCTAssertNotNil(instance)
        XCTAssertTrue(instance === AnalyticsManager.shared, "shared は常に同一インスタンスを返すこと")
    }

    // MARK: - Screen Tracking

    func testTrackScreenDoesNotCrash() {
        let sut = AnalyticsManager.shared
        sut.trackScreen("HomeScreen")
        sut.trackScreen("SettingsScreen", screenClass: "SettingsViewController")
    }

    // MARK: - Onboarding

    func testTrackOnboardingDoesNotCrash() {
        let sut = AnalyticsManager.shared
        sut.trackOnboardingStart()
        sut.trackOnboardingComplete()
    }

    // MARK: - Life Result

    func testTrackLifeResultDoesNotCrash() {
        let sut = AnalyticsManager.shared
        sut.trackLifeResultCalculation(lifeExpectancy: 80.5, currentAge: 30)
    }

    // MARK: - Settings

    func testTrackSettingsDoesNotCrash() {
        let sut = AnalyticsManager.shared
        sut.trackNotificationSettingChange(enabled: true)
        sut.trackReminderSettingChange(enabled: true, time: Date())
        sut.trackReminderSettingChange(enabled: false)
        sut.trackSettingChange(settingName: "theme", value: "dark")
        sut.trackDataReset()

        let user = UserModel()
        sut.setUserProperties(userModel: user)
    }

    // MARK: - Lifecycle

    func testTrackLifecycleDoesNotCrash() {
        let sut = AnalyticsManager.shared
        sut.trackAppLaunch()
        sut.trackSessionDuration(duration: 120.0)
        sut.trackDailyActive()
        sut.trackStreakDays(7)
        sut.trackShare(method: "clipboard")
    }

    // MARK: - Thread Safety Tests
    // TSan 有効スキーム (FinalHourglass-TSan) + ios-tsan.yml で CI 実行

    func testConfigure_concurrentCalls_doesNotCrash() {
        let sut = AnalyticsManager.shared
        DispatchQueue.concurrentPerform(iterations: 100) { _ in
            sut.configure()
        }
        // テスト環境では Info.plist に APP_ID がないため stub モードの early return パスを通過。
        // NSLock のストレステストとしてクラッシュなく完走することを検証
    }

    func testGuardConfigured_concurrentAccess_doesNotCrash() {
        let sut = AnalyticsManager.shared
        DispatchQueue.concurrentPerform(iterations: 100) { _ in
            sut.trackScreen("ConcurrentScreen")
        }
        // guardConfigured() 内の NSLock が並行アクセスで安全に動作することを検証
    }

    func testSetUserProperties_concurrentCalls_doesNotCrash() {
        let sut = AnalyticsManager.shared
        DispatchQueue.concurrentPerform(iterations: 100) { _ in
            let user = UserModel()
            sut.setUserProperties(userModel: user)
        }
        // UserDefaults への並行書き込みがクラッシュしないことを検証
    }
}
