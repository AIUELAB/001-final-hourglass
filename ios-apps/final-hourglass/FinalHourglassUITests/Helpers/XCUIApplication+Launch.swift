import XCTest

extension XCUIApplication {
    /// CI環境用のより長いタイムアウト時間
    private static let ciTimeout: TimeInterval = 30

    /// UIテスト用にアプリを起動（状態リセット + アニメーション無効化）
    func launchForTesting() {
        launchArguments = [
            "-UITest_ResetState",
            "-UITest_DisableAnimations"
        ]
        launch()
        // アプリ起動後に安定するまで待機
        waitForAppToBeReady()
    }

    /// オンボーディング完了済みの状態で起動
    func launchWithOnboardingComplete() {
        launchArguments = [
            "-UITest_ResetState",
            "-UITest_SkipOnboarding",
            "-UITest_DisableAnimations"
        ]
        launch()
        // アプリ起動後に安定するまで待機
        waitForAppToBeReady()
    }

    /// アプリが起動完了するまで待機
    private func waitForAppToBeReady() {
        // アプリの状態が安定するまで短い待機
        _ = self.wait(for: .runningForeground, timeout: Self.ciTimeout)

        // 追加の安定化待機（CI環境でのシミュレータレイテンシ対応）
        Thread.sleep(forTimeInterval: 2.0)
    }
}
