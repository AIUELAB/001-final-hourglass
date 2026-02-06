import SwiftUI

struct ExerciseEditView: View {
    @EnvironmentObject var userModel: UserModel
    @Environment(\.dismiss) var dismiss
    @State private var selectedFrequency: String = ""

    var body: some View {
        NavigationView {
            List {
            Section(header: Text("運動頻度を選択")) {
                ForEach([
                    ("never", "まったくしない", "運動習慣なし"),
                    ("rarely", "月1〜2回", "たまに運動する"),
                    ("sometimes", "週1〜2回", "定期的に運動"),
                    ("often", "週3〜4回", "頻繁に運動"),
                    ("daily", "ほぼ毎日", "毎日運動する")
                ], id: \.0) { frequency in
                    Button(action: {
                        selectedFrequency = frequency.0
                    }) {
                        HStack {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(frequency.1)
                                    .foregroundColor(.primary)
                                Text(frequency.2)
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                            Spacer()
                            if selectedFrequency == frequency.0 {
                                Image(systemName: "checkmark")
                                    .foregroundColor(.blue)
                            }
                        }
                        .padding(.vertical, 4)
                    }
                }
            }

            Section(footer: Text("定期的な運動は健康寿命を延ばす重要な要素です。")) {
                EmptyView()
            }
        }
        .navigationTitle("運動習慣")
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
                        userModel.exerciseFrequency = selectedFrequency
                    userModel.saveToUserDefaults()
                    dismiss()
                }
            }
        }
        .onAppear {
            selectedFrequency = userModel.exerciseFrequency
        }
        }
    }
}
