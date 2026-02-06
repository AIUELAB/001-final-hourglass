import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var userModel: UserModel
    @EnvironmentObject var appStateManager: AppStateManager
    @StateObject private var soundManager = SoundManager.shared
    @State private var showingResetAlert = false
    @State private var showingShareSheet = false

    var body: some View {
        ZStack {
            // 背景を先に配置
            MysticalSpaceBackground()
                .ignoresSafeArea()

            List {
                // アプリ設定セクション
                Section(header:
                            Text("アプリ設定")
                    .foregroundColor(Color.mysticalPurple.opacity(0.8))
                    .font(.system(size: 13, weight: .regular))
                    .textCase(.uppercase)
                    .shadow(color: Color.mysticalPurple.opacity(0.4), radius: 4)
                ) {
                    VStack(spacing: 0) {
                        // リマインダー設定に変更
                        VStack(alignment: .leading, spacing: 12) {
                            HStack {
                                StainedGlassIcon(
                                    systemName: "bell.fill",
                                    backgroundColor: Color.mysticBlue.opacity(0.2),
                                    borderColor: Color.mysticBlue.opacity(0.3),
                                    glowColor: Color.mysticBlue
                                )

                                Text("リマインダー")
                                    .foregroundColor(.white.opacity(0.85))
                                    .font(.system(size: 17, weight: .regular))
                                    .shadow(color: .black.opacity(0.5), radius: 1.5, x: 0, y: 1)

                                Spacer()

                                MysticalToggle(isOn: $appStateManager.reminderEnabled)
                                    .onChange(of: appStateManager.reminderEnabled) { newValue in
                                        if newValue {
                                            appStateManager.requestNotificationPermission { granted in
                                                if granted {
                                                    appStateManager.scheduleReminder()
                                                } else {
                                                    appStateManager.reminderEnabled = false
                                                }
                                            }
                                        } else {
                                            appStateManager.cancelReminder()
                                        }
                                    }
                            }
                            .padding(.horizontal, 16)
                            .padding(.top, 12)

                            // リマインダーが有効な場合、時刻選択を表示
                            if appStateManager.reminderEnabled {
                                HStack {
                                    Text("時刻")
                                        .foregroundColor(.white.opacity(0.65))
                                        .font(.system(size: 15))
                                        .padding(.leading, 56) // アイコン分のインデント

                                    Spacer()

                                    DatePicker("",
                                               selection: $appStateManager.reminderTime,
                                               displayedComponents: .hourAndMinute)
                                    .labelsHidden()
                                    .colorScheme(.dark)
                                    .accentColor(Color.mysticalPurple)
                                    .onChange(of: appStateManager.reminderTime) { _ in
                                        appStateManager.scheduleReminder()
                                    }
                                }
                                .padding(.horizontal, 16)
                                .padding(.bottom, 12)
                                .transition(.opacity.combined(with: .move(edge: .top)))
                            }
                        }
                        .animation(.easeInOut(duration: 0.3), value: appStateManager.reminderEnabled)
                    }
                    .background(
                        RoundedRectangle(cornerRadius: 14)
                            .fill(Color(white: 0.11, opacity: 0.4))
                            .overlay(
                                RoundedRectangle(cornerRadius: 14)
                                    .stroke(Color.mysticalPurple.opacity(0.1), lineWidth: 1)
                            )
                    )
                    .listRowBackground(Color.clear)
                    .listRowInsets(EdgeInsets(top: 0, leading: 20, bottom: 16, trailing: 20))

                    // BGM音量設定 (extracted)
                    VStack(spacing: 0) {
                        HStack {
                            StainedGlassIcon(
                                systemName: "music.note",
                                backgroundColor: Color.mysticBlue.opacity(0.2),
                                borderColor: Color.mysticBlue.opacity(0.3),
                                glowColor: Color.mysticBlue
                            )

                            Text("BGM音量")
                                .foregroundColor(.white.opacity(0.85))
                                .font(.system(size: 17, weight: .regular))
                                .shadow(color: .black.opacity(0.5), radius: 1.5, x: 0, y: 1)

                            Spacer()

                            HStack(spacing: 10) {
                                Image(systemName: "speaker.fill")
                                    .foregroundColor(.white.opacity(0.5))
                                    .font(.system(size: 12))

                                Slider(
                                    value: $soundManager.bgmVolume,
                                    in: 0...1,
                                    onEditingChanged: { _ in
                                        soundManager.setBGMVolume(soundManager.bgmVolume)
                                        UserDefaults.standard.set(soundManager.bgmVolume, forKey: "bgmVolume")
                                    }
                                )
                                .accentColor(Color.mysticalPurple)
                                .frame(width: 100)

                                Image(systemName: "speaker.wave.3.fill")
                                    .foregroundColor(.white.opacity(0.5))
                                    .font(.system(size: 12))
                            }
                        }
                        .padding(.horizontal, 16)
                        .padding(.vertical, 12)
                    }
                    .background(
                        RoundedRectangle(cornerRadius: 14)
                            .fill(Color(white: 0.11, opacity: 0.4))
                            .overlay(
                                RoundedRectangle(cornerRadius: 14)
                                    .stroke(Color.mysticalPurple.opacity(0.1), lineWidth: 1)
                            )
                    )
                    .listRowBackground(Color.clear)
                    .listRowInsets(EdgeInsets(top: 0, leading: 20, bottom: 16, trailing: 20))

                    // ハプティック設定
                    VStack(spacing: 0) {
                        HStack {
                            StainedGlassIcon(
                                systemName: "waveform",
                                backgroundColor: Color.mysticBlue.opacity(0.2),
                                borderColor: Color.mysticBlue.opacity(0.3),
                                glowColor: Color.mysticBlue
                            )

                            Text("振動フィードバック")
                                .foregroundColor(.white.opacity(0.85))
                                .font(.system(size: 17, weight: .regular))
                                .shadow(color: .black.opacity(0.5), radius: 1.5, x: 0, y: 1)

                            Spacer()

                            MysticalToggle(isOn: $soundManager.hapticEnabled)
                        }
                        .padding(.horizontal, 16)
                        .padding(.vertical, 12)
                    }
                    .background(
                        RoundedRectangle(cornerRadius: 14)
                            .fill(Color(white: 0.11, opacity: 0.4))
                            .overlay(
                                RoundedRectangle(cornerRadius: 14)
                                    .stroke(Color.mysticalPurple.opacity(0.1), lineWidth: 1)
                            )
                    )
                    .listRowBackground(Color.clear)
                    .listRowInsets(EdgeInsets(top: 0, leading: 20, bottom: 16, trailing: 20))
                }

                // 共有セクション
                Section(header:
                            Text("共有")
                    .foregroundColor(Color.mysticalPurple.opacity(0.8))
                    .font(.system(size: 13, weight: .regular))
                    .textCase(.uppercase)
                    .shadow(color: Color.mysticalPurple.opacity(0.4), radius: 4)
                ) {
                    VStack(spacing: 0) {
                        // Xに投稿
                        ShareItemButton(
                            icon: AnyView(
                                Text("𝕏")
                                    .font(.system(size: 16, weight: .bold))
                                    .foregroundColor(.white.opacity(0.9))
                            ),
                            title: "Xに投稿",
                            backgroundColor: Color.black.opacity(0.8),
                            borderColor: Color.white.opacity(0.3),
                            glowColor: Color.black,
                            action: { shareToX() }
                        )

                        ItemDivider()

                        // Instagramストーリー
                        ShareItemButton(
                            icon: AnyView(
                                Image(systemName: "camera.fill")
                                    .foregroundColor(.white.opacity(0.9))
                                    .font(.system(size: 16))
                            ),
                            title: "Instagramストーリー",
                            backgroundColor: Color(red: 0.8, green: 0.2, blue: 0.6).opacity(0.2),
                            borderColor: Color(red: 0.8, green: 0.2, blue: 0.6).opacity(0.3),
                            glowColor: Color(red: 0.8, green: 0.2, blue: 0.6),
                            action: { shareToInstagram() }
                        )

                        ItemDivider()

                        // LINEで送る
                        ShareItemButton(
                            icon: AnyView(
                                Image(systemName: "message.fill")
                                    .foregroundColor(.white.opacity(0.9))
                                    .font(.system(size: 16))
                            ),
                            title: "LINEで送る",
                            backgroundColor: Color(red: 0.0, green: 0.7, blue: 0.0).opacity(0.2),
                            borderColor: Color(red: 0.0, green: 0.7, blue: 0.0).opacity(0.3),
                            glowColor: Color(red: 0.0, green: 0.7, blue: 0.0),
                            action: { shareToLINE() }
                        )

                        ItemDivider()

                        // その他の方法で共有
                        ShareItemButton(
                            icon: AnyView(
                                Image(systemName: "square.and.arrow.up")
                                    .foregroundColor(.white.opacity(0.9))
                                    .font(.system(size: 16))
                            ),
                            title: "その他の方法で共有",
                            backgroundColor: Color.gray.opacity(0.2),
                            borderColor: Color.gray.opacity(0.3),
                            glowColor: Color.gray,
                            action: { shareToOther() }
                        )
                    }
                    .background(
                        RoundedRectangle(cornerRadius: 14)
                            .fill(Color(white: 0.11, opacity: 0.4))
                            .overlay(
                                RoundedRectangle(cornerRadius: 14)
                                    .stroke(Color.mysticalPurple.opacity(0.1), lineWidth: 1)
                            )
                    )
                    .listRowBackground(Color.clear)
                    .listRowInsets(EdgeInsets(top: 0, leading: 20, bottom: 16, trailing: 20))
                }

                // データ管理セクション
                Section(header:
                            Text("データ管理")
                    .foregroundColor(Color.mysticalPurple.opacity(0.8))
                    .font(.system(size: 13, weight: .regular))
                    .textCase(.uppercase)
                    .shadow(color: Color.mysticalPurple.opacity(0.4), radius: 4)
                ) {
                    VStack(spacing: 0) {
                        // データリセット
                        Button(action: {
                            // タップ音（警告）
                            soundManager.playTapSound(.warning)
                            showingResetAlert = true
                        }) {
                            HStack {
                                StainedGlassIcon(
                                    systemName: "trash.fill",
                                    backgroundColor: Color.crimson.opacity(0.2),
                                    borderColor: Color.crimson.opacity(0.3),
                                    glowColor: Color.crimson
                                )

                                Text("データをリセットして最初から始める")
                                    .foregroundColor(.red)
                                    .font(.system(size: 17, weight: .regular))
                                    .shadow(color: .red.opacity(0.3), radius: 1.5, x: 0, y: 1)

                                Spacer()

                                Image(systemName: "chevron.right")
                                    .foregroundColor(.secondary)
                                    .font(.system(size: 16))
                            }
                        }
                        .padding(.horizontal, 16)
                        .padding(.vertical, 12)
                    }
                    .background(
                        RoundedRectangle(cornerRadius: 14)
                            .fill(Color(white: 0.11, opacity: 0.4))
                            .overlay(
                                RoundedRectangle(cornerRadius: 14)
                                    .stroke(Color.mysticalPurple.opacity(0.1), lineWidth: 1)
                            )
                    )
                    .listRowBackground(Color.clear)
                    .listRowInsets(EdgeInsets(top: 0, leading: 20, bottom: 16, trailing: 20))
                }
            }
            .listStyle(PlainListStyle())
            .listRowSeparator(.hidden)
            .listSectionSeparator(.hidden)
            .environment(\.defaultMinListRowHeight, 44)
            .onAppear {
                // UITableViewの外観をカスタマイズ
                UITableView.appearance().backgroundColor = .clear
                UITableView.appearance().separatorStyle = .none
                UITableViewCell.appearance().backgroundColor = .clear
                UITableView.appearance().separatorColor = .clear
            }
            .navigationTitle("設定")
            .navigationBarTitleDisplayMode(.inline)
            .alert("データをリセット", isPresented: $showingResetAlert) {
                Button("キャンセル", role: .cancel) {
                    // タップ音（キャンセル）
                    soundManager.playTapSound(.cancel)
                }
                Button("リセット", role: .destructive) {
                    // タップ音（警告）
                    soundManager.playTapSound(.warning)
                    resetAllData()
                }
            } message: {
                Text("すべてのデータが削除されます。この操作は取り消せません。")
            }
            .sheet(isPresented: $showingShareSheet) {
                ShareSheetView()
            }
        }
    }

    private func resetAllData() {
        // すべてのサウンドを即座に停止
        soundManager.stopAllSounds()

        // 少し待ってから画面遷移（音声停止が完了するのを待つ）
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) {
            // UserModelをリセット（UserDefaultsもクリアされる）
            userModel.resetToDefaults()

            // エピソード履歴もリセット
            EpisodeManager.shared.resetAllData()

            // AppStateManagerを使用してアプリをリセット
            // これによりisFirstLaunch = true, hasCompletedOnboarding = falseが設定される
            appStateManager.resetApp()

            // RootViewは自動的にAppStateManagerの状態変更を検知して
            // OnboardingViewを表示するため、画面の再作成は不要
        }
    }

    // MARK: - Share Methods

    private func shareToX() {
        let remainingYears = calculateRemainingYears()
        let text = "私の人生の残り時間は約\(remainingYears)年。今を大切に生きよう！ #最期の砂時計"
        if let url = URL(string: "https://twitter.com/intent/tweet?text=\(text.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")") {
            UIApplication.shared.open(url)
            AnalyticsManager.shared.trackShare(method: "X")
        }
    }

    private func shareToInstagram() {
        print("shareToInstagram called")  // デバッグ用

#if targetEnvironment(simulator)
        // シミュレータの場合はアラートを表示
        let alert = UIAlertController(
            title: "Instagram",
            message: "シミュレータではInstagramを開けません。実機でテストしてください。",
            preferredStyle: .alert
        )
        alert.addAction(UIAlertAction(title: "OK", style: .default))

        if let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
           let window = windowScene.windows.first,
           let rootViewController = window.rootViewController {
            rootViewController.present(alert, animated: true)
        }
#else
        // Instagramアプリを開く
        if let instagramURL = URL(string: "instagram://app") {
            if UIApplication.shared.canOpenURL(instagramURL) {
                print("Opening Instagram app")  // デバッグ用
                UIApplication.shared.open(instagramURL)
                AnalyticsManager.shared.trackShare(method: "Instagram")
            } else {
                print("Instagram not installed, opening App Store")  // デバッグ用
                // Instagramアプリがインストールされていない場合
                if let appStoreURL = URL(string: "https://apps.apple.com/app/instagram/id389801252") {
                    UIApplication.shared.open(appStoreURL)
                }
            }
        }
#endif
    }

    private func shareToLINE() {
        let remainingYears = calculateRemainingYears()
        let text = "私の人生の残り時間は約\(remainingYears)年。今を大切に生きよう！ #最期の砂時計"

#if targetEnvironment(simulator)
        // シミュレータの場合はアラートを表示
        let alert = UIAlertController(
            title: "LINE",
            message: "シミュレータではLINEを開けません。実機でテストしてください。",
            preferredStyle: .alert
        )
        alert.addAction(UIAlertAction(title: "OK", style: .default))

        if let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
           let window = windowScene.windows.first,
           let rootViewController = window.rootViewController {
            rootViewController.present(alert, animated: true)
        }
#else

        if let url = URL(string: "line://msg/text/\(text.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")") {
            if UIApplication.shared.canOpenURL(url) {
                UIApplication.shared.open(url)
            } else {
                // LINEアプリがインストールされていない場合
                if let appStoreURL = URL(string: "https://apps.apple.com/app/line/id443904275") {
                    UIApplication.shared.open(appStoreURL)
                }
            }
        }
#endif
    }

    private func shareToOther() {
        let remainingYears = calculateRemainingYears()
        let text = "私の人生の残り時間は約\(remainingYears)年。今を大切に生きよう！ #最期の砂時計"

        let activityVC = UIActivityViewController(
            activityItems: [text],
            applicationActivities: nil
        )

        // 除外するアクティビティタイプを設定
        activityVC.excludedActivityTypes = [
            .assignToContact,
            .saveToCameraRoll,
            .addToReadingList,
            .postToFlickr,
            .postToVimeo,
            .openInIBooks
        ]

        // iPadでのポップオーバー対応
        if let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
           let window = windowScene.windows.first,
           var rootViewController = window.rootViewController {
            // 最前面のViewControllerを取得
            while let presented = rootViewController.presentedViewController {
                rootViewController = presented
            }

            if let popover = activityVC.popoverPresentationController {
                popover.sourceView = rootViewController.view
                popover.sourceRect = CGRect(x: rootViewController.view.bounds.midX,
                                            y: rootViewController.view.bounds.midY,
                                            width: 0,
                                            height: 0)
                popover.permittedArrowDirections = []
            }

            rootViewController.present(activityVC, animated: true)
        }
    }

    private func calculateRemainingYears() -> Int {
        let lifeExpectancy = calculateLifeExpectancy(user: userModel) ?? 84.0
        let birthDate = Calendar.current.date(from: DateComponents(
            year: userModel.birthYear,
            month: userModel.birthMonth,
            day: userModel.birthDay
        )) ?? Date()
        let currentAge = Double(Calendar.current.dateComponents([.year], from: birthDate, to: Date()).year ?? 0)
        return max(0, Int(lifeExpectancy - currentAge))
    }
}

// MARK: - ステンドグラス風アイコン
struct StainedGlassIcon: View {
    let systemName: String
    let backgroundColor: Color
    let borderColor: Color
    let glowColor: Color

    @State private var shimmerOffset: CGFloat = -1

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 6)
                .fill(backgroundColor)
                .frame(width: 28, height: 28)
                .overlay(
                    RoundedRectangle(cornerRadius: 6)
                        .stroke(borderColor, lineWidth: 1)
                )
                .shadow(color: glowColor.opacity(0.3), radius: 8)

            Image(systemName: systemName)
                .foregroundColor(.white.opacity(0.9))
                .font(.system(size: 16))

            // 光沢効果
            SettingsIconShimmer(shimmerOffset: $shimmerOffset)
        }
    }
}

// MARK: - 共有アイテムボタン
struct ShareItemButton: View {
    let icon: AnyView
    let title: String
    let backgroundColor: Color
    let borderColor: Color
    let glowColor: Color
    let action: () -> Void

    @State private var isPressed = false
    @State private var shimmerOffset: CGFloat = -1

    var body: some View {
        HStack {
            ZStack {
                RoundedRectangle(cornerRadius: 6)
                    .fill(backgroundColor)
                    .frame(width: 28, height: 28)
                    .overlay(
                        RoundedRectangle(cornerRadius: 6)
                            .stroke(borderColor, lineWidth: 1)
                    )
                    .shadow(color: glowColor.opacity(0.5), radius: 8)

                icon

                // 光沢効果
                SettingsIconShimmer(shimmerOffset: $shimmerOffset)
            }

            Text(title)
                .foregroundColor(.white.opacity(0.85))
                .font(.system(size: 17, weight: .regular))
                .shadow(color: .black.opacity(0.5), radius: 1.5, x: 0, y: 1)

            Spacer()

            Image(systemName: "chevron.right")
                .foregroundColor(.secondary)
                .font(.system(size: 16))
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(
            isPressed ? Color.white.opacity(0.05) : Color.clear
        )
        .scaleEffect(isPressed ? 0.98 : 1.0)
        .contentShape(Rectangle())
        .onTapGesture {
            // タップ音（共有系）
            SoundManager.shared.playTapSound(.soft)
            print("Button tapped: \(title)")  // どのボタンがタップされたか確認
            withAnimation(.easeInOut(duration: 0.1)) {
                isPressed = true
            }

            DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                isPressed = false
                action()
            }
        }
    }
}

// MARK: - 光沢エフェクト（名前を変更）
struct SettingsIconShimmer: View {
    @Binding var shimmerOffset: CGFloat

    var body: some View {
        RoundedRectangle(cornerRadius: 6)
            .fill(
                LinearGradient(
                    gradient: Gradient(colors: [
                        Color.white.opacity(0),
                        Color.white.opacity(0.3),
                        Color.white.opacity(0)
                    ]),
                    startPoint: .leading,
                    endPoint: .trailing
                )
            )
            .frame(width: 28, height: 28)
            .mask(
                Rectangle()
                    .frame(width: 10)
                    .offset(x: shimmerOffset * 40)
            )
            .onAppear {
                withAnimation(
                    Animation.linear(duration: 3)
                        .repeatForever(autoreverses: false)
                ) {
                    shimmerOffset = 1
                }
            }
    }
}

// MARK: - カスタムトグル
struct MysticalToggle: View {
    @Binding var isOn: Bool

    var body: some View {
        Toggle("", isOn: $isOn)
            .toggleStyle(MysticalToggleStyle())
            .labelsHidden()
    }
}

struct MysticalToggleStyle: ToggleStyle {
    func makeBody(configuration: Configuration) -> some View {
        ZStack {
            RoundedRectangle(cornerRadius: 16)
                .fill(
                    configuration.isOn ?
                    LinearGradient(
                        gradient: Gradient(colors: [Color.mysticalPurple, Color.mysticBlue]),
                        startPoint: .leading,
                        endPoint: .trailing
                    ) :
                        LinearGradient(
                            gradient: Gradient(colors: [Color.mysticalPurple.opacity(0.2), Color.mysticalPurple.opacity(0.2)]),
                            startPoint: .leading,
                            endPoint: .trailing
                        )
                )
                .frame(width: 51, height: 31)
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(
                            configuration.isOn ? Color.clear : Color.mysticalPurple.opacity(0.3),
                            lineWidth: 1
                        )
                )
                .shadow(
                    color: configuration.isOn ? Color.mysticalPurple.opacity(0.5) : Color.black.opacity(0.3),
                    radius: configuration.isOn ? 10 : 5
                )

            Circle()
                .fill(
                    LinearGradient(
                        gradient: Gradient(colors: [Color.white, Color(white: 0.94)]),
                        startPoint: .top,
                        endPoint: .bottom
                    )
                )
                .frame(width: 27, height: 27)
                .offset(x: configuration.isOn ? 10 : -10)
                .shadow(color: .black.opacity(0.3), radius: 2, x: 0, y: 2)
                .shadow(color: .white.opacity(0.5), radius: 8)
        }
        .onTapGesture {
            // トグル音（選択系）
            SoundManager.shared.playSelectionSound()
            withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                configuration.isOn.toggle()
            }
        }
    }
}

// MARK: - セクション間の区切り線
struct ItemDivider: View {
    var body: some View {
        Divider()
            .background(Color.mysticalPurple.opacity(0.1))
            .padding(.leading, 56)
    }
}
