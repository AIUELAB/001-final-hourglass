import SwiftUI
import UIKit
import UserNotifications

class AppStateManager: ObservableObject {
    // セッショントラッキング用
    private var sessionStartTime: Date?
    // periphery:ignore - State tracking for app lifecycle
    private var lastActiveDate: Date?

    // リセット中フラグ（画面遷移中の音声再生を防ぐため）
    @Published var isResetting: Bool = false

    @Published var isFirstLaunch: Bool {
        didSet {
            UserDefaults.standard.set(!isFirstLaunch, forKey: "hasLaunchedBefore")
        }
    }

    @Published var hasCompletedOnboarding: Bool {
        didSet {
            UserDefaults.standard.set(hasCompletedOnboarding, forKey: "hasCompletedOnboarding")
        }
    }

    @Published var notificationsEnabled: Bool {
        didSet {
            UserDefaults.standard.set(notificationsEnabled, forKey: "notificationsEnabled")
        }
    }

    @Published var reminderEnabled: Bool {
        didSet {
            UserDefaults.standard.set(reminderEnabled, forKey: "reminderEnabled")
        }
    }

    @Published var reminderTime: Date {
        didSet {
            UserDefaults.standard.set(reminderTime, forKey: "reminderTime")
        }
    }

    init() {
        // 初回起動チェック
        let hasLaunchedBefore = UserDefaults.standard.bool(forKey: "hasLaunchedBefore")
        self.isFirstLaunch = !hasLaunchedBefore

        // オンボーディング完了チェック
        self.hasCompletedOnboarding = UserDefaults.standard.bool(forKey: "hasCompletedOnboarding")

        // 通知設定
        self.notificationsEnabled = UserDefaults.standard.bool(forKey: "notificationsEnabled")

        // リマインダー設定（デフォルトはtrue）
        if UserDefaults.standard.object(forKey: "reminderEnabled") != nil {
            self.reminderEnabled = UserDefaults.standard.bool(forKey: "reminderEnabled")
        } else {
            self.reminderEnabled = true  // デフォルトでON
        }

        // リマインダー時刻（デフォルトは朝8:30）
        if let savedTime = UserDefaults.standard.object(forKey: "reminderTime") as? Date {
            self.reminderTime = savedTime
        } else {
            let calendar = Calendar.current
            let components = DateComponents(hour: 8, minute: 30)
            self.reminderTime = calendar.date(from: components) ?? Date()
        }

        // MARK: - UITest Launch Arguments
        #if DEBUG
        if ProcessInfo.processInfo.arguments.contains("-UITest_ResetState") {
            if let bundleIdentifier = Bundle.main.bundleIdentifier {
                UserDefaults.standard.removePersistentDomain(forName: bundleIdentifier)
                UserDefaults.standard.synchronize()
            }
            self.isFirstLaunch = true
            self.hasCompletedOnboarding = false
        }
        if ProcessInfo.processInfo.arguments.contains("-UITest_SkipOnboarding") {
            self.hasCompletedOnboarding = true
            self.isFirstLaunch = false
        }
        if ProcessInfo.processInfo.arguments.contains("-UITest_DisableAnimations") {
            UIView.setAnimationsEnabled(false)
        }
        #endif
    }

    // アプリをリセットする関数
    func resetApp() {
        // リセット開始を示すフラグを立てる
        self.isResetting = true

        // UserDefaultsの全データをクリア
        if let bundleIdentifier = Bundle.main.bundleIdentifier {
            UserDefaults.standard.removePersistentDomain(forName: bundleIdentifier)
            UserDefaults.standard.synchronize()
        }

        // 通知をすべてキャンセル
        UNUserNotificationCenter.current().removeAllPendingNotificationRequests()
        UNUserNotificationCenter.current().removeAllDeliveredNotifications()

        // プロパティを初期値にリセット
        self.isFirstLaunch = true
        self.hasCompletedOnboarding = false
        self.notificationsEnabled = false
        self.reminderEnabled = true  // デフォルトでON

        // リマインダー時刻をデフォルトに戻す
        let calendar = Calendar.current
        let components = DateComponents(hour: 8, minute: 30)
        self.reminderTime = calendar.date(from: components) ?? Date()

        // 画面遷移アニメーションが完了した後にリセットフラグを下ろす
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            self.isResetting = false
        }
    }

    // MARK: - 通知関連のメソッド

    // 通知権限をリクエスト
    func requestNotificationPermission(completion: @escaping (Bool) -> Void) {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .badge, .sound]) { granted, error in
            DispatchQueue.main.async {
                self.notificationsEnabled = granted
                completion(granted)
                if granted {
                    print("通知権限が許可されました")
                } else {
                    print("通知権限が拒否されました: \(error?.localizedDescription ?? "不明なエラー")")
                }
            }
        }
    }

    // リマインダーをスケジュール
    func scheduleReminder() {
        guard reminderEnabled else { return }

        // 既存のリマインダーをキャンセル
        cancelReminder()

        // ユーザーの年齢を計算
        let userAge = calculateUserAge()

        // エピソードを取得してから通知をスケジュール
        fetchEpisodeForNotification(age: userAge) { [weak self] personName, episode in
            guard let self = self else { return }

            // 新しいリマインダーを設定
            let content = UNMutableNotificationContent()
            content.title = "最期の砂時計"

            // エピソードがある場合は含める
            if let personName = personName, let episode = episode {
                content.subtitle = "あなたと同じ\(userAge)歳のとき、\(personName)は"
                content.body = episode
            } else {
                // エピソードがない場合はデフォルトメッセージ
                content.body = "今日も一日を大切に。あなたの残された時間を確認しましょう。"
            }

            content.sound = .default
            content.badge = 1

            // カテゴリーを設定（アクション付き通知用）
            content.categoryIdentifier = "REMINDER_CATEGORY"

            // 時刻を取得
            let calendar = Calendar.current
            var dateComponents = calendar.dateComponents([.hour, .minute], from: self.reminderTime)
            dateComponents.second = 0

            // 毎日繰り返すトリガーを作成
            let trigger = UNCalendarNotificationTrigger(dateMatching: dateComponents, repeats: true)

            // リクエストを作成
            let request = UNNotificationRequest(
                identifier: "daily_reminder",
                content: content,
                trigger: trigger
            )

            // 通知センターに追加
            UNUserNotificationCenter.current().add(request) { error in
                if let error = error {
                    print("通知のスケジュールに失敗: \(error.localizedDescription)")
                } else {
                    let hour = dateComponents.hour ?? 0
                    let minute = String(format: "%02d", dateComponents.minute ?? 0)
                    print("通知をスケジュールしました: 毎日 \(hour):\(minute)")
                }
            }
        }
    }

    // リマインダーをキャンセル
    func cancelReminder() {
        UNUserNotificationCenter.current().removePendingNotificationRequests(withIdentifiers: ["daily_reminder"])
        UNUserNotificationCenter.current().removeDeliveredNotifications(withIdentifiers: ["daily_reminder"])
        print("既存の通知をキャンセルしました")
    }

    // 通知設定の状態を確認
    func checkNotificationStatus(completion: @escaping (UNAuthorizationStatus) -> Void) {
        UNUserNotificationCenter.current().getNotificationSettings { settings in
            DispatchQueue.main.async {
                completion(settings.authorizationStatus)
            }
        }
    }

    // アプリ起動時の通知バッジをクリア
    func clearNotificationBadge() {
        if #available(iOS 16.0, *) {
            // iOS 16.0以降の新しい方法
            UNUserNotificationCenter.current().setBadgeCount(0) { error in
                if let error = error {
                    print("バッジのクリアに失敗: \(error.localizedDescription)")
                }
            }
        } else {
            // iOS 15以前の従来の方法
            UIApplication.shared.applicationIconBadgeNumber = 0
        }

        // 配信済み通知をクリア
        UNUserNotificationCenter.current().removeAllDeliveredNotifications()
    }

    // MARK: - App Lifecycle Methods

    // アプリがバックグラウンドに移行した時の処理
    func appDidEnterBackground() {
        // 現在の状態を保存
        UserDefaults.standard.synchronize()

        // セッション時間をトラッキング
        endSession()
    }

    // アプリがフォアグラウンドに復帰した時の処理
    func appWillEnterForeground() {
        // 通知権限の状態を再確認
        checkNotificationPermissions()
        // バッジをクリア
        clearNotificationBadge()

        // 新しいセッションを開始
        startSession()
    }

    // 通知権限の確認
    private func checkNotificationPermissions() {
        UNUserNotificationCenter.current().getNotificationSettings { settings in
            DispatchQueue.main.async {
                self.notificationsEnabled = settings.authorizationStatus == .authorized

                // リマインダーが有効で通知権限がない場合は無効化
                if self.reminderEnabled && settings.authorizationStatus != .authorized {
                    self.reminderEnabled = false
                }
            }
        }
    }

    // MARK: - Analytics Helper Methods

    private func startSession() {
        sessionStartTime = Date()

        // 日次アクティブユーザーをトラッキング
        trackDailyActiveUser()

        // アプリ起動をトラッキング
        AnalyticsManager.shared.trackAppLaunch()
    }

    private func endSession() {
        guard let startTime = sessionStartTime else { return }

        let duration = Date().timeIntervalSince(startTime)
        AnalyticsManager.shared.trackSessionDuration(duration: duration)

        sessionStartTime = nil
    }

    private func trackDailyActiveUser() {
        let today = Calendar.current.startOfDay(for: Date())
        let lastActive = UserDefaults.standard.object(forKey: "lastActiveDate") as? Date

        if lastActive == nil || !Calendar.current.isDate(lastActive!, inSameDayAs: today) {
            // 新しい日のアクティブユーザー
            AnalyticsManager.shared.trackDailyActive()

            // 連続使用日数を計算
            if let lastActive = lastActive {
                let daysBetween = Calendar.current.dateComponents([.day], from: lastActive, to: today).day ?? 0
                if daysBetween == 1 {
                    // 連続使用
                    let currentStreak = UserDefaults.standard.integer(forKey: "usageStreak") + 1
                    UserDefaults.standard.set(currentStreak, forKey: "usageStreak")
                    AnalyticsManager.shared.trackStreakDays(currentStreak)
                } else {
                    // 連続が途切れた
                    UserDefaults.standard.set(1, forKey: "usageStreak")
                }
            } else {
                // 初回使用
                UserDefaults.standard.set(1, forKey: "usageStreak")
            }

            UserDefaults.standard.set(today, forKey: "lastActiveDate")
        }
    }

    // MARK: - エピソード取得機能

    // 通知用のエピソードを取得
    func fetchEpisodeForNotification(age: Int, completion: @escaping (String?, String?) -> Void) {
        // EpisodeManager経由でSupabaseからエピソードを取得
        EpisodeManager.shared.getDailyEpisode(for: age) { episode in
            if let episode = episode {
                completion(episode.personName, episode.episode)
            } else {
                completion(nil, nil)
            }
        }
    }

    // ユーザーの現在の年齢を計算
    func calculateUserAge() -> Int {
        // UserModelから生年月日を取得（UserDefaultsから）
        let birthYear = UserDefaults.standard.integer(forKey: "birthYear")
        let birthMonth = UserDefaults.standard.integer(forKey: "birthMonth")
        let birthDay = UserDefaults.standard.integer(forKey: "birthDay")

        guard birthYear > 0, birthMonth > 0, birthDay > 0 else {
            // デフォルト値として30歳を返す
            return 30
        }

        let calendar = Calendar.current
        let birthComponents = DateComponents(year: birthYear, month: birthMonth, day: birthDay)

        guard let birthDate = calendar.date(from: birthComponents) else {
            return 30
        }

        let ageComponents = calendar.dateComponents([.year], from: birthDate, to: Date())
        return ageComponents.year ?? 30
    }
}
