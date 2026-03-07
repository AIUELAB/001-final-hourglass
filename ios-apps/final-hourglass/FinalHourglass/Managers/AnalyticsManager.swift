// periphery:ignore:all - Analytics管理（TelemetryDeck SDK統合）
import Foundation
import OSLog
import SwiftUI
import TelemetryDeck

/// Analytics管理クラス（TelemetryDeck SDK統合）
/// Info.plist の TELEMETRYDECK_APP_ID キーで初期化する
class AnalyticsManager {
    static let shared = AnalyticsManager()

    /// SDK初期化済みフラグ（スレッドセーフ: NSLock で保護）
    private let lock = NSLock()
    private var _isConfigured = false
    private var isConfigured: Bool {
        lock.withLock { _isConfigured }
    }

    /// 初回警告済みフラグ（lock で保護、guardConfigured() 内でのみ読み書き）
    private var _hasWarnedStubMode = false

    private func guardConfigured() -> Bool {
        lock.withLock {
            guard _isConfigured else {
                if !_hasWarnedStubMode {
                    Self.logger.warning("[Analytics] Event skipped — SDK not configured (stub mode)")
                    _hasWarnedStubMode = true
                }
                return false
            }
            return true
        }
    }

    private init() {}

    private static let logger = Logger(
        subsystem: Bundle.main.bundleIdentifier ?? "com.AIUELAB.FinalHourglass",
        category: "Analytics"
    )

    // MARK: - Configuration

    /// TelemetryDeck SDKを初期化する
    /// Info.plist に `TELEMETRYDECK_APP_ID` キーが必要。
    /// キーが未設定の場合は stub モードで動作し、SDK は初期化されない。
    /// 二重呼び出しは安全（appID が有効で初回初期化済みの場合、二回目以降は何もしない）。
    func configure() {
        guard let appID = Bundle.main.infoDictionary?["TELEMETRYDECK_APP_ID"] as? String,
              !appID.isEmpty,
              appID != "YOUR_TELEMETRYDECK_APP_ID"
        else {
            Self.logger.warning("[Analytics] TelemetryDeck App ID not configured — running in stub mode")
            return
        }

        let shouldInit = lock.withLock { () -> Bool in
            guard !_isConfigured else { return false }
            _isConfigured = true
            return true
        }
        guard shouldInit else { return }

        let config = TelemetryDeck.Config(appID: appID)
        config.defaultParameters = { @Sendable in
            var params: [String: String] = [:]
            let ageGroup = UserDefaults.standard.string(forKey: "analytics_age_group") ?? ""
            let gender = UserDefaults.standard.string(forKey: "analytics_gender") ?? ""
            if !ageGroup.isEmpty {
                params["age_group"] = AnalyticsManager.coarsenAgeGroup(ageGroup)
            }
            if !gender.isEmpty {
                params["gender"] = gender
            }
            return params
        }
        TelemetryDeck.initialize(config: config)
        Self.logger.info("[Analytics] TelemetryDeck initialized successfully")
    }

    // MARK: - User Properties

    /// ageGroup を粗粒化する（"_early" / "_late" サフィックスを除去）
    /// `hasSuffix` でサフィックスを確認後、`lastIndex(of: "_")` でサフィックス直前の
    /// "_" を取得し、それ以前を base とする。
    /// 例: "30s_early" → "30s", "40s_late" → "40s", "under_20_early" → "under_20s"
    /// base が既に "s" で終わる場合は重複追加しない。
    /// "under_20" のように "s" で終わらない base には "s" を付加する。
    /// サフィックスがない場合はそのまま返す。
    /// - Note: 対応サフィックスは `_early` と `_late` の2種類のみ。
    ///   他のサフィックス（例: "_mid"）は除去されずそのまま返される。
    static func coarsenAgeGroup(_ ageGroup: String) -> String {
        if ageGroup.hasSuffix("_early") || ageGroup.hasSuffix("_late"),
           let underscoreIndex = ageGroup.lastIndex(of: "_") {
            let base = String(ageGroup[..<underscoreIndex])
            return base.hasSuffix("s") ? base : base + "s"
        }
        return ageGroup
    }

    /// ユーザープロパティを設定する
    /// UserDefaults に保存し、`configure()` で登録した `defaultParameters` クロージャが
    /// 次回イベント送信時に最新値を読み取る。ageGroup の粗粒化は `defaultParameters`
    /// クロージャ側で `coarsenAgeGroup(_:)` を呼び出して行う。
    /// SDK 未初期化（stub モード）でも UserDefaults への保存は行われる
    /// （後から configure() された際に defaultParameters が最新値を返せるようにするため）。
    func setUserProperties(userModel: UserModel) {
        let coarsenedAgeGroup = Self.coarsenAgeGroup(userModel.ageGroup)
        Self.logger.debug(
            "[Analytics] setUserProperties: age_group=\(coarsenedAgeGroup, privacy: .private), gender=\(userModel.gender, privacy: .private)"
        )

        // defaultParameters クロージャが参照する UserDefaults に保存
        UserDefaults.standard.set(userModel.ageGroup, forKey: "analytics_age_group")
        UserDefaults.standard.set(userModel.gender, forKey: "analytics_gender")
    }

    // MARK: - Screen Tracking

    /// 画面表示をトラッキング
    func trackScreen(_ screenName: String, screenClass: String? = nil) {
        Self.logger.debug("[Analytics] trackScreen: \(screenName)")

        guard guardConfigured() else { return }

        var params: [String: String] = ["screen_name": screenName]
        if let screenClass = screenClass {
            params["screen_class"] = screenClass
        }
        TelemetryDeck.signal("screen_view", parameters: params)
    }

    // MARK: - User Actions

    /// 通知設定変更をトラッキング
    func trackNotificationSettingChange(enabled: Bool) {
        Self.logger.debug("[Analytics] trackNotificationSettingChange: enabled=\(enabled)")

        guard guardConfigured() else { return }

        TelemetryDeck.signal("notification_toggle", parameters: [
            "enabled": "\(enabled)"
        ])
    }

    /// リマインダー設定変更をトラッキング
    func trackReminderSettingChange(enabled: Bool, time: Date? = nil) {
        Self.logger.debug("[Analytics] trackReminderSettingChange: enabled=\(enabled), time=\(String(describing: time))")

        guard guardConfigured() else { return }

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
        Self.logger.debug("[Analytics] trackOnboardingStart")

        guard guardConfigured() else { return }
        TelemetryDeck.signal("onboarding_start")
    }

    /// オンボーディング完了をトラッキング
    func trackOnboardingComplete() {
        Self.logger.debug("[Analytics] trackOnboardingComplete")

        guard guardConfigured() else { return }
        TelemetryDeck.signal("onboarding_complete")
    }

    /// オンボーディングステップをトラッキング
    func trackOnboardingStep(stepNumber: Int, stepName: String) {
        Self.logger.debug("[Analytics] trackOnboardingStep: step=\(stepNumber), name=\(stepName)")

        guard guardConfigured() else { return }

        TelemetryDeck.signal("onboarding_step", parameters: [
            "step_number": "\(stepNumber)",
            "step_name": stepName
        ])
    }

    // MARK: - Life Result

    /// 寿命計算結果をトラッキング
    func trackLifeResultCalculation(lifeExpectancy: Double, currentAge: Int) {
        let remaining = Int(lifeExpectancy) - currentAge
        Self.logger.debug(
            "[Analytics] trackLifeResultCalculation: lifeExpectancy=\(Int(lifeExpectancy)), currentAge=\(currentAge), remainingYears=\(remaining)"
        )

        guard guardConfigured() else { return }

        TelemetryDeck.signal("life_result_view", parameters: [
            "life_expectancy": "\(Int(lifeExpectancy))",
            "current_age": "\(currentAge)"
        ])
    }

    // MARK: - Episodes

    /// エピソード表示をトラッキング
    func trackEpisodeView(episodeId: String, personName: String) {
        Self.logger.debug("[Analytics] trackEpisodeView: id=\(episodeId), person=\(personName)")

        guard guardConfigured() else { return }

        TelemetryDeck.signal("episode_view", parameters: [
            "episode_id": episodeId,
            "person_name": personName
        ])
    }

    /// エピソードお気に入り登録をトラッキング
    func trackEpisodeFavorite(episodeId: String) {
        Self.logger.debug("[Analytics] trackEpisodeFavorite: id=\(episodeId)")

        guard guardConfigured() else { return }

        TelemetryDeck.signal("episode_favorite", parameters: [
            "episode_id": episodeId
        ])
    }

    // MARK: - Sharing

    /// シェアアクションをトラッキング
    func trackShare(method: String) {
        Self.logger.debug("[Analytics] trackShare: method=\(method)")

        guard guardConfigured() else { return }

        TelemetryDeck.signal("episode_share", parameters: [
            "share_method": method
        ])
    }

    // MARK: - Settings

    /// 設定変更をトラッキング
    func trackSettingChange(settingName: String, value: Any) {
        let valueString = String(describing: value)
        Self.logger.debug("[Analytics] trackSettingChange: \(settingName)=\(valueString)")

        guard guardConfigured() else { return }

        TelemetryDeck.signal("setting_change", parameters: [
            "setting_name": settingName,
            "value": valueString
        ])
    }

    /// データリセットをトラッキング
    func trackDataReset() {
        Self.logger.debug("[Analytics] trackDataReset")

        guard guardConfigured() else { return }
        TelemetryDeck.signal("data_reset")
    }

    // MARK: - Health

    /// 健康スコア更新をトラッキング
    func trackHealthScoreUpdate(category: String, newScore: Double) {
        Self.logger.debug("[Analytics] trackHealthScoreUpdate: category=\(category), score=\(newScore)")

        guard guardConfigured() else { return }

        TelemetryDeck.signal("health_score_update", parameters: [
            "category": category,
            "new_score": "\(Int(newScore))"
        ])
    }

    // MARK: - App Lifecycle

    /// アプリ起動をトラッキング
    func trackAppLaunch() {
        Self.logger.debug("[Analytics] trackAppLaunch: \(Date())")

        guard guardConfigured() else { return }

        let appVersion = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "unknown"
        let osVersion = ProcessInfo.processInfo.operatingSystemVersionString

        TelemetryDeck.signal("app_launch", parameters: [
            "app_version": appVersion,
            "os_version": osVersion
        ])
    }

    /// セッション時間をトラッキング
    func trackSessionDuration(duration: TimeInterval) {
        Self.logger.debug("[Analytics] trackSessionDuration: \(Int(duration))秒")

        guard guardConfigured() else { return }

        TelemetryDeck.signal("session_end", parameters: [
            "duration_seconds": "\(Int(duration))"
        ])
    }

    // MARK: - Retention Metrics

    /// デイリーアクティブユーザーをトラッキング
    func trackDailyActive() {
        Self.logger.debug("[Analytics] trackDailyActive: \(Date())")

        guard guardConfigured() else { return }
        TelemetryDeck.signal("daily_active")
    }

    /// 連続使用日数をトラッキング
    func trackStreakDays(_ days: Int) {
        Self.logger.debug("[Analytics] trackStreakDays: \(days)日")

        guard guardConfigured() else { return }

        TelemetryDeck.signal("daily_active", parameters: [
            "streak_days": "\(days)"
        ])
    }

    // MARK: - Review Prompt

    /// レビュープロンプト表示をトラッキング
    func trackReviewPromptShown(triggerType: String) {
        Self.logger.debug("[Analytics] trackReviewPromptShown: trigger=\(triggerType)")

        guard guardConfigured() else { return }

        TelemetryDeck.signal("review_prompt_shown", parameters: [
            "trigger_type": triggerType
        ])
    }

    /// レビュープロンプト結果をトラッキング
    func trackReviewPromptResult(triggerType: String, result: String) {
        Self.logger.debug("[Analytics] trackReviewPromptResult: trigger=\(triggerType), result=\(result)")

        guard guardConfigured() else { return }

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
