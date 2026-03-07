import os
import SwiftUI

private let lifeResultLogger = Logger(subsystem: "com.finalhourglass.liferesult", category: "episode")

// MARK: - 定数
enum LifeResultScrollID {
    static let episodeSection = "episodeSection"
}

// MARK: - スクロールヒントビュー
struct ScrollHintView: View {
    let reduceMotion: Bool
    let onTap: () -> Void
    @State private var bounce = false

    var body: some View {
        Button(action: onTap) {
            VStack(spacing: 6) {
                Text("偉人のエピソードを見る")
                    .font(.caption)
                    .foregroundColor(.white.opacity(0.5))
                Image(systemName: "chevron.compact.down")
                    .font(.title2)
                    .foregroundColor(AppColors.antiqueGold.opacity(0.6))
                    .offset(y: (!reduceMotion && bounce) ? 4 : 0)
            }
        }
        .buttonStyle(.plain)
        .onAppear {
            guard !reduceMotion else { return }
            withAnimation(
                .easeInOut(duration: 1.2)
                .repeatForever(autoreverses: true)
            ) {
                bounce = true
            }
        }
    }
}

// MARK: - フォールバックエピソードビュー
/// API取得失敗時に表示するフォールバックエピソードのビュー
struct FallbackEpisodeView: View {
    let ageInt: Int
    let fallbackEpisode: EpisodeContent

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
                Text(fallbackEpisode.ageText)
                .font(.system(size: 14, weight: .medium))
                .foregroundStyle(
                    LinearGradient(
                        colors: [AppColors.antiqueGold, AppColors.amber],
                        startPoint: .leading,
                        endPoint: .trailing
                    )
                )

            Text(fallbackEpisode.personName)
                .font(.system(size: 20, weight: .semibold))
                .foregroundColor(.white)

            Text(fallbackEpisode.episodeText)
                .font(.system(size: 16))
                .foregroundColor(.white.opacity(0.9))
                .lineSpacing(8)
                .multilineTextAlignment(.leading)
                .fixedSize(horizontal: false, vertical: true)
        }
        .onAppear {
            lifeResultLogger.warning("API取得失敗、フォールバックエピソードを表示: age=\(ageInt)")
        }
    }
}

// MARK: - PreferenceKey（スクロール検知）
struct EpisodeSectionVisibleKey: PreferenceKey {
    static var defaultValue: Bool = false
    static func reduce(value: inout Bool, nextValue: () -> Bool) {
        value = value || nextValue()
    }
}
