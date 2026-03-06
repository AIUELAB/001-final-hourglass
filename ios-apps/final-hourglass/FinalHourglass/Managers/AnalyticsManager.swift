// periphery:ignore:all - Analytics管理（TelemetryDeck SDK統合）
import Foundation
import OSLog
import SwiftUI
import TelemetryDeck

/// Analytics管理クラス（TelemetryDeck SDK統合）
/// Info.plist の TELEMETRYDECK_APP_ID キーで初期化する
class AnalyticsManager {
    static let shared = AnalyticsManager()

    /// SDK初期化済みフラグ
    private let lock = NSLock()
    private var _isConfigured = false
    private var isConfigured: Bool {
        get { lock.withLock { _isConfigured } }
        set { lock.withLock { _isConfigured = newValue } }
    }

    private init() {}

    private static let logger = Logger(
        subsystem: Bundle.main.bundleIdentifier ?? "com.AIUELAB.FinalHourglass",
        category: "Analytics"
    )

    // MARK: - Configuration

    /// TelemetryDeck SDKを初期化する
    /// Info.plist に `TELEMETRYDECK_APP_ID` キーが必要
    func configure() {
        guard let appID = Bundle.main.infoDictionary?["TELEMETRYDECK_APP_ID"] as? String,
              !appID.isEmpty,
              appID != "YOUR_TELEMETRYDECK_APP_ID"
        else {
            Self.logger.warning("[Analytics] TelemetryDeck App ID not configured — running in stub mode")
            return
        }

        lock.withLock {
            guard !_isConfigured else { return }
            let config = TelemetryDeck.Config(appID: appID)
            TelemetryDeck.initialize(config: config)
            _isConfigured = true
        }

        Self.logger.info("[Analytics] TelemetryDeck initialized successfully")
    }

    // MARK: - User Properties

    /// ageGroup を10年単位に粗粒化する（例: "30_early" → "30s", "40_late" → "40s"）
    static func coarsenAgeGroup(_ ageGroup: String) -> String {
        if ageGroup.hasSuffix("_early") || ageGroup.hasSuffix("_late"),
           let underscoreIndex = ageGroup.lastIndex(of: "_") {
            return String(ageGroup[..<underscoreIndex]) + "s"
        }
        return ageGroup
    }

    /// ユーザープロパティを設定
    func setUserProperties(userModel: UserModel) {
        #if DEBUG
        print("[Analytics] setUserProperties: age_group=\(userModel.ageGroup), gender=\(userModel.gender)")
        #endif

        guard isConfigured else { return }

        TelemetryDeck.updateDefaultParameters([
            "age_group": Self.coarsenAgeGroup(userModel.ageGroup),
            "gender": userModel.gender
        ])
    }

    // MARK: - Screen Tracking

    /// 画面表示をトラッキング
    func trackScreen(_ screenName: String, screenClass: String? = nil) {
        #if DEBUG
        print("[Analytics] trackScreen: \(screenName)")
        #endif

        guard isConfigured else { return }

        var params: [String: String] = ["screen_name": screenName]
        if let screenClass = screenClass {
            params["screen_class"] = screenClass
        }
        TelemetryDeck.signal("screen_view", parameters: params)
    }

    // MARK: - User Actions

    /// 通知設定変更をトラッキング
    func trackNotificationSettingChange(enabled: Bool) {
        #if DEBUG
        print("[Analytics] trackNotificationSettingChange: enabled=\(enabled)")
        #endif

        guard isConfigured else { return }

        TelemetryDeck.signal("notification_toggle", parameters: [
            "enabled": "\(enabled)"
        ])
    }

    /// リマインダー設定変更をトラッキング
    func trackReminderSettingChange(enabled: Bool, time: Date? = nil) {
        #if DEBUG
        print("[Analytics] trackReminderSettingChange: enabled=\(enabled), time=\(String(describing: time))")
        #endif

        guard isConfigured else { return }

        var params: [String: String] = ["enabled": "\(enabled)"]
        if let time = time {
            let formatter = DateFormatter()
            formatter.dateFormat = "HH:mm"
            params["time"] = formatter.string(from: time)
        }
        TelemetryDeck.signal("reminder_toggle", parameters: params)
    }

    // MARK: - Onboarding

    /// オンボーディング開始をトラッキング
    func trackOnboardingStart() {
        #if DEBUG
        print("[Analytics] trackOnboardingStart")
        #endif

        guard isConfigured else { return }
        TelemetryDeck.signal("onboarding_start")
    }

    /// オンボーディング完了をトラッキング
    func trackOnboardingComplete() {
        #if DEBUG
        print("[Analytics] trackOnboardingComplete")
        #endif

        guard isConfigured else { return }
        TelemetryDeck.signal("onboarding_complete")
    }

    /// オンボーディングステップをトラッキング
    func trackOnboardingStep(stepNumber: Int, stepName: String) {
        #if DEBUG
        print("[Analytics] trackOnboardingStep: step=\(stepNumber), name=\(stepName)")
        #endif

        guard isConfigured else { return }

        TelemetryDeck.signal("onboarding_step", parameters: [
            "step_number": "\(stepNumber)",
            "step_name": stepName
        ])
    }

    // MARK: - Life Result

    /// 寿命計算結果をトラッキング
    func trackLifeResultCalculation(lifeExpectancy: Double, currentAge: Int) {
        #if DEBUG
        let remainingYears = Int(lifeExpectancy - Double(currentAge))
        print("[Analytics] trackLifeResultCalculation: " +
            "lifeExpectancy=\(Int(lifeExpectancy)), " +
            "currentAge=\(currentAge), remainingYears=\(remainingYears)")
        #endif

        guard isConfigured else { return }

        TelemetryDeck.signal("life_result_view", parameters: [
            "life_expectancy": "\(Int(lifeExpectancy))",
            "current_age": "\(currentAge)"
        ])
    }

    // MARK: - Episodes

    /// エピソード表示をトラッキング
    func trackEpisodeView(episodeId: String, personName: String) {
        #if DEBUG
        print("[Analytics] trackEpisodeView: id=\(episodeId), person=\(personName)")
        #endif

        guard isConfigured else { return }

        TelemetryDeck.signal("episode_view", parameters: [
            "episode_id": episodeId,
            "person_name": personName
        ])
    }

    /// エピソードお気に入り登録をトラッキング
    func trackEpisodeFavorite(episodeId: String) {
        #if DEBUG
        print("[Analytics] trackEpisodeFavorite: id=\(episodeId)")
        #endif

        guard isConfigured else { return }

        TelemetryDeck.signal("episode_favorite", parameters: [
            "episode_id": episodeId
        ])
    }

    // MARK: - Sharing

    /// シェアアクションをトラッキング
    func trackShare(method: String) {
        #if DEBUG
        print("[Analytics] trackShare: method=\(method)")
        #endif

        guard isConfigured else { return }

        TelemetryDeck.signal("episode_share", parameters: [
            "share_method": method
        ])
    }

    // MARK: - Settings

    /// 設定変更をトラッキング
    func trackSettingChange(settingName: String, value: Any) {
        #if DEBUG
        print("[Analytics] trackSettingChange: \(settingName)=\(value)")
        #endif

        guard isConfigured else { return }

        TelemetryDeck.signal("setting_change", parameters: [
            "setting_name": settingName,
            "value": "\(value)"
        ])
    }

    /// データリセットをトラッキング
    func trackDataReset() {
        #if DEBUG
        print("[Analytics] trackDataReset")
        #endif

        guard isConfigured else { return }
        TelemetryDeck.signal("data_reset")
    }

    // MARK: - Health

    /// 健康スコア更新をトラッキング
    func trackHealthScoreUpdate(category: String, newScore: Double) {
        #if DEBUG
        print("[Analytics] trackHealthScoreUpdate: category=\(category), score=\(newScore)")
        #endif

        guard isConfigured else { return }

        TelemetryDeck.signal("health_score_update", parameters: [
            "category": category,
            "new_score": "\(Int(newScore))"
        ])
    }

    // MARK: - App Lifecycle

    /// アプリ起動をトラッキング
    func trackAppLaunch() {
        #if DEBUG
        print("[Analytics] trackAppLaunch: \(ISO8601DateFormatter().string(from: Date()))")
        #endif

        guard isConfigured else { return }

        let appVersion = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "unknown"
        let osVersion = ProcessInfo.processInfo.operatingSystemVersionString

        TelemetryDeck.signal("app_launch", parameters: [
            "app_version": appVersion,
            "os_version": osVersion
        ])
    }

    /// セッション時間をトラッキング
    func trackSessionDuration(duration: TimeInterval) {
        #if DEBUG
        print("[Analytics] trackSessionDuration: \(Int(duration))秒")
        #endif

        guard isConfigured else { return }

        TelemetryDeck.signal("session_end", parameters: [
            "duration_seconds": "\(Int(duration))"
        ])
    }

    // MARK: - Retention Metrics

    /// デイリーアクティブユーザーをトラッキング
    func trackDailyActive() {
        #if DEBUG
        print("[Analytics] trackDailyActive: \(DateFormatter.localizedString(from: Date(), dateStyle: .short, timeStyle: .none))")
        #endif

        guard isConfigured else { return }
        TelemetryDeck.signal("daily_active")
    }

    /// 連続使用日数をトラッキング
    func trackStreakDays(_ days: Int) {
        #if DEBUG
        print("[Analytics] trackStreakDays: \(days)日")
        #endif

        guard isConfigured else { return }

        TelemetryDeck.signal("daily_active", parameters: [
            "streak_days": "\(days)"
        ])
    }

    // MARK: - Review Prompt

    /// レビュープロンプト表示をトラッキング
    func trackReviewPromptShown(triggerType: String) {
        #if DEBUG
        print("[Analytics] trackReviewPromptShown: trigger=\(triggerType)")
        #endif

        guard isConfigured else { return }

        TelemetryDeck.signal("review_prompt_shown", parameters: [
            "trigger_type": triggerType
        ])
    }

    /// レビュープロンプト結果をトラッキング
    func trackReviewPromptResult(triggerType: String, result: String) {
        #if DEBUG
        print("[Analytics] trackReviewPromptResult: trigger=\(triggerType), result=\(result)")
        #endif

        guard isConfigured else { return }

        TelemetryDeck.signal("review_prompt_result", parameters: [
            "trigger_type": triggerType,
            "result": result
        ])
    }
}

// MARK: - Analytics View Modifier

struct AnalyticsScreenView: ViewModifier {
    let screenName: String

    func body(content: Content) -> some View {
        content
            .onAppear {
                AnalyticsManager.shared.trackScreen(screenName)
            }
    }
}

extension View {
    func analyticsScreen(_ name: String) -> some View {
        self.modifier(AnalyticsScreenView(screenName: name))
    }
}
