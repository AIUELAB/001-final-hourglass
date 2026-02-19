import SwiftUI

struct MainTabView: View {
    // periphery:ignore - View dependency/styling
    @EnvironmentObject var userModel: UserModel
    @EnvironmentObject var appStateManager: AppStateManager
    @State private var selectedTab: Int = 0
    @State private var hasAppearedOnce = false

    var body: some View {
        TabView(selection: $selectedTab) {
            // タイムリミット画面
            NavigationView {
                LifeResultView()
                    .navigationBarHidden(false)
            }
            .navigationViewStyle(.stack)
            .tabItem {
                Label("タイムリミット", systemImage: "hourglass")
            }
            .tag(0)
            .accessibilityIdentifier("tab_timelimit")

            // 健康ダッシュボード画面
            NavigationView {
                HealthDashboardView()
            }
            .navigationViewStyle(.stack)
            .tabItem {
                Label("健康", systemImage: "heart.text.clipboard")
            }
            .tag(1)
            .accessibilityIdentifier("tab_health")

            // お気に入り画面
            NavigationView {
                FavoriteEpisodesView()
            }
            .navigationViewStyle(.stack)
            .tabItem {
                Label("お気に入り", systemImage: "heart.fill")
            }
            .tag(2)
            .accessibilityIdentifier("tab_favorites")

            // プロファイル画面
            NavigationView {
                ProfileView()
            }
            .navigationViewStyle(.stack)
            .tabItem {
                Label("プロファイル", systemImage: "person.crop.circle")
            }
            .tag(3)
            .accessibilityIdentifier("tab_profile")

            // 設定画面
            NavigationView {
                SettingsView()
            }
            .navigationViewStyle(.stack)
            .tabItem {
                Label("設定", systemImage: "gearshape.fill")
            }
            .tag(4)
            .accessibilityIdentifier("tab_settings")

            // About画面
            NavigationView {
                AboutView()
            }
            .navigationViewStyle(.stack)
            .tabItem {
                Label("About", systemImage: "info.circle.fill")
            }
            .tag(5)
            .accessibilityIdentifier("tab_about")
        }
        .accentColor(.blue)
        .forceBottomTabBar()
        .onAppear {
            if !hasAppearedOnce {
                hasAppearedOnce = true
                // タブバーの外観設定（最初の一度だけ実行）
                setupTabBarAppearance()
            }

            // アプリがフォアグラウンドに復帰
            appStateManager.appWillEnterForeground()
        }
        .onReceive(NotificationCenter.default.publisher(for: UIApplication.willResignActiveNotification)) { _ in
            // アプリがバックグラウンドに移行
            appStateManager.appDidEnterBackground()
        }
        .onReceive(NotificationCenter.default.publisher(for: NSNotification.Name("SwitchToHealthTab"))) { _ in
            selectedTab = 1  // 健康タブ
        }
    }

    // タブバーの外観をカスタマイズ
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

// MARK: - カスタムモディファイア

extension View {
    // periphery:ignore - View dependency/styling
    /// 各タブのビューに共通の設定を適用
    func tabViewStyle() -> some View {
        self
            .edgesIgnoringSafeArea(.top)
            .background(Color(.systemBackground))
    }

    /// iPadOS 18+ でタブバーがサイドバーに変わる問題を防止
    @ViewBuilder
    func forceBottomTabBar() -> some View {
        if #available(iOS 18.0, *) {
            self.tabViewStyle(.tabBarOnly)
        } else {
            self
        }
    }
}
