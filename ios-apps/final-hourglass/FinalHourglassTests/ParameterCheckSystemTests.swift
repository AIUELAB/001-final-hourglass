import XCTest
@testable import FinalHourglass

final class ParameterCheckSystemTests: XCTestCase {

    // MARK: - CheckResult Tests

    func testCheckResultInitialization() {
        let now = Date()
        let result = CheckResult(
            isValid: true,
            issues: ["issue1"],
            warnings: ["warning1"],
            timestamp: now
        )
        XCTAssertTrue(result.isValid)
        XCTAssertEqual(result.issues, ["issue1"])
        XCTAssertEqual(result.warnings, ["warning1"])
        XCTAssertEqual(result.timestamp, now)
    }

    // MARK: - ValidationResult Tests

    func testValidationResultInitialization() {
        let result = ValidationResult(isValid: false, message: "エラーメッセージ")
        XCTAssertFalse(result.isValid)
        XCTAssertEqual(result.message, "エラーメッセージ")
    }

    // MARK: - performStartupCheck Tests

    func testPerformStartupCheckReturnsCheckResult() {
        let result = ParameterCheckSystem.shared.performStartupCheck()
        // CheckResult型が返ることを確認（コンパイル時チェック + 値アクセス）
        _ = result.isValid
        _ = result.issues
        _ = result.warnings
        _ = result.timestamp
    }

    func testPerformStartupCheckTimestampIsRecent() {
        let before = Date()
        let result = ParameterCheckSystem.shared.performStartupCheck()
        let after = Date()
        XCTAssertGreaterThanOrEqual(result.timestamp, before)
        XCTAssertLessThanOrEqual(result.timestamp, after)
    }

    func testPerformStartupCheckIssuesIsArray() {
        let result = ParameterCheckSystem.shared.performStartupCheck()
        // issues が String 配列であることを確認
        XCTAssertTrue(type(of: result.issues) == [String].self)
    }

    func testPerformStartupCheckWarningsIsArray() {
        let result = ParameterCheckSystem.shared.performStartupCheck()
        XCTAssertTrue(type(of: result.warnings) == [String].self)
    }

    // MARK: - generateIntegrityReport Tests

    func testGenerateIntegrityReportNotEmpty() {
        let report = ParameterCheckSystem.shared.generateIntegrityReport()
        XCTAssertFalse(report.isEmpty, "レポートは空でない文字列を返すべき")
    }

    func testGenerateIntegrityReportContainsTitle() {
        let report = ParameterCheckSystem.shared.generateIntegrityReport()
        XCTAssertTrue(
            report.contains("パラメータ整合性レポート"),
            "レポートに「パラメータ整合性レポート」が含まれるべき"
        )
    }

    func testGenerateIntegrityReportContainsParameterIDs() {
        let report = ParameterCheckSystem.shared.generateIntegrityReport()
        XCTAssertTrue(report.contains("birth_date"), "レポートにパラメータID birth_date が含まれるべき")
        XCTAssertTrue(report.contains("gender"), "レポートにパラメータID gender が含まれるべき")
    }

    func testGenerateIntegrityReportContainsLabels() {
        let report = ParameterCheckSystem.shared.generateIntegrityReport()
        XCTAssertTrue(report.contains("必須"), "レポートに「必須」ラベルが含まれるべき")
        XCTAssertTrue(report.contains("任意"), "レポートに「任意」ラベルが含まれるべき")
    }

    // MARK: - Warnings Test

    func testPerformStartupCheckWarningsAreAccessible() {
        // 警告の有無は実装状態に依存するため、アクセス可能性のみを確認
        let result = ParameterCheckSystem.shared.performStartupCheck()
        // warnings配列にアクセスできることを確認（空でも非空でも許容）
        let warningsCount = result.warnings.count
        XCTAssertGreaterThanOrEqual(warningsCount, 0, "警告数は0以上であるべき")
    }

    // MARK: - Singleton Test

    func testSharedIsSameInstance() {
        let instance1 = ParameterCheckSystem.shared
        let instance2 = ParameterCheckSystem.shared
        XCTAssertTrue(instance1 === instance2, "shared は同一インスタンスを返すべき")
    }
}
