import SwiftUI

struct MaritalStatusEditView: View {
    @EnvironmentObject var userModel: UserModel
    @Environment(\.dismiss) var dismiss

    let statuses = [
        ("single", "未婚"),
        ("married", "既婚"),
        ("divorced", "離婚"),
        ("widowed", "死別")
    ]

    var body: some View {
        NavigationView {
        ZStack {
            MysticalSpaceBackground()
                .ignoresSafeArea()

            VStack(spacing: 20) {
                // タイトル
                Text("婚姻状況")
                    .font(.title2)
                    .fontWeight(.bold)
                    .foregroundColor(.white)
                    .padding(.top, 40)

                // 選択肢
                VStack(spacing: 12) {
                    ForEach(statuses, id: \.0) { status in
                        SelectionRow(
                            title: status.1,
                            isSelected: userModel.maritalStatus == status.0,
                            color: .deepPink
                        ) {
                            userModel.maritalStatus = status.0
                        }
                    }
                }
                .padding(.horizontal)
                .padding(.top, 20)

                // 既婚の場合、結婚年数を表示
                if userModel.maritalStatus == "married" {
                    VStack(spacing: 10) {
                        Text("結婚年数")
                            .font(.headline)
                            .foregroundColor(.white.opacity(0.8))
                            .padding(.top, 30)

                        HStack {
                            Button(action: {
                                if userModel.marriageDuration > 0 {
                                    userModel.marriageDuration -= 1
                                }
                            }) {
                                Image(systemName: "minus.circle.fill")
                                    .font(.title2)
                                    .foregroundColor(.deepPink)
                            }

                            Text("\(userModel.marriageDuration)年")
                                .font(.title3)
                                .foregroundColor(.white)
                                .frame(width: 100)

                            Button(action: {
                                userModel.marriageDuration += 1
                            }) {
                                Image(systemName: "plus.circle.fill")
                                    .font(.title2)
                                    .foregroundColor(.deepPink)
                            }
                        }
                    }
                }

                Spacer()
            }
        }
        .navigationTitle("婚姻状況")
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
