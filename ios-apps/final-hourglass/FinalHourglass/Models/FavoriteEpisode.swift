import Foundation
import os

// Logger定義
private let favoriteLogger = Logger(subsystem: "com.finalhourglass.favorite", category: "persistence")

/// お気に入りエピソードの記録
struct FavoriteEpisode: Codable, Identifiable {
    let id: String           // エピソードの一意ID（Episode.idを使用）
    let addedAt: Date        // お気に入りに追加した日時
    let episode: Episode     // エピソード本体

    // MARK: - DateFormatter（パフォーマンス向上のためstatic）

    private static let fullDateFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy年M月d日 HH:mm"
        formatter.locale = Locale(identifier: "ja_JP")
        return formatter
    }()

    private static let shortDateFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "M/d"
        return formatter
    }()

    // MARK: - Initializers

    init(episode: Episode, addedAt: Date = Date()) {
        self.id = episode.id
        self.addedAt = addedAt
        self.episode = episode
    }

    /// Codable デコード時のカスタムイニシャライザ
    /// idとepisode.idの整合性を検証
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let decodedEpisode = try container.decode(Episode.self, forKey: .episode)
        let decodedId = try container.decode(String.self, forKey: .id)

        // 不変条件: id == episode.id
        guard decodedId == decodedEpisode.id else {
            throw DecodingError.dataCorruptedError(
                forKey: .id,
                in: container,
                debugDescription: "id must match episode.id (got \(decodedId), expected \(decodedEpisode.id))"
            )
        }

        self.id = decodedId
        self.addedAt = try container.decode(Date.self, forKey: .addedAt)
        self.episode = decodedEpisode
    }

    // MARK: - Computed Properties

    /// フォーマット済み追加日時
    var formattedAddedAt: String {
        Self.fullDateFormatter.string(from: addedAt)
    }

    /// 短い日付表示
    var shortDate: String {
        Self.shortDateFormatter.string(from: addedAt)
    }
}

/// お気に入りエピソード管理クラス
/// - Note: UserDefaultsでJSON永続化。ViewedEpisodeHistoryと同パターン。
/// - Note: スレッドセーフ（内部でDispatchQueueを使用）
class FavoriteEpisodeManager: ObservableObject {
    static let shared = FavoriteEpisodeManager()

    @Published private(set) var favorites: [FavoriteEpisode] = []

    private let userDefaults = UserDefaults.standard
    private let favoritesKey = "favoriteEpisodes"

    // periphery:ignore - Future use for sync/debug
    /// スレッドセーフティのための同期キュー
    private let syncQueue = DispatchQueue(label: "com.finalhourglass.favorite.sync")

    private init() {
        loadFavorites()
    }

    // MARK: - Public Methods

    /// エピソードがお気に入りに登録されているか確認
    func isFavorite(episodeId: String) -> Bool {
        return favorites.contains { $0.id == episodeId }
    }

    /// お気に入りを登録/解除（トグル）
    /// - Returns: 登録後の状態（true=登録済み、false=解除済み）
    @discardableResult
    func toggleFavorite(episode: Episode) -> Bool {
        if isFavorite(episodeId: episode.id) {
            removeFavorite(episodeId: episode.id)
            return false
        } else {
            addFavorite(episode: episode)
            return true
        }
    }

    /// お気に入りに追加
    func addFavorite(episode: Episode) {
        // 重複チェック（同一エピソードは1件）
        guard !isFavorite(episodeId: episode.id) else {
            favoriteLogger.warning("重複登録をスキップ: \(episode.id, privacy: .public)")
            return
        }

        let favorite = FavoriteEpisode(episode: episode)
        favorites.insert(favorite, at: 0)  // 先頭に追加（最新が上）

        saveFavorites()
        favoriteLogger.info("お気に入りに追加: \(episode.id, privacy: .public)")
    }

    /// お気に入りから削除
    func removeFavorite(episodeId: String) {
        favorites.removeAll { $0.id == episodeId }
        saveFavorites()
        favoriteLogger.info("お気に入りから削除: \(episodeId, privacy: .public)")
    }

    /// 複数削除（インデックス指定）
    func removeFavorites(at offsets: IndexSet) {
        favorites.remove(atOffsets: offsets)
        saveFavorites()
    }

    // periphery:ignore - Future use for sync/debug
    /// 全件クリア
    func clearAllFavorites() {
        favorites = []
        saveFavorites()
        favoriteLogger.info("お気に入りを全件クリア")
    }

    // periphery:ignore - Future use for sync/debug
    /// お気に入り件数
    var count: Int {
        return favorites.count
    }

    // MARK: - Persistence

    /// 読み込み
    private func loadFavorites() {
        guard let data = userDefaults.data(forKey: favoritesKey) else {
            favorites = []
            return
        }

        do {
            let decoded = try JSONDecoder().decode([FavoriteEpisode].self, from: data)
            favorites = decoded
            favoriteLogger.info("お気に入りを読み込み: \(decoded.count, privacy: .public)件")
        } catch {
            // 破損データ時の復旧: 空配列で初期化
            favoriteLogger.error("お気に入りの読み込み失敗、初期化します: \(error.localizedDescription, privacy: .public)")
            favorites = []
            // 破損データを削除
            userDefaults.removeObject(forKey: favoritesKey)
        }
    }

    /// 保存
    private func saveFavorites() {
        do {
            let encoded = try JSONEncoder().encode(favorites)
            userDefaults.set(encoded, forKey: favoritesKey)
        } catch {
            // 保存失敗: ログに記録するが、アプリは落とさない
            favoriteLogger.error("お気に入りの保存失敗: \(error.localizedDescription, privacy: .public)")
        }
    }
}
