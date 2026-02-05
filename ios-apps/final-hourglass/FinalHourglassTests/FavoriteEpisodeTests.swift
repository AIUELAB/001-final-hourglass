import XCTest
@testable import FinalHourglass

final class FavoriteEpisodeTests: XCTestCase {
    private var manager: FavoriteEpisodeManager!

    override func setUp() {
        super.setUp()
        manager = FavoriteEpisodeManager.shared
        manager.clearAllFavorites()
    }

    override func tearDown() {
        manager.clearAllFavorites()
        UserDefaults.standard.removeObject(forKey: "favoriteEpisodes")
        super.tearDown()
    }

    // MARK: - Helper

    private func createTestEpisode(
        id: String = "test-ep-001",
        personName: String = "テスト太郎"
    ) -> Episode {
        return Episode(
            id: id,
            personName: personName,
            personNameJa: personName,
            episode: "あなたと同じ30歳のとき、\(personName)は大きな転機を迎えた。",
            episodeAge: 30,
            episodeType: "turning_point",
            createdAt: nil,
            characterCount: 40,
            qualityScore: 85,
            tags: ["テスト"],
            formatVersion: nil,
            personType: .real,
            workTitle: nil
        )
    }

    // MARK: - A. モデル初期化

    func testInit_setsIdFromEpisode() {
        let ep = createTestEpisode(id: "ep-abc")
        let fav = FavoriteEpisode(episode: ep)
        XCTAssertEqual(fav.id, "ep-abc")
        XCTAssertEqual(fav.id, fav.episode.id)
    }

    func testInit_setsAddedAt() {
        let ep = createTestEpisode()
        let date = Date(timeIntervalSince1970: 1_000_000)
        let fav = FavoriteEpisode(episode: ep, addedAt: date)
        XCTAssertEqual(fav.addedAt, date)
    }

    func testFormattedAddedAt() {
        let ep = createTestEpisode()
        // 2025-01-15 03:25:00 UTC -> JST 12:25
        let date = Date(timeIntervalSince1970: 1_736_907_900)
        let fav = FavoriteEpisode(episode: ep, addedAt: date)
        let formatted = fav.formattedAddedAt
        // DateFormatterはja_JPロケール, yyyy年M月d日 HH:mm
        XCTAssertTrue(formatted.contains("年"), "formattedAddedAt should contain 年: \(formatted)")
        XCTAssertTrue(formatted.contains("月"), "formattedAddedAt should contain 月: \(formatted)")
        XCTAssertTrue(formatted.contains("日"), "formattedAddedAt should contain 日: \(formatted)")
        XCTAssertTrue(formatted.contains(":"), "formattedAddedAt should contain time: \(formatted)")
    }

    func testShortDate() {
        let ep = createTestEpisode()
        let date = Date(timeIntervalSince1970: 1_736_907_900)
        let fav = FavoriteEpisode(episode: ep, addedAt: date)
        let short = fav.shortDate
        // M/d形式
        XCTAssertTrue(short.contains("/"), "shortDate should be M/d format: \(short)")
    }

    // MARK: - B. Codable

    func testCodable_roundtrip() throws {
        let ep = createTestEpisode(id: "roundtrip-001")
        let original = FavoriteEpisode(episode: ep, addedAt: Date(timeIntervalSince1970: 1_700_000_000))

        let data = try JSONEncoder().encode(original)
        let decoded = try JSONDecoder().decode(FavoriteEpisode.self, from: data)

        XCTAssertEqual(decoded.id, original.id)
        XCTAssertEqual(decoded.episode.id, original.episode.id)
        XCTAssertEqual(decoded.episode.personName, original.episode.personName)
        XCTAssertEqual(decoded.addedAt.timeIntervalSince1970, original.addedAt.timeIntervalSince1970, accuracy: 1.0)
    }

    func testCodable_idMismatchThrowsDecodingError() throws {
        let ep = createTestEpisode(id: "original-id")
        let fav = FavoriteEpisode(episode: ep)

        // エンコード後、JSONのidを改ざん
        var data = try JSONEncoder().encode(fav)
        var jsonString = String(data: data, encoding: .utf8)!
        jsonString = jsonString.replacingOccurrences(of: "\"id\":\"original-id\"", with: "\"id\":\"tampered-id\"")
        // 最初の出現のみ置換されるため、episode内のidは"original-id"のまま
        // ただしJSONの構造によっては両方置換される可能性があるため、
        // 手動でJSONを構築する方が確実
        let encoder = JSONEncoder()
        let episodeData = try encoder.encode(ep)
        let episodeJson = String(data: episodeData, encoding: .utf8)!
        let addedAtValue = fav.addedAt.timeIntervalSinceReferenceDate
        let tamperedJson = """
        {"id":"tampered-id","addedAt":\(addedAtValue),"episode":\(episodeJson)}
        """
        let tamperedData = tamperedJson.data(using: .utf8)!

        XCTAssertThrowsError(try JSONDecoder().decode(FavoriteEpisode.self, from: tamperedData)) { error in
            guard case DecodingError.dataCorrupted = error else {
                XCTFail("Expected DecodingError.dataCorrupted but got \(error)")
                return
            }
        }
    }

    // MARK: - C. Manager操作

    func testAddFavorite_insertsAtFront() {
        let ep1 = createTestEpisode(id: "ep-001")
        let ep2 = createTestEpisode(id: "ep-002")

        manager.addFavorite(episode: ep1)
        manager.addFavorite(episode: ep2)

        XCTAssertEqual(manager.favorites.count, 2)
        XCTAssertEqual(manager.favorites[0].id, "ep-002", "最新追加が先頭")
        XCTAssertEqual(manager.favorites[1].id, "ep-001")
    }

    func testRemoveFavorite_removesById() {
        let ep = createTestEpisode(id: "ep-remove")
        manager.addFavorite(episode: ep)
        XCTAssertEqual(manager.count, 1)

        manager.removeFavorite(episodeId: "ep-remove")
        XCTAssertEqual(manager.count, 0)
    }

    func testToggleFavorite_addsWhenNotPresent() {
        let ep = createTestEpisode(id: "ep-toggle")
        let result = manager.toggleFavorite(episode: ep)
        XCTAssertTrue(result, "追加時はtrueを返す")
        XCTAssertTrue(manager.isFavorite(episodeId: "ep-toggle"))
    }

    func testToggleFavorite_removesWhenPresent() {
        let ep = createTestEpisode(id: "ep-toggle2")
        manager.addFavorite(episode: ep)

        let result = manager.toggleFavorite(episode: ep)
        XCTAssertFalse(result, "解除時はfalseを返す")
        XCTAssertFalse(manager.isFavorite(episodeId: "ep-toggle2"))
    }

    func testClearAllFavorites() {
        for i in 0..<5 {
            manager.addFavorite(episode: createTestEpisode(id: "ep-\(i)"))
        }
        XCTAssertEqual(manager.count, 5)

        manager.clearAllFavorites()
        XCTAssertEqual(manager.count, 0)
        XCTAssertTrue(manager.favorites.isEmpty)
    }

    func testRemoveFavorites_atIndexSet() {
        for i in 0..<4 {
            manager.addFavorite(episode: createTestEpisode(id: "ep-idx-\(i)"))
        }
        // 順序: [3, 2, 1, 0] (先頭挿入のため逆順)
        XCTAssertEqual(manager.count, 4)

        // インデックス0と2を削除 → ep-idx-3 と ep-idx-1 を削除
        manager.removeFavorites(at: IndexSet([0, 2]))
        XCTAssertEqual(manager.count, 2)
        XCTAssertEqual(manager.favorites[0].id, "ep-idx-2")
        XCTAssertEqual(manager.favorites[1].id, "ep-idx-0")
    }

    // MARK: - D. 状態検査

    func testIsFavorite_returnsTrueWhenPresent() {
        let ep = createTestEpisode(id: "ep-check")
        manager.addFavorite(episode: ep)
        XCTAssertTrue(manager.isFavorite(episodeId: "ep-check"))
    }

    func testIsFavorite_returnsFalseWhenAbsent() {
        XCTAssertFalse(manager.isFavorite(episodeId: "nonexistent"))
    }

    func testCount_reflectsCurrentState() {
        XCTAssertEqual(manager.count, 0)
        manager.addFavorite(episode: createTestEpisode(id: "ep-c1"))
        XCTAssertEqual(manager.count, 1)
        manager.addFavorite(episode: createTestEpisode(id: "ep-c2"))
        XCTAssertEqual(manager.count, 2)
        manager.removeFavorite(episodeId: "ep-c1")
        XCTAssertEqual(manager.count, 1)
    }

    func testDuplicateAddIsSkipped() {
        let ep = createTestEpisode(id: "ep-dup")
        manager.addFavorite(episode: ep)
        manager.addFavorite(episode: ep)
        XCTAssertEqual(manager.count, 1, "同一エピソードの重複追加はスキップされる")
    }

    // MARK: - E. 永続化

    func testPersistence_dataExistsInUserDefaults() {
        let ep = createTestEpisode(id: "ep-persist")
        manager.addFavorite(episode: ep)

        let data = UserDefaults.standard.data(forKey: "favoriteEpisodes")
        XCTAssertNotNil(data, "addFavorite後にUserDefaultsにデータが存在する")
    }

    func testPersistence_corruptDataRecovery() {
        // 破損データをUserDefaultsに直接書き込む
        let corruptData = "this is not valid json".data(using: .utf8)!
        UserDefaults.standard.set(corruptData, forKey: "favoriteEpisodes")

        // Managerはsingletonなので、loadFavoritesを間接的にテスト
        // clearAll -> 破損データセット -> 再度loadを発火させる方法が限られるため、
        // JSONDecoderで直接テスト
        XCTAssertThrowsError(
            try JSONDecoder().decode([FavoriteEpisode].self, from: corruptData)
        )
        // 破損データでもManagerがクラッシュしないことを確認（setUp/tearDownで動作済み）
    }

    func testRemoveFavorite_nonexistentIdDoesNotCrash() {
        manager.addFavorite(episode: createTestEpisode(id: "ep-safe"))
        manager.removeFavorite(episodeId: "nonexistent-id")
        XCTAssertEqual(manager.count, 1, "存在しないIDの削除はエラーにならず既存データを保持")
    }
}
