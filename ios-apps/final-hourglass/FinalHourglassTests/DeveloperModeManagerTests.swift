import XCTest
@testable import FinalHourglass

final class DeveloperModeManagerTests: XCTestCase {

    var sut: DeveloperModeManager!

    override func setUp() {
        super.setUp()
        UserDefaults.standard.removeObject(forKey: "isDeveloperMode")
        sut = DeveloperModeManager()
    }

    override func tearDown() {
        sut = nil
        UserDefaults.standard.removeObject(forKey: "isDeveloperMode")
        super.tearDown()
    }

    // MARK: - 初期化テスト

    func testInit_defaultIsFalse() {
        XCTAssertFalse(sut.isDeveloperMode)
    }

    func testInit_restoresTrueFromUserDefaults() {
        UserDefaults.standard.isDeveloperMode = true
        let manager = DeveloperModeManager()
        XCTAssertTrue(manager.isDeveloperMode)
    }

    // MARK: - toggleDeveloperMode テスト

    func testToggle_whenOn_turnOff() {
        sut.isDeveloperMode = true
        sut.toggleDeveloperMode()
        XCTAssertFalse(sut.isDeveloperMode)
    }

    func testToggle_whenOff_showsPasswordPrompt() {
        sut.toggleDeveloperMode()
        XCTAssertTrue(sut.showPasswordPrompt)
        XCTAssertEqual(sut.passwordInput, "")
    }

    // MARK: - validatePassword テスト

    func testValidatePassword_correctPassword_enablesDeveloperMode() {
        sut.passwordInput = "dev2024"
        sut.showPasswordPrompt = true
        sut.validatePassword()
        XCTAssertTrue(sut.isDeveloperMode)
        XCTAssertFalse(sut.showPasswordPrompt)
        XCTAssertEqual(sut.passwordInput, "")
    }

    func testValidatePassword_wrongPassword_showsAlert() {
        sut.passwordInput = "wrong"
        sut.validatePassword()
        XCTAssertTrue(sut.wrongPasswordAlert)
        XCTAssertEqual(sut.passwordInput, "")
        XCTAssertFalse(sut.isDeveloperMode)
    }

    func testValidatePassword_emptyPassword_showsAlert() {
        sut.passwordInput = ""
        sut.validatePassword()
        XCTAssertTrue(sut.wrongPasswordAlert)
        XCTAssertEqual(sut.passwordInput, "")
        XCTAssertFalse(sut.isDeveloperMode)
    }

    // MARK: - 永続化テスト

    func testPersistence_isDeveloperModeChangeSavedToUserDefaults() {
        sut.isDeveloperMode = true
        XCTAssertTrue(UserDefaults.standard.isDeveloperMode)

        sut.isDeveloperMode = false
        XCTAssertFalse(UserDefaults.standard.isDeveloperMode)
    }

    func testPersistence_restoresFromUserDefaults() {
        sut.isDeveloperMode = true
        let newManager = DeveloperModeManager()
        XCTAssertTrue(newManager.isDeveloperMode)
    }

    // MARK: - 状態遷移テスト

    func testFullFlow_toggleThenValidateWithCorrectPassword() {
        // 初期状態: OFF
        XCTAssertFalse(sut.isDeveloperMode)

        // toggle → パスワードプロンプト表示
        sut.toggleDeveloperMode()
        XCTAssertTrue(sut.showPasswordPrompt)
        XCTAssertFalse(sut.isDeveloperMode)

        // 正しいパスワード入力 → ON
        sut.passwordInput = "dev2024"
        sut.validatePassword()
        XCTAssertTrue(sut.isDeveloperMode)
        XCTAssertFalse(sut.showPasswordPrompt)
        XCTAssertEqual(sut.passwordInput, "")
        XCTAssertTrue(UserDefaults.standard.isDeveloperMode)
    }
}
