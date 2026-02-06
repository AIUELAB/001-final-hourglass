import SwiftUI

struct DietEditView: View {
    @EnvironmentObject var userModel: UserModel
    @Environment(\.dismiss) var dismiss

    let dietOptions = [
        ("vegetables_daily", "野菜を毎日食べる", "leaf"),
        ("fruits_daily", "果物を毎日食べる", "apple.logo"),
        ("fish_weekly", "魚を週3回以上食べる", "fish"),
        ("limit_processed", "加工食品を控える", "minus.circle"),
        ("limit_fastfood", "ファストフードを控える", "fork.knife.circle"),
        ("balanced_meals", "バランスの良い食事", "checkmark.seal")
    ]

    var body: some View {
        NavigationView {
        ZStack {
            MysticalSpaceBackground()
                .ignoresSafeArea()

            ScrollView {
                VStack(spacing: 20) {
                    // タイトル
                    Text("食生活の習慣")
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(.white)
                        .padding(.top, 20)

                    Text("該当する項目を選択してください")
                        .font(.subheadline)
                        .foregroundColor(.secondary)

                    // 選択肢
                    VStack(spacing: 12) {
                        ForEach(dietOptions, id: \.0) { option in
                            DietOptionRow(
                                id: option.0,
                                title: option.1,
                                icon: option.2,
                                isSelected: userModel.dietHabits.contains(option.0)
                            ) { id in
                                if userModel.dietHabits.contains(id) {
                                    userModel.dietHabits.remove(id)
                                } else {
                                    userModel.dietHabits.insert(id)
                                }
                            }
                        }
                    }
                    .padding(.horizontal)

                    Spacer(minLength: 100)
                }
            }
        }
        .navigationTitle("食生活")
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

struct DietOptionRow: View {
    let id: String
    let title: String
    let icon: String
    let isSelected: Bool
    let onTap: (String) -> Void

    var body: some View {
        Button(action: { onTap(id) }) {
            HStack {
                Image(systemName: icon)
                    .font(.system(size: 20))
                    .foregroundColor(isSelected ? .white : .gray)
                    .frame(width: 30)

                Text(title)
                    .foregroundColor(isSelected ? .white : .gray)

                Spacer()

                Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                    .foregroundColor(isSelected ? .limeGreen : .gray)
            }
            .padding()
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(isSelected ? Color.limeGreen.opacity(0.2) : Color.white.opacity(0.05))
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(isSelected ? Color.limeGreen.opacity(0.5) : Color.white.opacity(0.1), lineWidth: 1)
                    )
            )
        }
    }
}
