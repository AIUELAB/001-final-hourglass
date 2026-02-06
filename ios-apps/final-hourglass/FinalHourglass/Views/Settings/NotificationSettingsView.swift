import SwiftUI
import UserNotifications

struct NotificationSettingsView: View {
    @EnvironmentObject var notificationManager: NotificationManager

    // 通知設定の状態
    @State private var isDailyNotificationEnabled = false
    @State private var notificationTime = Date()
    @State private var selectedNotificationType = NotificationType.motivation
    @State private var showingNotificationDeniedAlert = false
    @State private var notificationAuthStatus: UNAuthorizationStatus = .notDetermined

    // 通知タイプ
    enum NotificationType: String, CaseIterable {
        case motivation = "モチベーション"
        case episode = "偉人エピソード"
        case health = "健康リマインダー"
        case mixed = "ミックス"

        var description: String {
            switch self {
            case .motivation:
                return "日々の励ましとなるメッセージ"
            case .episode:
                return "同年齢の偉人のエピソード"
            case .health:
                return "健康習慣のリマインダー"
            case .mixed:
                return "すべてのタイプをランダムに"
            }
        }

        var icon: String {
            switch self {
            case .motivation: return "sparkles"
            case .episode: return "book.fill"
            case .health: return "heart.text.square.fill"
            case .mixed: return "shuffle"
            }
        }
    }

    var body: some View {
        ZStack {
            // 背景
            Color.black
                .edgesIgnoringSafeArea(.all)

            ScrollView {
                VStack(spacing: 24) {
                    // 通知許可状態
                    notificationStatusSection

                    // デイリー通知設定
                    if notificationAuthStatus == .authorized {
                        dailyNotificationSection

                        // 通知タイプ選択
                        if isDailyNotificationEnabled {
                            notificationTypeSection
                        }

                        // テスト通知
                        testNotificationSection
                    }

                    // 通知履歴
                    notificationHistorySection
                }
                .padding()
            }
        }
        .navigationTitle("通知設定")
        .navigationBarTitleDisplayMode(.inline)
        .preferredColorScheme(.dark)
        .onAppear {
            loadSettings()
            checkNotificationStatus()
        }
        .alert("通知が無効になっています", isPresented: $showingNotificationDeniedAlert) {
            Button("設定を開く") {
                if let url = URL(string: UIApplication.openSettingsURLString) {
                    UIApplication.shared.open(url)
                }
            }
            Button("キャンセル", role: .cancel) {}
        } message: {
            Text("通知を有効にするには、設定アプリで通知を許可してください。")
        }
    }

    // MARK: - 通知許可状態セクション
    private var notificationStatusSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Image(systemName: "bell.badge")
                    .foregroundColor(.red)
                Text("通知の状態")
                    .font(.headline)
                    .foregroundColor(.white)
            }

            HStack {
                Image(systemName: notificationAuthStatus == .authorized ? "checkmark.circle.fill" : "xmark.circle.fill")
                    .foregroundColor(notificationAuthStatus == .authorized ? .green : .red)
                    .font(.title2)

                VStack(alignment: .leading, spacing: 4) {
                    Text(notificationStatusText)
                        .font(.subheadline)
                        .foregroundColor(.white)

                    if notificationAuthStatus != .authorized {
                        Button(action: requestNotificationPermission) {
                            Text("通知を許可する")
                                .font(.caption)
                                .foregroundColor(.blue)
                        }
                    }
                }

                Spacer()
            }
            .padding()
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(Color.white.opacity(0.05))
            )
        }
    }

    // MARK: - デイリー通知設定セクション
    private var dailyNotificationSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Image(systemName: "calendar.badge.clock")
                    .foregroundColor(.red)
                Text("デイリーリマインダー")
                    .font(.headline)
                    .foregroundColor(.white)
            }

            VStack(spacing: 16) {
                // 通知ON/OFFトグル
                Toggle(isOn: $isDailyNotificationEnabled) {
                    HStack {
                        Image(systemName: "bell")
                            .foregroundColor(.orange)
                        Text("毎日の通知")
                            .foregroundColor(.white)
                    }
                }
                .toggleStyle(SwitchToggleStyle(tint: .red))
                .onChange(of: isDailyNotificationEnabled) { newValue in
                    if newValue {
                        enableDailyNotification()
                    } else {
                        disableDailyNotification()
                    }
                }

                // 時刻選択
                if isDailyNotificationEnabled {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("通知時刻")
                            .font(.subheadline)
                            .foregroundColor(.gray)

                        DatePicker(
                            "",
                            selection: $notificationTime,
                            displayedComponents: .hourAndMinute
                        )
                        .datePickerStyle(WheelDatePickerStyle())
                        .labelsHidden()
                        .colorScheme(.dark)
                        .frame(height: 120)
                        .onChange(of: notificationTime) { newValue in
                            updateNotificationTime(newValue)
                        }

                        // 選択された時刻の表示
                        HStack {
                            Image(systemName: "clock")
                                .foregroundColor(.gray)
                            Text("毎日 \(formattedTime) に通知します")
                                .font(.caption)
                                .foregroundColor(.gray)
                        }
                    }
                    .padding()
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(Color.white.opacity(0.03))
                    )
                }
            }
            .padding()
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(Color.white.opacity(0.05))
            )
        }
    }

    // MARK: - 通知タイプ選択セクション
    private var notificationTypeSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Image(systemName: "text.bubble")
                    .foregroundColor(.red)
                Text("通知の種類")
                    .font(.headline)
                    .foregroundColor(.white)
            }

            VStack(spacing: 12) {
                ForEach(NotificationType.allCases, id: \.self) { type in
                    NotificationTypeRow(
                        type: type,
                        isSelected: selectedNotificationType == type,
                        action: {
                            selectedNotificationType = type
                            saveNotificationType(type)
                        }
                    )
                }
            }
            .padding()
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(Color.white.opacity(0.05))
            )
        }
    }

    // MARK: - テスト通知セクション
    private var testNotificationSection: some View {
        VStack(spacing: 12) {
            Button(action: sendTestNotification) {
                HStack {
                    Image(systemName: "bell.badge")
                    Text("テスト通知を送信")
                    Spacer()
                    Image(systemName: "paperplane")
                }
                .foregroundColor(.white)
                .padding()
                .background(
                    RoundedRectangle(cornerRadius: 12)
                        .fill(Color.blue.opacity(0.8))
                )
            }

            Text("5秒後にテスト通知が届きます")
                .font(.caption)
                .foregroundColor(.gray)
        }
    }

    // MARK: - 通知履歴セクション
    private var notificationHistorySection: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Image(systemName: "clock.arrow.circlepath")
                    .foregroundColor(.red)
                Text("通知履歴")
                    .font(.headline)
                    .foregroundColor(.white)
            }

            VStack(alignment: .leading, spacing: 8) {
                if let lastNotificationDate = notificationManager.lastNotificationDate {
                    HStack {
                        Text("最後の通知:")
                            .font(.caption)
                            .foregroundColor(.gray)

                        Text(formattedDate(lastNotificationDate))
                            .font(.caption)
                            .foregroundColor(.white)
                    }
                } else {
                    Text("まだ通知を送信していません")
                        .font(.caption)
                        .foregroundColor(.gray)
                }

                HStack {
                    Text("連続記録:")
                        .font(.caption)
                        .foregroundColor(.gray)

                    Text("\(notificationManager.getCurrentStreak())日")
                        .font(.caption)
                        .fontWeight(.bold)
                        .foregroundColor(.orange)
                }
            }
            .padding()
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(Color.white.opacity(0.05))
            )
        }
    }

    // MARK: - Helper Properties
    private var notificationStatusText: String {
        switch notificationAuthStatus {
        case .authorized:
            return "通知が有効です"
        case .denied:
            return "通知が無効になっています"
        case .notDetermined:
            return "通知の許可が必要です"
        case .provisional:
            return "仮の通知許可"
        case .ephemeral:
            return "一時的な通知許可"
        @unknown default:
            return "不明な状態"
        }
    }

    private var formattedTime: String {
        let formatter = DateFormatter()
        formatter.timeStyle = .short
        formatter.locale = Locale(identifier: "ja_JP")
        return formatter.string(from: notificationTime)
    }

    // MARK: - Helper Functions
    private func loadSettings() {
        isDailyNotificationEnabled = notificationManager.isDailyNotificationEnabled
        notificationTime = notificationManager.dailyNotificationTime

        if let savedType = UserDefaults.standard.string(forKey: "selectedNotificationType"),
           let type = NotificationType(rawValue: savedType) {
            selectedNotificationType = type
        }
    }

    private func checkNotificationStatus() {
        UNUserNotificationCenter.current().getNotificationSettings { settings in
            DispatchQueue.main.async {
                self.notificationAuthStatus = settings.authorizationStatus
            }
        }
    }

    private func requestNotificationPermission() {
        notificationManager.requestAuthorization { granted in
            DispatchQueue.main.async {
                if granted {
                    self.checkNotificationStatus()
                } else {
                    self.showingNotificationDeniedAlert = true
                }
            }
        }
    }

    private func enableDailyNotification() {
        notificationManager.enableDailyNotification(at: notificationTime)
    }

    private func disableDailyNotification() {
        notificationManager.disableDailyNotification()
    }

    private func updateNotificationTime(_ time: Date) {
        if isDailyNotificationEnabled {
            notificationManager.updateDailyNotificationTime(to: time)
        }
    }

    private func saveNotificationType(_ type: NotificationType) {
        UserDefaults.standard.set(type.rawValue, forKey: "selectedNotificationType")
    }

    private func sendTestNotification() {
        notificationManager.sendTestNotification()
    }

    private func formattedDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        formatter.locale = Locale(identifier: "ja_JP")
        return formatter.string(from: date)
    }
}

// MARK: - Supporting Views
struct NotificationTypeRow: View {
    let type: NotificationSettingsView.NotificationType
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 16) {
                Image(systemName: type.icon)
                    .foregroundColor(isSelected ? .red : .gray)
                    .font(.system(size: 20))
                    .frame(width: 30)

                VStack(alignment: .leading, spacing: 4) {
                    Text(type.rawValue)
                        .font(.subheadline)
                        .fontWeight(isSelected ? .semibold : .regular)
                        .foregroundColor(isSelected ? .white : .gray)

                    Text(type.description)
                        .font(.caption)
                        .foregroundColor(.gray)
                }

                Spacer()

                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.red)
                }
            }
            .padding()
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(isSelected ? Color.red.opacity(0.1) : Color.white.opacity(0.03))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(isSelected ? Color.red.opacity(0.3) : Color.clear, lineWidth: 1)
            )
        }
        .buttonStyle(PlainButtonStyle())
    }
}
