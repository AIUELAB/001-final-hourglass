import SwiftUI

struct CommuteTimeEditView: View {
    @EnvironmentObject var userModel: UserModel
    @Environment(\.dismiss) var dismiss
    @State private var selectedTime: String = ""

    var body: some View {
        NavigationView {
            List {
            Section(header: Text("通勤時間を選択")) {
                ForEach([
                    ("none", "なし", "在宅勤務・無職"),
                    ("less_30", "30分未満", "近距離通勤"),
                    ("30_to_60", "30〜60分", "標準的な通勤時間"),
                    ("60_to_90", "60〜90分", "やや長い通勤"),
                    ("over_90", "90分以上", "長距離通勤")
                ], id: \.0) { time in
                    Button(action: {
                        selectedTime = time.0
                    }) {
                        HStack {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(time.1)
                                    .foregroundColor(.primary)
                                Text(time.2)
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                            Spacer()
                            if selectedTime == time.0 {
                                Image(systemName: "checkmark")
                                    .foregroundColor(.blue)
                            }
                        }
                        .padding(.vertical, 4)
                    }
                }
            }

            Section(footer: Text("長時間の通勤はストレスの原因となり、健康に影響を与える可能性があります。")) {
                EmptyView()
            }
        }
        .navigationTitle("通勤時間")
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
                        userModel.commuteTime = selectedTime
                    userModel.saveToUserDefaults()
                    dismiss()
                }
            }
        }
        .onAppear {
            selectedTime = userModel.commuteTime
        }
        }
    }
}
