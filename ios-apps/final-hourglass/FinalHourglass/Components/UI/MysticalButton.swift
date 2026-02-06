// periphery:ignore:all - UIコンポーネントライブラリ（再利用可能）
//
//  HourglassView.swift
//  LastHourglass
//
//  アニメーション付き砂時計コンポーネント
//  アプリのシンボルとして使用
//

import SwiftUI

struct HourglassView: View {
    // MARK: - Configuration
    var size: CGFloat = 90
    var showFrame: Bool = true
    var animateSand: Bool = true
    var glowEffect: Bool = true

    // MARK: - State
    @State private var sandLevel: CGFloat = 1.0
    @State private var isFloating: Bool = false
    @State private var rotation: Double = -2

    // MARK: - Computed Properties
    private var scale: CGFloat {
        size / 90.0 // 基準サイズ90に対する比率
    }

    // MARK: - Body
    var body: some View {
        ZStack {
            if showFrame {
                // 装飾的な枠
                MysticalFrame(size: size * 2.2)
            }

            // 砂時計本体
            hourglassShape
                .frame(width: size, height: size)
                .rotationEffect(.degrees(rotation))
                .offset(y: isFloating ? -5 * scale : 5 * scale)
                .scaleEffect(isFloating ? 1.02 : 0.98)
                .animation(
                    .easeInOut(duration: AnimationTiming.mysticalFloat)
                    .repeatForever(autoreverses: true),
                    value: isFloating
                )
        }
        .onAppear {
            if animateSand {
                startAnimations()
            }
        }
    }

    // MARK: - Hourglass Shape
    private var hourglassShape: some View {
        GeometryReader { geometry in
            let width = geometry.size.width
            let height = geometry.size.height

            ZStack {
                // 外枠の装飾
                HourglassDecoration(scale: scale)

                // 砂時計の輪郭
                HourglassOutline(scale: scale)
                    .stroke(
                        LinearGradient.mysticalGradient,
                        lineWidth: 2 * scale
                    )
                    .shadow(
                        color: glowEffect ? Shadow.mysticalGlow.color : Color.clear,
                        radius: glowEffect ? Shadow.mysticalGlow.radius : 0
                    )

                // 上部の砂
                UpperSand(sandLevel: sandLevel, scale: scale)

                // 流れる砂
                if animateSand {
                    FlowingSand(scale: scale)
                }

                // 下部の砂
                LowerSand(sandLevel: 1.0 - sandLevel, scale: scale)

                // 中央の装飾
                CenterOrnament(scale: scale)
            }
            .frame(width: width, height: height)
        }
    }

    // MARK: - Animations
    private func startAnimations() {
        // 浮遊アニメーション
        withAnimation {
            isFloating = true
        }

        // 回転アニメーション
        withAnimation(
            .easeInOut(duration: AnimationTiming.mysticalFloat * 0.5)
            .repeatForever(autoreverses: true)
        ) {
            rotation = 2
        }

        // 砂のアニメーション
        withAnimation(
            .linear(duration: AnimationTiming.ceremonial)
            .repeatForever(autoreverses: false)
        ) {
            sandLevel = 0
        }
    }
}

// MARK: - Subcomponents

// 装飾的な枠
struct MysticalFrame: View {
    let size: CGFloat
    @State private var ringRotation: Double = 0

    var body: some View {
        ZStack {
            // ステンドグラスパターン
            StainedGlassPattern(size: size)

            // 回転する光輪
            Circle()
                .stroke(
                    LinearGradient(
                        colors: [
                            Color.mysticalPurple.opacity(0.4),
                            Color.mysticBlue.opacity(0.4),
                            Color.mysticalPurple.opacity(0.4)
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    ),
                    lineWidth: 2
                )
                .frame(width: size, height: size)
                .rotationEffect(.degrees(ringRotation))
                .shadow(color: Shadow.mysticalGlow.color, radius: 20)

            // 光線
            LightRays(size: size)
                .rotationEffect(.degrees(-ringRotation * 0.8))
        }
        .onAppear {
            withAnimation(
                .linear(duration: AnimationTiming.eternal)
                .repeatForever(autoreverses: false)
            ) {
                ringRotation = 360
            }
        }
    }
}

// ステンドグラスパターン
struct StainedGlassPattern: View {
    let size: CGFloat

    var body: some View {
        // シンプルな実装例
        ZStack {
            ForEach(0..<8, id: \.self) { index in
                RoundedRectangle(cornerRadius: size * 0.1)
                    .fill(
                        LinearGradient(
                            colors: [
                                Color.deepPink.opacity(0.3),
                                Color.mysticBlue.opacity(0.3)
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(width: size * 0.3, height: size * 0.3)
                    .offset(
                        x: cos(Double(index) * .pi / 4) * size * 0.3,
                        y: sin(Double(index) * .pi / 4) * size * 0.3
                    )
                    .blur(radius: 1)
            }
        }
        .opacity(0.4)
    }
}

// 光線効果
struct LightRays: View {
    let size: CGFloat

    var body: some View {
        ZStack {
            ForEach(0..<4, id: \.self) { index in
                Rectangle()
                    .fill(
                        LinearGradient(
                            colors: [
                                Color.clear,
                                Color.mysticalPurple.opacity(0.4),
                                Color.mysticBlue.opacity(0.4),
                                Color.clear
                            ],
                            startPoint: .leading,
                            endPoint: .trailing
                        )
                    )
                    .frame(width: size * 1.1, height: 1)
                    .rotationEffect(.degrees(Double(index) * 45))
            }
        }
        .opacity(0.6)
    }
}

// 砂時計の輪郭
struct HourglassOutline: Shape {
    let scale: CGFloat

    func path(in rect: CGRect) -> Path {
        var path = Path()

        let width = rect.width
        let height = rect.height
        let midX = rect.midX
        let midY = rect.midY

        // 上部
        path.move(to: CGPoint(x: width * 0.3, y: height * 0.2))
        path.addQuadCurve(
            to: CGPoint(x: width * 0.7, y: height * 0.2),
            control: CGPoint(x: midX, y: height * 0.1)
        )
        path.addLine(to: CGPoint(x: width * 0.7, y: height * 0.35))
        path.addQuadCurve(
            to: CGPoint(x: midX, y: midY),
            control: CGPoint(x: width * 0.65, y: height * 0.43)
        )

        // 下部
        path.addQuadCurve(
            to: CGPoint(x: width * 0.7, y: height * 0.65),
            control: CGPoint(x: width * 0.65, y: height * 0.57)
        )
        path.addLine(to: CGPoint(x: width * 0.7, y: height * 0.8))
        path.addQuadCurve(
            to: CGPoint(x: width * 0.3, y: height * 0.8),
            control: CGPoint(x: midX, y: height * 0.9)
        )
        path.addLine(to: CGPoint(x: width * 0.3, y: height * 0.65))
        path.addQuadCurve(
            to: CGPoint(x: midX, y: midY),
            control: CGPoint(x: width * 0.35, y: height * 0.57)
        )

        // 上部に戻る
        path.addQuadCurve(
            to: CGPoint(x: width * 0.3, y: height * 0.35),
            control: CGPoint(x: width * 0.35, y: height * 0.43)
        )
        path.closeSubpath()

        return path
    }
}

// 上部の砂
struct UpperSand: View {
    let sandLevel: CGFloat
    let scale: CGFloat

    var body: some View {
        // 実装は簡略化
        Path { _ in
            // 砂の形状を描画
        }
        .fill(LinearGradient.sandFlowGradient)
        .opacity(0.8)
    }
}

// 流れる砂
struct FlowingSand: View {
    let scale: CGFloat
    @State private var sandY: CGFloat = 0

    var body: some View {
        Rectangle()
            .fill(LinearGradient.sandFlowGradient)
            .frame(width: 2 * scale, height: 6 * scale)
            .opacity(0.9)
            .offset(y: sandY)
            .onAppear {
                withAnimation(
                    .linear(duration: 3)
                    .repeatForever(autoreverses: false)
                ) {
                    sandY = 6 * scale
                }
            }
    }
}

// 下部の砂
struct LowerSand: View {
    let sandLevel: CGFloat
    let scale: CGFloat

    var body: some View {
        // 実装は簡略化
        Path { _ in
            // 砂の形状を描画
        }
        .fill(LinearGradient.sandFlowGradient)
        .opacity(0.8)
    }
}

// 中央の装飾
struct CenterOrnament: View {
    let scale: CGFloat

    var body: some View {
        ZStack {
            Circle()
                .stroke(
                    LinearGradient.mysticalGradient,
                    lineWidth: 1.5 * scale
                )
                .frame(width: 12 * scale, height: 12 * scale)
                .opacity(0.7)

            Circle()
                .fill(LinearGradient.mysticalGradient)
                .frame(width: 6 * scale, height: 6 * scale)
                .opacity(0.8)
        }
    }
}

// 砂時計の外枠装飾
struct HourglassDecoration: View {
    let scale: CGFloat

    var body: some View {
        // 実装は簡略化
        EmptyView()
    }
}

// MARK: - Preview
struct HourglassView_Previews: PreviewProvider {
    static var previews: some View {
        ZStack {
            LinearGradient.deepSpaceGradient
                .ignoresSafeArea()

            VStack(spacing: Spacing.lg) {
                // 大きいサイズ（フレーム付き）
                HourglassView(size: 120, showFrame: true)

                // 標準サイズ
                HourglassView()

                // 小さいサイズ（フレームなし）
                HourglassView(size: 60, showFrame: false)
            }
        }
        .preferredColorScheme(.dark)
    }
}
