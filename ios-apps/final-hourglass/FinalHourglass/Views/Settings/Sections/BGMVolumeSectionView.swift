// periphery:ignore:all - 将来使用予定のUIコンポーネント
import SwiftUI

struct BGMVolumeSectionView: View {
    @StateObject private var soundManager = SoundManager.shared

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                StainedGlassIcon(
                    systemName: "music.note",
                    backgroundColor: Color.mysticBlue.opacity(0.2),
                    borderColor: Color.mysticBlue.opacity(0.3),
                    glowColor: Color.mysticBlue
                )

                Text("BGM音量")
                    .foregroundColor(.white.opacity(0.85))
                    .font(.system(size: 17, weight: .regular))
                    .shadow(color: .black.opacity(0.5), radius: 1.5, x: 0, y: 1)

                Spacer()

                HStack(spacing: 10) {
                    Image(systemName: "speaker.fill")
                        .foregroundColor(.white.opacity(0.5))
                        .font(.system(size: 12))

                    Slider(
                        value: $soundManager.bgmVolume,
                        in: 0...1,
                        onEditingChanged: { _ in
                            soundManager.setBGMVolume(soundManager.bgmVolume)
                            UserDefaults.standard.set(soundManager.bgmVolume, forKey: "bgmVolume")
                        }
                    )
                    .accentColor(Color.mysticalPurple)
                    .frame(width: 100)

                    Image(systemName: "speaker.wave.3.fill")
                        .foregroundColor(.white.opacity(0.5))
                        .font(.system(size: 12))
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
