import XCTest

/// オンボーディング画面のPage Object
struct OnboardingPage {
    let app: XCUIApplication

    // MARK: - CI環境用タイムアウト
    private static let ciTimeout: TimeInterval = 30

    // MARK: - Elements

    var openDoorButton: XCUIElement {
        // accessibilityIdentifierで検索
        let identifierButton = app.buttons["onboarding_open_door"]
        if identifierButton.exists {
            return identifierButton
        }
        // フォールバック: ラベルで検索
        return app.buttons["扉を開く"].firstMatch
    }

    /// 扉を開くボタンが表示されるまで待機
    var openDoorButtonExists: Bool {
        let identifierButton = app.buttons["onboarding_open_door"]
        if identifierButton.waitForExistence(timeout: Self.ciTimeout) {
            return true
        }
        // フォールバック
        return app.buttons["扉を開く"].waitForExistence(timeout: 5)
    }

    func stepView(for step: Int) -> XCUIElement {
        app.otherElements["onboarding_step_\(step)"]
    }

    // MARK: - Actions

    /// 扉を開いてオンボーディングを開始
    func openDoor() {
        openDoorButton.tap()
    }

    /// 「次へ」ボタンをタップして次のステップへ
    func tapNext() {
        // OnboardingStepViewの「次へ」ボタンを探す
        let nextButton = app.buttons.matching(NSPredicate(format: "label CONTAINS '次'")).firstMatch
        if nextButton.waitForExistence(timeout: 5) {
            nextButton.tap()
        }
    }

    /// 選択肢ボタンをタップ（性別、喫煙、飲酒等の選択式入力）
    func tapOption(containing text: String) {
        let button = app.buttons.matching(NSPredicate(format: "label CONTAINS %@", text)).firstMatch
        if button.waitForExistence(timeout: 5) {
            button.tap()
        }
    }

    /// 都道府県を選択（ピッカーから東京都を選択）
    func selectPrefecture() {
        // 「都道府県を選択」または「変更する」ボタンをタップしてピッカーを開く
        let selectButton = app.buttons.matching(NSPredicate(format: "label CONTAINS '都道府県' OR label CONTAINS '変更'")).firstMatch
        if selectButton.waitForExistence(timeout: 5) {
            selectButton.tap()

            // ピッカーが表示されるのを待つ
            sleep(1)

            // 「東京都」を選択
            let tokyo = app.staticTexts["東京都"].firstMatch
            if tokyo.waitForExistence(timeout: 5) {
                tokyo.tap()

                // シートを閉じるボタン（完了または×）をタップ
                let doneButton = app.buttons.matching(NSPredicate(format: "label CONTAINS '完了' OR label CONTAINS '決定'")).firstMatch
                if doneButton.waitForExistence(timeout: 3) {
                    doneButton.tap()
                } else {
                    // スワイプダウンでシートを閉じる
                    app.swipeDown()
                }
            }
        }
    }

    /// 全16ステップを通過する（デフォルト選択で進行）
    func completeAllSteps() {
        // Step 0: 扉を開く
        openDoor()

        // Step 1: 生年月日（デフォルト値で次へ）
        tapNext()

        // Step 2: 性別（男性を選択）
        tapOption(containing: "男性")

        // Step 3: 身長（デフォルト値で次へ）
        tapNext()

        // Step 4: 体重（デフォルト値で次へ）
        tapNext()

        // Step 5: 喫煙（最初の選択肢）
        tapOption(containing: "吸わない")

        // Step 6: 飲酒（最初の選択肢）
        tapOption(containing: "飲まない")

        // Step 7: 運動（最初の選択肢）
        tapOption(containing: "まったくしない")

        // Step 8: ストレス（最初の選択肢）
        tapOption(containing: "低い")

        // Step 9: 睡眠（デフォルト値で次へ）
        tapNext()

        // Step 10: 食生活（複数選択式 + 次へボタン）
        tapOption(containing: "バランス")
        tapNext()

        // Step 11: 朝食（選択で自動次へ）
        tapOption(containing: "毎日")

        // Step 12: 座位時間（選択で自動次へ）
        tapOption(containing: "3時間")

        // Step 13: 都道府県（ピッカー選択 + 次へ）
        selectPrefecture()
        tapNext()

        // Step 14: 健康診断（2段階: 健康診断 → 歯科検診）
        tapOption(containing: "年1回")
        tapOption(containing: "年1回")

        // Step 15: 婚姻状況（未婚で自動完了）
        tapOption(containing: "未婚")
    }
}
