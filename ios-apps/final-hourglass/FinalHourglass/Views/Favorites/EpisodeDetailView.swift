import SwiftUI

/// エピソード詳細View（お気に入りからの遷移先）
struct EpisodeDetailView: View {
    let favorite: FavoriteEpisode
    @Environment(\.dismiss) private var dismiss
    @ObservedObject private var favoriteManager = FavoriteEpisodeManager.shared

    var body: some View {
        NavigationView {
            ZStack {
                // 背景
                RadialGradient(
                    gradient: Gradient(colors: [
                        AppColors.darkPurple,
                        AppColors.midnightBlue,
                        Color.black
                    ]),
                    center: .center,
                    startRadius: 50,
                    endRadius: 400
                )
                .ignoresSafeArea()

                ScrollView {
                    VStack(alignment: .leading, spacing: 24) {
                        // 人物情報ヘッダー
                        personInfoSection

                        // エピソード本文
                        episodeContentSection

                        // メタ情報
                        metaInfoSection

                        Spacer(minLength: 40)
                    }
                    .padding(20)
                }
            }
            .navigationTitle("エピソード詳細")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("閉じる") {
                        dismiss()
                    }
                    .foregroundColor(.white)
                }

                ToolbarItem(placement: .navigationBarTrailing) {
                    // お気に入り解除ボタン
                    Button(action: {
                        favoriteManager.removeFavorite(episodeId: favorite.id)
                        dismiss()
                    }) {
                        Image(systemName: "heart.fill")
                            .foregroundColor(AppColors.hotPink)
                    }
                }
            }
        }
    }

    // MARK: - Sections

    /// 人物情報セクション
    private var personInfoSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            // 人物名（日本語）
            Text(favorite.episode.personNameJa ?? favorite.episode.personName)
                .font(.system(size: 24, weight: .bold))
                .foregroundColor(.white)

            // 人物名（英語、日本語名がある場合）
            if let jaName = favorite.episode.personNameJa, !jaName.isEmpty {
                Text(favorite.episode.personName)
                    .font(.system(size: 14))
                    .foregroundColor(.white.opacity(0.6))
            }

            // 人物タイプ & 作品名（架空キャラの場合）
            HStack(spacing: 8) {
                if favorite.episode.isFictional {
                    Text("架空キャラクター")
                        .font(.system(size: 12, weight: .medium))
                        .foregroundColor(.white.opacity(0.7))
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(
                            Capsule()
                                .fill(AppColors.mediumPurple.opacity(0.3))
                        )

                    if let workTitle = favorite.episode.workTitle {
                        Text(workTitle)
                            .font(.system(size: 12))
                            .foregroundColor(.white.opacity(0.6))
                    }
                } else {
                    Text("実在人物")
                        .font(.system(size: 12, weight: .medium))
                        .foregroundColor(.white.opacity(0.7))
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(
                            Capsule()
                                .fill(AppColors.antiqueGold.opacity(0.3))
                        )
                }
            }
        }
        .padding(20)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(Color.black.opacity(0.4))
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(AppColors.antiqueGold.opacity(0.2), lineWidth: 1)
                )
        )
    }

    /// エピソード本文セクション
    private var episodeContentSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            // 年齢ラベル
            if let age = favorite.episode.episodeAge {
                HStack {
                    Image(systemName: "clock.fill")
                        .font(.system(size: 14))
                        .foregroundColor(AppColors.antiqueGold)

                    Text("\(age)歳のとき")
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundStyle(
                            LinearGradient(
                                colors: [AppColors.antiqueGold, AppColors.amber],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                }
            }

            // エピソード本文
            Text(getCleanEpisodeText())
                .font(.system(size: 16))
                .foregroundColor(.white.opacity(0.9))
                .lineSpacing(8)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(20)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(Color.black.opacity(0.4))
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(AppColors.mediumPurple.opacity(0.2), lineWidth: 1)
                )
        )
    }

    /// メタ情報セクション
    private var metaInfoSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("情報")
                .font(.system(size: 14, weight: .semibold))
                .foregroundColor(.white.opacity(0.6))

            Divider()
                .background(Color.white.opacity(0.2))

            // お気に入り追加日
            HStack {
                Text("お気に入り追加")
                    .foregroundColor(.white.opacity(0.6))
                Spacer()
                Text(favorite.formattedAddedAt)
                    .foregroundColor(.white.opacity(0.8))
            }
            .font(.system(size: 14))
        }
        .padding(20)
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(Color.black.opacity(0.3))
        )
    }

    // MARK: - Static Regex（パフォーマンス向上のためstaticにキャッシュ）

    private static let cleanEpisodeRegex: NSRegularExpression? = {
        try? NSRegularExpression(pattern: "^あなたと同じ\\d+歳のとき、.+?は", options: [])
    }()

    // MARK: - Helpers

    /// エピソードテキストから「あなたと同じX歳のとき、○○は」を除去
    private func getCleanEpisodeText() -> String {
        let text = favorite.episode.episode

        guard let regex = Self.cleanEpisodeRegex else {
            return text
        }

        let range = NSRange(text.startIndex..., in: text)
        let result = regex.stringByReplacingMatches(in: text, options: [], range: range, withTemplate: "")
        return result.trimmingCharacters(in: .whitespaces)
    }
}
