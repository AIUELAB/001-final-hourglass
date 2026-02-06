import StoreKit
import SwiftUI

struct DrinkingEditView: View {
    @EnvironmentObject var userModel: UserModel
    @Environment(\.dismiss) var dismiss
    @State private var selectedFrequency: String = ""

    var body: some View {
        NavigationView {
            List {
            Section(header: Text("飲酒頻度を選択")) {
                ForEach([
                    ("never", "飲まない", "お酒を全く飲まない"),
                    ("rarely", "月1-2回", "付き合い程度"),
                    ("sometimes", "週1-2回", "適度に楽しむ"),
                    ("often", "週3-4回", "よく飲む"),
                    ("daily", "毎日", "毎日飲む")
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

            Section(footer: Text("飲酒頻度は寿命予測の重要な要素の一つです。適度な飲酒を心がけましょう。")) {
                EmptyView()
            }
        }
        .navigationTitle("飲酒頻度")
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
                        userModel.drinkingFrequency = selectedFrequency
                    userModel.saveToUserDefaults()
                    dismiss()
                }
            }
        }
        .onAppear {
            selectedFrequency = userModel.drinkingFrequency
        }
        }
    }

    // periphery:ignore - App Store review prompt
    private func requestReview() {
        if let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene {
            if #available(iOS 18.0, *) {
                AppStore.requestReview(in: windowScene)
            } else {
                SKStoreReviewController.requestReview(in: windowScene)
            }
        }
    }
}
