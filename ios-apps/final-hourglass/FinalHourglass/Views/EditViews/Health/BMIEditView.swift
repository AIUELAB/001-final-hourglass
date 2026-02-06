import SwiftUI

struct BMIEditView: View {
    @EnvironmentObject var userModel: UserModel
    @Environment(\.dismiss) var dismiss

    @State private var heightText: String = ""
    @State private var weightText: String = ""
    @State private var showingAlert = false
    @State private var alertMessage = ""

    var calculatedBMI: Double {
        guard let height = Double(heightText), height > 0,
              let weight = Double(weightText), weight > 0 else {
            return 0.0
        }
        let heightInMeters = height / 100.0
        return weight / (heightInMeters * heightInMeters)
    }

    var bmiCategory: (text: String, color: Color) {
        if calculatedBMI == 0 {
            return ("未計算", .gray)
        } else if calculatedBMI < 18.5 {
            return ("低体重", .yellow)
        } else if calculatedBMI < 25.0 {
            return ("標準体重", .green)
        } else if calculatedBMI < 30.0 {
            return ("肥満（1度）", .orange)
        } else if calculatedBMI < 35.0 {
            return ("肥満（2度）", .red)
        } else {
            return ("高度肥満", .red)
        }
    }

    var body: some View {
        Form {
            Section(header: Text("身長・体重を入力")) {
                HStack {
                    Text("身長")
                        .frame(width: 60, alignment: .leading)
                    TextField("170", text: $heightText)
                        .keyboardType(.decimalPad)
                        .textFieldStyle(RoundedBorderTextFieldStyle())
                    Text("cm")
                }

                HStack {
                    Text("体重")
                        .frame(width: 60, alignment: .leading)
                    TextField("65", text: $weightText)
                        .keyboardType(.decimalPad)
                        .textFieldStyle(RoundedBorderTextFieldStyle())
                    Text("kg")
                }

                if calculatedBMI > 0 {
                    HStack {
                        Text("BMI")
                            .frame(width: 60, alignment: .leading)
                            .font(.system(size: 17, weight: .medium))
                        Text(String(format: "%.1f", calculatedBMI))
                            .font(.system(size: 28, weight: .bold))
                        Text(bmiCategory.text)
                            .foregroundColor(bmiCategory.color)
                            .font(.system(size: 17, weight: .medium))
                    }
                    .padding(.vertical, 8)
                }
            }

            Section(header: Text("BMI分類")) {
                VStack(alignment: .leading, spacing: 8) {
                    BMICategoryRow(range: "18.5未満", category: "低体重", color: .yellow)
                    BMICategoryRow(range: "18.5〜25.0", category: "標準体重", color: .green)
                    BMICategoryRow(range: "25.0〜30.0", category: "肥満（1度）", color: .orange)
                    BMICategoryRow(range: "30.0〜35.0", category: "肥満（2度）", color: .red)
                    BMICategoryRow(range: "35.0以上", category: "高度肥満", color: .red)
                }
            }

            Section(header: Text("BMIと死亡リスク")) {
                VStack(alignment: .leading, spacing: 10) {
                    HStack(alignment: .top) {
                        Image(systemName: "chart.line.uptrend.xyaxis")
                            .foregroundColor(.red)
                            .frame(width: 25)
                        VStack(alignment: .leading, spacing: 2) {
                            Text("低体重（BMI 18.5未満）")
                                .font(.system(size: 13, weight: .medium))
                            Text("死亡リスクが1.3倍増加")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }

                    HStack(alignment: .top) {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundColor(.green)
                            .frame(width: 25)
                        VStack(alignment: .leading, spacing: 2) {
                            Text("標準体重（BMI 22前後）")
                                .font(.system(size: 13, weight: .medium))
                            Text("最も死亡リスクが低い")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }

                    HStack(alignment: .top) {
                        Image(systemName: "exclamationmark.triangle")
                            .foregroundColor(.orange)
                            .frame(width: 25)
                        VStack(alignment: .leading, spacing: 2) {
                            Text("肥満（BMI 30以上）")
                                .font(.system(size: 13, weight: .medium))
                            Text("死亡リスクが1.2〜1.5倍増加")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                }
                .padding(.vertical, 4)
            }

            Section(footer: Text("BMIは身長と体重から計算される肥満度の指標です。健康的な体重維持は長寿の重要な要因の一つです。")) {
                EmptyView()
            }
        }
        .navigationTitle("BMI")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .navigationBarLeading) {
                Button("戻る") {
                        // タップ音
                        SoundManager.shared.playTapSound(.cancel)
                        dismiss()
                }
            }
            ToolbarItem(placement: .navigationBarTrailing) {
                Button("保存") {
                        // タップ音
                        SoundManager.shared.playTapSound(.confirm)
                        saveBMI()
                }
            }
        }
        .onAppear {
            heightText = String(format: "%.0f", userModel.height)
            weightText = String(format: "%.0f", userModel.weight)
        }
        .alert(isPresented: $showingAlert) {
            Alert(title: Text("エラー"), message: Text(alertMessage), dismissButton: .default(Text("OK")))
        }
    }

    private func saveBMI() {
        guard let height = Double(heightText), height > 0, height < 300,
              let weight = Double(weightText), weight > 0, weight < 500 else {
            alertMessage = "正しい身長と体重を入力してください"
            showingAlert = true
            return
        }

        userModel.height = height
        userModel.weight = weight
        userModel.bmi = calculatedBMI
        userModel.saveToUserDefaults()
        dismiss()
    }
}

struct BMICategoryRow: View {
    let range: String
    let category: String
    let color: Color

    var body: some View {
        HStack {
            Circle()
                .fill(color)
                .frame(width: 12, height: 12)
            Text(range)
                .font(.footnote)
                .frame(width: 100, alignment: .leading)
            Text(category)
                .font(.system(size: 13, weight: .medium))
            Spacer()
        }
    }
}

#Preview {
    NavigationView {
        BMIEditView()
            .environmentObject(UserModel())
    }
}
