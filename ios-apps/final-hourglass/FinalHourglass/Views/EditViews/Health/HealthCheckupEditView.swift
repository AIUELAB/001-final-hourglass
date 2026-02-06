import SwiftUI

struct HealthCheckupEditView: View {
    @EnvironmentObject var userModel: UserModel
    @Environment(\.dismiss) var dismiss
    @State private var selectedFrequency: String = ""

    var body: some View {
        NavigationView {
            List {
            Section(header: Text("健康診断の頻度を選択")) {
                ForEach([
                    ("yearly", "年1回以上", "定期的に受診"),
                    ("every_2_3_years", "2〜3年に1回", "時々受診"),
                    ("rarely", "ほとんど受けない", "まれに受診")
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

            Section(footer: Text("定期的な健康診断は病気の早期発見につながり、健康寿命を延ばす重要な要素です。")) {
                EmptyView()
            }
        }
        .navigationTitle("健康診断")
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
                        userModel.healthCheckupFrequency = selectedFrequency
                    userModel.saveToUserDefaults()
                    dismiss()
                }
            }
        }
        .onAppear {
            selectedFrequency = userModel.healthCheckupFrequency
        }
        }
    }
}
