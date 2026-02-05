//
//  CacheManagerTests.swift
//  FinalHourglassTests
//
//  CacheManager のユニットテスト
//  キャッシュ管理機能の正確性を検証
//

import XCTest
@testable import FinalHourglass

final class CacheManagerTests: XCTestCase {

    // MARK: - Setup / TearDown

    override func setUp() {
        super.setUp()
        // テスト前にキャッシュをクリア
        CacheManager.shared.clearAllEpisodeCache()
    }

    override func tearDown() {
        // テスト後にクリーンアップ
        CacheManager.shared.clearAllEpisodeCache()
        super.tearDown()
    }

    // MARK: - A. シングルトンテスト

    /// シングルトンインスタンスが常に同一であることを確認
    func testSharedInstance() {
        let instance1 = CacheManager.shared
        let instance2 = CacheManager.shared

        // 同一インスタンスであることを検証
        XCTAssertTrue(instance1 === instance2, "CacheManager.shared は常に同じインスタンスを返すべき")
    }

    // MARK: - B. キャッシュクリアテスト

    /// clearAllEpisodeCache() が全キーを削除することを確認
    func testClearAllEpisodeCacheRemovesAllKeys() {
        let userDefaults = UserDefaults.standard

        // テストデータを設定
        userDefaults.set(["EP-001", "EP-002"], forKey: "viewedEpisodeIds")
        userDefaults.set(Date(), forKey: "lastEpisodeDate")
        userDefaults.set(Data(), forKey: "dailyEpisode")
        userDefaults.set(Data(), forKey: "cachedEpisodes")
        userDefaults.synchronize()

        // クリア前の状態を確認
        XCTAssertNotNil(userDefaults.object(forKey: "viewedEpisodeIds"))
        XCTAssertNotNil(userDefaults.object(forKey: "lastEpisodeDate"))
        XCTAssertNotNil(userDefaults.object(forKey: "dailyEpisode"))
        XCTAssertNotNil(userDefaults.object(forKey: "cachedEpisodes"))

        // キャッシュをクリア
        CacheManager.shared.clearAllEpisodeCache()

        // クリア後の状態を確認
        XCTAssertNil(userDefaults.object(forKey: "viewedEpisodeIds"), "viewedEpisodeIds が削除されるべき")
        XCTAssertNil(userDefaults.object(forKey: "lastEpisodeDate"), "lastEpisodeDate が削除されるべき")
        XCTAssertNil(userDefaults.object(forKey: "dailyEpisode"), "dailyEpisode が削除されるべき")
        XCTAssertNil(userDefaults.object(forKey: "cachedEpisodes"), "cachedEpisodes が削除されるべき")
    }

    /// 空のキャッシュに対して clearAllEpisodeCache() を呼んでもクラッシュしないことを確認
    func testClearAllEpisodeCacheOnEmptyCache() {
        // setUp() で既にクリアされているので、再度クリアしてもエラーにならないことを確認
        CacheManager.shared.clearAllEpisodeCache()
        CacheManager.shared.clearAllEpisodeCache()

        // ここまで到達すればテスト成功（クラッシュしなかった）
        XCTAssertTrue(true, "空のキャッシュに対するクリアは安全に実行されるべき")
    }

    // MARK: - C. キャッシュ状態チェックテスト

    /// キャッシュが存在しない場合の checkCacheStatus() を確認
    func testCheckCacheStatusWithNoCache() {
        // setUp() で既にクリアされている
        let status = CacheManager.shared.checkCacheStatus()

        XCTAssertFalse(status.hasViewedIds, "viewedEpisodeIds は存在しないはず")
        XCTAssertFalse(status.hasLastDate, "lastEpisodeDate は存在しないはず")
        XCTAssertFalse(status.hasDailyEpisode, "dailyEpisode は存在しないはず")
        XCTAssertFalse(status.hasCachedEpisodes, "cachedEpisodes は存在しないはず")
    }

    /// viewedEpisodeIds が存在する場合の checkCacheStatus() を確認
    func testCheckCacheStatusWithViewedIds() {
        let userDefaults = UserDefaults.standard
        userDefaults.set(["EP-001", "EP-002", "EP-003"], forKey: "viewedEpisodeIds")
        userDefaults.synchronize()

        let status = CacheManager.shared.checkCacheStatus()

        XCTAssertTrue(status.hasViewedIds, "viewedEpisodeIds が存在するはず")
        XCTAssertFalse(status.hasLastDate, "lastEpisodeDate は存在しないはず")
        XCTAssertFalse(status.hasDailyEpisode, "dailyEpisode は存在しないはず")
        XCTAssertFalse(status.hasCachedEpisodes, "cachedEpisodes は存在しないはず")

        // description プロパティのテスト
        XCTAssertTrue(status.description.contains("閲覧済みID: あり"), "description に正しい状態が含まれるべき")
    }

    /// dailyEpisode が存在する場合の checkCacheStatus() を確認
    func testCheckCacheStatusWithDailyEpisode() throws {
        // テスト用エピソードを作成
        let episode = Episode(
            id: "EP-TEST-001",
            personName: "テスト太郎",
            personNameJa: "テスト太郎",
            episode: "あなたと同じ30歳のとき、テスト太郎はテストを実行していた。これは50文字以上のテストエピソードです。",
            episodeAge: 30,
            episodeType: "test",
            createdAt: nil,
            characterCount: 100,
            qualityScore: 90,
            tags: nil,
            formatVersion: nil,
            personType: .real,
            workTitle: nil
        )

        // エピソードをエンコードしてUserDefaultsに保存
        let data = try JSONEncoder().encode(episode)
        UserDefaults.standard.set(data, forKey: "dailyEpisode")
        UserDefaults.standard.synchronize()

        let status = CacheManager.shared.checkCacheStatus()

        XCTAssertFalse(status.hasViewedIds, "viewedEpisodeIds は存在しないはず")
        XCTAssertFalse(status.hasLastDate, "lastEpisodeDate は存在しないはず")
        XCTAssertTrue(status.hasDailyEpisode, "dailyEpisode が存在するはず")
        XCTAssertFalse(status.hasCachedEpisodes, "cachedEpisodes は存在しないはず")
    }

    // MARK: - D. 古いキャッシュ検出テスト

    /// personNameJa が nil の場合に hasOldCache() が true を返すことを確認
    func testHasOldCacheWithNullPersonNameJa() throws {
        // personNameJa が nil のエピソードを作成
        let episode = Episode(
            id: "EP-OLD-001",
            personName: "古いデータ太郎",
            personNameJa: nil,  // nil = 古いキャッシュ
            episode: "あなたと同じ25歳のとき、古いデータ太郎は何かをしていた。これは50文字以上のテストエピソードです。",
            episodeAge: 25,
            episodeType: "old",
            createdAt: nil,
            characterCount: 80,
            qualityScore: 70,
            tags: nil,
            formatVersion: nil,
            personType: .real,
            workTitle: nil
        )

        // エピソードをエンコードしてUserDefaultsに保存
        let data = try JSONEncoder().encode(episode)
        UserDefaults.standard.set(data, forKey: "dailyEpisode")
        UserDefaults.standard.synchronize()

        let hasOld = CacheManager.shared.hasOldCache()

        XCTAssertTrue(hasOld, "personNameJa が nil の場合は古いキャッシュとして検出されるべき")
    }

    /// 有効なキャッシュの場合に hasOldCache() が false を返すことを確認
    func testHasOldCacheWithValidCache() throws {
        // 有効なエピソードを作成（personNameJa が設定されており、「この人物」を含まない）
        let episode = Episode(
            id: "EP-VALID-001",
            personName: "有効データ太郎",
            personNameJa: "有効データ太郎",  // 有効な日本語名
            episode: "あなたと同じ35歳のとき、有効データ太郎は正常なテストを実行していた。これは50文字以上のテストエピソードです。",
            episodeAge: 35,
            episodeType: "valid",
            createdAt: nil,
            characterCount: 90,
            qualityScore: 95,
            tags: nil,
            formatVersion: nil,
            personType: .real,
            workTitle: nil
        )

        // エピソードをエンコードしてUserDefaultsに保存
        let data = try JSONEncoder().encode(episode)
        UserDefaults.standard.set(data, forKey: "dailyEpisode")
        UserDefaults.standard.synchronize()

        let hasOld = CacheManager.shared.hasOldCache()

        XCTAssertFalse(hasOld, "有効なキャッシュは古いキャッシュとして検出されないべき")
    }

    // MARK: - E. CacheStatus構造体テスト

    /// CacheStatus の description プロパティが正しくフォーマットされることを確認
    func testCacheStatusDescription() {
        // すべて存在する場合
        let allExists = CacheStatus(
            hasViewedIds: true,
            hasLastDate: true,
            hasDailyEpisode: true,
            hasCachedEpisodes: true
        )

        XCTAssertTrue(allExists.description.contains("閲覧済みID: あり"))
        XCTAssertTrue(allExists.description.contains("最終日付: あり"))
        XCTAssertTrue(allExists.description.contains("今日のエピソード: あり"))
        XCTAssertTrue(allExists.description.contains("キャッシュ済みエピソード: あり"))

        // すべて存在しない場合
        let noneExists = CacheStatus(
            hasViewedIds: false,
            hasLastDate: false,
            hasDailyEpisode: false,
            hasCachedEpisodes: false
        )

        XCTAssertTrue(noneExists.description.contains("閲覧済みID: なし"))
        XCTAssertTrue(noneExists.description.contains("最終日付: なし"))
        XCTAssertTrue(noneExists.description.contains("今日のエピソード: なし"))
        XCTAssertTrue(noneExists.description.contains("キャッシュ済みエピソード: なし"))
    }
}
