import SwiftUI

// MARK: - アイコンの光沢効果
struct ProfileIconShimmer: View {
    @Binding var shimmerOffset: CGFloat

    var body: some View {
        RoundedRectangle(cornerRadius: 6)
            .fill(
                LinearGradient(
                    gradient: Gradient(colors: [
                        Color.white.opacity(0),
                        Color.white.opacity(0.3),
                        Color.white.opacity(0)
                    ]),
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
            )
            .frame(width: 28, height: 28)
            .offset(x: shimmerOffset * 40, y: shimmerOffset * 40)
            .mask(
                RoundedRectangle(cornerRadius: 6)
                    .frame(width: 28, height: 28)
            )
            .onAppear {
                withAnimation(
                    Animation.linear(duration: 3)
                        .repeatForever(autoreverses: false)
                ) {
                    shimmerOffset = 1
                }
            }
    }
}

// MARK: - プロフィールヘッダー
struct ProfileHeaderView: View {
    // periphery:ignore - View dependency/UI component
    @EnvironmentObject var userModel: UserModel

    var body: some View {
        VStack(spacing: 15) {
            // プロフィールアイコン
            ZStack {
                Circle()
                    .fill(
                        LinearGradient(
                            colors: [Color.mysticalPurple.opacity(0.3), Color.mysticBlue.opacity(0.2)],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(width: 100, height: 100)
                    .overlay(
                        Circle()
                            .stroke(Color.mysticalPurple.opacity(0.5), lineWidth: 1)
                    )
                    .shadow(color: Color.mysticalPurple.opacity(0.5), radius: 20)

                Image(systemName: "person.fill")
                    .font(.system(size: 50))
                    .foregroundStyle(
                        LinearGradient(
                            colors: [Color.mysticalPurple, Color.mysticBlue],
                            startPoint: .top,
                            endPoint: .bottom
                        )
                    )
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 30)
        .listRowBackground(Color.clear)
        .listRowInsets(EdgeInsets())
    }
}

// MARK: - メインビュー
struct ProfileView: View {
    @EnvironmentObject var userModel: UserModel
    @State private var isEditMode = false

    var body: some View {
        ZStack {
            // 背景を先に配置
            MysticalSpaceBackground()
                .ignoresSafeArea()

            List {
                // プロフィールヘッダー
                ProfileHeaderView()

                // 基本情報セクション
                BasicInfoSection(isEditMode: isEditMode)
                    .accessibilityIdentifier("profile_section_basic")

                // 身体情報セクション
                BodyInfoSection(isEditMode: isEditMode)

                // 生活習慣セクション
                LifestyleSection(isEditMode: isEditMode)

                // 地域情報セクション
                LocationSection(isEditMode: isEditMode)

                // 健康状態セクション
                HealthSection(isEditMode: isEditMode)

                // 個人情報セクション
                PersonalInfoSection(isEditMode: isEditMode)
            }
            .listStyle(PlainListStyle())
            // .scrollContentBackground(.hidden) // iOS 16.0+ only
            .listRowSeparator(.hidden)
            .listSectionSeparator(.hidden)
            .environment(\.defaultMinListRowHeight, 44)
            .onAppear {
                // UITableViewの外観をカスタマイズ
                UITableView.appearance().backgroundColor = .clear
                UITableView.appearance().separatorStyle = .none
                UITableViewCell.appearance().backgroundColor = .clear
                UITableView.appearance().separatorColor = .clear
            }
            .navigationTitle("プロフィール")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(isEditMode ? "完了" : "編集") {
                        // タップ音
                        SoundManager.shared.playTapSound(isEditMode ? .success : .soft)
                        withAnimation {
                            isEditMode.toggle()
                            if !isEditMode {
                                // 編集完了時にUserDefaultsに保存
                                userModel.saveToUserDefaults()
                            }
                        }
                    }
                    .foregroundColor(Color.mysticalPurple)
                    .accessibilityIdentifier("profile_edit_button")
                }
            }
        }
        .onAppear {
            // 画面表示時にUserDefaultsから読み込み
            userModel.loadFromUserDefaults()
        }
    }
}

// MARK: - 基本情報セクション
struct BasicInfoSection: View {
    @EnvironmentObject var userModel: UserModel
    let isEditMode: Bool

    var body: some View {
        Section(header:
                    Text("基本情報")
            .foregroundColor(Color.mysticalPurple.opacity(0.8))
            .font(.system(size: 13, weight: .regular))
            .textCase(.uppercase)
            .shadow(color: Color.mysticalPurple.opacity(0.4), radius: 4)
        ) {
            VStack(spacing: 0) {
                // 生年月日（編集不可）
                ProfileNavigationRow(
                    icon: AnyView(
                        Image(systemName: "calendar")
                            .foregroundColor(.white.opacity(0.9))
                            .font(.system(size: 16))
                    ),
                    title: "生年月日",
                    value: "\(userModel.birthYear)年\(userModel.birthMonth)月\(userModel.birthDay)日",
                    backgroundColor: Color.mysticBlue.opacity(0.2),
                    borderColor: Color.mysticBlue.opacity(0.3),
                    glowColor: Color.mysticBlue,
                    isEditMode: isEditMode,
                    destination: BirthdayEditView()
                )

                ProfileItemDivider()

                // 性別
                ProfileNavigationRow(
                    icon: AnyView(
                        Image(systemName: "person.2")
                            .foregroundColor(.white.opacity(0.9))
                            .font(.system(size: 16))
                    ),
                    title: "性別",
                    value: userModel.gender == "male" ? "男性" : "女性",
                    backgroundColor: Color.mysticalPurple.opacity(0.2),
                    borderColor: Color.mysticalPurple.opacity(0.3),
                    glowColor: Color.mysticalPurple,
                    isEditMode: isEditMode,
                    destination: GenderEditView()
                )
            }
            .background(
                RoundedRectangle(cornerRadius: 14)
                    .fill(Color(white: 0.11, opacity: 0.4))
                    .overlay(
                        RoundedRectangle(cornerRadius: 14)
                            .stroke(Color.mysticalPurple.opacity(0.1), lineWidth: 1)
                    )
            )
            .listRowBackground(Color.clear)
            .listRowInsets(EdgeInsets(top: 0, leading: 20, bottom: 16, trailing: 20))
        }
    }
}

// MARK: - 身体情報セクション
struct BodyInfoSection: View {
    @EnvironmentObject var userModel: UserModel
    let isEditMode: Bool

    var body: some View {
        Section(header:
                    Text("身体情報")
            .foregroundColor(Color.mysticalPurple.opacity(0.8))
            .font(.system(size: 13, weight: .regular))
            .textCase(.uppercase)
            .shadow(color: Color.mysticalPurple.opacity(0.4), radius: 4)
        ) {
            VStack(spacing: 0) {
                // 身長
                ProfileNavigationRow(
                    icon: AnyView(
                        Image(systemName: "ruler")
                            .foregroundColor(.white.opacity(0.9))
                            .font(.system(size: 16))
                    ),
                    title: "身長",
                    value: String(format: "%.1f cm", userModel.height),
                    backgroundColor: Color.skyBlue.opacity(0.2),
                    borderColor: Color.skyBlue.opacity(0.3),
                    glowColor: Color.skyBlue,
                    isEditMode: isEditMode,
                    destination: HeightEditView()
                )

                ProfileItemDivider()

                // 体重
                ProfileNavigationRow(
                    icon: AnyView(
                        Image(systemName: "scalemass")
                            .foregroundColor(.white.opacity(0.9))
                            .font(.system(size: 16))
                    ),
                    title: "体重",
                    value: String(format: "%.1f kg", userModel.weight),
                    backgroundColor: Color.skyBlue.opacity(0.2),
                    borderColor: Color.skyBlue.opacity(0.3),
                    glowColor: Color.skyBlue,
                    isEditMode: isEditMode,
                    destination: WeightEditView()
                )

                ProfileItemDivider()

                // BMI
                ProfileInfoRow(
                    icon: AnyView(
                        Image(systemName: "chart.bar.fill")
                            .foregroundColor(.white.opacity(0.9))
                            .font(.system(size: 16))
                    ),
                    title: "BMI",
                    value: String(format: "%.1f", userModel.bmi),
                    valueColor: ProfileViewHelper.getBMIColor(userModel.bmi),
                    backgroundColor: ProfileViewHelper.getBMIColor(userModel.bmi).opacity(0.2),
                    borderColor: ProfileViewHelper.getBMIColor(userModel.bmi).opacity(0.3),
                    glowColor: ProfileViewHelper.getBMIColor(userModel.bmi),
                    showChevron: false
                )
            }
            .background(
                RoundedRectangle(cornerRadius: 14)
                    .fill(Color(white: 0.11, opacity: 0.4))
                    .overlay(
                        RoundedRectangle(cornerRadius: 14)
                            .stroke(Color.mysticalPurple.opacity(0.1), lineWidth: 1)
                    )
            )
            .listRowBackground(Color.clear)
            .listRowInsets(EdgeInsets(top: 0, leading: 20, bottom: 16, trailing: 20))
        }
    }
}

// MARK: - 生活習慣セクション
struct LifestyleSection: View {
    @EnvironmentObject var userModel: UserModel
    let isEditMode: Bool

    var body: some View {
        Section(header:
                    Text("生活習慣")
            .foregroundColor(Color.mysticalPurple.opacity(0.8))
            .font(.system(size: 13, weight: .regular))
            .textCase(.uppercase)
            .shadow(color: Color.mysticalPurple.opacity(0.4), radius: 4)
        ) {
            VStack(spacing: 0) {
                // 喫煙
                ProfileNavigationRow(
                    icon: AnyView(
                        Image(systemName: "smoke")
                            .foregroundColor(.white.opacity(0.9))
                            .font(.system(size: 16))
                    ),
                    title: "喫煙",
                    value: ProfileViewHelper.getSmokingStatusText(userModel.smokingStatus),
                    statusColor: ProfileViewHelper.getSmokingStatusColor(userModel.smokingStatus),
                    backgroundColor: ProfileViewHelper.getSmokingStatusColor(userModel.smokingStatus).opacity(0.2),
                    borderColor: ProfileViewHelper.getSmokingStatusColor(userModel.smokingStatus).opacity(0.3),
                    glowColor: ProfileViewHelper.getSmokingStatusColor(userModel.smokingStatus),
                    isEditMode: isEditMode,
                    destination: SmokingEditView()
                )

                ProfileItemDivider()

                // 飲酒
                ProfileNavigationRow(
                    icon: AnyView(
                        Image(systemName: "wineglass")
                            .foregroundColor(.white.opacity(0.9))
                            .font(.system(size: 16))
                    ),
                    title: "飲酒",
                    value: ProfileViewHelper.getDrinkingFrequencyText(userModel.drinkingFrequency),
                    statusColor: ProfileViewHelper.getDrinkingFrequencyColor(userModel.drinkingFrequency),
                    backgroundColor: ProfileViewHelper.getDrinkingFrequencyColor(userModel.drinkingFrequency).opacity(0.2),
                    borderColor: ProfileViewHelper.getDrinkingFrequencyColor(userModel.drinkingFrequency).opacity(0.3),
                    glowColor: ProfileViewHelper.getDrinkingFrequencyColor(userModel.drinkingFrequency),
                    isEditMode: isEditMode,
                    destination: DrinkingEditView()
                )

                ProfileItemDivider()

                // 運動
                ProfileNavigationRow(
                    icon: AnyView(
                        Image(systemName: "figure.run")
                            .foregroundColor(.white.opacity(0.9))
                            .font(.system(size: 16))
                    ),
                    title: "運動",
                    value: ProfileViewHelper.getExerciseFrequencyText(userModel.exerciseFrequency),
                    backgroundColor: Color.limeGreen.opacity(0.2),
                    borderColor: Color.limeGreen.opacity(0.3),
                    glowColor: Color.limeGreen,
                    isEditMode: isEditMode,
                    destination: ExerciseEditView()
                )

                ProfileItemDivider()

                // 睡眠時間
                ProfileNavigationRow(
                    icon: AnyView(
                        Image(systemName: "bed.double")
                            .foregroundColor(.white.opacity(0.9))
                            .font(.system(size: 16))
                    ),
                    title: "睡眠時間",
                    value: "\(userModel.sleepHours)時間",
                    backgroundColor: Color.deepViolet.opacity(0.2),
                    borderColor: Color.deepViolet.opacity(0.3),
                    glowColor: Color.deepViolet,
                    isEditMode: isEditMode,
                    destination: SleepHoursEditView()
                )

                ProfileItemDivider()

                // 食生活
                ProfileNavigationRow(
                    icon: AnyView(
                        Image(systemName: "leaf")
                            .foregroundColor(.white.opacity(0.9))
                            .font(.system(size: 16))
                    ),
                    title: "食生活",
                    value: ProfileViewHelper.getDietHabitsText(userModel.dietHabits),
                    backgroundColor: Color.limeGreen.opacity(0.2),
                    borderColor: Color.limeGreen.opacity(0.3),
                    glowColor: Color.limeGreen,
                    isEditMode: isEditMode,
                    destination: DietEditView()
                )

                ProfileItemDivider()

                // 朝食習慣
                ProfileNavigationRow(
                    icon: AnyView(
                        Image(systemName: "sunrise")
                            .foregroundColor(.white.opacity(0.9))
                            .font(.system(size: 16))
                    ),
                    title: "朝食",
                    value: ProfileViewHelper.getBreakfastFrequencyText(userModel.breakfastFrequency),
                    backgroundColor: Color.amber.opacity(0.2),
                    borderColor: Color.amber.opacity(0.3),
                    glowColor: Color.amber,
                    isEditMode: isEditMode,
                    destination: BreakfastEditView()
                )

                ProfileItemDivider()

                // 座位時間
                ProfileNavigationRow(
                    icon: AnyView(
                        Image(systemName: "chair")
                            .foregroundColor(.white.opacity(0.9))
                            .font(.system(size: 16))
                    ),
                    title: "座位時間",
                    value: ProfileViewHelper.getSittingHoursText(userModel.sittingHours),
                    backgroundColor: Color.gray.opacity(0.2),
                    borderColor: Color.gray.opacity(0.3),
                    glowColor: Color.gray,
                    isEditMode: isEditMode,
                    destination: SittingHoursEditView()
                )
            }
            .background(
                RoundedRectangle(cornerRadius: 14)
                    .fill(Color(white: 0.11, opacity: 0.4))
                    .overlay(
                        RoundedRectangle(cornerRadius: 14)
                            .stroke(Color.mysticalPurple.opacity(0.1), lineWidth: 1)
                    )
            )
            .listRowBackground(Color.clear)
            .listRowInsets(EdgeInsets(top: 0, leading: 20, bottom: 16, trailing: 20))
        }
    }
}

// MARK: - 地域情報セクション
struct LocationSection: View {
    @EnvironmentObject var userModel: UserModel
    let isEditMode: Bool

    var body: some View {
        Section(header:
                    Text("地域・環境")
            .foregroundColor(Color.mysticalPurple.opacity(0.8))
            .font(.system(size: 13, weight: .regular))
            .textCase(.uppercase)
            .shadow(color: Color.mysticalPurple.opacity(0.4), radius: 4)
        ) {
            VStack(spacing: 0) {
                // 居住地
                ProfileNavigationRow(
                    icon: AnyView(
                        Image(systemName: "map")
                            .foregroundColor(.white.opacity(0.9))
                            .font(.system(size: 16))
                    ),
                    title: "居住地",
                    value: ProfileViewHelper.getPrefectureName(userModel.currentPrefecture),
                    backgroundColor: Color.mysticBlue.opacity(0.2),
                    borderColor: Color.mysticBlue.opacity(0.3),
                    glowColor: Color.mysticBlue,
                    isEditMode: isEditMode,
                    destination: PrefectureEditView()
                )

                ProfileItemDivider()

                // 通勤時間
                ProfileNavigationRow(
                    icon: AnyView(
                        Image(systemName: "tram")
                            .foregroundColor(.white.opacity(0.9))
                            .font(.system(size: 16))
                    ),
                    title: "通勤時間",
                    value: ProfileViewHelper.getCommuteTimeText(userModel.commuteTime),
                    backgroundColor: Color.orange.opacity(0.2),
                    borderColor: Color.orange.opacity(0.3),
                    glowColor: Color.orange,
                    isEditMode: isEditMode,
                    destination: CommuteTimeEditView()
                )
            }
            .background(
                RoundedRectangle(cornerRadius: 14)
                    .fill(Color(white: 0.11, opacity: 0.4))
                    .overlay(
                        RoundedRectangle(cornerRadius: 14)
                            .stroke(Color.mysticalPurple.opacity(0.1), lineWidth: 1)
                    )
            )
            .listRowBackground(Color.clear)
            .listRowInsets(EdgeInsets(top: 0, leading: 20, bottom: 16, trailing: 20))
        }
    }
}

// MARK: - 健康状態セクション
struct HealthSection: View {
    @EnvironmentObject var userModel: UserModel
    let isEditMode: Bool

    var body: some View {
        Section(header:
                    Text("健康状態")
            .foregroundColor(Color.mysticalPurple.opacity(0.8))
            .font(.system(size: 13, weight: .regular))
            .textCase(.uppercase)
            .shadow(color: Color.mysticalPurple.opacity(0.4), radius: 4)
        ) {
            VStack(spacing: 0) {
                // ストレスレベル
                ProfileNavigationRow(
                    icon: AnyView(
                        Image(systemName: "brain.head.profile")
                            .foregroundColor(.white.opacity(0.9))
                            .font(.system(size: 16))
                    ),
                    title: "ストレス",
                    value: ProfileViewHelper.getStressLevelText(userModel.stressLevel),
                    backgroundColor: Color.deepPink.opacity(0.2),
                    borderColor: Color.deepPink.opacity(0.3),
                    glowColor: Color.deepPink,
                    isEditMode: isEditMode,
                    destination: StressLevelEditView()
                )

                ProfileItemDivider()

                // 健康診断
                ProfileNavigationRow(
                    icon: AnyView(
                        Image(systemName: "stethoscope")
                            .foregroundColor(.white.opacity(0.9))
                            .font(.system(size: 16))
                    ),
                    title: "健康診断",
                    value: ProfileViewHelper.getHealthCheckupText(userModel.healthCheckupFrequency),
                    backgroundColor: Color.mysticBlue.opacity(0.2),
                    borderColor: Color.mysticBlue.opacity(0.3),
                    glowColor: Color.mysticBlue,
                    isEditMode: isEditMode,
                    destination: HealthCheckupEditView()
                )

                ProfileItemDivider()

                // 歯科検診
                ProfileNavigationRow(
                    icon: AnyView(
                        Image(systemName: "mouth")
                            .foregroundColor(.white.opacity(0.9))
                            .font(.system(size: 16))
                    ),
                    title: "歯科検診",
                    value: ProfileViewHelper.getDentalCheckupText(userModel.dentalCheckupFrequency),
                    backgroundColor: Color.skyBlue.opacity(0.2),
                    borderColor: Color.skyBlue.opacity(0.3),
                    glowColor: Color.skyBlue,
                    isEditMode: isEditMode,
                    destination: DentalCheckupEditView()
                )
            }
            .background(
                RoundedRectangle(cornerRadius: 14)
                    .fill(Color(white: 0.11, opacity: 0.4))
                    .overlay(
                        RoundedRectangle(cornerRadius: 14)
                            .stroke(Color.mysticalPurple.opacity(0.1), lineWidth: 1)
                    )
            )
            .listRowBackground(Color.clear)
            .listRowInsets(EdgeInsets(top: 0, leading: 20, bottom: 16, trailing: 20))
        }
    }
}

// MARK: - 個人情報セクション
struct PersonalInfoSection: View {
    @EnvironmentObject var userModel: UserModel
    let isEditMode: Bool

    var body: some View {
        Section(header:
                    Text("個人情報")
            .foregroundColor(Color.mysticalPurple.opacity(0.8))
            .font(.system(size: 13, weight: .regular))
            .textCase(.uppercase)
            .shadow(color: Color.mysticalPurple.opacity(0.4), radius: 4)
        ) {
            VStack(spacing: 0) {
                // 婚姻状況
                ProfileNavigationRow(
                    icon: AnyView(
                        Image(systemName: "heart.circle")
                            .foregroundColor(.white.opacity(0.9))
                            .font(.system(size: 16))
                    ),
                    title: "婚姻状況",
                    value: ProfileViewHelper.getMaritalStatusText(userModel.maritalStatus),
                    subtitle: userModel.maritalStatus != "single" && userModel.marriageDuration > 0 ? "\(userModel.marriageDuration)年" : nil,
                    backgroundColor: Color.deepPink.opacity(0.2),
                    borderColor: Color.deepPink.opacity(0.3),
                    glowColor: Color.deepPink,
                    isEditMode: isEditMode,
                    destination: MaritalStatusEditView()
                )
            }
            .background(
                RoundedRectangle(cornerRadius: 14)
                    .fill(Color(white: 0.11, opacity: 0.4))
                    .overlay(
                        RoundedRectangle(cornerRadius: 14)
                            .stroke(Color.mysticalPurple.opacity(0.1), lineWidth: 1)
                    )
            )
            .listRowBackground(Color.clear)
            .listRowInsets(EdgeInsets(top: 0, leading: 20, bottom: 16, trailing: 20))
        }
    }
}

// MARK: - プロフィール情報行（表示用）
struct ProfileInfoRow: View {
    let icon: AnyView
    let title: String
    let value: String
    var valueColor: Color = .white.opacity(0.85)
    let backgroundColor: Color
    let borderColor: Color
    let glowColor: Color
    let showChevron: Bool

    @State private var shimmerOffset: CGFloat = -1

    var body: some View {
        HStack {
            ZStack {
                RoundedRectangle(cornerRadius: 6)
                    .fill(backgroundColor)
                    .frame(width: 28, height: 28)
                    .overlay(
                        RoundedRectangle(cornerRadius: 6)
                            .stroke(borderColor, lineWidth: 1)
                    )
                    .shadow(color: glowColor.opacity(0.5), radius: 8)

                icon

                // 光沢効果
                ProfileIconShimmer(shimmerOffset: $shimmerOffset)
            }

            Text(title)
                .foregroundColor(.white.opacity(0.85))
                .font(.system(size: 17, weight: .regular))
                .shadow(color: .black.opacity(0.5), radius: 1.5, x: 0, y: 1)

            Spacer()

            Text(value)
                .foregroundColor(valueColor)
                .font(.system(size: 15))

            if showChevron {
                Image(systemName: "chevron.right")
                    .foregroundColor(.secondary)
                    .font(.system(size: 16))
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
    }
}

// periphery:ignore - View dependency/UI component
// MARK: - プロフィール編集行
struct ProfileEditRow<Content: View>: View {
    let icon: AnyView
    let title: String
    let backgroundColor: Color
    let borderColor: Color
    let glowColor: Color
    let content: () -> Content

    @State private var shimmerOffset: CGFloat = -1

    var body: some View {
        HStack {
            ZStack {
                RoundedRectangle(cornerRadius: 6)
                    .fill(backgroundColor)
                    .frame(width: 28, height: 28)
                    .overlay(
                        RoundedRectangle(cornerRadius: 6)
                            .stroke(borderColor, lineWidth: 1)
                    )
                    .shadow(color: glowColor.opacity(0.5), radius: 8)

                icon

                // 光沢効果
                ProfileIconShimmer(shimmerOffset: $shimmerOffset)
            }

            Text(title)
                .foregroundColor(.white.opacity(0.85))
                .font(.system(size: 17, weight: .regular))
                .shadow(color: .black.opacity(0.5), radius: 1.5, x: 0, y: 1)

            Spacer()

            content()
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
    }
}

// MARK: - プロフィールナビゲーション行
struct ProfileNavigationRow<Destination: View>: View {
    let icon: AnyView
    let title: String
    let value: String
    var subtitle: String?
    var statusColor: Color?
    let backgroundColor: Color
    let borderColor: Color
    let glowColor: Color
    let isEditMode: Bool
    let destination: Destination

    @State private var shimmerOffset: CGFloat = -1
    @State private var isPressed = false
    @State private var showingEditView = false

    var body: some View {
        rowContent
            .background(
                isPressed ? Color.white.opacity(0.05) : Color.clear
            )
            .scaleEffect(isPressed ? 0.98 : 1.0)
            .contentShape(Rectangle())
            .onTapGesture {
                if isEditMode {
                    // タップ音
                    SoundManager.shared.playTapSound(.soft)

                    withAnimation(.easeInOut(duration: 0.1)) {
                        isPressed = true
                    }

                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                        isPressed = false
                        showingEditView = true
                    }
                }
            }
            .sheet(isPresented: $showingEditView) {
                destination
            }
    }

    private var rowContent: some View {
        HStack {
            ZStack {
                RoundedRectangle(cornerRadius: 6)
                    .fill(backgroundColor)
                    .frame(width: 28, height: 28)
                    .overlay(
                        RoundedRectangle(cornerRadius: 6)
                            .stroke(borderColor, lineWidth: 1)
                    )
                    .shadow(color: glowColor.opacity(0.5), radius: 8)

                icon

                // 光沢効果
                ProfileIconShimmer(shimmerOffset: $shimmerOffset)
            }

            Text(title)
                .foregroundColor(.white.opacity(0.85))
                .font(.system(size: 17, weight: .regular))
                .shadow(color: .black.opacity(0.5), radius: 1.5, x: 0, y: 1)

            Spacer()

            if let statusColor = statusColor {
                Circle()
                    .fill(statusColor)
                    .frame(width: 8, height: 8)
                    .shadow(color: statusColor.opacity(0.5), radius: 4)
            }

            VStack(alignment: .trailing, spacing: 2) {
                Text(value)
                    .foregroundColor(.white.opacity(0.85))
                    .font(.system(size: 15))

                if let subtitle = subtitle {
                    Text(subtitle)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }

            if isEditMode {
                Image(systemName: "chevron.right")
                    .foregroundColor(.secondary)
                    .font(.system(size: 16))
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
    }
}

// MARK: - セクション間の区切り線
struct ProfileItemDivider: View {
    var body: some View {
        Divider()
            .background(Color.mysticalPurple.opacity(0.1))
            .padding(.leading, 56)
    }
}
