import Foundation

/// キャッシュ管理用のユーティリティ
class CacheManager {
    static let shared = CacheManager()

    private init() {}

    /// すべてのエピソードキャッシュをクリア
    func clearAllEpisodeCache() {
        let userDefaults = UserDefaults.standard

        // エピソード関連のキーをすべて削除
        userDefaults.removeObject(forKey: "viewedEpisodeIds")
        userDefaults.removeObject(forKey: "lastEpisodeDate")
        userDefaults.removeObject(forKey: "dailyEpisode")
        userDefaults.removeObject(forKey: "cachedEpisodes")

        // 即座に同期
        userDefaults.synchronize()

        print("✅ エピソードキャッシュをクリアしました")
    }

    /// キャッシュ状態を確認
    func checkCacheStatus() -> CacheStatus {
        let userDefaults = UserDefaults.standard

        let hasViewedIds = userDefaults.object(forKey: "viewedEpisodeIds") != nil
        let hasLastDate = userDefaults.object(forKey: "lastEpisodeDate") != nil
        let hasDailyEpisode = userDefaults.object(forKey: "dailyEpisode") != nil
        let hasCachedEpisodes = userDefaults.object(forKey: "cachedEpisodes") != nil

        return CacheStatus(
            hasViewedIds: hasViewedIds,
            hasLastDate: hasLastDate,
            hasDailyEpisode: hasDailyEpisode,
            hasCachedEpisodes: hasCachedEpisodes
        )
    }

    /// 古いキャッシュを検出
    func hasOldCache() -> Bool {
        let userDefaults = UserDefaults.standard

        // dailyEpisodeのデータを取得
        if let data = userDefaults.data(forKey: "dailyEpisode"),
           let episode = try? JSONDecoder().decode(Episode.self, from: data) {
            // person_name_jaが空またはpersonNameに"この人物"が含まれる場合は古いキャッシュ
            if episode.personNameJa == nil || episode.personNameJa?.isEmpty == true {
                return true
            }

            // エピソードテキストに"この人物"が含まれる場合も古いキャッシュ
            if episode.episode.contains("この人物") {
                return true
            }
        }

        // cachedEpisodesも確認
        if let data = userDefaults.data(forKey: "cachedEpisodes"),
           let episodes = try? JSONDecoder().decode([Episode].self, from: data) {
            for episode in episodes {
                if episode.personNameJa == nil || episode.personNameJa?.isEmpty == true {
                    return true
                }
                if episode.episode.contains("この人物") {
                    return true
                }
            }
        }

        return false
    }
}

/// キャッシュ状態を表す構造体
struct CacheStatus {
    let hasViewedIds: Bool
    let hasLastDate: Bool
    let hasDailyEpisode: Bool
    let hasCachedEpisodes: Bool

    // periphery:ignore - Debug description
    var description: String {
        return """
        キャッシュ状態:
        - 閲覧済みID: \(hasViewedIds ? "あり" : "なし")
        - 最終日付: \(hasLastDate ? "あり" : "なし")
        - 今日のエピソード: \(hasDailyEpisode ? "あり" : "なし")
        - キャッシュ済みエピソード: \(hasCachedEpisodes ? "あり" : "なし")
        """
    }
}
