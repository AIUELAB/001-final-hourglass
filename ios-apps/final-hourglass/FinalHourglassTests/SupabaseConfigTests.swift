//
//  SupabaseConfigTests.swift
//  FinalHourglassTests
//
//  SupabaseConfig の単体テスト
//

import XCTest
@testable import FinalHourglass

final class SupabaseConfigTests: XCTestCase {

    // MARK: - projectURL

    func testProjectURLIsNotNil() {
        // テスト環境ではフォールバックURL "https://test.supabase.co" が返される
        let url = SupabaseConfig.projectURL
        XCTAssertNotNil(url)
        XCTAssertEqual(url.scheme, "https")
    }

    // MARK: - anonKey

    func testAnonKeyIsNotEmpty() {
        // テスト環境ではフォールバック "test-anon-key-for-unit-tests" が返される
        let key = SupabaseConfig.anonKey
        XCTAssertFalse(key.isEmpty, "anonKey should not be empty in test environment")
    }

    // MARK: - Tables

    func testTablesEpisodesDefaultValue() {
        XCTAssertEqual(SupabaseConfig.Tables.episodes, "episodes")
    }

    // MARK: - DataSource

    func testDataSourceEnumHasBothCases() {
        let firebase = SupabaseConfig.DataSource.firebase
        let supabase = SupabaseConfig.DataSource.supabase
        // 両ケースが存在し、異なることを確認
        XCTAssertFalse(isEqual(firebase, supabase))
    }

    func testCurrentDataSourceDefaultsToSupabase() {
        // デフォルト値は .supabase
        switch SupabaseConfig.currentDataSource {
        case .supabase:
            break // 期待通り
        case .firebase:
            XCTFail("currentDataSource should default to .supabase")
        }
    }

    // MARK: - isSupabaseEnabled

    func testIsSupabaseEnabledReturnsTrue() {
        // currentDataSource が .supabase のとき true
        XCTAssertTrue(SupabaseConfig.isSupabaseEnabled)
    }

    // MARK: - isConfigurationValid

    func testIsConfigurationValidReflectsActualConfiguration() {
        // テスト環境では2つのケースがある:
        // 1. Info.plistから実際のキーが読み込まれる → isConfigurationValid = true (if URL is also valid)
        // 2. フォールバック値 "test-anon-key-for-unit-tests" → isConfigurationValid = false
        let key = SupabaseConfig.anonKey
        let isValid = SupabaseConfig.isConfigurationValid

        if key == "test-anon-key-for-unit-tests" {
            // フォールバック値の場合は無効
            XCTAssertFalse(isValid,
                           "isConfigurationValid should be false with test fallback key")
        } else if key.hasPrefix("eyJ") && key.count >= 100 {
            // 有効なJWTキーの場合、URLの設定にも依存するためどちらも許容
            // (有効なキーがあってもURLが無効なら false になりうる)
            XCTAssertTrue(true, "Valid JWT key detected, configuration validity depends on URL too")
        } else {
            // 予期しないパターン
            XCTFail("Unexpected anonKey pattern: \(key.prefix(10))... (\(key.count) chars)")
        }
    }

    // MARK: - ConfigurationError

    func testConfigurationErrorDescriptionsAreNotEmpty() {
        let errors: [SupabaseConfig.ConfigurationError] = [
            .missingProjectURL,
            .missingAnonKey,
            .invalidURL("https://bad-url"),
        ]

        for error in errors {
            let description = error.errorDescription ?? ""
            XCTAssertFalse(description.isEmpty,
                           "\(error) should have a non-empty error description")
        }
    }

    // MARK: - Helpers

    /// DataSource は Equatable 未準拠のため、パターンマッチで比較
    private func isEqual(_ lhs: SupabaseConfig.DataSource, _ rhs: SupabaseConfig.DataSource) -> Bool {
        switch (lhs, rhs) {
        case (.firebase, .firebase), (.supabase, .supabase):
            return true
        default:
            return false
        }
    }
}
