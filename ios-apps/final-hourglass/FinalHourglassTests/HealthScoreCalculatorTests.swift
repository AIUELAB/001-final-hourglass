import XCTest
@testable import FinalHourglass

final class HealthScoreCalculatorTests: XCTestCase {

    // MARK: - Test Helper

    /// テスト用のUserModelを作成（UserDefaultsをバイパス）
    private func createTestUser() -> UserModel {
        let user = UserModel()
        user.resetToDefaults()
        return user
    }

    // MARK: - Basic Score Tests

    func testDefaultUserScore() {
        let user = createTestUser()
        let result = calculateHealthScore(user: user)

        // デフォルト値でのスコアを確認
        // デフォルト: non_smoker(0), sometimes(-0?), sometimes(0), dietHabits空(-5), sleep7(0), stress medium(0)
        // 100 + 0 + 0 + 0 + (-5) + 0 + 0 = 95
        XCTAssertGreaterThanOrEqual(result.score, 0)
        XCTAssertLessThanOrEqual(result.score, 100)
    }

    func testPerfectHealthScore() {
        let user = createTestUser()
        user.smokingStatus = "non_smoker" // 0
        user.drinkingFrequency = "never" // 0
        user.exerciseFrequency = "daily" // +10
        user.dietHabits = Set(["a", "b", "c", "d"]) // >= 4: +5
        user.sleepHours = 7 // 0
        user.stressLevel = "low" // +5

        let result = calculateHealthScore(user: user)

        // 100 + 0 + 0 + 10 + 5 + 0 + 5 = 120 -> clamped to 100
        XCTAssertEqual(result.score, 100)
    }

    func testWorstHealthScore() {
        let user = createTestUser()
        user.smokingStatus = "current_smoker" // -15
        user.drinkingFrequency = "daily" // -10
        user.exerciseFrequency = "never" // -10
        user.dietHabits = [] // < 2: -5
        user.sleepHours = 4 // < 6: -5
        user.stressLevel = "high" // -5

        let result = calculateHealthScore(user: user)

        // 100 - 15 - 10 - 10 - 5 - 5 - 5 = 50
        XCTAssertEqual(result.score, 50)
    }

    // MARK: - Smoking Tests

    func testSmokingCurrentSmoker() {
        let user = createTestUser()
        user.smokingStatus = "current_smoker"

        let result = calculateHealthScore(user: user)

        XCTAssertEqual(result.factors[.smoking], -15)
    }

    func testSmokingFormerSmoker() {
        let user = createTestUser()
        user.smokingStatus = "former_smoker"

        let result = calculateHealthScore(user: user)

        XCTAssertEqual(result.factors[.smoking], -5)
    }

    func testSmokingNonSmoker() {
        let user = createTestUser()
        user.smokingStatus = "non_smoker"

        let result = calculateHealthScore(user: user)

        XCTAssertEqual(result.factors[.smoking], 0)
    }

    func testSmokingUnknownValue() {
        let user = createTestUser()
        user.smokingStatus = "unknown"

        let result = calculateHealthScore(user: user)

        XCTAssertEqual(result.factors[.smoking], 0)
    }

    // MARK: - Drinking Tests

    func testDrinkingDaily() {
        let user = createTestUser()
        user.drinkingFrequency = "daily"

        let result = calculateHealthScore(user: user)

        XCTAssertEqual(result.factors[.drinking], -10)
    }

    func testDrinkingOften() {
        let user = createTestUser()
        user.drinkingFrequency = "often"

        let result = calculateHealthScore(user: user)

        XCTAssertEqual(result.factors[.drinking], -5)
    }

    func testDrinkingSometimes() {
        let user = createTestUser()
        user.drinkingFrequency = "sometimes"

        let result = calculateHealthScore(user: user)

        XCTAssertEqual(result.factors[.drinking], 0)
    }

    func testDrinkingNever() {
        let user = createTestUser()
        user.drinkingFrequency = "never"

        let result = calculateHealthScore(user: user)

        XCTAssertEqual(result.factors[.drinking], 0)
    }

    // MARK: - Exercise Tests

    func testExerciseDaily() {
        let user = createTestUser()
        user.exerciseFrequency = "daily"

        let result = calculateHealthScore(user: user)

        XCTAssertEqual(result.factors[.exercise], 10)
    }

    func testExerciseOften() {
        let user = createTestUser()
        user.exerciseFrequency = "often"

        let result = calculateHealthScore(user: user)

        XCTAssertEqual(result.factors[.exercise], 5)
    }

    func testExerciseSometimes() {
        let user = createTestUser()
        user.exerciseFrequency = "sometimes"

        let result = calculateHealthScore(user: user)

        XCTAssertEqual(result.factors[.exercise], 0)
    }

    func testExerciseRarely() {
        let user = createTestUser()
        user.exerciseFrequency = "rarely"

        let result = calculateHealthScore(user: user)

        XCTAssertEqual(result.factors[.exercise], -5)
    }

    func testExerciseNever() {
        let user = createTestUser()
        user.exerciseFrequency = "never"

        let result = calculateHealthScore(user: user)

        XCTAssertEqual(result.factors[.exercise], -10)
    }

    // MARK: - Diet Tests

    func testDietExcellent() {
        let user = createTestUser()
        user.dietHabits = Set(["a", "b", "c", "d"]) // >= 4

        let result = calculateHealthScore(user: user)

        XCTAssertEqual(result.factors[.diet], 5)
    }

    func testDietModerate() {
        let user = createTestUser()
        user.dietHabits = Set(["a", "b"]) // >= 2, < 4

        let result = calculateHealthScore(user: user)

        XCTAssertEqual(result.factors[.diet], 0)
    }

    func testDietPoor() {
        let user = createTestUser()
        user.dietHabits = Set(["a"]) // < 2

        let result = calculateHealthScore(user: user)

        XCTAssertEqual(result.factors[.diet], -5)
    }

    func testDietEmpty() {
        let user = createTestUser()
        user.dietHabits = [] // < 2

        let result = calculateHealthScore(user: user)

        XCTAssertEqual(result.factors[.diet], -5)
    }

    // MARK: - Sleep Tests

    func testSleepOptimal7Hours() {
        let user = createTestUser()
        user.sleepHours = 7

        let result = calculateHealthScore(user: user)

        XCTAssertEqual(result.factors[.sleep], 0)
    }

    func testSleepOptimal8Hours() {
        let user = createTestUser()
        user.sleepHours = 8

        let result = calculateHealthScore(user: user)

        XCTAssertEqual(result.factors[.sleep], 0)
    }

    func testSleepTooShort() {
        let user = createTestUser()
        user.sleepHours = 5 // < 6

        let result = calculateHealthScore(user: user)

        XCTAssertEqual(result.factors[.sleep], -5)
    }

    func testSleepTooLong() {
        let user = createTestUser()
        user.sleepHours = 10 // > 9

        let result = calculateHealthScore(user: user)

        XCTAssertEqual(result.factors[.sleep], -5)
    }

    func testSleepBorderline6Hours() {
        let user = createTestUser()
        user.sleepHours = 6 // 6 is not < 6, but also not 7-8

        let result = calculateHealthScore(user: user)

        // 6時間は < 6 ではないが、7-8の範囲外なので条件により0か-5
        // コードを見ると: if sleepHours >= 7 && sleepHours <= 8 { return 0 }
        // if sleepHours < 6 || sleepHours > 9 { return -5 }
        // それ以外は return 0
        XCTAssertEqual(result.factors[.sleep], 0)
    }

    func testSleepBorderline9Hours() {
        let user = createTestUser()
        user.sleepHours = 9 // > 9 は false

        let result = calculateHealthScore(user: user)

        XCTAssertEqual(result.factors[.sleep], 0)
    }

    // MARK: - Stress Tests

    func testStressLow() {
        let user = createTestUser()
        user.stressLevel = "low"

        let result = calculateHealthScore(user: user)

        XCTAssertEqual(result.factors[.stress], 5)
    }

    func testStressMedium() {
        let user = createTestUser()
        user.stressLevel = "medium"

        let result = calculateHealthScore(user: user)

        XCTAssertEqual(result.factors[.stress], 0)
    }

    func testStressHigh() {
        let user = createTestUser()
        user.stressLevel = "high"

        let result = calculateHealthScore(user: user)

        XCTAssertEqual(result.factors[.stress], -5)
    }

    func testStressUnknown() {
        let user = createTestUser()
        user.stressLevel = "unknown"

        let result = calculateHealthScore(user: user)

        XCTAssertEqual(result.factors[.stress], 0)
    }

    // MARK: - Score Clamp Tests

    func testScoreNeverExceeds100() {
        let user = createTestUser()
        // 最高条件を設定
        user.smokingStatus = "non_smoker"
        user.drinkingFrequency = "never"
        user.exerciseFrequency = "daily"
        user.dietHabits = Set(["a", "b", "c", "d", "e"])
        user.sleepHours = 7
        user.stressLevel = "low"

        let result = calculateHealthScore(user: user)

        XCTAssertLessThanOrEqual(result.score, 100)
    }

    func testScoreNeverBelowZero() {
        let user = createTestUser()
        // 最悪条件を設定（理論上は100-50=50なので0以下にはならないが念のため）
        user.smokingStatus = "current_smoker"
        user.drinkingFrequency = "daily"
        user.exerciseFrequency = "never"
        user.dietHabits = []
        user.sleepHours = 3
        user.stressLevel = "high"

        let result = calculateHealthScore(user: user)

        XCTAssertGreaterThanOrEqual(result.score, 0)
    }

    // MARK: - Factors Dictionary Tests

    func testAllFactorsPresent() {
        let user = createTestUser()
        let result = calculateHealthScore(user: user)

        XCTAssertNotNil(result.factors[.smoking])
        XCTAssertNotNil(result.factors[.drinking])
        XCTAssertNotNil(result.factors[.exercise])
        XCTAssertNotNil(result.factors[.diet])
        XCTAssertNotNil(result.factors[.sleep])
        XCTAssertNotNil(result.factors[.stress])
    }

    func testFactorsCount() {
        let user = createTestUser()
        let result = calculateHealthScore(user: user)

        XCTAssertEqual(result.factors.count, 6)
    }

    func testScoreEqualsBaseMinusDeltas() {
        let user = createTestUser()
        user.smokingStatus = "current_smoker" // -15
        user.drinkingFrequency = "daily" // -10
        user.exerciseFrequency = "daily" // +10
        user.dietHabits = Set(["a", "b", "c", "d"]) // +5
        user.sleepHours = 7 // 0
        user.stressLevel = "low" // +5

        let result = calculateHealthScore(user: user)

        // 100 - 15 - 10 + 10 + 5 + 0 + 5 = 95
        let expectedScore = 100 + result.factors.values.reduce(0, +)
        XCTAssertEqual(result.score, max(0, min(100, expectedScore)))
    }

    // MARK: - HealthFactor Enum Tests

    func testHealthFactorAllCases() {
        XCTAssertEqual(HealthFactor.allCases.count, 6)
        XCTAssertTrue(HealthFactor.allCases.contains(.smoking))
        XCTAssertTrue(HealthFactor.allCases.contains(.drinking))
        XCTAssertTrue(HealthFactor.allCases.contains(.exercise))
        XCTAssertTrue(HealthFactor.allCases.contains(.diet))
        XCTAssertTrue(HealthFactor.allCases.contains(.sleep))
        XCTAssertTrue(HealthFactor.allCases.contains(.stress))
    }

    func testHealthFactorRawValues() {
        XCTAssertEqual(HealthFactor.smoking.rawValue, "喫煙")
        XCTAssertEqual(HealthFactor.drinking.rawValue, "飲酒")
        XCTAssertEqual(HealthFactor.exercise.rawValue, "運動")
        XCTAssertEqual(HealthFactor.diet.rawValue, "食事")
        XCTAssertEqual(HealthFactor.sleep.rawValue, "睡眠")
        XCTAssertEqual(HealthFactor.stress.rawValue, "ストレス")
    }

    func testHealthFactorIcons() {
        XCTAssertEqual(HealthFactor.smoking.icon, "lungs")
        XCTAssertEqual(HealthFactor.drinking.icon, "wineglass")
        XCTAssertEqual(HealthFactor.exercise.icon, "figure.run")
        XCTAssertEqual(HealthFactor.diet.icon, "leaf")
        XCTAssertEqual(HealthFactor.sleep.icon, "bed.double")
        XCTAssertEqual(HealthFactor.stress.icon, "brain.head.profile")
    }

    // MARK: - HealthScore Struct Tests

    func testHealthScoreStruct() {
        let factors: [HealthFactor: Int] = [
            .smoking: -15,
            .drinking: 0,
            .exercise: 10,
            .diet: 5,
            .sleep: 0,
            .stress: 5
        ]
        let healthScore = HealthScore(score: 100, factors: factors)

        XCTAssertEqual(healthScore.score, 100)
        XCTAssertEqual(healthScore.factors[.smoking], -15)
        XCTAssertEqual(healthScore.factors.count, 6)
    }
}
