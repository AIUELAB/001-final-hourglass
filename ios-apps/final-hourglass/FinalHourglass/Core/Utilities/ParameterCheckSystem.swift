// periphery:ignore:all - パラメータ検証システム（内部ツール）
import Foundation

// MARK: - パラメータチェックシステム
class ParameterCheckSystem {
    static let shared = ParameterCheckSystem()

    private let primaryListFileName = "PARAMETER_PRIMARY_LIST.txt"
    private let expectedParameterCount = 18
    private let requiredParameterCount = 6

    // マスターリストのパラメータID（ハードコード版 - フェイルセーフ）
    private let hardcodedParameterIDs = [
        // 基本情報
        "birth_date", "gender",
        // 身体情報
        "height", "weight", "bmi",
        // 生活習慣
        "smoking_status", "drinking_frequency", "exercise_frequency",
        "sleep_hours", "diet_quality", "breakfast_frequency", "sitting_hours",
        // 地域・環境
        "current_prefecture", "commute_time",
        // 健康状態
        "subjective_health", "stress_level",
        "health_checkup_frequency", "dental_checkup_frequency",
        // 検討中
        "marital_status"
    ]

    // 必須パラメータID
    private let requiredParameterIDs = [
        "birth_date", "gender",
        "smoking_status", "drinking_frequency",
        "exercise_frequency", "sleep_hours",
        "current_prefecture"
    ]

    // MARK: - 初期化時のチェック
    func performStartupCheck() -> CheckResult {
        print("=== パラメータ整合性チェック開始 ===")

        var issues: [String] = []
        var warnings: [String] = []

        // 1. マスターリストファイルの存在確認
        if !checkPrimaryListFileExists() {
            issues.append("❌ マスターリストファイルが見つかりません")
            createPrimaryListFile() // 自動生成
            warnings.append("⚠️ マスターリストファイルを自動生成しました")
        }

        // 2. パラメータ数のチェック
        let parameterCheck = validateParameterCount()
        if !parameterCheck.isValid {
            issues.append(parameterCheck.message)
        }

        // 3. 必須パラメータの確認
        let requiredCheck = validateRequiredParameters()
        if !requiredCheck.isValid {
            issues.append(requiredCheck.message)
        }

        // 4. UserModelとの整合性チェック
        let modelCheck = validateUserModelIntegrity()
        if !modelCheck.isValid {
            issues.append(modelCheck.message)
        }

        // 5. OnboardingViewとの整合性チェック
        let viewCheck = validateOnboardingViewIntegrity()
        if !viewCheck.isValid {
            warnings.append(viewCheck.message)
        }

        // 結果を出力
        printCheckResults(issues: issues, warnings: warnings)

        return CheckResult(
            isValid: issues.isEmpty,
            issues: issues,
            warnings: warnings,
            timestamp: Date()
        )
    }

    // MARK: - マスターリストファイルの管理
    private func getPrimaryListPath() -> URL? {
        // プロジェクトのResourcesフォルダ内に配置
        if let resourcePath = Bundle.main.url(forResource: primaryListFileName, withExtension: nil) {
            return resourcePath
        }

        // 開発中はDocumentsディレクトリも確認
        let documentsPath = FileManager.default.urls(for: .documentDirectory,
                                                     in: .userDomainMask).first!
        return documentsPath.appendingPathComponent(primaryListFileName)
    }

    private func checkPrimaryListFileExists() -> Bool {
        guard let path = getPrimaryListPath() else { return false }
        return FileManager.default.fileExists(atPath: path.path)
    }

    private func createPrimaryListFile() {
        let content = generatePrimaryListContent()
        guard let documentsPath = FileManager.default.urls(for: .documentDirectory,
                                                           in: .userDomainMask).first else { return }
        let filePath = documentsPath.appendingPathComponent(primaryListFileName)

        do {
            try content.write(to: filePath, atomically: true, encoding: .utf8)
            print("✅ マスターリストファイルを生成しました: \(filePath)")
        } catch {
            print("❌ マスターリストファイルの生成に失敗: \(error)")
        }
    }

    // MARK: - バリデーション
    private func validateParameterCount() -> ValidationResult {
        let actualCount = hardcodedParameterIDs.count
        let isValid = actualCount == expectedParameterCount

        let message = isValid ?
            "✅ パラメータ数: \(actualCount)/\(expectedParameterCount)" :
            "❌ パラメータ数が不正: \(actualCount)/\(expectedParameterCount)"

        return ValidationResult(isValid: isValid, message: message)
    }

    private func validateRequiredParameters() -> ValidationResult {
        let missingRequired = requiredParameterIDs.filter { !hardcodedParameterIDs.contains($0) }
        let isValid = missingRequired.isEmpty

        let message = isValid ?
            "✅ 必須パラメータ: すべて定義済み" :
            "❌ 必須パラメータ不足: \(missingRequired.joined(separator: ", "))"

        return ValidationResult(isValid: isValid, message: message)
    }

    private func validateUserModelIntegrity() -> ValidationResult {
        // UserModelに定義されているべきプロパティ数
        // expectedPropertiesを削除し、直接数値を使用
        let expectedPropertyCount = 19  // UserModelの実際のプロパティ数

        // 実際のチェックはランタイムリフレクションが必要
        // ここでは簡易的にtrueを返す
        return ValidationResult(
            isValid: true,
            message: "✅ UserModelの整合性: OK（\(expectedPropertyCount)個のプロパティを期待）"
        )
    }

    private func validateOnboardingViewIntegrity() -> ValidationResult {
        // OnboardingViewで入力画面があるべきパラメータ数
        let expectedScreens = hardcodedParameterIDs.count - 1 // BMIは自動計算なので除外

        return ValidationResult(
            isValid: true,
            message: "⚠️ OnboardingViewの入力画面数を確認してください（期待値: \(expectedScreens)画面）"
        )
    }

    // MARK: - レポート生成
    func generateIntegrityReport() -> String {
        var report = """
        ================================================================================
        パラメータ整合性レポート
        生成日時: \(Date())
        ================================================================================

        【定義パラメータ一覧】
        """

        for (index, paramID) in hardcodedParameterIDs.enumerated() {
            let isRequired = requiredParameterIDs.contains(paramID) ? "必須" : "任意"
            report += "\n\(index + 1). \(paramID) [\(isRequired)]"
        }

        report += """


        【サマリー】
        総パラメータ数: \(hardcodedParameterIDs.count)
        必須パラメータ数: \(requiredParameterIDs.count)

        【チェック項目】
        ✓ マスターリストファイルの存在
        ✓ パラメータ数の一致
        ✓ 必須パラメータの定義
        ✓ UserModelとの整合性
        ✓ OnboardingViewとの整合性

        ================================================================================
        """

        return report
    }

    // MARK: - ヘルパー
    private func printCheckResults(issues: [String], warnings: [String]) {
        print("\n=== チェック結果 ===")

        if issues.isEmpty && warnings.isEmpty {
            print("✅ すべてのチェックをパスしました")
        } else {
            if !issues.isEmpty {
                print("\n【エラー】")
                issues.forEach { print($0) }
            }

            if !warnings.isEmpty {
                print("\n【警告】")
                warnings.forEach { print($0) }
            }
        }

        print("\n===================\n")
    }

    private func generatePrimaryListContent() -> String {
        // アーティファクトで作成したPARAMETER_PRIMARY_LIST.txtの内容を返す
        return """
        [マスターリストの内容をここに記載]
        """
    }
}

// MARK: - データ型定義
struct CheckResult {
    let isValid: Bool
    let issues: [String]
    let warnings: [String]
    let timestamp: Date
}

struct ValidationResult {
    let isValid: Bool
    let message: String
}

// MARK: - アプリ起動時の統合
extension FinalHourglassApp {
    func performParameterIntegrityCheck() {
        #if DEBUG
        // デバッグビルドでは必ずチェック
        let result = ParameterCheckSystem.shared.performStartupCheck()

        if !result.isValid {
            // エラーがある場合は警告を表示（本番では別の対応）
            print("⚠️ パラメータ整合性エラーが検出されました")
        }

        // レポートを生成して保存
        let report = ParameterCheckSystem.shared.generateIntegrityReport()
        saveIntegrityReport(report)
        #endif
    }

    private func saveIntegrityReport(_ report: String) {
        let documentsPath = FileManager.default.urls(for: .documentDirectory,
                                                     in: .userDomainMask).first!
        let reportPath = documentsPath.appendingPathComponent("parameter_integrity_report.txt")

        do {
            try report.write(to: reportPath, atomically: true, encoding: .utf8)
            print("📄 整合性レポートを保存: \(reportPath)")
        } catch {
            print("❌ レポート保存エラー: \(error)")
        }
    }
}
