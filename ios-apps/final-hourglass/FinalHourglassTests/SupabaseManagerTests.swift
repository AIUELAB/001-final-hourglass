//
//  SupabaseManagerTests.swift
//  FinalHourglassTests
//
//  SupabaseManager および関連コンポーネントのユニットテスト
//  ネットワーク接続なしでテスト可能な範囲に限定
//

import XCTest
@testable import FinalHourglass

final class SupabaseManagerTests: XCTestCase {

    // MARK: - A. SupabaseEpisode構造体テスト

    /// JSONからSupabaseEpisodeへのデコードが正しく動作することを確認
    func testSupabaseEpisodeDecoding() throws {
        // Supabaseから返されるJSON形式（snake_case）
        let json = """
        {
            "episode_id": "EP-123456",
            "person_id": "P-001",
            "person_name": "田中太郎",
            "age": 30,
            "category": "起業家",
            "episode_text": "あなたと同じ30歳のとき、田中太郎は会社を設立した。",
            "episode_type": "turning_point",
            "super_total_score": 85.5,
            "composite_score": 80.0,
            "fame_score_v3": 75.0,
            "episode_fame_v6": 70.0,
            "episode_fame_tier_v6": 3,
            "memorability_score": 8.5,
            "empathy_score": 7.5,
            "surprise_score": 6.0,
            "generation_quality_score": 9.0,
            "educational_value": 8.0,
            "story_quality": 7.0,
            "factual_density": 6.5,
            "iconic_score": 5.0,
            "person_type": "REAL",
            "work_title": null,
            "is_group_member": false,
            "group_name": null,
            "episode_count": 10,
            "wikipedia_pv": 50000,
            "created_at": "2024-01-15T10:30:00Z"
        }
        """

        let data = json.data(using: .utf8)!
        let decoder = JSONDecoder()

        let episode = try decoder.decode(SupabaseEpisode.self, from: data)

        // 基本フィールドの検証
        XCTAssertEqual(episode.episodeId, "EP-123456")
        XCTAssertEqual(episode.personId, "P-001")
        XCTAssertEqual(episode.personName, "田中太郎")
        XCTAssertEqual(episode.age, 30)
        XCTAssertEqual(episode.category, "起業家")
        XCTAssertEqual(episode.episodeText, "あなたと同じ30歳のとき、田中太郎は会社を設立した。")
        XCTAssertEqual(episode.episodeType, "turning_point")

        // スコアフィールドの検証（Optional値をアンラップ）
        XCTAssertEqual(episode.superTotalScore!, 85.5, accuracy: 0.01)
        XCTAssertEqual(episode.compositeScore!, 80.0, accuracy: 0.01)
        XCTAssertEqual(episode.fameScoreV3!, 75.0, accuracy: 0.01)
        XCTAssertEqual(episode.episodeFameV6!, 70.0, accuracy: 0.01)
        XCTAssertEqual(episode.episodeFameTierV6, 3)
        XCTAssertEqual(episode.memorabilityScore!, 8.5, accuracy: 0.01)
        XCTAssertEqual(episode.empathyScore!, 7.5, accuracy: 0.01)
        XCTAssertEqual(episode.surpriseScore!, 6.0, accuracy: 0.01)
        XCTAssertEqual(episode.generationQualityScore!, 9.0, accuracy: 0.01)
        XCTAssertEqual(episode.educationalValue!, 8.0, accuracy: 0.01)
        XCTAssertEqual(episode.storyQuality!, 7.0, accuracy: 0.01)
        XCTAssertEqual(episode.factualDensity!, 6.5, accuracy: 0.01)
        XCTAssertEqual(episode.iconicScore!, 5.0, accuracy: 0.01)

        // メタデータフィールドの検証
        XCTAssertEqual(episode.personType, "REAL")
        XCTAssertNil(episode.workTitle)
        XCTAssertEqual(episode.isGroupMember, false)
        XCTAssertNil(episode.groupName)
        XCTAssertEqual(episode.episodeCount, 10)
        XCTAssertEqual(episode.wikipediaPv, 50000)
        XCTAssertEqual(episode.createdAt, "2024-01-15T10:30:00Z")
    }

    /// toEpisode()メソッドがSupabaseEpisodeをEpisodeに正しく変換することを確認
    func testSupabaseEpisodeToEpisodeConversion() throws {
        let json = """
        {
            "episode_id": "EP-789",
            "person_id": "P-002",
            "person_name": "鈴木花子",
            "age": 25,
            "category": "アーティスト",
            "episode_text": "あなたと同じ25歳のとき、鈴木花子はデビューアルバムをリリースした。",
            "episode_type": "glory",
            "super_total_score": 90.0,
            "composite_score": 85.0,
            "fame_score_v3": 80.0,
            "episode_fame_v6": 75.0,
            "episode_fame_tier_v6": 4,
            "memorability_score": 9.0,
            "empathy_score": 8.0,
            "surprise_score": 7.0,
            "generation_quality_score": 8.5,
            "educational_value": 6.0,
            "story_quality": 9.0,
            "factual_density": 7.0,
            "iconic_score": 8.0,
            "person_type": "REAL",
            "work_title": null,
            "is_group_member": false,
            "group_name": null,
            "episode_count": 5,
            "wikipedia_pv": 30000,
            "created_at": "2024-02-20T14:00:00Z"
        }
        """

        let data = json.data(using: .utf8)!
        let decoder = JSONDecoder()
        let supabaseEpisode = try decoder.decode(SupabaseEpisode.self, from: data)

        // Episodeへ変換
        let episode = supabaseEpisode.toEpisode()

        // 変換結果の検証
        XCTAssertEqual(episode.id, "EP-789")
        XCTAssertEqual(episode.personName, "鈴木花子")
        XCTAssertNil(episode.personNameJa)  // Supabaseには日本語名フィールドがない
        XCTAssertEqual(episode.episode, "あなたと同じ25歳のとき、鈴木花子はデビューアルバムをリリースした。")
        XCTAssertEqual(episode.episodeAge, 25)
        XCTAssertEqual(episode.episodeType, "glory")
        XCTAssertNil(episode.createdAt)  // 文字列からDateへの変換は行われない
        XCTAssertEqual(episode.characterCount, 34)  // episodeText.count
        XCTAssertEqual(episode.qualityScore, 8)  // Int(8.5)
        XCTAssertNil(episode.tags)
        XCTAssertNil(episode.formatVersion)
        XCTAssertEqual(episode.personType, .real)
        XCTAssertNil(episode.workTitle)
    }

    /// CodingKeysによるsnake_case → camelCase変換が正しく動作することを確認
    func testSupabaseEpisodeCodingKeys() throws {
        // 最小限のJSONでキーマッピングをテスト
        let json = """
        {
            "episode_id": "test-id",
            "person_name": "テスト太郎",
            "episode_text": "テストエピソード",
            "super_total_score": 100.0,
            "fame_score_v3": 50.0,
            "episode_fame_v6": 60.0,
            "episode_fame_tier_v6": 5,
            "memorability_score": 7.0,
            "empathy_score": 8.0,
            "surprise_score": 9.0,
            "generation_quality_score": 10.0,
            "educational_value": 6.0,
            "story_quality": 7.0,
            "factual_density": 8.0,
            "iconic_score": 9.0,
            "person_type": "FICTIONAL",
            "work_title": "テスト作品",
            "is_group_member": true,
            "group_name": "テストグループ",
            "episode_count": 100,
            "wikipedia_pv": 999999,
            "created_at": "2024-12-31T23:59:59Z"
        }
        """

        let data = json.data(using: .utf8)!
        let decoder = JSONDecoder()
        let episode = try decoder.decode(SupabaseEpisode.self, from: data)

        // snake_case → camelCase変換の確認
        XCTAssertEqual(episode.episodeId, "test-id")           // episode_id
        XCTAssertEqual(episode.personName, "テスト太郎")        // person_name
        XCTAssertEqual(episode.episodeText, "テストエピソード")  // episode_text
        XCTAssertEqual(episode.superTotalScore, 100.0)          // super_total_score
        XCTAssertEqual(episode.fameScoreV3, 50.0)               // fame_score_v3
        XCTAssertEqual(episode.episodeFameV6, 60.0)             // episode_fame_v6
        XCTAssertEqual(episode.episodeFameTierV6, 5)            // episode_fame_tier_v6
        XCTAssertEqual(episode.memorabilityScore, 7.0)          // memorability_score
        XCTAssertEqual(episode.empathyScore, 8.0)               // empathy_score
        XCTAssertEqual(episode.surpriseScore, 9.0)              // surprise_score
        XCTAssertEqual(episode.generationQualityScore, 10.0)    // generation_quality_score
        XCTAssertEqual(episode.educationalValue, 6.0)           // educational_value
        XCTAssertEqual(episode.storyQuality, 7.0)        // story_quality
        XCTAssertEqual(episode.factualDensity, 8.0)             // factual_density
        XCTAssertEqual(episode.iconicScore, 9.0)                // iconic_score
        XCTAssertEqual(episode.personType, "FICTIONAL")         // person_type
        XCTAssertEqual(episode.workTitle, "テスト作品")          // work_title
        XCTAssertEqual(episode.isGroupMember, true)             // is_group_member
        XCTAssertEqual(episode.groupName, "テストグループ")      // group_name
        XCTAssertEqual(episode.episodeCount, 100)               // episode_count
        XCTAssertEqual(episode.wikipediaPv, 999999)             // wikipedia_pv
        XCTAssertEqual(episode.createdAt, "2024-12-31T23:59:59Z") // created_at
    }

    // MARK: - B. SupabaseConfigテスト

    /// テスト環境が正しく検出されることを確認
    /// XCTestが実行中のため、isRunningTestsはtrueを返すべき
    func testIsRunningTestsDetection() {
        // テスト環境では、XCTestConfigurationFilePath または XCTest クラスが存在
        // このテスト自体がXCTest内で実行されているため、検出されるはず

        // SupabaseConfigがテスト環境を検出して、
        // fatalErrorではなくフォールバック値を使用することを間接的に確認
        // （テストがクラッシュしなければ検出成功）
        let url = SupabaseConfig.projectURL
        XCTAssertNotNil(url)

        let key = SupabaseConfig.anonKey
        XCTAssertFalse(key.isEmpty)
    }

    /// テスト用フォールバックURLが有効なURLであることを確認
    func testTestFallbackURLIsValid() {
        let url = SupabaseConfig.projectURL

        // URLが有効であること
        XCTAssertNotNil(url.scheme)
        XCTAssertNotNil(url.host)

        // スキームがhttpsであること（フォールバック値でも）
        XCTAssertEqual(url.scheme, "https")

        // ホストが存在すること
        XCTAssertFalse(url.host?.isEmpty ?? true)
    }

    /// テーブル名定数が正しく定義されていることを確認
    func testTableNameConstant() {
        let tableName = SupabaseConfig.Tables.episodes

        // 空文字でないこと
        XCTAssertFalse(tableName.isEmpty)

        // デフォルト値または設定値が返ること
        // Info.plistに設定がない場合は "episodes" がデフォルト
        XCTAssertTrue(tableName == "episodes" || !tableName.contains("$("))
    }

    // MARK: - C. SupabaseManagerインスタンステスト

    /// シングルトンインスタンスが存在することを確認
    func testSharedInstanceExists() {
        let instance = SupabaseManager.shared

        // インスタンスがnilでないこと
        XCTAssertNotNil(instance)

        // 同じインスタンスが返されること（シングルトンパターン）
        let instance2 = SupabaseManager.shared
        XCTAssertTrue(instance === instance2)
    }

    /// クライアントが初期化される（クラッシュしない）ことを確認
    func testClientInitialization() {
        // テスト環境ではフォールバック値が使用されるため、
        // クライアント初期化でクラッシュしないことを確認
        // このテスト自体が正常に実行されれば成功

        let instance = SupabaseManager.shared
        XCTAssertNotNil(instance)

        // SupabaseManagerのinit()が完了していることを確認
        // privateなclientプロパティには直接アクセスできないが、
        // インスタンスが作成されていればclientも初期化済み
    }

    // MARK: - D. 追加テスト（オプショナルフィールド）

    /// オプショナルフィールドがnullの場合にデコードが成功することを確認
    func testSupabaseEpisodeDecodingWithNulls() throws {
        // 最小限の必須フィールドのみ
        let json = """
        {
            "episode_id": "EP-MINIMAL",
            "person_name": "最小テスト",
            "episode_text": "必須フィールドのみ"
        }
        """

        let data = json.data(using: .utf8)!
        let decoder = JSONDecoder()

        let episode = try decoder.decode(SupabaseEpisode.self, from: data)

        // 必須フィールドの検証
        XCTAssertEqual(episode.episodeId, "EP-MINIMAL")
        XCTAssertEqual(episode.personName, "最小テスト")
        XCTAssertEqual(episode.episodeText, "必須フィールドのみ")

        // オプショナルフィールドがnilであること
        XCTAssertNil(episode.personId)
        XCTAssertNil(episode.age)
        XCTAssertNil(episode.category)
        XCTAssertNil(episode.episodeType)
        XCTAssertNil(episode.superTotalScore)
        XCTAssertNil(episode.compositeScore)
        XCTAssertNil(episode.personType)
        XCTAssertNil(episode.workTitle)
        XCTAssertNil(episode.createdAt)
    }

    /// 架空キャラクターのtoEpisode()変換を確認
    func testSupabaseEpisodeToEpisodeConversionForFictional() throws {
        let json = """
        {
            "episode_id": "EP-FICTIONAL-001",
            "person_name": "孫悟空",
            "episode_text": "あなたと同じ30歳のとき、孫悟空はフリーザを倒した。",
            "age": 30,
            "person_type": "FICTIONAL",
            "work_title": "ドラゴンボール",
            "generation_quality_score": 9.5
        }
        """

        let data = json.data(using: .utf8)!
        let decoder = JSONDecoder()
        let supabaseEpisode = try decoder.decode(SupabaseEpisode.self, from: data)

        let episode = supabaseEpisode.toEpisode()

        // 架空キャラクター関連フィールドの検証
        XCTAssertEqual(episode.personType, .fictional)
        XCTAssertEqual(episode.workTitle, "ドラゴンボール")
        XCTAssertTrue(episode.isFictional)
    }
}
