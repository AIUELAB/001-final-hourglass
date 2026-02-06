import SwiftUI

struct BreakfastEditView: View {
    @EnvironmentObject var userModel: UserModel
    @Environment(\.dismiss) var dismiss

    let frequencies = [
        ("daily", "毎日"),
        ("often", "ほぼ毎日"),
        ("sometimes", "時々"),
        ("rarely", "たまに"),
        ("never", "食べない")
    ]

    var body: some View {
        NavigationView {
            ZStack {
                MysticalSpaceBackground()
                    .ignoresSafeArea()

                VStack(spacing: 20) {
                    // タイトル
                    Text("朝食の頻度")
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(.white)
                        .padding(.top, 40)

                    Text("どのくらいの頻度で朝食を食べますか？")
                        .font(.subheadline)
                        .foregroundColor(.secondary)

                    // 選択肢
                    VStack(spacing: 12) {
                        ForEach(frequencies, id: \.0) { frequency in
                            SelectionRow(
                                title: frequency.1,
                                isSelected: userModel.breakfastFrequency == frequency.0,
                                color: .amber
                            ) {
                                userModel.breakfastFrequency = frequency.0
                            }
                        }
                    }
                    .padding(.horizontal)
                    .padding(.top, 20)

                    Spacer()
                }
            }
            .navigationTitle("朝食習慣")
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
