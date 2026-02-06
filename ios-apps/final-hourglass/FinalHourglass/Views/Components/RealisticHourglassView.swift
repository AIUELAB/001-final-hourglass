// periphery:ignore:all - 将来使用予定のUIコンポーネント
import SwiftUI

/// リアルな砂時計ビュー
struct RealisticHourglassView: View {
    let progress: Double  // 0.0 (開始) から 1.0 (終了)
    let size: CGSize
    let isAnimating: Bool

    // カスタマイズ可能な色
    var sandColor: Color = Color(red: 1.0, green: 0.84, blue: 0.47)  // ゴールド
    var glassColor: Color = Color.blue.opacity(0.1)
    var frameColor: Color = Color(red: 0.7, green: 0.6, blue: 0.4)  // ブロンズ

    @State private var sandFallAnimation = false
    @State private var glowAnimation = false
    @State private var rotationAnimation: Double = 0

    // 砂の配分計算
    private var topSandLevel: Double {
        max(0, 1.0 - progress)
    }

    private var bottomSandLevel: Double {
        min(1.0, progress)
    }

    private var isSandFlowing: Bool {
        progress > 0.01 && progress < 0.99
    }

    var body: some View {
        ZStack {
            // グロー効果（背景）
            if isAnimating {
                Circle()
                    .fill(
                        RadialGradient(
                            gradient: Gradient(colors: [
                                Color.mysticalPurple.opacity(0.3),
                                Color.clear
                            ]),
                            center: .center,
                            startRadius: size.width * 0.3,
                            endRadius: size.width * 0.8
                        )
                    )
                    .frame(width: size.width * 2, height: size.width * 2)
                    .scaleEffect(glowAnimation ? 1.2 : 1.0)
                    .opacity(glowAnimation ? 0.6 : 0.3)
                    .animation(
                        Animation.easeInOut(duration: 2.0)
                            .repeatForever(autoreverses: true),
                        value: glowAnimation
                    )
            }

            // メイン砂時計
            GeometryReader { geometry in
                ZStack {
                    // ガラスフレーム（背面）
                    HourglassShape(neckRatio: 0.12, curveIntensity: 0.25)
                        .stroke(
                            LinearGradient(
                                gradient: Gradient(colors: [
                                    frameColor.opacity(0.8),
                                    frameColor.opacity(0.4),
                                    frameColor.opacity(0.8)
                                ]),
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            ),
                            lineWidth: 3
                        )
                        .shadow(color: .black.opacity(0.3), radius: 5, x: 2, y: 2)

                    // ガラス本体
                    HourglassShape(neckRatio: 0.12, curveIntensity: 0.25)
                        .fill(glassColor)
                        .overlay(
                            // ガラスの反射
                            LinearGradient(
                                gradient: Gradient(stops: [
                                    .init(color: .white.opacity(0.3), location: 0.0),
                                    .init(color: .clear, location: 0.3),
                                    .init(color: .clear, location: 0.7),
                                    .init(color: .white.opacity(0.1), location: 1.0)
                                ]),
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                            .mask(HourglassShape(neckRatio: 0.12, curveIntensity: 0.25))
                        )

                    // 上部の砂
                    TopSandShape(progress: progress)
                        .fill(
                            LinearGradient(
                                gradient: Gradient(colors: [
                                    sandColor,
                                    sandColor.opacity(0.9),
                                    sandColor.opacity(0.8)
                                ]),
                                startPoint: .top,
                                endPoint: .bottom
                            )
                        )
                        .mask(
                            HourglassShape(neckRatio: 0.14, curveIntensity: 0.25)
                                .padding(3)
                        )

                    // 下部の砂
                    BottomSandShape(progress: progress)
                        .fill(
                            LinearGradient(
                                gradient: Gradient(colors: [
                                    sandColor.opacity(0.8),
                                    sandColor.opacity(0.9),
                                    sandColor
                                ]),
                                startPoint: .top,
                                endPoint: .bottom
                            )
                        )
                        .mask(
                            HourglassShape(neckRatio: 0.14, curveIntensity: 0.25)
                                .padding(3)
                        )

                    // 流れ落ちる砂のストリーム
                    if isSandFlowing && isAnimating {
                        FallingSandStream(
                            isAnimating: true,
                            sandColor: sandColor,
                            streamWidth: size.width * 0.02
                        )
                        .frame(width: size.width * 0.1, height: size.height * 0.3)
                        .position(
                            x: geometry.size.width / 2,
                            y: geometry.size.height / 2
                        )
                    }

                    // 砂のパーティクル効果
                    if isSandFlowing && isAnimating {
                        SandParticleSystem(
                            isActive: true,
                            emissionRate: 8,
                            sandColor: sandColor,
                            size: geometry.size
                        )
                        .allowsHitTesting(false)
                    }

                    // ハイライト効果（前面）
                    HourglassShape(neckRatio: 0.12, curveIntensity: 0.25)
                        .stroke(
                            LinearGradient(
                                gradient: Gradient(stops: [
                                    .init(color: .white.opacity(0.4), location: 0.0),
                                    .init(color: .clear, location: 0.2),
                                    .init(color: .clear, location: 0.8),
                                    .init(color: .white.opacity(0.2), location: 1.0)
                                ]),
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            ),
                            lineWidth: 1
                        )

                    // 装飾的な金属フレーム（上部）
                    RoundedRectangle(cornerRadius: 8)
                        .fill(
                            LinearGradient(
                                gradient: Gradient(colors: [
                                    frameColor,
                                    frameColor.opacity(0.7),
                                    frameColor
                                ]),
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .frame(width: geometry.size.width * 1.2, height: 12)
                        .position(x: geometry.size.width / 2, y: 6)
                        .shadow(color: .black.opacity(0.3), radius: 2, y: 1)

                    // 装飾的な金属フレーム（下部）
                    RoundedRectangle(cornerRadius: 8)
                        .fill(
                            LinearGradient(
                                gradient: Gradient(colors: [
                                    frameColor,
                                    frameColor.opacity(0.7),
                                    frameColor
                                ]),
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .frame(width: geometry.size.width * 1.2, height: 12)
                        .position(x: geometry.size.width / 2, y: geometry.size.height - 6)
                        .shadow(color: .black.opacity(0.3), radius: 2, y: -1)
                }
            }
            .frame(width: size.width, height: size.height)
            .rotationEffect(.degrees(rotationAnimation))
        }
        .onAppear {
            if isAnimating {
                glowAnimation = true

                // 砂が流れ終わったら回転アニメーション
                if progress >= 0.98 {
                    withAnimation(
                        Animation.easeInOut(duration: 1.5)
                            .delay(0.5)
                    ) {
                        rotationAnimation = 180
                    }
                }
            }
        }
    }
}
