//
//  ShareSheetView.swift
//  FinalHourglass
//
//  SNS共有シート画面
//

import SwiftUI

struct ShareSheetView: View {
    @Environment(\.dismiss) var dismiss
    @EnvironmentObject var userModel: UserModel

    // 残り寿命を計算
    var remainingYears: Int {
        let lifeExpectancy = calculateLifeExpectancy(user: userModel) ?? 84.0
        let currentAge = Double(Calendar.current.dateComponents([.year], from: userModel.birthDate, to: Date()).year ?? 0)
        return max(0, Int(lifeExpectancy - currentAge))
    }

    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                // ヘッダー
                headerView

                // プレビューカード
                previewCard

                // SNSボタン
                snsButtons

                Spacer()
            }
            .navigationBarHidden(true)
        }
    }

    // MARK: - Views

    private var headerView: some View {
        HStack {
            Button("キャンセル") {
                dismiss()
            }
            Spacer()
            Text("SNSに投稿")
                .font(.headline)
            Spacer()
            // 右側のスペースを均等にするための透明なボタン
            Button("キャンセル") { }
                .opacity(0)
                .disabled(true)
        }
        .padding()
    }

    private var previewCard: some View {
        VStack(spacing: 16) {
            Image(systemName: "hourglass")
                .font(.system(size: 60))
                .foregroundColor(.orange)

            Text("私の人生の残り時間")
                .font(.headline)

            Text("約\(remainingYears)年")
                .font(.largeTitle)
                .fontWeight(.bold)
                .foregroundColor(.red)

            Text("今を大切に生きよう")
                .font(.subheadline)
                .foregroundColor(.secondary)

            Text("#人生のタイムリミット")
                .font(.footnote)
                .foregroundColor(.blue)
        }
        .padding(30)
        .frame(maxWidth: .infinity)
        .background(
            RoundedRectangle(cornerRadius: 20)
                .fill(Color(.systemGray6))
        )
        .padding(.horizontal)
    }

    private var snsButtons: some View {
        VStack(spacing: 12) {
            ShareButton(
                title: "Xに投稿",
                icon: "x.circle.fill",
                color: .black
            ) {
                shareToX()
            }

            ShareButton(
                title: "Instagramストーリー",
                icon: "camera.fill",
                color: Color(red: 0.8, green: 0.2, blue: 0.6)
            ) {
                shareToInstagram()
            }

            ShareButton(
                title: "LINEで送る",
                icon: "message.fill",
                color: Color(red: 0.0, green: 0.7, blue: 0.0)
            ) {
                shareToLINE()
            }

            ShareButton(
                title: "その他の方法で共有",
                icon: "square.and.arrow.up",
                color: .gray
            ) {
                shareToOther()
            }
        }
        .padding(.horizontal)
    }

    // MARK: - Share Methods

    private func shareToX() {
        let text = "私の人生の残り時間は約\(remainingYears)年。今を大切に生きよう！ #人生のタイムリミット"
        if let url = URL(string: "https://twitter.com/intent/tweet?text=\(text.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")") {
            UIApplication.shared.open(url)
        }
        dismiss()
    }

    private func shareToInstagram() {
        // Instagram Stories APIの実装
        let alert = UIAlertController(
            title: "Instagram",
            message: "画像を保存してInstagramストーリーに投稿してください",
            preferredStyle: .alert
        )
        alert.addAction(UIAlertAction(title: "OK", style: .default))

        if let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
           let window = windowScene.windows.first,
           let rootViewController = window.rootViewController {
            rootViewController.present(alert, animated: true)
        }

        dismiss()
    }

    private func shareToLINE() {
        let text = "私の人生の残り時間は約\(remainingYears)年。今を大切に生きよう！"
        if let url = URL(string: "line://msg/text/\(text.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")") {
            if UIApplication.shared.canOpenURL(url) {
                UIApplication.shared.open(url)
            } else {
                // LINEアプリがインストールされていない場合
                if let appStoreURL = URL(string: "https://apps.apple.com/app/line/id443904275") {
                    UIApplication.shared.open(appStoreURL)
                }
            }
        }
        dismiss()
    }

    private func shareToOther() {
        let text = "私の人生の残り時間は約\(remainingYears)年。今を大切に生きよう！ #人生のタイムリミット"
        let url = URL(string: "https://apps.apple.com/app/id1234567890")! // 実際のApp Store URLに置き換え

        let activityVC = UIActivityViewController(
            activityItems: [text, url],
            applicationActivities: nil
        )

        // iPadでのポップオーバー対応
        if let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
           let window = windowScene.windows.first,
           let rootViewController = window.rootViewController {
            if let popover = activityVC.popoverPresentationController {
                popover.sourceView = rootViewController.view
                popover.sourceRect = CGRect(x: rootViewController.view.bounds.midX,
                                            y: rootViewController.view.bounds.midY,
                                            width: 0,
                                            height: 0)
                popover.permittedArrowDirections = []
            }

            rootViewController.present(activityVC, animated: true)
        }

        dismiss()
    }
}

// MARK: - ShareButton Component
struct ShareButton: View {
    let title: String
    let icon: String
    let color: Color
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 16) {
                Image(systemName: icon)
                    .font(.system(size: 24))
                    .frame(width: 30)

                Text(title)
                    .font(.system(size: 17, weight: .medium))

                Spacer()

                Image(systemName: "chevron.right")
                    .font(.system(size: 14))
                    .foregroundColor(.white.opacity(0.6))
            }
            .foregroundColor(.white)
            .padding(.horizontal, 20)
            .padding(.vertical, 16)
            .background(color)
            .cornerRadius(12)
        }
    }
}
