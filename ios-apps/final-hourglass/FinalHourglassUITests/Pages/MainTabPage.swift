import XCTest

/// メインタブ画面のPage Object
///
/// iPadOS 18+ では TabView が floating tab bar を使用するため、
/// XCUITest の `app.tabBars` にマッチしない。
/// ラベルテキストでボタンを検索することで iPhone/iPad 両対応する。
struct MainTabPage {
    let app: XCUIApplication

    // MARK: - Tab Elements

    var timeLimitTab: XCUIElement {
        tabButton(label: "タイムリミット")
    }

    var favoritesTab: XCUIElement {
        tabButton(label: "お気に入り")
    }

    var profileTab: XCUIElement {
        tabButton(label: "プロファイル")
    }

    var settingsTab: XCUIElement {
        tabButton(label: "設定")
    }

    var healthTab: XCUIElement {
        tabButton(label: "健康")
    }

    var aboutTab: XCUIElement {
        tabButton(label: "About")
    }

    // MARK: - Verification

    /// CI環境用タイムアウト時間（シミュレータの遅延を考慮）
    private static let ciTimeout: TimeInterval = 30

    /// タブバーが表示されているか
    var isDisplayed: Bool {
        // iPhone: 従来の UITabBar
        if app.tabBars.firstMatch.waitForExistence(timeout: 5) {
            return true
        }
        // iPad (iPadOS 18+): floating tab bar — ラベルテキストでボタンを検出
        return app.buttons["タイムリミット"].waitForExistence(timeout: Self.ciTimeout - 5)
    }

    // MARK: - Actions

    func selectTimeLimit() {
        timeLimitTab.tap()
    }

    func selectFavorites() {
        favoritesTab.tap()
    }

    func selectProfile() {
        profileTab.tap()
    }

    func selectSettings() {
        settingsTab.tap()
    }

    func selectHealth() {
        healthTab.tap()
    }

    func selectAbout() {
        aboutTab.tap()
    }

    // MARK: - Tab Selection State

    /// タブの選択状態を判定する（iPhone/iPad 両対応）
    ///
    /// iPhone: `app.tabBars.buttons` の `.isSelected` で判定
    /// iPad (iPadOS 18+): floating tab bar では `.isSelected` が常に false を返すため、
    /// タブコンテンツの `accessibilityIdentifier` の存在で判定する
    func isTabSelected(_ label: String) -> Bool {
        // iPhone: tabBars が存在する場合は .isSelected で判定
        let tabBarButton = app.tabBars.buttons[label]
        if tabBarButton.exists {
            return tabBarButton.isSelected
        }
        // iPad フォールバック: タブコンテンツの accessibilityIdentifier で判定
        let tabId = tabContentIdentifier(for: label)
        if !tabId.isEmpty {
            return app.otherElements[tabId].waitForExistence(timeout: 3)
        }
        return false
    }

    var isTimeLimitSelected: Bool { isTabSelected("タイムリミット") }
    var isFavoritesSelected: Bool { isTabSelected("お気に入り") }
    var isProfileSelected: Bool { isTabSelected("プロファイル") }
    var isSettingsSelected: Bool { isTabSelected("設定") }
    var isHealthSelected: Bool { isTabSelected("健康") }
    var isAboutSelected: Bool { isTabSelected("About") }

    // MARK: - Private

    /// タブラベルに対応するコンテンツビューの accessibilityIdentifier を返す
    private func tabContentIdentifier(for label: String) -> String {
        switch label {
        case "タイムリミット": return "tab_timelimit"
        case "お気に入り": return "tab_favorites"
        case "プロファイル": return "tab_profile"
        case "設定": return "tab_settings"
        case "健康": return "tab_health"
        case "About": return "tab_about"
        default:
            XCTFail("未知のタブラベル '\(label)' にはaccessibilityIdentifierが未定義")
            return ""
        }
    }

    /// iPhone の tabBars.buttons と iPad の floating tab bar 両方に対応するタブ検索
    private func tabButton(label: String) -> XCUIElement {
        let tabBarButton = app.tabBars.buttons[label]
        if tabBarButton.waitForExistence(timeout: 3) {
            return tabBarButton
        }
        // iPadOS 18+ floating tab bar: ボタンが2重ネストのため firstMatch で取得
        return app.buttons[label].firstMatch
    }
}
