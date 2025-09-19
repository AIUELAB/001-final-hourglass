import Foundation
import UIKit

/// Apple App Store Guidelines準拠のエラーハンドリングシステム
/// Guidelines 2.1 (App Completeness) - アプリは適切にエラーを処理する必要がある
class ErrorHandlingSystem {

    static let shared = ErrorHandlingSystem()

    private init() {}

    // MARK: - App Store Guidelines準拠エラー定義

    enum AppStoreCompliantError: LocalizedError {
        case networkUnavailable
        case invalidUserInput(field: String)
        case permissionDenied(permission: String)
        case subscriptionRequired
        case contentNotAvailable
        case serverMaintenance
        case rateLimit
        case incompatibleDevice
        case storageInsufficient
        case userNotAuthenticated

        var errorDescription: String? {
            switch self {
            case .networkUnavailable:
                return "インターネット接続を確認してください"
            case .invalidUserInput(let field):
                return "\(field)の入力内容を確認してください"
            case .permissionDenied(let permission):
                return "\(permission)の許可が必要です。設定から許可してください"
            case .subscriptionRequired:
                return "この機能をご利用いただくには有料プランへのアップグレードが必要です"
            case .contentNotAvailable:
                return "コンテンツが利用できません"
            case .serverMaintenance:
                return "メンテナンス中です。しばらくお待ちください"
            case .rateLimit:
                return "一時的に制限されています。時間をおいて再度お試しください"
            case .incompatibleDevice:
                return "お使いのデバイスはこの機能に対応していません"
            case .storageInsufficient:
                return "ストレージ容量が不足しています"
            case .userNotAuthenticated:
                return "ログインが必要です"
            }
        }

        var recoverySuggestion: String? {
            switch self {
            case .networkUnavailable:
                return "Wi-Fiまたはモバイルデータの接続を確認してください"
            case .invalidUserInput:
                return "正しい形式で入力してください"
            case .permissionDenied:
                return "設定 > プライバシーから許可してください"
            case .subscriptionRequired:
                return "アップグレードボタンをタップして詳細をご確認ください"
            case .contentNotAvailable:
                return "コンテンツが復旧するまでお待ちください"
            case .serverMaintenance:
                return "メンテナンスが完了するまでお待ちください"
            case .rateLimit:
                return "少し時間をおいてから再度お試しください"
            case .incompatibleDevice:
                return "対応デバイスでのご利用をお願いします"
            case .storageInsufficient:
                return "不要なファイルを削除してストレージを確保してください"
            case .userNotAuthenticated:
                return "アカウントにログインしてください"
            }
        }
    }

    // MARK: - ユーザーフレンドリーなエラー表示

    /// App Store Guidelines 2.1準拠のエラーアラート表示
    func showUserFriendlyError(_ error: Error, from viewController: UIViewController, completion: (() -> Void)? = nil) {

        let (title, message, actions) = processError(error)

        let alert = UIAlertController(title: title, message: message, preferredStyle: .alert)

        for action in actions {
            alert.addAction(action)
        }

        // アクセシビリティ対応
        alert.view.accessibilityLabel = title
        alert.view.accessibilityHint = message

        DispatchQueue.main.async {
            viewController.present(alert, animated: true) {
                completion?()
            }
        }

        // エラーログ記録
        logError(error)
    }

    private func processError(_ error: Error) -> (title: String, message: String, actions: [UIAlertAction]) {

        var title = "エラー"
        var message = "予期しないエラーが発生しました"
        var actions: [UIAlertAction] = []

        if let appError = error as? AppStoreCompliantError {
            title = getLocalizedTitle(for: appError)
            message = appError.errorDescription ?? message
            actions = createActionsForError(appError)
        } else {
            // 一般的なエラーをユーザーフレンドリーに変換
            title = "問題が発生しました"
            message = convertGenericError(error)
            actions = [UIAlertAction(title: "OK", style: .default)]
        }

        // 必ず「OK」または代替アクションを含める
        if actions.isEmpty {
            actions.append(UIAlertAction(title: "OK", style: .default))
        }

        return (title, message, actions)
    }

    private func getLocalizedTitle(for error: AppStoreCompliantError) -> String {
        switch error {
        case .networkUnavailable:
            return "接続エラー"
        case .invalidUserInput:
            return "入力エラー"
        case .permissionDenied:
            return "許可が必要"
        case .subscriptionRequired:
            return "プレミアム機能"
        case .contentNotAvailable:
            return "コンテンツなし"
        case .serverMaintenance:
            return "メンテナンス中"
        case .rateLimit:
            return "制限中"
        case .incompatibleDevice:
            return "非対応デバイス"
        case .storageInsufficient:
            return "容量不足"
        case .userNotAuthenticated:
            return "ログインが必要"
        }
    }

    private func createActionsForError(_ error: AppStoreCompliantError) -> [UIAlertAction] {
        switch error {
        case .networkUnavailable:
            return [
                UIAlertAction(title: "再試行", style: .default) { _ in
                    // 再試行処理
                    NotificationCenter.default.post(name: .retryLastAction, object: nil)
                },
                UIAlertAction(title: "後で", style: .cancel)
            ]

        case .permissionDenied:
            return [
                UIAlertAction(title: "設定を開く", style: .default) { _ in
                    if let settingsURL = URL(string: UIApplication.openSettingsURLString) {
                        UIApplication.shared.open(settingsURL)
                    }
                },
                UIAlertAction(title: "キャンセル", style: .cancel)
            ]

        case .subscriptionRequired:
            return [
                UIAlertAction(title: "アップグレード", style: .default) { _ in
                    NotificationCenter.default.post(name: .showSubscriptionView, object: nil)
                },
                UIAlertAction(title: "後で", style: .cancel)
            ]

        case .storageInsufficient:
            return [
                UIAlertAction(title: "設定を開く", style: .default) { _ in
                    if let settingsURL = URL(string: UIApplication.openSettingsURLString) {
                        UIApplication.shared.open(settingsURL)
                    }
                },
                UIAlertAction(title: "OK", style: .cancel)
            ]

        case .userNotAuthenticated:
            return [
                UIAlertAction(title: "ログイン", style: .default) { _ in
                    NotificationCenter.default.post(name: .showLoginView, object: nil)
                },
                UIAlertAction(title: "後で", style: .cancel)
            ]

        default:
            return [UIAlertAction(title: "OK", style: .default)]
        }
    }

    // MARK: - ネットワークエラーハンドリング

    /// ネットワークエラーの詳細処理
    func handleNetworkError(_ error: Error) -> AppStoreCompliantError {
        if let urlError = error as? URLError {
            switch urlError.code {
            case .notConnectedToInternet, .networkConnectionLost:
                return .networkUnavailable
            case .timedOut:
                return .serverMaintenance
            case .cancelled:
                return .contentNotAvailable
            case .cannotFindHost, .cannotConnectToHost:
                return .serverMaintenance
            default:
                return .contentNotAvailable
            }
        }

        return .networkUnavailable
    }

    // MARK: - バックグラウンド処理エラーハンドリング

    /// バックグラウンドタスクでのエラー処理
    func handleBackgroundTaskError(_ error: Error, completion: @escaping () -> Void) {
        // Silent failureの実装（ユーザーに表示しない）
        logError(error)

        // 必要に応じてローカル通知を送信
        scheduleErrorNotification(error)

        completion()
    }

    private func scheduleErrorNotification(_ error: Error) {
        // App Store Guidelines 4.5.4: 適切な通知のみ
        guard shouldNotifyUser(error) else { return }

        let content = UNMutableNotificationContent()
        content.title = "同期エラー"
        content.body = "データの同期中に問題が発生しました。アプリを開いて確認してください。"
        content.sound = .default

        let trigger = UNTimeIntervalNotificationTrigger(timeInterval: 1, repeats: false)
        let request = UNNotificationRequest(identifier: "background_error", content: content, trigger: trigger)

        UNUserNotificationCenter.current().add(request)
    }

    private func shouldNotifyUser(_ error: Error) -> Bool {
        // 通知が必要なエラーのみフィルタリング
        if let appError = error as? AppStoreCompliantError {
            switch appError {
            case .networkUnavailable, .serverMaintenance:
                return false  // ネットワークエラーは通知しない
            case .subscriptionRequired, .storageInsufficient:
                return true   // アクション可能なエラーは通知
            default:
                return false
            }
        }
        return false
    }

    // MARK: - クラッシュ防止

    /// App Store Guidelines 2.1: アプリクラッシュの防止
    func safeExecute<T>(_ operation: () throws -> T, fallback: T) -> T {
        do {
            return try operation()
        } catch {
            logError(error)
            return fallback
        }
    }

    /// 非同期処理の安全実行
    func safeExecuteAsync<T>(_ operation: @escaping () async throws -> T, fallback: T) async -> T {
        do {
            return try await operation()
        } catch {
            logError(error)
            return fallback
        }
    }

    // MARK: - エラーログ記録

    private func logError(_ error: Error) {
        let errorInfo = [
            "error": String(describing: error),
            "timestamp": ISO8601DateFormatter().string(from: Date()),
            "app_version": Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "Unknown",
            "ios_version": UIDevice.current.systemVersion,
            "device_model": UIDevice.current.model
        ]

        // App Store Guidelines 5.1.2: プライバシーを考慮したログ記録
        print("Error Log: \(errorInfo)")

        // クラッシュレポートツール（Crashlytics等）への送信
        // ただし、個人識別情報は含めない
    }

    private func convertGenericError(_ error: Error) -> String {
        // 一般的なエラーをユーザーフレンドリーなメッセージに変換
        let errorDescription = error.localizedDescription.lowercased()

        if errorDescription.contains("network") || errorDescription.contains("internet") {
            return "インターネット接続を確認してください"
        } else if errorDescription.contains("permission") || errorDescription.contains("authorization") {
            return "必要な許可が得られていません"
        } else if errorDescription.contains("timeout") {
            return "処理がタイムアウトしました。再度お試しください"
        } else {
            return "一時的な問題が発生しました。しばらくお待ちください"
        }
    }
}

// MARK: - 通知名定義

extension Notification.Name {
    static let retryLastAction = Notification.Name("retryLastAction")
    static let showSubscriptionView = Notification.Name("showSubscriptionView")
    static let showLoginView = Notification.Name("showLoginView")
}

// MARK: - グローバルエラーハンドラー

/// アプリ全体でキャッチされなかったエラーを処理
class GlobalErrorHandler {

    static let shared = GlobalErrorHandler()

    private init() {
        setupGlobalErrorHandling()
    }

    private func setupGlobalErrorHandling() {
        // NSSetUncaughtExceptionHandler は App Store で制限される場合があるため注意
        // 代替案：各処理で適切な try-catch を実装

        // メイン隊列での未処理エラーをキャッチ
        Thread.setThreadDictionary([
            "ErrorHandler": self
        ])
    }

    func handleUncaughtError(_ error: Error) {
        // App Store Guidelines 2.1: 適切な復旧処理
        ErrorHandlingSystem.shared.logError(error)

        // アプリの状態を安全な状態に復元
        DispatchQueue.main.async {
            self.restoreAppToSafeState()
        }
    }

    private func restoreAppToSafeState() {
        // アプリをホーム画面または安全な状態に復元
        if let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
           let window = windowScene.windows.first {

            // ルートビューコントローラーにリセット
            let storyboard = UIStoryboard(name: "Main", bundle: nil)
            if let rootVC = storyboard.instantiateInitialViewController() {
                window.rootViewController = rootVC
            }
        }
    }
}
