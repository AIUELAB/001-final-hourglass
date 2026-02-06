import SwiftUI

struct SittingHoursEditView: View {
    @EnvironmentObject var userModel: UserModel
    @Environment(\.dismiss) var dismiss

    let sittingHours = [
        ("less_3", "3時間未満"),
        ("3_to_6", "3〜6時間"),
        ("6_to_9", "6〜9時間"),
        ("over_9", "9時間以上")
    ]

    var body: some View {
        NavigationView {
        ZStack {
            MysticalSpaceBackground()
                .ignoresSafeArea()

            VStack(spacing: 20) {
                // タイトル
                Text("座位時間")
                    .font(.title2)
                    .fontWeight(.bold)
                    .foregroundColor(.white)
                    .padding(.top, 40)

                Text("1日の座っている時間はどのくらいですか？")
                    .font(.subheadline)
                    .foregroundColor(.secondary)

                // 選択肢
                VStack(spacing: 12) {
                    ForEach(sittingHours, id: \.0) { hours in
                        SelectionRow(
                            title: hours.1,
                            isSelected: userModel.sittingHours == hours.0,
                            color: .gray
                        ) {
                            userModel.sittingHours = hours.0
                        }
                    }
                }
                .padding(.horizontal)
                .padding(.top, 20)

                Spacer()
            }
        }
        .navigationTitle("座位時間")
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
