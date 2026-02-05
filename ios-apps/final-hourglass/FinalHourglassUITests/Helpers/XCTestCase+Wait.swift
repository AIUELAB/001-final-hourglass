import XCTest

extension XCTestCase {
    /// CI環境用のデフォルトタイムアウト（シミュレータの遅延を考慮）
    private static let ciDefaultTimeout: TimeInterval = 30

    /// 要素が表示されるまで待機（CI環境対応で30秒）
    @discardableResult
    func waitForElement(_ element: XCUIElement, timeout: TimeInterval = 30) -> Bool {
        return element.waitForExistence(timeout: timeout)
    }

    /// 要素が消えるまで待機（CI環境対応で30秒）
    @discardableResult
    func waitForElementToDisappear(_ element: XCUIElement, timeout: TimeInterval = 30) -> Bool {
        let predicate = NSPredicate(format: "exists == false")
        let expectation = XCTNSPredicateExpectation(predicate: predicate, object: element)
        let result = XCTWaiter.wait(for: [expectation], timeout: timeout)
        return result == .completed
    }
}
