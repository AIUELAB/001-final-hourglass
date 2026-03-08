import SwiftUI
import UIKit
import UserNotifications

@main
struct FinalHourglassApp: App {
    @StateObject private var userModel = UserModel()
    @StateObject private var appStateManager = AppStateManager()

    init() {
        // 通知のカテゴリーとアクションを設定
        setupNotificationCategories()

        // サウンドと振動のデフォルト設定（初回起動時のみ）
        setupDefaultSettings()

        setupTabBarAppearance()

        // Supabase接続テスト（DEBUG時のみ）
        #if DEBUG
        if SupabaseConfig.isSupabaseEnabled {
            Task {
                let success = await SupabaseManager.shared.testConnection()
                print(success ? "✅ Supabase接続成功" : "❌ Supabase接続失敗")
            }
        }
        #endif
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(userModel)
                .environmentObject(appStateManager)
                .onAppear {  // MARK: - 追加開始
                    // アプリ起動時にバッジをクリア
                    appStateManager.clearNotificationBadge()

                    // 通知の状態を確認
                    appStateManager.checkNotificationStatus { status in
                        #if DEBUG
                        print("通知の許可状態: \(status.rawValue)")
                        #endif
                    }
                }
                .onReceive(NotificationCenter.default.publisher(for: UIApplication.willEnterForegroundNotification)) { _ in
                    // アプリがフォアグラウンドに戻ったときもバッジをクリア
                    appStateManager.clearNotificationBadge()
                }  // MARK: - 追加終了
        }
    }

    // MARK: - 通知設定メソッドを追加
    private func setupNotificationCategories() {
        // "今すぐ確認"アクション
        let checkAction = UNNotificationAction(
            identifier: "CHECK_ACTION",
            title: "今すぐ確認",
            options: [.foreground]
        )

        // "後で"アクション
        let laterAction = UNNotificationAction(
            identifier: "LATER_ACTION",
            title: "後で",
            options: []
        )

        // カテゴリーを作成
        let reminderCategory = UNNotificationCategory(
            identifier: "REMINDER_CATEGORY",
            actions: [checkAction, laterAction],
            intentIdentifiers: [],
            options: []
        )

        // カテゴリーを登録
        UNUserNotificationCenter.current().setNotificationCategories([reminderCategory])
    }

    // MARK: - デフォルト設定の初期化
    private func setupDefaultSettings() {
        let defaults = UserDefaults.standard

        // 初回起動時のみ設定（すでに値がある場合はスキップ）
        if defaults.object(forKey: "soundEnabled") == nil {
            defaults.set(true, forKey: "soundEnabled")  // サウンド効果をデフォルトでON
        }

        if defaults.object(forKey: "hapticEnabled") == nil {
            defaults.set(true, forKey: "hapticEnabled")  // 振動フィードバックをデフォルトでON
        }

        // その他の設定もここで初期化可能
        defaults.synchronize()
    }

    private func setupTabBarAppearance() {
        // iOS 15以降の新しいAPI
        if #available(iOS 15.0, *) {
            let appearance = UITabBarAppearance()
            appearance.configureWithOpaqueBackground()
            appearance.backgroundColor = UIColor.systemBackground

            // 通常状態のアイテムの色
            appearance.stackedLayoutAppearance.normal.iconColor = UIColor.systemGray
            appearance.stackedLayoutAppearance.normal.titleTextAttributes = [
                NSAttributedString.Key.foregroundColor: UIColor.systemGray
            ]

            // 選択状態のアイテムの色
            appearance.stackedLayoutAppearance.selected.iconColor = UIColor.systemBlue
            appearance.stackedLayoutAppearance.selected.titleTextAttributes = [
                NSAttributedString.Key.foregroundColor: UIColor.systemBlue
            ]

            UITabBar.appearance().standardAppearance = appearance
            UITabBar.appearance().scrollEdgeAppearance = appearance
        } else {
            // iOS 14以前の設定
            UITabBar.appearance().barTintColor = UIColor.systemBackground
            UITabBar.appearance().tintColor = UIColor.systemBlue
            UITabBar.appearance().unselectedItemTintColor = UIColor.systemGray
        }
    }
}
