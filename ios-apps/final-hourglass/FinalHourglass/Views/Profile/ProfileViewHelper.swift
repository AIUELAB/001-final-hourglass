import SwiftUI

// MARK: - ProfileViewHelper
/// プロフィール画面で使用するヘルパーメソッド群
/// BMI、喫煙状況、飲酒頻度、運動頻度などの表示テキストと色を提供
struct ProfileViewHelper {
    static func getBMIColor(_ bmi: Double) -> Color {
        switch bmi {
        case ..<18.5:
            return .skyBlue
        case 18.5..<25:
            return .limeGreen
        case 25..<30:
            return .amber
        default:
            return .errorRed
        }
    }

    static func getSmokingStatusText(_ status: String) -> String {
        switch status {
        case "non_smoker":
            return "吸わない"
        case "former_smoker":
            return "以前吸っていた"
        case "current_smoker":
            return "現在吸っている"
        case "smoker":
            return "吸う"
        case "quit":
            return "禁煙した"
        default:
            return "未設定"
        }
    }

    static func getSmokingStatusColor(_ status: String) -> Color {
        switch status {
        case "non_smoker":
            return .limeGreen
        case "former_smoker", "quit":
            return .skyBlue
        case "current_smoker", "smoker":
            return .errorRed
        default:
            return .gray
        }
    }

    static func getDrinkingFrequencyText(_ frequency: String) -> String {
        switch frequency {
        case "never":
            return "飲まない"
        case "rarely":
            return "月1-2回"
        case "sometimes":
            return "週1-2回"
        case "often":
            return "週3-5回"
        case "daily":
            return "ほぼ毎日"
        default:
            return "未設定"
        }
    }

    static func getDrinkingFrequencyColor(_ frequency: String) -> Color {
        switch frequency {
        case "never", "rarely":
            return .limeGreen
        case "sometimes":
            return .amber
        case "often", "daily":
            return .orange
        default:
            return .gray
        }
    }

    static func getExerciseFrequencyText(_ frequency: String) -> String {
        switch frequency {
        case "never":
            return "まったくしない"
        case "rarely":
            return "月1-2回"
        case "sometimes":
            return "週1-2回"
        case "often":
            return "週3-4回"
        case "daily":
            return "ほぼ毎日"
        default:
            return "未設定"
        }
    }

    static func getPrefectureName(_ prefectureValue: String) -> String {
        if let prefecture = Prefecture.fromCode(prefectureValue) {
            return prefecture.name
        }
        if let prefecture = Prefecture.fromRawValue(prefectureValue) {
            return prefecture.name
        }
        return "未設定"
    }

    static func getCommuteTimeText(_ time: String) -> String {
        switch time {
        case "none":
            return "なし"
        case "less_30":
            return "30分未満"
        case "30_to_60":
            return "30-60分"
        case "60_to_90":
            return "60-90分"
        case "over_90":
            return "90分以上"
        default:
            return "未設定"
        }
    }

    static func getStressLevelText(_ level: String) -> String {
        switch level {
        case "low":
            return "低い"
        case "medium":
            return "普通"
        case "high":
            return "高い"
        case "very_high":
            return "とても高い"
        default:
            return "未設定"
        }
    }

    static func getHealthCheckupText(_ frequency: String) -> String {
        switch frequency {
        case "yearly":
            return "年1回以上"
        case "every_2_years":
            return "2年に1回"
        case "every_2_3_years":
            return "2-3年に1回"
        case "rarely":
            return "ほとんど受けない"
        case "never":
            return "受けたことがない"
        default:
            return "未設定"
        }
    }

    static func getDietHabitsText(_ habits: Set<String>) -> String {
        if habits.isEmpty {
            return "未設定"
        }

        let count = habits.count
        let habitDescriptions = [
            "vegetables_daily": "野菜",
            "fruits_daily": "果物",
            "fish_weekly": "魚",
            "limit_processed": "加工食品制限",
            "limit_fastfood": "ファストフード制限",
            "balanced_meals": "バランス食"
        ]

        if count == 1, let habit = habits.first, let desc = habitDescriptions[habit] {
            return desc
        } else {
            return "\(count)項目"
        }
    }

    static func getBreakfastFrequencyText(_ frequency: String) -> String {
        switch frequency {
        case "never":
            return "食べない"
        case "rarely":
            return "たまに"
        case "sometimes":
            return "時々"
        case "often":
            return "ほぼ毎日"
        case "daily":
            return "毎日"
        default:
            return "未設定"
        }
    }

    static func getSittingHoursText(_ hours: String) -> String {
        switch hours {
        case "less_3":
            return "3時間未満"
        case "3_to_6":
            return "3〜6時間"
        case "6_to_9":
            return "6〜9時間"
        case "over_9":
            return "9時間以上"
        default:
            return "未設定"
        }
    }

    static func getDentalCheckupText(_ frequency: String) -> String {
        switch frequency {
        case "biannually":
            return "年2回以上"
        case "yearly":
            return "年1回"
        case "every_2_3_years":
            return "2-3年に1回"
        case "rarely":
            return "ほとんど受けない"
        default:
            return "未設定"
        }
    }

    static func getMaritalStatusText(_ status: String) -> String {
        switch status {
        case "single":
            return "未婚"
        case "married":
            return "既婚"
        case "divorced":
            return "離婚"
        case "widowed":
            return "死別"
        default:
            return "未設定"
        }
    }
}
