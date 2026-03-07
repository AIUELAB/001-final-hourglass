import XCTest
@testable import FinalHourglass

private struct TestVersionHistoryData: Codable {
    let versions: [VersionHistoryEntry]
}

final class VersionHistoryLoaderTests: XCTestCase {

    func testVersionHistoryDataDecodesCorrectly() throws {
        let json = """
        {
            "versions": [
                {
                    "version": "1.0.0",
                    "releaseDate": "2024年3月リリース",
                    "changes": ["初回リリース", "寿命予測機能"]
                }
            ]
        }
        """.data(using: .utf8)!

        let decoded = try JSONDecoder().decode(TestVersionHistoryData.self, from: json)
        XCTAssertEqual(decoded.versions.count, 1)
        XCTAssertEqual(decoded.versions[0].version, "1.0.0")
        XCTAssertEqual(decoded.versions[0].releaseDate, "2024年3月リリース")
        XCTAssertEqual(decoded.versions[0].changes, ["初回リリース", "寿命予測機能"])
    }

    func testVersionHistoryEntryIdentifiable() {
        let entry = VersionHistoryEntry(
            version: "1.0.9",
            releaseDate: "2026年2月リリース",
            changes: ["バグ修正"]
        )
        XCTAssertEqual(entry.id, "1.0.9")
    }

    func testEmptyVersionsDecodes() throws {
        let json = """
        { "versions": [] }
        """.data(using: .utf8)!

        let decoded = try JSONDecoder().decode(TestVersionHistoryData.self, from: json)
        XCTAssertTrue(decoded.versions.isEmpty)
    }

    func testMultipleVersionsDecodeInOrder() throws {
        let json = """
        {
            "versions": [
                { "version": "1.0.9", "releaseDate": "2026年2月", "changes": ["修正A"] },
                { "version": "1.0.8", "releaseDate": "2026年2月", "changes": ["機能B"] },
                { "version": "1.0.0", "releaseDate": "2024年3月", "changes": ["初回"] }
            ]
        }
        """.data(using: .utf8)!

        let decoded = try JSONDecoder().decode(TestVersionHistoryData.self, from: json)
        XCTAssertEqual(decoded.versions.count, 3)
        XCTAssertEqual(decoded.versions[0].version, "1.0.9")
        XCTAssertEqual(decoded.versions[2].version, "1.0.0")
    }

    func testDecodingFailsWhenRequiredFieldMissing() {
        let json = """
        {
            "versions": [
                { "version": "1.0.0", "releaseDate": "2024年3月" }
            ]
        }
        """.data(using: .utf8)!

        XCTAssertThrowsError(try JSONDecoder().decode(TestVersionHistoryData.self, from: json))
    }

    func testEntryWithEmptyChangesDecodes() throws {
        let json = """
        {
            "versions": [
                { "version": "1.0.0", "releaseDate": "2024年3月", "changes": [] }
            ]
        }
        """.data(using: .utf8)!

        let decoded = try JSONDecoder().decode(TestVersionHistoryData.self, from: json)
        XCTAssertTrue(decoded.versions[0].changes.isEmpty)
    }
}
