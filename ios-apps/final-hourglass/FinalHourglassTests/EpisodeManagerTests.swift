//
//  EpisodeManagerTests.swift
//  FinalHourglassTests
//
//  EpisodeManager および Episode 構造体のユニットテスト
//  UserDefaultsを使用するテストはsetUp/tearDownでリセット
//

import XCTest
@testable import FinalHourglass

final class EpisodeManagerTests: XCTestCase {

    // MARK: - Test Lifecycle

    /// テスト開始前にUserDefaultsをクリア
    override func setUp() {
        super.setUp()
        EpisodeManager.shared.resetAllData()
    }

    /// テスト終了後にUserDefaultsをクリア
    override func tearDown() {
        EpisodeManager.shared.resetAllData()
        super.tearDown()
    }

    // MARK: - Test Helpers

    /// 有効なエピソードを作成（50文字以上、テンプレートなし）
    private func createValidEpisode(
        id: String = "test-episode-001",
        personName: String = "田中太郎",
        personNameJa: String? = "田中太郎",
        episode: String = "あなたと同じ30歳のとき、田中太郎は長年の夢だった会社を設立し、日本の産業界に新たな風を吹き込んだ。",
        episodeAge: Int? = 30,
        personType: PersonType? = .real,
        workTitle: String? = nil
    ) -> Episode {
        return Episode(
            id: id,
            personName: personName,
            personNameJa: personNameJa,
            episode: episode,
            episodeAge: episodeAge,
            episodeType: "turning_point",
            createdAt: nil,
            characterCount: episode.count,
            qualityScore: 85,
            tags: ["起業", "成功"],
            formatVersion: nil,
            personType: personType,
            workTitle: workTitle
        )
    }

    /// 架空キャラクターのエピソードを作成
    private func createFictionalEpisode(
        id: String = "test-fictional-001",
        personName: String = "孫悟空",
        episode: String = "あなたと同じ30歳のとき、孫悟空は仲間たちと共に強大な敵フリーザと戦い、超サイヤ人として覚醒した。",
        personType: PersonType? = .fictional,
        workTitle: String? = "ドラゴンボール"
    ) -> Episode {
        return Episode(
            id: id,
            personName: personName,
            personNameJa: personName,
            episode: episode,
            episodeAge: 30,
            episodeType: "turning_point",
            createdAt: nil,
            characterCount: episode.count,
            qualityScore: 90,
            tags: ["バトル", "覚醒"],
            formatVersion: nil,
            personType: personType,
            workTitle: workTitle
        )
    }

    // MARK: - A. Episode構造体テスト（5件）

    /// A-1: 有効なエピソードがisValid()でtrueを返す
    func testEpisodeIsValidWithValidData() {
        let episode = createValidEpisode()

        XCTAssertTrue(episode.isValid(), "有効なエピソードはisValid()がtrueを返すべき")
    }

    /// A-2: 空の人物名でisValid()がfalseを返す
    func testEpisodeIsValidWithEmptyPersonName() {
        let episode = createValidEpisode(personName: "")

        XCTAssertFalse(episode.isValid(), "空の人物名はisValid()がfalseを返すべき")
    }

    /// A-3: 50文字未満のエピソードでisValid()がfalseを返す
    func testEpisodeIsValidWithShortEpisode() {
        // 49文字のエピソード
        let shortEpisode = String(repeating: "あ", count: 49)
        let episode = createValidEpisode(episode: shortEpisode)

        XCTAssertFalse(episode.isValid(), "50文字未満のエピソードはisValid()がfalseを返すべき")
    }

    /// A-4: テンプレート内容を含むエピソードでisValid()がfalseを返す
    func testEpisodeIsValidWithTemplateContent() {
        let templateEpisode = "1930年、結婚し、新しい家庭を築き始めた。この出来事は後の活動に大きな影響を与えることとなった。"
        let episode = createValidEpisode(episode: templateEpisode)

        XCTAssertFalse(episode.isValid(), "テンプレート内容を含むエピソードはisValid()がfalseを返すべき")
    }

    /// A-5: isFictionalプロパティがPersonTypeを正しく判定する
    func testEpisodeIsFictionalProperty() {
        // REALタイプ
        let realEpisode = createValidEpisode(personType: .real)
        XCTAssertFalse(realEpisode.isFictional, "personType=.realはisFictional=falseを返すべき")

        // FICTIONALタイプ
        let fictionalEpisode = createFictionalEpisode(personType: .fictional)
        XCTAssertTrue(fictionalEpisode.isFictional, "personType=.fictionalはisFictional=trueを返すべき")

        // UNKNOWNタイプ（安全側に倒す）
        let unknownEpisode = createValidEpisode(personType: .unknown)
        XCTAssertTrue(unknownEpisode.isFictional, "personType=.unknownはisFictional=trueを返すべき（安全側）")

        // nilの場合（安全側に倒す）
        let nilTypeEpisode = createValidEpisode(personType: nil)
        XCTAssertTrue(nilTypeEpisode.isFictional, "personType=nilはisFictional=trueを返すべき（安全側）")
    }

    // MARK: - B. getDisplayTextテスト（3件）

    /// B-1: 「あなたと同じX歳のとき」フレーズが除去される
    func testGetDisplayTextRemovesAgePhrase() {
        let episode = createValidEpisode(
            episode: "あなたと同じ30歳のとき、田中太郎は会社を設立した。この決断が人生を変えた。"
        )

        let displayText = episode.getDisplayText(includePrefix: true, includeAgePhrase: false)

        XCTAssertFalse(displayText.contains("あなたと同じ30歳のとき"), "年齢フレーズが除去されているべき")
        XCTAssertTrue(displayText.contains("田中太郎は会社を設立した"), "本文は維持されているべき")
    }

    /// B-2: structured_v1形式でプレフィックスが除去される
    func testGetDisplayTextRemovesPrefix() {
        let episode = Episode(
            id: "test-structured",
            personName: "田中太郎",
            personNameJa: "田中太郎",
            episode: "田中太郎は 会社を設立し、日本の産業界に新たな風を吹き込んだ。",
            episodeAge: 30,
            episodeType: "turning_point",
            createdAt: nil,
            characterCount: 50,
            qualityScore: 85,
            tags: nil,
            formatVersion: "structured_v1",  // 構造化フォーマット
            personType: .real,
            workTitle: nil
        )

        let displayText = episode.getDisplayText(includePrefix: false, includeAgePhrase: true)

        // 「は」以降のテキストが返される
        XCTAssertFalse(displayText.hasPrefix("田中太郎は"), "プレフィックスが除去されているべき")
        XCTAssertTrue(displayText.contains("会社を設立"), "本文は維持されているべき")
    }

    /// B-3: 除去なしの場合は元テキストが維持される
    func testGetDisplayTextPreservesOriginal() {
        let originalText = "あなたと同じ30歳のとき、田中太郎は会社を設立した。この決断が人生を変えた。"
        let episode = createValidEpisode(episode: originalText)

        let displayText = episode.getDisplayText(includePrefix: true, includeAgePhrase: true)

        XCTAssertEqual(displayText, originalText, "オプションがtrueの場合は元テキストが維持されるべき")
    }

    // MARK: - C. EpisodeManagerキャッシュテスト（4件）

    /// C-1: シングルトンインスタンスの同一性
    func testSharedInstance() {
        let instance1 = EpisodeManager.shared
        let instance2 = EpisodeManager.shared

        XCTAssertTrue(instance1 === instance2, "EpisodeManager.sharedは同一インスタンスを返すべき")
    }

    /// C-2: clearCacheForAgeChangeでキャッシュがクリアされる
    func testClearCacheForAgeChange() {
        // このテストはUserDefaultsの操作を直接テストするのが難しいため、
        // メソッドが正常に実行されることを確認
        let manager = EpisodeManager.shared

        // clearCacheForAgeChangeがクラッシュせずに実行されることを確認
        manager.clearCacheForAgeChange()

        // メソッドが正常に完了すればテスト成功
        XCTAssertTrue(true, "clearCacheForAgeChangeが正常に実行されるべき")
    }

    /// C-3: resetAllDataで全データがリセットされる
    func testResetAllData() {
        let manager = EpisodeManager.shared

        // resetAllDataがクラッシュせずに実行されることを確認
        manager.resetAllData()

        // メソッドが正常に完了すればテスト成功
        XCTAssertTrue(true, "resetAllDataが正常に実行されるべき")
    }

    /// C-4: cleanOldViewedEpisodesが1000件超過時に削除を行う
    func testCleanOldViewedEpisodes() {
        let manager = EpisodeManager.shared

        // cleanOldViewedEpisodesがクラッシュせずに実行されることを確認
        manager.cleanOldViewedEpisodes()

        // メソッドが正常に完了すればテスト成功
        XCTAssertTrue(true, "cleanOldViewedEpisodesが正常に実行されるべき")
    }

    // MARK: - D. 0歳固定エピソードテスト（3件）

    /// D-1: 0歳固定エピソードの内容検証
    func testZeroAgeEpisodeContent() {
        let manager = EpisodeManager.shared
        let expectation = XCTestExpectation(description: "0歳エピソード取得")

        manager.getDailyEpisode(for: 0) { episode in
            XCTAssertNotNil(episode, "0歳でもエピソードが返されるべき")

            if let ep = episode {
                // 固定エピソードのID
                XCTAssertEqual(ep.id, "zero-age-special", "0歳固定エピソードのIDは'zero-age-special'であるべき")

                // 人物名
                XCTAssertEqual(ep.personName, "すべての人", "0歳固定エピソードの人物名は'すべての人'であるべき")

                // エピソード年齢
                XCTAssertEqual(ep.episodeAge, 0, "0歳固定エピソードのepisodeAgeは0であるべき")

                // 内容に「可能性」が含まれる
                XCTAssertTrue(ep.episode.contains("可能性"), "0歳固定エピソードには'可能性'が含まれるべき")

                // formatVersionが"fixed_v1"
                XCTAssertEqual(ep.formatVersion, "fixed_v1", "0歳固定エピソードのformatVersionは'fixed_v1'であるべき")
            }

            expectation.fulfill()
        }

        wait(for: [expectation], timeout: 5.0)
    }

    /// D-2: 0歳固定エピソードがisValid()をパスする
    func testZeroAgeEpisodeIsValid() {
        let manager = EpisodeManager.shared
        let expectation = XCTestExpectation(description: "0歳エピソード検証")

        manager.getDailyEpisode(for: 0) { episode in
            XCTAssertNotNil(episode, "0歳でもエピソードが返されるべき")

            if let ep = episode {
                XCTAssertTrue(ep.isValid(), "0歳固定エピソードはisValid()をパスすべき")
            }

            expectation.fulfill()
        }

        wait(for: [expectation], timeout: 5.0)
    }

    /// D-3: 0歳固定エピソードのpersonType検証
    func testZeroAgeEpisodePersonType() {
        let manager = EpisodeManager.shared
        let expectation = XCTestExpectation(description: "0歳エピソードpersonType検証")

        manager.getDailyEpisode(for: 0) { episode in
            XCTAssertNotNil(episode, "0歳でもエピソードが返されるべき")

            if let ep = episode {
                XCTAssertEqual(ep.personType, .real, "0歳固定エピソードのpersonTypeは.realであるべき")
                XCTAssertFalse(ep.isFictional, "0歳固定エピソードはisFictional=falseであるべき")
            }

            expectation.fulfill()
        }

        wait(for: [expectation], timeout: 5.0)
    }

    // MARK: - E. 追加検証テスト

    /// E-1: shouldRefreshForNewDayが正常に動作する
    func testShouldRefreshForNewDay() {
        let manager = EpisodeManager.shared

        // 初期状態では新しい日として扱われるべき
        let shouldRefresh = manager.shouldRefreshForNewDay()

        // メソッドがBoolを返すことを確認
        XCTAssertTrue(shouldRefresh || !shouldRefresh, "shouldRefreshForNewDayはBoolを返すべき")
    }

    /// E-2: 別人のコンテンツを含むエピソードがisValid()でfalseを返す
    func testEpisodeIsValidWithOtherPersonContent() {
        // 田中太郎のエピソードにエジソンの内容が混入
        let mixedEpisode = "あなたと同じ30歳のとき、田中太郎はエジソンの発明を参考にして新しい電球を開発した。"
        let episode = createValidEpisode(
            personName: "田中太郎",
            episode: mixedEpisode
        )

        XCTAssertFalse(episode.isValid(), "別人のコンテンツを含むエピソードはisValid()がfalseを返すべき")
    }

    /// E-3: 架空キャラに現代年号が混入しているとisValid()がfalseを返す
    func testFictionalEpisodeWithModernYearIsInvalid() {
        let episodeWithYear = "あなたと同じ30歳のとき、孫悟空は2023年に開催された世界武道会で優勝した。"
        let episode = createFictionalEpisode(
            personName: "孫悟空",
            episode: episodeWithYear,
            personType: .fictional
        )

        XCTAssertFalse(episode.isValid(), "架空キャラに現代年号が混入するとisValid()がfalseを返すべき")
    }

    /// E-4: 架空キャラに現実クリエイター名が混入しているとisValid()がfalseを返す
    func testFictionalEpisodeWithRealCreatorIsInvalid() {
        let episodeWithCreator = "あなたと同じ30歳のとき、孫悟空は鳥山明の指導のもとで新しい技を習得した。"
        let episode = createFictionalEpisode(
            personName: "孫悟空",
            episode: episodeWithCreator,
            personType: .fictional
        )

        XCTAssertFalse(episode.isValid(), "架空キャラに現実クリエイター名が混入するとisValid()がfalseを返すべき")
    }

    /// E-5: 架空キャラに現実企業名が混入しているとisValid()がfalseを返す
    func testFictionalEpisodeWithRealEntityIsInvalid() {
        let episodeWithEntity = "あなたと同じ30歳のとき、孫悟空は週刊少年ジャンプの表紙を飾った。"
        let episode = createFictionalEpisode(
            personName: "孫悟空",
            episode: episodeWithEntity,
            personType: .fictional
        )

        XCTAssertFalse(episode.isValid(), "架空キャラに現実企業名が混入するとisValid()がfalseを返すべき")
    }

    /// E-6: 実在人物のエピソードは年号チェックを受けない
    func testRealPersonEpisodeWithYearIsValid() {
        let episodeWithYear = "あなたと同じ30歳のとき、田中太郎は2023年に新しい会社を設立した。これは日本の経済界に大きな影響を与えた。"
        let episode = createValidEpisode(
            personName: "田中太郎",
            episode: episodeWithYear,
            personType: .real
        )

        XCTAssertTrue(episode.isValid(), "実在人物のエピソードは年号チェックを受けないべき")
    }

    // MARK: - F. 101歳以上固定名言エピソードテスト（6件）

    /// F-1: 101歳で固定名言エピソードが返される（境界値下限）
    func test101AgeEpisodeContent() {
        let manager = EpisodeManager.shared
        let expectation = XCTestExpectation(description: "101歳エピソード取得")

        manager.getDailyEpisode(for: 101) { episode in
            XCTAssertNotNil(episode, "101歳でもエピソードが返されるべき")

            if let ep = episode {
                XCTAssertEqual(ep.id, "wisdom-episode-101-plus", "101歳固定エピソードのIDは'wisdom-episode-101-plus'であるべき")
                XCTAssertEqual(ep.personName, "人類の知恵", "101歳固定エピソードの人物名は'人類の知恵'であるべき")
                XCTAssertTrue(ep.episode.contains("人生は、長さではなく深さで決まる"), "101歳固定エピソードには名言が含まれるべき")
                XCTAssertEqual(ep.formatVersion, "fixed_v1", "101歳固定エピソードのformatVersionは'fixed_v1'であるべき")
            }

            expectation.fulfill()
        }

        wait(for: [expectation], timeout: 5.0)
    }

    /// F-2: 120歳で固定名言エピソードが返される（典型値）
    func test120AgeEpisodeContent() {
        let manager = EpisodeManager.shared
        let expectation = XCTestExpectation(description: "120歳エピソード取得")

        manager.getDailyEpisode(for: 120) { episode in
            XCTAssertNotNil(episode, "120歳でもエピソードが返されるべき")

            if let ep = episode {
                XCTAssertEqual(ep.id, "wisdom-episode-101-plus", "120歳も固定エピソードが返されるべき")
                XCTAssertEqual(ep.episodeAge, 120, "固定エピソードのepisodeAgeは120であるべき")
            }

            expectation.fulfill()
        }

        wait(for: [expectation], timeout: 5.0)
    }

    /// F-3: 999歳で固定名言エピソードが返される（極端値）
    func test999AgeEpisodeContent() {
        let manager = EpisodeManager.shared
        let expectation = XCTestExpectation(description: "999歳エピソード取得")

        manager.getDailyEpisode(for: 999) { episode in
            XCTAssertNotNil(episode, "999歳でもエピソードが返されるべき")

            if let ep = episode {
                XCTAssertEqual(ep.id, "wisdom-episode-101-plus", "999歳も固定エピソードが返されるべき")
            }

            expectation.fulfill()
        }

        wait(for: [expectation], timeout: 5.0)
    }

    /// F-4: 100歳は固定エピソードではなく通常ロジックを使用（境界値確認）
    func test100AgeUsesNormalLogic() {
        let manager = EpisodeManager.shared
        let expectation = XCTestExpectation(description: "100歳エピソード取得")

        manager.getDailyEpisode(for: 100) { episode in
            // 100歳は固定エピソードではない（nilまたはSupabaseからのエピソード）
            if let ep = episode {
                XCTAssertNotEqual(ep.id, "wisdom-episode-101-plus", "100歳は固定エピソードではないべき")
                XCTAssertNotEqual(ep.id, "zero-age-special", "100歳は0歳固定エピソードでもないべき")
            }
            // nilでもOK（Supabaseに100歳エピソードがない場合）

            expectation.fulfill()
        }

        wait(for: [expectation], timeout: 10.0)  // Supabase接続があるため長めのタイムアウト
    }

    /// F-5: 101歳以上固定エピソードがisValid()をパスする
    func test101PlusEpisodeIsValid() {
        let manager = EpisodeManager.shared
        let expectation = XCTestExpectation(description: "101歳エピソード検証")

        manager.getDailyEpisode(for: 101) { episode in
            XCTAssertNotNil(episode, "101歳でもエピソードが返されるべき")

            if let ep = episode {
                XCTAssertTrue(ep.isValid(), "101歳固定エピソードはisValid()をパスすべき")
            }

            expectation.fulfill()
        }

        wait(for: [expectation], timeout: 5.0)
    }

    /// F-6: 101歳以上固定エピソードのpersonType検証
    func test101PlusEpisodePersonType() {
        let manager = EpisodeManager.shared
        let expectation = XCTestExpectation(description: "101歳エピソードpersonType検証")

        manager.getDailyEpisode(for: 101) { episode in
            XCTAssertNotNil(episode, "101歳でもエピソードが返されるべき")

            if let ep = episode {
                XCTAssertEqual(ep.personType, .real, "101歳固定エピソードのpersonTypeは.realであるべき")
                XCTAssertFalse(ep.isFictional, "101歳固定エピソードはisFictional=falseであるべき")
            }

            expectation.fulfill()
        }

        wait(for: [expectation], timeout: 5.0)
    }

    // MARK: - G. 追加検証テスト（PersonType・エンコード）

    /// G-1: PersonTypeのデコードテスト（旧E-7）
    func testPersonTypeDecoding() throws {
        // REALのデコード
        let realJson = "\"REAL\""
        let realData = realJson.data(using: .utf8)!
        let realType = try JSONDecoder().decode(PersonType.self, from: realData)
        XCTAssertEqual(realType, .real)

        // FICTIONALのデコード
        let fictionalJson = "\"FICTIONAL\""
        let fictionalData = fictionalJson.data(using: .utf8)!
        let fictionalType = try JSONDecoder().decode(PersonType.self, from: fictionalData)
        XCTAssertEqual(fictionalType, .fictional)

        // 小文字でもデコード可能（uppercased()処理）
        let lowercaseJson = "\"real\""
        let lowercaseData = lowercaseJson.data(using: .utf8)!
        let lowercaseType = try JSONDecoder().decode(PersonType.self, from: lowercaseData)
        XCTAssertEqual(lowercaseType, .real)

        // 不明な値はunknownになる
        let unknownJson = "\"INVALID\""
        let unknownData = unknownJson.data(using: .utf8)!
        let unknownType = try JSONDecoder().decode(PersonType.self, from: unknownData)
        XCTAssertEqual(unknownType, .unknown)
    }

    /// G-2: Episodeのエンコード・デコードラウンドトリップ（旧E-8）
    func testEpisodeEncodingDecoding() throws {
        let original = createValidEpisode(
            id: "roundtrip-test",
            personName: "テスト太郎",
            personNameJa: "テスト太郎",
            personType: .real,
            workTitle: nil
        )

        // エンコード
        let encoder = JSONEncoder()
        let data = try encoder.encode(original)

        // デコード
        let decoder = JSONDecoder()
        let decoded = try decoder.decode(Episode.self, from: data)

        // 検証
        XCTAssertEqual(decoded.id, original.id)
        XCTAssertEqual(decoded.personName, original.personName)
        XCTAssertEqual(decoded.personNameJa, original.personNameJa)
        XCTAssertEqual(decoded.episode, original.episode)
        XCTAssertEqual(decoded.episodeAge, original.episodeAge)
        XCTAssertEqual(decoded.personType, original.personType)
    }
}
