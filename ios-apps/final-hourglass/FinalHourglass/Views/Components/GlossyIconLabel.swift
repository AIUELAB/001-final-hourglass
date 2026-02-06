// periphery:ignore:all - 将来使用予定のUIコンポーネント
//
//  GlossyIconLabel.swift
//  FinalHourglass
//
//  光沢効果付きアイコンラベルコンポーネント
//

import SwiftUI

struct GlossyIconLabel: View {
    // MARK: - プロパティ（この部品が受け取る設定値）
    let icon: String           // SF Symbolsのアイコン名
    let text: String           // 表示するテキスト
    let iconColor: Color       // アイコンの背景色
    let shadowColor: Color     // 影の色

    // MARK: - Body（見た目の定義）
    var body: some View {
        HStack(spacing: 12) {
            // アイコン部分
            iconView

            // テキスト部分
            textView
        }
    }

    // MARK: - Private Views（部品を更に細かく分割）

    // アイコンの見た目
    private var iconView: some View {
        ZStack {
            // 背景の四角形
            RoundedRectangle(cornerRadius: 6)
                .fill(iconColor.opacity(0.2))
                .overlay(
                    RoundedRectangle(cornerRadius: 6)
                        .stroke(iconColor.opacity(0.3), lineWidth: 1)
                )
                .frame(width: 28, height: 28)
                .shadow(color: shadowColor.opacity(0.3), radius: 8)

            // アイコン画像
            Image(systemName: icon)
                .foregroundColor(.white.opacity(0.9))
                .font(.system(size: 16))
        }
        // .glossyIcon() // 光沢効果を追加（コメントアウト）
    }

    // テキストの見た目
    private var textView: some View {
        Text(text)
            .foregroundColor(.white.opacity(0.85))
            .font(.system(size: 17, weight: .regular))
            .shadow(color: .black.opacity(0.5), radius: 1.5, x: 0, y: 1)
    }
}
