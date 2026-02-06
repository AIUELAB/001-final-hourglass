import SwiftUI

class UserModel: ObservableObject {
    // 基本情報
    @Published var birthYear: Int = 1990 {
        didSet {
            if oldValue != birthYear { notifyAgeChanged() }
        }
    }
    @Published var birthMonth: Int = 1 {
        didSet {
            if oldValue != birthMonth { notifyAgeChanged() }
        }
    }
    @Published var birthDay: Int = 1 {
        didSet {
            if oldValue != birthDay { notifyAgeChanged() }
        }
    }
    @Published var gender: String = "male"

    // 身体情報
    @Published var height: Double = 170.0
    @Published var weight: Double = 65.0
    @Published var bmi: Double = 22.5

    // 生活習慣
    @Published var smokingStatus: String = "non_smoker"
    @Published var smokingYears: Int = 0  // 喫煙年数（禁煙済みの場合に使用）
    @Published var drinkingFrequency: String = "sometimes"
    @Published var exerciseFrequency: String = "sometimes"
    @Published var sleepHours: Int = 7

    // 地域・環境
    @Published var currentPrefecture: String = "tokyo"
    @Published var commuteTime: String = "30_to_60"

    // 健康状態
    @Published var stressLevel: String = "medium"
    @Published var healthCheckupFrequency: String = "yearly"

    // 追加プロパティ（OnboardingViewで使用）
    @Published var dietHabits: Set<String> = []
    @Published var breakfastFrequency: String = "daily"
    @Published var sittingHours: String = "3_to_6"
    @Published var dentalCheckupFrequency: String = "yearly"
    @Published var maritalStatus: String = "single"
    @Published var marriageDuration: Int = 0

    // 家族歴（将来の拡張用）
    @Published var familyHistoryCancer: Bool = false
    @Published var familyHistoryHeartDisease: Bool = false
    @Published var familyHistoryDiabetes: Bool = false
    @Published var familyHistoryStroke: Bool = false
    @Published var familyHistoryAlzheimers: Bool = false
    @Published var familyHistoryOther: Bool = false
    @Published var familyHistoryOtherText: String = ""
    @Published var hasLongLivedRelatives: Bool = false

    // 計算されたプロパティ
    var birthDate: Date {
        Calendar.current.date(from: DateComponents(year: birthYear, month: birthMonth, day: birthDay)) ?? Date()
    }

    // 年齢計算
    var age: Int {
        let calendar = Calendar.current
        let ageComponents = calendar.dateComponents([.year], from: birthDate, to: Date())
        return ageComponents.year ?? 0
    }

    // 年齢グループ判定
    var ageGroup: String {
        switch age {
        case 16...19:
            return "10s"
        case 20...24:
            return "20s_early"
        case 25...29:
            return "20s_late"
        case 30...39:
            return "30s"
        case 40...49:
            return "40s"
        case 50...59:
            return "50s"
        case 60...:
            return "60s"
        default:
            return "all"
        }
    }

    // periphery:ignore - Future personalization feature
    // パーソナライゼーションメッセージ
    var personalizedMessage: String {
        switch ageGroup {
        case "10s":
            return "君の可能性は無限大"
        case "20s_early":
            return "今の努力が未来を作る"
        case "20s_late":
            return "自分の道を信じて"
        case "30s":
            return "両立の中で輝く"
        case "40s":
            return "経験を次代へ"
        case "50s":
            return "これからが本番"
        case "60s":
            return "あなたの物語を"
        default:
            return "人生の価値を再発見"
        }
    }

    // periphery:ignore - Future personalization feature
    // 推奨エピソードタイプ
    var recommendedEpisodeTypes: [String] {
        switch ageGroup {
        case "10s", "20s_early", "20s_late":
            return ["failure", "turning_point", "glory"]
        case "30s", "40s":
            return ["turning_point", "failure", "glory"]
        case "50s", "60s":
            return ["glory", "turning_point", "failure"]
        default:
            return ["turning_point", "glory", "failure"]
        }
    }

    init() {
        loadFromUserDefaults()
        calculateBMI()
    }

    // UserDefaultsから全てのユーザーデータをクリア
    func clearAllUserDefaults() {
        let defaults = UserDefaults.standard

        // ユーザーデータのキーをすべて削除
        let userDataKeys = [
            "birthYear", "birthMonth", "birthDay", "gender",
            "height", "weight",
            "smokingStatus", "smokingYears", "drinkingFrequency",
            "exerciseFrequency", "sleepHours",
            "currentPrefecture", "commuteTime",
            "stressLevel", "healthCheckupFrequency",
            "dietHabits", "breakfastFrequency", "sittingHours",
            "dentalCheckupFrequency", "maritalStatus", "marriageDuration",
            "familyHistoryCancer", "familyHistoryHeartDisease",
            "familyHistoryDiabetes", "familyHistoryStroke",
            "familyHistoryAlzheimers", "familyHistoryOther",
            "familyHistoryOtherText", "hasLongLivedRelatives"
        ]

        for key in userDataKeys {
            defaults.removeObject(forKey: key)
        }

        defaults.synchronize()
    }

    // データを初期値にリセット
    func resetToDefaults() {
        // UserDefaultsをクリア
        clearAllUserDefaults()

        // 基本情報
        birthYear = 1990
        birthMonth = 1
        birthDay = 1
        gender = "male"

        // 身体情報
        height = 170.0
        weight = 65.0
        bmi = 22.5

        // 生活習慣
        smokingStatus = "non_smoker"
        smokingYears = 0
        drinkingFrequency = "sometimes"
        exerciseFrequency = "sometimes"
        sleepHours = 7

        // 地域・環境
        currentPrefecture = "tokyo"
        commuteTime = "30_to_60"

        // 健康状態
        stressLevel = "medium"
        healthCheckupFrequency = "yearly"

        // 追加プロパティ
        dietHabits = []
        breakfastFrequency = "daily"
        sittingHours = "3_to_6"
        dentalCheckupFrequency = "yearly"
        maritalStatus = "single"
        marriageDuration = 0

        // 家族歴
        familyHistoryCancer = false
        familyHistoryHeartDisease = false
        familyHistoryDiabetes = false
        familyHistoryStroke = false
        familyHistoryAlzheimers = false
        familyHistoryOther = false
        familyHistoryOtherText = ""
        hasLongLivedRelatives = false

        // BMIを再計算
        calculateBMI()
    }

    // BMI計算
    func calculateBMI() {
        let heightInMeters = height / 100
        if heightInMeters > 0 {
            bmi = weight / (heightInMeters * heightInMeters)
        }
    }

    // UserDefaultsに保存
    func saveToUserDefaults() {
        let defaults = UserDefaults.standard

        // 基本情報
        defaults.set(birthYear, forKey: "birthYear")
        defaults.set(birthMonth, forKey: "birthMonth")
        defaults.set(birthDay, forKey: "birthDay")
        defaults.set(gender, forKey: "gender")

        // 身体情報
        defaults.set(height, forKey: "height")
        defaults.set(weight, forKey: "weight")

        // 生活習慣
        defaults.set(smokingStatus, forKey: "smokingStatus")
        defaults.set(smokingYears, forKey: "smokingYears")
        defaults.set(drinkingFrequency, forKey: "drinkingFrequency")
        defaults.set(exerciseFrequency, forKey: "exerciseFrequency")
        defaults.set(sleepHours, forKey: "sleepHours")

        // 地域・環境
        defaults.set(currentPrefecture, forKey: "currentPrefecture")
        defaults.set(commuteTime, forKey: "commuteTime")

        // 健康状態
        defaults.set(stressLevel, forKey: "stressLevel")
        defaults.set(healthCheckupFrequency, forKey: "healthCheckupFrequency")

        // 追加プロパティ
        defaults.set(Array(dietHabits), forKey: "dietHabits")
        defaults.set(breakfastFrequency, forKey: "breakfastFrequency")
        defaults.set(sittingHours, forKey: "sittingHours")
        defaults.set(dentalCheckupFrequency, forKey: "dentalCheckupFrequency")
        defaults.set(maritalStatus, forKey: "maritalStatus")
        defaults.set(marriageDuration, forKey: "marriageDuration")

        // 家族歴
        defaults.set(familyHistoryCancer, forKey: "familyHistoryCancer")
        defaults.set(familyHistoryHeartDisease, forKey: "familyHistoryHeartDisease")
        defaults.set(familyHistoryDiabetes, forKey: "familyHistoryDiabetes")
        defaults.set(familyHistoryStroke, forKey: "familyHistoryStroke")
        defaults.set(familyHistoryAlzheimers, forKey: "familyHistoryAlzheimers")
        defaults.set(familyHistoryOther, forKey: "familyHistoryOther")
        defaults.set(familyHistoryOtherText, forKey: "familyHistoryOtherText")
        defaults.set(hasLongLivedRelatives, forKey: "hasLongLivedRelatives")
    }

    // 年齢が変更されたことを通知
    private func notifyAgeChanged() {
        // EpisodeManagerのキャッシュをクリア
        EpisodeManager.shared.clearCacheForAgeChange()
    }

    // UserDefaultsから読み込み
    func loadFromUserDefaults() {
        let defaults = UserDefaults.standard

        loadBasicInfo(defaults)

        loadBodyInfo(defaults)

        loadLifestyle(defaults)

        loadRegion(defaults)

        loadHealth(defaults)

        loadAdditional(defaults)

        loadFamilyHistory(defaults)

        calculateBMI()
    }
}

extension UserModel {
    // MARK: - UserDefaults Section Loaders
    private func loadBasicInfo(_ defaults: UserDefaults) {
        if defaults.object(forKey: "birthYear") != nil { birthYear = defaults.integer(forKey: "birthYear") }
        if defaults.object(forKey: "birthMonth") != nil { birthMonth = defaults.integer(forKey: "birthMonth") }
        if defaults.object(forKey: "birthDay") != nil { birthDay = defaults.integer(forKey: "birthDay") }
        if let savedGender = defaults.string(forKey: "gender") { gender = savedGender }
    }

    private func loadBodyInfo(_ defaults: UserDefaults) {
        if defaults.object(forKey: "height") != nil { height = defaults.double(forKey: "height") }
        if defaults.object(forKey: "weight") != nil { weight = defaults.double(forKey: "weight") }
    }

    private func loadLifestyle(_ defaults: UserDefaults) {
        if let savedSmokingStatus = defaults.string(forKey: "smokingStatus") { smokingStatus = savedSmokingStatus }
        if defaults.object(forKey: "smokingYears") != nil { smokingYears = defaults.integer(forKey: "smokingYears") }
        if let savedDrinkingFrequency = defaults.string(forKey: "drinkingFrequency") {
            drinkingFrequency = savedDrinkingFrequency
        }
        if let savedExerciseFrequency = defaults.string(forKey: "exerciseFrequency") {
            exerciseFrequency = savedExerciseFrequency
        }
        if defaults.object(forKey: "sleepHours") != nil { sleepHours = defaults.integer(forKey: "sleepHours") }
    }

    private func loadRegion(_ defaults: UserDefaults) {
        if let savedPrefecture = defaults.string(forKey: "currentPrefecture") { currentPrefecture = savedPrefecture }
        if let savedCommuteTime = defaults.string(forKey: "commuteTime") { commuteTime = savedCommuteTime }
    }

    private func loadHealth(_ defaults: UserDefaults) {
        if let savedStressLevel = defaults.string(forKey: "stressLevel") { stressLevel = savedStressLevel }
        if let savedHealthCheckupFrequency = defaults.string(forKey: "healthCheckupFrequency") {
            healthCheckupFrequency = savedHealthCheckupFrequency
        }
    }

    private func loadAdditional(_ defaults: UserDefaults) {
        if let arr = defaults.array(forKey: "dietHabits") as? [String] { dietHabits = Set(arr) }
        if let savedBreakfastFrequency = defaults.string(forKey: "breakfastFrequency") {
            breakfastFrequency = savedBreakfastFrequency
        }
        if let savedSittingHours = defaults.string(forKey: "sittingHours") {
            sittingHours = savedSittingHours
        }
        if let savedDentalCheckupFrequency = defaults.string(forKey: "dentalCheckupFrequency") {
                dentalCheckupFrequency = savedDentalCheckupFrequency
            }
        if let savedMaritalStatus = defaults.string(forKey: "maritalStatus") {
                maritalStatus = savedMaritalStatus
            }
        if defaults.object(forKey: "marriageDuration") != nil {
            marriageDuration = defaults.integer(forKey: "marriageDuration")
        }
    }

    private func loadFamilyHistory(_ defaults: UserDefaults) {
        familyHistoryCancer = defaults.bool(forKey: "familyHistoryCancer")
        familyHistoryHeartDisease = defaults.bool(
            forKey: "familyHistoryHeartDisease"
        )
        familyHistoryDiabetes = defaults.bool(forKey: "familyHistoryDiabetes")
        familyHistoryStroke = defaults.bool(forKey: "familyHistoryStroke")
        familyHistoryAlzheimers = defaults.bool(forKey: "familyHistoryAlzheimers")
        familyHistoryOther = defaults.bool(forKey: "familyHistoryOther")
        familyHistoryOtherText = defaults.string(
                forKey: "familyHistoryOtherText"
            ) ?? ""
        hasLongLivedRelatives = defaults.bool(forKey: "hasLongLivedRelatives")
    }
}
