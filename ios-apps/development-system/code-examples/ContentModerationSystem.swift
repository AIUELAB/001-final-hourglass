import Foundation
import UIKit
import Vision
import NaturalLanguage

/// Apple App Store Guidelines準拠のユーザー生成コンテンツ管理システム
/// Guidelines 1.2 (User Generated Content) - ユーザー生成コンテンツの適切な管理
class ContentModerationSystem: ObservableObject {

    static let shared = ContentModerationSystem()

    @Published var moderationEnabled = true

    private let userDefaults = UserDefaults.standard

    private init() {
        setupModeration()
    }

    // MARK: - コンテンツフィルタリング設定

    enum ContentCategory {
        case profanity      // 冒涜的言語
        case harassment     // ハラスメント
        case hate          // ヘイトスピーチ
        case violence      // 暴力的内容
        case sexual        // 性的内容
        case spam          // スパム
        case personalInfo  // 個人情報
        case inappropriate // 不適切な内容
    }

    enum ModerationAction {
        case allow
        case warn
        case block
        case reportToModerator
        case autoRemove
    }

    enum ContentType {
        case text
        case image
        case video
        case audio
    }

    // MARK: - テキストコンテンツのモデレーション

    /// App Store Guidelines 1.2.1準拠のテキストフィルタリング
    func moderateText(_ text: String, completion: @escaping (ModerationResult) -> Void) {
        Task {
            let result = await performTextModeration(text)
            DispatchQueue.main.async {
                completion(result)
            }
        }
    }

    private func performTextModeration(_ text: String) async -> ModerationResult {
        var violations: [ContentCategory] = []
        var confidence: Float = 0.0

        // 1. 基本的な禁止用語チェック
        violations.append(contentsOf: checkProfanity(text))

        // 2. Natural Language Framework を使用したセンチメント分析
        violations.append(contentsOf: await analyzeTextSentiment(text))

        // 3. 個人情報の検出
        violations.append(contentsOf: detectPersonalInformation(text))

        // 4. スパム検出
        violations.append(contentsOf: detectSpam(text))

        // 5. ヘイトスピーチ検出
        violations.append(contentsOf: detectHateSpeech(text))

        let action = determineAction(for: violations)
        confidence = calculateConfidence(for: violations, textLength: text.count)

        return ModerationResult(
            contentType: .text,
            isApproved: action == .allow,
            violations: violations,
            suggestedAction: action,
            confidence: confidence,
            originalContent: text,
            moderatedContent: action == .allow ? text : filterContent(text, violations: violations)
        )
    }

    private func checkProfanity(_ text: String) -> [ContentCategory] {
        // App Store Guidelines 1.2: 冒涜的言語の検出
        let profanityList = loadProfanityList()
        let lowercaseText = text.lowercased()

        for word in profanityList {
            if lowercaseText.contains(word.lowercased()) {
                return [.profanity]
            }
        }

        return []
    }

    private func analyzeTextSentiment(_ text: String) async -> [ContentCategory] {
        let tagger = NLTagger(tagSchemes: [.sentiment])
        tagger.string = text

        let (sentiment, confidence) = tagger.tag(at: text.startIndex,
                                                 unit: .paragraph,
                                                 scheme: .sentiment)

        if let sentiment = sentiment, confidence > 0.8 {
            switch sentiment {
            case .negative:
                return [.harassment]
            default:
                break
            }
        }

        return []
    }

    private func detectPersonalInformation(_ text: String) -> [ContentCategory] {
        // App Store Guidelines 5.1: 個人情報の保護
        var violations: [ContentCategory] = []

        // 電話番号検出
        if isPhoneNumber(text) {
            violations.append(.personalInfo)
        }

        // メールアドレス検出
        if isEmailAddress(text) {
            violations.append(.personalInfo)
        }

        // 住所検出（簡易版）
        if isAddress(text) {
            violations.append(.personalInfo)
        }

        return violations
    }

    private func detectSpam(_ text: String) -> [ContentCategory] {
        // スパムパターンの検出
        let spamPatterns = [
            "今すぐクリック",
            "限定オファー",
            "簡単に稼ぐ",
            "無料で", "click here",
            "limited time", "earn money"
        ]

        let lowercaseText = text.lowercased()

        for pattern in spamPatterns {
            if lowercaseText.contains(pattern.lowercased()) {
                return [.spam]
            }
        }

        return []
    }

    private func detectHateSpeech(_ text: String) -> [ContentCategory] {
        // ヘイトスピーチの検出（基本的なパターン）
        let hateKeywords = loadHateSpeechKeywords()
        let lowercaseText = text.lowercased()

        for keyword in hateKeywords {
            if lowercaseText.contains(keyword.lowercased()) {
                return [.hate]
            }
        }

        return []
    }

    // MARK: - 画像コンテンツのモデレーション

    /// Vision Framework を使用した画像コンテンツのモデレーション
    func moderateImage(_ image: UIImage, completion: @escaping (ModerationResult) -> Void) {
        Task {
            let result = await performImageModeration(image)
            DispatchQueue.main.async {
                completion(result)
            }
        }
    }

    private func performImageModeration(_ image: UIImage) async -> ModerationResult {
        var violations: [ContentCategory] = []

        guard let cgImage = image.cgImage else {
            return createFailedModerationResult(.image)
        }

        // 1. 不適切な内容の検出
        violations.append(contentsOf: await detectInappropriateImageContent(cgImage))

        // 2. テキスト検出と分析
        violations.append(contentsOf: await detectTextInImage(cgImage))

        // 3. 暴力的内容の検出
        violations.append(contentsOf: await detectViolentContent(cgImage))

        let action = determineAction(for: violations)
        let confidence = calculateImageConfidence(for: violations)

        return ModerationResult(
            contentType: .image,
            isApproved: action == .allow,
            violations: violations,
            suggestedAction: action,
            confidence: confidence,
            originalContent: image,
            moderatedContent: action == .allow ? image : applyImageCensorship(image, violations: violations)
        )
    }

    private func detectInappropriateImageContent(_ cgImage: CGImage) async -> [ContentCategory] {
        return await withCheckedContinuation { continuation in
            let request = VNClassifyImageRequest { request, error in
                guard let results = request.results as? [VNClassificationObservation],
                      error == nil else {
                    continuation.resume(returning: [])
                    return
                }

                var violations: [ContentCategory] = []

                for result in results.prefix(5) { // 上位5件をチェック
                    if result.confidence > 0.7 {
                        if self.isInappropriateContent(result.identifier) {
                            violations.append(.inappropriate)
                        }
                        if self.isSexualContent(result.identifier) {
                            violations.append(.sexual)
                        }
                        if self.isViolentContent(result.identifier) {
                            violations.append(.violence)
                        }
                    }
                }

                continuation.resume(returning: violations)
            }

            let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
            try? handler.perform([request])
        }
    }

    private func detectTextInImage(_ cgImage: CGImage) async -> [ContentCategory] {
        return await withCheckedContinuation { continuation in
            let request = VNRecognizeTextRequest { request, error in
                guard let results = request.results as? [VNRecognizedTextObservation],
                      error == nil else {
                    continuation.resume(returning: [])
                    return
                }

                var violations: [ContentCategory] = []

                for result in results {
                    if let topCandidate = result.topCandidates(1).first {
                        let detectedText = topCandidate.string

                        // 検出されたテキストをモデレーション
                        Task {
                            let textResult = await self.performTextModeration(detectedText)
                            violations.append(contentsOf: textResult.violations)
                        }
                    }
                }

                continuation.resume(returning: violations)
            }

            request.recognitionLevel = .accurate
            request.recognitionLanguages = ["ja", "en"] // 日本語と英語

            let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
            try? handler.perform([request])
        }
    }

    private func detectViolentContent(_ cgImage: CGImage) async -> [ContentCategory] {
        // 暴力的内容の検出ロジック
        // 実際の実装では、より高度な機械学習モデルを使用
        return []
    }

    // MARK: - ユーザーレポート機能

    /// App Store Guidelines 1.2: ユーザーによるコンテンツ報告機能
    func reportContent(_ content: Any, reason: ReportReason, reportedBy userId: String, completion: @escaping (Bool) -> Void) {

        let report = ContentReport(
            contentId: generateContentId(content),
            reportedBy: userId,
            reason: reason,
            timestamp: Date(),
            status: .pending
        )

        // レポートの保存
        saveContentReport(report) { success in
            if success {
                // モデレーターに通知
                self.notifyModerators(report)

                // 自動アクションの実行
                self.performAutomaticAction(for: report, content: content)
            }

            completion(success)
        }
    }

    enum ReportReason: CaseIterable {
        case spam
        case harassment
        case hateSpeech
        case violence
        case sexualContent
        case personalInformation
        case copyrightViolation
        case other

        var localizedDescription: String {
            switch self {
            case .spam: return "スパム"
            case .harassment: return "ハラスメント"
            case .hateSpeech: return "ヘイトスピーチ"
            case .violence: return "暴力的内容"
            case .sexualContent: return "性的コンテンツ"
            case .personalInformation: return "個人情報"
            case .copyrightViolation: return "著作権侵害"
            case .other: return "その他"
            }
        }
    }

    // MARK: - コンテンツフィルタリング

    private func filterContent(_ text: String, violations: [ContentCategory]) -> String {
        var filtered = text

        for violation in violations {
            switch violation {
            case .profanity:
                filtered = censorProfanity(filtered)
            case .personalInfo:
                filtered = censorPersonalInfo(filtered)
            default:
                break
            }
        }

        return filtered
    }

    private func censorProfanity(_ text: String) -> String {
        let profanityList = loadProfanityList()
        var result = text

        for word in profanityList {
            let censored = String(repeating: "*", count: word.count)
            result = result.replacingOccurrences(of: word, with: censored, options: .caseInsensitive)
        }

        return result
    }

    private func censorPersonalInfo(_ text: String) -> String {
        var result = text

        // 電話番号をマスク
        let phoneRegex = try? NSRegularExpression(pattern: #"\b\d{3}-\d{4}-\d{4}\b"#)
        result = phoneRegex?.stringByReplacingMatches(in: result,
                                                     range: NSRange(result.startIndex..., in: result),
                                                     withTemplate: "[電話番号]") ?? result

        // メールアドレスをマスク
        let emailRegex = try? NSRegularExpression(pattern: #"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"#)
        result = emailRegex?.stringByReplacingMatches(in: result,
                                                     range: NSRange(result.startIndex..., in: result),
                                                     withTemplate: "[メールアドレス]") ?? result

        return result
    }

    private func applyImageCensorship(_ image: UIImage, violations: [ContentCategory]) -> UIImage {
        // 画像にフィルターを適用（ブラー、モザイクなど）
        guard !violations.isEmpty else { return image }

        // Core Image を使用したフィルター適用
        let context = CIContext()
        guard let ciImage = CIImage(image: image) else { return image }

        let filter = CIFilter(name: "CIGaussianBlur")
        filter?.setValue(ciImage, forKey: kCIInputImageKey)
        filter?.setValue(10.0, forKey: kCIInputRadiusKey) // ブラー強度

        guard let outputImage = filter?.outputImage,
              let cgImage = context.createCGImage(outputImage, from: ciImage.extent) else {
            return image
        }

        return UIImage(cgImage: cgImage)
    }

    // MARK: - ヘルパーメソッド

    private func setupModeration() {
        moderationEnabled = userDefaults.bool(forKey: "content_moderation_enabled")
        if !userDefaults.bool(forKey: "moderation_setup_completed") {
            // 初回セットアップ
            moderationEnabled = true
            userDefaults.set(true, forKey: "content_moderation_enabled")
            userDefaults.set(true, forKey: "moderation_setup_completed")
        }
    }

    private func determineAction(for violations: [ContentCategory]) -> ModerationAction {
        if violations.isEmpty {
            return .allow
        }

        // 重篤な違反は即座にブロック
        let severeViolations: Set<ContentCategory> = [.hate, .violence, .sexual]
        if !Set(violations).isDisjoint(with: severeViolations) {
            return .autoRemove
        }

        // 軽微な違反は警告
        let minorViolations: Set<ContentCategory> = [.spam, .profanity]
        if Set(violations).isSubset(of: minorViolations) {
            return .warn
        }

        // その他はモデレーターに報告
        return .reportToModerator
    }

    private func calculateConfidence(for violations: [ContentCategory], textLength: Int) -> Float {
        if violations.isEmpty {
            return 0.9
        }

        let baseConfidence: Float = 0.7
        let violationPenalty: Float = 0.1 * Float(violations.count)
        let lengthBonus: Float = min(0.2, Float(textLength) / 1000.0)

        return max(0.1, min(1.0, baseConfidence - violationPenalty + lengthBonus))
    }

    private func calculateImageConfidence(for violations: [ContentCategory]) -> Float {
        if violations.isEmpty {
            return 0.8
        }

        return max(0.3, 0.9 - 0.15 * Float(violations.count))
    }

    private func createFailedModerationResult(_ contentType: ContentType) -> ModerationResult {
        return ModerationResult(
            contentType: contentType,
            isApproved: false,
            violations: [.inappropriate],
            suggestedAction: .block,
            confidence: 0.1,
            originalContent: nil,
            moderatedContent: nil
        )
    }

    // MARK: - データ読み込み

    private func loadProfanityList() -> [String] {
        // 実際の実装では、外部ファイルまたはサーバーから取得
        return ["不適切な言葉1", "不適切な言葉2"] // プレースホルダー
    }

    private func loadHateSpeechKeywords() -> [String] {
        // ヘイトスピーチキーワードの読み込み
        return [] // 実装時に適切なキーワードを設定
    }

    // MARK: - 画像分析ヘルパー

    private func isInappropriateContent(_ identifier: String) -> Bool {
        let inappropriateTerms = ["explicit", "adult", "nudity"]
        return inappropriateTerms.contains { identifier.lowercased().contains($0) }
    }

    private func isSexualContent(_ identifier: String) -> Bool {
        let sexualTerms = ["sexual", "erotic", "porn"]
        return sexualTerms.contains { identifier.lowercased().contains($0) }
    }

    private func isViolentContent(_ identifier: String) -> Bool {
        let violentTerms = ["violence", "weapon", "blood"]
        return violentTerms.contains { identifier.lowercased().contains($0) }
    }

    // MARK: - 個人情報検出ヘルパー

    private func isPhoneNumber(_ text: String) -> Bool {
        let phonePattern = #"\b\d{3}-\d{4}-\d{4}\b|\b\d{11}\b"#
        return text.range(of: phonePattern, options: .regularExpression) != nil
    }

    private func isEmailAddress(_ text: String) -> Bool {
        let emailPattern = #"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"#
        return text.range(of: emailPattern, options: .regularExpression) != nil
    }

    private func isAddress(_ text: String) -> Bool {
        // 簡易的な住所検出
        let addressKeywords = ["県", "市", "区", "町", "丁目", "番地"]
        return addressKeywords.contains { text.contains($0) }
    }

    // MARK: - レポート処理

    private func generateContentId(_ content: Any) -> String {
        return UUID().uuidString
    }

    private func saveContentReport(_ report: ContentReport, completion: @escaping (Bool) -> Void) {
        // データベースまたはファイルシステムにレポートを保存
        DispatchQueue.global().async {
            // 保存処理の実装
            completion(true)
        }
    }

    private func notifyModerators(_ report: ContentReport) {
        // モデレーターへの通知実装
    }

    private func performAutomaticAction(for report: ContentReport, content: Any) {
        // レポートに基づく自動アクション
        switch report.reason {
        case .spam:
            // スパムコンテンツの自動隠蔽
            break
        case .violence, .sexualContent:
            // 重篤な内容は即座に削除
            break
        default:
            break
        }
    }
}

// MARK: - Supporting Types

struct ModerationResult {
    let contentType: ContentModerationSystem.ContentType
    let isApproved: Bool
    let violations: [ContentModerationSystem.ContentCategory]
    let suggestedAction: ContentModerationSystem.ModerationAction
    let confidence: Float
    let originalContent: Any?
    let moderatedContent: Any?
}

struct ContentReport {
    let contentId: String
    let reportedBy: String
    let reason: ContentModerationSystem.ReportReason
    let timestamp: Date
    let status: ReportStatus
}

enum ReportStatus {
    case pending
    case underReview
    case resolved
    case dismissed
}
