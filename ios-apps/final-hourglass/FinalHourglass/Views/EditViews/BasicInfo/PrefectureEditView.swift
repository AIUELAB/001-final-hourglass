import SwiftUI

struct PrefectureEditView: View {
    @EnvironmentObject var userModel: UserModel
    @Environment(\.dismiss) var dismiss
    @State private var showingPicker = false
    @State private var selectedPrefecture: String = ""

    var body: some View {
        NavigationView {
            List {
            Section(header: Text("現在お住まいの都道府県")) {
                HStack {
                    Text("選択中:")
                    Spacer()
                    Text(getPrefectureName(selectedPrefecture))
                        .foregroundColor(.secondary)
                        .fontWeight(.medium)
                }
                .padding(.vertical, 8)

                Button(action: {
                    showingPicker = true
                }) {
                    HStack {
                        Image(systemName: "map")
                            .foregroundColor(.blue)
                        Text("都道府県を変更")
                        Spacer()
                        Image(systemName: "chevron.right")
                            .foregroundColor(.secondary)
                            .font(.caption)
                    }
                }
                .padding(.vertical, 4)
            }

            Section(footer: Text("お住まいの地域によって平均寿命に差があります。")) {
                EmptyView()
            }
        }
        .navigationTitle("居住地")
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
                        userModel.currentPrefecture = selectedPrefecture
                    userModel.saveToUserDefaults()
                    dismiss()
                }
            }
        }
        .onAppear {
            selectedPrefecture = userModel.currentPrefecture
        }
        .sheet(isPresented: $showingPicker) {
            PrefecturePickerView(
                selectedPrefecture: $selectedPrefecture,
                isPresented: $showingPicker
            )
        }
        }
    }

    private func getPrefectureName(_ prefectureValue: String) -> String {
        if let prefecture = Prefecture.fromCode(prefectureValue) {
            return prefecture.name
        }
        if let prefecture = Prefecture.fromRawValue(prefectureValue) {
            return prefecture.name
        }
        return "未設定"
    }
}
