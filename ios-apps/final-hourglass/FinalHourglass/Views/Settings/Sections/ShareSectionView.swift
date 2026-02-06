// periphery:ignore:all - 将来使用予定のUIコンポーネント
import SwiftUI

struct ShareSectionView: View {
    let shareToX: () -> Void
    let shareToInstagram: () -> Void
    let shareToLINE: () -> Void
    let shareToOther: () -> Void

    var body: some View {
        VStack(spacing: 0) {
            ShareItemButton(
                icon: AnyView(Text("𝕏").font(.system(size: 16, weight: .bold)).foregroundColor(.white.opacity(0.9))),
                title: "Xに投稿",
                backgroundColor: Color.black.opacity(0.8),
                borderColor: Color.white.opacity(0.3),
                glowColor: Color.black,
                action: { shareToX() }
            )
            ItemDivider()
            ShareItemButton(
                icon: AnyView(Image(systemName: "camera.fill").foregroundColor(.white.opacity(0.9)).font(.system(size: 16))),
                title: "Instagramストーリー",
                backgroundColor: Color(red: 0.8, green: 0.2, blue: 0.6).opacity(0.2),
                borderColor: Color(red: 0.8, green: 0.2, blue: 0.6).opacity(0.3),
                glowColor: Color(red: 0.8, green: 0.2, blue: 0.6),
                action: { shareToInstagram() }
            )
            ItemDivider()
            ShareItemButton(
                icon: AnyView(Image(systemName: "message.fill").foregroundColor(.white.opacity(0.9)).font(.system(size: 16))),
                title: "LINEで送る",
                backgroundColor: Color(red: 0.0, green: 0.7, blue: 0.0).opacity(0.2),
                borderColor: Color(red: 0.0, green: 0.7, blue: 0.0).opacity(0.3),
                glowColor: Color(red: 0.0, green: 0.7, blue: 0.0),
                action: { shareToLINE() }
            )
            ItemDivider()
            ShareItemButton(
                icon: AnyView(Image(systemName: "square.and.arrow.up").foregroundColor(.white.opacity(0.9)).font(.system(size: 16))),
                title: "その他の方法で共有",
                backgroundColor: Color.gray.opacity(0.2),
                borderColor: Color.gray.opacity(0.3),
                glowColor: Color.gray,
                action: { shareToOther() }
            )
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
