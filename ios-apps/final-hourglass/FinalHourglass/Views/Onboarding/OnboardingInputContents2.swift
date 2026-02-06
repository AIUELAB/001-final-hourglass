import SwiftUI

// MARK: - 婚姻状況入力
struct MaritalStatusInputContent: View {
    @Binding var maritalStatus: String
    @Binding var marriageDuration: Int
    let onNext: () -> Void

    @State private var showingMarriageDuration = false

    let options = [
        ("single", "未婚", "person.fill"),
        ("married", "既婚", "heart.circle.fill"),
        ("divorced", "離婚", "heart.slash"),
        ("widowed", "死別", "heart")
    ]

    var body: some View {
        VStack(spacing: 30) {
            // アイコン
            Image(systemName: "heart.text.square.fill")
                .font(.system(size: 60))
                .foregroundStyle(
                    LinearGradient(
                        colors: [AppColors.mediumPurple, AppColors.cornflowerBlue],
                        startPoint: .top,
                        endPoint: .bottom
                    )
                )
                .padding(.bottom, 10)

            // 選択肢
            VStack(spacing: 15) {
                ForEach(options, id: \.0) { value, title, icon in
                    MysticalSelectionButton(
                        title: title,
                        icon: icon,
                        isSelected: maritalStatus == value,
                        action: {
                            maritalStatus = value
                            // 既婚、離婚、死別の場合は結婚期間を入力
                            if value == "married" || value == "divorced" || value == "widowed" {
                                withAnimation {
                                    showingMarriageDuration = true
                                }
                            } else {
                                showingMarriageDuration = false
                                marriageDuration = 0  // 未婚は0年にリセット
                                onNext()
                            }
                        }
                    )
                }
            }
            .padding(.horizontal, 40)

            // 結婚期間の入力（既婚・離婚・死別選択時）
            if showingMarriageDuration {
                VStack(spacing: 20) {
                    Divider()
                        .background(Color.gray.opacity(0.3))
                        .padding(.horizontal, 40)

                    Text(marriageDurationTitle)
                        .font(.system(size: 18, weight: .medium))
                        .foregroundColor(.white)

                    // 結婚期間表示
                    Text("\(marriageDuration)年")
                        .font(.system(size: 32, weight: .bold))
                        .foregroundColor(AppColors.deepCrimson)
                        .padding(.vertical, 10)

                    // スライダー
                    VStack(spacing: 10) {
                        Slider(value: Binding(
                            get: { Double(marriageDuration) },
                            set: { marriageDuration = Int($0) }
                        ), in: 0...60, step: 1)
                        .accentColor(AppColors.mediumPurple)
                        .padding(.horizontal, 40)

                        HStack {
                            Text("新婚")
                                .font(.caption)
                                .foregroundColor(.gray)
                            Spacer()
                            Text("60年")
                                .font(.caption)
                                .foregroundColor(.gray)
                        }
                        .padding(.horizontal, 40)
                    }

                    // 説明文
                    HStack {
                        Image(systemName: "info.circle")
                            .foregroundColor(AppColors.cornflowerBlue)
                        Text(marriageDurationDescription)
                            .font(.caption)
                            .foregroundColor(.gray)
                    }
                    .padding(.top, 10)

                    MysticalNextButton(title: "次へ", action: onNext)
                        .padding(.top, 20)
                }
                .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
    }

    // 婚姻状況に応じたタイトル
    private var marriageDurationTitle: String {
        switch maritalStatus {
        case "married":
            return "結婚期間"
        case "divorced":
            return "結婚していた期間"
        case "widowed":
            return "結婚していた期間"
        default:
            return "結婚期間"
        }
    }

    // 婚姻状況に応じた説明文
    private var marriageDurationDescription: String {
        switch maritalStatus {
        case "married":
            return "結婚してから現在までの年数を入力してください"
        case "divorced":
            return "結婚していた期間の合計年数を入力してください"
        case "widowed":
            return "結婚していた期間の年数を入力してください"
        default:
            return "結婚期間を入力してください"
        }
    }
}
