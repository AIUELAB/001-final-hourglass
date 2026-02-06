import SwiftUI

struct GenderEditView: View {
    @EnvironmentObject var userModel: UserModel
    @Environment(\.dismiss) var dismiss

    var body: some View {
        NavigationView {
            ZStack {
                MysticalSpaceBackground()
                    .ignoresSafeArea()

                VStack(spacing: 24) {
                    // ヘッダー
                    VStack(spacing: 8) {
                        Image(systemName: "person.2")
                            .font(.system(size: 60))
                            .foregroundStyle(
                                LinearGradient(
                                    colors: [Color.mysticalPurple, Color.mysticBlue],
                                    startPoint: .top,
                                    endPoint: .bottom
                                )
                            )

                        Text("性別")
                            .font(.title2)
                            .fontWeight(.semibold)
                            .foregroundColor(.white)

                        Text("性別を選択してください")
                            .font(.subheadline)
                            .foregroundColor(.gray)
                    }
                    .padding(.top, 40)

                    // 性別選択
                    VStack(spacing: 16) {
                        GenderOptionCard(
                            title: "男性",
                            icon: "person.fill",
                            isSelected: userModel.gender == "male",
                            action: {
                                // タップ音
                                SoundManager.shared.playTapSound(.soft)
                                userModel.gender = "male"
                            }
                        )

                        GenderOptionCard(
                            title: "女性",
                            icon: "person.fill",
                            isSelected: userModel.gender == "female",
                            action: {
                                // タップ音
                                SoundManager.shared.playTapSound(.soft)
                                userModel.gender = "female"
                            }
                        )
                    }
                    .padding(.horizontal)

                    Spacer()
                }
            }
            .navigationTitle("性別")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("戻る") {
                        // タップ音
                        SoundManager.shared.playTapSound(.cancel)
                        dismiss()
                    }
                    .foregroundColor(.gray)
                }

                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("保存") {
                        // タップ音
                        SoundManager.shared.playTapSound(.confirm)
                        userModel.saveToUserDefaults()
                        dismiss()
                    }
                    .foregroundColor(.mysticBlue)
                    .font(.system(size: 17, weight: .semibold))
                }
            }
        }
    }
}

struct GenderOptionCard: View {
    let title: String
    let icon: String
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack {
                Image(systemName: icon)
                    .font(.system(size: 24))
                    .foregroundColor(isSelected ? .white : .gray)

                Text(title)
                    .font(.system(size: 18))
                    .fontWeight(.medium)
                    .foregroundColor(isSelected ? .white : .gray)

                Spacer()

                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 24))
                        .foregroundColor(.mysticBlue)
                }
            }
            .padding()
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(isSelected ? Color.mysticalPurple.opacity(0.3) : Color.white.opacity(0.05))
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(isSelected ? Color.mysticalPurple : Color.gray.opacity(0.3), lineWidth: 1)
                    )
            )
        }
    }
}
