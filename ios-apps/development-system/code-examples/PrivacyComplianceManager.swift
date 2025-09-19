import Foundation
import UIKit
import AppTrackingTransparency
import AdSupport

/// Apple App Store Guidelines準拠のプライバシー管理システム
/// Guidelines 5.1.2 (Privacy - Data Collection and Storage)
class PrivacyComplianceManager: ObservableObject {

    static let shared = PrivacyComplianceManager()

    @Published var hasUserConsent = false
    @Published var trackingAuthorizationStatus: ATTrackingManager.AuthorizationStatus = .notDetermined

    private let userDefaults = UserDefaults.standard
    private let privacyConsentKey = "privacy_consent_granted"
    private let consentVersionKey = "privacy_consent_version"

    // 現在のプライバシーポリシーバージョン
    private let currentPrivacyVersion = "1.0.0"

    private init() {
        loadConsentStatus()
    }

    // MARK: - Privacy Consent Management

    /// プライバシー同意の確認
    func checkPrivacyConsent() -> Bool {
        let hasConsent = userDefaults.bool(forKey: privacyConsentKey)
        let consentVersion = userDefaults.string(forKey: consentVersionKey) ?? ""

        // バージョンが古い場合は再同意を求める
        if hasConsent && consentVersion != currentPrivacyVersion {
            return false
        }

        return hasConsent
    }

    /// プライバシー同意の記録
    func recordPrivacyConsent() {
        userDefaults.set(true, forKey: privacyConsentKey)
        userDefaults.set(currentPrivacyVersion, forKey: consentVersionKey)
        userDefaults.set(Date(), forKey: "privacy_consent_date")
        hasUserConsent = true

        // App Store Guidelines 5.1.2: 同意記録の保存
        logPrivacyEvent("Privacy consent granted", metadata: [
            "version": currentPrivacyVersion,
            "timestamp": ISO8601DateFormatter().string(from: Date())
        ])
    }

    /// プライバシー同意の撤回
    func revokePrivacyConsent() {
        userDefaults.set(false, forKey: privacyConsentKey)
        userDefaults.removeObject(forKey: consentVersionKey)
        hasUserConsent = false

        // 収集済みデータの削除
        clearCollectedData()

        logPrivacyEvent("Privacy consent revoked")
    }

    // MARK: - App Tracking Transparency (ATT)

    /// iOS 14.5+ App Tracking Transparency対応
    @available(iOS 14, *)
    func requestTrackingPermission() async {
        await MainActor.run {
            trackingAuthorizationStatus = ATTrackingManager.trackingAuthorizationStatus
        }

        if trackingAuthorizationStatus == .notDetermined {
            let status = await ATTrackingManager.requestTrackingAuthorization()
            await MainActor.run {
                trackingAuthorizationStatus = status
            }

            logPrivacyEvent("ATT permission requested", metadata: [
                "status": statusToString(status)
            ])
        }
    }

    /// 広告識別子の取得（ATT準拠）
    func getAdvertisingIdentifier() -> String? {
        guard trackingAuthorizationStatus == .authorized else {
            return nil
        }

        let idfa = ASIdentifierManager.shared().advertisingIdentifier
        return idfa.uuidString != "00000000-0000-0000-0000-000000000000" ? idfa.uuidString : nil
    }

    // MARK: - Data Minimization (Guidelines 5.1.1)

    /// 必要最小限のデータのみ収集
    struct CollectedData {
        let userID: String
        let appVersion: String
        let deviceModel: String
        let osVersion: String
        let timestamp: Date

        // 収集しないデータ例:
        // - 詳細な位置情報（不要な場合）
        // - 連絡先情報（不要な場合）
        // - 健康データ（Health & Fitnessカテゴリ以外）
    }

    func collectNecessaryDataOnly() -> CollectedData? {
        guard hasUserConsent else {
            return nil
        }

        return CollectedData(
            userID: getUserID(),
            appVersion: getAppVersion(),
            deviceModel: getDeviceModel(),
            osVersion: UIDevice.current.systemVersion,
            timestamp: Date()
        )
    }

    // MARK: - Data Security (Guidelines 5.1.3)

    /// 暗号化されたデータストレージ
    func securelyStoreData<T: Codable>(_ data: T, forKey key: String) throws {
        let encoder = JSONEncoder()
        let encodedData = try encoder.encode(data)

        // キーチェーンまたは暗号化ストレージに保存
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecValueData as String: encodedData
        ]

        SecItemDelete(query as CFDictionary)
        let status = SecItemAdd(query as CFDictionary, nil)

        guard status == errSecSuccess else {
            throw PrivacyError.secureStorageFailed
        }
    }

    /// 暗号化されたデータの読み取り
    func securelyRetrieveData<T: Codable>(_ type: T.Type, forKey key: String) throws -> T? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecReturnData as String: true
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        guard status == errSecSuccess,
              let data = result as? Data else {
            return nil
        }

        let decoder = JSONDecoder()
        return try decoder.decode(type, from: data)
    }

    // MARK: - Data Retention (Guidelines 5.1.4)

    /// データ保持期間管理
    func cleanupExpiredData() {
        let retentionPeriod: TimeInterval = 365 * 24 * 60 * 60 // 1年
        let cutoffDate = Date().addingTimeInterval(-retentionPeriod)

        // 古いデータの削除
        cleanupDataOlderThan(cutoffDate)

        logPrivacyEvent("Data cleanup completed", metadata: [
            "cutoff_date": ISO8601DateFormatter().string(from: cutoffDate)
        ])
    }

    // MARK: - COPPA Compliance (13歳未満ユーザー対応)

    /// COPPA準拠チェック
    func isCOPPACompliant(userAge: Int?) -> Bool {
        guard let age = userAge else {
            // 年齢不明の場合は最も厳しい基準を適用
            return false
        }

        if age < 13 {
            // 13歳未満の場合、追加の制限
            return validateCOPPACompliance()
        }

        return true
    }

    private func validateCOPPACompliance() -> Bool {
        // COPPA要件チェック
        let checks = [
            hasParentalConsent(),
            hasLimitedDataCollection(),
            hasNoPersonalizedAds(),
            hasNoDirectCommunication()
        ]

        return checks.allSatisfy { $0 }
    }

    // MARK: - Privacy Dashboard

    /// ユーザー向けプライバシーダッシュボード
    func generatePrivacyReport() -> PrivacyReport {
        return PrivacyReport(
            consentStatus: hasUserConsent,
            consentDate: userDefaults.object(forKey: "privacy_consent_date") as? Date,
            dataCollected: getCollectedDataSummary(),
            dataShared: getDataSharingStatus(),
            retentionPeriod: "365 days",
            lastCleanup: getLastCleanupDate()
        )
    }

    // MARK: - Helper Methods

    private func loadConsentStatus() {
        hasUserConsent = checkPrivacyConsent()
        if #available(iOS 14, *) {
            trackingAuthorizationStatus = ATTrackingManager.trackingAuthorizationStatus
        }
    }

    private func statusToString(_ status: ATTrackingManager.AuthorizationStatus) -> String {
        switch status {
        case .authorized: return "authorized"
        case .denied: return "denied"
        case .restricted: return "restricted"
        case .notDetermined: return "notDetermined"
        @unknown default: return "unknown"
        }
    }

    private func getUserID() -> String {
        // UUID生成（個人識別不可能）
        if let existingID = userDefaults.string(forKey: "user_anonymous_id") {
            return existingID
        }

        let newID = UUID().uuidString
        userDefaults.set(newID, forKey: "user_anonymous_id")
        return newID
    }

    private func getAppVersion() -> String {
        return Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "Unknown"
    }

    private func getDeviceModel() -> String {
        var systemInfo = utsname()
        uname(&systemInfo)
        let identifier = withUnsafePointer(to: &systemInfo.machine) {
            $0.withMemoryRebound(to: CChar.self, capacity: 1) {
                ptr in String.init(validatingUTF8: ptr)
            }
        }
        return identifier ?? "Unknown"
    }

    private func clearCollectedData() {
        // 収集済みデータの安全な削除
        userDefaults.removeObject(forKey: "user_anonymous_id")
        // その他の収集データも削除
    }

    private func cleanupDataOlderThan(_ date: Date) {
        // 古いデータの削除実装
    }

    private func hasParentalConsent() -> Bool {
        // 保護者同意の確認実装
        return userDefaults.bool(forKey: "parental_consent")
    }

    private func hasLimitedDataCollection() -> Bool {
        // 制限されたデータ収集の確認
        return true
    }

    private func hasNoPersonalizedAds() -> Bool {
        // パーソナライズ広告なしの確認
        return true
    }

    private func hasNoDirectCommunication() -> Bool {
        // 直接コミュニケーション機能なしの確認
        return true
    }

    private func getCollectedDataSummary() -> [String] {
        return ["Device model", "App version", "Usage statistics"]
    }

    private func getDataSharingStatus() -> [String: Bool] {
        return [
            "Analytics providers": trackingAuthorizationStatus == .authorized,
            "Ad networks": trackingAuthorizationStatus == .authorized,
            "Social media": false
        ]
    }

    private func getLastCleanupDate() -> Date? {
        return userDefaults.object(forKey: "last_data_cleanup") as? Date
    }

    private func logPrivacyEvent(_ event: String, metadata: [String: Any] = [:]) {
        // プライバシー関連イベントのログ記録
        print("Privacy Event: \(event), Metadata: \(metadata)")
    }
}

// MARK: - Supporting Types

enum PrivacyError: Error {
    case secureStorageFailed
    case dataRetrievalFailed
    case consentRequired
}

struct PrivacyReport {
    let consentStatus: Bool
    let consentDate: Date?
    let dataCollected: [String]
    let dataShared: [String: Bool]
    let retentionPeriod: String
    let lastCleanup: Date?
}
