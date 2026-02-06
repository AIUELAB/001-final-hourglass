import Foundation
import SwiftUI

// MARK: - Health Factor Enum
enum HealthFactor: String, CaseIterable {
    case smoking = "喫煙"
    case drinking = "飲酒"
    case exercise = "運動"
    case diet = "食事"
    case sleep = "睡眠"
    case stress = "ストレス"

    var icon: String {
        switch self {
        case .smoking: return "lungs"
        case .drinking: return "wineglass"
        case .exercise: return "figure.run"
        case .diet: return "leaf"
        case .sleep: return "bed.double"
        case .stress: return "brain.head.profile"
        }
    }

    var color: Color {
        switch self {
        case .smoking: return .red
        case .drinking: return .orange
        case .exercise: return .green
        case .diet: return .blue
        case .sleep: return .purple
        case .stress: return .pink
        }
    }
}

// MARK: - Health Score Model
struct HealthScore {
    let score: Int
    let factors: [HealthFactor: Int]
}

// MARK: - Health Score Calculator
// 複雑な分岐を小関数へ分割して可読性・テスト容易性を向上
private func smokingDelta(for user: UserModel) -> Int {
    switch user.smokingStatus {
    case "current_smoker": return -15
    case "former_smoker": return -5
    case "non_smoker": return 0
    default: return 0
    }
}

private func drinkingDelta(for user: UserModel) -> Int {
    switch user.drinkingFrequency {
    case "daily": return -10
    case "often": return -5
    case "sometimes", "occasionally", "rarely", "never": return 0
    default: return 0
    }
}

private func exerciseDelta(for user: UserModel) -> Int {
    switch user.exerciseFrequency {
    case "daily": return 10
    case "often": return 5
    case "sometimes", "occasionally": return 0
    case "rarely": return -5
    case "never": return -10
    default: return 0
    }
}

private func dietDelta(for user: UserModel) -> Int {
    let dietScore = user.dietHabits.count
    if dietScore >= 4 { return 5 }
    if dietScore >= 2 { return 0 }
    return -5
}

private func sleepDelta(for user: UserModel) -> Int {
    if user.sleepHours >= 7 && user.sleepHours <= 8 { return 0 }
    if user.sleepHours < 6 || user.sleepHours > 9 { return -5 }
    return 0
}

private func stressDelta(for user: UserModel) -> Int {
    switch user.stressLevel {
    case "low": return 5
    case "medium": return 0
    case "high": return -5
    default: return 0
    }
}

func calculateHealthScore(user: UserModel) -> HealthScore {
    var totalScore = 100
    var factors: [HealthFactor: Int] = [:]

    let deltas: [(HealthFactor, Int)] = [
        (.smoking, smokingDelta(for: user)),
        (.drinking, drinkingDelta(for: user)),
        (.exercise, exerciseDelta(for: user)),
        (.diet, dietDelta(for: user)),
        (.sleep, sleepDelta(for: user)),
        (.stress, stressDelta(for: user))
    ]

    for (factor, delta) in deltas {
        totalScore += delta
        factors[factor] = delta
    }

    totalScore = max(0, min(100, totalScore))
    return HealthScore(score: totalScore, factors: factors)
}
