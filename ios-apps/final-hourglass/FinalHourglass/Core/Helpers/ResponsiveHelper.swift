// periphery:ignore:all - 将来使用予定のUIコンポーネント
import SwiftUI

// MARK: - レスポンシブサイズ計算用のヘルパー
// 画面サイズに応じて要素のサイズを自動調整します

struct ResponsiveHelper {
    // 画面の横幅を取得
    static var screenWidth: CGFloat {
        UIScreen.main.bounds.width
    }

    // 画面の縦幅を取得
    static var screenHeight: CGFloat {
        UIScreen.main.bounds.height
    }

    // iPadかどうかを判定
    static var isIPad: Bool {
        UIDevice.current.userInterfaceIdiom == .pad
    }

    // iPhone 14（390pt）を基準にしたスケール計算
    static var scaleFactor: CGFloat {
        if isIPad {
            return 1.5  // iPadは1.5倍
        } else {
            return screenWidth / 390.0  // iPhone 14の幅を基準
        }
    }

    // サイズを画面に応じて調整する関数
    // 使い方: scaledSize(20) → iPhone SEなら約19pt、Pro Maxなら約22pt
    static func scaledSize(_ baseSize: CGFloat, min minSize: CGFloat? = nil, max maxSize: CGFloat? = nil) -> CGFloat {
        var scaled = baseSize * scaleFactor

        // 最小サイズの制限
        if let min = minSize {
            scaled = Swift.max(scaled, min)
        }

        // 最大サイズの制限
        if let max = maxSize {
            scaled = Swift.min(scaled, max)
        }

        return scaled
    }

    // フォントサイズの取得（よく使うサイズをまとめました）
    static func fontSize(_ style: FontStyle) -> CGFloat {
        switch style {
        case .largeTitle:
            return scaledSize(52, min: 36, max: 72)    // 特大タイトル
        case .title:
            return scaledSize(36, min: 24, max: 48)    // タイトル
        case .headline:
            return scaledSize(20, min: 16, max: 28)    // 見出し
        case .body:
            return scaledSize(17, min: 14, max: 22)    // 本文
        case .caption:
            return scaledSize(12, min: 10, max: 14)    // キャプション
        }
    }

    // パディング（余白）の取得
    static func padding(_ style: PaddingStyle) -> CGFloat {
        switch style {
        case .large:
            return scaledSize(32, min: 20, max: 48)    // 大きな余白
        case .medium:
            return scaledSize(20, min: 12, max: 32)    // 中くらいの余白
        case .small:
            return scaledSize(12, min: 8, max: 20)     // 小さな余白
        }
    }
}

// フォントスタイルの種類
enum FontStyle {
    case largeTitle  // 特大タイトル（例：2062年）
    case title      // タイトル（例：10月20日）
    case headline   // 見出し（例：人生の進捗率）
    case body       // 本文（例：エピソードテキスト）
    case caption    // キャプション（例：残り〇〇日）
}

// パディングスタイルの種類
enum PaddingStyle {
    case large      // 大きな余白
    case medium     // 中くらいの余白
    case small      // 小さな余白
}
