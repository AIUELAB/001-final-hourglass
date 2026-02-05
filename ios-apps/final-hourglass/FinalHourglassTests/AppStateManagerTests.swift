import XCTest
@testable import FinalHourglass

final class AppStateManagerTests: XCTestCase {

    // MARK: - Setup / Teardown

    override func setUp() {
        super.setUp()
        // UserDefaultsをクリア
        clearUserDefaults()
    }

    override func tearDown() {
        // クリーンアップ
        clearUserDefaults()
        super.tearDown()
    }

    private func clearUserDefaults() {
        if let bundleId = Bundle.main.bundleIdentifier {
            UserDefaults.standard.removePersistentDomain(forName: bundleId)
        }
        UserDefaults.standard.synchronize()
    }

    // MARK: - A. 初期化・状態管理テスト

    /// テスト1: 初期値の検証（isFirstLaunch=true, hasCompletedOnboarding=false等）
    func testDefaultValues() {
        // UserDefaultsが空の状態で新しいインスタンスを作成
        let appState = AppStateManager()

        // 初回起動フラグはtrue（hasLaunchedBeforeがfalseのため）
        XCTAssertTrue(appState.isFirstLaunch, "初期値ではisFirstLaunch=trueであるべき")

        // オンボーディング未完了
        XCTAssertFalse(appState.hasCompletedOnboarding, "初期値ではhasCompletedOnboarding=falseであるべき")

        // 通知は無効（デフォルト）
        XCTAssertFalse(appState.notificationsEnabled, "初期値ではnotificationsEnabled=falseであるべき")

        // リマインダーはデフォルトでON
        XCTAssertTrue(appState.reminderEnabled, "初期値ではreminderEnabled=trueであるべき")

        // リセット中フラグは初期状態でfalse
        XCTAssertFalse(appState.isResetting, "初期値ではisResetting=falseであるべき")

        // リマインダー時刻のデフォルトは8:30
        let calendar = Calendar.current
        let components = calendar.dateComponents([.hour, .minute], from: appState.reminderTime)
        XCTAssertEqual(components.hour, 8, "デフォルトリマインダー時刻は8時であるべき")
        XCTAssertEqual(components.minute, 30, "デフォルトリマインダー時刻は30分であるべき")
    }

    /// テスト2: プロパティ変更がUserDefaultsに保存される
    func testStatePersistedToUserDefaults() {
        let appState = AppStateManager()
        let defaults = UserDefaults.standard

        // isFirstLaunchを変更
        appState.isFirstLaunch = false
        // didSet内で hasLaunchedBefore = !isFirstLaunch = true を保存
        XCTAssertTrue(defaults.bool(forKey: "hasLaunchedBefore"), "isFirstLaunch=falseでhasLaunchedBefore=trueが保存されるべき")

        // hasCompletedOnboardingを変更
        appState.hasCompletedOnboarding = true
        XCTAssertTrue(defaults.bool(forKey: "hasCompletedOnboarding"), "hasCompletedOnboardingの変更が保存されるべき")

        // notificationsEnabledを変更
        appState.notificationsEnabled = true
        XCTAssertTrue(defaults.bool(forKey: "notificationsEnabled"), "notificationsEnabledの変更が保存されるべき")

        // reminderEnabledを変更
        appState.reminderEnabled = false
        XCTAssertFalse(defaults.bool(forKey: "reminderEnabled"), "reminderEnabledの変更が保存されるべき")

        // reminderTimeを変更
        let testDate = Date(timeIntervalSince1970: 3600) // 任意の日時
        appState.reminderTime = testDate
        if let savedTime = defaults.object(forKey: "reminderTime") as? Date {
            XCTAssertEqual(savedTime.timeIntervalSince1970, testDate.timeIntervalSince1970, accuracy: 1.0, "reminderTimeの変更が保存されるべき")
        } else {
            XCTFail("reminderTimeがUserDefaultsに保存されていない")
        }
    }

    /// テスト3: UserDefaultsに保存された値が正しく読み込まれる
    func testLoadFromUserDefaults() {
        let defaults = UserDefaults.standard

        // UserDefaultsに事前に値を設定
        defaults.set(true, forKey: "hasLaunchedBefore")
        defaults.set(true, forKey: "hasCompletedOnboarding")
        defaults.set(true, forKey: "notificationsEnabled")
        defaults.set(false, forKey: "reminderEnabled")

        // カスタムリマインダー時刻を設定
        let calendar = Calendar.current
        let customComponents = DateComponents(hour: 9, minute: 45)
        let customTime = calendar.date(from: customComponents)!
        defaults.set(customTime, forKey: "reminderTime")

        defaults.synchronize()

        // 新しいインスタンスで読み込み
        let appState = AppStateManager()

        // hasLaunchedBefore=trueなので、isFirstLaunch=false
        XCTAssertFalse(appState.isFirstLaunch, "hasLaunchedBefore=trueの場合、isFirstLaunch=falseであるべき")
        XCTAssertTrue(appState.hasCompletedOnboarding, "保存されたhasCompletedOnboardingが読み込まれるべき")
        XCTAssertTrue(appState.notificationsEnabled, "保存されたnotificationsEnabledが読み込まれるべき")
        XCTAssertFalse(appState.reminderEnabled, "保存されたreminderEnabledが読み込まれるべき")

        // リマインダー時刻の確認
        let loadedComponents = calendar.dateComponents([.hour, .minute], from: appState.reminderTime)
        XCTAssertEqual(loadedComponents.hour, 9, "保存されたリマインダー時刻（時）が読み込まれるべき")
        XCTAssertEqual(loadedComponents.minute, 45, "保存されたリマインダー時刻（分）が読み込まれるべき")
    }

    // MARK: - B. 年齢計算テスト

    /// テスト4: 正確な年齢計算
    func testCalculateUserAgeWithValidBirthDate() {
        let defaults = UserDefaults.standard
        let calendar = Calendar.current
        let currentYear = calendar.component(.year, from: Date())

        // 30年前の1月1日生まれに設定（確実に誕生日を過ぎている）
        defaults.set(currentYear - 30, forKey: "birthYear")
        defaults.set(1, forKey: "birthMonth")
        defaults.set(1, forKey: "birthDay")
        defaults.synchronize()

        let appState = AppStateManager()
        let age = appState.calculateUserAge()

        XCTAssertEqual(age, 30, "1月1日生まれの場合、正確な年齢が計算されるべき")
    }

    /// テスト5: UserDefaultsに値がない場合デフォルト30歳
    func testCalculateUserAgeWithDefaultValues() {
        // UserDefaultsには何も設定しない（clearUserDefaultsで空になっている）
        let appState = AppStateManager()
        let age = appState.calculateUserAge()

        XCTAssertEqual(age, 30, "生年月日が設定されていない場合、デフォルトの30歳を返すべき")
    }

    /// テスト6: 閏年2月29日生まれのエッジケース
    func testCalculateUserAgeLeapYear() {
        let defaults = UserDefaults.standard
        let calendar = Calendar.current

        // 2000年（閏年）の2月29日生まれ
        defaults.set(2000, forKey: "birthYear")
        defaults.set(2, forKey: "birthMonth")
        defaults.set(29, forKey: "birthDay")
        defaults.synchronize()

        let appState = AppStateManager()
        let age = appState.calculateUserAge()

        // 現在の日付に基づいて期待される年齢を計算
        let now = Date()
        let currentYear = calendar.component(.year, from: now)
        let currentMonth = calendar.component(.month, from: now)

        var expectedAge = currentYear - 2000
        // 誕生日（2/29）がまだ来ていない場合は1歳引く
        // 3月1日以降は誕生日を過ぎたとみなす
        if currentMonth < 3 {
            // 1月または2月の場合、誕生日前
            expectedAge -= 1
        }

        XCTAssertEqual(age, expectedAge, "閏年2月29日生まれの年齢計算が正しいべき")
    }

    // MARK: - C. リセット処理テスト

    /// テスト7: 全状態が初期値に戻る
    func testResetAppClearsAllState() {
        let defaults = UserDefaults.standard

        // 事前に状態を変更
        defaults.set(true, forKey: "hasLaunchedBefore")
        defaults.set(true, forKey: "hasCompletedOnboarding")
        defaults.set(true, forKey: "notificationsEnabled")
        defaults.set(false, forKey: "reminderEnabled")
        defaults.set(1985, forKey: "birthYear")
        defaults.set(7, forKey: "birthMonth")
        defaults.set(15, forKey: "birthDay")
        defaults.synchronize()

        let appState = AppStateManager()

        // 状態が読み込まれていることを確認
        XCTAssertFalse(appState.isFirstLaunch)
        XCTAssertTrue(appState.hasCompletedOnboarding)

        // リセット実行
        appState.resetApp()

        // 状態が初期値に戻っている
        XCTAssertTrue(appState.isFirstLaunch, "リセット後isFirstLaunch=trueであるべき")
        XCTAssertFalse(appState.hasCompletedOnboarding, "リセット後hasCompletedOnboarding=falseであるべき")
        XCTAssertFalse(appState.notificationsEnabled, "リセット後notificationsEnabled=falseであるべき")
        XCTAssertTrue(appState.reminderEnabled, "リセット後reminderEnabled=true（デフォルト）であるべき")

        // リマインダー時刻がデフォルト（8:30）に戻っている
        let calendar = Calendar.current
        let components = calendar.dateComponents([.hour, .minute], from: appState.reminderTime)
        XCTAssertEqual(components.hour, 8, "リセット後リマインダー時刻は8時であるべき")
        XCTAssertEqual(components.minute, 30, "リセット後リマインダー時刻は30分であるべき")
    }

    /// テスト8: isResettingフラグが正しく動作
    func testResetAppSetsIsResettingFlag() {
        let appState = AppStateManager()

        // リセット前はfalse
        XCTAssertFalse(appState.isResetting, "リセット前はisResetting=falseであるべき")

        // リセット実行
        appState.resetApp()

        // リセット直後はtrue
        XCTAssertTrue(appState.isResetting, "リセット直後はisResetting=trueであるべき")

        // 1秒後にfalseに戻ることを確認
        let expectation = self.expectation(description: "isResettingがfalseに戻る")
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
            XCTAssertFalse(appState.isResetting, "1秒後にisResetting=falseに戻るべき")
            expectation.fulfill()
        }

        waitForExpectations(timeout: 3.0)
    }

    // MARK: - D. セッション追跡テスト

    /// テスト9: 同日再起動でストリーク維持
    func testUsageStreakSameDayKeeps() {
        let defaults = UserDefaults.standard
        let calendar = Calendar.current
        let today = calendar.startOfDay(for: Date())

        // 今日既にアクティブだった状態を模擬
        defaults.set(today, forKey: "lastActiveDate")
        defaults.set(5, forKey: "usageStreak")
        defaults.synchronize()

        // 新しいインスタンスを作成（startSessionが呼ばれる）
        _ = AppStateManager()

        // 同日なのでストリークは変化しない
        let streak = defaults.integer(forKey: "usageStreak")
        XCTAssertEqual(streak, 5, "同日再起動ではストリークが維持されるべき")
    }

    /// テスト10: 翌日起動でストリーク+1
    func testUsageStreakNewDayIncrements() {
        let defaults = UserDefaults.standard
        let calendar = Calendar.current
        let today = calendar.startOfDay(for: Date())

        // 昨日アクティブだった状態を模擬
        guard let yesterday = calendar.date(byAdding: .day, value: -1, to: today) else {
            XCTFail("昨日の日付を計算できなかった")
            return
        }
        defaults.set(yesterday, forKey: "lastActiveDate")
        defaults.set(5, forKey: "usageStreak")
        defaults.synchronize()

        // 新しいインスタンスを作成（startSession → trackDailyActiveUserが呼ばれる）
        _ = AppStateManager()

        // 翌日なのでストリークが+1される
        let streak = defaults.integer(forKey: "usageStreak")
        XCTAssertEqual(streak, 6, "翌日起動ではストリークが+1されるべき")

        // lastActiveDateが今日に更新されている
        if let lastActive = defaults.object(forKey: "lastActiveDate") as? Date {
            XCTAssertTrue(calendar.isDate(lastActive, inSameDayAs: today), "lastActiveDateが今日に更新されるべき")
        } else {
            XCTFail("lastActiveDateが設定されていない")
        }
    }
}
