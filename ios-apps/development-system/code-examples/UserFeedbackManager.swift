import Foundation
import UIKit
import StoreKit
import MessageUI

/// Apple App Store Guidelines準拠ユーザーフィードバック管理システム
/// Guidelines 1.1.4: 過度なレビュー要求の回避
/// Guidelines 3.1.1: アプリ内レビューシステム
class UserFeedbackManager: NSObject, ObservableObject {

    static let shared = UserFeedbackManager()

    @Published var canRequestReview = false
    @Published var shouldShowFeedbackPrompt = false

    private let userDefaults = UserDefaults.standard
    private var feedbackSubmissionDelegate: FeedbackSubmissionDelegate?

    // App Store Guidelines準拠の定数
    private struct Constants {
        static let reviewRequestCooldownDays = 90  // 90日間のクールダウン
        static let minimumUsageDaysBeforeReview = 7  // 7日間使用後
        static let minimumSessionsBeforeReview = 5   // 5回使用後
        static let maxReviewRequestsPerYear = 3      // 年間最大3回
        static let minPositiveActionsBeforeReview = 10  // 10回のポジティブアクション後
    }

    // UserDefaults Keys
    private struct UserDefaultsKeys {
        static let lastReviewRequestDate = "last_review_request_date"
        static let reviewRequestCount = "review_request_count_current_year"
        static let appInstallDate = "app_install_date"
        static let sessionCount = "app_session_count"
        static let positiveActionCount = "positive_action_count"
        static let feedbackGiven = "user_feedback_given"
        static let lastFeedbackPromptDate = "last_feedback_prompt_date"
    }

    override init() {
        super.init()
        initializeTrackingIfNeeded()
        updateReviewEligibility()
    }

    // MARK: - 初期化とトラッキング

    private func initializeTrackingIfNeeded() {
        // 初回インストール日の記録
        if userDefaults.object(forKey: UserDefaultsKeys.appInstallDate) == nil {
            userDefaults.set(Date(), forKey: UserDefaultsKeys.appInstallDate)
        }

        // セッション数の増加
        let currentSessions = userDefaults.integer(forKey: UserDefaultsKeys.sessionCount)
        userDefaults.set(currentSessions + 1, forKey: UserDefaultsKeys.sessionCount)

        // 年間リクエスト数のリセット（年が変わった場合）
        resetYearlyCountIfNeeded()
    }

    private func resetYearlyCountIfNeeded() {
        let calendar = Calendar.current
        let currentYear = calendar.component(.year, from: Date())

        let lastRequestDate = userDefaults.object(forKey: UserDefaultsKeys.lastReviewRequestDate) as? Date
        if let lastDate = lastRequestDate {
            let lastRequestYear = calendar.component(.year, from: lastDate)
            if currentYear > lastRequestYear {
                userDefaults.set(0, forKey: UserDefaultsKeys.reviewRequestCount)
            }
        }
    }

    // MARK: - レビューリクエスト管理

    /// App Store Guidelines準拠のレビューリクエスト
    @MainActor
    func requestReviewIfAppropriate() {
        guard canRequestReview else {
            print("📝 Review request skipped: conditions not met")
            return
        }

        // App Store Guidelines 1.1.4: 過度なレビュー要求の回避
        guard isEligibleForReviewRequest() else {
            print("📝 Review request skipped: not eligible")
            return
        }

        // iOS 14.0以上でSKStoreReviewControllerを使用
        if #available(iOS 14.0, *) {
            // WindowSceneの取得
            guard let windowScene = UIApplication.shared.connectedScenes
                .first(where: { $0.activationState == .foregroundActive }) as? UIWindowScene else {
                return
            }

            SKStoreReviewController.requestReview(in: windowScene)
        } else {
            SKStoreReviewController.requestReview()
        }

        // リクエスト記録
        recordReviewRequest()

        print("✅ Review request displayed")
    }

    private func isEligibleForReviewRequest() -> Bool {
        let calendar = Calendar.current
        let now = Date()

        // 1. インストールから十分な日数が経過しているか
        guard let installDate = userDefaults.object(forKey: UserDefaultsKeys.appInstallDate) as? Date else {
            return false
        }

        let daysSinceInstall = calendar.dateComponents([.day], from: installDate, to: now).day ?? 0
        guard daysSinceInstall >= Constants.minimumUsageDaysBeforeReview else {
            return false
        }

        // 2. 十分なセッション数があるか
        let sessionCount = userDefaults.integer(forKey: UserDefaultsKeys.sessionCount)
        guard sessionCount >= Constants.minimumSessionsBeforeReview else {
            return false
        }

        // 3. 十分なポジティブアクションがあるか
        let positiveActions = userDefaults.integer(forKey: UserDefaultsKeys.positiveActionCount)
        guard positiveActions >= Constants.minPositiveActionsBeforeReview else {
            return false
        }

        // 4. 前回のリクエストから十分な時間が経過しているか
        if let lastRequestDate = userDefaults.object(forKey: UserDefaultsKeys.lastReviewRequestDate) as? Date {
            let daysSinceLastRequest = calendar.dateComponents([.day], from: lastRequestDate, to: now).day ?? 0
            guard daysSinceLastRequest >= Constants.reviewRequestCooldownDays else {
                return false
            }
        }

        // 5. 年間リクエスト上限に達していないか
        let yearlyRequestCount = userDefaults.integer(forKey: UserDefaultsKeys.reviewRequestCount)
        guard yearlyRequestCount < Constants.maxReviewRequestsPerYear else {
            return false
        }

        return true
    }

    private func recordReviewRequest() {
        userDefaults.set(Date(), forKey: UserDefaultsKeys.lastReviewRequestDate)

        let currentCount = userDefaults.integer(forKey: UserDefaultsKeys.reviewRequestCount)
        userDefaults.set(currentCount + 1, forKey: UserDefaultsKeys.reviewRequestCount)

        updateReviewEligibility()
    }

    private func updateReviewEligibility() {
        canRequestReview = isEligibleForReviewRequest()
    }

    // MARK: - ポジティブアクション追跡

    /// ユーザーのポジティブアクションを記録
    /// - Parameter action: ポジティブアクションの種類
    func recordPositiveAction(_ action: PositiveAction) {
        let currentCount = userDefaults.integer(forKey: UserDefaultsKeys.positiveActionCount)
        userDefaults.set(currentCount + 1, forKey: UserDefaultsKeys.positiveActionCount)

        print("📊 Positive action recorded: \(action.rawValue), total: \(currentCount + 1)")

        updateReviewEligibility()

        // 特定の条件でフィードバックプロンプトを表示
        checkForFeedbackPrompt()
    }

    enum PositiveAction: String, CaseIterable {
        case completedTask = "completed_task"
        case sharedContent = "shared_content"
        case usedPremiumFeature = "used_premium_feature"
        case completedOnboarding = "completed_onboarding"
        case enabledNotifications = "enabled_notifications"
        case madeInAppPurchase = "made_in_app_purchase"
        case invitedFriend = "invited_friend"
        case customizedSettings = "customized_settings"
        case achievedGoal = "achieved_goal"
        case usedFeatureFirstTime = "used_feature_first_time"

        var displayName: String {
            switch self {
            case .completedTask: return "タスク完了"
            case .sharedContent: return "コンテンツ共有"
            case .usedPremiumFeature: return "プレミアム機能使用"
            case .completedOnboarding: return "オンボーディング完了"
            case .enabledNotifications: return "通知有効化"
            case .madeInAppPurchase: return "アプリ内購入"
            case .invitedFriend: return "友達招待"
            case .customizedSettings: return "設定カスタマイズ"
            case .achievedGoal: return "目標達成"
            case .usedFeatureFirstTime: return "新機能初回使用"
            }
        }
    }

    // MARK: - フィードバックプロンプト管理

    private func checkForFeedbackPrompt() {
        let positiveActions = userDefaults.integer(forKey: UserDefaultsKeys.positiveActionCount)
        let feedbackGiven = userDefaults.bool(forKey: UserDefaultsKeys.feedbackGiven)

        // すでにフィードバックを提供済みの場合はスキップ
        guard !feedbackGiven else { return }

        // 十分なポジティブアクションがある場合
        if positiveActions >= Constants.minPositiveActionsBeforeReview {
            // 前回のプロンプトから十分な時間が経過しているかチェック
            if let lastPromptDate = userDefaults.object(forKey: UserDefaultsKeys.lastFeedbackPromptDate) as? Date {
                let daysSinceLastPrompt = Calendar.current.dateComponents([.day], from: lastPromptDate, to: Date()).day ?? 0
                if daysSinceLastPrompt < 30 { // 30日間のクールダウン
                    return
                }
            }

            shouldShowFeedbackPrompt = true
        }
    }

    /// カスタムフィードバックプロンプトの表示
    @MainActor
    func showFeedbackPrompt(from viewController: UIViewController) {
        let alert = UIAlertController(
            title: "アプリのご感想をお聞かせください",
            message: "より良いアプリにするため、ご意見をお聞かせください。",
            preferredStyle: .alert
        )

        // App Storeレビューを促す
        let reviewAction = UIAlertAction(title: "App Storeでレビュー", style: .default) { _ in
            self.requestReviewIfAppropriate()
            self.recordFeedbackGiven(.appStoreReview)
        }

        // アプリ内フィードバック
        let feedbackAction = UIAlertAction(title: "フィードバックを送信", style: .default) { _ in
            self.showInAppFeedbackForm(from: viewController)
        }

        // 後で
        let laterAction = UIAlertAction(title: "後で", style: .cancel) { _ in
            self.recordFeedbackPromptShown()
        }

        alert.addAction(reviewAction)
        alert.addAction(feedbackAction)
        alert.addAction(laterAction)

        viewController.present(alert, animated: true)
    }

    // MARK: - アプリ内フィードバックフォーム

    private func showInAppFeedbackForm(from viewController: UIViewController) {
        let feedbackVC = FeedbackViewController()
        feedbackVC.delegate = self

        let navigationController = UINavigationController(rootViewController: feedbackVC)
        navigationController.modalPresentationStyle = .formSheet

        viewController.present(navigationController, animated: true)
    }

    private func recordFeedbackGiven(_ type: FeedbackType) {
        userDefaults.set(true, forKey: UserDefaultsKeys.feedbackGiven)
        shouldShowFeedbackPrompt = false

        print("✅ Feedback recorded: \(type.rawValue)")
    }

    private func recordFeedbackPromptShown() {
        userDefaults.set(Date(), forKey: UserDefaultsKeys.lastFeedbackPromptDate)
        shouldShowFeedbackPrompt = false
    }

    enum FeedbackType: String {
        case appStoreReview = "app_store_review"
        case inAppFeedback = "in_app_feedback"
        case email = "email_feedback"
    }

    // MARK: - メールフィードバック

    func sendEmailFeedback(from viewController: UIViewController) {
        guard MFMailComposeViewController.canSendMail() else {
            showEmailNotAvailableAlert(from: viewController)
            return
        }

        let mailComposer = MFMailComposeViewController()
        mailComposer.mailComposeDelegate = self
        mailComposer.setToRecipients(["support@yourapp.com"])
        mailComposer.setSubject("[\(getAppName())] フィードバック")

        let messageBody = createEmailTemplate()
        mailComposer.setMessageBody(messageBody, isHTML: false)

        viewController.present(mailComposer, animated: true)
    }

    private func showEmailNotAvailableAlert(from viewController: UIViewController) {
        let alert = UIAlertController(
            title: "メールが設定されていません",
            message: "デバイスでメールアカウントが設定されていないため、メールを送信できません。設定アプリからメールアカウントを設定してください。",
            preferredStyle: .alert
        )

        let settingsAction = UIAlertAction(title: "設定を開く", style: .default) { _ in
            if let settingsURL = URL(string: UIApplication.openSettingsURLString) {
                UIApplication.shared.open(settingsURL)
            }
        }

        let cancelAction = UIAlertAction(title: "キャンセル", style: .cancel)

        alert.addAction(settingsAction)
        alert.addAction(cancelAction)

        viewController.present(alert, animated: true)
    }

    private func createEmailTemplate() -> String {
        let appName = getAppName()
        let appVersion = getAppVersion()
        let buildNumber = getBuildNumber()
        let deviceInfo = getDeviceInfo()
        let osVersion = UIDevice.current.systemVersion

        return """
        アプリ名: \(appName)
        バージョン: \(appVersion) (\(buildNumber))
        デバイス: \(deviceInfo)
        iOS バージョン: \(osVersion)

        ===== フィードバック内容 =====



        ===== 問題が発生している場合は以下もご記入ください =====

        発生日時:
        再現手順:
        1.
        2.
        3.

        期待する動作:


        実際の動作:


        その他:

        """
    }

    // MARK: - アプリ情報取得

    private func getAppName() -> String {
        return Bundle.main.infoDictionary?["CFBundleDisplayName"] as? String ??
               Bundle.main.infoDictionary?["CFBundleName"] as? String ?? "Unknown"
    }

    private func getAppVersion() -> String {
        return Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "Unknown"
    }

    private func getBuildNumber() -> String {
        return Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "Unknown"
    }

    private func getDeviceInfo() -> String {
        var systemInfo = utsname()
        uname(&systemInfo)
        let identifier = withUnsafePointer(to: &systemInfo.machine) {
            $0.withMemoryRebound(to: CChar.self, capacity: 1) {
                ptr in String(validatingUTF8: ptr)
            }
        }
        return identifier ?? UIDevice.current.model
    }

    // MARK: - 分析データ

    func getFeedbackAnalytics() -> FeedbackAnalytics {
        let installDate = userDefaults.object(forKey: UserDefaultsKeys.appInstallDate) as? Date ?? Date()
        let sessionCount = userDefaults.integer(forKey: UserDefaultsKeys.sessionCount)
        let positiveActions = userDefaults.integer(forKey: UserDefaultsKeys.positiveActionCount)
        let reviewRequestCount = userDefaults.integer(forKey: UserDefaultsKeys.reviewRequestCount)
        let feedbackGiven = userDefaults.bool(forKey: UserDefaultsKeys.feedbackGiven)

        let daysSinceInstall = Calendar.current.dateComponents([.day], from: installDate, to: Date()).day ?? 0

        return FeedbackAnalytics(
            daysSinceInstall: daysSinceInstall,
            totalSessions: sessionCount,
            positiveActionCount: positiveActions,
            reviewRequestCount: reviewRequestCount,
            hasFeedbackGiven: feedbackGiven,
            canRequestReview: canRequestReview
        )
    }
}

// MARK: - MFMailComposeViewControllerDelegate

extension UserFeedbackManager: MFMailComposeViewControllerDelegate {
    func mailComposeController(_ controller: MFMailComposeViewController, didFinishWith result: MFMailComposeResult, error: Error?) {
        controller.dismiss(animated: true)

        if result == .sent {
            recordFeedbackGiven(.email)
            print("✅ Email feedback sent successfully")
        } else if let error = error {
            print("❌ Email feedback failed: \(error.localizedDescription)")
        }
    }
}

// MARK: - FeedbackViewControllerDelegate

extension UserFeedbackManager: FeedbackViewControllerDelegate {
    func feedbackViewController(_ viewController: FeedbackViewController, didSubmitFeedback feedback: String, rating: Int) {
        // フィードバックの処理（サーバーに送信等）
        submitFeedbackToServer(feedback: feedback, rating: rating) { [weak self] success in
            DispatchQueue.main.async {
                viewController.dismiss(animated: true) {
                    if success {
                        self?.recordFeedbackGiven(.inAppFeedback)
                        self?.showFeedbackThankYou()
                    } else {
                        self?.showFeedbackError()
                    }
                }
            }
        }
    }

    func feedbackViewControllerDidCancel(_ viewController: FeedbackViewController) {
        viewController.dismiss(animated: true)
    }

    private func submitFeedbackToServer(feedback: String, rating: Int, completion: @escaping (Bool) -> Void) {
        // サーバーへのフィードバック送信実装
        // 実際のプロジェクトではAPI呼び出しを実装

        let feedbackData: [String: Any] = [
            "feedback": feedback,
            "rating": rating,
            "app_version": getAppVersion(),
            "device_info": getDeviceInfo(),
            "timestamp": ISO8601DateFormatter().string(from: Date())
        ]

        print("📤 Submitting feedback: \(feedbackData)")

        // シミュレート
        DispatchQueue.global().asyncAfter(deadline: .now() + 1.0) {
            completion(true)
        }
    }

    private func showFeedbackThankYou() {
        // フィードバック送信完了の通知
        print("🙏 Thank you for your feedback!")
    }

    private func showFeedbackError() {
        // エラー表示
        print("❌ Failed to submit feedback")
    }
}

// MARK: - Supporting Types

struct FeedbackAnalytics {
    let daysSinceInstall: Int
    let totalSessions: Int
    let positiveActionCount: Int
    let reviewRequestCount: Int
    let hasFeedbackGiven: Bool
    let canRequestReview: Bool
}

protocol FeedbackSubmissionDelegate: AnyObject {
    func didSubmitFeedback(_ feedback: String, rating: Int)
    func didCancelFeedback()
}

// MARK: - カスタムフィードバックViewController

class FeedbackViewController: UIViewController {

    weak var delegate: FeedbackViewControllerDelegate?

    @IBOutlet private var feedbackTextView: UITextView!
    @IBOutlet private var ratingStackView: UIStackView!
    @IBOutlet private var submitButton: UIButton!

    private var selectedRating: Int = 0
    private var ratingButtons: [UIButton] = []

    override func viewDidLoad() {
        super.viewDidLoad()
        setupUI()
    }

    private func setupUI() {
        title = "フィードバック"

        navigationItem.leftBarButtonItem = UIBarButtonItem(
            barButtonSystemItem: .cancel,
            target: self,
            action: #selector(cancelTapped)
        )

        setupRatingButtons()
        setupTextView()
        setupSubmitButton()
    }

    private func setupRatingButtons() {
        // 5つ星評価ボタンの作成
        for index in 1...5 {
            let button = UIButton(type: .system)
            button.setTitle("★", for: .normal)
            button.titleLabel?.font = UIFont.systemFont(ofSize: 30)
            button.setTitleColor(.systemGray, for: .normal)
            button.tag = i
            button.addTarget(self, action: #selector(ratingButtonTapped(_:)), for: .touchUpInside)

            ratingStackView.addArrangedSubview(button)
            ratingButtons.append(button)
        }
    }

    private func setupTextView() {
        feedbackTextView.layer.borderColor = UIColor.systemGray4.cgColor
        feedbackTextView.layer.borderWidth = 1.0
        feedbackTextView.layer.cornerRadius = 8.0
        feedbackTextView.font = UIFont.systemFont(ofSize: 16)
    }

    private func setupSubmitButton() {
        submitButton.layer.cornerRadius = 8.0
        submitButton.isEnabled = false
        updateSubmitButtonState()
    }

    @objc private func ratingButtonTapped(_ sender: UIButton) {
        selectedRating = sender.tag
        updateRatingDisplay()
        updateSubmitButtonState()
    }

    private func updateRatingDisplay() {
        for (index, button) in ratingButtons.enumerated() {
            let starIndex = index + 1
            button.setTitleColor(starIndex <= selectedRating ? .systemYellow : .systemGray, for: .normal)
        }
    }

    private func updateSubmitButtonState() {
        let hasRating = selectedRating > 0
        let hasFeedback = !(feedbackTextView.text?.isEmpty ?? true)

        submitButton.isEnabled = hasRating || hasFeedback
        submitButton.backgroundColor = submitButton.isEnabled ? .systemBlue : .systemGray4
    }

    @IBAction private func submitButtonTapped() {
        let feedback = feedbackTextView.text ?? ""
        delegate?.feedbackViewController(self, didSubmitFeedback: feedback, rating: selectedRating)
    }

    @objc private func cancelTapped() {
        delegate?.feedbackViewControllerDidCancel(self)
    }
}

protocol FeedbackViewControllerDelegate: AnyObject {
    func feedbackViewController(_ viewController: FeedbackViewController, didSubmitFeedback feedback: String, rating: Int)
    func feedbackViewControllerDidCancel(_ viewController: FeedbackViewController)
}

// MARK: - SwiftUI Integration

#if canImport(SwiftUI)
import SwiftUI

@available(iOS 13.0, *)
struct FeedbackPromptView: View {
    @ObservedObject var feedbackManager = UserFeedbackManager.shared
    @State private var showingFeedbackSheet = false

    var body: some View {
        Group {
            if feedbackManager.shouldShowFeedbackPrompt {
                VStack {
                    Text("アプリはいかがですか？")
                        .font(.headline)

                    Text("ご感想をお聞かせください")
                        .font(.subheadline)
                        .foregroundColor(.secondary)

                    HStack {
                        Button("App Storeでレビュー") {
                            feedbackManager.requestReviewIfAppropriate()
                        }
                        .buttonStyle(.bordered)

                        Button("フィードバック") {
                            showingFeedbackSheet = true
                        }
                        .buttonStyle(.borderedProminent)
                    }
                }
                .padding()
                .background(Color(.systemBackground))
                .cornerRadius(12)
                .shadow(radius: 4)
                .sheet(isPresented: $showingFeedbackSheet) {
                    FeedbackFormView()
                }
            }
        }
    }
}

@available(iOS 13.0, *)
struct FeedbackFormView: View {
    @State private var feedback = ""
    @State private var rating = 0
    @Environment(\.presentationMode) var presentationMode

    var body: some View {
        NavigationView {
            Form {
                Section("評価") {
                    HStack {
                        ForEach(1...5, id: \.self) { star in
                            Button(action: {
                                rating = star
                            }) {
                                Image(systemName: star <= rating ? "star.fill" : "star")
                                    .foregroundColor(star <= rating ? .yellow : .gray)
                                    .font(.title2)
                            }
                        }
                    }
                }

                Section("ご意見・ご感想") {
                    TextEditor(text: $feedback)
                        .frame(minHeight: 100)
                }
            }
            .navigationTitle("フィードバック")
            .navigationBarTitleDisplayMode(.inline)
            .navigationBarBackButtonHidden(true)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("キャンセル") {
                        presentationMode.wrappedValue.dismiss()
                    }
                }

                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("送信") {
                        submitFeedback()
                    }
                    .disabled(rating == 0 && feedback.isEmpty)
                }
            }
        }
    }

    private func submitFeedback() {
        // フィードバック送信処理
        print("Feedback submitted: Rating \(rating), Feedback: \(feedback)")
        presentationMode.wrappedValue.dismiss()
    }
}
#endif
