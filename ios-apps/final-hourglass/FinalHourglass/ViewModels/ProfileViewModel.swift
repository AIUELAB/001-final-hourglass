import Combine
import Foundation
import SwiftUI

/// プロフィール画面のViewModel
/// ユーザー情報の表示・編集ロジックをViewから分離
@MainActor
final class ProfileViewModel: ObservableObject {
    // MARK: - Published Properties

    /// 編集モード
    @Published var isEditMode: Bool = false

    /// 保存中フラグ
    @Published var isSaving: Bool = false

    /// エラーメッセージ
    @Published var errorMessage: String?

    /// 成功メッセージ
    @Published var successMessage: String?

    // MARK: - Editable Fields (String型でUserModelと互換)

    /// 編集中の生年
    @Published var editingBirthYear: Int = 1990

    /// 編集中の生月
    @Published var editingBirthMonth: Int = 1

    /// 編集中の生日
    @Published var editingBirthDay: Int = 1

    /// 編集中の性別 ("male" or "female")
    @Published var editingGender: String = "male"

    /// 編集中の身長 (cm)
    @Published var editingHeight: Double = 170.0

    /// 編集中の体重 (kg)
    @Published var editingWeight: Double = 65.0

    /// 編集中の喫煙状況
    @Published var editingSmoking: String = "non_smoker"

    /// 編集中の飲酒頻度
    @Published var editingDrinking: String = "sometimes"

    /// 編集中の運動頻度
    @Published var editingExercise: String = "sometimes"

    /// 編集中の睡眠時間
    @Published var editingSleepHours: Int = 7

    /// 編集中の都道府県
    @Published var editingPrefecture: String = "tokyo"

    // MARK: - Private Properties

    private var cancellables = Set<AnyCancellable>()
    private weak var userModel: UserModel?

    // MARK: - Computed Properties

    /// BMI計算
    var bmi: Double {
        let heightInMeters = editingHeight / 100.0
        guard heightInMeters > 0 else { return 0 }
        return editingWeight / (heightInMeters * heightInMeters)
    }

    /// BMIステータス
    var bmiStatus: BMIStatus {
        switch bmi {
        case ..<18.5: return .underweight
        case 18.5..<25: return .normal
        case 25..<30: return .overweight
        default: return .obese
        }
    }

    /// 年齢
    var age: Int {
        let calendar = Calendar.current
        let birthDate = calendar.date(
            from: DateComponents(
                year: editingBirthYear,
                month: editingBirthMonth,
                day: editingBirthDay
            )
        ) ?? Date()
        let now = Date()
        let components = calendar.dateComponents([.year], from: birthDate, to: now)
        return components.year ?? 0
    }

    // MARK: - Initialization

    init() {}

    // MARK: - Public Methods

    /// UserModelからデータを読み込む
    func loadFromUserModel(_ userModel: UserModel) {
        self.userModel = userModel
        editingBirthYear = userModel.birthYear
        editingBirthMonth = userModel.birthMonth
        editingBirthDay = userModel.birthDay
        editingGender = userModel.gender
        editingHeight = userModel.height
        editingWeight = userModel.weight
        editingSmoking = userModel.smokingStatus
        editingDrinking = userModel.drinkingFrequency
        editingExercise = userModel.exerciseFrequency
        editingSleepHours = userModel.sleepHours
        editingPrefecture = userModel.currentPrefecture
    }

    /// 編集モードを開始
    func startEditing() {
        isEditMode = true
        errorMessage = nil
        successMessage = nil
    }

    /// 編集をキャンセル
    func cancelEditing() {
        if let userModel = userModel {
            loadFromUserModel(userModel)
        }
        isEditMode = false
        errorMessage = nil
    }

    /// 変更を保存
    func saveChanges() {
        guard let userModel = userModel else {
            errorMessage = "ユーザーデータが見つかりません"
            return
        }

        // バリデーション
        guard validateInput() else { return }

        isSaving = true
        errorMessage = nil

        // UserModelに反映
        userModel.birthYear = editingBirthYear
        userModel.birthMonth = editingBirthMonth
        userModel.birthDay = editingBirthDay
        userModel.gender = editingGender
        userModel.height = editingHeight
        userModel.weight = editingWeight
        userModel.smokingStatus = editingSmoking
        userModel.drinkingFrequency = editingDrinking
        userModel.exerciseFrequency = editingExercise
        userModel.sleepHours = editingSleepHours
        userModel.currentPrefecture = editingPrefecture

        // BMI再計算
        userModel.calculateBMI()

        // 保存処理
        userModel.saveToUserDefaults()

        isSaving = false
        isEditMode = false
        successMessage = "プロフィールを保存しました"

        // 成功メッセージを3秒後にクリア
        Task {
            try? await Task.sleep(nanoseconds: 3_000_000_000)
            successMessage = nil
        }
    }

    /// プロフィールをリセット
    func resetProfile() {
        userModel?.resetToDefaults()
        if let userModel = userModel {
            loadFromUserModel(userModel)
        }
        successMessage = "プロフィールをリセットしました"
    }

    // MARK: - Private Methods

    /// 入力バリデーション
    private func validateInput() -> Bool {
        // 年齢チェック
        if age < 0 || age > 120 {
            errorMessage = "有効な生年月日を入力してください"
            return false
        }

        // 身長チェック
        if editingHeight < 50 || editingHeight > 300 {
            errorMessage = "身長は50cm〜300cmの範囲で入力してください"
            return false
        }

        // 体重チェック
        if editingWeight < 10 || editingWeight > 500 {
            errorMessage = "体重は10kg〜500kgの範囲で入力してください"
            return false
        }

        // 睡眠時間チェック
        if editingSleepHours < 0 || editingSleepHours > 24 {
            errorMessage = "睡眠時間は0〜24時間の範囲で入力してください"
            return false
        }

        return true
    }
}

// MARK: - BMI Status

extension ProfileViewModel {
    enum BMIStatus: String {
        case underweight = "低体重"
        case normal = "普通体重"
        case overweight = "過体重"
        case obese = "肥満"

        var color: Color {
            switch self {
            case .underweight: return .blue
            case .normal: return .green
            case .overweight: return .orange
            case .obese: return .red
            }
        }
    }
}

// MARK: - Formatting Helpers

extension ProfileViewModel {
    /// 身長をフォーマット
    var formattedHeight: String {
        String(format: "%.1f cm", editingHeight)
    }

    /// 体重をフォーマット
    var formattedWeight: String {
        String(format: "%.1f kg", editingWeight)
    }

    /// BMIをフォーマット
    var formattedBMI: String {
        String(format: "%.1f", bmi)
    }

    /// 睡眠時間をフォーマット
    var formattedSleepHours: String {
        "\(editingSleepHours) 時間"
    }

    /// 生年月日をフォーマット
    var formattedBirthDate: String {
        "\(editingBirthYear)年\(editingBirthMonth)月\(editingBirthDay)日"
    }

    /// 年齢をフォーマット
    var formattedAge: String {
        "\(age)歳"
    }

    /// 性別をフォーマット
    var formattedGender: String {
        editingGender == "male" ? "男性" : "女性"
    }
}
