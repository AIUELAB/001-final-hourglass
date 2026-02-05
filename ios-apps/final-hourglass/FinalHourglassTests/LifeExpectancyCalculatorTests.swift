import XCTest
@testable import FinalHourglass

final class LifeExpectancyCalculatorTests: XCTestCase {

    // MARK: - Test Helper

    /// テスト用のUserModelを作成（UserDefaultsをバイパス）
    private func createTestUser() -> UserModel {
        let user = UserModel()
        user.resetToDefaults()
        return user
    }

    // MARK: - Gender Tests

    func testMaleBaseExpectancy() {
        let user = createTestUser()
        user.gender = "male"
        // デフォルト設定での期待値を計算
        // 基本81 + 各種調整
        let result = calculateLifeExpectancy(user: user)
        XCTAssertNotNil(result)
        // 男性の基本値は81歳
        XCTAssertLessThan(result!, 87.0, "男性は女性より基本値が低い")
    }

    func testFemaleBaseExpectancy() {
        let user = createTestUser()
        user.gender = "female"
        let result = calculateLifeExpectancy(user: user)
        XCTAssertNotNil(result)
        // 女性の基本値は87歳
        XCTAssertGreaterThan(result!, 81.0, "女性は男性より基本値が高い")
    }

    func testGenderDifference() {
        let maleUser = createTestUser()
        maleUser.gender = "male"

        let femaleUser = createTestUser()
        femaleUser.gender = "female"

        let maleResult = calculateLifeExpectancy(user: maleUser)!
        let femaleResult = calculateLifeExpectancy(user: femaleUser)!

        // 性別のみの違いで6年差（87 - 81）
        XCTAssertEqual(femaleResult - maleResult, 6.0, accuracy: 0.01)
    }

    // MARK: - BMI Tests

    func testBMIUnderweight() {
        let user = createTestUser()
        user.bmi = 17.0 // < 18.5: -3.0
        let underweightResult = calculateLifeExpectancy(user: user)!

        user.bmi = 22.0 // 正常: 0.0
        let normalResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(normalResult - underweightResult, 3.0, accuracy: 0.01)
    }

    func testBMINormal() {
        let user = createTestUser()
        user.bmi = 22.0 // 18.5-25: 0.0
        let normalResult = calculateLifeExpectancy(user: user)!

        user.bmi = 24.9
        let upperNormalResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(normalResult, upperNormalResult, accuracy: 0.01)
    }

    func testBMIOverweight() {
        let user = createTestUser()
        user.bmi = 27.0 // 25-30: -2.0
        let overweightResult = calculateLifeExpectancy(user: user)!

        user.bmi = 22.0 // 正常: 0.0
        let normalResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(normalResult - overweightResult, 2.0, accuracy: 0.01)
    }

    func testBMIObeseClass1() {
        let user = createTestUser()
        user.bmi = 32.0 // 30-35: -3.5
        let obeseResult = calculateLifeExpectancy(user: user)!

        user.bmi = 22.0
        let normalResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(normalResult - obeseResult, 3.5, accuracy: 0.01)
    }

    func testBMIObeseClass2() {
        let user = createTestUser()
        user.bmi = 40.0 // >= 35: -5.0
        let severeObeseResult = calculateLifeExpectancy(user: user)!

        user.bmi = 22.0
        let normalResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(normalResult - severeObeseResult, 5.0, accuracy: 0.01)
    }

    // MARK: - Smoking Tests

    func testSmokingCurrentSmoker() {
        let user = createTestUser()
        user.smokingStatus = "current_smoker" // -10.0
        let smokerResult = calculateLifeExpectancy(user: user)!

        user.smokingStatus = "non_smoker" // 0.0
        let nonSmokerResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(nonSmokerResult - smokerResult, 10.0, accuracy: 0.01)
    }

    func testSmokingDaily() {
        let user = createTestUser()
        user.smokingStatus = "daily" // -10.0 (same as current_smoker)
        let dailyResult = calculateLifeExpectancy(user: user)!

        user.smokingStatus = "non_smoker"
        let nonSmokerResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(nonSmokerResult - dailyResult, 10.0, accuracy: 0.01)
    }

    func testSmokingSometimes() {
        let user = createTestUser()
        user.smokingStatus = "sometimes" // -5.0
        let sometimesResult = calculateLifeExpectancy(user: user)!

        user.smokingStatus = "non_smoker"
        let nonSmokerResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(nonSmokerResult - sometimesResult, 5.0, accuracy: 0.01)
    }

    func testSmokingFormerSmokerShortTerm() {
        let user = createTestUser()
        user.smokingStatus = "former_smoker"
        user.smokingYears = 5 // < 10年: -3.0 + 1.0 = -2.0
        let shortTermResult = calculateLifeExpectancy(user: user)!

        user.smokingStatus = "non_smoker"
        let nonSmokerResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(nonSmokerResult - shortTermResult, 2.0, accuracy: 0.01)
    }

    func testSmokingFormerSmokerLongTerm() {
        let user = createTestUser()
        user.smokingStatus = "former_smoker"
        user.smokingYears = 25 // >= 20年: -3.0 - 1.0 = -4.0
        let longTermResult = calculateLifeExpectancy(user: user)!

        user.smokingStatus = "non_smoker"
        let nonSmokerResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(nonSmokerResult - longTermResult, 4.0, accuracy: 0.01)
    }

    // MARK: - Drinking Tests

    func testDrinkingNever() {
        let user = createTestUser()
        user.drinkingFrequency = "never" // 0.0
        let neverResult = calculateLifeExpectancy(user: user)!

        user.drinkingFrequency = "sometimes" // 0.5
        let sometimesResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(sometimesResult - neverResult, 0.5, accuracy: 0.01)
    }

    func testDrinkingRarely() {
        let user = createTestUser()
        user.drinkingFrequency = "rarely" // +1.0
        let rarelyResult = calculateLifeExpectancy(user: user)!

        user.drinkingFrequency = "never"
        let neverResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(rarelyResult - neverResult, 1.0, accuracy: 0.01)
    }

    func testDrinkingDaily() {
        let user = createTestUser()
        user.drinkingFrequency = "daily" // -5.0
        let dailyResult = calculateLifeExpectancy(user: user)!

        user.drinkingFrequency = "never"
        let neverResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(neverResult - dailyResult, 5.0, accuracy: 0.01)
    }

    // MARK: - Exercise Tests

    func testExerciseDaily() {
        let user = createTestUser()
        user.exerciseFrequency = "daily" // +5.0
        let dailyResult = calculateLifeExpectancy(user: user)!

        user.exerciseFrequency = "never" // -4.0
        let neverResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(dailyResult - neverResult, 9.0, accuracy: 0.01)
    }

    func testExerciseOften() {
        let user = createTestUser()
        user.exerciseFrequency = "often" // +3.0
        let oftenResult = calculateLifeExpectancy(user: user)!

        user.exerciseFrequency = "sometimes" // 0.0
        let sometimesResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(oftenResult - sometimesResult, 3.0, accuracy: 0.01)
    }

    // MARK: - Sleep Tests

    func testSleepOptimal() {
        let user = createTestUser()
        user.sleepHours = 7 // 0.0
        let optimalResult = calculateLifeExpectancy(user: user)!

        user.sleepHours = 8
        let eightHoursResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(optimalResult, eightHoursResult, accuracy: 0.01)
    }

    func testSleepTooShort() {
        let user = createTestUser()
        user.sleepHours = 4 // < 5: -3.0
        let tooShortResult = calculateLifeExpectancy(user: user)!

        user.sleepHours = 7
        let optimalResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(optimalResult - tooShortResult, 3.0, accuracy: 0.01)
    }

    func testSleepTooLong() {
        let user = createTestUser()
        user.sleepHours = 11 // > 10: -3.0
        let tooLongResult = calculateLifeExpectancy(user: user)!

        user.sleepHours = 7
        let optimalResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(optimalResult - tooLongResult, 3.0, accuracy: 0.01)
    }

    // MARK: - Stress Tests

    func testStressLow() {
        let user = createTestUser()
        user.stressLevel = "low" // +1.5
        let lowResult = calculateLifeExpectancy(user: user)!

        user.stressLevel = "medium" // 0.0
        let mediumResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(lowResult - mediumResult, 1.5, accuracy: 0.01)
    }

    func testStressVeryHigh() {
        let user = createTestUser()
        user.stressLevel = "very_high" // -5.0
        let veryHighResult = calculateLifeExpectancy(user: user)!

        user.stressLevel = "medium"
        let mediumResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(mediumResult - veryHighResult, 5.0, accuracy: 0.01)
    }

    // MARK: - Diet Tests

    func testDietPoor() {
        let user = createTestUser()
        user.dietHabits = [] // <= 1: -3.0
        let poorResult = calculateLifeExpectancy(user: user)!

        user.dietHabits = ["vegetables", "fish", "whole_grains", "fruits", "low_salt", "dairy"]
        let excellentResult = calculateLifeExpectancy(user: user)! // > 5: +4.0

        XCTAssertEqual(excellentResult - poorResult, 7.0, accuracy: 0.01)
    }

    func testDietModerate() {
        let user = createTestUser()
        user.dietHabits = ["vegetables", "fish"] // <= 3: -1.0
        let moderateResult = calculateLifeExpectancy(user: user)!

        user.dietHabits = ["vegetables", "fish", "whole_grains", "fruits"] // <= 5: +2.0
        let goodResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(goodResult - moderateResult, 3.0, accuracy: 0.01)
    }

    // MARK: - Breakfast Tests

    func testBreakfastDaily() {
        let user = createTestUser()
        user.breakfastFrequency = "daily" // +1.0
        let dailyResult = calculateLifeExpectancy(user: user)!

        user.breakfastFrequency = "never" // -2.0
        let neverResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(dailyResult - neverResult, 3.0, accuracy: 0.01)
    }

    // MARK: - Sitting Tests

    func testSittingShort() {
        let user = createTestUser()
        user.sittingHours = "less_3" // +1.0
        let shortResult = calculateLifeExpectancy(user: user)!

        user.sittingHours = "over_9" // -3.0
        let longResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(shortResult - longResult, 4.0, accuracy: 0.01)
    }

    // MARK: - Health Checkup Tests

    func testHealthCheckupYearly() {
        let user = createTestUser()
        user.healthCheckupFrequency = "yearly" // +2.0
        let yearlyResult = calculateLifeExpectancy(user: user)!

        user.healthCheckupFrequency = "rarely" // -1.0
        let rarelyResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(yearlyResult - rarelyResult, 3.0, accuracy: 0.01)
    }

    // MARK: - Dental Checkup Tests

    func testDentalBiannually() {
        let user = createTestUser()
        user.dentalCheckupFrequency = "biannually" // +1.0
        let biannuallyResult = calculateLifeExpectancy(user: user)!

        user.dentalCheckupFrequency = "rarely" // -2.0
        let rarelyResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(biannuallyResult - rarelyResult, 3.0, accuracy: 0.01)
    }

    // MARK: - Marital Status Tests

    func testMaritalSingle() {
        let user = createTestUser()
        user.maritalStatus = "single" // -1.0
        let singleResult = calculateLifeExpectancy(user: user)!

        user.maritalStatus = "married"
        user.marriageDuration = 10 // 基本+2.5
        let marriedResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(marriedResult - singleResult, 3.5, accuracy: 0.01)
    }

    func testMaritalMarriedLongTerm() {
        let user = createTestUser()
        user.maritalStatus = "married"
        user.marriageDuration = 25 // > 20年: +2.5 + 1.0 = +3.5
        let longTermResult = calculateLifeExpectancy(user: user)!

        user.marriageDuration = 10 // +2.5
        let normalResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(longTermResult - normalResult, 1.0, accuracy: 0.01)
    }

    func testMaritalDivorced() {
        let user = createTestUser()
        user.maritalStatus = "divorced"
        user.marriageDuration = 5 // < 10年: -1.5
        let shortDivorcedResult = calculateLifeExpectancy(user: user)!

        user.marriageDuration = 15 // > 10年: -1.0
        let longDivorcedResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(longDivorcedResult - shortDivorcedResult, 0.5, accuracy: 0.01)
    }

    // MARK: - Prefecture Tests

    func testPrefectureNagano() {
        let user = createTestUser()
        user.currentPrefecture = "nagano" // +2.5
        let naganoResult = calculateLifeExpectancy(user: user)!

        user.currentPrefecture = "aomori" // -2.0
        let aomoriResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(naganoResult - aomoriResult, 4.5, accuracy: 0.01)
    }

    func testPrefectureTokyo() {
        let user = createTestUser()
        user.currentPrefecture = "tokyo" // +0.8
        let tokyoResult = calculateLifeExpectancy(user: user)!

        user.currentPrefecture = "13" // コードでも動作確認（東京）
        let tokyoCodeResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(tokyoResult, tokyoCodeResult, accuracy: 0.01)
    }

    func testPrefectureUnknown() {
        let user = createTestUser()
        user.currentPrefecture = "unknown" // 0.0
        let unknownResult = calculateLifeExpectancy(user: user)!

        user.currentPrefecture = "nagano" // +2.5
        let naganoResult = calculateLifeExpectancy(user: user)!

        XCTAssertEqual(naganoResult - unknownResult, 2.5, accuracy: 0.01)
    }

    // MARK: - Boundary Tests

    func testMinimumClamp() {
        let user = createTestUser()
        // 最悪のケースを設定
        user.gender = "male" // 81
        user.bmi = 40.0 // -5
        user.smokingStatus = "current_smoker" // -10
        user.drinkingFrequency = "daily" // -5
        user.exerciseFrequency = "never" // -4
        user.sleepHours = 4 // -3
        user.stressLevel = "very_high" // -5
        user.dietHabits = [] // -3
        user.breakfastFrequency = "never" // -2
        user.sittingHours = "over_9" // -3
        user.healthCheckupFrequency = "rarely" // -1
        user.dentalCheckupFrequency = "rarely" // -2
        user.maritalStatus = "widowed"
        user.marriageDuration = 5 // -2
        user.currentPrefecture = "aomori" // -2

        let result = calculateLifeExpectancy(user: user)!

        // 81 - 47 = 34 だが、40にクランプされる
        XCTAssertEqual(result, 40.0, accuracy: 0.01)
    }

    func testMaximumClamp() {
        let user = createTestUser()
        // 最良のケースを設定
        user.gender = "female" // 87
        user.bmi = 22.0 // 0
        user.smokingStatus = "non_smoker" // 0
        user.drinkingFrequency = "rarely" // +1
        user.exerciseFrequency = "daily" // +5
        user.sleepHours = 7 // 0
        user.stressLevel = "low" // +1.5
        user.dietHabits = Set(["a", "b", "c", "d", "e", "f"]) // +4
        user.breakfastFrequency = "daily" // +1
        user.sittingHours = "less_3" // +1
        user.healthCheckupFrequency = "yearly" // +2
        user.dentalCheckupFrequency = "biannually" // +1
        user.maritalStatus = "married"
        user.marriageDuration = 25 // +3.5
        user.currentPrefecture = "nagano" // +2.5

        let result = calculateLifeExpectancy(user: user)!

        // 87 + 22.5 = 109.5 で120以下なのでそのまま
        XCTAssertLessThanOrEqual(result, 120.0)
        XCTAssertGreaterThanOrEqual(result, 40.0)
    }

    // MARK: - Result Not Nil Tests

    func testResultNeverNil() {
        let user = createTestUser()
        let result = calculateLifeExpectancy(user: user)
        XCTAssertNotNil(result)
    }
}
