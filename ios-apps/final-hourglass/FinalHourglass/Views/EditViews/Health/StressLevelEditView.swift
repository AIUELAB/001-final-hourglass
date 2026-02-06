import SwiftUI

struct StressLevelEditView: View {
    @EnvironmentObject var userModel: UserModel
    @Environment(\.dismiss) var dismiss
    @State private var selectedLevel: String = ""

    var body: some View {
        NavigationView {
            List {
            Section(header: Text("ストレスレベルを選択")) {
                ForEach([
                    ("low", "低い", "リラックスした生活"),
                    ("medium", "普通", "一般的なストレス"),
                    ("high", "高い", "ストレスを感じる"),
                    ("very_high", "とても高い", "強いストレスを感じる")
                ], id: \.0) { level in
                    Button(action: {
                        // タップ音
                        SoundManager.shared.playTapSound(.soft)
                        selectedLevel = level.0
                    }) {
                        HStack {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(level.1)
                                    .foregroundColor(.primary)
                                Text(level.2)
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                            Spacer()
                            if selectedLevel == level.0 {
                                Image(systemName: "checkmark")
                                    .foregroundColor(.blue)
                            }
                        }
                        .padding(.vertical, 4)
                    }
                }
            }

            Section(footer: Text("慢性的なストレスは健康に悪影響を与えます。ストレス管理は健康寿命を延ばす重要な要素です。")) {
                EmptyView()
            }
        }
        .navigationTitle("ストレスレベル")
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
                        userModel.stressLevel = selectedLevel
                    userModel.saveToUserDefaults()
                    dismiss()
                }
            }
        }
        .onAppear {
            selectedLevel = userModel.stressLevel
        }
        }
    }
}
