// periphery:ignore:all - ブランドカラーパレット（将来使用予定）
//
//  ColorPalette.swift
//  LastHourglass
//
//  Created by Design System Generator
//  Copyright © 2024 AIUELAB. All rights reserved.
//
//  最期の砂時計 - カラーパレット定義
//  ブランドガイドラインに基づいた色定義
//

import SwiftUI

// MARK: - Global Shortcut Alias
// アプリ全体で Color.AppColors を簡潔に参照できるようにする
typealias AppColors = Color.AppColors

// MARK: - Color Extension
extension Color {
    // MARK: - AppColors (旧ColorExtension.swiftとの互換性のため)
    struct AppColors {
        static let deepCrimson = Color(hex: "8B0000")
        static let charcoalBlack = Color(hex: "1C1C1C")
        static let antiqueGold = Color(hex: "D4A574")
        static let ashWhite = Color(hex: "F5F5F0")
        static let amber = Color.amber
        static let deepForest = Color(hex: "013220")
        static let hotPink = Color.deepPink
        static let crimson = Color.crimson
        static let mediumPurple = Color.mysticalPurple
        static let darkViolet = Color.deepViolet
        static let cornflowerBlue = Color.mysticBlue
        static let darkPurple = Color.deepSpace
        static let midnightBlue = Color.pitchBlack
        static let emeraldGreen = Color.limeGreen
    }

    // MARK: - Primary Colors (神秘的な紫系)
    /// 神秘の紫 - メインブランドカラー
    static let mysticalPurple = Color(hex: "9370DB")

    /// 深い紫 - 深遠さと変容を表現
    static let deepViolet = Color(hex: "8A2BE2")

    /// 神秘的な青 - 希望と昇華を表現
    static let mysticBlue = Color(hex: "6495ED")

    // MARK: - Secondary Colors (補助色)
    /// ラベンダー - 純粋さと浄化
    static let lavender = Color(hex: "E6E6FA")

    /// 黄金 - 価値と永遠性
    static let gold = Color(hex: "FFD700")

    /// 琥珀 - 温かみと生命力
    static let amber = Color(hex: "FFA500")

    // MARK: - Background Colors (背景色)
    /// 深宇宙 - 無限と深淵
    static let deepSpace = Color(hex: "1A0033")

    /// 漆黒 - 終焉と静寂
    static let pitchBlack = Color(hex: "000011")

    /// 純黒 - 絶対と無
    static let pureBlack = Color(hex: "000000")

    // MARK: - Accent Colors (アクセント色)
    /// 深紅 - 生命力
    static let deepPink = Color(hex: "FF1493")

    /// 天空青 - 解放
    static let skyBlue = Color(hex: "00BFFF")

    /// エメラルド - 再生
    static let limeGreen = Color(hex: "32CD32")

    /// クリムゾン - 情熱
    static let crimson = Color(hex: "DC143C")

    /// ダークブルー - 深海
    static let darkBlue = Color(hex: "00008B")

    /// オレンジレッド - 夕焼け
    static let orangeRed = Color(hex: "FF4500")

    // MARK: - Gradient Colors (グラデーション用)
    /// ステンドグラス赤系
    static let stainedGlassRed = Color(hex: "FF1493")

    /// ステンドグラス青系
    static let stainedGlassBlue = Color(hex: "0080FF")

    /// 神秘的な緑
    static let mysticGreen = Color(hex: "00FF00")

    // MARK: - Text Colors (テキスト色)
    /// プライマリテキスト
    static let primaryText = Color.white.opacity(0.9)

    /// セカンダリテキスト
    static let secondaryText = Color.white.opacity(0.85)

    /// 控えめなテキスト
    static let tertiaryText = Color(hex: "9370DB").opacity(0.6)

    /// 無効状態のテキスト
    static let disabledText = Color.white.opacity(0.4)

    // MARK: - Special Effect Colors (特殊効果用)
    /// 光彩効果
    static let glowEffect = Color(hex: "9370DB").opacity(0.6)

    /// ガラス効果の境界線
    static let glassBorder = Color.white.opacity(0.2)

    /// 影の色
    static let shadowColor = Color.black.opacity(0.3)

    // MARK: - Semantic Colors (意味的な色)
    /// 成功
    static let successGreen = Color(hex: "32CD32")

    /// 警告
    static let warningAmber = Color(hex: "FFA500")

    /// エラー
    static let errorRed = Color(hex: "DC143C")

    /// 情報
    static let infoBlue = Color(hex: "6495ED")
}

// MARK: - Gradient Definitions
extension LinearGradient {
    /// 神秘的なグラデーション（メインボタン用）
    static let mysticalGradient = LinearGradient(
        colors: [
            Color(hex: "8A2BE2").opacity(0.15),
            Color(hex: "9370DB").opacity(0.1),
            Color(hex: "6495ED").opacity(0.15)
        ],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )

    /// 砂の流れグラデーション
    static let sandFlowGradient = LinearGradient(
        colors: [
            Color(hex: "E6E6FA").opacity(0.9),
            Color(hex: "9370DB").opacity(0.9),
            Color(hex: "6495ED").opacity(0.9)
        ],
        startPoint: .top,
        endPoint: .bottom
    )

    /// 深宇宙グラデーション（背景用）
    static let deepSpaceGradient = LinearGradient(
        colors: [
            Color(hex: "1A0033"),
            Color(hex: "000011"),
            Color(hex: "000000")
        ],
        startPoint: .top,
        endPoint: .bottom
    )

    /// オーロラグラデーション
    static let auroraGradient = LinearGradient(
        colors: [
            Color.clear,
            Color(hex: "FF00FF").opacity(0.15),
            Color(hex: "0064FF").opacity(0.2),
            Color(hex: "00FFFF").opacity(0.15),
            Color(hex: "FFD700").opacity(0.1),
            Color(hex: "FF0000").opacity(0.15),
            Color.clear
        ],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )
}

// MARK: - Helper Extensions
extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let alphaComponent, redComponent, greenComponent, blueComponent: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (alphaComponent, redComponent, greenComponent, blueComponent) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (alphaComponent, redComponent, greenComponent, blueComponent) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: // ARGB (32-bit)
            (alphaComponent, redComponent, greenComponent, blueComponent) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (alphaComponent, redComponent, greenComponent, blueComponent) = (1, 1, 1, 0)
        }

        self.init(
            .sRGB,
            red: Double(redComponent) / 255,
            green: Double(greenComponent) / 255,
            blue: Double(blueComponent) / 255,
            opacity: Double(alphaComponent) / 255
        )
    }
}
