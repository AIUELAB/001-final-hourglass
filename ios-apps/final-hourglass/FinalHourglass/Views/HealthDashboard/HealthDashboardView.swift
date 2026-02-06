// periphery:ignore:all - 将来使用予定
import Charts
import SwiftUI

struct HealthDashboardView: View {
    @EnvironmentObject var userModel: UserModel
    @State private var selectedTab = 0
    @State private var showingHealthTips = false
    @State private var animateChart = false

    // 健康スコア計算
    private var healthScore: HealthScore {
        calculateHealthScore(user: userModel)
    }

    // 予測寿命
    private var lifeExpectancy: Double {
        calculateLifeExpectancy(user: userModel) ?? 84.0
    }

    // 現在の年齢
    private var currentAge: Int {
        let birthday = Calendar.current.date(from: DateComponents(
            year: userModel.birthYear,
            month: userModel.birthMonth,
            day: userModel.birthDay
        )) ?? Date()

        let ageComponents = Calendar.current.dateComponents([.year], from: birthday, to: Date())
        return ageComponents.year ?? 0
    }

    var body: some View {
        ZStack {
            // 背景
            Color.black
                .edgesIgnoringSafeArea(.all)

            ScrollView {
                VStack(spacing: 24) {
                    // ヘッダー
                    headerSection

                    // タブ選択
                    tabSelector

                    // コンテンツ
                    if selectedTab == 0 {
                        overviewContent
                    } else {
                        detailsContent
                    }
                }
                .padding()
            }
        }
        .navigationTitle("健康ダッシュボード")
        .navigationBarTitleDisplayMode(.inline)
        .preferredColorScheme(.dark)
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                Button(action: {
                    SoundManager.shared.playTapSound(.soft)
                    showingHealthTips = true
                }) {
                    Image(systemName: "lightbulb")
                        .foregroundColor(.yellow)
                }
            }
        }
        .sheet(isPresented: $showingHealthTips) {
            HealthTipsView()
        }
    }

    // MARK: - ヘッダーセクション
    private var headerSection: some View {
        VStack(spacing: 20) {
            // スコアサークル
            ZStack {
                // 背景の円
                Circle()
                    .stroke(Color.gray.opacity(0.3), lineWidth: 20)
                    .frame(width: 200, height: 200)

                // スコアの円
                Circle()
                    .trim(from: 0, to: CGFloat(healthScore.score) / 100)
                    .stroke(
                        LinearGradient(
                            gradient: Gradient(colors: [scoreColor, scoreColor.opacity(0.6)]),
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        ),
                        style: StrokeStyle(lineWidth: 20, lineCap: .round)
                    )
                    .frame(width: 200, height: 200)
                    .rotationEffect(.degrees(-90))
                    .animation(.spring(response: 1.0, dampingFraction: 0.8), value: animateChart)

                // スコア表示
                VStack(spacing: 8) {
                    Text("\(healthScore.score)")
                        .font(.system(size: 60, weight: .bold))
                        .foregroundColor(scoreColor)

                    Text("健康スコア")
                        .font(.caption)
                        .foregroundColor(.gray)

                    HStack(spacing: 4) {
                        Image(systemName: scoreIcon)
                        Text(scoreMessage)
                    }
                    .font(.caption2)
                    .foregroundColor(scoreColor)
                }
            }
            .onAppear {
                withAnimation(.easeInOut(duration: 1.5).delay(0.3)) {
                    animateChart = true
                }
            }

            // 予測寿命
            HStack(spacing: 40) {
                VStack(spacing: 4) {
                    Text("\(currentAge)")
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(.white)
                    Text("現在の年齢")
                        .font(.caption)
                        .foregroundColor(.gray)
                }

                Image(systemName: "arrow.right")
                    .foregroundColor(.gray)

                VStack(spacing: 4) {
                    Text(String(format: "%.1f", lifeExpectancy))
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(.blue)
                    Text("予測寿命")
                        .font(.caption)
                        .foregroundColor(.gray)
                }
            }
            .padding()
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(Color.white.opacity(0.05))
            )
        }
    }

    // MARK: - タブセレクター
    private var tabSelector: some View {
        HStack(spacing: 0) {
            TabButton(title: "概要", isSelected: selectedTab == 0) {
                selectedTab = 0
            }

            TabButton(title: "詳細", isSelected: selectedTab == 1) {
                selectedTab = 1
            }
        }
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color.white.opacity(0.05))
        )
    }

    // MARK: - 概要コンテンツ
    private var overviewContent: some View {
        VStack(spacing: 20) {
            // 健康要因サマリー
            ForEach(Array(healthScore.factors.keys.sorted(by: { $0.rawValue < $1.rawValue })), id: \.self) { factor in
                if let impact = healthScore.factors[factor] {
                    HealthFactorRow(
                        factor: factor,
                        impact: impact,
                        currentValue: getCurrentValue(for: factor)
                    )
                }
            }

            // アドバイスセクション
            adviceSection
        }
    }

    // MARK: - 詳細コンテンツ
    private var detailsContent: some View {
        VStack(spacing: 20) {
            // 各要因の詳細
            ForEach(HealthFactor.allCases, id: \.self) { factor in
                HealthFactorDetailCard(
                    factor: factor,
                    userModel: userModel,
                    impact: healthScore.factors[factor] ?? 0
                )
            }
        }
    }

    // MARK: - アドバイスセクション
    private var adviceSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            SectionHeader(title: "改善のヒント", icon: "lightbulb.fill")

            VStack(spacing: 12) {
                if let worstFactor = getWorstFactor() {
                    AdviceCard(
                        icon: worstFactor.icon,
                        title: "\(worstFactor.rawValue)を改善しましょう",
                        description: getAdvice(for: worstFactor),
                        color: worstFactor.color
                    )
                }

                if healthScore.score >= 80 {
                    AdviceCard(
                        icon: "star.fill",
                        title: "素晴らしい健康状態です！",
                        description: "現在の生活習慣を維持しましょう。",
                        color: .green
                    )
                }
            }
        }
    }

    // MARK: - Helper Properties
    private var scoreColor: Color {
        switch healthScore.score {
        case 80...100: return .green
        case 60..<80: return .yellow
        case 40..<60: return .orange
        default: return .red
        }
    }

    private var scoreIcon: String {
        switch healthScore.score {
        case 80...100: return "checkmark.circle.fill"
        case 60..<80: return "exclamationmark.circle.fill"
        default: return "xmark.circle.fill"
        }
    }

    private var scoreMessage: String {
        switch healthScore.score {
        case 80...100: return "優秀"
        case 60..<80: return "良好"
        case 40..<60: return "要改善"
        default: return "要注意"
        }
    }

    // MARK: - Helper Functions
    private func getCurrentValue(for factor: HealthFactor) -> String {
        switch factor {
        case .smoking:
            return smokingStatusText(userModel.smokingStatus)
        case .drinking:
            return drinkingFrequencyText(userModel.drinkingFrequency)
        case .exercise:
            return exerciseFrequencyText(userModel.exerciseFrequency)
        default:
            return "未設定"
        }
    }

    private func smokingStatusText(_ status: String) -> String {
        switch status {
        case "non_smoker": return "非喫煙者"
        case "quit_smoker": return "禁煙者"
        case "smoker": return "喫煙者"
        case "heavy_smoker": return "ヘビースモーカー"
        default: return "未設定"
        }
    }

    private func drinkingFrequencyText(_ frequency: String) -> String {
        switch frequency {
        case "never": return "飲まない"
        case "rarely": return "たまに"
        case "sometimes": return "時々"
        case "often": return "よく飲む"
        case "daily": return "毎日"
        default: return "未設定"
        }
    }

    private func exerciseFrequencyText(_ frequency: String) -> String {
        switch frequency {
        case "never": return "しない"
        case "rarely": return "ほとんどしない"
        case "sometimes": return "時々"
        case "often": return "よくする"
        case "daily": return "毎日"
        default: return "未設定"
        }
    }

    private func getWorstFactor() -> HealthFactor? {
        healthScore.factors
            .filter { $0.value < 0 }
            .min { $0.value < $1.value }?
            .key
    }

    private func getAdvice(for factor: HealthFactor) -> String {
        switch factor {
        case .smoking:
            return "禁煙は健康寿命を大幅に延ばします。医師に相談してみましょう。"
        case .drinking:
            return "適度な飲酒を心がけましょう。週に2日は休肝日を設けることをお勧めします。"
        case .exercise:
            return "週150分以上の中強度の運動を目指しましょう。まずは毎日10分のウォーキングから始めてみませんか？"
        default:
            return "生活習慣の改善を検討しましょう。"
        }
    }
}

// MARK: - Supporting Views
struct TabButton: View {
    let title: String
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: {
            SoundManager.shared.playTapSound(.soft)
            action()
        }) {
            Text(title)
                .font(.subheadline)
                .fontWeight(isSelected ? .semibold : .regular)
                .foregroundColor(isSelected ? .white : .gray)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 12)
                .background(
                    isSelected ? Color.red.opacity(0.3) : Color.clear
                )
        }
        .animation(.easeInOut(duration: 0.2), value: isSelected)
    }
}

struct HealthFactorRow: View {
    let factor: HealthFactor
    let impact: Int
    let currentValue: String

    var body: some View {
        HStack {
            Image(systemName: factor.icon)
                .foregroundColor(factor.color)
                .frame(width: 30)

            VStack(alignment: .leading, spacing: 4) {
                Text(factor.rawValue)
                    .font(.subheadline)
                    .foregroundColor(.white)

                Text(currentValue)
                    .font(.caption)
                    .foregroundColor(.gray)
            }

            Spacer()

            HStack(spacing: 4) {
                Image(systemName: impact > 0 ? "arrow.up" : impact < 0 ? "arrow.down" : "minus")
                    .font(.caption)

                Text("\(abs(impact))点")
                    .font(.caption)
                    .fontWeight(.medium)
            }
            .foregroundColor(impact > 0 ? .green : impact < 0 ? .red : .gray)
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color.white.opacity(0.05))
        )
    }
}

struct HealthFactorDetailCard: View {
    let factor: HealthFactor
    let userModel: UserModel
    let impact: Int

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Image(systemName: factor.icon)
                    .foregroundColor(factor.color)
                    .font(.title2)

                Text(factor.rawValue)
                    .font(.title3)
                    .fontWeight(.semibold)
                    .foregroundColor(.white)

                Spacer()

                Text("\(impact > 0 ? "+" : "")\(impact)点")
                    .font(.headline)
                    .foregroundColor(impact > 0 ? .green : impact < 0 ? .red : .gray)
            }

            // 詳細情報をここに追加
            Text(getDetailDescription(for: factor))
                .font(.caption)
                .foregroundColor(.gray)
                .lineSpacing(4)
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(factor.color.opacity(0.1))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(factor.color.opacity(0.3), lineWidth: 1)
        )
    }

    private func getDetailDescription(for factor: HealthFactor) -> String {
        switch factor {
        case .smoking:
            return "喫煙は心臓病、脳卒中、がんなどのリスクを高めます。禁煙により、これらのリスクは大幅に低下します。"
        case .drinking:
            return "適度な飲酒は問題ありませんが、過度の飲酒は肝臓病やがんのリスクを高めます。"
        case .exercise:
            return "定期的な運動は心血管系の健康を改善し、多くの慢性疾患のリスクを低下させます。"
        case .diet:
            return "バランスの取れた食事は健康の基本です。野菜、果物、全粒穀物を多く摂りましょう。"
        case .sleep:
            return "質の良い睡眠は身体と精神の健康に不可欠です。7-9時間の睡眠を目指しましょう。"
        case .stress:
            return "慢性的なストレスは様々な健康問題を引き起こします。リラクゼーション技法を身につけましょう。"
        }
    }
}

struct AdviceCard: View {
    let icon: String
    let title: String
    let description: String
    let color: Color

    var body: some View {
        HStack(alignment: .top, spacing: 16) {
            Image(systemName: icon)
                .foregroundColor(color)
                .font(.title2)
                .frame(width: 40)

            VStack(alignment: .leading, spacing: 8) {
                Text(title)
                    .font(.subheadline)
                    .fontWeight(.semibold)
                    .foregroundColor(.white)

                Text(description)
                    .font(.caption)
                    .foregroundColor(.gray)
                    .lineSpacing(4)
            }
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(color.opacity(0.1))
        )
    }
}

// MARK: - Health Tips View
struct HealthTipsView: View {
    @Environment(\.dismiss) var dismiss

    var body: some View {
        NavigationView {
            ZStack {
                Color.black.edgesIgnoringSafeArea(.all)

                ScrollView {
                    VStack(alignment: .leading, spacing: 20) {
                        ForEach(healthTips, id: \.title) { tip in
                            TipCard(tip: tip)
                        }
                    }
                    .padding()
                }
            }
            .navigationTitle("健康のヒント")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("閉じる") {
                        SoundManager.shared.playTapSound(.cancel)
                        dismiss()
                    }
                    .foregroundColor(.red)
                }
            }
            .preferredColorScheme(.dark)
        }
    }

    private let healthTips = [
        HealthTip(
            title: "水分補給",
            icon: "drop.fill",
            description: "1日に体重1kgあたり35mlの水を飲むことを目指しましょう。"
        ),
        HealthTip(
            title: "睡眠の質",
            icon: "moon.stars.fill",
            description: "寝る前のスマートフォン使用を避け、規則正しい睡眠習慣を心がけましょう。"
        ),
        HealthTip(
            title: "ストレス管理",
            icon: "leaf.fill",
            description: "深呼吸、瞑想、ヨガなどでストレスを軽減しましょう。"
        )
    ]
}

struct HealthTip {
    let title: String
    let icon: String
    let description: String
}

struct TipCard: View {
    let tip: HealthTip

    var body: some View {
        HStack(alignment: .top, spacing: 16) {
            Image(systemName: tip.icon)
                .foregroundColor(.green)
                .font(.title2)

            VStack(alignment: .leading, spacing: 8) {
                Text(tip.title)
                    .font(.headline)
                    .foregroundColor(.white)

                Text(tip.description)
                    .font(.subheadline)
                    .foregroundColor(.gray)
            }
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color.white.opacity(0.05))
        )
    }
}
