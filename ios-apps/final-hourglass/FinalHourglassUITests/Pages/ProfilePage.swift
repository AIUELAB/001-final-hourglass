import XCTest

/// プロフィール画面のPage Object
struct ProfilePage {
    let app: XCUIApplication

    /// CI環境用のタイムアウト時間
    private static let ciTimeout: TimeInterval = 30

    // MARK: - Elements

    var editButton: XCUIElement {
        app.buttons["profile_edit_button"]
    }

    var basicInfoSection: XCUIElement {
        app.otherElements["profile_section_basic"]
    }

    var navigationTitle: XCUIElement {
        app.navigationBars["プロフィール"]
    }

    // MARK: - Verification

    var isDisplayed: Bool {
        // まずナビゲーションバーを確認、なければプロファイルタブが選択されているか確認
        let navBarExists = navigationTitle.waitForExistence(timeout: Self.ciTimeout)
        if navBarExists { return true }

        // フォールバック: プロファイルタブが選択されているか確認
        let profileTab = app.tabBars.buttons["プロファイル"]
        return profileTab.exists && profileTab.isSelected
    }

    // MARK: - Actions

    func tapEdit() {
        editButton.tap()
    }
}
