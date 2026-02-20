import AVFoundation
import SwiftUI

struct OnboardingView: View {
    @Binding var isFirstLaunch: Bool
    @EnvironmentObject var userModel: UserModel
    @EnvironmentObject var appStateManager: AppStateManager
    @StateObject private var soundManager = SoundManager.shared

    @State private var currentPage = 0
    @State private var doorOpacity = 0.0
    @State private var doorScale = 0.8
    @State private var textOpacity = 0.0
    @State private var buttonOpacity = 0.0
    @State private var isAnimating = false

    // UIテストモード検出
    private var isUITestMode: Bool {
        ProcessInfo.processInfo.arguments.contains("-UITest_DisableAnimations")
    }

    // 入力ステップの総数（身長・体重を追加）
    // 扉 + 生年月日 + 性別 + 身長 + 体重 + 喫煙 + 飲酒 + 運動
    // + ストレス + 睡眠 + 食生活 + 朝食 + 座位時間 + 都道府県 + 健康診断 + 婚姻状況
    private let totalSteps = 16

    // periphery:ignore - Audio management
    // サウンド再生用（オプション）
    @State private var audioPlayer: AVAudioPlayer?

    var body: some View {
        ZStack {
            backgroundGradient
                .ignoresSafeArea()

            VStack(spacing: 0) {
                progressBarView
                    .padding(.top, 60) // Safe Area対応

                currentPageContent
                    .padding(.bottom, 40) // Safe Area対応
            }
        }
        .onAppear {
            // リセット後の場合、まず全ての音声を即座に停止
            soundManager.stopAllSounds()

            // リセットフラグをクリア（画面遷移が完了したので）
            appStateManager.isResetting = false

            // 少し待ってからBGMを開始（クリーンな状態を確保）
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) {
                soundManager.fadeInBackgroundMusic(duration: 3.0)
            }
        }
        .onDisappear {
            // オンボーディング完了時のみBGMを停止（View再構築による誤発火を防止）
            if appStateManager.hasCompletedOnboarding {
                soundManager.fadeOutBackgroundMusic(duration: 2.0)
            }
        }
    }

    // MARK: - Progress Bar
    @ViewBuilder
    private var progressBarView: some View {
        if currentPage > 0 {
            ProgressView(value: Double(currentPage), total: Double(totalSteps - 1))
                .progressViewStyle(LinearProgressViewStyle(tint: .red))
                .padding(.horizontal)
                .padding(.top, 10)
        } else {
            Spacer()
                .frame(height: 4)
        }
    }

    // MARK: - Current Page Content
    @ViewBuilder
    private var currentPageContent: some View {
        currentPageView
            .accessibilityIdentifier("onboarding_step_\(currentPage)")
            .transition(.asymmetric(
                insertion: .move(edge: .trailing).combined(with: .opacity),
                removal: .move(edge: .leading).combined(with: .opacity)
            ))
            .onChange(of: currentPage) { newValue in
                print("ページ遷移: \(newValue)")
            }
    }

    @ViewBuilder
    private var currentPageView: some View {
        switch currentPage {
        case 0:
            doorPage
        case 1:
            birthdayInputPage
        case 2:
            genderInputPage
        case 3:
            heightInputPage
        case 4:
            weightInputPage
        case 5:
            smokingInputPage
        case 6:
            drinkingInputPage
        case 7:
            exerciseInputPage
        case 8:
            healthStatusInputPage
        case 9:
            sleepInputPage
        case 10:
            dietInputPage
        case 11:
            breakfastInputPage
        case 12:
            sittingHoursInputPage
        case 13:
            prefectureInputPage
        case 14:
            healthCheckupInputPage
        case 15:
            maritalStatusInputPage
        default:
            EmptyView()
        }
    }

    // MARK: - オンボーディング完了処理
    private func completeOnboarding() {
        // UserDefaultsに保存
        userModel.saveToUserDefaults()

        // AppStateManagerの状態を更新
        appStateManager.hasCompletedOnboarding = true
        appStateManager.isFirstLaunch = false

        // メイン画面へ遷移
        withAnimation(.easeInOut(duration: 0.5)) {
            isFirstLaunch = false
        }
    }
}

// MARK: - Background & Door Page
extension OnboardingView {
    // MARK: - 背景グラデーション
    private var backgroundGradient: some View {
        LinearGradient(
            gradient: Gradient(colors: [
                Color.black,
                Color.red.opacity(0.05),
                Color.black
            ]),
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }

    // MARK: - 運命の扉ページ（修正版）
    private var doorPage: some View {
        ZStack {
            // 背景エフェクトレイヤー
            backgroundEffects

            // メインコンテンツ
            VStack(spacing: 30) {
                Spacer()
                    .frame(minHeight: 60)

                // サブタイトル（上部）
                Text("あなたは\nその一粒が落ちる日を\n知る覚悟はありますか")
                    .font(.system(size: 14, weight: .regular))
                    .foregroundColor(.white.opacity(0.85))
                    .multilineTextAlignment(.center)
                    .lineSpacing(6)
                    .opacity(textOpacity)
                    .shadow(color: Color.AppColors.mediumPurple.opacity(0.4), radius: 15)

                // メインビジュアル（ステンドグラス風砂時計）
                ZStack {
                    // ステンドグラスパターン
                    stainedGlassFrame

                    // 光輪エフェクト
                    Circle()
                        .stroke(
                            LinearGradient(
                                colors: [AppColors.mediumPurple.opacity(0.4), AppColors.cornflowerBlue.opacity(0.4)],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            ),
                            lineWidth: 2
                        )
                        .frame(width: 200, height: 200)
                        .rotationEffect(.degrees(isAnimating ? 360 : 0))
                        .animation(isAnimating ? .linear(duration: 30).repeatCount(3, autoreverses: false) : .none, value: isAnimating)
                        .blur(radius: 1)

                    // 光線
                    ForEach(0..<4) { index in
                        Rectangle()
                            .fill(
                                LinearGradient(
                                    colors: [
                                        Color.clear,
                                        AppColors.mediumPurple.opacity(0.4),
                                        AppColors.cornflowerBlue.opacity(0.4),
                                        Color.clear
                                    ],
                                    startPoint: .leading,
                                    endPoint: .trailing
                                )
                            )
                            .frame(width: 220, height: 1)
                            .rotationEffect(.degrees(Double(index) * 45))
                            .opacity(0.6)
                    }
                    .rotationEffect(.degrees(isAnimating ? -360 : 0))
                    .animation(isAnimating ? .linear(duration: 25).repeatCount(3, autoreverses: false) : .none, value: isAnimating)

                    // 砂時計アイコン（グラデーション付き）
                    Image(systemName: "hourglass")
                        .resizable()
                        .scaledToFit()
                        .frame(width: 90, height: 90)
                        .foregroundStyle(
                            LinearGradient(
                                colors: [
                                    AppColors.mediumPurple,
                                    Color(hex: "8A2BE2"),
                                    AppColors.cornflowerBlue,
                                    AppColors.mediumPurple
                                ],
                                startPoint: .top,
                                endPoint: .bottom
                            )
                        )
                        .shadow(color: Color.AppColors.mediumPurple.opacity(0.6), radius: 25)
                        .rotationEffect(.degrees(isAnimating ? 5 : -5))
                        .animation(isAnimating ? .easeInOut(duration: 6).repeatCount(5, autoreverses: true) : .none, value: isAnimating)
                        .offset(y: isAnimating ? -5 : 5)
                        .animation(isAnimating ? .easeInOut(duration: 6).repeatCount(5, autoreverses: true) : .none, value: isAnimating)
                }
                .frame(width: 200, height: 200)
                .scaleEffect(doorScale)
                .opacity(doorOpacity)

                // タイトル（明朝体風）
                Text("最期の砂時計")
                    .font(.system(size: 30, weight: .thin, design: .serif))
                    .foregroundColor(.white)
                    .shadow(color: Color.AppColors.mediumPurple.opacity(0.5), radius: 20)
                    .shadow(color: Color.black.opacity(0.3), radius: 4, y: 2)
                    .opacity(textOpacity)

                Spacer()

                // ボタンセクション
                VStack(spacing: 22) {
                    // 扉を開くボタン（神秘的なデザイン）
                    Button(action: {
                        // タップ音とハプティックフィードバック
                        soundManager.playTapSound(.confirm)

                        // 20秒かけてBGMをフェードアウト
                        soundManager.fadeOutBackgroundMusic(duration: 20.0)

                        // ページ遷移
                        withAnimation(.easeInOut(duration: 0.5)) {
                            currentPage = 1
                        }
                    }) {
                        ZStack {
                            // ボタンの光彩
                            RoundedRectangle(cornerRadius: 25)
                                .fill(AppColors.mediumPurple.opacity(0.3))
                                .frame(width: 300, height: 55)
                                .blur(radius: 25)
                                .scaleEffect(isAnimating ? 1.1 : 0.9)
                                .animation(isAnimating ? .easeInOut(duration: 4).repeatCount(5, autoreverses: true) : .none, value: isAnimating)

                            // ボタン本体
                            RoundedRectangle(cornerRadius: 25)
                                .fill(
                                    LinearGradient(
                                        colors: [
                                            Color(hex: "8A2BE2").opacity(0.15),
                                            AppColors.mediumPurple.opacity(0.1),
                                            AppColors.cornflowerBlue.opacity(0.15)
                                        ],
                                        startPoint: .topLeading,
                                        endPoint: .bottomTrailing
                                    )
                                )
                                .frame(width: 290, height: 50)
                                .overlay(
                                    RoundedRectangle(cornerRadius: 25)
                                        .stroke(AppColors.mediumPurple.opacity(0.6), lineWidth: 1.5)
                                )
                                .background(
                                    // スイープアニメーション
                                    GeometryReader { geometry in
                                        Rectangle()
                                            .fill(
                                                LinearGradient(
                                                    colors: [
                                                        Color.clear,
                                                        Color.white.opacity(0.2),
                                                        Color.clear
                                                    ],
                                                    startPoint: .leading,
                                                    endPoint: .trailing
                                                )
                                            )
                                            .frame(width: geometry.size.width * 0.5)
                                            .offset(x: isAnimating ? geometry.size.width : -geometry.size.width)
                                            .animation(
                                                isAnimating
                                                    ? .linear(duration: 4).repeatCount(3, autoreverses: false)
                                                    : .none,
                                                value: isAnimating
                                            )
                                    }
                                        .clipShape(RoundedRectangle(cornerRadius: 25))
                                )

                            Text("扉を開く")
                                .font(.system(size: 16, weight: .regular))
                                .foregroundColor(.white.opacity(0.9))
                        }
                    }
                    .shadow(color: Color.AppColors.mediumPurple.opacity(0.3), radius: 25)
                    .accessibilityIdentifier("onboarding_open_door")

                    // 立ち去るリンク
                    Button(action: {
                        // タップ音（キャンセル系）
                        soundManager.playTapSound(.cancel)

                        // アプリを終了
                        exit(0)
                    }) {
                        Text("立ち去る")
                            .font(.system(size: 14, weight: .light))
                            .foregroundColor(AppColors.mediumPurple.opacity(0.6))
                    }
                }
                .opacity(buttonOpacity)

                Spacer()
                    .frame(minHeight: 60)
            }
            .padding(.horizontal)
            .padding(.bottom, 40)
        }
        .onAppear {
            // UIテストモードではアニメーションをスキップして即座に表示
            if isUITestMode {
                doorScale = 1.0
                doorOpacity = 1.0
                textOpacity = 1.0
                buttonOpacity = 1.0
                isAnimating = false
            } else {
                withAnimation(.easeOut(duration: 1.0)) {
                    doorScale = 1.0
                    doorOpacity = 1.0
                }
                withAnimation(.easeIn(duration: 0.8).delay(0.5)) {
                    textOpacity = 1.0
                }
                withAnimation(.easeIn(duration: 0.8).delay(1.0)) {
                    buttonOpacity = 1.0
                }
                isAnimating = true
            }
        }
        .onDisappear {
            isAnimating = false
        }
    }

    // MARK: - 背景エフェクト
    private var backgroundEffects: some View {
        ZStack {
            // ステンドグラス効果の背景
            GeometryReader { geometry in
                // オーロラ効果
                LinearGradient(
                    colors: [
                        Color.clear,
                        Color(hex: "FF00FF").opacity(0.15),
                        Color(hex: "0064FF").opacity(0.2),
                        Color(hex: "00FFFF").opacity(0.15),
                        AppColors.antiqueGold.opacity(0.1),
                        Color(hex: "FF0000").opacity(0.15),
                        Color.clear
                    ],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                .frame(width: geometry.size.width * 1.5, height: 400)
                .blur(radius: 30)
                .rotationEffect(.degrees(-3))
                .offset(x: isAnimating ? geometry.size.width * 0.15 : 0, y: -150)
                .animation(isAnimating ? .easeInOut(duration: 25).repeatCount(2, autoreverses: true) : .none, value: isAnimating)
                .opacity(0.6)
            }

            // 色付き光線
            ForEach(0..<4) { index in
                LinearGradient(
                    colors: [
                        colorForRay(index).opacity(0.6),
                        Color.clear
                    ],
                    startPoint: .top,
                    endPoint: .bottom
                )
                .frame(width: 2, height: 400)
                .blur(radius: 3)
                .rotationEffect(.degrees(Double(index - 2) * 10 - 5))
                .offset(y: -100)
                .opacity(0.3)
            }

            // 星座（小さな光の点）
            ForEach(0..<5) { index in
                Circle()
                    .fill(Color.white)
                    .frame(width: 3, height: 3)
                    .blur(radius: 0.5)
                    .position(
                        x: starPosition(index).x,
                        y: starPosition(index).y
                    )
                    .opacity(isAnimating ? 1 : 0.4)
                    .animation(
                        .easeInOut(duration: 3)
                        .repeatCount(5, autoreverses: true)
                        .delay(Double(index) * 0.5),
                        value: isAnimating
                    )
                    .scaleEffect(isAnimating ? 1.2 : 0.8)
            }

            // 神秘的な粒子
            ForEach(0..<5) { index in
                Circle()
                    .fill(
                        RadialGradient(
                            colors: [
                                AppColors.mediumPurple.opacity(0.6),
                                Color(hex: "8A2BE2").opacity(0.3),
                                Color.clear
                            ],
                            center: .center,
                            startRadius: 0,
                            endRadius: 2
                        )
                    )
                    .frame(width: 4, height: 4)
                    .blur(radius: 0.5)
                    .offset(
                        x: particleOffset(index).x,
                        y: isAnimating ? -UIScreen.main.bounds.height : UIScreen.main.bounds.height
                    )
                    .animation(
                        .linear(duration: 10)
                        .repeatCount(3, autoreverses: false)
                        .delay(Double(index) * 2),
                        value: isAnimating
                    )
            }
        }
    }
}

// MARK: - Glass Segment
extension OnboardingView {
    // MARK: - ステンドグラスフレーム
    private var stainedGlassFrame: some View {
        ZStack {
            // ガラスセグメント
            ForEach(0..<8) { index in
                glassSegment(index: index)
            }
        }
        .frame(width: 200, height: 200)
        .opacity(0.4)
    }

    // MARK: - Glass Segment Configs (静的プロパティ)
    private static var glassSegmentConfigs: [GlassSegmentConfig] {
        [
            // 上の三角形
            GlassSegmentConfig(
                offset: CGSize(width: 0, height: -50),
                size: CGSize(width: 60, height: 70),
                colors: [Color(hex: "FF1493"), Color(hex: "FF00FF"), Color(hex: "8A2BE2")],
                rotation: 0
            ),
            // 下の三角形
            GlassSegmentConfig(
                offset: CGSize(width: 0, height: 50),
                size: CGSize(width: 60, height: 70),
                colors: [Color(hex: "00BFFF"), Color(hex: "0064FF"), Color(hex: "00008B")],
                rotation: 180
            ),
            // 左
            GlassSegmentConfig(
                offset: CGSize(width: -50, height: 0),
                size: CGSize(width: 70, height: 60),
                colors: [AppColors.antiqueGold, Color(hex: "FF8C00"), Color(hex: "FF4500")],
                rotation: 270
            ),
            // 右
            GlassSegmentConfig(
                offset: CGSize(width: 50, height: 0),
                size: CGSize(width: 70, height: 60),
                colors: [Color(hex: "FF0000"), Color(hex: "DC143C"), Color(hex: "8B0000")],
                rotation: 90
            ),
            // 小さな円（左上）
            GlassSegmentConfig(
                offset: CGSize(width: -30, height: -30),
                size: CGSize(width: 30, height: 30),
                colors: [Color(hex: "32CD32"), Color(hex: "008000")],
                rotation: 0
            ),
            // 小さな円（右上）
            GlassSegmentConfig(
                offset: CGSize(width: 30, height: -30),
                size: CGSize(width: 30, height: 30),
                colors: [Color(hex: "FFFF00"), AppColors.antiqueGold],
                rotation: 0
            ),
            // 小さな四角（左下）
            GlassSegmentConfig(
                offset: CGSize(width: -30, height: 30),
                size: CGSize(width: 24, height: 24),
                colors: [Color(hex: "FF8C00"), Color(hex: "FF4500")],
                rotation: 45
            ),
            // 小さな四角（右下）
            GlassSegmentConfig(
                offset: CGSize(width: 30, height: 30),
                size: CGSize(width: 24, height: 24),
                colors: [Color(hex: "8A2BE2"), Color(hex: "4B0082")],
                rotation: 45
            )
        ]
    }

    // MARK: - Glass Segment Entry Point
    private func glassSegment(index: Int) -> some View {
        let config = Self.glassSegmentConfigs[index % Self.glassSegmentConfigs.count]
        return buildGlassShape(index: index, config: config)
    }

    // MARK: - Glass Shape Builder
    @ViewBuilder
    private func buildGlassShape(index: Int, config: GlassSegmentConfig) -> some View {
        if index < 4 {
            buildTriangleShape(index: index, config: config)
        } else if index < 6 {
            buildCircleShape(config: config)
        } else {
            buildRectangleShape(config: config)
        }
    }

    // MARK: - Triangle Shape Builder
    private func buildTriangleShape(index: Int, config: GlassSegmentConfig) -> some View {
        Path { path in
            buildTrianglePath(index: index, path: &path)
        }
        .fill(
            RadialGradient(
                colors: config.colors.map { $0.opacity(0.4) },
                center: .center,
                startRadius: 0,
                endRadius: 30
            )
        )
        .frame(width: config.size.width, height: config.size.height)
        .overlay(
            Path { path in
                buildTrianglePath(index: index, path: &path)
            }
            .stroke(Color.black.opacity(0.6), lineWidth: 2)
        )
        .rotationEffect(.degrees(config.rotation))
        .offset(config.offset)
    }

    // MARK: - Triangle Path Helper
    private func buildTrianglePath(index: Int, path: inout Path) {
        if index == 0 {
            path.move(to: CGPoint(x: 30, y: 0))
            path.addLine(to: CGPoint(x: 0, y: 60))
            path.addLine(to: CGPoint(x: 60, y: 60))
            path.closeSubpath()
        } else if index == 1 {
            path.move(to: CGPoint(x: 30, y: 60))
            path.addLine(to: CGPoint(x: 0, y: 0))
            path.addLine(to: CGPoint(x: 60, y: 0))
            path.closeSubpath()
        } else {
            path.move(to: CGPoint(x: 0, y: 20))
            path.addLine(to: CGPoint(x: 60, y: 0))
            path.addLine(to: CGPoint(x: 60, y: 40))
            path.addLine(to: CGPoint(x: 0, y: 40))
            path.closeSubpath()
        }
    }

    // MARK: - Circle Shape Builder
    private func buildCircleShape(config: GlassSegmentConfig) -> some View {
        Circle()
            .fill(
                RadialGradient(
                    colors: config.colors.map { $0.opacity(0.4) },
                    center: .center,
                    startRadius: 0,
                    endRadius: 15
                )
            )
            .frame(width: config.size.width, height: config.size.height)
            .overlay(
                Circle()
                    .stroke(Color.black.opacity(0.6), lineWidth: 2)
            )
            .offset(config.offset)
    }

    // MARK: - Rectangle Shape Builder
    private func buildRectangleShape(config: GlassSegmentConfig) -> some View {
        RoundedRectangle(cornerRadius: 4)
            .fill(
                RadialGradient(
                    colors: config.colors.map { $0.opacity(0.4) },
                    center: .center,
                    startRadius: 0,
                    endRadius: 12
                )
            )
            .frame(width: config.size.width, height: config.size.height)
            .overlay(
                RoundedRectangle(cornerRadius: 4)
                    .stroke(Color.black.opacity(0.6), lineWidth: 2)
            )
            .rotationEffect(.degrees(config.rotation))
            .offset(config.offset)
    }
}

// MARK: - Helper Functions
extension OnboardingView {
    private struct GlassSegmentConfig {
        let offset: CGSize
        let size: CGSize
        let colors: [Color]
        let rotation: Double
    }

    private func colorForRay(_ index: Int) -> Color {
        let colors = [
            Color(hex: "FF1493"), // Hot Pink
            Color(hex: "00BFFF"), // Deep Sky Blue
            AppColors.antiqueGold,
            Color(hex: "32CD32")  // Lime Green
        ]
        return colors[index % colors.count]
    }

    private func starPosition(_ index: Int) -> CGPoint {
        let positions = [
            CGPoint(x: UIScreen.main.bounds.width * 0.25, y: 120),
            CGPoint(x: UIScreen.main.bounds.width * 0.75, y: 160),
            CGPoint(x: UIScreen.main.bounds.width * 0.20, y: 280),
            CGPoint(x: UIScreen.main.bounds.width * 0.80, y: 240),
            CGPoint(x: UIScreen.main.bounds.width * 0.50, y: 200)
        ]
        return positions[index % positions.count]
    }

    private func particleOffset(_ index: Int) -> CGPoint {
        let xOffsets = [
            UIScreen.main.bounds.width * 0.15,
            UIScreen.main.bounds.width * 0.35,
            UIScreen.main.bounds.width * 0.55,
            UIScreen.main.bounds.width * 0.75,
            UIScreen.main.bounds.width * 0.85
        ]
        return CGPoint(x: xOffsets[index % xOffsets.count] - UIScreen.main.bounds.width / 2, y: 0)
    }
}

// MARK: - Page Views
extension OnboardingView {
    // MARK: - 生年月日入力ページ
    private var birthdayInputPage: some View {
        OnboardingStepView(
            title: "生年月日を刻む",
            subtitle: "運命の計算を開始します",
            currentPage: $currentPage,
            showBackButton: false
        ) {
            BirthdayInputContent(
                birthDate: Binding(
                    get: { userModel.birthDate },
                    set: { date in
                        let components = Calendar.current.dateComponents([.year, .month, .day], from: date)
                        userModel.birthYear = components.year ?? 2000
                        userModel.birthMonth = components.month ?? 1
                        userModel.birthDay = components.day ?? 1
                    }
                ),
                onNext: {
                    currentPage = 2
                }
            )
        }
    }

    // MARK: - 性別入力ページ
    private var genderInputPage: some View {
        OnboardingStepView(
            title: "性別",
            subtitle: "正確な計算のために必要です",
            currentPage: $currentPage,
            showBackButton: true
        ) {
            GenderInputContent(
                gender: $userModel.gender,
                onNext: {
                    currentPage = 3
                }
            )
        }
    }

    // MARK: - 身長入力ページ（新規追加）
    private var heightInputPage: some View {
        OnboardingStepView(
            title: "身長",
            subtitle: "BMI計算に必要です",
            currentPage: $currentPage,
            showBackButton: true
        ) {
            HeightInputContent(
                height: $userModel.height,
                onNext: {
                    currentPage = 4
                }
            )
        }
    }

    // MARK: - 体重入力ページ（新規追加）
    private var weightInputPage: some View {
        OnboardingStepView(
            title: "体重",
            subtitle: "健康状態の評価に使用します",
            currentPage: $currentPage,
            showBackButton: true
        ) {
            WeightInputContent(
                weight: $userModel.weight,
                height: userModel.height,
                bmi: $userModel.bmi,
                onNext: {
                    userModel.calculateBMI()
                    currentPage = 5
                }
            )
        }
    }

    // MARK: - 喫煙習慣入力ページ
    private var smokingInputPage: some View {
        OnboardingStepView(
            title: "喫煙習慣",
            subtitle: "健康状態の把握のため",
            currentPage: $currentPage,
            showBackButton: true
        ) {
            SmokingInputContent(
                smokingStatus: $userModel.smokingStatus,
                onNext: {
                    currentPage = 6
                }
            )
        }
    }

    // MARK: - 飲酒習慣入力ページ
    private var drinkingInputPage: some View {
        OnboardingStepView(
            title: "飲酒習慣",
            subtitle: "どのくらいの頻度で飲酒しますか？",
            currentPage: $currentPage,
            showBackButton: true
        ) {
            DrinkingInputContent(
                drinkingFrequency: $userModel.drinkingFrequency,
                onNext: {
                    currentPage = 7
                }
            )
        }
    }

    // MARK: - 運動習慣入力ページ
    private var exerciseInputPage: some View {
        OnboardingStepView(
            title: "運動習慣",
            subtitle: "週にどのくらい運動しますか？",
            currentPage: $currentPage,
            showBackButton: true
        ) {
            ExerciseInputContent(
                exerciseFrequency: $userModel.exerciseFrequency,
                onNext: {
                    currentPage = 8
                }
            )
        }
    }

    // MARK: - 健康状態入力ページ
    private var healthStatusInputPage: some View {
        OnboardingStepView(
            title: "ストレスレベル",
            subtitle: "日常的なストレスの程度を教えてください",
            currentPage: $currentPage,
            showBackButton: true
        ) {
            StressLevelInputContent(
                stressLevel: $userModel.stressLevel,
                onNext: {
                    currentPage = 9
                }
            )
        }
    }

    // MARK: - 睡眠時間入力ページ
    private var sleepInputPage: some View {
        OnboardingStepView(
            title: "睡眠時間",
            subtitle: "平均的な睡眠時間を教えてください",
            currentPage: $currentPage,
            showBackButton: true
        ) {
            SleepInputContent(
                sleepHours: $userModel.sleepHours,
                onNext: {
                    currentPage = 10
                }
            )
        }
    }

    // MARK: - 食生活入力ページ
    private var dietInputPage: some View {
        OnboardingStepView(
            title: "食生活",
            subtitle: "普段の食事について教えてください",
            currentPage: $currentPage,
            showBackButton: true
        ) {
            DietInputContent(
                dietHabits: $userModel.dietHabits,
                onNext: {
                    currentPage = 11
                }
            )
        }
    }

    // MARK: - 朝食習慣入力ページ
    private var breakfastInputPage: some View {
        OnboardingStepView(
            title: "朝食習慣",
            subtitle: "朝食を食べる頻度を教えてください",
            currentPage: $currentPage,
            showBackButton: true
        ) {
            BreakfastInputContent(
                breakfastFrequency: $userModel.breakfastFrequency,
                onNext: {
                    currentPage = 12
                }
            )
        }
    }

    // MARK: - 座位時間入力ページ
    private var sittingHoursInputPage: some View {
        OnboardingStepView(
            title: "座位時間",
            subtitle: "1日にどのくらい座っていますか？",
            currentPage: $currentPage,
            showBackButton: true
        ) {
            SittingHoursInputContent(
                sittingHours: $userModel.sittingHours,
                onNext: {
                    print("座位時間入力完了: \(userModel.sittingHours)")
                    currentPage = 13
                }
            )
        }
    }

    // MARK: - 都道府県入力ページ
    private var prefectureInputPage: some View {
        OnboardingStepView(
            title: "お住まいの地域",
            subtitle: "現在お住まいの都道府県を選択してください",
            currentPage: $currentPage,
            showBackButton: true
        ) {
            PrefectureInputContent(
                currentPrefecture: $userModel.currentPrefecture,
                onNext: {
                    print("都道府県選択完了: \(userModel.currentPrefecture)")
                    currentPage = 14
                }
            )
        }
    }

    // MARK: - 健康診断頻度入力ページ
    private var healthCheckupInputPage: some View {
        OnboardingStepView(
            title: "健康管理",
            subtitle: "健康診断の受診状況を教えてください",
            currentPage: $currentPage,
            showBackButton: true
        ) {
            HealthCheckupInputContent(
                healthCheckupFrequency: $userModel.healthCheckupFrequency,
                dentalCheckupFrequency: $userModel.dentalCheckupFrequency,
                onNext: {
                    print("健康診断入力完了")
                    print("健康診断: \(userModel.healthCheckupFrequency)")
                    print("歯科検診: \(userModel.dentalCheckupFrequency)")
                    currentPage = 15
                }
            )
        }
    }

    // MARK: - 婚姻状況入力ページ
    private var maritalStatusInputPage: some View {
        OnboardingStepView(
            title: "婚姻状況",
            subtitle: "現在の婚姻状況を教えてください",
            currentPage: $currentPage,
            showBackButton: true
        ) {
            MaritalStatusInputContent(
                maritalStatus: $userModel.maritalStatus,
                marriageDuration: $userModel.marriageDuration,
                onNext: {
                    // すべての入力が完了
                    completeOnboarding()
                }
            )
        }
    }
}
