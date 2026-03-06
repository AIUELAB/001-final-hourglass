import MessageUI
import XCTest
@testable import FinalHourglass

final class FeedbackFormViewTests: XCTestCase {

    // MARK: - Helper

    private func makeSUT(
        onComplete: ((MFMailComposeResult, Error?) -> Void)? = nil
    ) -> FeedbackMailComposerView {
        FeedbackMailComposerView(
            recipients: ["test@example.com"],
            subject: "Test Subject",
            messageBody: "Test Body",
            onComplete: onComplete
        )
    }

    // MARK: - onComplete Callback Tests

    func testOnComplete_sentResult_callsCallbackWithSent() {
        var capturedResult: MFMailComposeResult?
        var capturedError: Error?
        let sut = makeSUT { result, error in
            capturedResult = result
            capturedError = error
        }
        let coordinator = sut.makeCoordinator()
        let controller = MFMailComposeViewController()

        coordinator.mailComposeController(controller, didFinishWith: .sent, error: nil)

        XCTAssertEqual(capturedResult, .sent)
        XCTAssertNil(capturedError)
    }

    func testOnComplete_failedResult_callsCallbackWithFailed() {
        var capturedResult: MFMailComposeResult?
        var capturedError: Error?
        let sut = makeSUT { result, error in
            capturedResult = result
            capturedError = error
        }
        let coordinator = sut.makeCoordinator()
        let controller = MFMailComposeViewController()

        coordinator.mailComposeController(controller, didFinishWith: .failed, error: nil)

        XCTAssertEqual(capturedResult, .failed)
        XCTAssertNil(capturedError)
    }

    func testOnComplete_savedResult_callsCallbackWithSaved() {
        var capturedResult: MFMailComposeResult?
        let sut = makeSUT { result, _ in
            capturedResult = result
        }
        let coordinator = sut.makeCoordinator()
        let controller = MFMailComposeViewController()

        coordinator.mailComposeController(controller, didFinishWith: .saved, error: nil)

        XCTAssertEqual(capturedResult, .saved)
    }

    func testOnComplete_cancelledResult_callsCallbackWithCancelled() {
        var capturedResult: MFMailComposeResult?
        let sut = makeSUT { result, _ in
            capturedResult = result
        }
        let coordinator = sut.makeCoordinator()
        let controller = MFMailComposeViewController()

        coordinator.mailComposeController(controller, didFinishWith: .cancelled, error: nil)

        XCTAssertEqual(capturedResult, .cancelled)
    }

    func testOnComplete_withError_callsCallbackWithError() {
        var capturedResult: MFMailComposeResult?
        var capturedError: Error?
        let testError = NSError(domain: "TestDomain", code: 42)
        let sut = makeSUT { result, error in
            capturedResult = result
            capturedError = error
        }
        let coordinator = sut.makeCoordinator()
        let controller = MFMailComposeViewController()

        coordinator.mailComposeController(controller, didFinishWith: .failed, error: testError)

        XCTAssertEqual(capturedResult, .failed)
        XCTAssertEqual(capturedError as? NSError, testError)
    }

    func testOnComplete_nilCallback_doesNotCrash() {
        let sut = makeSUT(onComplete: nil)
        let coordinator = sut.makeCoordinator()
        let controller = MFMailComposeViewController()

        coordinator.mailComposeController(controller, didFinishWith: .sent, error: nil)
    }

    // MARK: - FeedbackCategory Tests
    // ReviewManagerTests から集約済み（allCases / displayName / icon / rawValue / identifiable）

    func testFeedbackCategory_rawValues() {
        XCTAssertEqual(FeedbackCategory.bugReport.rawValue, "bug_report")
        XCTAssertEqual(FeedbackCategory.featureRequest.rawValue, "feature_request")
        XCTAssertEqual(FeedbackCategory.usability.rawValue, "usability")
        XCTAssertEqual(FeedbackCategory.other.rawValue, "other")
    }

    func testFeedbackCategory_identifiable() {
        for category in FeedbackCategory.allCases {
            XCTAssertEqual(category.id, category.rawValue)
        }
    }

    func testFeedbackCategory_allCasesCount() {
        XCTAssertEqual(FeedbackCategory.allCases.count, 4)
    }

    func testFeedbackCategory_displayNames() {
        XCTAssertEqual(FeedbackCategory.bugReport.displayName, "バグ報告")
        XCTAssertEqual(FeedbackCategory.featureRequest.displayName, "機能要望")
        XCTAssertEqual(FeedbackCategory.usability.displayName, "使いにくい")
        XCTAssertEqual(FeedbackCategory.other.displayName, "その他")
    }

    func testFeedbackCategory_icons() {
        XCTAssertEqual(FeedbackCategory.bugReport.icon, "ladybug")
        XCTAssertEqual(FeedbackCategory.featureRequest.icon, "lightbulb")
        XCTAssertEqual(FeedbackCategory.usability.icon, "hand.tap")
        XCTAssertEqual(FeedbackCategory.other.icon, "ellipsis.circle")
    }
}
