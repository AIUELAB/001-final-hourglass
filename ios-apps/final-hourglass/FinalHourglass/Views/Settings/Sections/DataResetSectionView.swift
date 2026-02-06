// periphery:ignore:all - 将来使用予定のUIコンポーネント
import SwiftUI

struct DataResetSectionView: View {
    @StateObject private var soundManager = SoundManager.shared
    @Binding var showingResetAlert: Bool

    var body: some View {
        VStack(spacing: 0) {
            Button(action: {
                soundManager.playTapSound(.warning)
                showingResetAlert = true
            }) {
                HStack {
                    StainedGlassIcon(
                        systemName: "trash.fill",
                        backgroundColor: Color.crimson.opacity(0.2),
                        borderColor: Color.crimson.opacity(0.3),
                        glowColor: Color.crimson
                    )
                    Text("データをリセットして最初から始める")
                        .foregroundColor(.red)
                        .font(.system(size: 17, weight: .regular))
                        .shadow(color: .red.opacity(0.3), radius: 1.5, x: 0, y: 1)
                    Spacer()
                    Image(systemName: "chevron.right")
                        .foregroundColor(.secondary)
                        .font(.system(size: 16))
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
        .background(
            RoundedRectangle(cornerRadius: 14)
                .fill(Color(white: 0.11, opacity: 0.4))
                .overlay(
                    RoundedRectangle(cornerRadius: 14)
                        .stroke(Color.mysticalPurple.opacity(0.1), lineWidth: 1)
                )
        )
        .listRowBackground(Color.clear)
        .listRowInsets(EdgeInsets(top: 0, leading: 20, bottom: 16, trailing: 20))
    }
}
