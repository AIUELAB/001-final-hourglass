// periphery:ignore:all - デザインシステムの基盤トークン（将来使用予定）
//
//  DesignTokens.swift
//  LastHourglass
//
//  Created by Design System Generator
//  Copyright © 2024 AIUELAB. All rights reserved.
//
//  最期の砂時計 - デザイントークン定義
//  スペーシング、サイズ、アニメーション等の定数
//

import SwiftUI
import UIKit

// MARK: - Spacing System
enum Spacing {
    /// 極小: 5pt
    static let xxs: CGFloat = 5

    /// 小: 10pt
    static let xs: CGFloat = 10

    /// 標準: 20pt
    static let sm: CGFloat = 20

    /// 中: 40pt
    static let md: CGFloat = 40

    /// 大: 60pt
    static let lg: CGFloat = 60

    /// 特大: 120pt
    static let xl: CGFloat = 120

    /// カスタムスペーシング
    static let buttonGap: CGFloat = 22
    static let sectionGap: CGFloat = 32
}

// MARK: - Typography
enum Typography {
    // MARK: Font Names
    enum FontName {
        static let serifJP = "Noto Serif JP"
        static let mincho = "Hiragino Mincho ProN"
        static let gothic = "Hiragino Sans"
        static let system = "-apple-system"
    }

    // MARK: Font Sizes
    enum Size {
        static let xxl: CGFloat = 40  // 特大見出し
        static let xl: CGFloat = 30   // 大見出し
        static let lg: CGFloat = 24   // 中見出し
        static let md: CGFloat = 20   // 本文
        static let sm: CGFloat = 18   // キャプション
        static let xs: CGFloat = 16   // 極小
    }

    // MARK: Font Weights
    enum Weight {
        static let ultraLight = Font.Weight.ultraLight
        static let light = Font.Weight.light
        static let regular = Font.Weight.regular
        static let medium = Font.Weight.medium
        static let semibold = Font.Weight.semibold
    }

    // MARK: Letter Spacing
    enum LetterSpacing {
        static let loose: CGFloat = 0.25  // em単位
        static let normal: CGFloat = 0.15
        static let tight: CGFloat = 0.08
        static let tighter: CGFloat = 0.05
        static let tightest: CGFloat = 0.1
    }

    // MARK: Line Height
    enum LineHeight {
        static let compressed: CGFloat = 1.2
        static let normal: CGFloat = 1.5
        static let relaxed: CGFloat = 1.7
        static let loose: CGFloat = 2.0
    }
}

// MARK: - Animation Timing
enum AnimationTiming {
    /// 瞬間的: 0.1秒 - マイクロインタラクション
    static let instant: Double = 0.1

    /// 標準: 0.3秒 - 状態変化
    static let standard: Double = 0.3

    /// ゆっくり: 2.5秒 - フェードイン
    static let slow: Double = 2.5

    /// 儀式的: 6秒 - 砂の流れ
    static let ceremonial: Double = 6.0

    /// 永遠: 25-30秒 - 背景の動き
    static let eternal: Double = 25.0
    static let eternalLong: Double = 30.0

    /// カスタムタイミング
    static let sweep: Double = 4.0
    static let mysticalFloat: Double = 6.0
    static let auroaDrift: Double = 25.0
    static let particleRise: Double = 10.0
}

// MARK: - Corner Radius
enum CornerRadius {
    static let none: CGFloat = 0
    static let sm: CGFloat = 8
    static let md: CGFloat = 14
    static let lg: CGFloat = 25
    static let xl: CGFloat = 40
    static let pill: CGFloat = 9999
}

// MARK: - Border Width
enum BorderWidth {
    static let hairline: CGFloat = 0.5
    static let thin: CGFloat = 1.0
    static let medium: CGFloat = 1.5
    static let thick: CGFloat = 2.0
}

// MARK: - Shadow
enum Shadow {
    struct Style {
        let color: Color
        let radius: CGFloat
        let xOffset: CGFloat
        let yOffset: CGFloat
    }

    /// 基本的な影
    static let basic = Style(
        color: .black.opacity(0.1),
        radius: 5,
        xOffset: 0,
        yOffset: 2
    )

    /// 神秘的な光彩
    static let mysticalGlow = Style(
        color: Color(hex: "9370DB").opacity(0.6),
        radius: 25,
        xOffset: 0,
        yOffset: 0
    )

    /// ボタンの光彩
    static let buttonGlow = Style(
        color: Color(hex: "9370DB").opacity(0.3),
        radius: 25,
        xOffset: 0,
        yOffset: 0
    )

    /// ホバー時の強い光彩
    static let hoverGlow = Style(
        color: Color(hex: "9370DB").opacity(0.5),
        radius: 40,
        xOffset: 0,
        yOffset: 0
    )

    /// 内側の光
    static let innerGlow = Style(
        color: Color(hex: "6495ED").opacity(0.1),
        radius: 20,
        xOffset: 0,
        yOffset: 0
    )
}

// MARK: - Blur Effects
enum BlurEffect {
    static let light: CGFloat = 3
    static let medium: CGFloat = 8
    static let heavy: CGFloat = 15
    static let extreme: CGFloat = 25
}

// MARK: - Opacity Levels
enum Opacity {
    static let invisible: Double = 0
    static let barely: Double = 0.1
    static let faint: Double = 0.2
    static let light: Double = 0.4
    static let medium: Double = 0.6
    static let strong: Double = 0.8
    static let opaque: Double = 1.0
}

// MARK: - Device Sizes
enum DeviceSize {
    static let iPhoneSE = CGSize(width: 320, height: 568)
    static let iPhone8 = CGSize(width: 375, height: 667)
    static let iPhone12 = CGSize(width: 390, height: 844)
    static let iPhone14Pro = CGSize(width: 393, height: 852)
    static let iPhone14ProMax = CGSize(width: 430, height: 932)
    static let iPad = CGSize(width: 768, height: 1024)

    /// デフォルトのiPhoneコンテナサイズ
    static let defaultPhone = CGSize(width: 375, height: 812)
}

// MARK: - Component Sizes
enum ComponentSize {
    /// 砂時計のサイズ
    static let hourglassIcon = CGSize(width: 90, height: 90)
    static let hourglassFrame = CGSize(width: 200, height: 200)

    /// ボタンのサイズ
    static let primaryButton = CGSize(width: 290, height: 50)
    static let minimumTapTarget = CGSize(width: 44, height: 44)

    /// ステータスバー
    static let statusBarHeight: CGFloat = 50

    /// ホームインジケーター
    static let homeIndicator = CGSize(width: 134, height: 5)
}

// MARK: - Z-Index Layers
enum ZIndex {
    static let background: Double = 0
    static let environment: Double = 1
    static let decoration: Double = 2
    static let content: Double = 10
    static let overlay: Double = 50
    static let statusBar: Double = 100
}

// MARK: - Animation Curves
extension Animation {
    /// 神秘的な浮遊アニメーション
    static let mysticalFloat = Animation.easeInOut(duration: AnimationTiming.mysticalFloat)

    /// 標準的なトランジション
    static let standardTransition = Animation.easeInOut(duration: AnimationTiming.standard)

    /// ゆっくりとしたフェード
    static let slowFade = Animation.easeOut(duration: AnimationTiming.slow)

    /// 永遠の動き
    static let eternalMotion = Animation.linear(duration: AnimationTiming.eternal).repeatForever(autoreverses: false)

    /// パーティクルの上昇
    static let particleRise = Animation.linear(duration: AnimationTiming.particleRise).repeatForever(autoreverses: false)
}

// MARK: - Gradient Angle
enum GradientAngle {
    static let horizontal: UnitPoint = .leading
    static let vertical: UnitPoint = .top
    static let diagonal: UnitPoint = .topLeading
    static let diagonalReverse: UnitPoint = .topTrailing
}

// MARK: - Glass Effect Settings
struct GlassEffect {
    static let material: Material = .ultraThinMaterial
    static let blurRadius: CGFloat = 8
    static let opacity: Double = 0.8
}

// MARK: - Haptic Feedback
enum HapticStyle {
    case light
    case medium
    case heavy
    case success
    case warning
    case error

    @available(iOS 13.0, *)
    var impact: UIImpactFeedbackGenerator.FeedbackStyle {
        switch self {
        case .light: return .light
        case .medium: return .medium
        case .heavy: return .heavy
        case .success: return .medium
        case .warning: return .medium
        case .error: return .heavy
        }
    }
}

// MARK: - Accessibility
enum Accessibility {
    /// 最小フォントサイズ
    static let minimumFontSize: CGFloat = 14

    /// 最小タップ領域
    static let minimumTapArea: CGFloat = 44

    /// コントラスト比
    enum ContrastRatio {
        static let largeText: Double = 3.0
        static let normalText: Double = 4.5
    }
}

// MARK: - Layout Constants
enum Layout {
    /// セーフエリアのパディング
    static let safeAreaPadding: CGFloat = 25

    /// コンテンツの最大幅
    static let maxContentWidth: CGFloat = 600

    /// グリッドの列数
    static let gridColumns: Int = 12
}

// MARK: - File Naming Convention
enum FileNaming {
    static let mysticalPrefix = "mystical_"
    static let stainedGlassPrefix = "stained_glass_"
    static let divinePrefix = "divine_"
}
