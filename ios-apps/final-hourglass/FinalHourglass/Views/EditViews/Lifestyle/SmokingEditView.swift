import SwiftUI

struct SmokingEditView: View {
    @EnvironmentObject var userModel: UserModel
    @Environment(\.dismiss) var dismiss
    @State private var selectedStatus: String = ""
    @State private var selectedYears: Int = 0

    var body: some View {
        NavigationView {
            List {
            Section(header: Text("喫煙状況を選択")) {
                ForEach([
                    ("non_smoker", "吸わない", "お酒を全く飲まない"),
                    ("former_smoker", "以前吸っていた", "禁煙済み"),
                    ("current_smoker", "現在吸っている", "現在も喫煙中")
                ], id: \.0) { status in
                    Button(action: {
                        selectedStatus = status.0
                    }) {
                        HStack {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(status.1)
                                    .foregroundColor(.primary)
                                Text(status.2)
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                            Spacer()
                            if selectedStatus == status.0 {
                                Image(systemName: "checkmark")
                                    .foregroundColor(.blue)
                            }
                        }
                        .padding(.vertical, 4)
                    }
                }
            }

            // 喫煙年数（禁煙済みの場合）
            if selectedStatus == "former_smoker" {
                Section(header: Text("喫煙していた期間")) {
                    Stepper("\(selectedYears)年", value: $selectedYears, in: 0...50)
                }
            }

            Section(footer: Text("喫煙は寿命に大きな影響を与える要因の一つです。")) {
                EmptyView()
            }
        }
        .navigationTitle("喫煙習慣")
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
                        userModel.smokingStatus = selectedStatus
                    userModel.smokingYears = selectedYears
                    userModel.saveToUserDefaults()
                    dismiss()
                }
            }
        }
        .onAppear {
            selectedStatus = userModel.smokingStatus
            selectedYears = userModel.smokingYears
        }
        }
    }
}
