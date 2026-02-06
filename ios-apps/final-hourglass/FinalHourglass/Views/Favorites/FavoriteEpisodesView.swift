import SwiftUI
import UIKit

/// お気に入りエピソード一覧View
struct FavoriteEpisodesView: View {
    @ObservedObject private var favoriteManager = FavoriteEpisodeManager.shared
    @State private var selectedFavorite: FavoriteEpisode?

    var body: some View {
        ZStack {
            // 背景（LifeResultViewと同じ神秘的なグラデーション）
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

            if favoriteManager.favorites.isEmpty {
                // 空の状態
                emptyStateView
            } else {
                // お気に入り一覧
                favoriteListView
            }
        }
        .navigationTitle("お気に入り")
        .navigationBarTitleDisplayMode(.inline)
        .sheet(item: $selectedFavorite) { favorite in
            EpisodeDetailView(favorite: favorite)
        }
    }

    // MARK: - Empty State

    private var emptyStateView: some View {
        VStack(spacing: 20) {
            Image(systemName: "heart.slash")
                .font(.system(size: 60))
                .foregroundColor(.white.opacity(0.3))

            Text("お気に入りはまだありません")
                .font(.system(size: 18, weight: .medium))
                .foregroundColor(.white.opacity(0.6))

            Text("エピソードの♡をタップして\nお気に入りに追加しましょう")
                .font(.system(size: 14))
                .foregroundColor(.white.opacity(0.4))
                .multilineTextAlignment(.center)
        }
        .padding()
    }

    // MARK: - Favorite List

    private var favoriteListView: some View {
        List {
            ForEach(favoriteManager.favorites) { favorite in
                FavoriteRowView(favorite: favorite)
                    .listRowBackground(Color.clear)
                    .listRowSeparator(.hidden)
                    .contentShape(Rectangle())
                    .onTapGesture {
                        selectedFavorite = favorite
                    }
            }
            .onDelete(perform: deleteFavorites)
        }
        .listStyle(.plain)
        .modifier(ScrollContentBackgroundHiddenModifier())
    }

    // MARK: - Actions

    private func deleteFavorites(at offsets: IndexSet) {
        favoriteManager.removeFavorites(at: offsets)
    }
}

/// お気に入り一覧の行View
struct FavoriteRowView: View {
    let favorite: FavoriteEpisode

    // MARK: - Static Regex（パフォーマンス向上のためstaticにキャッシュ）

    private static let agePreviewRegex: NSRegularExpression? = {
        try? NSRegularExpression(pattern: "^あなたと同じ\\d+歳のとき、", options: [])
    }()

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // ヘッダー: 人物名 + 追加日
            HStack {
                // 人物名
                Text(favorite.episode.personNameJa ?? favorite.episode.personName)
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundColor(.white)

                Spacer()

                // 追加日
                Text(favorite.shortDate)
                    .font(.system(size: 12))
                    .foregroundColor(.white.opacity(0.5))

                // ハートアイコン
                Image(systemName: "heart.fill")
                    .font(.system(size: 14))
                    .foregroundColor(AppColors.hotPink)
            }

            // エピソード年齢（あれば）
            if let age = favorite.episode.episodeAge {
                Text("\(age)歳のエピソード")
                    .font(.system(size: 12, weight: .medium))
                    .foregroundStyle(
                        LinearGradient(
                            colors: [AppColors.antiqueGold, AppColors.amber],
                            startPoint: .leading,
                            endPoint: .trailing
                        )
                    )
            }

            // エピソード本文（2行まで）
            Text(Self.getEpisodePreview(favorite.episode))
                .font(.system(size: 14))
                .foregroundColor(.white.opacity(0.8))
                .lineLimit(2)
                .lineSpacing(4)
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color.black.opacity(0.4))
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(
                            LinearGradient(
                                colors: [
                                    AppColors.antiqueGold.opacity(0.2),
                                    AppColors.mediumPurple.opacity(0.1)
                                ],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            ),
                            lineWidth: 1
                        )
                )
        )
        .padding(.vertical, 4)
    }

    /// エピソードのプレビューテキストを取得
    /// 「あなたと同じX歳のとき、」を除去した本文
    private static func getEpisodePreview(_ episode: Episode) -> String {
        let text = episode.episode

        guard let regex = agePreviewRegex else {
            return text
        }

        let range = NSRange(text.startIndex..., in: text)
        let result = regex.stringByReplacingMatches(in: text, options: [], range: range, withTemplate: "")
        return result.trimmingCharacters(in: .whitespaces)
    }
}

// MARK: - iOS 16 Compatibility

/// iOS 16互換性のためのViewModifier
/// scrollContentBackground(.hidden)はiOS 16以降でのみ利用可能
private struct ScrollContentBackgroundHiddenModifier: ViewModifier {
    func body(content: Content) -> some View {
        if #available(iOS 16.0, *) {
            content.scrollContentBackground(.hidden)
        } else {
            content
                .onAppear {
                    UITableView.appearance().backgroundColor = .clear
                }
        }
    }
}
