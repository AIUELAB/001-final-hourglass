// periphery:ignore:all - 将来使用予定のUIコンポーネント
import Foundation
import SwiftUI
import UserNotifications

class NotificationManager: NSObject, ObservableObject {
    static let shared = NotificationManager()

    @Published var isNotificationEnabled = false
    @Published var notificationTime = Date()
    @Published var notificationFrequency = "daily"
    @Published var lastNotificationDate: Date?

    private let notificationCenter = UNUserNotificationCenter.current()
    private var userModel: UserModel?

    // NotificationSettingsViewで使用されるプロパティ
    var isDailyNotificationEnabled: Bool {
        get { isNotificationEnabled }
        set { isNotificationEnabled = newValue }
    }

    var dailyNotificationTime: Date {
        get { notificationTime }
        set { notificationTime = newValue }
    }

    override init() {
        super.init()
        notificationCenter.delegate = self
        loadNotificationSettings()
        checkNotificationStatus()
    }

    // 依存性を設定
    func configure(userModel: UserModel) {
        self.userModel = userModel
    }

    // 通知権限をリクエスト
    func requestNotificationPermission() {
        notificationCenter.requestAuthorization(options: [.alert, .badge, .sound]) { [weak self] granted, _ in
            DispatchQueue.main.async {
                self?.isNotificationEnabled = granted
                if granted {
                    self?.scheduleDailyNotification()
                }
            }
        }
    }

    // NotificationSettingsViewで使用されるメソッド
    func requestAuthorization(completion: @escaping (Bool) -> Void) {
        notificationCenter.requestAuthorization(options: [.alert, .badge, .sound]) { granted, _ in
            DispatchQueue.main.async {
                self.isNotificationEnabled = granted
                completion(granted)
            }
        }
    }

    func enableDailyNotification(at time: Date) {
        notificationTime = time
        isNotificationEnabled = true
        scheduleDailyNotification()
    }

    func disableDailyNotification() {
        isNotificationEnabled = false
        cancelNotifications()
    }

    func updateDailyNotificationTime(to time: Date) {
        notificationTime = time
        if isNotificationEnabled {
            scheduleDailyNotification()
        }
    }

    func sendTestNotification() {
        let content = UNMutableNotificationContent()
        content.title = "🧪 テスト通知"
        content.body = "通知設定が正常に動作しています！"
        content.sound = .default

        let trigger = UNTimeIntervalNotificationTrigger(timeInterval: 5, repeats: false)
        let request = UNNotificationRequest(identifier: "test_notification", content: content, trigger: trigger)

        notificationCenter.add(request) { error in
            if let error = error {
                print("テスト通知エラー: \(error)")
            }
        }
    }

    func getCurrentStreak() -> Int {
        // 簡易的な連続記録計算
        let streakKey = "notificationStreak"
        return UserDefaults.standard.integer(forKey: streakKey)
    }

    // 通知ステータスを確認
    func checkNotificationStatus() {
        notificationCenter.getNotificationSettings { [weak self] settings in
            DispatchQueue.main.async {
                self?.isNotificationEnabled = settings.authorizationStatus == .authorized
            }
        }
    }

    // 毎日の通知をスケジュール
    func scheduleDailyNotification() {
        // 既存の通知をキャンセル
        notificationCenter.removeAllPendingNotificationRequests()

        guard isNotificationEnabled,
              let userModel = userModel else { return }

        // 通知内容を作成
        let content = UNMutableNotificationContent()
        content.title = "🏛️ 今日の著名人の知恵"
        content.sound = .default
        content.badge = 1

        // 残り時間を計算
        let lifeExpectancy = calculateLifeExpectancy(for: userModel)
        let remainingDays = calculateRemainingDays(birthDate: userModel.birthDate, lifeExpectancy: lifeExpectancy)

        // シンプルな通知内容
        content.subtitle = "残り時間：\(formatRemainingTime(days: remainingDays))"
        content.body = "アプリを開いて、今日の著名人の知恵を確認しましょう"

        // 通知カテゴリーを設定
        content.categoryIdentifier = "DAILY_EPISODE"
        content.userInfo = ["type": "daily_calendar"]

        // トリガーを作成（毎日指定時刻）
        let dateComponents = Calendar.current.dateComponents([.hour, .minute], from: notificationTime)
        let trigger = UNCalendarNotificationTrigger(dateMatching: dateComponents, repeats: true)

        // リクエストを作成
        let request = UNNotificationRequest(
            identifier: "daily_episode_notification",
            content: content,
            trigger: trigger
        )

        // 通知をスケジュール
        notificationCenter.add(request) { [weak self] error in
            if let error = error {
                print("通知のスケジュールエラー: \(error)")
            } else {
                print("通知をスケジュールしました")
                DispatchQueue.main.async {
                    self?.lastNotificationDate = Date()
                }
            }
        }

        // 設定を保存
        saveNotificationSettings()
    }

    // 通知をキャンセル
    func cancelNotifications() {
        notificationCenter.removeAllPendingNotificationRequests()
        isNotificationEnabled = false
        saveNotificationSettings()
    }

    // 通知時間を更新
    func updateNotificationTime(_ newTime: Date) {
        notificationTime = newTime
        if isNotificationEnabled {
            scheduleDailyNotification()
        }
    }

    // 残り時間をフォーマット
    func formatRemainingTime(days: Int) -> String {
        if days < 365 {
            return "\(days)日"
        } else {
            let years = days / 365
            let months = (days % 365) / 30
            if months > 0 {
                return "\(years)年\(months)ヶ月"
            } else {
                return "\(years)年"
            }
        }
    }

    // 寿命計算（簡易版）
    func calculateLifeExpectancy(for userModel: UserModel) -> Double {
        // 基本寿命
        var lifeExpectancy = userModel.gender == "male" ? 81.64 : 87.74

        // 喫煙による影響
        if userModel.smokingStatus == "smoker" {
            lifeExpectancy -= 10
        } else if userModel.smokingStatus == "ex_smoker" {
            lifeExpectancy -= 3
        }

        // 運動による影響
        if userModel.exerciseFrequency == "rarely" {
            lifeExpectancy -= 3
        } else if userModel.exerciseFrequency == "daily" {
            lifeExpectancy += 2
        }

        return lifeExpectancy
    }

    // 残り日数を計算
    func calculateRemainingDays(birthDate: Date, lifeExpectancy: Double) -> Int {
        let calendar = Calendar.current
        let deathDate = calendar.date(byAdding: .year, value: Int(lifeExpectancy), to: birthDate) ?? Date()
        let components = calendar.dateComponents([.day], from: Date(), to: deathDate)
        return max(0, components.day ?? 0)
    }

    // 設定を保存
    private func saveNotificationSettings() {
        UserDefaults.standard.set(isNotificationEnabled, forKey: "isNotificationEnabled")
        UserDefaults.standard.set(notificationTime, forKey: "notificationTime")
        UserDefaults.standard.set(notificationFrequency, forKey: "notificationFrequency")
        if let lastDate = lastNotificationDate {
            UserDefaults.standard.set(lastDate, forKey: "lastNotificationDate")
        }
    }

    // 設定を読み込み
    private func loadNotificationSettings() {
        isNotificationEnabled = UserDefaults.standard.bool(forKey: "isNotificationEnabled")
        if let savedTime = UserDefaults.standard.object(forKey: "notificationTime") as? Date {
            notificationTime = savedTime
        } else {
            // デフォルトは朝7時
            var components = DateComponents()
            components.hour = 7
            components.minute = 0
            notificationTime = Calendar.current.date(from: components) ?? Date()
        }
        notificationFrequency = UserDefaults.standard.string(forKey: "notificationFrequency") ?? "daily"
        lastNotificationDate = UserDefaults.standard.object(forKey: "lastNotificationDate") as? Date
    }
}

// MARK: - UNUserNotificationCenterDelegate
extension NotificationManager: UNUserNotificationCenterDelegate {
    // フォアグラウンドで通知を受信した時の処理
    func userNotificationCenter(
            _ center: UNUserNotificationCenter,
            willPresent notification: UNNotification,
            withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void
          ) {
        // フォアグラウンドでも通知を表示
        completionHandler([.banner, .sound, .badge])
    }

    // 通知をタップした時の処理
    func userNotificationCenter(
            _ center: UNUserNotificationCenter,
            didReceive response: UNNotificationResponse,
            withCompletionHandler completionHandler: @escaping () -> Void
          ) {
        let userInfo = response.notification.request.content.userInfo

        // エピソードIDを取得して画面遷移
        if let episodeId = userInfo["episodeId"] as? String {
            // エピソード詳細画面への遷移（実装予定）
            print("エピソードID: \(episodeId) を開く")
        }

        completionHandler()
    }

    /// エピソードの表示用名前を取得
    private func getDisplayName(for episode: Episode) -> String {
        // personNameJaが存在し、空でない場合は日本語名を使用
        if let jaName = episode.personNameJa, !jaName.isEmpty {
            return jaName
        }
        // そうでなければ英語名を使用
        return episode.personName
    }
}
