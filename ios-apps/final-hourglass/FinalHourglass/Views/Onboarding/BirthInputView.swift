// periphery:ignore:all - 将来使用予定
import SwiftUI

struct BirthInputView: View {
    @ObservedObject var userModel: UserModel
    @State private var birthDate: Date
    @State private var showResult = false

    init(userModel: UserModel) {
        self.userModel = userModel
        // UserModelの値から初期値生成（なければDate()でもOK）
        let components = DateComponents(
            year: userModel.birthYear,
            month: userModel.birthMonth,
            day: userModel.birthDay
        )
        _birthDate = State(initialValue: Calendar.current.date(from: components) ?? Date())
    }

    var body: some View {
        VStack(spacing: 32) {
            Text("生年月日を選択してください")
                .font(.title2)

            DatePicker(
                "生年月日",
                selection: $birthDate,
                displayedComponents: .date
            )
            .datePickerStyle(.graphical)
            .environment(\.locale, Locale(identifier: "ja_JP"))
            .labelsHidden()
            .onChange(of: birthDate) { _ in
                // 日付選択時の音
                SoundManager.shared.playSelectionSound()
            }

            Button("進む") {
                // タップ音（確認）
                SoundManager.shared.playTapSound(.confirm)

                // UserModelに日付を反映
                let comps = Calendar.current.dateComponents([.year, .month, .day], from: birthDate)
                userModel.birthYear = comps.year ?? userModel.birthYear
                userModel.birthMonth = comps.month ?? userModel.birthMonth
                userModel.birthDay = comps.day ?? userModel.birthDay
                showResult = true
            }
            .buttonStyle(.borderedProminent)
            .padding(.top, 20)
        }
        .padding()
        .fullScreenCover(isPresented: $showResult) {
            // iOS 16.0互換性を考慮してnavigationDestinationからfullScreenCoverに変更
            LifeResultView().environmentObject(userModel)
        }
    }
}
