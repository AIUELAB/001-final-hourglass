import SwiftUI

struct CacheSettingsView: View {
    @State private var showAlert = false
    @State private var alertMessage = ""
    @State private var cacheStatus = CacheManager.shared.checkCacheStatus()

    var body: some View {
        Form {
            Section(header: Text("キャッシュ管理")) {
                // キャッシュ状態
                VStack(alignment: .leading, spacing: 8) {
                    Label("キャッシュ状態", systemImage: "internaldrive")
                        .font(.headline)

                    Group {
                        HStack {
                            Text("閲覧済みエピソード:")
                            Spacer()
                            Text(cacheStatus.hasViewedIds ? "あり" : "なし")
                                .foregroundColor(cacheStatus.hasViewedIds ? .orange : .gray)
                        }

                        HStack {
                            Text("最終閲覧日:")
                            Spacer()
                            Text(cacheStatus.hasLastDate ? "記録あり" : "なし")
                                .foregroundColor(cacheStatus.hasLastDate ? .green : .gray)
                        }

                        HStack {
                            Text("今日のエピソード:")
                            Spacer()
                            Text(cacheStatus.hasDailyEpisode ? "キャッシュ済み" : "なし")
                                .foregroundColor(cacheStatus.hasDailyEpisode ? .blue : .gray)
                        }

                        HStack {
                            Text("オフライン用:")
                            Spacer()
                            Text(cacheStatus.hasCachedEpisodes ? "保存済み" : "なし")
                                .foregroundColor(cacheStatus.hasCachedEpisodes ? .purple : .gray)
                        }
                    }
                    .font(.system(size: 14))
                }
                .padding(.vertical, 4)

                // 古いキャッシュの検出
                if CacheManager.shared.hasOldCache() {
                    HStack {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundColor(.yellow)
                        Text("古いキャッシュが検出されました")
                            .font(.system(size: 14))
                            .foregroundColor(.yellow)
                    }
                    .padding(.vertical, 4)
                }

                // キャッシュクリアボタン
                Button(action: clearCache) {
                    HStack {
                        Image(systemName: "trash")
                        Text("キャッシュをクリア")
                    }
                    .foregroundColor(.red)
                }
                .padding(.vertical, 4)
            }

            Section(footer: Text("キャッシュをクリアすると、保存されたエピソードや閲覧履歴がリセットされ、新しいエピソードが表示されます。")) {
                EmptyView()
            }
        }
        .navigationTitle("キャッシュ設定")
        .navigationBarTitleDisplayMode(.inline)
        .alert(isPresented: $showAlert) {
            Alert(
                title: Text("キャッシュクリア完了"),
                message: Text(alertMessage),
                dismissButton: .default(Text("OK")) {
                    // キャッシュ状態を更新
                    cacheStatus = CacheManager.shared.checkCacheStatus()
                }
            )
        }
    }

    private func clearCache() {
        // キャッシュクリア実行
        CacheManager.shared.clearAllEpisodeCache()

        // EpisodeManagerもリセット
        EpisodeManager.shared.resetAllData()

        // アラート表示
        alertMessage = "キャッシュがクリアされました。\n次回アプリ起動時に新しいエピソードが読み込まれます。"
        showAlert = true
    }
}
