// periphery:ignore:all - Supabase設定（環境変数経由で使用）
//
//  SupabaseConfig.swift
//  FinalHourglass
//
//  Supabase接続設定
//  設定値はxcconfig経由でInfo.plistから読み込み
//  注意: ANON_KEYはpublic用途で設計されており、RLSで保護されています
//
//  セットアップ:
//  1. Debug.xcconfig.template を Debug.xcconfig にコピー
//  2. Release.xcconfig.template を Release.xcconfig にコピー
//  3. 各ファイル内のプレースホルダーを実際の値に置き換え
//

import Foundation
import OSLog

// MARK: - Logger

private let supabaseLogger = Logger(
    subsystem: Bundle.main.bundleIdentifier ?? "co.aiuelab.finalhourclass",
    category: "Supabase"
)

// MARK: - Test Environment Detection

/// テスト環境かどうかを検出
private var isRunningTests: Bool {
    // XCTestが実行中かどうかをチェック（Unit Tests）
    if ProcessInfo.processInfo.environment["XCTestConfigurationFilePath"] != nil
        || NSClassFromString("XCTest") != nil {
        return true
    }
    // UIテスト用launch argumentsをチェック（E2E Tests）
    // アプリは別プロセスで起動されるため、launch argumentsで判定
    let uiTestArguments = ["-UITest_ResetState", "-UITest_SkipOnboarding", "-UITest_DisableAnimations"]
    for arg in uiTestArguments where ProcessInfo.processInfo.arguments.contains(arg) {
        return true
    }
    return false
}

// MARK: - Fallback URL

/// 設定未構成時のフォールバックURL（無効なURL）
private let fallbackURL = URL(string: "https://unconfigured.supabase.co")!

/// テスト環境用フォールバックURL
private let testFallbackURL = URL(string: "https://test.supabase.co")!

enum SupabaseConfig {
    // MARK: - 設定エラー

    /// 設定が見つからない場合のエラー
    enum ConfigurationError: Error, LocalizedError {
        case missingProjectURL
        case missingAnonKey
        case invalidURL(String)
        case configurationNotReady

        var errorDescription: String? {
            switch self {
            case .missingProjectURL:
                return "SUPABASE_PROJECT_URL is not configured. Check xcconfig setup."
            case .missingAnonKey:
                return "SUPABASE_ANON_KEY is not configured. Check xcconfig setup."
            case .invalidURL(let urlString):
                return "Invalid Supabase URL: \(urlString)"
            case .configurationNotReady:
                return "Supabase configuration is not ready. Check xcconfig setup."
            }
        }
    }

    // MARK: - 設定状態

    /// 設定読み込み状態
    enum ConfigurationState {
        case valid
        case missingURL
        case invalidURL
        case missingKey
        case usingTestFallback
    }

    /// 現在の設定状態（診断用）
    private(set) static var configurationState: ConfigurationState = .valid

    // MARK: - Info.plist から読み込み (xcconfig経由)

    /// Supabase Project URL
    /// xcconfig -> Info.plist -> Bundle.main.infoDictionary経由で読み込み
    /// 設定未構成時はフォールバックURLを返し、クラッシュを回避
    static let projectURL: URL = {
        guard let urlString = Bundle.main.infoDictionary?["SUPABASE_PROJECT_URL"] as? String,
              !urlString.isEmpty,
              !urlString.contains("$("),  // 未展開の変数チェック
              !urlString.contains("YOUR_SUPABASE") else {  // テンプレート値チェック

            // テスト環境ではフォールバックURLを返す
            if isRunningTests {
                supabaseLogger.warning("SUPABASE_PROJECT_URL not configured - using test fallback")
                configurationState = .usingTestFallback
                return testFallbackURL
            }

            // ログ出力（DEBUGビルドでは詳細なガイダンスを表示）
            #if DEBUG
            supabaseLogger.error("""
                SUPABASE_PROJECT_URL not configured in xcconfig
                Fix:
                  1. Copy Debug.xcconfig.template to Debug.xcconfig
                  2. Replace YOUR_SUPABASE_PROJECT_ID with your actual Project ID
                  3. Rebuild the app
                """)
            #else
            supabaseLogger.error("Supabase configuration missing - using fallback URL")
            #endif

            configurationState = .missingURL
            return fallbackURL
        }

        guard let url = URL(string: urlString) else {
            // テスト環境ではフォールバックURLを返す
            if isRunningTests {
                supabaseLogger.warning("Invalid Supabase URL - using test fallback")
                configurationState = .usingTestFallback
                return testFallbackURL
            }

            // ログ出力
            #if DEBUG
            supabaseLogger.error("""
                Invalid Supabase URL: \(urlString)
                Fix:
                  1. Check Debug.xcconfig for correct URL format
                  2. Ensure URL starts with https://
                  3. Rebuild the app
                """)
            #else
            supabaseLogger.error("Invalid Supabase URL format - using fallback")
            #endif

            configurationState = .invalidURL
            return fallbackURL
        }

        return url
    }()

    /// Supabase Anonymous Key (RLSで保護済み - SELECT only)
    /// xcconfig -> Info.plist -> Bundle.main.infoDictionary経由で読み込み
    /// 設定未構成時は空文字を返し、クラッシュを回避
    static let anonKey: String = {
        guard let key = Bundle.main.infoDictionary?["SUPABASE_ANON_KEY"] as? String,
              !key.isEmpty,
              !key.contains("$("),  // 未展開の変数チェック
              !key.contains("YOUR_SUPABASE") else {  // テンプレート値チェック

            // テスト環境ではダミーキーを返す
            if isRunningTests {
                supabaseLogger.warning("SUPABASE_ANON_KEY not configured - using test fallback")
                configurationState = .usingTestFallback
                return "test-anon-key-for-unit-tests"
            }

            // ログ出力
            #if DEBUG
            supabaseLogger.error("""
                SUPABASE_ANON_KEY not configured in xcconfig
                Fix:
                  1. Copy Debug.xcconfig.template to Debug.xcconfig
                  2. Replace YOUR_SUPABASE_ANON_KEY with your actual Anon Key
                  3. Rebuild the app
                """)
            #else
            supabaseLogger.error("Supabase anon key missing - using empty fallback")
            #endif

            configurationState = .missingKey
            return ""
        }

        return key
    }()

    // MARK: - 安全な設定取得（Result型）

    /// 設定を安全に取得（Result型で返却）
    /// 呼び出し側で明示的にエラーハンドリングが必要
    static func getConfiguration() -> Result<(url: URL, key: String), ConfigurationError> {
        // URLが有効か確認
        guard projectURL.host != "unconfigured.supabase.co" else {
            return .failure(.missingProjectURL)
        }

        // キーが有効か確認
        guard !anonKey.isEmpty, anonKey != "test-anon-key-for-unit-tests" else {
            return .failure(.missingAnonKey)
        }

        // 設定が有効か確認
        guard isConfigurationValid else {
            return .failure(.configurationNotReady)
        }

        return .success((url: projectURL, key: anonKey))
    }

    // MARK: - テーブル名

    enum Tables {
        /// エピソードテーブル名
        static let episodes: String = {
            if let tableName = Bundle.main.infoDictionary?["SUPABASE_EPISODES_TABLE"] as? String,
               !tableName.isEmpty,
               !tableName.contains("$(") {
                return tableName
            }
            supabaseLogger.info("Table name not configured, using default: episodes")
            return "episodes"
        }()
    }

    // MARK: - データソース設定

    enum DataSource {
        case firebase
        case supabase
    }

    /// 現在のデータソース（切り替え可能）
    /// 本番移行後はsupabaseに変更
    static var currentDataSource: DataSource = .supabase

    /// Supabaseを有効にするかどうか
    static var isSupabaseEnabled: Bool {
        return currentDataSource == .supabase
    }

    /// Supabase設定が有効かどうか（設定値が正しく読み込まれているか）
    static var isConfigurationValid: Bool {
        // anonKeyが空でないことを確認
        guard !anonKey.isEmpty else {
            supabaseLogger.warning("Configuration invalid: anonKey is empty")
            return false
        }

        // テスト用フォールバック値の場合は無効
        guard anonKey != "test-anon-key-for-unit-tests" else {
            supabaseLogger.warning("Configuration invalid: using test fallback key")
            return false
        }

        // URLスキームがhttpsであることを確認
        guard projectURL.scheme == "https" else {
            supabaseLogger.warning("Configuration invalid: scheme must be https")
            return false
        }

        // hostが有効であることを確認
        guard let host = projectURL.host,
              !host.isEmpty,
              host != "invalid.supabase.co",
              host != "unconfigured.supabase.co",
              host != "test.supabase.co" else {
            supabaseLogger.warning("Configuration invalid: invalid host")
            return false
        }

        // hostが.supabase.coで終わることを確認
        guard host.hasSuffix(".supabase.co") else {
            supabaseLogger.warning("Configuration invalid: host must be .supabase.co")
            return false
        }

        // anonKeyの長さをチェック（Supabase JWT は通常100文字以上）
        guard anonKey.count >= 50 else {
            supabaseLogger.warning("Configuration invalid: anonKey too short (\(anonKey.count) chars)")
            return false
        }

        return true
    }

    // MARK: - デバッグ設定

    /// 接続テストを有効にするか（DEBUG時のみ使用）
    static var isConnectionTestEnabled: Bool {
        if let testEnabled = Bundle.main.infoDictionary?["SUPABASE_DEBUG_CONNECTION_TEST"] as? String {
            return testEnabled.uppercased() == "YES"
        }
        #if DEBUG
        return true  // DEBUGビルドではデフォルトで有効
        #else
        return false
        #endif
    }

    // MARK: - 設定確認用（DEBUG）

    #if DEBUG
    /// 現在の設定を出力（デバッグ用）
    static func printCurrentConfig() {
        supabaseLogger.debug("--------------------------------------------")
        supabaseLogger.debug("[Supabase Configuration]")
        supabaseLogger.debug("--------------------------------------------")
        supabaseLogger.debug("  Project URL: \(projectURL.absoluteString)")

        // AnonKeyの安全な表示（先頭4文字 + ... + 末尾4文字）
        let displayKey: String
        if anonKey.count >= 8 {
            displayKey = String(anonKey.prefix(4)) + "..." + String(anonKey.suffix(4))
        } else {
            displayKey = "***REDACTED***"
        }
        supabaseLogger.debug("  Anon Key: \(displayKey) (\(anonKey.count) chars)")

        supabaseLogger.debug("  Table: \(Tables.episodes)")
        supabaseLogger.debug("  Data Source: \(String(describing: currentDataSource))")
        supabaseLogger.debug("  Connection Test: \(isConnectionTestEnabled)")
        supabaseLogger.debug("  Configuration Valid: \(isConfigurationValid)")
        supabaseLogger.debug("  Configuration State: \(String(describing: configurationState))")
        supabaseLogger.debug("--------------------------------------------")
    }
    #endif
}
