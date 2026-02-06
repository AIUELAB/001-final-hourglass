import SwiftUI

struct BirthdayEditView: View {
    @EnvironmentObject var userModel: UserModel
    @Environment(\.dismiss) private var dismiss

    @State private var selectedDate: Date

    init() {
        let calendar = Calendar.current
        let components = DateComponents(year: 1990, month: 1, day: 1)
        self._selectedDate = State(initialValue: calendar.date(from: components) ?? Date())
    }

    var body: some View {
        NavigationView {
            ZStack {
                MysticalSpaceBackground()
                    .ignoresSafeArea()

                VStack(spacing: 30) {
                    // ヘッダー
                    VStack(spacing: 10) {
                        Image(systemName: "calendar")
                            .font(.system(size: 50))
                            .foregroundStyle(
                                LinearGradient(
                                    colors: [Color.mysticalPurple, Color.mysticBlue],
                                    startPoint: .top,
                                    endPoint: .bottom
                                )
                            )

                        Text("生年月日")
                            .font(.title2)
                            .fontWeight(.bold)
                            .foregroundColor(.white)

                        Text("生年月日を選択してください")
                            .font(.subheadline)
                            .foregroundColor(.gray)
                    }
                    .padding(.top, 40)

                    // DatePicker
                    DatePicker("",
                              selection: $selectedDate,
                              displayedComponents: .date)
                        .datePickerStyle(WheelDatePickerStyle())
                        .labelsHidden()
                        .colorScheme(.dark)
                        .scaleEffect(1.2)
                        .padding()
                        .background(
                            RoundedRectangle(cornerRadius: 20)
                                .fill(Color.black.opacity(0.3))
                                .overlay(
                                    RoundedRectangle(cornerRadius: 20)
                                        .stroke(Color.mysticalPurple.opacity(0.3), lineWidth: 1)
                                )
                        )
                        .padding(.horizontal)

                    Spacer()
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("戻る") {
                        // タップ音
                        SoundManager.shared.playTapSound(.cancel)
                        dismiss()
                    }
                    .foregroundColor(Color.mysticalPurple)
                }

                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("保存") {
                        // タップ音
                        SoundManager.shared.playTapSound(.confirm)

                        let calendar = Calendar.current
                        let components = calendar.dateComponents([.year, .month, .day], from: selectedDate)

                        userModel.birthYear = components.year ?? 1990
                        userModel.birthMonth = components.month ?? 1
                        userModel.birthDay = components.day ?? 1

                        userModel.saveToUserDefaults()
                        dismiss()
                    }
                    .foregroundColor(Color.mysticalPurple)
                    .font(.system(size: 17, weight: .semibold))
                }
            }
            .onAppear {
                // 現在の生年月日をDatePickerに設定
                let calendar = Calendar.current
                let components = DateComponents(
                    year: userModel.birthYear,
                    month: userModel.birthMonth,
                    day: userModel.birthDay
                )
                if let date = calendar.date(from: components) {
                    selectedDate = date
                }
            }
        }
    }
}
