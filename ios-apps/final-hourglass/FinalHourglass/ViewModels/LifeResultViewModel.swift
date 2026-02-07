import Combine
import Foundation
import SwiftUI

/// 寿命計算結果画面のViewModel
/// ビジネスロジックをViewから分離し、テスタビリティを向上
@MainActor
final class LifeResultViewModel: ObservableObject {
    // MARK: - Published Properties

    /// 残り年数（カウントアップアニメーション用）
    @Published var countUpYears: Int = 0

    /// 残り日数（カウントアップアニメーション用）
    @Published var countUpDays: Int = 0

    /// 死亡予定年（カウントアップアニメーション用）
    @Published var deathYearCount: Int = 0

    /// 人生進捗率（アニメーション用）
    @Published var progressValue: Double = 0.0

    /// 現在のエピソード
    @Published var currentEpisode: Episode?

    /// エピソード読み込み中フラグ
    @Published var isLoadingEpisode: Bool = false

    /// お気に入り状態
    @Published var isLiked: Bool = false

    /// ドラマチック演出のState
    @Published var showIntro: Bool = true
    @Published var showRemainingTime: Bool = false
    @Published var showDeathDate: Bool = false
    @Published var showHourglass: Bool = false
    @Published var showProgress: Bool = false
    @Published var showEpisode: Bool = false
    @Published var showFinalMessage: Bool = false

    // MARK: - Private Properties

    private var lastFetchedAge: Int = -1
    private var cancellables = Set<AnyCancellable>()

    // Managers
    private let episodeManager: EpisodeManager
    private let favoriteManager: FavoriteEpisodeManager

    // MARK: - Computed Properties

    /// 計算された残り年数（実際の値）
    var remainingYears: Int {
        // UserModelから計算（依存注入で対応可能）
        0
    }

    /// 計算された残り日数（実際の値）
    var remainingDays: Int {
        0
    }

    // MARK: - Initialization

    init(
        episodeManager: EpisodeManager = .shared,
        favoriteManager: FavoriteEpisodeManager = .shared
    ) {
        self.episodeManager = episodeManager
        self.favoriteManager = favoriteManager
    }

    // MARK: - Public Methods

    /// ドラマチック演出を開始
    func startDramaticSequence(
        remainingYears: Int,
        remainingDays: Int,
        deathYear: Int
    ) {
        // 残り時間を表示
        Task { @MainActor in
            try? await Task.sleep(nanoseconds: 2_000_000_000) // 2秒
            showRemainingTime = true
            animateCountUp(
                targetYears: remainingYears,
                targetDays: remainingDays
            )
        }

        // 死亡予定日を表示
        Task { @MainActor in
            try? await Task.sleep(nanoseconds: 3_500_000_000) // 3.5秒
            showDeathDate = true
            animateDeathYearCount(targetYear: deathYear)
        }

        // 進捗率を表示
        Task { @MainActor in
            try? await Task.sleep(nanoseconds: 4_500_000_000) // 4.5秒
            showProgress = true
        }

        // エピソードを表示
        Task { @MainActor in
            try? await Task.sleep(nanoseconds: 5_500_000_000) // 5.5秒
            showEpisode = true
        }

        // 最後の問いかけを表示
        Task { @MainActor in
            try? await Task.sleep(nanoseconds: 6_500_000_000) // 6.5秒
            showFinalMessage = true
        }
    }

    /// 今日のエピソードを取得
    func fetchDailyEpisode(for age: Int) {
        guard age != lastFetchedAge else { return }

        isLoadingEpisode = true
        lastFetchedAge = age

        episodeManager.getDailyEpisode(for: age) { [weak self] episode in
            Task { @MainActor in
                self?.currentEpisode = episode
                self?.isLoadingEpisode = false

                if let ep = episode {
                    self?.isLiked = self?.favoriteManager.isFavorite(episodeId: ep.id) ?? false
                } else {
                    self?.isLiked = false
                }
            }
        }
    }

    /// お気に入りをトグル
    func toggleFavorite() {
        guard let episode = currentEpisode else { return }

        if isLiked {
            favoriteManager.removeFavorite(episodeId: episode.id)
        } else {
            favoriteManager.addFavorite(episode: episode)
        }
        isLiked.toggle()
    }

    /// 演出状態をリセット
    func resetAnimation() {
        showIntro = true
        showRemainingTime = false
        showDeathDate = false
        showHourglass = false
        showProgress = false
        showEpisode = false
        showFinalMessage = false
        countUpYears = 0
        countUpDays = 0
        deathYearCount = 0
        progressValue = 0.0
    }

    // MARK: - Private Methods

    /// カウントアップアニメーション
    private func animateCountUp(targetYears: Int, targetDays: Int) {
        let duration = 1.0
        let steps = 30
        let stepDuration = duration / Double(steps)

        for index in 0...steps {
            Task { @MainActor in
                try? await Task.sleep(
                    nanoseconds: UInt64(Double(index) * stepDuration * 1_000_000_000)
                )
                countUpYears = Int(Double(targetYears) * Double(index) / Double(steps))
                countUpDays = Int(Double(targetDays) * Double(index) / Double(steps))
            }
        }
    }

    /// 死亡年のカウントアップ
    private func animateDeathYearCount(targetYear: Int) {
        let currentYear = Calendar.current.component(.year, from: Date())
        let duration = 1.5
        let steps = 30
        let stepDuration = duration / Double(steps)

        for index in 0...steps {
            Task { @MainActor in
                try? await Task.sleep(
                    nanoseconds: UInt64(Double(index) * stepDuration * 1_000_000_000)
                )
                let progress = Double(index) / Double(steps)
                deathYearCount = Int(Double(currentYear) + (Double(targetYear - currentYear) * progress))
            }
        }
    }

    /// 進捗率アニメーション
    func animateProgress(targetProgress: Double) {
        let duration = 1.0
        let steps = 30
        let stepDuration = duration / Double(steps)

        for index in 0...steps {
            Task { @MainActor in
                try? await Task.sleep(
                    nanoseconds: UInt64(Double(index) * stepDuration * 1_000_000_000)
                )
                progressValue = targetProgress * Double(index) / Double(steps)
            }
        }
    }
}

// MARK: - Episode Parsing

extension LifeResultViewModel {
    /// エピソードコンテンツの構造体
    struct ParsedEpisodeContent {
        let ageText: String
        let personName: String
        let episodeText: String
    }

    /// エピソードテキストを解析して3つの部分に分割
    func parseEpisodeText(_ text: String) -> ParsedEpisodeContent {
        // パターン: "あなたと同じ○○歳のとき、〇〇は..."
        if let regex = try? NSRegularExpression(
            pattern: "あなたと同じ(\\d+)歳のとき、(.+?)は(.+)",
            options: []
        ) {
            let nsString = text as NSString
            let range = NSRange(location: 0, length: nsString.length)

            if let match = regex.firstMatch(in: text, options: [], range: range) {
                let ageRange = match.range(at: 1)
                let age = nsString.substring(with: ageRange)
                let ageText = "あなたと同じ\(age)歳のとき"

                let personRange = match.range(at: 2)
                let person = nsString.substring(with: personRange)
                let personName = "\(person)は"

                let episodeRange = match.range(at: 3)
                var episodeText = nsString.substring(with: episodeRange)

                // フォールバック保護
                let personWithHa = "\(person)は"
                if episodeText.hasPrefix(personWithHa) {
                    episodeText = String(episodeText.dropFirst(personWithHa.count))
                }

                return ParsedEpisodeContent(
                    ageText: ageText,
                    personName: personName,
                    episodeText: episodeText
                )
            }
        }

        // パースに失敗した場合
        return ParsedEpisodeContent(
            ageText: "",
            personName: "",
            episodeText: text
        )
    }
}
