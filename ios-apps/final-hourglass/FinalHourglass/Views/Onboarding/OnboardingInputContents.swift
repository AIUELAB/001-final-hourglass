import SwiftUI

// MARK: - 共通のステップビュー（神秘的デザイン）
struct OnboardingStepView<Content: View>: View {
    let title: String
    let subtitle: String
    @Binding var currentPage: Int
    let showBackButton: Bool
    let content: Content

    init(title: String, subtitle: String, currentPage: Binding<Int>, showBackButton: Bool = true, @ViewBuilder content: () -> Content) {
        self.title = title
        self.subtitle = subtitle
        self._currentPage = currentPage
        self.showBackButton = showBackButton
        self.content = content()
    }

    var body: some View {
        VStack(spacing: 0) {
            // ヘッダー
            VStack(spacing: 15) {
                Text(title)
                    .font(.system(size: 32, weight: .thin, design: .serif))
                    .foregroundColor(.white)
                    .shadow(color: Color.AppColors.mediumPurple.opacity(0.3), radius: 5)

                Text(subtitle)
                    .font(.system(size: 14, weight: .light))
                    .foregroundColor(.gray)
            }
            .padding(.top, 60)
            .padding(.bottom, 30)

            // コンテンツ
            content

            Spacer()

            // 戻るボタン
            if showBackButton {
                Button(action: {
                    // タップ音（戻る）
                    SoundManager.shared.playTapSound(.cancel)

                    withAnimation(.easeInOut(duration: 0.3)) {
                        currentPage -= 1
                    }
                }) {
                    HStack {
                        Image(systemName: "chevron.left")
                        Text("戻る")
                    }
                    .font(.system(size: 14))
                    .foregroundColor(AppColors.mediumPurple.opacity(0.6))
                }
                .padding(.bottom, 60)
            }
        }
    }
}

// MARK: - 各入力コンテンツ

// MARK: - 生年月日入力
struct BirthdayInputContent: View {
    @Binding var birthDate: Date
    let onNext: () -> Void

    private var dateRange: ClosedRange<Date> {
        let calendar = Calendar.current
        let endDate = Date()
        let startDate = calendar.date(byAdding: .year, value: -100, to: endDate) ?? endDate
        return startDate...endDate
    }

    var body: some View {
        VStack(spacing: 30) {
            ZStack {
                RoundedRectangle(cornerRadius: 20)
                    .fill(Color.black.opacity(0.3))
                    .overlay(
                        RoundedRectangle(cornerRadius: 20)
                            .stroke(AppColors.mediumPurple.opacity(0.3), lineWidth: 1)
                    )

                DatePicker(
                    "",
                    selection: $birthDate,
                    in: dateRange,
                    displayedComponents: .date
                )
                .datePickerStyle(WheelDatePickerStyle())
                .labelsHidden()
                .colorScheme(.dark)
                .environment(\.locale, Locale(identifier: "ja_JP"))
                .scaleEffect(1.1)
                .padding()
            }
            .frame(height: 220)
            .padding(.horizontal, 30)

            Text(dateFormatter.string(from: birthDate))
                .font(.system(size: 18, weight: .light))
                .foregroundColor(.white)
                .opacity(0.8)

            MysticalNextButton(title: "次へ", action: onNext)
        }
    }

    private var dateFormatter: DateFormatter {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "ja_JP")
        formatter.dateStyle = .long
        return formatter
    }
}

// MARK: - 性別入力
struct GenderInputContent: View {
    @Binding var gender: String
    let onNext: () -> Void

    var body: some View {
        VStack(spacing: 20) {
            MysticalSelectionButton(
                title: "男性",
                icon: "person.fill",
                isSelected: gender == "male",
                action: {
                    gender = "male"
                    onNext()
                }
            )

            MysticalSelectionButton(
                title: "女性",
                icon: "person.fill",
                isSelected: gender == "female",
                action: {
                    gender = "female"
                    onNext()
                }
            )
        }
        .padding(.horizontal, 40)
    }
}

// MARK: - 身長入力
struct HeightInputContent: View {
    @Binding var height: Double
    let onNext: () -> Void

    @State private var tempHeight: Double = 170.0

    var body: some View {
        VStack(spacing: 40) {
            // ビジュアル表示
            ZStack {
                Circle()
                    .fill(Color.black.opacity(0.3))
                    .overlay(
                        Circle()
                            .stroke(AppColors.mediumPurple.opacity(0.3), lineWidth: 2)
                    )
                    .frame(width: 200, height: 200)

                VStack(spacing: 10) {
                    Image(systemName: "ruler.fill")
                        .font(.system(size: 60))
                        .foregroundStyle(
                            LinearGradient(
                                colors: [AppColors.mediumPurple, AppColors.cornflowerBlue],
                                startPoint: .top,
                                endPoint: .bottom
                            )
                        )

                    Text("\(Int(tempHeight)) cm")
                        .font(.system(size: 32, weight: .medium))
                        .foregroundColor(.white)
                }
            }

            // スライダー
            VStack(spacing: 20) {
                Slider(value: $tempHeight, in: 120...220, step: 1)
                    .accentColor(AppColors.mediumPurple)
                    .padding(.horizontal, 40)

                HStack {
                    Text("120 cm")
                        .font(.caption)
                        .foregroundColor(.gray)
                    Spacer()
                    Text("220 cm")
                        .font(.caption)
                        .foregroundColor(.gray)
                }
                .padding(.horizontal, 40)
            }

            // 日本人の平均身長
            HStack {
                Image(systemName: "info.circle")
                    .foregroundColor(AppColors.cornflowerBlue)
                Text("日本人平均: 男性171cm / 女性158cm")
                    .font(.caption)
                    .foregroundColor(.gray)
            }

            MysticalNextButton(title: "次へ", action: {
                height = tempHeight
                onNext()
            })
        }
        .onAppear {
            tempHeight = height
        }
    }
}

// MARK: - 体重入力
struct WeightInputContent: View {
    @Binding var weight: Double
    let height: Double
    @Binding var bmi: Double
    let onNext: () -> Void

    @State private var tempWeight: Double = 65.0

    var body: some View {
        VStack(spacing: 40) {
            // ビジュアル表示
            ZStack {
                Circle()
                    .fill(Color.black.opacity(0.3))
                    .overlay(
                        Circle()
                            .stroke(AppColors.mediumPurple.opacity(0.3), lineWidth: 2)
                    )
                    .frame(width: 200, height: 200)

                VStack(spacing: 10) {
                    Image(systemName: "scalemass.fill")
                        .font(.system(size: 60))
                        .foregroundStyle(
                            LinearGradient(
                                colors: [AppColors.mediumPurple, AppColors.cornflowerBlue],
                                startPoint: .top,
                                endPoint: .bottom
                            )
                        )

                    Text("\(String(format: "%.1f", tempWeight)) kg")
                        .font(.system(size: 32, weight: .medium))
                        .foregroundColor(.white)

                    // BMI表示
                    Text("BMI: \(String(format: "%.1f", calculateBMI()))")
                        .font(.system(size: 16, weight: .medium))
                        .foregroundColor(getBMIColor())
                }
            }

            // スライダー
            VStack(spacing: 20) {
                Slider(value: $tempWeight, in: 30...150, step: 0.5)
                    .accentColor(AppColors.mediumPurple)
                    .padding(.horizontal, 40)

                HStack {
                    Text("30 kg")
                        .font(.caption)
                        .foregroundColor(.gray)
                    Spacer()
                    Text("150 kg")
                        .font(.caption)
                        .foregroundColor(.gray)
                }
                .padding(.horizontal, 40)
            }

            // BMI判定
            HStack {
                Image(systemName: "info.circle")
                    .foregroundColor(AppColors.cornflowerBlue)
                Text(getBMIStatus())
                    .font(.caption)
                    .foregroundColor(.gray)
            }

            MysticalNextButton(title: "次へ", action: {
                weight = tempWeight
                bmi = calculateBMI()
                onNext()
            })
        }
        .onAppear {
            tempWeight = weight
        }
    }

    private func calculateBMI() -> Double {
        let heightInMeters = height / 100
        if heightInMeters > 0 {
            return tempWeight / (heightInMeters * heightInMeters)
        }
        return 0
    }

    private func getBMIColor() -> Color {
        let bmi = calculateBMI()
        switch bmi {
        case ..<18.5:
            return AppColors.cornflowerBlue
        case 18.5..<25:
            return Color(hex: "32CD32")
        case 25..<30:
            return AppColors.amber
        default:
            return AppColors.deepCrimson
        }
    }

    private func getBMIStatus() -> String {
        let bmi = calculateBMI()
        switch bmi {
        case ..<18.5:
            return "低体重"
        case 18.5..<25:
            return "標準体重"
        case 25..<30:
            return "肥満（1度）"
        default:
            return "肥満（2度以上）"
        }
    }
}

// MARK: - 喫煙習慣入力
struct SmokingInputContent: View {
    @Binding var smokingStatus: String
    let onNext: () -> Void

    @State private var showingSmokingDuration = false
    @State private var smokingYears: Int = 0

    let options = [
        ("non_smoker", "吸わない", "nosign"),
        ("former_smoker", "以前吸っていた", "clock.arrow.circlepath"),
        ("current_smoker", "現在吸っている", "flame")
    ]

    var body: some View {
        VStack(spacing: 15) {
            ForEach(options, id: \.0) { value, title, icon in
                MysticalSelectionButton(
                    title: title,
                    icon: icon,
                    isSelected: smokingStatus == value,
                    action: {
                        smokingStatus = value
                        if value == "former_smoker" {
                            withAnimation {
                                showingSmokingDuration = true
                            }
                        } else {
                            showingSmokingDuration = false
                            smokingYears = 0
                            onNext()
                        }
                    }
                )
            }
            .padding(.horizontal, 40)

            // 喫煙期間の入力（元喫煙者の場合）
            if showingSmokingDuration {
                VStack(spacing: 20) {
                    Divider()
                        .background(Color.gray.opacity(0.3))
                        .padding(.horizontal, 40)

                    Text("喫煙していた期間")
                        .font(.system(size: 18, weight: .medium))
                        .foregroundColor(.white)

                    Text("\(smokingYears)年")
                        .font(.system(size: 32, weight: .bold))
                        .foregroundColor(AppColors.deepCrimson)
                        .padding(.vertical, 10)

                    VStack(spacing: 10) {
                        Slider(value: Binding(
                            get: { Double(smokingYears) },
                            set: { smokingYears = Int($0) }
                        ), in: 0...50, step: 1)
                        .accentColor(AppColors.mediumPurple)
                        .padding(.horizontal, 40)

                        HStack {
                            Text("0年")
                                .font(.caption)
                                .foregroundColor(.gray)
                            Spacer()
                            Text("50年")
                                .font(.caption)
                                .foregroundColor(.gray)
                        }
                        .padding(.horizontal, 40)
                    }

                    MysticalNextButton(title: "次へ", action: {
                        // UserModelに喫煙期間を保存
                        UserDefaults.standard.set(smokingYears, forKey: "smokingYears")
                        onNext()
                    })
                    .padding(.top, 20)
                }
                .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
    }
}

// MARK: - 飲酒習慣入力
struct DrinkingInputContent: View {
    @Binding var drinkingFrequency: String
    let onNext: () -> Void

    let options = [
        ("never", "飲まない", "nosign"),
        ("rarely", "月1〜2回", "calendar"),
        ("sometimes", "週1〜2回", "calendar.badge.plus"),
        ("often", "週3〜5回", "calendar.circle"),
        ("daily", "ほぼ毎日", "calendar.circle.fill")
    ]

    var body: some View {
        VStack(spacing: 12) {
            ForEach(options, id: \.0) { value, title, icon in
                MysticalSelectionButton(
                    title: title,
                    icon: icon,
                    isSelected: drinkingFrequency == value,
                    action: {
                        drinkingFrequency = value
                        onNext()
                    }
                )
            }
        }
        .padding(.horizontal, 40)
    }
}

// MARK: - 運動習慣入力
struct ExerciseInputContent: View {
    @Binding var exerciseFrequency: String
    let onNext: () -> Void

    let options = [
        ("never", "まったくしない", "zzz"),
        ("rarely", "月1〜2回", "figure.walk"),
        ("sometimes", "週1〜2回", "figure.walk.motion"),
        ("often", "週3〜4回", "figure.run"),
        ("daily", "ほぼ毎日", "figure.run.circle.fill")
    ]

    var body: some View {
        VStack(spacing: 12) {
            ForEach(options, id: \.0) { value, title, icon in
                MysticalSelectionButton(
                    title: title,
                    icon: icon,
                    isSelected: exerciseFrequency == value,
                    action: {
                        exerciseFrequency = value
                        onNext()
                    }
                )
            }
        }
        .padding(.horizontal, 40)
    }
}

// MARK: - ストレスレベル入力
struct StressLevelInputContent: View {
    @Binding var stressLevel: String
    let onNext: () -> Void

    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "brain.head.profile")
                .font(.system(size: 60))
                .foregroundStyle(
                    LinearGradient(
                        colors: [AppColors.mediumPurple, AppColors.cornflowerBlue],
                        startPoint: .top,
                        endPoint: .bottom
                    )
                )
                .padding(.bottom, 20)

            ForEach(
                [
                    ("low", "低い", "face.smiling"),
                    ("medium", "普通", "circle"),
                    ("high", "高い", "exclamationmark.triangle")
                ],
                id: \.0
            ) { value, title, icon in
                MysticalSelectionButton(
                    title: title,
                    icon: icon,
                    isSelected: stressLevel == value,
                    action: {
                        stressLevel = value
                        onNext()
                    }
                )
            }
        }
        .padding(.horizontal, 40)
    }
}

// MARK: - 睡眠時間入力
struct SleepInputContent: View {
    @Binding var sleepHours: Int
    let onNext: () -> Void

    @State private var tempHours: Double = 7.0

    var body: some View {
        VStack(spacing: 40) {
            // ビジュアル表示
            ZStack {
                Circle()
                    .fill(Color.black.opacity(0.3))
                    .overlay(
                        Circle()
                            .stroke(AppColors.mediumPurple.opacity(0.3), lineWidth: 2)
                    )
                    .frame(width: 200, height: 200)

                VStack(spacing: 10) {
                    Image(systemName: "moon.zzz.fill")
                        .font(.system(size: 60))
                        .foregroundStyle(
                            LinearGradient(
                                colors: [AppColors.mediumPurple, AppColors.cornflowerBlue],
                                startPoint: .top,
                                endPoint: .bottom
                            )
                        )

                    Text("\(String(format: "%.1f", tempHours))時間")
                        .font(.system(size: 28, weight: .medium))
                        .foregroundColor(.white)
                }
            }

            // スライダー
            VStack(spacing: 20) {
                Slider(value: $tempHours, in: 3...12, step: 0.5)
                    .accentColor(AppColors.mediumPurple)
                    .padding(.horizontal, 40)

                HStack {
                    Text("3時間")
                        .font(.caption)
                        .foregroundColor(.gray)
                    Spacer()
                    Text("12時間")
                        .font(.caption)
                        .foregroundColor(.gray)
                }
                .padding(.horizontal, 40)
            }

            // 推奨情報
            HStack {
                Image(systemName: "info.circle")
                    .foregroundColor(AppColors.cornflowerBlue)
                Text("推奨: 7〜9時間")
                    .font(.caption)
                    .foregroundColor(.gray)
            }

            MysticalNextButton(title: "次へ", action: {
                sleepHours = Int(tempHours)
                onNext()
            })
        }
        .onAppear {
            tempHours = Double(sleepHours)
        }
    }
}

// MARK: - 食生活入力
struct DietInputContent: View {
    @Binding var dietHabits: Set<String>
    let onNext: () -> Void

    let dietOptions = [
        ("vegetables_daily", "野菜を毎日食べる", "leaf"),
        ("fruits_daily", "果物を毎日食べる", "apple.logo"),
        ("fish_weekly", "魚を週2回以上食べる", "fish"),
        ("limit_processed", "加工食品を控えている", "xmark.circle"),
        ("limit_fastfood", "ファストフードは月1回以下", "takeoutbag.and.cup.and.straw"),
        ("balanced_meals", "栄養バランスを意識している", "checkmark.seal")
    ]

    var body: some View {
        VStack(spacing: 25) {
            Text("当てはまるものを選択してください")
                .font(.system(size: 16, weight: .medium))
                .foregroundColor(.gray)
                .padding(.bottom, 10)

            VStack(spacing: 15) {
                ForEach(dietOptions, id: \.0) { value, title, icon in
                    MysticalDietCheckButton(
                        title: title,
                        icon: icon,
                        isSelected: dietHabits.contains(value),
                        action: {
                            if dietHabits.contains(value) {
                                dietHabits.remove(value)
                            } else {
                                dietHabits.insert(value)
                            }
                        }
                    )
                }
            }
            .padding(.horizontal, 30)

            // 選択数の表示
            Text("\(dietHabits.count)個選択中")
                .font(.caption)
                .foregroundColor(.gray)
                .padding(.top, 10)

            MysticalNextButton(title: "次へ", action: onNext)
                .padding(.top, 20)
        }
    }
}

// MARK: - 朝食習慣入力
struct BreakfastInputContent: View {
    @Binding var breakfastFrequency: String
    let onNext: () -> Void

    let options = [
        ("never", "食べない", "xmark.circle"),
        ("rarely", "たまに", "circle.badge.questionmark"),
        ("sometimes", "時々", "circle.lefthalf.filled"),
        ("often", "ほぼ毎日", "circle.righthalf.filled"),
        ("daily", "毎日", "checkmark.circle.fill")
    ]

    var body: some View {
        VStack(spacing: 15) {
            ForEach(options, id: \.0) { value, title, icon in
                MysticalSelectionButton(
                    title: title,
                    icon: icon,
                    isSelected: breakfastFrequency == value,
                    action: {
                        breakfastFrequency = value
                        onNext()
                    }
                )
            }
        }
        .padding(.horizontal, 40)
    }
}

// MARK: - 座位時間入力
struct SittingHoursInputContent: View {
    @Binding var sittingHours: String
    let onNext: () -> Void

    let options = [
        ("less_3", "3時間未満", "figure.walk"),
        ("3_to_6", "3〜6時間", "person.fill"),
        ("6_to_9", "6〜9時間", "person.fill"),
        ("over_9", "9時間以上", "person.fill")
    ]

    var body: some View {
        VStack(spacing: 20) {
            // イラスト
            Image(systemName: "clock.fill")
                .font(.system(size: 60))
                .foregroundStyle(
                    LinearGradient(
                        colors: [AppColors.amber.opacity(0.7), AppColors.deepCrimson.opacity(0.7)],
                        startPoint: .top,
                        endPoint: .bottom
                    )
                )
                .padding(.bottom, 20)

            VStack(spacing: 15) {
                ForEach(options, id: \.0) { value, title, icon in
                    MysticalSelectionButton(
                        title: title,
                        icon: icon,
                        isSelected: sittingHours == value,
                        action: {
                            print("座位時間選択: \(value)")
                            sittingHours = value
                            DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                                onNext()
                            }
                        }
                    )
                }
            }

            // 健康情報
            HStack {
                Image(systemName: "exclamationmark.triangle")
                    .foregroundColor(AppColors.amber)
                Text("長時間の座位は健康リスクを高めます")
                    .font(.caption)
                    .foregroundColor(.gray)
            }
            .padding(.top, 10)
        }
        .padding(.horizontal, 40)
    }
}

// MARK: - 都道府県入力
struct PrefectureInputContent: View {
    @Binding var currentPrefecture: String
    let onNext: () -> Void

    @State private var showingPicker = false

    var body: some View {
        VStack(spacing: 30) {
            // 地図アイコン
            Image(systemName: "map.fill")
                .font(.system(size: 60))
                .foregroundStyle(
                    LinearGradient(
                        colors: [AppColors.mediumPurple, AppColors.cornflowerBlue],
                        startPoint: .top,
                        endPoint: .bottom
                    )
                )
                .padding(.bottom, 10)

            // 選択した都道府県の表示
            if let prefecture = Prefecture.fromCode(currentPrefecture) ?? Prefecture.fromRawValue(currentPrefecture) {
                VStack(spacing: 10) {
                    Text(prefecture.name)
                        .font(.system(size: 24, weight: .medium))
                        .foregroundColor(.white)

                    Text(prefecture.region.rawValue)
                        .font(.caption)
                        .foregroundColor(.gray)
                }
                .padding()
                .background(
                    RoundedRectangle(cornerRadius: 15)
                        .fill(AppColors.mediumPurple.opacity(0.2))
                        .overlay(
                            RoundedRectangle(cornerRadius: 15)
                                .stroke(AppColors.mediumPurple, lineWidth: 1)
                        )
                )
            } else {
                // 未選択時の表示
                VStack(spacing: 10) {
                    Text("都道府県を選択してください")
                        .font(.system(size: 18, weight: .medium))
                        .foregroundColor(.gray)

                    Text("正確な寿命予測のために必要です")
                        .font(.caption)
                        .foregroundColor(.gray.opacity(0.7))
                }
                .padding()
            }

            // 選択ボタン
            Button(action: {
                // タップ音（選択）
                SoundManager.shared.playTapSound(.soft)
                showingPicker = true
            }) {
                HStack {
                    Image(systemName: "location.circle")
                    Text(
                        currentPrefecture.isEmpty ||
                            (Prefecture.fromCode(currentPrefecture) ??
                                Prefecture.fromRawValue(currentPrefecture)) == nil
                            ? "都道府県を選択"
                            : "変更する"
                    )
                }
                .foregroundColor(.white)
                .padding(.horizontal, 30)
                .padding(.vertical, 15)
                .background(
                    RoundedRectangle(cornerRadius: 25)
                        .fill(AppColors.mediumPurple.opacity(0.3))
                )
            }

            // 次へボタン
            MysticalNextButton(
                title: "次へ",
                action: onNext,
                isEnabled: !currentPrefecture.isEmpty &&
                    ((Prefecture.fromCode(currentPrefecture) ??
                        Prefecture.fromRawValue(currentPrefecture)) != nil)
            )
        }
        .sheet(isPresented: $showingPicker) {
            PrefecturePickerView(
                selectedPrefecture: $currentPrefecture,
                isPresented: $showingPicker
            )
        }
        .onAppear {
            // デフォルト値の設定（必要に応じて）
            if currentPrefecture.isEmpty {
                // 初期値は空のままにしておく（ユーザーに選択を促す）
            }
        }
    }
}

// MARK: - 健康診断入力
struct HealthCheckupInputContent: View {
    @Binding var healthCheckupFrequency: String
    @Binding var dentalCheckupFrequency: String
    let onNext: () -> Void

    @State private var currentSubStep = 0

    var body: some View {
        VStack {
            switch currentSubStep {
            case 0:
                // 健康診断頻度
                VStack(spacing: 20) {
                    Image(systemName: "stethoscope")
                        .font(.system(size: 50))
                        .foregroundStyle(
                            LinearGradient(
                                colors: [AppColors.mediumPurple, AppColors.cornflowerBlue],
                                startPoint: .top,
                                endPoint: .bottom
                            )
                        )
                        .padding(.bottom, 10)

                    Text("健康診断の受診頻度")
                        .font(.system(size: 20, weight: .medium))
                        .foregroundColor(.white)

                    ForEach([
                        ("yearly", "年1回以上", "checkmark.circle"),
                        ("every_2_3_years", "2〜3年に1回", "circle"),
                        ("rarely", "ほとんど受けない", "xmark.circle")
                    ], id: \.0) { value, title, icon in
                        MysticalSelectionButton(
                            title: title,
                            icon: icon,
                            isSelected: healthCheckupFrequency == value,
                            action: {
                                print("健康診断頻度選択: \(value)")
                                healthCheckupFrequency = value
                                withAnimation {
                                    currentSubStep = 1
                                }
                            }
                        )
                    }
                }
                .padding(.horizontal, 40)

            case 1:
                // 歯科検診頻度
                VStack(spacing: 20) {
                    Image(systemName: "mouth.fill")
                        .font(.system(size: 50))
                        .foregroundStyle(
                            LinearGradient(
                                colors: [AppColors.mediumPurple, AppColors.cornflowerBlue],
                                startPoint: .top,
                                endPoint: .bottom
                            )
                        )
                        .padding(.bottom, 10)

                    Text("歯科検診の受診頻度")
                        .font(.system(size: 20, weight: .medium))
                        .foregroundColor(.white)

                    ForEach([
                        ("biannually", "年2回以上", "star.circle.fill"),
                        ("yearly", "年1回", "checkmark.circle"),
                        ("every_2_3_years", "2〜3年に1回", "circle"),
                        ("rarely", "ほとんど受けない", "xmark.circle")
                    ], id: \.0) { value, title, icon in
                        MysticalSelectionButton(
                            title: title,
                            icon: icon,
                            isSelected: dentalCheckupFrequency == value,
                            action: {
                                print("歯科検診頻度選択: \(value)")
                                dentalCheckupFrequency = value
                                DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                                    onNext()
                                }
                            }
                        )
                    }
                }
                .padding(.horizontal, 40)

            default:
                EmptyView()
            }
        }
        .transition(.slide)
        .onAppear {
            print("健康診断入力画面表示 - サブステップ: \(currentSubStep)")
        }
    }
}
