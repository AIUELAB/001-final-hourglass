import XCTest

/// 健康情報入力画面のPage Object
struct HealthInputPage {
    let app: XCUIApplication

    // MARK: - Elements

    var heightField: XCUIElement {
        app.textFields["身長"].firstMatch
    }

    var weightField: XCUIElement {
        app.textFields["体重"].firstMatch
    }

    var saveButton: XCUIElement {
        app.buttons["保存"].firstMatch
    }

    var bmiDisplay: XCUIElement {
        app.staticTexts["BMI"].firstMatch
    }

    // MARK: - Verification

    /// 健康情報入力画面が表示されているか
    var isDisplayed: Bool {
        saveButton.waitForExistence(timeout: 10)
    }

    // MARK: - Actions

    func enterHeight(_ value: String) {
        heightField.tap()
        heightField.clearAndTypeText(value)
    }

    func enterWeight(_ value: String) {
        weightField.tap()
        weightField.clearAndTypeText(value)
    }

    func tapSave() {
        saveButton.tap()
    }
}

// MARK: - XCUIElement Helper

private extension XCUIElement {
    func clearAndTypeText(_ text: String) {
        guard let currentValue = value as? String, !currentValue.isEmpty else {
            typeText(text)
            return
        }
        let deleteString = String(repeating: XCUIKeyboardKey.delete.rawValue, count: currentValue.count)
        typeText(deleteString)
        typeText(text)
    }
}
