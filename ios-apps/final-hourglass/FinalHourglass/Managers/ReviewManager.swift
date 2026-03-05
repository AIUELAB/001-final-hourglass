import Foundation
import StoreKit
import SwiftUI
import UIKit

// MARK: - ReviewTrigger

/// レビュー依頼のトリガー種別
enum ReviewTrigger: String {
    case episodeViews = "episode_views"
    case usageStreak = "usage_streak"
    case favorites = "favorites"
    case healthScoreComplete = "health_score_complete"
    case manual = "manual"
}

// MARK: - PrePromptResponse

/// プレプロンプトのユーザー回答
enum PrePromptResponse: String {
    case positive = "positive"
    case neutral = "neutral"
    case negative = "negative"
}

// MARK: - ReviewManager

/// App Store Guidelines準拠のレビュー依頼管理
/// Guidelines 1.1.4: 過度なレビュー要求の回避
/// Guidelines 3.1.1: アプリ内レビューシステム
class ReviewManager: ObservableObject {
    static let shared = ReviewManager()

    // MARK: - Published Properties

    @Published var showPrePrompt = false
    @Published var showFeedbackForm = false
    var currentTrigger: ReviewTrigger = .manual

    // MARK: - Constants

    private struct Constants {
        static let cooldownDays = 90
        static let minimumUsageDays = 7
        static let minimumSessions = 5
        static let maxRequestsPerYear = 3
        static let episodeViewThreshold = 10
        static let usageStreakThreshold = 7
        static let favoritesThreshold = 3
    }

    // MARK: - UserDefaults Keys

    private struct Keys {
        static let lastRequestDate = "review_last_request_date"
        static let requestCountCurrentYear = "review_request_count_current_year"
        static let requestYear = "review_request_year"
        static let episodeViewCount = "review_episode_view_count"
        static let sessionsCount = "review_sessions_count"
        static let appInstallDate = "review_app_install_date"
    }

    // MARK: - Dependencies

    private let userDefaults: UserDefaults

    // MARK: - Init

    init(userDefaults: UserDefaults = .standard) {
        self.userDefaults = userDefaults
        initializeInstallDateIfNeeded()
        resetYearlyCountIfNeeded()
    }

    // MARK: - Public Methods

    /// トリガーに基づいてレビュー依頼を検討する
    func checkAndPromptReview(trigger: ReviewTrigger) {
        currentTrigger = trigger

        guard canRequestReview() else {
            return
        }

        AnalyticsManager.shared.trackReviewPromptShown(triggerType: trigger.rawValue)
        showPrePrompt = true
    }

    /// レビュー依頼可能かどうかを判定する
    func canRequestReview() -> Bool {
        let calendar = Calendar.current
        let now = Date()

        // 1. インストールから最低日数が経過しているか
        guard let installDate = userDefaults.object(forKey: Keys.appInstallDate) as? Date else {
            return false
        }
        let daysSinceInstall = calendar.dateComponents([.day], from: installDate, to: now).day ?? 0
        guard daysSinceInstall >= Constants.minimumUsageDays else {
            return false
        }

        // 2. 最低セッション数に達しているか
        let sessions = userDefaults.integer(forKey: Keys.sessionsCount)
        guard sessions >= Constants.minimumSessions else {
            return false
        }

        // 3. クールダウン期間を過ぎているか
        if let lastRequest = userDefaults.object(forKey: Keys.lastRequestDate) as? Date {
            let daysSinceLast = calendar.dateComponents([.day], from: lastRequest, to: now).day ?? 0
            guard daysSinceLast >= Constants.cooldownDays else {
                return false
            }
        }

        // 4. 年間上限に達していないか
        let yearlyCount = userDefaults.integer(forKey: Keys.requestCountCurrentYear)
        guard yearlyCount < Constants.maxRequestsPerYear else {
            return false
        }

        return true
    }

    /// App Store レビューダイアログを表示する
    @MainActor
    func requestReview() {
        guard let windowScene = UIApplication.shared.connectedScenes
            .first(where: { $0.activationState == .foregroundActive }) as? UIWindowScene else {
            return
        }

        if #available(iOS 18.0, *) {
            AppStore.requestReview(in: windowScene)
        } else {
            SKStoreReviewController.requestReview(in: windowScene)
        }

        recordReviewRequest()
        AnalyticsManager.shared.trackReviewPromptResult(
            triggerType: currentTrigger.rawValue,
            result: PrePromptResponse.positive.rawValue
        )
    }

    /// エピソード閲覧をカウントし、閾値チェックを行う
    func recordEpisodeView() {
        let current = userDefaults.integer(forKey: Keys.episodeViewCount)
        let newCount = current + 1
        userDefaults.set(newCount, forKey: Keys.episodeViewCount)

        if newCount == Constants.episodeViewThreshold {
            checkAndPromptReview(trigger: .episodeViews)
        }
    }

    /// セッション数をカウントする
    func recordSession() {
        let current = userDefaults.integer(forKey: Keys.sessionsCount)
        userDefaults.set(current + 1, forKey: Keys.sessionsCount)
    }

    /// プレプロンプトの回答を処理する
    @MainActor
    func handlePrePromptResponse(_ response: PrePromptResponse) {
        showPrePrompt = false

        switch response {
        case .positive:
            requestReview()
        case .neutral:
            AnalyticsManager.shared.trackReviewPromptResult(
                triggerType: currentTrigger.rawValue,
                result: response.rawValue
            )
        case .negative:
            showFeedbackForm = true
            AnalyticsManager.shared.trackReviewPromptResult(
                triggerType: currentTrigger.rawValue,
                result: response.rawValue
            )
        }
    }

    // MARK: - Private Methods

    private func initializeInstallDateIfNeeded() {
        if userDefaults.object(forKey: Keys.appInstallDate) == nil {
            userDefaults.set(Date(), forKey: Keys.appInstallDate)
        }
    }

    private func resetYearlyCountIfNeeded() {
        let calendar = Calendar.current
        let currentYear = calendar.component(.year, from: Date())
        let storedYear = userDefaults.integer(forKey: Keys.requestYear)

        if storedYear != currentYear {
            userDefaults.set(0, forKey: Keys.requestCountCurrentYear)
            userDefaults.set(currentYear, forKey: Keys.requestYear)
        }
    }

    private func recordReviewRequest() {
        userDefaults.set(Date(), forKey: Keys.lastRequestDate)

        let currentCount = userDefaults.integer(forKey: Keys.requestCountCurrentYear)
        userDefaults.set(currentCount + 1, forKey: Keys.requestCountCurrentYear)
    }
}

// MARK: - ReviewPromptModifier

/// ルートビューに1箇所だけ配置するViewModifier
struct ReviewPromptModifier: ViewModifier {
    @ObservedObject var reviewManager = ReviewManager.shared

    func body(content: Content) -> some View {
        content
            .alert("アプリはいかがですか？", isPresented: $reviewManager.showPrePrompt) {
                Button("気に入っています") {
                    reviewManager.handlePrePromptResponse(.positive)
                }
                Button("まあまあです") {
                    reviewManager.handlePrePromptResponse(.neutral)
                }
                Button("改善してほしい") {
                    reviewManager.handlePrePromptResponse(.negative)
                }
            }
            .sheet(isPresented: $reviewManager.showFeedbackForm) {
                FeedbackFormView()
            }
    }
}

extension View {
    /// レビュープロンプト機能を付与する
    func reviewPrompt() -> some View {
        self.modifier(ReviewPromptModifier())
    }
}
