import Foundation
import os

// Logger定義
private let episodeLogger = Logger(subsystem: "com.finalhourglass.episode", category: "validation")

/// 人物タイプ列挙型
enum PersonType: String, Codable {
    case real = "REAL"
    case fictional = "FICTIONAL"
    case unknown = "UNKNOWN"

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        let rawValue = try container.decode(String.self).uppercased()
        self = PersonType(rawValue: rawValue) ?? .unknown
    }
}

// エピソードデータモデル
// periphery:ignore:all - Codable properties for API compatibility
struct Episode: Codable {
    let id: String
    let personName: String
    let personNameJa: String?
    let episode: String
    let episodeAge: Int?  // エピソード発生時の年齢（death_age から名前変更）
    // periphery:ignore
    let episodeType: String?
    // periphery:ignore
    let createdAt: Date?
    // periphery:ignore
    let characterCount: Int?
    // periphery:ignore
    let qualityScore: Int?
    // periphery:ignore
    let tags: [String]?
    let formatVersion: String?  // 構造化フォーマットバージョン
    let personType: PersonType?  // 人物タイプ
    let workTitle: String?      // 架空作品名（架空キャラの場合）

    /// 架空キャラクターかどうかを判定
    /// personTypeがnilまたはunknownの場合は安全側に倒して架空キャラとして扱う
    var isFictional: Bool {
        guard let type = personType else {
            // nil の場合は安全側に倒す（品質チェック適用）
            episodeLogger.warning("personType が nil: person=\(self.personName, privacy: .public)")
            return true
        }
        return type == .fictional || type == .unknown
    }

    // 標準初期化子（Supabase/手動作成用）
    init(
        id: String,
        personName: String,
        personNameJa: String?,
        episode: String,
        episodeAge: Int?,
        episodeType: String?,
        createdAt: Date?,
        characterCount: Int?,
        qualityScore: Int?,
        tags: [String]?,
        formatVersion: String?,
        personType: PersonType? = nil,
        workTitle: String? = nil
    ) {
        self.id = id
        self.personName = personName
        self.personNameJa = personNameJa
        self.episode = episode
        self.episodeAge = episodeAge
        self.episodeType = episodeType
        self.createdAt = createdAt
        self.characterCount = characterCount
        self.qualityScore = qualityScore
        self.tags = tags
        self.formatVersion = formatVersion
        self.personType = personType
        self.workTitle = workTitle
    }

    // エピソード表示用メソッド（拡張版）
    func getDisplayText(includePrefix: Bool = true, includeAgePhrase: Bool = true) -> String {
        var text = episode

        // 「あなたと同じX歳のとき」を除去する処理
        if !includeAgePhrase {
            // 正規表現パターン: 「あなたと同じ数字歳の(とき|時)、?」
            let pattern = "^あなたと同じ\\d+歳の(とき|時)、?"
            do {
                let regex = try NSRegularExpression(pattern: pattern, options: [])
                let range = NSRange(text.startIndex..., in: text)
                text = regex.stringByReplacingMatches(
                    in: text,
                    options: [],
                    range: range,
                    withTemplate: ""
                )
            } catch {
                episodeLogger.error("年齢フレーズ正規表現コンパイル失敗: \(error.localizedDescription, privacy: .public)")
            }
        }

        // 既存のプレフィックス処理
        if !includePrefix && formatVersion == "structured_v1" {
            // プレフィックスを削除して本文のみ返す
            if let range = text.range(of: "は") {
                let afterPrefix = String(text[text.index(after: range.upperBound)...])
                text = afterPrefix
            } else {
                episodeLogger.warning("structured_v1形式だが「は」が見つからない: person=\(self.personName, privacy: .public)")
            }
        }

        return text.trimmingCharacters(in: .whitespaces)
    }

    // periphery:ignore - Legacy compatibility method
    // 既存のgetDisplayTextメソッド（互換性のため）
    func getDisplayText(includePrefix: Bool = true) -> String {
        return getDisplayText(includePrefix: includePrefix, includeAgePhrase: true)
    }

    // MARK: - エピソード検証

    /// エピソードの妥当性を検証（リファクタリング済み）
    func isValid() -> Bool {
        guard validateBasicRequirements() else { return false }
        warnIfMissingJapaneseName()

        if containsTemplateContent() { return false }
        if containsOtherPersonContent() { return false }
        if isFictional && containsModernYearReference() { return false }
        if containsRealCreatorName() { return false }
        if containsRealEntityName() { return false }

        return true
    }

    // MARK: - 検証用プライベートメソッド

    /// 基本要件の検証（人物名・エピソード本文・文字数）
    private func validateBasicRequirements() -> Bool {
        guard !personName.isEmpty,
              !episode.isEmpty,
              episode.count >= 50 else {  // 最低50文字
            return false
        }
        return true
    }

    /// 日本語名が欠落している場合に警告を出力（無効にはしない）
    private func warnIfMissingJapaneseName() {
        if personNameJa == nil || personNameJa?.isEmpty == true {
            episodeLogger.warning("日本語名が欠落: person=\(self.personName, privacy: .public)")
        }
    }

    /// テンプレート的な内容が含まれているかチェック
    private func containsTemplateContent() -> Bool {
        let templatePhrases = [
            "1930年、結婚し、新しい家庭を築き始めた",
            "1930年、最初の主要作品を完成させ",
            "1930年、重要な研究成果を発表し",
            "この出来事は後の活動に大きな影響を与えることとなった"
        ]

        for phrase in templatePhrases where episode.contains(phrase) {
            episodeLogger.warning("テンプレート的内容を検出: person=\(self.personName, privacy: .public)")
            return true
        }
        return false
    }

    /// 別人のエピソードが混入しているかチェック
    private func containsOtherPersonContent() -> Bool {
        // 別人エピソード混入チェック用リスト
        // 選定基準: 歴史上著名な人物で、混同されやすい名前
        let otherFamousNames = [
            "アレクサンダー・グラハム・ベル", "ベル電話",
            "トーマス・エジソン", "エジソン",
            "アインシュタイン", "相対性理論",
            "ニュートン", "万有引力",
            "ダーウィン", "進化論",
            "チャーチル", "第二次世界大戦",
            "ナポレオン", "フランス皇帝",
            "ベートーヴェン", "第九",
            "モーツァルト", "魔笛"
        ]

        // 自分の名前は除外
        let ownNames = [personName, personNameJa].compactMap { $0 }

        for otherName in otherFamousNames where episode.contains(otherName) {
            // 自分の名前でない場合は無効
            var isOwnName = false
            for ownName in ownNames {
                if otherName.contains(ownName) || ownName.contains(otherName) {
                    isOwnName = true
                    break
                }
            }

            if !isOwnName {
                let name = self.personName
                episodeLogger.warning(
                    "別人の内容を検出: person=\(name, privacy: .public), found=\(otherName, privacy: .public)"
                )
                return true
            }
        }
        return false
    }

    /// 【架空キャラ用】現代年号（1900-2099年）が含まれているかチェック
    private func containsModernYearReference() -> Bool {
        guard isFictional else { return false }

        // 正規表現: 1900-2099年を検出（将来の年号にも対応）
        let yearPattern = #"(19\d{2}|20\d{2})年"#
        do {
            let regex = try NSRegularExpression(pattern: yearPattern, options: [])
            let range = NSRange(episode.startIndex..., in: episode)
            if regex.firstMatch(in: episode, options: [], range: range) != nil {
                episodeLogger.warning("架空キャラに現代年号混入: person=\(self.personName, privacy: .public)")
                return true
            }
        } catch {
            episodeLogger.error("年号検出正規表現コンパイル失敗: \(error.localizedDescription, privacy: .public)")
            // 安全側に倒す: チェックできない場合は無効として扱う
            return true
        }
        return false
    }

    /// 【架空キャラ用】現実のクリエイター名が含まれているかチェック
    private func containsRealCreatorName() -> Bool {
        guard isFictional else { return false }

        let realCreators = [
            "鳥山明", "宮本茂", "尾田栄一郎", "岸本斉史", "諫山創",
            "藤子不二雄", "手塚治虫", "宮崎駿", "庵野秀明", "新海誠"
        ]
        for creator in realCreators where episode.contains(creator) {
            episodeLogger.warning(
                "架空キャラに現実人物混入: person=\(self.personName, privacy: .public), creator=\(creator, privacy: .public)"
            )
            return true
        }
        return false
    }

    /// 【架空キャラ用】現実の企業・媒体名が含まれているかチェック
    private func containsRealEntityName() -> Bool {
        guard isFictional else { return false }

        let realEntities = [
            "週刊少年ジャンプ", "週刊少年マガジン", "バンダイナムコ",
            "任天堂", "スクウェア・エニックス", "集英社", "講談社"
        ]
        for entity in realEntities where episode.contains(entity) {
            episodeLogger.warning(
                "架空キャラに現実企業混入: person=\(self.personName, privacy: .public), entity=\(entity, privacy: .public)"
            )
            return true
        }
        return false
    }
}

// エピソード管理クラス
final class EpisodeManager: ObservableObject, @unchecked Sendable {
    static let shared = EpisodeManager()

    private let userDefaults = UserDefaults.standard

    // ★ View再構築対応: 現在表示中のエピソードを保持（タブ切り替え時もシングルトンで維持）
    @Published var displayedEpisode: Episode?
    @Published var displayedAge: Int = -1

    init() {
        // 古いキャッシュを検出して削除
        checkAndClearOldCache()
        // ★ 起動時にキャッシュからエピソードを復元
        restoreDisplayedEpisodeFromCache()
    }

    /// キャッシュから表示エピソードを復元（起動時・タブ切り替え対応）
    private func restoreDisplayedEpisodeFromCache() {
        if let cached = todayEpisode, !isNewDay() {
            displayedEpisode = cached
            displayedAge = userDefaults.integer(forKey: lastEpisodeAgeKey)
            #if DEBUG
            print("🔄 キャッシュから復元: \(cached.personName), age=\(displayedAge)")
            #endif
        }
    }

    // キャッシュキー
    private let viewedEpisodesKey = "viewedEpisodeIds"
    private let lastEpisodeDateKey = "lastEpisodeDate"
    private let dailyEpisodeKey = "dailyEpisode"
    private let cachedEpisodesKey = "cachedEpisodes"
    private let lastEpisodeAgeKey = "lastEpisodeAge"

    // 表示済みエピソードID
    private var viewedEpisodeIds: Set<String> {
        get {
            let array = userDefaults.stringArray(forKey: viewedEpisodesKey) ?? []
            return Set(array)
        }
        set {
            userDefaults.set(Array(newValue), forKey: viewedEpisodesKey)
        }
    }

    // 最後にエピソードを見た日付
    private var lastEpisodeDate: Date? {
        get {
            userDefaults.object(forKey: lastEpisodeDateKey) as? Date
        }
        set {
            userDefaults.set(newValue, forKey: lastEpisodeDateKey)
        }
    }

    // 今日のエピソード（キャッシュ）
    private var todayEpisode: Episode? {
        get {
            guard let data = userDefaults.data(forKey: dailyEpisodeKey) else { return nil }
            do {
                return try JSONDecoder().decode(Episode.self, from: data)
            } catch {
                episodeLogger.error("todayEpisode デコード失敗: \(error.localizedDescription, privacy: .public)")
                return nil
            }
        }
        set {
            guard let episode = newValue else {
                #if DEBUG
                print("💾 todayEpisode クリア")
                #endif
                userDefaults.removeObject(forKey: dailyEpisodeKey)
                return
            }
            do {
                let data = try JSONEncoder().encode(episode)
                userDefaults.set(data, forKey: dailyEpisodeKey)
                #if DEBUG
                print("💾 todayEpisode 保存成功: \(episode.personName), dataSize=\(data.count)")
                #endif
            } catch {
                episodeLogger.error("todayEpisode エンコード失敗: \(error.localizedDescription, privacy: .public)")
                userDefaults.removeObject(forKey: dailyEpisodeKey)
            }
        }
    }

    // オフライン用キャッシュ
    private var cachedEpisodes: [Episode] {
        get {
            guard let data = userDefaults.data(forKey: cachedEpisodesKey) else { return [] }
            do {
                return try JSONDecoder().decode([Episode].self, from: data)
            } catch {
                episodeLogger.error("cachedEpisodes デコード失敗: \(error.localizedDescription, privacy: .public)")
                return []
            }
        }
        set {
            do {
                let data = try JSONEncoder().encode(newValue)
                userDefaults.set(data, forKey: cachedEpisodesKey)
            } catch {
                episodeLogger.error("cachedEpisodes エンコード失敗: \(error.localizedDescription, privacy: .public)")
            }
        }
    }

    // MARK: - 0歳固定エピソード

    /// 0歳固定エピソード（全ユーザー共通の特別なメッセージ）
    private static let zeroAgeEpisode = Episode(
        id: "zero-age-special",
        personName: "すべての人",
        personNameJa: "すべての人",
        episode: "あなたと同じ0歳のとき、この世のすべての人は、" +
            "まだ言葉にならない無数の可能性を胸に抱いています。" +
            "小さな泣き声も、握りしめた指先も、「これから何にでもなれる」という合図。" +
            "何者かになる前の「まっさらな今」は、すでに尊くて、" +
            "これからの物語につながる確かなスタートです。",
        episodeAge: 0,
        episodeType: "universal",
        createdAt: nil,
        characterCount: nil,
        qualityScore: 100,
        tags: ["誕生", "可能性", "はじまり"],
        formatVersion: "fixed_v1",  // 固定エピソード用（プレフィックス処理対象外）
        personType: .real,
        workTitle: nil
    )

    // MARK: - 101歳以上固定エピソード

    /// 101歳以上のユーザーに表示する固定名言エピソード
    private static let wisdomEpisodeFor101Plus = Episode(
        id: "wisdom-episode-101-plus",
        personName: "人類の知恵",
        personNameJa: "人類の知恵",
        episode: """
あなたと同じ120歳のとき人類は年齢を"終わりの数字"ではなく"経験の器"として数えるようになっていた。
かつて若さだけが価値だと信じられた時代を越え、長く生きた人の言葉には、未来をほどく鍵が宿ると皆が知ったのだ。
「人生は、長さではなく深さで決まる」——その一句が、静かに世界の背筋を正した。
""",
        episodeAge: 120,
        episodeType: "wisdom",
        createdAt: nil,
        characterCount: nil,
        qualityScore: 100,
        tags: ["知恵", "人生", "長寿"],
        formatVersion: "fixed_v1",  // 固定エピソード用
        personType: .real,
        workTitle: nil
    )

    // MARK: - Public Methods

    /// 年齢が変更されたときキャッシュをクリア
    func clearCacheForAgeChange() {
        todayEpisode = nil
        displayedEpisode = nil
        displayedAge = -1
        userDefaults.removeObject(forKey: dailyEpisodeKey)
        userDefaults.removeObject(forKey: lastEpisodeAgeKey)
    }

    /// 今日のキャッシュが有効かどうかをチェック（View側で再取得判定用）
    func hasValidCacheForToday(for age: Int) -> Bool {
        // 0歳と101歳以上は常に固定エピソードが返されるので有効
        if age == 0 || age >= 101 {
            return true
        }

        // ★ 修正: todayEpisode（永続化）を信頼の源泉とする
        // displayedEpisode のチェックを削除（タブ切り替えで nil になるため不適切）
        guard !isNewDay() else {
            #if DEBUG
            print("📊 キャッシュ無効: 新しい日です")
            #endif
            return false
        }
        guard todayEpisode != nil else {
            #if DEBUG
            print("📊 キャッシュ無効: todayEpisode が nil")
            #endif
            return false
        }

        let lastAge = userDefaults.integer(forKey: lastEpisodeAgeKey)
        let isValid = lastAge == age

        #if DEBUG
        print("📊 キャッシュ確認: lastAge=\(lastAge), requestedAge=\(age), valid=\(isValid)")
        #endif

        return isValid
    }

    /// 今日のエピソードを取得（閲覧履歴として記録）
    func getDailyEpisode(for age: Int, completion: @escaping (Episode?) -> Void) {
        // 0歳は固定エピソードを返す（データベースにアクセスしない）
        // 固定エピソードのため閲覧履歴・キャッシュには追加しない
        if age == 0 {
            displayedEpisode = Self.zeroAgeEpisode
            displayedAge = age
            completion(Self.zeroAgeEpisode)
            return
        }

        // 101歳以上は固定名言エピソードを返す（データベースにアクセスしない）
        // 固定エピソードのため閲覧履歴・キャッシュには追加しない
        if age >= 101 {
            displayedEpisode = Self.wisdomEpisodeFor101Plus
            displayedAge = age
            completion(Self.wisdomEpisodeFor101Plus)
            return
        }

        // ★ 修正: todayEpisode（永続化）を信頼の源泉とする
        // 同じ日・同じ年齢なら todayEpisode を即座に返す（絶対に再取得しない）
        let lastAge = userDefaults.integer(forKey: lastEpisodeAgeKey)
        if !isNewDay() && lastAge == age {
            if let cached = todayEpisode {
                #if DEBUG
                print("✅ todayEpisode キャッシュから即座に返却: \(cached.personName)")
                #endif
                displayedEpisode = cached  // メモリにも復元
                displayedAge = age
                completion(cached)
                return  // ★ 絶対に再取得しない
            }
        }

        #if DEBUG
        print("🔄 新しいエピソードを取得: age=\(age), isNewDay=\(isNewDay()), lastAge=\(lastAge)")
        #endif

        // 新しいエピソードを取得（新しい日 or 年齢変更時のみ）
        fetchNewEpisode(for: age) { [weak self] episode in
            guard let self = self else { return }
            if let episode = episode {
                #if DEBUG
                print("💾 保存開始: \(episode.personName), age=\(age)")
                #endif

                self.todayEpisode = episode
                self.lastEpisodeDate = Date()
                self.userDefaults.set(age, forKey: self.lastEpisodeAgeKey)
                self.userDefaults.synchronize()  // 即座に永続化

                #if DEBUG
                // 保存直後に読み戻して確認
                let savedAge = self.userDefaults.integer(forKey: self.lastEpisodeAgeKey)
                let savedEpisode = self.todayEpisode
                print("💾 保存確認: savedAge=\(savedAge), savedEpisode=\(savedEpisode?.personName ?? "nil")")
                #endif

                self.markAsViewed(episode.id)
                self.addToCache(episode)
                self.displayedEpisode = episode
                self.displayedAge = age
            }
            completion(episode)
        }
    }

    /// 表示済みエピソードIDをクリーンアップ（1000件超過時に古い500件を削除）
    func cleanOldViewedEpisodes() {
        // 表示済みIDが1000件を超えたら古いものから削除
        if viewedEpisodeIds.count > 1000 {
            // 最初の500件を削除（簡易的な実装）
            let array = Array(viewedEpisodeIds)
            let newSet = Set(array.suffix(500))
            viewedEpisodeIds = newSet
        }
    }

    /// すべてのデータをリセット
    func resetAllData() {
        viewedEpisodeIds = []
        lastEpisodeDate = nil
        todayEpisode = nil
        cachedEpisodes = []
        displayedEpisode = nil
        displayedAge = -1
    }

    /// 新しい日かどうかをチェック（0時跨ぎ対応用）
    func shouldRefreshForNewDay() -> Bool {
        return isNewDay()
    }

    /// 古いキャッシュを検出して削除
    private func checkAndClearOldCache() {
        // 今日のエピソードをチェック
        if let episode = todayEpisode {
            // person_name_jaが空または"この人物"を含む場合はクリア
            if episode.personNameJa == nil ||
               episode.personNameJa?.isEmpty == true ||
               episode.episode.contains("この人物") {
                episodeLogger.warning("古いキャッシュを検出しました。クリアします。")
                resetAllData()
            }
        }

        // キャッシュされたエピソードもチェック
        for episode in cachedEpisodes {
            if episode.personNameJa == nil ||
               episode.personNameJa?.isEmpty == true ||
               episode.episode.contains("この人物") {
                episodeLogger.warning("古いキャッシュを検出しました。クリアします。")
                resetAllData()
                break
            }
        }
    }

    // MARK: - Private Methods

    /// 新しい日かどうかチェック
    private func isNewDay() -> Bool {
        guard let lastDate = lastEpisodeDate else { return true }

        // タイムゾーン巻き戻し対策: 未来の日付が記録されている場合は新しい日として扱わない
        if lastDate > Date() {
            return false
        }

        let calendar = Calendar.current
        let lastDay = calendar.dateComponents([.year, .month, .day], from: lastDate)
        let today = calendar.dateComponents([.year, .month, .day], from: Date())

        return lastDay.year != today.year || lastDay.month != today.month || lastDay.day != today.day
    }

    /// 新しいエピソードを取得（Supabaseのみ）
    private func fetchNewEpisode(for age: Int, completion: @escaping (Episode?) -> Void) {
        fetchNewEpisodeFromSupabase(for: age, completion: completion)
    }

    /// Supabaseから新しいエピソードを取得
    private func fetchNewEpisodeFromSupabase(for age: Int, completion: @escaping (Episode?) -> Void) {
        let excludeIds = viewedEpisodeIds  // キャプチャ用にコピー
        Task { [weak self] in
            do {
                var episode = try await SupabaseManager.shared.fetchEpisodeWithFallback(
                    targetAge: age,
                    excludeIds: excludeIds,
                    maxRange: 10
                )

                // ループリセット: 候補が枯渇した場合は消費済みリストをリセットして再取得
                if episode == nil && !excludeIds.isEmpty {
                    #if DEBUG
                    print("🔄 エピソード候補枯渇 - 消費済みリストをリセット")
                    #endif
                    await MainActor.run { [weak self] in
                        self?.viewedEpisodeIds = []
                    }
                    episode = try await SupabaseManager.shared.fetchEpisodeWithFallback(
                        targetAge: age,
                        excludeIds: [],
                        maxRange: 10
                    )
                }

                DispatchQueue.main.async {
                    #if DEBUG
                    if let fetched = episode {
                        print("✅ Supabase: エピソード取得成功 - \(fetched.personName)")
                    } else {
                        print("⚠️ Supabase: エピソードが見つかりませんでした")
                    }
                    #endif
                    completion(episode)
                }
            } catch {
                episodeLogger.error("Supabase取得エラー: \(error.localizedDescription, privacy: .public)")
                // エラー時はnilを返す（オフラインキャッシュがあれば上位で対応）
                DispatchQueue.main.async { [weak self] in
                    // オフラインキャッシュから取得を試みる
                    if let cachedEpisode = self?.getRandomCachedEpisode() {
                        episodeLogger.warning("キャッシュフォールバック使用")
                        completion(cachedEpisode)
                    } else {
                        completion(nil)
                    }
                }
            }
        }
    }

    /// エピソードIDを表示済みとしてマーク
    private func markAsViewed(_ episodeId: String) {
        var viewed = viewedEpisodeIds
        viewed.insert(episodeId)
        viewedEpisodeIds = viewed

        // 定期的にクリーンアップ
        if viewed.count % 100 == 0 {
            cleanOldViewedEpisodes()
        }
    }

    /// エピソードをキャッシュに追加
    private func addToCache(_ episode: Episode) {
        var cache = cachedEpisodes

        // 重複を避ける
        cache.removeAll { $0.id == episode.id }
        cache.append(episode)

        // キャッシュサイズを制限（最新10件）
        if cache.count > 10 {
            cache = Array(cache.suffix(10))
        }

        cachedEpisodes = cache
    }

    /// キャッシュからランダムにエピソードを取得
    private func getRandomCachedEpisode() -> Episode? {
        let cache = cachedEpisodes
        guard !cache.isEmpty else { return nil }

        // 有効なエピソードのみフィルタリング
        let validCache = cache.filter { $0.isValid() }
        guard !validCache.isEmpty else { return nil }

        let randomIndex = Int.random(in: 0..<validCache.count)
        return validCache[randomIndex]
    }
}
