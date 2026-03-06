import XCTest
@testable import FinalHourglass

final class ReviewManagerTests: XCTestCase {

    // MARK: - Properties

    private var sut: ReviewManager!
    private var testDefaults: UserDefaults!

    // MARK: - Lifecycle

    override func setUp() {
        super.setUp()
        testDefaults = UserDefaults(suiteName: "ReviewManagerTests")!
        testDefaults.removePersistentDomain(forName: "ReviewManagerTests")
        sut = ReviewManager(userDefaults: testDefaults)
    }

    override func tearDown() {
        testDefaults.removePersistentDomain(forName: "ReviewManagerTests")
        testDefaults = nil
        sut = nil
        super.tearDown()
    }

    // MARK: - canRequestReview Tests

    @MainActor
    func testCanRequestReview_noInstallDate_returnsFalse() {
        // install date is auto-set in init, so remove it
        testDefaults.removeObject(forKey: "review_app_install_date")
        let manager = ReviewManager(userDefaults: testDefaults)
        XCTAssertFalse(manager.canRequestReview())
    }

    @MainActor
    func testCanRequestReview_recentInstall_returnsFalse() {
        // install date was just set (today) in setUp -> less than 7 days
        testDefaults.set(5, forKey: "review_sessions_count")
        XCTAssertFalse(sut.canRequestReview())
    }

    @MainActor
    func testCanRequestReview_sufficientDaysButFewSessions_returnsFalse() {
        let eightDaysAgo = Calendar.current.date(byAdding: .day, value: -8, to: Date())!
        testDefaults.set(eightDaysAgo, forKey: "review_app_install_date")
        testDefaults.set(3, forKey: "review_sessions_count") // less than 5
        let manager = ReviewManager(userDefaults: testDefaults)
        XCTAssertFalse(manager.canRequestReview())
    }

    @MainActor
    func testCanRequestReview_allConditionsMet_returnsTrue() {
        let tenDaysAgo = Calendar.current.date(byAdding: .day, value: -10, to: Date())!
        testDefaults.set(tenDaysAgo, forKey: "review_app_install_date")
        testDefaults.set(6, forKey: "review_sessions_count")
        // No previous request, no yearly count
        let manager = ReviewManager(userDefaults: testDefaults)
        XCTAssertTrue(manager.canRequestReview())
    }

    // MARK: - Cooldown 90 Days Tests

    @MainActor
    func testCanRequestReview_withinCooldown_returnsFalse() {
        let tenDaysAgo = Calendar.current.date(byAdding: .day, value: -10, to: Date())!
        testDefaults.set(tenDaysAgo, forKey: "review_app_install_date")
        testDefaults.set(6, forKey: "review_sessions_count")

        // Last request was 30 days ago (within 90 day cooldown)
        let thirtyDaysAgo = Calendar.current.date(byAdding: .day, value: -30, to: Date())!
        testDefaults.set(thirtyDaysAgo, forKey: "review_last_request_date")

        let manager = ReviewManager(userDefaults: testDefaults)
        XCTAssertFalse(manager.canRequestReview())
    }

    @MainActor
    func testCanRequestReview_afterCooldown_returnsTrue() {
        let hundredDaysAgo = Calendar.current.date(byAdding: .day, value: -100, to: Date())!
        testDefaults.set(hundredDaysAgo, forKey: "review_app_install_date")
        testDefaults.set(10, forKey: "review_sessions_count")

        // Last request was 91 days ago (past cooldown)
        let ninetyOneDaysAgo = Calendar.current.date(byAdding: .day, value: -91, to: Date())!
        testDefaults.set(ninetyOneDaysAgo, forKey: "review_last_request_date")

        let manager = ReviewManager(userDefaults: testDefaults)
        XCTAssertTrue(manager.canRequestReview())
    }

    // MARK: - Yearly Limit Tests

    @MainActor
    func testCanRequestReview_yearlyLimitReached_returnsFalse() {
        let tenDaysAgo = Calendar.current.date(byAdding: .day, value: -10, to: Date())!
        testDefaults.set(tenDaysAgo, forKey: "review_app_install_date")
        testDefaults.set(6, forKey: "review_sessions_count")

        // Set yearly count to 3 (maximum)
        let currentYear = Calendar.current.component(.year, from: Date())
        testDefaults.set(currentYear, forKey: "review_request_year")
        testDefaults.set(3, forKey: "review_request_count_current_year")

        let manager = ReviewManager(userDefaults: testDefaults)
        XCTAssertFalse(manager.canRequestReview())
    }

    @MainActor
    func testCanRequestReview_yearlyLimitNotReached_returnsTrue() {
        let tenDaysAgo = Calendar.current.date(byAdding: .day, value: -10, to: Date())!
        testDefaults.set(tenDaysAgo, forKey: "review_app_install_date")
        testDefaults.set(6, forKey: "review_sessions_count")

        let currentYear = Calendar.current.component(.year, from: Date())
        testDefaults.set(currentYear, forKey: "review_request_year")
        testDefaults.set(2, forKey: "review_request_count_current_year")

        let manager = ReviewManager(userDefaults: testDefaults)
        XCTAssertTrue(manager.canRequestReview())
    }

    // MARK: - recordEpisodeView Tests

    @MainActor
    func testRecordEpisodeView_incrementsCount() {
        sut.recordEpisodeView()
        XCTAssertEqual(testDefaults.integer(forKey: "review_episode_view_count"), 1)

        sut.recordEpisodeView()
        XCTAssertEqual(testDefaults.integer(forKey: "review_episode_view_count"), 2)
    }

    @MainActor
    func testRecordEpisodeView_triggersAtThreshold() {
        // Set conditions so canRequestReview is true
        let tenDaysAgo = Calendar.current.date(byAdding: .day, value: -10, to: Date())!
        testDefaults.set(tenDaysAgo, forKey: "review_app_install_date")
        testDefaults.set(6, forKey: "review_sessions_count")
        // Re-init with the updated defaults
        sut = ReviewManager(userDefaults: testDefaults)

        // Record 9 views
        testDefaults.set(9, forKey: "review_episode_view_count")

        // 10th view should trigger prompt
        sut.recordEpisodeView()
        XCTAssertEqual(testDefaults.integer(forKey: "review_episode_view_count"), 10)
        XCTAssertTrue(sut.showPrePrompt)
    }

    @MainActor
    func testRecordEpisodeView_doesNotTriggerBelowThreshold() {
        testDefaults.set(7, forKey: "review_episode_view_count")
        sut.recordEpisodeView()
        XCTAssertFalse(sut.showPrePrompt)
    }

    @MainActor
    func testRecordEpisodeView_retriggersAtMultipleOfThreshold() {
        // Set conditions so canRequestReview is true
        let tenDaysAgo = Calendar.current.date(byAdding: .day, value: -10, to: Date())!
        testDefaults.set(tenDaysAgo, forKey: "review_app_install_date")
        testDefaults.set(6, forKey: "review_sessions_count")
        sut = ReviewManager(userDefaults: testDefaults)

        // Set to 19 views (next will be 20 = 2nd multiple of 10)
        testDefaults.set(19, forKey: "review_episode_view_count")

        sut.recordEpisodeView()
        XCTAssertEqual(testDefaults.integer(forKey: "review_episode_view_count"), 20)
        XCTAssertTrue(sut.showPrePrompt)
    }

    // MARK: - recordSession Tests

    @MainActor
    func testRecordSession_incrementsCount() {
        sut.recordSession()
        let count = testDefaults.integer(forKey: "review_sessions_count")
        // init already does not call recordSession, so first call = 1
        XCTAssertEqual(count, 1)

        sut.recordSession()
        XCTAssertEqual(testDefaults.integer(forKey: "review_sessions_count"), 2)
    }

    // MARK: - checkAndPromptReview Tests

    @MainActor
    func testCheckAndPromptReview_conditionsNotMet_doesNotShowPrompt() {
        // Fresh install, conditions not met
        sut.checkAndPromptReview(trigger: .manual)
        XCTAssertFalse(sut.showPrePrompt)
    }

    @MainActor
    func testCheckAndPromptReview_conditionsMet_showsPrompt() {
        let tenDaysAgo = Calendar.current.date(byAdding: .day, value: -10, to: Date())!
        testDefaults.set(tenDaysAgo, forKey: "review_app_install_date")
        testDefaults.set(6, forKey: "review_sessions_count")
        sut = ReviewManager(userDefaults: testDefaults)

        sut.checkAndPromptReview(trigger: .manual)
        XCTAssertTrue(sut.showPrePrompt)
        XCTAssertEqual(sut.currentTrigger, .manual)
    }

    // MARK: - handlePrePromptResponse Tests

    @MainActor
    func testHandlePrePromptResponse_neutral_dismisses() {
        sut.showPrePrompt = true
        sut.handlePrePromptResponse(.neutral)
        XCTAssertFalse(sut.showPrePrompt)
        XCTAssertFalse(sut.showFeedbackForm)
    }

    @MainActor
    func testHandlePrePromptResponse_negative_showsFeedbackForm() {
        sut.showPrePrompt = true
        sut.handlePrePromptResponse(.negative)
        XCTAssertFalse(sut.showPrePrompt)
        XCTAssertTrue(sut.showFeedbackForm)
    }

    // MARK: - handlePrePromptResponse Positive Tests

    @MainActor
    func testHandlePrePromptResponse_positive_recordsRequest() {
        let tenDaysAgo = Calendar.current.date(byAdding: .day, value: -10, to: Date())!
        testDefaults.set(tenDaysAgo, forKey: "review_app_install_date")
        testDefaults.set(6, forKey: "review_sessions_count")
        sut = ReviewManager(userDefaults: testDefaults)

        sut.showPrePrompt = true
        sut.handlePrePromptResponse(.positive)

        XCTAssertFalse(sut.showPrePrompt)
        XCTAssertNotNil(testDefaults.object(forKey: "review_last_request_date"))
        XCTAssertEqual(testDefaults.integer(forKey: "review_request_count_current_year"), 1)
    }

    // MARK: - Cooldown Integration Tests

    @MainActor
    func testHandlePrePromptResponse_positive_activatesCooldown() {
        let tenDaysAgo = Calendar.current.date(byAdding: .day, value: -10, to: Date())!
        testDefaults.set(tenDaysAgo, forKey: "review_app_install_date")
        testDefaults.set(6, forKey: "review_sessions_count")
        sut = ReviewManager(userDefaults: testDefaults)

        XCTAssertTrue(sut.canRequestReview(), "Before recording, review should be requestable")

        sut.showPrePrompt = true
        sut.handlePrePromptResponse(.positive)

        XCTAssertFalse(sut.canRequestReview(), "After recording, cooldown should prevent review")
    }

    // MARK: - Yearly Reset Tests

    func testYearlyCountResetsOnNewYear() {
        // Simulate a request count from a previous year
        let lastYear = Calendar.current.component(.year, from: Date()) - 1
        testDefaults.set(lastYear, forKey: "review_request_year")
        testDefaults.set(3, forKey: "review_request_count_current_year")

        // Re-init triggers resetYearlyCountIfNeeded
        let manager = ReviewManager(userDefaults: testDefaults)
        _ = manager // Suppress unused warning

        let currentYear = Calendar.current.component(.year, from: Date())
        XCTAssertEqual(testDefaults.integer(forKey: "review_request_year"), currentYear)
        XCTAssertEqual(testDefaults.integer(forKey: "review_request_count_current_year"), 0)
    }

    @MainActor
    func testCanRequestReview_yearChangedAfterInit_resetsAndReturnsTrue() {
        let tenDaysAgo = Calendar.current.date(byAdding: .day, value: -10, to: Date())!
        testDefaults.set(tenDaysAgo, forKey: "review_app_install_date")
        testDefaults.set(6, forKey: "review_sessions_count")
        sut = ReviewManager(userDefaults: testDefaults)

        // init 後に前年の状態をシミュレート（年越し）
        let lastYear = Calendar.current.component(.year, from: Date()) - 1
        testDefaults.set(lastYear, forKey: "review_request_year")
        testDefaults.set(3, forKey: "review_request_count_current_year")

        // canRequestReview 内の resetYearlyCountIfNeeded でリセットされるべき
        XCTAssertTrue(sut.canRequestReview())
        XCTAssertEqual(testDefaults.integer(forKey: "review_request_count_current_year"), 0)
    }

    @MainActor
    func testHandlePrePromptResponse_positive_afterYearChange_resetsBeforeIncrement() {
        let tenDaysAgo = Calendar.current.date(byAdding: .day, value: -10, to: Date())!
        testDefaults.set(tenDaysAgo, forKey: "review_app_install_date")
        testDefaults.set(6, forKey: "review_sessions_count")
        sut = ReviewManager(userDefaults: testDefaults)

        // init でリセットされた後、再度前年状態をシミュレート
        let lastYear = Calendar.current.component(.year, from: Date()) - 1
        testDefaults.set(lastYear, forKey: "review_request_year")
        testDefaults.set(3, forKey: "review_request_count_current_year")

        sut.showPrePrompt = true
        sut.handlePrePromptResponse(.positive)

        // recordReviewRequest 内で resetYearlyCountIfNeeded → 0 にリセット → +1 = 1
        XCTAssertEqual(testDefaults.integer(forKey: "review_request_count_current_year"), 1)
        let currentYear = Calendar.current.component(.year, from: Date())
        XCTAssertEqual(testDefaults.integer(forKey: "review_request_year"), currentYear)
    }

    // MARK: - Install Date Initialization

    func testInstallDateSetOnFirstInit() {
        XCTAssertNotNil(testDefaults.object(forKey: "review_app_install_date"))
    }

    func testInstallDateNotOverwrittenOnSubsequentInit() {
        let originalDate = testDefaults.object(forKey: "review_app_install_date") as? Date
        // Re-init
        _ = ReviewManager(userDefaults: testDefaults)
        let dateAfterReinit = testDefaults.object(forKey: "review_app_install_date") as? Date
        XCTAssertEqual(originalDate, dateAfterReinit)
    }

    // MARK: - Boundary Value Tests

    @MainActor
    func testCanRequestReview_exactMinimumDays_returnsTrue() {
        let sevenDaysAgo = Calendar.current.date(byAdding: .day, value: -7, to: Date())!
        testDefaults.set(sevenDaysAgo, forKey: "review_app_install_date")
        testDefaults.set(5, forKey: "review_sessions_count")
        let manager = ReviewManager(userDefaults: testDefaults)
        XCTAssertTrue(manager.canRequestReview())
    }

    @MainActor
    func testCanRequestReview_oneDayBelowMinimum_returnsFalse() {
        let sixDaysAgo = Calendar.current.date(byAdding: .day, value: -6, to: Date())!
        testDefaults.set(sixDaysAgo, forKey: "review_app_install_date")
        testDefaults.set(5, forKey: "review_sessions_count")
        let manager = ReviewManager(userDefaults: testDefaults)
        XCTAssertFalse(manager.canRequestReview())
    }

    @MainActor
    func testCanRequestReview_exactMinimumSessions_returnsTrue() {
        let tenDaysAgo = Calendar.current.date(byAdding: .day, value: -10, to: Date())!
        testDefaults.set(tenDaysAgo, forKey: "review_app_install_date")
        testDefaults.set(5, forKey: "review_sessions_count")
        let manager = ReviewManager(userDefaults: testDefaults)
        XCTAssertTrue(manager.canRequestReview())
    }

    @MainActor
    func testCanRequestReview_belowMinimumSessions_returnsFalse() {
        let tenDaysAgo = Calendar.current.date(byAdding: .day, value: -10, to: Date())!
        testDefaults.set(tenDaysAgo, forKey: "review_app_install_date")
        testDefaults.set(4, forKey: "review_sessions_count")
        let manager = ReviewManager(userDefaults: testDefaults)
        XCTAssertFalse(manager.canRequestReview())
    }

    @MainActor
    func testCanRequestReview_exactCooldownDays_returnsTrue() {
        let hundredDaysAgo = Calendar.current.date(byAdding: .day, value: -100, to: Date())!
        testDefaults.set(hundredDaysAgo, forKey: "review_app_install_date")
        testDefaults.set(10, forKey: "review_sessions_count")
        let ninetyDaysAgo = Calendar.current.date(byAdding: .day, value: -90, to: Date())!
        testDefaults.set(ninetyDaysAgo, forKey: "review_last_request_date")
        let manager = ReviewManager(userDefaults: testDefaults)
        XCTAssertTrue(manager.canRequestReview())
    }

    @MainActor
    func testCanRequestReview_oneDayBelowCooldown_returnsFalse() {
        let hundredDaysAgo = Calendar.current.date(byAdding: .day, value: -100, to: Date())!
        testDefaults.set(hundredDaysAgo, forKey: "review_app_install_date")
        testDefaults.set(10, forKey: "review_sessions_count")
        let eightyNineDaysAgo = Calendar.current.date(byAdding: .day, value: -89, to: Date())!
        testDefaults.set(eightyNineDaysAgo, forKey: "review_last_request_date")
        let manager = ReviewManager(userDefaults: testDefaults)
        XCTAssertFalse(manager.canRequestReview())
    }

    // MARK: - FeedbackCategory Tests

    func testFeedbackCategory_allCasesCount() {
        XCTAssertEqual(FeedbackCategory.allCases.count, 4)
    }

    func testFeedbackCategory_displayNames() {
        XCTAssertEqual(FeedbackCategory.bugReport.displayName, "バグ報告")
        XCTAssertEqual(FeedbackCategory.featureRequest.displayName, "機能要望")
        XCTAssertEqual(FeedbackCategory.usability.displayName, "使いにくい")
        XCTAssertEqual(FeedbackCategory.other.displayName, "その他")
    }

    func testFeedbackCategory_icons() {
        XCTAssertEqual(FeedbackCategory.bugReport.icon, "ladybug")
        XCTAssertEqual(FeedbackCategory.featureRequest.icon, "lightbulb")
        XCTAssertEqual(FeedbackCategory.usability.icon, "hand.tap")
        XCTAssertEqual(FeedbackCategory.other.icon, "ellipsis.circle")
    }

    // MARK: - coarsenAgeGroup Tests

    func testCoarsenAgeGroup_earlySuffix_withS() {
        // 実データ形式: UserModel.ageGroup は "30s_early" を出力する
        XCTAssertEqual(AnalyticsManager.coarsenAgeGroup("30s_early"), "30s")
    }

    func testCoarsenAgeGroup_lateSuffix_withS() {
        // 実データ形式: "40s_late" → "40s"（"s" の重複追加を防止）
        XCTAssertEqual(AnalyticsManager.coarsenAgeGroup("40s_late"), "40s")
    }

    func testCoarsenAgeGroup_earlySuffix_withoutS() {
        // s なし形式も引き続き正しく処理される
        XCTAssertEqual(AnalyticsManager.coarsenAgeGroup("30_early"), "30s")
    }

    func testCoarsenAgeGroup_lateSuffix_withoutS() {
        // s なし形式: "30_late" → "30s"
        XCTAssertEqual(AnalyticsManager.coarsenAgeGroup("30_late"), "30s")
    }

    func testCoarsenAgeGroup_20s_early_regressionTest() {
        // バグ回帰防止: "20s_early" → "20s"（"20ss" にならないこと）
        XCTAssertEqual(AnalyticsManager.coarsenAgeGroup("20s_early"), "20s")
    }

    func testCoarsenAgeGroup_noSuffix_passthrough() {
        XCTAssertEqual(AnalyticsManager.coarsenAgeGroup("20s"), "20s")
    }

    func testCoarsenAgeGroup_empty_passthrough() {
        XCTAssertEqual(AnalyticsManager.coarsenAgeGroup(""), "")
    }

    func testCoarsenAgeGroup_compoundPrefix() {
        // "under_20_early" should produce "under_20s" (not "unders")
        XCTAssertEqual(AnalyticsManager.coarsenAgeGroup("under_20_early"), "under_20s")
    }

    func testCoarsenAgeGroup_compoundPrefix_late() {
        XCTAssertEqual(AnalyticsManager.coarsenAgeGroup("under_20_late"), "under_20s")
    }

    func testCoarsenAgeGroup_compoundPrefix_over80() {
        XCTAssertEqual(AnalyticsManager.coarsenAgeGroup("over_80_late"), "over_80s")
    }

    // MARK: - requestReview windowScene Fallback Tests

    @MainActor
    func testRequestReview_recordsRequestEvenWithoutWindowScene() {
        let tenDaysAgo = Calendar.current.date(byAdding: .day, value: -10, to: Date())!
        testDefaults.set(tenDaysAgo, forKey: "review_app_install_date")
        testDefaults.set(6, forKey: "review_sessions_count")
        sut = ReviewManager(userDefaults: testDefaults)

        XCTAssertTrue(sut.canRequestReview(), "Before request, review should be available")

        // In test environment, windowScene is unavailable — fallback path executes.
        // Note: The normal path (windowScene available → SKStoreReviewController)
        // cannot be tested in unit tests. Cover via UI/integration tests.
        sut.requestReview()

        // Should still record the request (cooldown consumed)
        XCTAssertNotNil(testDefaults.object(forKey: "review_last_request_date"))
        XCTAssertEqual(testDefaults.integer(forKey: "review_request_count_current_year"), 1)

        // Cooldown should now prevent further requests
        // (windowScene-unavailable path must also activate cooldown)
        XCTAssertFalse(sut.canRequestReview(), "After windowScene-unavailable request, cooldown should be active")
    }
}
