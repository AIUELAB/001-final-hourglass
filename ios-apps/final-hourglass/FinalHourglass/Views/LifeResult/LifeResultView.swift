import os
import SwiftUI

// Logger定義
private let lifeResultLogger = Logger(subsystem: "com.finalhourglass.liferesult", category: "episode")

// エピソードコンテンツの構造体
struct EpisodeContent {
    let ageText: String        // "あなたと同じ〇〇歳のとき"
    let personName: String      // "アインシュタインは"など
    let episodeText: String     // エピソード本文
}

// 死亡予定日の日付コンポーネント構造体（large_tuple警告対応）
struct DateComponentsResult {
    let year: Int
    let month: Int
    let day: Int
}

struct LifeResultView: View {
    @EnvironmentObject var userModel: UserModel
    @EnvironmentObject var appStateManager: AppStateManager
    @StateObject private var soundManager = SoundManager.shared
    // ★ 修正: シングルトンには @ObservedObject を使用（タブ切り替え時のView再構築対策）
    @ObservedObject private var episodeManager = EpisodeManager.shared
    @ObservedObject private var favoriteManager = FavoriteEpisodeManager.shared

    // periphery:ignore - UI state management
    // ドラマチック演出用のState
    @State private var showIntro = true
    @State private var showRemainingTime = false
    @State private var showDeathDate = false
    @State private var showHourglass = false
    @State private var showProgress = false
    @State private var showEpisode = false
    @State private var showFinalMessage = false

    // BGM制御用のState
    @State private var bgmStarted = false

    // ビューのアクティブ状態を管理
    @State private var isViewActive = false

    // 健康タブへの遷移用
    @State private var navigateToHealth = false

    // ドラマチック演出の表示済みフラグ
    @AppStorage("hasSeenDramaticSequence") private var hasSeenDramaticSequence = false

    // エピソード関連
    @State private var currentEpisode: Episode?
    @State private var isLoadingEpisode = false
    @State private var lastFetchedAge: Int = -1
    @State private var isLiked: Bool = false

    // アニメーション用の値
    @State private var hourglassScale: CGFloat = 3.0
    @State private var hourglassOpacity: Double = 0.0
    @State private var doorOffset: CGFloat = 0
    @State private var countUpYears: Int = 0
    @State private var countUpDays: Int = 0
    @State private var deathYearCount: Int = 0
    @State private var progressValue: Double = 0.0

    var body: some View {
        ZStack {
            // 新しい背景（神秘的なグラデーション）
            RadialGradient(
                gradient: Gradient(colors: [
                    AppColors.darkPurple,
                    AppColors.midnightBlue,
                    Color.black
                ]),
                center: .center,
                startRadius: 50,
                endRadius: 400
            )
            .ignoresSafeArea()

            // メインコンテンツ（ピンチズーム対応）
            PinchZoomView(minScale: 0.8, maxScale: 3.0) {
                ScrollView {
                    VStack(spacing: 30) {
                    // 残り時間の表示（最上部）
                    VStack(spacing: 15) {
                        Text("あなたの人生は")
                            .font(.system(size: 20, weight: .medium))
                            .foregroundColor(.white.opacity(0.9))

                        HStack(spacing: 0) {
                            Text("残り")
                                .font(.system(size: 22))
                                .foregroundColor(.white)
                            Text("\(countUpYears)")
                                .font(.system(size: ResponsiveHelper.scaledSize(40, min: 32, max: 48), weight: .bold, design: .monospaced))
                                .foregroundStyle(
                                    LinearGradient(
                                        colors: [AppColors.antiqueGold, AppColors.amber],
                                        startPoint: .leading,
                                        endPoint: .trailing
                                    )
                                )
                                .padding(.horizontal, 5)
                            Text("年")
                                .font(.system(size: 22))
                                .foregroundColor(.white)
                            Text("\(countUpDays)")
                                .font(.system(size: 40, weight: .bold, design: .monospaced))
                                .foregroundColor(.orange)
                                .padding(.horizontal, 5)
                            Text("日")
                                .font(.system(size: 22))
                                .foregroundColor(.white)
                        }

                        Text("です。")
                            .font(.system(size: 20, weight: .medium))
                            .foregroundColor(.white.opacity(0.9))
                    }
                    .padding(.top, 20)
                    .opacity(showRemainingTime ? 1 : 0)
                    .scaleEffect(showRemainingTime ? 1 : 0.8)
                    .animation(.easeOut(duration: 0.8), value: showRemainingTime)

                    // 死亡予定日
                    VStack(spacing: 15) {
                        Text("あなたは")
                            .font(.system(size: 20, weight: .medium))
                            .foregroundColor(.white.opacity(0.9))

                        // 年
                        HStack(spacing: ResponsiveHelper.scaledSize(2, min: 1, max: 3)) {
                            ForEach(Array(String(deathYearCount).enumerated()), id: \.offset) { _, char in
                                Text(String(char))
                                    .font(.system(
                                        size: ResponsiveHelper.fontSize(.largeTitle),
                                        weight: .bold,
                                        design: .monospaced
                                    ))
                                    .foregroundStyle(
                                        LinearGradient(
                                            colors: [
                                                AppColors.hotPink,
                                                AppColors.crimson,
                                                AppColors.deepCrimson
                                            ],
                                            startPoint: .top,
                                            endPoint: .bottom
                                        )
                                    )
                            }
                            Text("年")
                                .font(.system(size: ResponsiveHelper.fontSize(.title), weight: .medium))
                                .foregroundStyle(
                                    LinearGradient(
                                        colors: [AppColors.hotPink, AppColors.crimson],
                                        startPoint: .top,
                                        endPoint: .bottom
                                    )
                                )
                        }
                        .shadow(color: AppColors.crimson.opacity(0.5), radius: 15)

                        // 月日
                        HStack(spacing: 0) {
                            Text("\(predictedDeathComponents.month)")
                                .font(.system(size: 42, weight: .bold, design: .monospaced))
                                .foregroundStyle(
                                    LinearGradient(
                                        colors: [AppColors.hotPink, AppColors.crimson],
                                        startPoint: .top,
                                        endPoint: .bottom
                                    )
                                )
                            Text("月")
                                .font(.system(size: 22))
                                .foregroundColor(.white)
                                .padding(.leading, 3)

                            Text("\(predictedDeathComponents.day)")
                                .font(.system(size: 42, weight: .bold, design: .monospaced))
                                .foregroundStyle(
                                    LinearGradient(
                                        colors: [AppColors.hotPink, AppColors.crimson],
                                        startPoint: .top,
                                        endPoint: .bottom
                                    )
                                )
                                .padding(.leading, 8)
                            Text("日")
                                .font(.system(size: 22))
                                .foregroundColor(.white)
                                .padding(.leading, 3)
                        }

                        Text("に死にます。")
                            .font(.system(size: 24, weight: .bold))
                            .foregroundColor(.white)
                    }
                    .padding(.vertical, 25)
                    .padding(.horizontal, 20)
                    .frame(maxWidth: .infinity)
                    .background(
                        RoundedRectangle(cornerRadius: ResponsiveHelper.scaledSize(16, min: 12, max: 20))
                            .fill(Color.black.opacity(0.4))
                            .overlay(
                                RoundedRectangle(cornerRadius: ResponsiveHelper.scaledSize(16, min: 12, max: 20))
                                    .stroke(
                                        LinearGradient(
                                            colors: [
                                                AppColors.antiqueGold.opacity(0.3),
                                                AppColors.mediumPurple.opacity(0.2)
                                            ],
                                            startPoint: .topLeading,
                                            endPoint: .bottomTrailing
                                        ),
                                        lineWidth: 1
                                    )
                            )
                    )
                    .shadow(color: AppColors.crimson.opacity(0.3), radius: 15, y: 5)
                    .opacity(showDeathDate ? 1 : 0)
                    .scaleEffect(showDeathDate ? 1 : 0.8)
                    .animation(.easeOut(duration: 1.0).delay(0.3), value: showDeathDate)

                    // リアルな砂時計アニメーション
                    RealisticHourglassView(
                        progress: progress,
                        size: CGSize(
                            width: ResponsiveHelper.scaledSize(150, min: 120, max: 200),
                            height: ResponsiveHelper.scaledSize(200, min: 160, max: 260)
                        ),
                        isAnimating: showHourglass,
                        sandColor: Color(red: 1.0, green: 0.84, blue: 0.47)  // ゴールド
                    )
                    .scaleEffect(hourglassScale)
                    .opacity(showHourglass ? hourglassOpacity : 0)
                    .animation(.spring(response: 1.2, dampingFraction: 0.8), value: hourglassScale)
                    .animation(.easeOut(duration: 0.6), value: hourglassOpacity)
                    .frame(height: 250) // リアルな砂時計用に高さを増加

                    // 進捗率セクション
                    VStack(spacing: 12) {
                        Text("人生の進捗率")
                            .font(.system(size: 16, weight: .medium))
                            .foregroundColor(.white.opacity(0.8))

                        ProgressView(value: progressValue)
                            .progressViewStyle(LinearProgressViewStyle(tint: AppColors.mediumPurple))
                            .frame(width: 200, height: 6)
                            .background(
                                RoundedRectangle(cornerRadius: 3)
                                    .fill(Color.white.opacity(0.1))
                            )

                        Text("\(progressPercent)％")
                            .font(.system(size: 24, weight: .bold, design: .monospaced))
                            .foregroundStyle(
                                LinearGradient(
                                    colors: [AppColors.mediumPurple, AppColors.cornflowerBlue],
                                    startPoint: .leading,
                                    endPoint: .trailing
                                )
                            )
                    }
                    .padding(.vertical, 20)
                    .opacity(showProgress ? 1 : 0)
                    .scaleEffect(showProgress ? 1 : 0.8)
                    .animation(.easeOut(duration: 0.8), value: showProgress)

                    // 偉人のエピソードセクション
                    VStack(alignment: .leading, spacing: 16) {
                        EpisodeContentSection(
                            isLoadingEpisode: isLoadingEpisode,
                            currentEpisode: currentEpisode,
                            ageInt: ageInt,
                            fallbackEpisode: getAgeGroupMessage(),
                            parseEpisodeText: parseEpisodeText
                        )

                        // いいねボタン（右下配置）
                        // 0歳固定エピソードはお気に入り対象外
                        if !isLoadingEpisode, let episode = currentEpisode, episode.episodeAge != 0 {
                            HStack {
                                Spacer()
                                Button(action: {
                                    withAnimation(.spring(response: 0.3, dampingFraction: 0.6)) {
                                        // お気に入り登録/解除をトグル
                                        isLiked = favoriteManager.toggleFavorite(episode: episode)
                                    }
                                }) {
                                    Image(systemName: isLiked ? "heart.fill" : "heart")
                                        .font(.system(size: 24))
                                        .foregroundColor(isLiked ? AppColors.hotPink : .white.opacity(0.5))
                                        .scaleEffect(isLiked ? 1.2 : 1.0)
                                }
                            }
                            .padding(.top, 8)
                        }
                    }
                    .padding(25)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(
                        RoundedRectangle(cornerRadius: 16)
                            .fill(Color.black.opacity(0.4))
                            .overlay(
                                RoundedRectangle(cornerRadius: 16)
                                    .stroke(
                                        LinearGradient(
                                            colors: [
                                                AppColors.antiqueGold.opacity(0.3),
                                                AppColors.mediumPurple.opacity(0.2)
                                            ],
                                            startPoint: .topLeading,
                                            endPoint: .bottomTrailing
                                        ),
                                        lineWidth: 1
                                    )
                            )
                    )
                    .opacity(showEpisode ? 1 : 0)
                    .scaleEffect(showEpisode ? 1 : 0.8)
                    .animation(.easeOut(duration: 0.8), value: showEpisode)

                    // 健康サマリーカード
                    HealthSummaryCard(onTapDetail: {
                        // MainTabViewの健康タブに切り替え
                        // NotificationCenterを使用してタブ切り替えを通知
                        NotificationCenter.default.post(
                            name: NSNotification.Name("SwitchToHealthTab"),
                            object: nil
                        )
                    })
                    .opacity(showFinalMessage ? 1 : 0)
                    .scaleEffect(showFinalMessage ? 1 : 0.8)
                    .animation(.easeOut(duration: 0.8), value: showFinalMessage)

                    // 最後の問いかけ
                    VStack(spacing: 8) {
                        Text("あなたは今日から")
                            .font(.system(size: 18, weight: .medium))
                            .foregroundColor(.white.opacity(0.8))

                        Text("最後の一粒が落ちるまでどのように")
                            .font(.system(size: 18, weight: .medium))
                            .foregroundColor(.white.opacity(0.8))

                        Text("時を刻みますか？")
                            .font(.system(size: 18, weight: .medium))
                            .foregroundColor(.white.opacity(0.8))
                    }
                    .padding(.top, 20)
                    .padding(.bottom, 40)
                    .opacity(showFinalMessage ? 1 : 0)
                    .offset(y: showFinalMessage ? 0 : 20)
                    .animation(.easeOut(duration: 1.0), value: showFinalMessage)

                    Spacer()
                    }
                    .padding(.horizontal)
                }
            }
            .navigationTitle("最期の砂時計")
            .navigationBarTitleDisplayMode(.inline)
            .onAppear {
                isViewActive = true
                // ★ 永続化されたlastFetchedAgeを復元（タブ切り替え対策）
                lastFetchedAge = UserDefaults.standard.integer(forKey: "lastEpisodeAge")

                // リセット中でない場合のみ、ドラマチックな演出シーケンスを開始
                if isViewActive && !appStateManager.isResetting {
                    startDramaticSequence()

                    // ★ Phase 2修正: 常に fetchDailyEpisode を呼ぶ
                    // getDailyEpisode() 内で todayEpisode キャッシュを使用するため、
                    // 同じ日・同じ年齢なら再取得されない（displayedEpisode への依存を除去）
                    fetchDailyEpisode()

                    // 寿命計算結果をトラッキング
                    let currentAge = Calendar.current.dateComponents([.year], from: birthday, to: Date()).year ?? 0
                    AnalyticsManager.shared.trackLifeResultCalculation(
                        lifeExpectancy: predictedLifeSpan,
                        currentAge: currentAge
                    )
                }
            }
            .onChange(of: ageInt) { newAge in
                // ★ 永続化された年齢と比較（@Stateではなく）
                let persistedAge = UserDefaults.standard.integer(forKey: "lastEpisodeAge")

                // 実際に年齢が変わった場合のみ再選定（0は初回起動）
                if newAge != persistedAge && persistedAge != 0 {
                    episodeManager.clearCacheForAgeChange()
                    fetchDailyEpisode()
                } else if persistedAge == 0 {
                    // 初回起動時
                    fetchDailyEpisode()
                }
                lastFetchedAge = newAge
            }
            .onDisappear {
                isViewActive = false
                // ビューが非アクティブになったら、BGMを短時間でフェードアウト
                soundManager.fadeOutBackgroundMusic(duration: 2.0) {
                    // フェードアウト完了後、フラグをリセット
                    bgmStarted = false
                }
            }
            .onReceive(NotificationCenter.default.publisher(for: UIApplication.willEnterForegroundNotification)) { _ in
                // 0時跨ぎ対応: フォアグラウンド復帰時に日付が変わっていたら新しいエピソードを取得
                if episodeManager.shouldRefreshForNewDay() {
                    fetchDailyEpisode()
                }
            }
            .analyticsScreen("LifeResult")

            // 運命の扉エフェクト
            GeometryReader { geometry in
                HStack(spacing: 0) {
                    // 左の扉
                    Rectangle()
                        .fill(Color.black)
                        .frame(width: geometry.size.width / 2)
                        .offset(x: -doorOffset)

                    // 右の扉
                    Rectangle()
                        .fill(Color.black)
                        .frame(width: geometry.size.width / 2)
                        .offset(x: doorOffset)
                }
                .ignoresSafeArea()
                .animation(.easeInOut(duration: 1.5), value: doorOffset)
            }
        }  // ZStackの閉じカッコ
    }

    // 年齢層に応じた偉人のエピソードデータ（データ駆動型）
    // swiftlint:disable:next large_tuple
    private static let ageGroupEpisodes: [(range: Range<Int>, personName: String, episodeText: String)] = [
        (0..<20, "アインシュタインは",
         "光の速さで並走したら光はどう見えるのかという思考実験を始めていました。この純粋な好奇心が、後に相対性理論という人類史上最も重要な発見の一つに繋がりました。"),
        (20..<30, "スティーブ・ジョブズは",
         "ガレージから始めた小さな会社Appleを、世界を変える巨大企業へと成長させていました。「点と点は後から繋がる」という言葉を残し、今を信じることの大切さを教えてくれました。"),
        (30..<40, "坂本龍馬は",
         "薩長同盟を成立させ、日本の近代化に大きく貢献していました。「日本を今一度洗濯いたし申し候」という言葉には、変革への強い意志が込められています。"),
        (40..<50, "ココ・シャネルは",
         "ファッション界に革命を起こしていました。女性を束縛していたコルセットから解放し、シンプルで機能的な服を提案しました。「流行は色褪せるが、スタイルは永遠」という言葉を残しています。"),
        (50..<60, "レイ・クロックは",
         "マクドナルドのフランチャイズ事業で成功を収めていました。「成功は99%の失敗に支えられた1%だ」という言葉は、年齢に関係なく新しい挑戦を始められることを証明しています。"),
        (60..<70, "伊能忠敬は",
         "日本全国の測量に情熱を注いでいました。17年かけて日本初の実測地図を完成させ、「歩け、歩け。続ける事の大切さ」を身をもって示しました。老いてなお学び、挑戦する姿勢の象徴です。"),
        (70..<80, "葛飾北斎は",
         "「富嶽三十六景」など傑作を次々と生み出していました。90歳まで絵を描き続け、「あと5年生きられたら本当の絵描きになれる」と語りました。生涯現役の精神を体現した芸術家です。"),
        (80..<90, "ヴェルディは",
         "歌劇「ファルスタッフ」など晩年の傑作を作曲していました。「休息とは錆びることだ」と語り、常に前進し続けました。年齢は創造性の障害にはならないことを証明しています。"),
        (90..<100, "日野原重明は",
         "現役医師として活動を続けていました。「いのちは時間である」という哲学を持ち、最期まで他者のために時間を使い続けました。長寿の意味を体現した人生でした。")
    ]

    // デフォルトエピソード（範囲外の年齢用）
    private static let defaultEpisode = (
        personName: "織田信長は",
        episodeText: "天下統一への道を歩んでいました。「人生50年」と謡いましたが、限られた時間の中で何を成すか、それこそが人生の本質であることを教えてくれます。"
    )

    // 年齢層に応じた偉人のエピソードを取得
    func getAgeGroupMessage() -> EpisodeContent {
        let episode = Self.ageGroupEpisodes.first { $0.range.contains(ageInt) }
        let personName = episode?.personName ?? Self.defaultEpisode.personName
        let episodeText = episode?.episodeText ?? Self.defaultEpisode.episodeText
        return EpisodeContent(
            ageText: "あなたと同じ\(ageInt)歳のとき",
            personName: personName,
            episodeText: episodeText
        )
    }
}  // struct LifeResultView の閉じカッコ

// MARK: - Computed Properties
extension LifeResultView {
    // 予測寿命（年単位）
    // 注意: フォールバック時のログはonAppear等で適宜出力すること
    var predictedLifeSpan: Double {
        calculateLifeExpectancy(user: userModel) ?? 84.0
    }

    // 生年月日
    var birthday: Date {
        Calendar.current.date(from: DateComponents(
            year: userModel.birthYear,
            month: userModel.birthMonth,
            day: userModel.birthDay)) ?? Date()
    }

    // 死亡予定日
    var predictedDeath: Date {
        Calendar.current.date(byAdding: .day, value: Int(predictedLifeSpan * 365.25), to: birthday) ?? Date()
    }

    // 残り期間の計算
    var remainingTime: DateComponents {
        Calendar.current.dateComponents([.year, .day], from: Date(), to: predictedDeath)
    }

    // 死亡予定日のフォーマット（年月日）
    var predictedDeathComponents: DateComponentsResult {
        let components = Calendar.current.dateComponents([.year, .month, .day], from: predictedDeath)
        return DateComponentsResult(
            year: components.year ?? 2050,
            month: components.month ?? 1,
            day: components.day ?? 1
        )
    }

    // 残り時間のフォーマット
    var remainingYears: Int {
        remainingTime.year ?? 0
    }

    var remainingDays: Int {
        remainingTime.day ?? 0
    }

    // 年齢・進捗率
    var age: Double {
        let interval = Date().timeIntervalSince(birthday)
        return interval / (365.25 * 24 * 60 * 60)
    }

    var ageInt: Int {
        return Int(age)
    }

    var progress: Double {
        min(age / predictedLifeSpan, 1.0)
    }

    var progressPercent: String {
        String(format: "%.1f", progress * 100)
    }

    // periphery:ignore - UI state management
    // ユーザー日齢
    var userDays: Int {
        let now = Date()
        let components = Calendar.current.dateComponents([.day], from: birthday, to: now)
        return components.day ?? 0
    }
}

// MARK: - Animation Methods
extension LifeResultView {
    // ドラマチックな演出シーケンス
    func startDramaticSequence() {
        guard isViewActive && !appStateManager.isResetting else { return }

        if hasSeenDramaticSequence {
            showAllElementsImmediately()
            return
        }

        playFirstTimeSequence()
    }

    // 2回目以降: 演出をスキップして即座に全要素を表示
    private func showAllElementsImmediately() {
        doorOffset = 200
        showHourglass = true
        hourglassOpacity = 1.0
        hourglassScale = 1.0
        showRemainingTime = true
        countUpYears = remainingYears
        countUpDays = remainingDays
        showDeathDate = true
        deathYearCount = predictedDeathComponents.year
        showProgress = true
        progressValue = progress
        showEpisode = true
        showFinalMessage = true
        if !bgmStarted && !appStateManager.isResetting {
            soundManager.playBackgroundMusic(filename: "saigono", withExtension: "m4a")
            bgmStarted = true
        }
    }

    // 初回: ドラマチック演出シーケンス
    private func playFirstTimeSequence() {
        soundManager.playSoundEffect(filename: "sweep", withExtension: "m4a", volume: 0.5, syncWithBGMVolume: true)

        withAnimation(.easeInOut(duration: 1.5)) {
            doorOffset = 200
        }

        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            showHourglass = true
            hourglassOpacity = 1.0
            withAnimation(.spring(response: 1.2, dampingFraction: 0.8).delay(0.5)) {
                hourglassScale = 1.0
            }
        }

        DispatchQueue.main.asyncAfter(deadline: .now() + 2.5) {
            showRemainingTime = true
            animateCountUp()
        }

        DispatchQueue.main.asyncAfter(deadline: .now() + 3.5) {
            if isViewActive && !bgmStarted && !appStateManager.isResetting {
                soundManager.playBackgroundMusic(filename: "saigono", withExtension: "m4a")
                bgmStarted = true
            }
        }

        DispatchQueue.main.asyncAfter(deadline: .now() + 3.5) {
            showDeathDate = true
            animateDeathYearCount()
        }

        DispatchQueue.main.asyncAfter(deadline: .now() + 4.5) {
            showProgress = true
            animateProgress()
        }

        DispatchQueue.main.asyncAfter(deadline: .now() + 5.5) {
            showEpisode = true
        }

        DispatchQueue.main.asyncAfter(deadline: .now() + 6.5) {
            showFinalMessage = true
            hasSeenDramaticSequence = true
        }
    }

    // カウントアップアニメーション
    func animateCountUp() {
        let duration = 1.0
        let steps = 30
        let stepDuration = duration / Double(steps)

        // カウントアップサウンドシーケンス（設定でONの場合のみ）
        // SoundManager.shared.playCountUpSequence(count: 10, interval: 0.1)

        for index in 0...steps {
            DispatchQueue.main.asyncAfter(deadline: .now() + Double(index) * stepDuration) {
                countUpYears = Int(Double(remainingYears) * Double(index) / Double(steps))
                countUpDays = Int(Double(remainingDays) * Double(index) / Double(steps))
            }
        }
    }

    // 死亡年のカウントアップ
    func animateDeathYearCount() {
        let targetYear = predictedDeathComponents.year
        let currentYear = Calendar.current.component(.year, from: Date())
        let duration = 1.5
        let steps = 30
        let stepDuration = duration / Double(steps)

        for index in 0...steps {
            DispatchQueue.main.asyncAfter(deadline: .now() + Double(index) * stepDuration) {
                let progress = Double(index) / Double(steps)
                deathYearCount = Int(Double(currentYear) + (Double(targetYear - currentYear) * progress))
            }
        }
    }

    // 進捗率アニメーション
    func animateProgress() {
        let duration = 1.0
        let steps = 30
        let stepDuration = duration / Double(steps)

        for index in 0...steps {
            DispatchQueue.main.asyncAfter(deadline: .now() + Double(index) * stepDuration) {
                progressValue = progress * Double(index) / Double(steps)
            }
        }
    }
}

// MARK: - Episode Helper Methods
extension LifeResultView {
    /// エピソードテキストを解析して3つの部分に分割
    func parseEpisodeText(_ text: String) -> EpisodeContent {
        // パターン: "あなたと同じ○○歳のとき、〇〇は..."
        // 正規表現パターン: あなたと同じ(\d+)歳のとき、(.+?)は(.+)

        // パターンマッチング
        if let regex = try? NSRegularExpression(
            pattern: "あなたと同じ(\\d+)歳のとき、(.+?)は(.+)",
            options: []
        ) {
            let nsString = text as NSString
            let range = NSRange(location: 0, length: nsString.length)

            if let match = regex.firstMatch(in: text, options: [], range: range) {
                // 年齢部分を抽出
                let ageRange = match.range(at: 1)
                let age = nsString.substring(with: ageRange)
                let ageText = "あなたと同じ\(age)歳のとき"

                // 人物名部分を抽出
                let personRange = match.range(at: 2)
                let person = nsString.substring(with: personRange)
                let personName = "\(person)は"

                // エピソード本文を抽出
                let episodeRange = match.range(at: 3)
                var episodeText = nsString.substring(with: episodeRange)

                // フォールバック保護: 本文の先頭に人物名「〇〇は」が重複していれば削除
                let personWithHa = "\(person)は"
                if episodeText.hasPrefix(personWithHa) {
                    episodeText = String(episodeText.dropFirst(personWithHa.count))
                }

                return EpisodeContent(
                    ageText: ageText,
                    personName: personName,
                    episodeText: episodeText
                )
            }
        }

        // パースに失敗した場合のフォールバック
        lifeResultLogger.warning("エピソードパース失敗: \(text.prefix(50), privacy: .public)...")
        return EpisodeContent(
            ageText: "",
            personName: "",
            episodeText: text
        )
    }

    /// 今日のエピソードを取得
    func fetchDailyEpisode() {
        isLoadingEpisode = true
        lastFetchedAge = ageInt

        #if DEBUG
        print("🔍 エピソード取得開始: 年齢 \(ageInt)歳")
        #endif

        episodeManager.getDailyEpisode(for: ageInt) { episode in
            DispatchQueue.main.async {
                self.currentEpisode = episode
                self.isLoadingEpisode = false

                // お気に入り状態を初期化
                if let ep = episode {
                    self.isLiked = self.favoriteManager.isFavorite(episodeId: ep.id)
                } else {
                    self.isLiked = false
                }

                #if DEBUG
                if let episode = episode {
                    lifeResultLogger.debug("エピソード取得成功: \(episode.personName, privacy: .public)")
                } else {
                    lifeResultLogger.debug("エピソード取得失敗: nilが返されました")
                }
                #endif
            }
        }
    }
}

// MARK: - エピソードコンテンツセクション
/// エピソード表示のメインセクション（型チェック最適化のためbodyから分離）
private struct EpisodeContentSection: View {
    let isLoadingEpisode: Bool
    let currentEpisode: Episode?
    let ageInt: Int
    let fallbackEpisode: EpisodeContent
    let parseEpisodeText: (String) -> EpisodeContent

    var body: some View {
        if isLoadingEpisode {
            // ローディング表示
            VStack(spacing: 16) {
                ProgressView()
                    .progressViewStyle(CircularProgressViewStyle(tint: .white))
                    .scaleEffect(1.2)

                Text("今日のエピソードを読み込んでいます...")
                    .font(.system(size: 14))
                    .foregroundColor(.white.opacity(0.6))
            }
            .frame(height: 150)
            .frame(maxWidth: .infinity)
        } else if let episode = currentEpisode {
            EpisodeDisplayView(
                episode: episode,
                parseEpisodeText: parseEpisodeText
            )
        } else {
            // フォールバック（ハードコードされたエピソード）
            FallbackEpisodeView(ageInt: ageInt, fallbackEpisode: fallbackEpisode)
        }
    }
}

// MARK: - エピソード表示ビュー
/// 取得したエピソードを表示するビュー
private struct EpisodeDisplayView: View {
    let episode: Episode
    let parseEpisodeText: (String) -> EpisodeContent

    var body: some View {
        // 0歳の場合は特別な表示形式
        if episode.episodeAge == 0 {
            ZeroAgeEpisodeView(episode: episode)
        } else {
            // 1歳以上は通常のパース処理
            RegularEpisodeView(
                episode: episode,
                parsedEpisode: parseEpisodeText(episode.episode)
            )
        }
    }
}

// MARK: - 0歳エピソードビュー
/// 0歳用の特別な表示形式
private struct ZeroAgeEpisodeView: View {
    let episode: Episode

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            // タイトル（ゴールド）
            Text("0歳 ― 可能性のはじまり")
                .font(.system(size: 14, weight: .medium))
                .foregroundStyle(
                    LinearGradient(
                        colors: [AppColors.antiqueGold, AppColors.amber],
                        startPoint: .leading,
                        endPoint: .trailing
                    )
                )

            // 本文（人物名行は省略、エピソード本文のみ）
            Text(episode.getDisplayText(includePrefix: true, includeAgePhrase: false))
                .font(.system(size: 16))
                .foregroundColor(.white.opacity(0.9))
                .lineSpacing(8)
                .multilineTextAlignment(.leading)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}

// MARK: - 通常エピソードビュー
/// 1歳以上の通常エピソード表示
private struct RegularEpisodeView: View {
    let episode: Episode
    let parsedEpisode: EpisodeContent

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            // 年齢部分（ゴールド、小さめ）
            Text(parsedEpisode.ageText)
                .font(.system(size: 14, weight: .medium))
                .foregroundStyle(
                    LinearGradient(
                        colors: [AppColors.antiqueGold, AppColors.amber],
                        startPoint: .leading,
                        endPoint: .trailing
                    )
                )

            // 人物名部分（白、大きめ）+ 作品名（架空キャラの場合）
            PersonNameView(episode: episode, parsedEpisode: parsedEpisode)

            // エピソード本文（通常）
            Text(parsedEpisode.episodeText)
                .font(.system(size: 16))
                .foregroundColor(.white.opacity(0.9))
                .lineSpacing(8)
                .multilineTextAlignment(.leading)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}

// MARK: - 人物名表示ビュー
/// 人物名を表示（架空キャラは作品名付き）
private struct PersonNameView: View {
    let episode: Episode
    let parsedEpisode: EpisodeContent

    var body: some View {
        // EPUP原則: 架空キャラクターの名前には必ず作品名を併記
        if episode.isFictional, let workTitle = episode.workTitle {
            // 架空キャラ: 「〇〇『作品名』は」形式
            // エッジケース: 「は」だけの名前や空文字を防止
            let personNameWithoutHa = getPersonNameWithoutHa()

            HStack(alignment: .lastTextBaseline, spacing: 0) {
                Text(personNameWithoutHa)
                    .font(.system(size: 20, weight: .semibold))
                    .foregroundColor(.white)

                Text("『\(workTitle)』")
                    .font(.system(size: 14))
                    .foregroundColor(.white.opacity(0.7))

                Text("は")
                    .font(.system(size: 20, weight: .semibold))
                    .foregroundColor(.white)
            }
        } else {
            // 実在人物: 従来通り「〇〇は」
            Text(parsedEpisode.personName)
                .font(.system(size: 20, weight: .semibold))
                .foregroundColor(.white)
        }
    }

    private func getPersonNameWithoutHa() -> String {
        if parsedEpisode.personName.hasSuffix("は") && parsedEpisode.personName.count > 1 {
            return String(parsedEpisode.personName.dropLast())
        }
        return parsedEpisode.personName
    }
}

// MARK: - フォールバックエピソードビュー
/// API取得失敗時に表示するフォールバックエピソードのビュー
private struct FallbackEpisodeView: View {
    let ageInt: Int
    let fallbackEpisode: EpisodeContent

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            // 年齢部分（ゴールド、小さめ）
            Text(fallbackEpisode.ageText)
                .font(.system(size: 14, weight: .medium))
                .foregroundStyle(
                    LinearGradient(
                        colors: [AppColors.antiqueGold, AppColors.amber],
                        startPoint: .leading,
                        endPoint: .trailing
                    )
                )

            // 人物名部分（白、大きめ）
            Text(fallbackEpisode.personName)
                .font(.system(size: 20, weight: .semibold))
                .foregroundColor(.white)

            // エピソード本文（通常）
            Text(fallbackEpisode.episodeText)
                .font(.system(size: 16))
                .foregroundColor(.white.opacity(0.9))
                .lineSpacing(8)
                .multilineTextAlignment(.leading)
                .fixedSize(horizontal: false, vertical: true)
        }
        .onAppear {
            lifeResultLogger.warning("API取得失敗、フォールバックエピソードを表示: age=\(ageInt)")
        }
    }
}
