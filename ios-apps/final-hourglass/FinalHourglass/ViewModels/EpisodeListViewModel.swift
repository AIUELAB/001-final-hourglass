import Combine
import Foundation
import SwiftUI

/// エピソード一覧画面のViewModel
/// エピソードの取得・フィルタリング・お気に入り管理ロジックをViewから分離
@MainActor
final class EpisodeListViewModel: ObservableObject {
    // MARK: - Published Properties

    /// 表示するエピソード一覧
    @Published var episodes: [Episode] = []

    /// お気に入りエピソード一覧
    @Published var favoriteEpisodes: [FavoriteEpisode] = []

    /// 選択中のエピソード
    @Published var selectedEpisode: Episode?

    /// 選択中のお気に入り
    @Published var selectedFavorite: FavoriteEpisode?

    /// 読み込み中フラグ
    @Published var isLoading: Bool = false

    /// エラーメッセージ
    @Published var errorMessage: String?

    /// 検索クエリ
    @Published var searchQuery: String = ""

    /// フィルタリング条件
    @Published var filterOptions: FilterOptions = FilterOptions()

    /// ソート順
    @Published var sortOrder: SortOrder = .dateDescending

    // MARK: - Private Properties

    private var cancellables = Set<AnyCancellable>()
    private let episodeManager: EpisodeManager
    private let favoriteManager: FavoriteEpisodeManager

    // MARK: - Computed Properties

    /// フィルタリング・検索適用後のエピソード
    var filteredEpisodes: [Episode] {
        var result = episodes

        // 検索クエリでフィルタリング
        if !searchQuery.isEmpty {
            result = result.filter { ep in
                ep.personName.localizedCaseInsensitiveContains(searchQuery) ||
                (ep.personNameJa?.localizedCaseInsensitiveContains(searchQuery) ?? false) ||
                ep.episode.localizedCaseInsensitiveContains(searchQuery)
            }
        }

        // 年齢フィルター
        if let minAge = filterOptions.minAge {
            result = result.filter { ($0.episodeAge ?? 0) >= minAge }
        }
        if let maxAge = filterOptions.maxAge {
            result = result.filter { ($0.episodeAge ?? 0) <= maxAge }
        }

        // カテゴリフィルター
        if let category = filterOptions.category {
            result = result.filter { $0.episodeType == category }
        }

        // ソート
        result = sortEpisodes(result)

        return result
    }

    /// フィルタリング・検索適用後のお気に入り
    var filteredFavorites: [FavoriteEpisode] {
        var result = favoriteManager.favorites

        // 検索クエリでフィルタリング
        if !searchQuery.isEmpty {
            result = result.filter { favorite in
                favorite.episode.personName.localizedCaseInsensitiveContains(searchQuery) ||
                (favorite.episode.personNameJa?.localizedCaseInsensitiveContains(searchQuery) ?? false) ||
                favorite.episode.episode.localizedCaseInsensitiveContains(searchQuery)
            }
        }

        // ソート（お気に入りは追加日順）
        switch sortOrder {
        case .dateDescending:
            result = result.sorted { $0.addedAt > $1.addedAt }
        case .dateAscending:
            result = result.sorted { $0.addedAt < $1.addedAt }
        case .ageAscending:
            result = result.sorted { ($0.episode.episodeAge ?? 0) < ($1.episode.episodeAge ?? 0) }
        case .ageDescending:
            result = result.sorted { ($0.episode.episodeAge ?? 0) > ($1.episode.episodeAge ?? 0) }
        case .nameAscending:
            result = result.sorted { $0.episode.personName < $1.episode.personName }
        case .nameDescending:
            result = result.sorted { $0.episode.personName > $1.episode.personName }
        }

        return result
    }

    /// お気に入りが空かどうか
    var isFavoritesEmpty: Bool {
        favoriteManager.favorites.isEmpty
    }

    /// お気に入りの件数
    var favoritesCount: Int {
        favoriteManager.favorites.count
    }

    // MARK: - Initialization

    init(
        episodeManager: EpisodeManager = .shared,
        favoriteManager: FavoriteEpisodeManager = .shared
    ) {
        self.episodeManager = episodeManager
        self.favoriteManager = favoriteManager

        // お気に入りの変更を監視
        setupFavoriteObserver()
    }

    // MARK: - Public Methods

    /// エピソードを取得（年齢指定）
    func fetchEpisodes(for age: Int) {
        isLoading = true
        errorMessage = nil

        episodeManager.getDailyEpisode(for: age) { [weak self] episode in
            Task { @MainActor in
                self?.isLoading = false
                if let ep = episode {
                    self?.episodes = [ep]
                } else {
                    self?.episodes = []
                }
            }
        }
    }

    /// お気に入りを更新
    func refreshFavorites() {
        favoriteEpisodes = favoriteManager.favorites
    }

    /// お気に入りに追加
    func addToFavorites(_ episode: Episode) {
        favoriteManager.addFavorite(episode: episode)
        refreshFavorites()
    }

    /// お気に入りから削除
    func removeFromFavorites(episodeId: String) {
        favoriteManager.removeFavorite(episodeId: episodeId)
        refreshFavorites()
    }

    /// お気に入りを削除（インデックス指定）
    func removeFromFavorites(at offsets: IndexSet) {
        favoriteManager.removeFavorites(at: offsets)
        refreshFavorites()
    }

    /// お気に入りかどうかを確認
    func isFavorite(episodeId: String) -> Bool {
        favoriteManager.isFavorite(episodeId: episodeId)
    }

    /// お気に入りをトグル
    func toggleFavorite(_ episode: Episode) {
        if isFavorite(episodeId: episode.id) {
            removeFromFavorites(episodeId: episode.id)
        } else {
            addToFavorites(episode)
        }
    }

    /// フィルターをリセット
    func resetFilters() {
        filterOptions = FilterOptions()
        searchQuery = ""
    }

    /// エピソードを選択
    func selectEpisode(_ episode: Episode) {
        selectedEpisode = episode
    }

    /// お気に入りを選択
    func selectFavorite(_ favorite: FavoriteEpisode) {
        selectedFavorite = favorite
    }

    /// 選択を解除
    func clearSelection() {
        selectedEpisode = nil
        selectedFavorite = nil
    }

    // MARK: - Private Methods

    /// お気に入りの変更を監視
    private func setupFavoriteObserver() {
        // FavoriteEpisodeManagerの変更を監視
        favoriteManager.objectWillChange
            .receive(on: DispatchQueue.main)
            .sink { [weak self] _ in
                self?.refreshFavorites()
            }
            .store(in: &cancellables)

        // 初期データを読み込み
        refreshFavorites()
    }

    /// エピソードをソート
    private func sortEpisodes(_ episodes: [Episode]) -> [Episode] {
        switch sortOrder {
        case .dateDescending, .dateAscending:
            // エピソードには日付がないため、IDでソート
            return sortOrder == .dateDescending
                ? episodes.sorted { $0.id > $1.id }
                : episodes.sorted { $0.id < $1.id }
        case .ageAscending:
            return episodes.sorted { ($0.episodeAge ?? 0) < ($1.episodeAge ?? 0) }
        case .ageDescending:
            return episodes.sorted { ($0.episodeAge ?? 0) > ($1.episodeAge ?? 0) }
        case .nameAscending:
            return episodes.sorted { $0.personName < $1.personName }
        case .nameDescending:
            return episodes.sorted { $0.personName > $1.personName }
        }
    }
}

// MARK: - Supporting Types

extension EpisodeListViewModel {
    /// フィルタリングオプション
    struct FilterOptions {
        var minAge: Int?
        var maxAge: Int?
        var category: String?
        var personType: EpisodePersonType?

        enum EpisodePersonType: String, CaseIterable {
            case historical = "歴史上の人物"
            case fictional = "架空のキャラクター"
            case contemporary = "現代の著名人"
        }
    }

    /// ソート順
    enum SortOrder: String, CaseIterable {
        case dateDescending = "新しい順"
        case dateAscending = "古い順"
        case ageAscending = "年齢（若い順）"
        case ageDescending = "年齢（高い順）"
        case nameAscending = "名前（A-Z）"
        case nameDescending = "名前（Z-A）"
    }
}

// MARK: - Episode Text Parsing

extension EpisodeListViewModel {
    /// エピソードのプレビューテキストを生成
    func previewText(for episode: Episode, maxLength: Int = 50) -> String {
        var text = episode.episode

        // "あなたと同じ○歳のとき、"を削除
        if let regex = try? NSRegularExpression(
            pattern: "^あなたと同じ\\d+歳のとき、",
            options: []
        ) {
            let range = NSRange(location: 0, length: text.utf16.count)
            text = regex.stringByReplacingMatches(in: text, options: [], range: range, withTemplate: "")
        }

        // 長さを制限
        if text.count > maxLength {
            text = String(text.prefix(maxLength)) + "..."
        }

        return text
    }

    /// 人物名を取得（日本語名優先）
    func displayName(for episode: Episode) -> String {
        episode.personNameJa ?? episode.personName
    }
}
