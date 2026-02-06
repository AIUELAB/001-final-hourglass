// periphery:ignore:all - 将来使用予定のUIコンポーネント
import SwiftUI

struct DirectShareView: UIViewControllerRepresentable {
    func makeUIViewController(context: Context) -> UIActivityViewController {
        let text = "「最期の砂時計」- 人生の残り時間を可視化するアプリ\n\n今すぐダウンロードして、大切な時間を意識しよう！"
        let url = URL(string: "https://apps.apple.com/app/id1234567890")!

        let activityVC = UIActivityViewController(
            activityItems: [text, url],
            applicationActivities: nil
        )

        return activityVC
    }

    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}
