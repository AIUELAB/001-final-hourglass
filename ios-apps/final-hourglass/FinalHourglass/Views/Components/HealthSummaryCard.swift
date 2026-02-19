import SwiftUI

/// メイン画面に表示する健康サマリーカード
struct HealthSummaryCard: View {
    @EnvironmentObject var userModel: UserModel
    let onTapDetail: () -> Void

    private var healthScore: HealthScore {
        calculateHealthScore(user: userModel)
    }

    private var scoreColor: Color {
        switch healthScore.score {
        case 80...100: return .green
        case 60..<80: return .yellow
        case 40..<60: return .orange
        default: return .red
        }
    }

    private var topImprovements: [(HealthFactor, Int)] {
        healthScore.factors
            .filter { $0.value < 0 }
            .sorted { $0.value < $1.value }
            .prefix(3)
            .map { ($0.key, $0.value) }
    }

    var body: some View {
        VStack(spacing: 16) {
            // ヘッダー
            HStack {
                Image(systemName: "heart.text.clipboard")
                    .foregroundColor(scoreColor)
                Text("健康スコア")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundColor(.white)
                Spacer()
                Button(action: onTapDetail) {
                    HStack(spacing: 4) {
                        Text("詳しく見る")
                            .font(.system(size: 13))
                        Image(systemName: "chevron.right")
                            .font(.system(size: 11))
                    }
                    .foregroundColor(AppColors.cornflowerBlue)
                }
            }

            // スコア表示
            HStack(spacing: 20) {
                // 円グラフ（小さい版）
                ZStack {
                    Circle()
                        .stroke(Color.gray.opacity(0.3), lineWidth: 8)
                        .frame(width: 60, height: 60)

                    Circle()
                        .trim(from: 0, to: CGFloat(healthScore.score) / 100)
                        .stroke(
                            scoreColor,
                            style: StrokeStyle(lineWidth: 8, lineCap: .round)
                        )
                        .frame(width: 60, height: 60)
                        .rotationEffect(.degrees(-90))

                    Text("\(healthScore.score)")
                        .font(.system(size: 20, weight: .bold))
                        .foregroundColor(scoreColor)
                }

                // 改善ポイント
                if topImprovements.isEmpty {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("素晴らしい健康状態です！")
                            .font(.system(size: 14, weight: .medium))
                            .foregroundColor(.green)
                        Text("現在の生活習慣を維持しましょう。")
                            .font(.system(size: 12))
                            .foregroundColor(.white.opacity(0.6))
                    }
                } else {
                    VStack(alignment: .leading, spacing: 6) {
                        ForEach(topImprovements, id: \.0) { factor, impact in
                            HStack(spacing: 6) {
                                Image(systemName: factor.icon)
                                    .font(.system(size: 12))
                                    .foregroundColor(factor.color)
                                    .frame(width: 16)
                                Text(factor.rawValue)
                                    .font(.system(size: 13))
                                    .foregroundColor(.white.opacity(0.8))
                                Spacer()
                                Text("\(impact)点")
                                    .font(.system(size: 12, weight: .medium))
                                    .foregroundColor(.red.opacity(0.8))
                            }
                        }
                    }
                }
            }
        }
        .padding(20)
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(Color.black.opacity(0.4))
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(
                            LinearGradient(
                                colors: [
                                    scoreColor.opacity(0.3),
                                    AppColors.mediumPurple.opacity(0.2)
                                ],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            ),
                            lineWidth: 1
                        )
                )
        )
    }
}
