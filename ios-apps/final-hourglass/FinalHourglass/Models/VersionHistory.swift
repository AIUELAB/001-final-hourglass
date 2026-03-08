import Foundation

struct VersionHistoryEntry: Codable, Identifiable {
    let version: String
    let releaseDate: String
    let changes: [String]

    var id: String { version }
}

enum VersionHistoryLoader {
    private struct VersionHistoryData: Codable {
        let versions: [VersionHistoryEntry]
    }

    static func load(from bundle: Bundle = .main) -> [VersionHistoryEntry] {
        guard let url = bundle.url(forResource: "version_history", withExtension: "json") else {
            #if DEBUG
            assertionFailure("version_history.json がバンドルに見つかりません")
            #endif
            return []
        }

        let data: Data
        do {
            data = try Data(contentsOf: url)
        } catch {
            #if DEBUG
            assertionFailure("version_history.json の読み込みに失敗: \(error)")
            #endif
            return []
        }

        do {
            return try JSONDecoder().decode(VersionHistoryData.self, from: data).versions
        } catch {
            #if DEBUG
            assertionFailure("version_history.json のデコードに失敗: \(error)")
            #endif
            return []
        }
    }
}
