import XCTest
@testable import FinalHourglass

final class UserModelTests: XCTestCase {

    // MARK: - Test Helper

    /// テスト用のUserModelを作成（UserDefaultsをバイパス）
    private func createTestUser() -> UserModel {
        let user = UserModel()
        user.resetToDefaults()
        return user
    }

    // MARK: - A. 初期化テスト

    func testDefaultValues() {
        let user = createTestUser()

        // 基本情報
        XCTAssertEqual(user.birthYear, 1990)
        XCTAssertEqual(user.birthMonth, 1)
        XCTAssertEqual(user.birthDay, 1)
        XCTAssertEqual(user.gender, "male")

        // 身体情報
        XCTAssertEqual(user.height, 170.0, accuracy: 0.01)
        XCTAssertEqual(user.weight, 65.0, accuracy: 0.01)
        XCTAssertEqual(user.bmi, 22.49, accuracy: 0.01)

        // 生活習慣
        XCTAssertEqual(user.smokingStatus, "non_smoker")
        XCTAssertEqual(user.smokingYears, 0)
        XCTAssertEqual(user.drinkingFrequency, "sometimes")
        XCTAssertEqual(user.exerciseFrequency, "sometimes")
        XCTAssertEqual(user.sleepHours, 7)

        // 地域・環境
        XCTAssertEqual(user.currentPrefecture, "tokyo")
        XCTAssertEqual(user.commuteTime, "30_to_60")

        // 健康状態
        XCTAssertEqual(user.stressLevel, "medium")
        XCTAssertEqual(user.healthCheckupFrequency, "yearly")

        // 追加プロパティ
        XCTAssertTrue(user.dietHabits.isEmpty)
        XCTAssertEqual(user.breakfastFrequency, "daily")
        XCTAssertEqual(user.sittingHours, "3_to_6")
        XCTAssertEqual(user.dentalCheckupFrequency, "yearly")
        XCTAssertEqual(user.maritalStatus, "single")
        XCTAssertEqual(user.marriageDuration, 0)

        // 家族歴
        XCTAssertFalse(user.familyHistoryCancer)
        XCTAssertFalse(user.familyHistoryHeartDisease)
        XCTAssertFalse(user.familyHistoryDiabetes)
        XCTAssertFalse(user.familyHistoryStroke)
        XCTAssertFalse(user.familyHistoryAlzheimers)
        XCTAssertFalse(user.familyHistoryOther)
        XCTAssertEqual(user.familyHistoryOtherText, "")
        XCTAssertFalse(user.hasLongLivedRelatives)
    }

    func testInitCallsLoadAndCalculateBMI() {
        // UserDefaultsに値を保存
        let defaults = UserDefaults.standard
        defaults.set(180.0, forKey: "height")
        defaults.set(75.0, forKey: "weight")

        // 新しいインスタンスを作成（init()がloadFromUserDefaultsとcalculateBMIを呼ぶ）
        let user = UserModel()

        // 保存した値がロードされている
        XCTAssertEqual(user.height, 180.0, accuracy: 0.01)
        XCTAssertEqual(user.weight, 75.0, accuracy: 0.01)

        // BMIが計算されている（180cm, 75kg → 75 / (1.8 * 1.8) ≈ 23.15）
        XCTAssertEqual(user.bmi, 23.15, accuracy: 0.01)

        // クリーンアップ
        user.clearAllUserDefaults()
    }

    func testDefaultBMI() {
        let user = createTestUser()

        // デフォルト値（170cm, 65kg）でBMI計算
        // BMI = 65 / (1.7 * 1.7) = 65 / 2.89 ≈ 22.49
        XCTAssertEqual(user.bmi, 22.49, accuracy: 0.01)
    }

    // MARK: - B. 計算プロパティテスト

    func testBirthDateCalculation() {
        let user = createTestUser()
        user.birthYear = 1985
        user.birthMonth = 7
        user.birthDay = 15

        let birthDate = user.birthDate
        let calendar = Calendar.current
        let components = calendar.dateComponents([.year, .month, .day], from: birthDate)

        XCTAssertEqual(components.year, 1985)
        XCTAssertEqual(components.month, 7)
        XCTAssertEqual(components.day, 15)
    }

    func testAgeCalculation() {
        let user = createTestUser()
        let calendar = Calendar.current
        let currentYear = calendar.component(.year, from: Date())

        // 今年誕生日がまだ来ていない場合（12月31日生まれ）
        user.birthYear = currentYear - 30
        user.birthMonth = 12
        user.birthDay = 31

        // 現在の月日によって年齢が29か30
        let expectedAge = calendar.component(.month, from: Date()) == 12
            && calendar.component(.day, from: Date()) >= 31 ? 30 : 29
        XCTAssertEqual(user.age, expectedAge)

        // 今年誕生日が過ぎている場合（1月1日生まれ）
        user.birthMonth = 1
        user.birthDay = 1
        XCTAssertEqual(user.age, 30)
    }

    func testAgeGroupTeens() {
        let user = createTestUser()
        let currentYear = Calendar.current.component(.year, from: Date())

        // 16歳
        user.birthYear = currentYear - 16
        user.birthMonth = 1
        user.birthDay = 1
        XCTAssertEqual(user.ageGroup, "10s")

        // 19歳
        user.birthYear = currentYear - 19
        XCTAssertEqual(user.ageGroup, "10s")
    }

    func testAgeGroup20sEarly() {
        let user = createTestUser()
        let currentYear = Calendar.current.component(.year, from: Date())

        // 20歳
        user.birthYear = currentYear - 20
        user.birthMonth = 1
        user.birthDay = 1
        XCTAssertEqual(user.ageGroup, "20s_early")

        // 24歳
        user.birthYear = currentYear - 24
        XCTAssertEqual(user.ageGroup, "20s_early")
    }

    func testAgeGroup30s() {
        let user = createTestUser()
        let currentYear = Calendar.current.component(.year, from: Date())

        // 30歳
        user.birthYear = currentYear - 30
        user.birthMonth = 1
        user.birthDay = 1
        XCTAssertEqual(user.ageGroup, "30s")

        // 39歳
        user.birthYear = currentYear - 39
        XCTAssertEqual(user.ageGroup, "30s")
    }

    func testAgeGroupEdgeCases() {
        let user = createTestUser()
        let currentYear = Calendar.current.component(.year, from: Date())

        // 60歳以上は "60s"
        user.birthYear = currentYear - 60
        user.birthMonth = 1
        user.birthDay = 1
        XCTAssertEqual(user.ageGroup, "60s")

        user.birthYear = currentYear - 80
        XCTAssertEqual(user.ageGroup, "60s")

        // 15歳以下は "all"（範囲外）
        user.birthYear = currentYear - 15
        XCTAssertEqual(user.ageGroup, "all")

        user.birthYear = currentYear - 10
        XCTAssertEqual(user.ageGroup, "all")
    }

    // MARK: - C. BMI計算テスト

    func testCalculateBMINormal() {
        let user = createTestUser()
        user.height = 170.0
        user.weight = 65.0
        user.calculateBMI()

        // BMI = 65 / (1.7 * 1.7) ≈ 22.49
        XCTAssertEqual(user.bmi, 22.49, accuracy: 0.01)
    }

    func testCalculateBMIShort() {
        let user = createTestUser()
        user.height = 150.0
        user.weight = 50.0
        user.calculateBMI()

        // BMI = 50 / (1.5 * 1.5) ≈ 22.22
        XCTAssertEqual(user.bmi, 22.22, accuracy: 0.01)
    }

    func testCalculateBMITall() {
        let user = createTestUser()
        user.height = 190.0
        user.weight = 80.0
        user.calculateBMI()

        // BMI = 80 / (1.9 * 1.9) ≈ 22.16
        XCTAssertEqual(user.bmi, 22.16, accuracy: 0.01)
    }

    func testCalculateBMIZeroHeight() {
        let user = createTestUser()
        let originalBMI = user.bmi // デフォルト値を保存

        user.height = 0.0
        user.calculateBMI()

        // height=0の場合、BMIは変更されない（0除算対策）
        XCTAssertEqual(user.bmi, originalBMI, accuracy: 0.01)
    }

    // MARK: - D. UserDefaults連携テスト

    func testSaveAndLoadRoundTrip() {
        let user = createTestUser()

        // 値を変更
        user.birthYear = 1985
        user.birthMonth = 6
        user.birthDay = 15
        user.gender = "female"
        user.height = 160.0
        user.weight = 55.0
        user.smokingStatus = "former_smoker"
        user.currentPrefecture = "osaka"
        user.familyHistoryCancer = true

        // 保存
        user.saveToUserDefaults()

        // 新しいインスタンスで読み込み
        let newUser = UserModel()

        // 値が復元されている
        XCTAssertEqual(newUser.birthYear, 1985)
        XCTAssertEqual(newUser.birthMonth, 6)
        XCTAssertEqual(newUser.birthDay, 15)
        XCTAssertEqual(newUser.gender, "female")
        XCTAssertEqual(newUser.height, 160.0, accuracy: 0.01)
        XCTAssertEqual(newUser.weight, 55.0, accuracy: 0.01)
        XCTAssertEqual(newUser.smokingStatus, "former_smoker")
        XCTAssertEqual(newUser.currentPrefecture, "osaka")
        XCTAssertTrue(newUser.familyHistoryCancer)

        // クリーンアップ
        newUser.clearAllUserDefaults()
    }

    func testDietHabitsSetConversion() {
        let user = createTestUser()

        // Setに値を設定
        user.dietHabits = Set(["vegetables", "fish", "whole_grains"])

        // 保存
        user.saveToUserDefaults()

        // 新しいインスタンスで読み込み
        let newUser = UserModel()

        // Set↔Array変換が正しく動作している
        XCTAssertEqual(newUser.dietHabits.count, 3)
        XCTAssertTrue(newUser.dietHabits.contains("vegetables"))
        XCTAssertTrue(newUser.dietHabits.contains("fish"))
        XCTAssertTrue(newUser.dietHabits.contains("whole_grains"))

        // クリーンアップ
        newUser.clearAllUserDefaults()
    }

    func testClearAllUserDefaults() {
        let user = createTestUser()

        // 値を変更して保存
        user.birthYear = 2000
        user.gender = "other"
        user.saveToUserDefaults()

        // UserDefaultsに保存されていることを確認
        let defaults = UserDefaults.standard
        XCTAssertEqual(defaults.integer(forKey: "birthYear"), 2000)
        XCTAssertEqual(defaults.string(forKey: "gender"), "other")

        // クリア
        user.clearAllUserDefaults()

        // キーが削除されている
        XCTAssertNil(defaults.object(forKey: "birthYear"))
        XCTAssertNil(defaults.object(forKey: "gender"))
    }

    func testResetToDefaults() {
        let user = createTestUser()

        // 値を変更
        user.birthYear = 1970
        user.birthMonth = 12
        user.birthDay = 25
        user.gender = "female"
        user.height = 155.0
        user.weight = 48.0
        user.smokingStatus = "current_smoker"
        user.dietHabits = Set(["a", "b", "c"])
        user.familyHistoryCancer = true

        // リセット
        user.resetToDefaults()

        // 初期値に戻っている
        XCTAssertEqual(user.birthYear, 1990)
        XCTAssertEqual(user.birthMonth, 1)
        XCTAssertEqual(user.birthDay, 1)
        XCTAssertEqual(user.gender, "male")
        XCTAssertEqual(user.height, 170.0, accuracy: 0.01)
        XCTAssertEqual(user.weight, 65.0, accuracy: 0.01)
        XCTAssertEqual(user.smokingStatus, "non_smoker")
        XCTAssertTrue(user.dietHabits.isEmpty)
        XCTAssertFalse(user.familyHistoryCancer)
    }

    // MARK: - E. エッジケーステスト

    func testBoundaryBirthDateCalculation() {
        let user = createTestUser()

        // Calendarは範囲外の日付をオーバーフロー処理で修正する
        // 例: 2000年13月45日 → 2001年2月14日頃
        user.birthYear = 2000
        user.birthMonth = 13
        user.birthDay = 45

        let birthDate = user.birthDate
        let calendar = Calendar.current
        let components = calendar.dateComponents([.year, .month, .day], from: birthDate)

        // Calendarがオーバーフローを計算: 13月 = 翌年1月、45日 = 2月14日頃
        // 正確な結果はCalendarの実装に依存するが、nilではなく有効なDateが返る
        XCTAssertNotNil(components.year)
        XCTAssertNotNil(components.month)
        XCTAssertNotNil(components.day)

        // オーバーフロー後は元の値とは異なる
        XCTAssertNotEqual(components.year, 2000)
    }

    func testPersonalizedMessageByAgeGroup() {
        let user = createTestUser()
        let currentYear = Calendar.current.component(.year, from: Date())
        user.birthMonth = 1
        user.birthDay = 1

        // 10s
        user.birthYear = currentYear - 17
        XCTAssertEqual(user.personalizedMessage, "君の可能性は無限大")

        // 20s_early
        user.birthYear = currentYear - 22
        XCTAssertEqual(user.personalizedMessage, "今の努力が未来を作る")

        // 20s_late
        user.birthYear = currentYear - 27
        XCTAssertEqual(user.personalizedMessage, "自分の道を信じて")

        // 30s
        user.birthYear = currentYear - 35
        XCTAssertEqual(user.personalizedMessage, "両立の中で輝く")

        // 40s
        user.birthYear = currentYear - 45
        XCTAssertEqual(user.personalizedMessage, "経験を次代へ")

        // 50s
        user.birthYear = currentYear - 55
        XCTAssertEqual(user.personalizedMessage, "これからが本番")

        // 60s
        user.birthYear = currentYear - 65
        XCTAssertEqual(user.personalizedMessage, "あなたの物語を")

        // default (all)
        user.birthYear = currentYear - 10
        XCTAssertEqual(user.personalizedMessage, "人生の価値を再発見")
    }

    func testRecommendedEpisodeTypesByAgeGroup() {
        let user = createTestUser()
        let currentYear = Calendar.current.component(.year, from: Date())
        user.birthMonth = 1
        user.birthDay = 1

        // 10s, 20s_early, 20s_late
        user.birthYear = currentYear - 17
        XCTAssertEqual(user.recommendedEpisodeTypes, ["failure", "turning_point", "glory"])

        user.birthYear = currentYear - 22
        XCTAssertEqual(user.recommendedEpisodeTypes, ["failure", "turning_point", "glory"])

        user.birthYear = currentYear - 27
        XCTAssertEqual(user.recommendedEpisodeTypes, ["failure", "turning_point", "glory"])

        // 30s, 40s
        user.birthYear = currentYear - 35
        XCTAssertEqual(user.recommendedEpisodeTypes, ["turning_point", "failure", "glory"])

        user.birthYear = currentYear - 45
        XCTAssertEqual(user.recommendedEpisodeTypes, ["turning_point", "failure", "glory"])

        // 50s, 60s
        user.birthYear = currentYear - 55
        XCTAssertEqual(user.recommendedEpisodeTypes, ["glory", "turning_point", "failure"])

        user.birthYear = currentYear - 65
        XCTAssertEqual(user.recommendedEpisodeTypes, ["glory", "turning_point", "failure"])

        // default (all)
        user.birthYear = currentYear - 10
        XCTAssertEqual(user.recommendedEpisodeTypes, ["turning_point", "glory", "failure"])
    }
}
