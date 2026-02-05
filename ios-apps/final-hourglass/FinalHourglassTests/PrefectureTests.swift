import XCTest
@testable import FinalHourglass

final class PrefectureTests: XCTestCase {

    // MARK: - Prefecture Count Tests

    func testAllPrefecturesCount() {
        // 日本の都道府県は47
        XCTAssertEqual(Prefecture.allCases.count, 47)
    }

    // MARK: - Prefecture Name Tests

    func testTokyoName() {
        XCTAssertEqual(Prefecture.tokyo.name, "東京都")
    }

    func testOsakaName() {
        XCTAssertEqual(Prefecture.osaka.name, "大阪府")
    }

    func testHokkaidoName() {
        XCTAssertEqual(Prefecture.hokkaido.name, "北海道")
    }

    // MARK: - Prefecture Code Tests

    func testTokyoCode() {
        XCTAssertEqual(Prefecture.tokyo.code, "13")
    }

    func testHokkaidoCode() {
        XCTAssertEqual(Prefecture.hokkaido.code, "01")
    }

    func testOkinawaCode() {
        XCTAssertEqual(Prefecture.okinawa.code, "47")
    }

    // MARK: - Prefecture From Code Tests

    func testFromCodeTokyo() {
        let prefecture = Prefecture.fromCode("13")
        XCTAssertEqual(prefecture, .tokyo)
    }

    func testFromCodeInvalid() {
        let prefecture = Prefecture.fromCode("99")
        XCTAssertNil(prefecture)
    }

    // MARK: - Region Tests

    func testTokyoRegion() {
        XCTAssertEqual(Prefecture.tokyo.region, .kanto)
    }

    func testOsakaRegion() {
        XCTAssertEqual(Prefecture.osaka.region, .kinki)
    }

    func testHokkaidoRegion() {
        XCTAssertEqual(Prefecture.hokkaido.region, .hokkaido)
    }

    func testOkinawaRegion() {
        XCTAssertEqual(Prefecture.okinawa.region, .kyushu)
    }

    // MARK: - Region Count Tests

    func testAllRegionsCount() {
        XCTAssertEqual(Region.allCases.count, 8)
    }
}
