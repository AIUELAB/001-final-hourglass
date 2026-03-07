import os
import SwiftUI

private let lifeResultLogger = Logger(subsystem: "com.finalhourglass.liferesult", category: "episode")

// MARK: - 定数
enum LifeResultScrollID {
    static let episodeSection = "episodeSection"
}

// MARK: - エピソードティーザーカード
/// 進捗率の下に表示するエピソードプレビュー。タップでエピソードセクションにスクロール。
struct EpisodeTeaserCard: View {
    let currentEpisode: Episode?
    let isLoading: Bool
    let ageInt: Int
    let onTap: () -> Void
    let reduceMotion: Bool
    @State private var bounce = false

    var body: some View {
        Button(action: onTap) {
            VStack(spacing: 10) {
                // ヘッダー行: アイコン + タイトル + chevron
                HStack {
                    Image(systemName: "book.fill")
                        .font(.system(size: 14))
                        .foregroundColor(AppColors.antiqueGold)

                    Text("今日の偉人エピソード")
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundColor(AppColors.antiqueGold)

                    Spacer()

                    Image(systemName: "chevron.down")
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundColor(AppColors.antiqueGold.opacity(0.7))
                        .offset(y: (!reduceMotion && bounce) ? 3 : 0)
                }

                // プレビュー内容
                if isLoading {
                    HStack(spacing: 8) {
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle(tint: .white.opacity(0.5)))
                            .scaleEffect(0.8)
                        Text("読み込み中...")
                            .font(.system(size: 13))
                            .foregroundColor(.white.opacity(0.4))
                    }
                } else if let episode = currentEpisode {
                    // 人物名とエピソード冒頭をプレビュー
                    HStack(alignment: .top, spacing: 0) {
                        Text(episode.personNameJa ?? episode.personName)
                            .font(.system(size: 14, weight: .medium))
                            .foregroundColor(.white.opacity(0.8))
                        Text("のエピソード")
                            .font(.system(size: 14))
                            .foregroundColor(.white.opacity(0.5))
                    }
                } else {
                    Text("\(ageInt)歳の偉人エピソードを読む")
                        .font(.system(size: 14))
                        .foregroundColor(.white.opacity(0.5))
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .frame(maxWidth: .infinity)
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(Color.black.opacity(0.3))
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(
                                LinearGradient(
                                    colors: [
                                        AppColors.antiqueGold.opacity(0.3),
                                        AppColors.mediumPurple.opacity(0.15)
                                    ],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                ),
                                lineWidth: 1
                            )
                    )
            )
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
