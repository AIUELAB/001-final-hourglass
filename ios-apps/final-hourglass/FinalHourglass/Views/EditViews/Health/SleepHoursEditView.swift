import SwiftUI

struct SleepHoursEditView: View {
    @EnvironmentObject var userModel: UserModel
    @Environment(\.dismiss) var dismiss
    @State private var selectedHours: Int = 7

    var body: some View {
        NavigationView {
            List {
            Section(header: Text("1日の平均睡眠時間")) {
                ForEach([
                    (4, "4時間以下", "極度の睡眠不足", Color.red),
                    (5, "5時間", "睡眠不足", Color.orange),
                    (6, "6時間", "やや不足", Color.yellow),
                    (7, "7時間", "理想的", Color.green),
                    (8, "8時間", "十分", Color.green),
                    (9, "9時間以上", "長時間睡眠", Color.blue)
                ], id: \.0) { hours, title, description, color in
                    Button(action: {
                        selectedHours = hours
                    }) {
                        HStack {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(title)
                                    .font(.headline)
                                    .foregroundColor(.primary)
                                Text(description)
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }

                            Spacer()

                            Circle()
                                .fill(color)
                                .frame(width: 24, height: 24)

                            if selectedHours == hours {
                                Image(systemName: "checkmark")
                                    .foregroundColor(.blue)
                                    .padding(.leading, 8)
                            }
                        }
                        .padding(.vertical, 4)
                    }
                }
            }

            Section(header: Text("睡眠時間と健康リスク")) {
                VStack(alignment: .leading, spacing: 10) {
                    HStack(alignment: .top) {
                        Image(systemName: "heart.text.square")
                            .foregroundColor(.red)
                            .frame(width: 25)
                        VStack(alignment: .leading, spacing: 2) {
                            Text("心血管疾患")
                                .font(.footnote)
                                .fontWeight(.medium)
                            Text("6時間未満で1.15倍、5時間未満で1.45倍")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }

                    HStack(alignment: .top) {
                        Image(systemName: "brain")
                            .foregroundColor(.purple)
                            .frame(width: 25)
                        VStack(alignment: .leading, spacing: 2) {
                            Text("認知症リスク")
                                .font(.footnote)
                                .fontWeight(.medium)
                            Text("6時間未満で1.3倍増加")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }

                    HStack(alignment: .top) {
                        Image(systemName: "chart.line.downtrend.xyaxis")
                            .foregroundColor(.orange)
                            .frame(width: 25)
                        VStack(alignment: .leading, spacing: 2) {
                            Text("死亡リスク")
                                .font(.footnote)
                                .fontWeight(.medium)
                            Text("4時間以下または10時間以上で1.3倍")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }

                    HStack(alignment: .top) {
                        Image(systemName: "scalemass")
                            .foregroundColor(.yellow)
                            .frame(width: 25)
                        VStack(alignment: .leading, spacing: 2) {
                            Text("肥満リスク")
                                .font(.footnote)
                                .fontWeight(.medium)
                            Text("5時間未満で1.5倍増加")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                }
                .padding(.vertical, 4)
            }

            Section(header: Text("良質な睡眠のためのヒント")) {
                VStack(alignment: .leading, spacing: 8) {
                    Label("就寝・起床時間を一定にする", systemImage: "clock.fill")
                        .font(.caption)
                    Label("寝る前のスマホ・PCを避ける", systemImage: "iphone.slash")
                        .font(.caption)
                    Label("カフェインは午後3時まで", systemImage: "cup.and.saucer")
                        .font(.caption)
                    Label("寝室を涼しく暗くする", systemImage: "moon.stars")
                        .font(.caption)
                    Label("就寝3時間前の食事を避ける", systemImage: "fork.knife")
                        .font(.caption)
                }
                .foregroundColor(.secondary)
            }

            Section(footer: Text("適切な睡眠時間は個人差がありますが、一般的に7-8時間が推奨されています。質の良い睡眠は健康長寿の重要な要因です。")) {
                EmptyView()
            }
        }
        .navigationTitle("睡眠時間")
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
                        userModel.sleepHours = selectedHours
                    userModel.saveToUserDefaults()
                    dismiss()
                }
            }
        }
        .onAppear {
            selectedHours = userModel.sleepHours
        }
        }
    }
}

#Preview {
    NavigationView {
        SleepHoursEditView()
            .environmentObject(UserModel())
    }
}
