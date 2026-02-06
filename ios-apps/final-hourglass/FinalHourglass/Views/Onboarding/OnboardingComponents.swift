import SwiftUI

// MARK: - Mystical Selection Button
struct MysticalSelectionButton: View {
    let title: String
    let icon: String
    let isSelected: Bool
    let action: () -> Void

    @State private var isPressed = false

    var body: some View {
        Button(action: {
            // タップ音（選択系）
            SoundManager.shared.playTapSound(.soft)
            action()
        }) {
            HStack(spacing: 15) {
                Image(systemName: icon)
                    .font(.system(size: 20))
                    .frame(width: 30)

                Text(title)
                    .font(.system(size: 16, weight: .medium))

                Spacer()

                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(Color(hex: "32CD32"))
                }
            }
            .foregroundColor(isSelected ? .white : .gray)
            .padding(.horizontal, 20)
            .padding(.vertical, 15)
            .background(
                RoundedRectangle(cornerRadius: 15)
                    .fill(isSelected ? AppColors.mediumPurple.opacity(0.3) : Color.white.opacity(0.05))
                    .overlay(
                        RoundedRectangle(cornerRadius: 15)
                            .stroke(isSelected ? AppColors.mediumPurple : Color.gray.opacity(0.3), lineWidth: 1)
                    )
            )
        }
        .scaleEffect(isPressed ? 0.95 : 1.0)
        .onLongPressGesture(minimumDuration: 0, maximumDistance: .infinity, pressing: { pressing in
            withAnimation(.easeInOut(duration: 0.1)) {
                isPressed = pressing
            }
        }, perform: {})
    }
}

// MARK: - Mystical Diet Check Button
struct MysticalDietCheckButton: View {
    let title: String
    let icon: String
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: {
            // タップ音（選択系）
            SoundManager.shared.playTapSound(.soft)
            action()
        }) {
            HStack(spacing: 15) {
                Image(systemName: icon)
                    .font(.system(size: 20))
                    .foregroundColor(isSelected ? .white : .gray)
                    .frame(width: 30)

                Text(title)
                    .font(.system(size: 15))
                    .foregroundColor(isSelected ? .white : .gray)
                    .multilineTextAlignment(.leading)

                Spacer()

                Image(systemName: isSelected ? "checkmark.square.fill" : "square")
                    .font(.system(size: 20))
                    .foregroundColor(isSelected ? Color(hex: "32CD32") : .gray)
            }
            .padding(.horizontal, 15)
            .padding(.vertical, 12)
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(isSelected ? AppColors.mediumPurple.opacity(0.2) : Color.white.opacity(0.05))
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(isSelected ? AppColors.mediumPurple.opacity(0.5) : Color.gray.opacity(0.3), lineWidth: 1)
                    )
            )
        }
    }
}

// MARK: - Mystical Next Button
struct MysticalNextButton: View {
    let title: String
    let action: () -> Void
    var isEnabled: Bool = true

    @State private var isAnimating = false

    var body: some View {
        Button(action: {
            if isEnabled {
                // タップ音（確認系）
                SoundManager.shared.playTapSound(.confirm)
                action()
            }
        }) {
            ZStack {
                // ボタンの光彩
                RoundedRectangle(cornerRadius: 30)
                    .fill(AppColors.mediumPurple.opacity(isEnabled ? 0.3 : 0.1))
                    .frame(width: 220, height: 60)
                    .blur(radius: 15)
                    .scaleEffect(isAnimating && isEnabled ? 1.15 : 0.95)

                // ボタン本体
                RoundedRectangle(cornerRadius: 30)
                    .fill(LinearGradient(
                        gradient: Gradient(colors: [
                            AppColors.mediumPurple.opacity(isEnabled ? 0.8 : 0.3),
                            AppColors.cornflowerBlue.opacity(isEnabled ? 0.8 : 0.2)
                        ]),
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    ))
                    .frame(width: 200, height: 50)
                    .overlay(
                        // スイープアニメーション
                        GeometryReader { geometry in
                            Rectangle()
                                .fill(
                                    LinearGradient(
                                        colors: [
                                            Color.clear,
                                            Color.white.opacity(0.2),
                                            Color.clear
                                        ],
                                        startPoint: .leading,
                                        endPoint: .trailing
                                    )
                                )
                                .frame(width: geometry.size.width * 0.5)
                                .offset(x: isAnimating && isEnabled ? geometry.size.width : -geometry.size.width)
                                .animation(
                                    isAnimating && isEnabled
                                        ? .linear(duration: 3).repeatCount(5, autoreverses: false)
                                        : .none,
                                    value: isAnimating
                                )
                        }
                            .clipShape(RoundedRectangle(cornerRadius: 30))
                    )

                HStack(spacing: 10) {
                    Text(title)
                        .font(.system(size: 18, weight: .semibold))
                    Image(systemName: "arrow.right")
                        .font(.system(size: 16, weight: .bold))
                }
                .foregroundColor(.white.opacity(isEnabled ? 1.0 : 0.5))
            }
        }
        .disabled(!isEnabled)
        .shadow(color: Color.AppColors.mediumPurple.opacity(isEnabled ? 0.6 : 0.2), radius: 20)
        .onAppear {
            if isEnabled {
                withAnimation(.easeInOut(duration: 1.5).repeatCount(10, autoreverses: true)) {
                    isAnimating = true
                }
            }
        }
        .onDisappear {
            isAnimating = false
        }
    }
}
