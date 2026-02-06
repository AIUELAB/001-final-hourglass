// periphery:ignore:all - Analytics管理（将来のMixpanel/Amplitude移行予定）
import Foundation
import SwiftUI

/// Analytics管理クラス（スタブ実装）
/// Firebase Analyticsを削除し、ログ出力のみに変更
/// 将来的にMixpanel/Amplitude等への移行を検討
class AnalyticsManager {
    static let shared = AnalyticsManager()

    private init() {}

    // MARK: - User Properties

    /// ユーザープロパティを設定（スタブ）
    func setUserProperties(userModel: UserModel) {
        #if DEBUG
        print("[Analytics] setUserProperties: age_group=\(userModel.ageGroup), gender=\(userModel.gender)")
        #endif
    }

    // MARK: - Screen Tracking

    /// 画面表示をトラッキング（スタブ）
    func trackScreen(_ screenName: String, screenClass: String? = nil) {
        #if DEBUG
        print("[Analytics] trackScreen: \(screenName)")
        #endif
    }

    // MARK: - User Actions

    /// 通知設定変更をトラッキング（スタブ）
    func trackNotificationSettingChange(enabled: Bool) {
        #if DEBUG
        print("[Analytics] trackNotificationSettingChange: enabled=\(enabled)")
        #endif
    }

    /// リマインダー設定変更をトラッキング（スタブ）
    func trackReminderSettingChange(enabled: Bool, time: Date? = nil) {
        #if DEBUG
        print("[Analytics] trackReminderSettingChange: enabled=\(enabled), time=\(String(describing: time))")
        #endif
    }

    // MARK: - Onboarding

    /// オンボーディング開始をトラッキング（スタブ）
    func trackOnboardingStart() {
        #if DEBUG
        print("[Analytics] trackOnboardingStart")
        #endif
    }

    /// オンボーディング完了をトラッキング（スタブ）
    func trackOnboardingComplete() {
        #if DEBUG
        print("[Analytics] trackOnboardingComplete")
        #endif
    }

    // MARK: - Life Result

    /// 寿命計算結果をトラッキング（スタブ）
    func trackLifeResultCalculation(lifeExpectancy: Double, currentAge: Int) {
        #if DEBUG
        let remainingYears = Int(lifeExpectancy - Double(currentAge))
        print("[Analytics] trackLifeResultCalculation: " +
            "lifeExpectancy=\(Int(lifeExpectancy)), " +
            "currentAge=\(currentAge), remainingYears=\(remainingYears)")
        #endif
    }

    // MARK: - Sharing

    /// シェアアクションをトラッキング（スタブ）
    func trackShare(method: String) {
        #if DEBUG
        print("[Analytics] trackShare: method=\(method)")
        #endif
    }

    // MARK: - Settings

    /// 設定変更をトラッキング（スタブ）
    func trackSettingChange(settingName: String, value: Any) {
        #if DEBUG
        print("[Analytics] trackSettingChange: \(settingName)=\(value)")
        #endif
    }

    /// データリセットをトラッキング（スタブ）
    func trackDataReset() {
        #if DEBUG
        print("[Analytics] trackDataReset")
        #endif
    }

    // MARK: - App Lifecycle

    /// アプリ起動をトラッキング（スタブ）
    func trackAppLaunch() {
        #if DEBUG
        print("[Analytics] trackAppLaunch: \(ISO8601DateFormatter().string(from: Date()))")
        #endif
    }

    /// セッション時間をトラッキング（スタブ）
    func trackSessionDuration(duration: TimeInterval) {
        #if DEBUG
        print("[Analytics] trackSessionDuration: \(Int(duration))秒")
        #endif
    }

    // MARK: - Retention Metrics

    /// デイリーアクティブユーザーをトラッキング（スタブ）
    func trackDailyActive() {
        #if DEBUG
        print("[Analytics] trackDailyActive: \(DateFormatter.localizedString(from: Date(), dateStyle: .short, timeStyle: .none))")
        #endif
    }

    /// 連続使用日数をトラッキング（スタブ）
    func trackStreakDays(_ days: Int) {
        #if DEBUG
        print("[Analytics] trackStreakDays: \(days)日")
        #endif
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
