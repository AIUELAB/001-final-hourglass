import XCTest
@testable import FinalHourglass

final class ContentFilterManagerTests: XCTestCase {

    var sut: ContentFilterManager!

    override func setUp() {
        super.setUp()
        // テストごとにUserDefaultsをクリアしてから生成
        UserDefaults.standard.removeObject(forKey: "contentFilter")
        UserDefaults.standard.removeObject(forKey: "hasSeenContentWarning")
        UserDefaults.standard.removeObject(forKey: "userAge")
        sut = ContentFilterManager()
    }

    override func tearDown() {
        UserDefaults.standard.removeObject(forKey: "contentFilter")
        UserDefaults.standard.removeObject(forKey: "hasSeenContentWarning")
        UserDefaults.standard.removeObject(forKey: "userAge")
        sut = nil
        super.tearDown()
    }

    // MARK: - ContentFilter Enum: displayName

    func testDisplayName_allCases() {
        XCTAssertEqual(ContentFilter.all.displayName, "すべて表示")
        XCTAssertEqual(ContentFilter.light.displayName, "光のエピソード")
        XCTAssertEqual(ContentFilter.shadow.displayName, "影のエピソード")
    }

    // MARK: - ContentFilter Enum: icon

    func testIcon_allCases() {
        XCTAssertEqual(ContentFilter.all.icon, "⚡")
        XCTAssertEqual(ContentFilter.light.icon, "☀️")
        XCTAssertEqual(ContentFilter.shadow.icon, "🌙")
    }

    // MARK: - ContentFilter Enum: description

    func testDescription_allCases() {
        XCTAssertTrue(ContentFilter.all.description.contains("偉人も独裁者も"))
        XCTAssertTrue(ContentFilter.light.description.contains("偉人"))
        XCTAssertTrue(ContentFilter.shadow.description.contains("独裁者"))
    }

    // MARK: - changeFilter

    func testChangeFilter_lightToAll_succeeds() {
        XCTAssertEqual(sut.currentFilter, .light)
        sut.changeFilter(to: .all)
        XCTAssertEqual(sut.currentFilter, .all)
    }

    func testChangeFilter_toShadowWithoutWarning_doesNotChange() {
        XCTAssertFalse(sut.hasSeenWarning)
        sut.changeFilter(to: .shadow)
        XCTAssertNotEqual(sut.currentFilter, .shadow)
    }

    func testChangeFilter_toShadowAfterWarning_succeeds() {
        sut.confirmWarning()
        sut.changeFilter(to: .shadow)
        XCTAssertEqual(sut.currentFilter, .shadow)
    }

    // MARK: - confirmWarning

    func testConfirmWarning_setsFlag() {
        XCTAssertFalse(sut.hasSeenWarning)
        sut.confirmWarning()
        XCTAssertTrue(sut.hasSeenWarning)
    }

    func testConfirmWarning_persistsToUserDefaults() {
        sut.confirmWarning()
        let persisted = UserDefaults.standard.bool(forKey: "hasSeenContentWarning")
        XCTAssertTrue(persisted)
    }

    // MARK: - setUserAge

    func testSetUserAge_setsValue() {
        sut.setUserAge(25)
        XCTAssertEqual(sut.userAge, 25)
    }

    func testSetUserAge_persistsToUserDefaults() {
        sut.setUserAge(30)
        let persisted = UserDefaults.standard.integer(forKey: "userAge")
        XCTAssertEqual(persisted, 30)
    }

    // MARK: - canAccessShadowContent

    func testCanAccessShadowContent_age16_returnsFalse() {
        sut.setUserAge(16)
        XCTAssertFalse(sut.canAccessShadowContent())
    }

    func testCanAccessShadowContent_age17_returnsTrue() {
        sut.setUserAge(17)
        XCTAssertTrue(sut.canAccessShadowContent())
    }

    func testCanAccessShadowContent_ageNil_returnsFalse() {
        XCTAssertNil(sut.userAge)
        XCTAssertFalse(sut.canAccessShadowContent())
    }
}
