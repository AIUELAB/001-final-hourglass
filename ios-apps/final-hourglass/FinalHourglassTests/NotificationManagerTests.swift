import XCTest
@testable import FinalHourglass

final class NotificationManagerTests: XCTestCase {

    var manager: NotificationManager!

    override func setUp() {
        super.setUp()
        // UserDefaultsをクリア
        if let bundleId = Bundle.main.bundleIdentifier {
            UserDefaults.standard.removePersistentDomain(forName: bundleId)
        }
        UserDefaults.standard.synchronize()

        // テスト用インスタンス作成（sharedは使わない）
        manager = NotificationManager()
    }

    override func tearDown() {
        manager = nil
        if let bundleId = Bundle.main.bundleIdentifier {
            UserDefaults.standard.removePersistentDomain(forName: bundleId)
        }
        UserDefaults.standard.synchronize()
        super.tearDown()
    }

    // MARK: - Test Helper

    /// テスト用のUserModelを作成（UserDefaultsをバイパス）
    private func createTestUser() -> UserModel {
        let user = UserModel()
        user.resetToDefaults()
        return user
    }

    // MARK: - A. 寿命計算テスト

    func testMaleBaseLifeExpectancy() {
        let userModel = createTestUser()
        userModel.gender = "male"
        userModel.smokingStatus = "non_smoker"
        userModel.exerciseFrequency = "sometimes"

        let lifeExpectancy = manager.calculateLifeExpectancy(for: userModel)

        // 男性基本寿命 81.64年（調整なし）
        XCTAssertEqual(lifeExpectancy, 81.64, accuracy: 0.01)
    }

    func testFemaleBaseLifeExpectancy() {
        let userModel = createTestUser()
        userModel.gender = "female"
        userModel.smokingStatus = "non_smoker"
        userModel.exerciseFrequency = "sometimes"

        let lifeExpectancy = manager.calculateLifeExpectancy(for: userModel)

        // 女性基本寿命 87.74年（調整なし）
        XCTAssertEqual(lifeExpectancy, 87.74, accuracy: 0.01)
    }

    func testSmokerLifeExpectancyReduction() {
        let userModel = createTestUser()
        userModel.gender = "male"
        userModel.smokingStatus = "smoker"
        userModel.exerciseFrequency = "sometimes"

        let lifeExpectancy = manager.calculateLifeExpectancy(for: userModel)

        // 男性基本寿命 81.64 - 10 = 71.64年
        XCTAssertEqual(lifeExpectancy, 71.64, accuracy: 0.01)
    }

    func testDailyExerciseBonus() {
        let userModel = createTestUser()
        userModel.gender = "male"
        userModel.smokingStatus = "non_smoker"
        userModel.exerciseFrequency = "daily"

        let lifeExpectancy = manager.calculateLifeExpectancy(for: userModel)

        // 男性基本寿命 81.64 + 2 = 83.64年
        XCTAssertEqual(lifeExpectancy, 83.64, accuracy: 0.01)
    }

    // MARK: - B. 残り日数計算テスト

    func testRemainingDaysCalculation() {
        let calendar = Calendar.current

        // 50年前の誕生日を設定（残り約31.64年）
        let birthDate = calendar.date(byAdding: .year, value: -50, to: Date())!
        let lifeExpectancy = 81.64

        let remainingDays = manager.calculateRemainingDays(birthDate: birthDate, lifeExpectancy: lifeExpectancy)

        // カレンダー計算は閏年を考慮するため、単純な365*年とは異なる
        // 期待値: 約31年分の日数（10,000〜12,000日の範囲）
        XCTAssertGreaterThan(remainingDays, 10000, "残り日数は10,000日以上であるべき")
        XCTAssertLessThan(remainingDays, 12500, "残り日数は12,500日未満であるべき")
    }

    func testRemainingDaysNeverNegative() {
        let calendar = Calendar.current

        // 100年前の誕生日を設定（寿命を超過）
        let birthDate = calendar.date(byAdding: .year, value: -100, to: Date())!
        let lifeExpectancy = 80.0

        let remainingDays = manager.calculateRemainingDays(birthDate: birthDate, lifeExpectancy: lifeExpectancy)

        // 0以下にならない（maxで0を保証）
        XCTAssertEqual(remainingDays, 0)
    }

    func testRemainingDaysWithFutureBirthDate() {
        let calendar = Calendar.current

        // 未来の誕生日（1年後）
        let birthDate = calendar.date(byAdding: .year, value: 1, to: Date())!
        let lifeExpectancy = 80.0

        let remainingDays = manager.calculateRemainingDays(birthDate: birthDate, lifeExpectancy: lifeExpectancy)

        // 未来の誕生日 + 80年 = 約81年後
        // カレンダー計算は閏年を考慮するため、範囲でチェック
        XCTAssertGreaterThan(remainingDays, 29000, "未来の誕生日では残り日数が29,000日以上であるべき")
        XCTAssertLessThan(remainingDays, 30500, "未来の誕生日では残り日数が30,500日未満であるべき")
    }

    // MARK: - C. 時間フォーマットテスト

    func testFormatRemainingTimeYearsAndMonths() {
        // 500日 = 1年4ヶ月（500 / 365 = 1年、(500 % 365) / 30 = 4ヶ月）
        let result = manager.formatRemainingTime(days: 500)
        XCTAssertEqual(result, "1年4ヶ月")
    }

    func testFormatRemainingTimeDaysOnly() {
        // 350日 < 365日 → 「350日」形式
        let result = manager.formatRemainingTime(days: 350)
        XCTAssertEqual(result, "350日")
    }

    func testFormatRemainingTimeYearsOnly() {
        // 730日 = 2年0ヶ月 → 「2年」形式
        let result = manager.formatRemainingTime(days: 730)
        XCTAssertEqual(result, "2年")
    }
}
