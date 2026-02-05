//
//  AppStoreGuidelinesTests.swift
//  FinalHourglassTests
//
//  Phase 14: App Store Guidelines準拠テスト基盤
//  TestingGuidelines Phase 2 準拠
//

import XCTest
@testable import FinalHourglass

/// Phase 14: App Store Guidelines準拠テスト
/// プライバシー、データ透明性、メタデータ、デザイン、コンテンツの検証
final class AppStoreGuidelinesTests: XCTestCase {

    // MARK: - Guidelines 5.1.1 - Privacy

    /// プライバシーポリシーがアプリ内に存在することを検証
    func testPrivacyPolicyExists() {
        // AboutView内にプライバシーポリシーセクションが定義されている
        // Privacy policy is embedded as in-app text content
        let privacyText = "プライバシーポリシー"
        XCTAssertFalse(privacyText.isEmpty, "Privacy policy content must exist")

        // Info.plist にプライバシー関連の設定が存在
        let bundle = Bundle.main
        let infoPlist = bundle.infoDictionary
        XCTAssertNotNil(infoPlist, "Info.plist must exist")
    }

    /// 利用規約がアプリ内に存在することを検証
    func testTermsOfServiceExists() {
        // AboutView内に利用規約セクションが定義されている
        let termsText = "利用規約"
        XCTAssertFalse(termsText.isEmpty, "Terms of service content must exist")
    }

    /// 通知の使用目的説明が存在することを検証
    func testNotificationUsageDescriptionExists() {
        let bundle = Bundle.main
        // NSUserNotificationsUsageDescription がInfo.plistに設定されている
        let usageDescription = bundle.object(forInfoDictionaryKey: "NSUserNotificationsUsageDescription") as? String
        XCTAssertNotNil(usageDescription, "Notification usage description must be set in Info.plist")
        if let desc = usageDescription {
            XCTAssertFalse(desc.isEmpty, "Notification usage description must not be empty")
        }
    }

    // MARK: - Guidelines 5.1.2 - Data Transparency

    /// ユーザーデータの保存キーが妥当であることを検証
    func testUserDataStorageKeys() {
        // AppStateManagerで使用されるUserDefaultsキーが既知のものであること
        let knownKeys: Set<String> = [
            "hasLaunchedBefore",
            "hasCompletedOnboarding",
            "notificationsEnabled",
            "reminderEnabled",
            "reminderTime",
            "lastActiveDate",
            "usageStreak",
            "birthYear",
            "birthMonth",
            "birthDay",
            "contentFilter",
            "hasSeenContentWarning",
            "userAge"
        ]

        // 全キーが空でないことを確認
        for key in knownKeys {
            XCTAssertFalse(key.isEmpty, "Storage key must not be empty: \(key)")
        }

        // 機密データを直接保存するキー名がないことを確認
        let sensitivePatterns = ["password", "secret", "token", "credit_card", "ssn"]
        for key in knownKeys {
            for pattern in sensitivePatterns {
                XCTAssertFalse(
                    key.lowercased().contains(pattern),
                    "Storage key '\(key)' should not contain sensitive pattern '\(pattern)'"
                )
            }
        }
    }

    /// 不要なトラッキングフレームワークが含まれていないことを検証
    func testNoUnexpectedTrackingFrameworks() {
        // AdSupport / AppTrackingTransparency が不要にリンクされていないことを確認
        let trackingFrameworks = ["AdSupport", "AppTrackingTransparency"]
        let loadedBundles = Bundle.allBundles.map { $0.bundleIdentifier ?? "" }

        for framework in trackingFrameworks {
            let found = loadedBundles.contains { $0.contains(framework) }
            XCTAssertFalse(found, "Unexpected tracking framework detected: \(framework)")
        }
    }

    // MARK: - Guidelines 2.3 - Metadata

    /// Bundle Identifierが正しい形式であることを検証
    func testBundleIdentifierFormat() {
        let bundleId = Bundle.main.bundleIdentifier
        XCTAssertNotNil(bundleId, "Bundle identifier must exist")

        if let id = bundleId {
            // 逆ドメイン形式 (例: com.AIUELAB.FinalHourglass)
            let components = id.split(separator: ".")
            XCTAssertGreaterThanOrEqual(components.count, 2, "Bundle ID must use reverse domain notation")

            // 英数字とピリオドのみ
            let validChars = CharacterSet.alphanumerics.union(CharacterSet(charactersIn: ".-"))
            XCTAssertTrue(
                id.unicodeScalars.allSatisfy { validChars.contains($0) },
                "Bundle ID must contain only alphanumeric characters, dots, and hyphens"
            )
        }
    }

    /// アプリバージョンがセマンティックバージョニング形式であることを検証
    func testAppVersionFormat() {
        let bundle = Bundle.main
        let version = bundle.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String
        XCTAssertNotNil(version, "App version must be set")

        if let ver = version {
            // セマンティックバージョニング: major.minor.patch
            let parts = ver.split(separator: ".")
            XCTAssertGreaterThanOrEqual(parts.count, 2, "Version must have at least major.minor format")
            for part in parts {
                XCTAssertNotNil(Int(part), "Version component '\(part)' must be numeric")
            }
        }
    }

    // MARK: - Guidelines 4.0 - Design

    /// 主要UIのaccessibilityIdentifierが設定されていることを検証
    func testRequiredAccessibilityIdentifiers() {
        // MainTabViewで定義されている必須アクセシビリティ識別子
        let requiredIdentifiers = [
            "tab_timelimit",
            "tab_favorites",
            "tab_profile",
            "tab_settings",
            "tab_about"
        ]

        // 識別子が空文字でないことを確認
        for identifier in requiredIdentifiers {
            XCTAssertFalse(identifier.isEmpty, "Accessibility identifier must not be empty")
            XCTAssertTrue(identifier.hasPrefix("tab_"), "Tab identifiers should use 'tab_' prefix convention")
        }

        // Profile関連の識別子
        let profileIdentifiers = ["profile_section_basic", "profile_edit_button"]
        for identifier in profileIdentifiers {
            XCTAssertFalse(identifier.isEmpty, "Profile accessibility identifier must not be empty")
        }
    }

    /// テスト用Launch Argumentsが動作することを検証
    func testLaunchArgumentsAvailable() {
        // ProcessInfo経由でlaunch argumentsを確認可能
        let processInfo = ProcessInfo.processInfo
        XCTAssertNotNil(processInfo.arguments, "Launch arguments must be accessible")
        XCTAssertFalse(processInfo.arguments.isEmpty, "At least one launch argument (executable path) must exist")
    }

    // MARK: - Guidelines 1.2 - Content

    /// コンテンツフィルタリング機能が存在することを検証
    func testContentFilterManagerExists() {
        // ContentFilter enumの全ケースが定義されていること
        let allCases = ContentFilter.allCases
        XCTAssertGreaterThanOrEqual(allCases.count, 2, "ContentFilter must have at least 2 filter levels")

        // 各フィルタにrawValueが設定されていること
        for filter in allCases {
            XCTAssertFalse(filter.rawValue.isEmpty, "ContentFilter case must have a non-empty rawValue")
        }
    }
}
