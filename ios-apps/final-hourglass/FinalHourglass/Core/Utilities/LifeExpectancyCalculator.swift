import Foundation

// MARK: - Helpers for Life Expectancy adjustments
private func adjustmentFromBMI(_ user: UserModel) -> Double {
    let bmi = user.bmi
    if bmi < 18.5 { return -3.0 }
    if bmi < 25 { return 0.0 }
    if bmi < 30 { return -2.0 }
    if bmi < 35 { return -3.5 }
    return -5.0
}

private func adjustmentFromSmoking(_ user: UserModel) -> Double {
    switch user.smokingStatus {
    case "current_smoker", "daily": return -10.0
    case "sometimes": return -5.0
    case "former_smoker", "quit":
        var impact = -3.0
        if user.smokingYears > 0 && user.smokingYears < 10 { impact += 1.0 } else if user.smokingYears >= 20 { impact -= 1.0 }
        return impact
    case "never", "non_smoker": return 0.0
    default: return 0.0
    }
}

private func adjustmentFromDrinking(_ user: UserModel) -> Double {
    switch user.drinkingFrequency {
    case "never": return 0.0
    case "rarely": return 1.0
    case "sometimes", "occasionally": return 0.5
    case "often": return -2.0
    case "daily": return -5.0
    default: return 0.0
    }
}

private func adjustmentFromExercise(_ user: UserModel) -> Double {
    switch user.exerciseFrequency {
    case "never": return -4.0
    case "rarely": return -2.0
    case "sometimes", "occasionally": return 0.0
    case "often": return 3.0
    case "daily": return 5.0
    default: return 0.0
    }
}

private func adjustmentFromSleep(_ user: UserModel) -> Double {
    if user.sleepHours < 5 { return -3.0 }
    if user.sleepHours < 6 { return -2.0 }
    if user.sleepHours < 7 { return -1.0 }
    if user.sleepHours > 10 { return -3.0 }
    if user.sleepHours > 9 { return -2.0 }
    return 0.0
}

private func adjustmentFromStress(_ user: UserModel) -> Double {
    switch user.stressLevel {
    case "low": return 1.5
    case "medium": return 0.0
    case "high": return -3.0
    case "very_high": return -5.0
    default: return 0.0
    }
}

private func adjustmentFromDiet(_ user: UserModel) -> Double {
    let dietCount = user.dietHabits.count
    if dietCount <= 1 { return -3.0 }
    if dietCount <= 3 { return -1.0 }
    if dietCount <= 5 { return 2.0 }
    return 4.0
}

private func adjustmentFromBreakfast(_ user: UserModel) -> Double {
    switch user.breakfastFrequency {
    case "never": return -2.0
    case "rarely": return -1.5
    case "sometimes": return -0.5
    case "often": return 0.5
    case "daily": return 1.0
    default: return 0.0
    }
}

private func adjustmentFromSitting(_ user: UserModel) -> Double {
    switch user.sittingHours {
    case "less_3": return 1.0
    case "3_to_6": return 0.0
    case "6_to_9": return -1.5
    case "over_9": return -3.0
    default: return 0.0
    }
}

private func adjustmentFromHealthCheck(_ user: UserModel) -> Double {
    switch user.healthCheckupFrequency {
    case "yearly": return 2.0
    case "every_2_3_years": return 0.0
    case "rarely": return -1.0
    default: return 0.0
    }
}

private func adjustmentFromDental(_ user: UserModel) -> Double {
    switch user.dentalCheckupFrequency {
    case "biannually": return 1.0
    case "yearly": return 0.5
    case "every_2_3_years": return 0.0
    case "rarely": return -2.0
    default: return 0.0
    }
}

private func adjustmentFromMarital(_ user: UserModel) -> Double {
    switch user.maritalStatus {
    case "single": return -1.0
    case "married":
        var adj = 2.5
        if user.marriageDuration > 20 { adj += 1.0 } else if user.marriageDuration < 2 { adj -= 0.5 }
        return adj
    case "divorced":
        // 離婚: 基本-1.5、婚姻期間10年超で+0.5 -> -1.0
        return user.marriageDuration > 10 ? -1.0 : -1.5
    case "widowed":
        // 死別: 基本-2.0、婚姻期間20年超で+0.5 -> -1.5
        return user.marriageDuration > 20 ? -1.5 : -2.0
    default: return 0.0
    }
}

private func adjustmentFromPrefecture(_ user: UserModel) -> Double {
    let table: [String: Double] = [
        "nagano": 2.5, "shiga": 1.8, "fukui": 1.5, "kyoto": 1.2,
        "shizuoka": 1.0, "yamanashi": 0.8, "tokyo": 0.8, "kanagawa": 0.7,
        "aichi": 0.5, "saitama": 0.3, "chiba": 0.2, "osaka": -0.5,
        "hyogo": -0.3, "fukuoka": -0.8, "aomori": -2.0, "akita": -1.8,
        "iwate": -1.5, "okinawa": 0.5
    ]
    if let pref = Prefecture.fromCode(user.currentPrefecture),
       let value = table[pref.rawValue] {
        return value
    }
    if let pref = Prefecture.fromRawValue(user.currentPrefecture),
       let value = table[pref.rawValue] {
        return value
    }
    return 0.0
}

// MARK: - Main Life Expectancy Calculation

func calculateLifeExpectancy(user: UserModel) -> Double? {
    var expectancy: Double = user.gender == "female" ? 87.0 : 81.0
    let adjustments: [Double] = [
        adjustmentFromBMI(user),
        adjustmentFromSmoking(user),
        adjustmentFromDrinking(user),
        adjustmentFromExercise(user),
        adjustmentFromSleep(user),
        adjustmentFromStress(user),
        adjustmentFromDiet(user),
        adjustmentFromBreakfast(user),
        adjustmentFromSitting(user),
        adjustmentFromHealthCheck(user),
        adjustmentFromDental(user),
        adjustmentFromMarital(user),
        adjustmentFromPrefecture(user)
    ]
    for delta in adjustments { expectancy += delta }
    return max(40.0, min(120.0, expectancy))
}
