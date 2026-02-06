import SwiftUI

struct WeightEditView: View {
    @EnvironmentObject var userModel: UserModel
    @Environment(\.dismiss) var dismiss
    @State private var tempWeight: Double = 0

    var body: some View {
        NavigationView {
            ZStack {
            // 背景
            Color.black.ignoresSafeArea()

            VStack(spacing: 40) {
                // 現在の体重表示
                VStack(spacing: 16) {
                    Text("現在の体重")
                        .font(.headline)
                        .foregroundColor(.white.opacity(0.6))

                    HStack(alignment: .bottom, spacing: 4) {
                        Text(String(format: "%.1f", tempWeight))
                            .font(.system(size: 48, weight: .light))
                            .foregroundColor(.white)

                        Text("kg")
                            .font(.title2)
                            .foregroundColor(.white.opacity(0.6))
                            .padding(.bottom, 8)
                    }
                }
                .padding(.top, 40)

                // スライダー
                VStack(spacing: 20) {
                    Slider(value: $tempWeight, in: 30...150, step: 0.1)
                        .accentColor(Color.skyBlue)
                        .padding(.horizontal)
                        .onChange(of: tempWeight) { _ in
                            // スライダー操作時の選択音
                            SoundManager.shared.playSelectionSound()
                        }

                    HStack {
                        Text("30kg")
                            .font(.caption)
                            .foregroundColor(.white.opacity(0.5))
                        Spacer()
                        Text("150kg")
                            .font(.caption)
                            .foregroundColor(.white.opacity(0.5))
                    }
                    .padding(.horizontal)
                }
                .padding(.horizontal)

                // BMI表示
                VStack(spacing: 8) {
                    Text("BMI")
                        .font(.caption)
                        .foregroundColor(.white.opacity(0.5))

                    let bmi = tempWeight / pow(userModel.height / 100, 2)
                    Text(String(format: "%.1f", bmi))
                        .font(.title3)
                        .foregroundColor(getBMIColor(bmi))

                    Text(getBMIStatus(bmi))
                        .font(.caption)
                        .foregroundColor(getBMIColor(bmi).opacity(0.8))
                }
                .padding()
                .background(
                    RoundedRectangle(cornerRadius: 12)
                        .fill(Color.white.opacity(0.05))
                )

                Spacer()
            }
        }
        .navigationTitle("体重")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .navigationBarLeading) {
                Button("戻る") {
                        // タップ音
                        SoundManager.shared.playTapSound(.cancel)
                        dismiss()
                }
                .foregroundColor(Color.mysticalPurple)
            }

            ToolbarItem(placement: .navigationBarTrailing) {
                Button("保存") {
                        // タップ音
                        SoundManager.shared.playTapSound(.confirm)
                        userModel.weight = tempWeight
                    userModel.saveToUserDefaults()
                    dismiss()
                }
                .foregroundColor(Color.mysticalPurple)
                .font(.system(size: 17, weight: .semibold))
            }
        }
        .onAppear {
            tempWeight = userModel.weight
        }
        }
    }

    private func getBMIColor(_ bmi: Double) -> Color {
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

    private func getBMIStatus(_ bmi: Double) -> String {
        switch bmi {
        case ..<18.5:
            return "低体重"
        case 18.5..<25:
            return "標準"
        case 25..<30:
            return "肥満(1度)"
        default:
            return "肥満(2度以上)"
        }
    }
}
