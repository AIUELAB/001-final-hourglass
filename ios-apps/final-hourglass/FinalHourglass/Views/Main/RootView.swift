import SwiftUI

struct RootView: View {
    @EnvironmentObject var userModel: UserModel
    @EnvironmentObject var appStateManager: AppStateManager

    var body: some View {
        Group {
            if appStateManager.isFirstLaunch || !appStateManager.hasCompletedOnboarding {
                // オンボーディング画面
                OnboardingView(isFirstLaunch: Binding(
                    get: { appStateManager.isFirstLaunch },
                    set: { newValue in
                        appStateManager.isFirstLaunch = newValue
                        if !newValue {
                            appStateManager.hasCompletedOnboarding = true
                        }
                    }
                ))
                .environmentObject(userModel)
                .environmentObject(appStateManager)
                .transition(.opacity)
            } else {
                // メイン画面（ContentViewの代わりにMainTabViewを直接使用）
                MainTabView()
                    .environmentObject(userModel)
                    .environmentObject(appStateManager)
                    .transition(.opacity)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .ignoresSafeArea()
        .animation(.easeInOut(duration: 0.5), value: appStateManager.isFirstLaunch)
        .animation(.easeInOut(duration: 0.5), value: appStateManager.hasCompletedOnboarding)
        .preferredColorScheme(.dark)
        .statusBarHidden()
    }
}
