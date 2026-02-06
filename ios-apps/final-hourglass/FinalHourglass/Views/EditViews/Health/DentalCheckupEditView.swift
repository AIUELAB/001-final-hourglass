import SwiftUI

struct DentalCheckupEditView: View {
    @EnvironmentObject var userModel: UserModel
    @Environment(\.dismiss) var dismiss

    let frequencies = [
        ("biannually", "年2回以上"),
        ("yearly", "年1回"),
        ("every_2_3_years", "2-3年に1回"),
        ("rarely", "ほとんど受けない")
    ]

    var body: some View {
        NavigationView {
            ZStack {
                MysticalSpaceBackground()
                    .ignoresSafeArea()

                VStack(spacing: 20) {
                    // タイトル
                    Text("歯科検診の頻度")
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(.white)
                        .padding(.top, 40)

                    Text("どのくらいの頻度で歯科検診を受けていますか？")
                        .font(.subheadline)
                        .foregroundColor(.secondary)

                    // 選択肢
                    VStack(spacing: 12) {
                        ForEach(frequencies, id: \.0) { frequency in
                            SelectionRow(
                                title: frequency.1,
                                isSelected: userModel.dentalCheckupFrequency == frequency.0,
                                color: .skyBlue
                            ) {
                                userModel.dentalCheckupFrequency = frequency.0
                            }
                        }
                    }
                    .padding(.horizontal)
                    .padding(.top, 20)

                    Spacer()
                }
            }
            .navigationTitle("歯科検診")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("戻る") {
                        // タップ音
                        SoundManager.shared.playTapSound(.cancel)
                        dismiss()
                    }
                    .foregroundColor(.mysticalPurple)
                }

                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("保存") {
                        // タップ音
                        SoundManager.shared.playTapSound(.confirm)
                        userModel.saveToUserDefaults()
                        dismiss()
                    }
                    .foregroundColor(.mysticalPurple)
                }
            }
        }
    }
}
