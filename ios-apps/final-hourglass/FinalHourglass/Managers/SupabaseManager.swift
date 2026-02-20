//
//  SupabaseManager.swift
//  FinalHourglass
//
//  Supabaseからエピソードデータを取得するマネージャー
//  EpisodeManagerのFirebase実装を置き換える/並行運用するために設計
//

import Auth
import Foundation
@preconcurrency import Supabase

// MARK: - Supabase Episode Model (DB mapping)

/// Supabaseテーブルに対応するエピソードモデル
/// - Note: 内部DBマッピング用。外部からは `Episode` モデルを使用
struct SupabaseEpisode: Codable { // periphery:ignore - Internal DB mapping model
    let episodeId: String
    let personId: String?
    let personName: String
    let age: Int?
    let category: String?
    let episodeText: String
    let episodeType: String?
    let superTotalScore: Double?
    let desirabilityScore: Double?  // 望ましさスコア（ソート用）
    let hybridScore: Double?
    let compositeScore: Double?
    let fameScoreV3: Double?
    let episodeFameV6: Double?
    let episodeFameTierV6: Int?
    let memorabilityScore: Double?
    let empathyScore: Double?
    let surpriseScore: Double?
    let generationQualityScore: Double?
    let educationalValue: Double?
    let storyQuality: Double?
    let factualDensity: Double?
    let iconicScore: Double?
    let personType: String?
    let workTitle: String?
    let isGroupMember: Bool?
    let groupName: String?
    let episodeCount: Int?
    let wikipediaPv: Int?
    let createdAt: String?

    enum CodingKeys: String, CodingKey {
        case episodeId = "episode_id"
        case personId = "person_id"
        case personName = "person_name"
        case age
        case category
        case episodeText = "episode_text"
        case episodeType = "episode_type"
        case superTotalScore = "super_total_score"
        case desirabilityScore = "desirability_score"
        case hybridScore = "hybrid_score"
        case compositeScore = "composite_score"
        case fameScoreV3 = "fame_score_v3"
        case episodeFameV6 = "episode_fame_v6"
        case episodeFameTierV6 = "episode_fame_tier_v6"
        case memorabilityScore = "memorability_score"
        case empathyScore = "empathy_score"
        case surpriseScore = "surprise_score"
        case generationQualityScore = "generation_quality_score"
        case educationalValue = "educational_value"
        case storyQuality = "story_quality"
        case factualDensity = "factual_density"
        case iconicScore = "iconic_score"
        case personType = "person_type"
        case workTitle = "work_title"
        case isGroupMember = "is_group_member"
        case groupName = "group_name"
        case episodeCount = "episode_count"
        case wikipediaPv = "wikipedia_pv"
        case createdAt = "created_at"
    }

    /// 既存のEpisodeモデルに変換
    func toEpisode() -> Episode {
        return Episode(
            id: episodeId,
            personName: personName,
            personNameJa: nil,  // Supabaseには日本語名が別フィールドとしてない
            episode: episodeText,
            episodeAge: age,
            episodeType: episodeType,
            createdAt: nil,  // 文字列からDateへの変換は必要に応じて
            characterCount: episodeText.count,
            qualityScore: Int(generationQualityScore ?? 0),
            tags: nil,
            formatVersion: nil,
            personType: personType.flatMap { PersonType(rawValue: $0.uppercased()) },
            workTitle: workTitle
        )
    }
}

// MARK: - Supabase Manager

/// Supabaseとの通信を管理するシングルトン
final class SupabaseManager {
    // MARK: - Singleton

    static let shared = SupabaseManager()

    // MARK: - Properties

    private let client: SupabaseClient

    // MARK: - Initialization

    private init() {
        client = SupabaseClient(
            supabaseURL: SupabaseConfig.projectURL,
            supabaseKey: SupabaseConfig.anonKey,
            options: SupabaseClientOptions(
                auth: .init(
                    storage: KeychainLocalStorage(),
                    // Supabase Swift SDK 2.40+ 警告対応
                    // ローカルセッションを常に発行する新しい動作にオプトイン
                    emitLocalSessionAsInitialSession: true
                )
            )
        )
        #if DEBUG
        print("✅ SupabaseManager initialized")
        #endif
    }

    // MARK: - Public Methods

    /// 指定した年齢のエピソードを取得
    /// - Parameters:
    ///   - age: 検索対象の年齢
    ///   - limit: 取得件数上限
    /// - Returns: エピソード配列
    func fetchEpisodes(forAge age: Int, limit: Int = 50) async throws -> [Episode] { // periphery:ignore
        let supabaseEpisodes: [SupabaseEpisode] = try await client
            .from(SupabaseConfig.Tables.episodes)
            .select()
            .eq("age", value: age)
            .order("hybrid_score", ascending: false)
            .order("episode_id", ascending: true)  // タイブレーク: 決定論的ソート
            .limit(limit)
            .execute()
            .value

        #if DEBUG
        print("📥 Supabase: \(supabaseEpisodes.count)件取得 (age=\(age))")
        #endif

        return supabaseEpisodes.map { $0.toEpisode() }
    }

    /// 年齢範囲でエピソードを取得
    /// - Parameters:
    ///   - minAge: 最小年齢
    ///   - maxAge: 最大年齢
    ///   - limit: 取得件数上限
    /// - Returns: エピソード配列
    func fetchEpisodes(minAge: Int, maxAge: Int, limit: Int = 100) async throws -> [Episode] { // periphery:ignore
        let supabaseEpisodes: [SupabaseEpisode] = try await client
            .from(SupabaseConfig.Tables.episodes)
            .select()
            .gte("age", value: minAge)
            .lte("age", value: maxAge)
            .order("hybrid_score", ascending: false)
            .order("episode_id", ascending: true)  // タイブレーク: 決定論的ソート
            .limit(limit)
            .execute()
            .value

        #if DEBUG
        print("📥 Supabase: \(supabaseEpisodes.count)件取得 (age=\(minAge)-\(maxAge))")
        #endif

        return supabaseEpisodes.map { $0.toEpisode() }
    }

    /// ランダムエピソードを取得（年齢指定）
    /// - Parameters:
    ///   - age: 検索対象の年齢
    ///   - excludeIds: 除外するエピソードID
    /// - Returns: ランダムに選ばれたエピソード
    func fetchRandomEpisode(forAge age: Int, excludeIds: Set<String> = []) async throws -> Episode? { // periphery:ignore
        // まず対象年齢のエピソードを取得
        let episodes = try await fetchEpisodes(forAge: age, limit: 100)

        // 除外IDをフィルタリング
        let filtered = episodes.filter { !excludeIds.contains($0.id) }

        // super_total_score最高のエピソードを選択（降順ソート済みなので先頭）
        return filtered.first
    }

    /// 年齢範囲を広げながらエピソードを探す（Firebase実装と同様のロジック）
    /// - Parameters:
    ///   - targetAge: 目標年齢
    ///   - excludeIds: 除外するエピソードID
    ///   - maxRange: 最大検索範囲
    /// - Returns: 見つかったエピソード
    func fetchEpisodeWithFallback(
        targetAge: Int,
        excludeIds: Set<String> = [],
        maxRange: Int = 10
    ) async throws -> Episode? {
        // まず完全一致を試行
        if let episode = try await fetchRandomEpisode(forAge: targetAge, excludeIds: excludeIds) {
            return episode
        }

        // 範囲を広げながら検索
        for range in 1...maxRange {
            let minAge = targetAge - range
            let maxAge = targetAge + range

            let episodes = try await fetchEpisodes(minAge: minAge, maxAge: maxAge, limit: 50)
            let filtered = episodes.filter { !excludeIds.contains($0.id) }

            if let episode = filtered.first {
                #if DEBUG
                print("🔍 Supabase: 範囲±\(range)歳で発見")
                #endif
                return episode
            }
        }

        return nil
    }

    /// 総エピソード数を取得
    func fetchTotalCount() async throws -> Int { // periphery:ignore
        let response = try await client
            .from(SupabaseConfig.Tables.episodes)
            .select("episode_id", head: true, count: .exact)
            .execute()

        return response.count ?? 0
    }

    /// 接続テスト
    func testConnection() async -> Bool {
        do {
            let count = try await fetchTotalCount()
            #if DEBUG
            print("✅ Supabase接続成功: \(count)件のエピソード")
            #endif
            return count > 0
        } catch {
            #if DEBUG
            print("❌ Supabase接続エラー: \(error.localizedDescription)")
            #endif
            return false
        }
    }
}
