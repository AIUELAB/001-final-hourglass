import XCTest

/// エピソード画面のPage Object
struct EpisodePage {
    let app: XCUIApplication

    // MARK: - Elements

    var episodeList: XCUIElement {
        app.collectionViews.firstMatch
    }

    var episodeDetailView: XCUIElement {
        app.scrollViews["エピソード詳細"].firstMatch
    }

    var favoriteButton: XCUIElement {
        app.buttons["お気に入り"].firstMatch
    }

    var episodeTitle: XCUIElement {
        app.staticTexts["エピソードタイトル"].firstMatch
    }

    // MARK: - Verification

    /// エピソード画面が表示されているか
    var isDisplayed: Bool {
        episodeList.waitForExistence(timeout: 10)
    }

    // MARK: - Actions

    func selectFirstEpisode() {
        let firstCell = episodeList.cells.firstMatch
        firstCell.tap()
    }

    func toggleFavorite() {
        favoriteButton.tap()
    }
}
