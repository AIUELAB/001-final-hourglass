// periphery:ignore:all - 将来使用予定のUIコンポーネント
//
//  MysticalSpaceBackground.swift
//  LastHourglass
//
//  神秘的な宇宙背景コンポーネント
//  設定画面やその他の画面で使用される幻想的な背景
//

import SwiftUI

struct MysticalSpaceBackground: View {
    // MARK: - State
    @State private var auroraOffset: CGFloat = 0
    @State private var shimmerOpacity: Double = 0.15

    var body: some View {
        ZStack {
            // ベースグラデーション（深宇宙）
            LinearGradient(
                stops: [
                    .init(color: Color.deepSpace, location: 0),
                    .init(color: Color.pitchBlack, location: 0.6),
                    .init(color: Color.pureBlack, location: 1.0)
                ],
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()

            // オーロラ効果
            AuroraVeil()
                .offset(x: auroraOffset)
                .onAppear {
                    withAnimation(
                        .easeInOut(duration: AnimationTiming.auroaDrift)
                        .repeatForever(autoreverses: true)
                    ) {
                        auroraOffset = 60
                    }
                }

            // 神秘的な粒子（ランダム化）
            ForEach(0..<12, id: \.self) { index in
                RandomMysticParticle(index: index)
            }

            // ステンドグラスのシマー効果
            StainedGlassShimmer()
                .opacity(shimmerOpacity)
                .onAppear {
                    withAnimation(
                        .easeInOut(duration: AnimationTiming.eternal)
                        .repeatForever(autoreverses: true)
                    ) {
                        shimmerOpacity = 0.25
                    }
                }
        }
    }
}

// MARK: - Subcomponents

// オーロラ効果
struct AuroraVeil: View {
    var body: some View {
        GeometryReader { geometry in
            LinearGradient(
                stops: [
                    .init(color: Color.clear, location: 0),
                    .init(color: Color.deepPink.opacity(0.15), location: 0.15),
                    .init(color: Color.mysticBlue.opacity(0.2), location: 0.3),
                    .init(color: Color.skyBlue.opacity(0.15), location: 0.45),
                    .init(color: Color.gold.opacity(0.1), location: 0.6),
                    .init(color: Color.errorRed.opacity(0.15), location: 0.75),
                    .init(color: Color.clear, location: 1.0)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .frame(width: geometry.size.width * 1.5, height: 400)
            .rotationEffect(.degrees(-3))
            .blur(radius: BlurEffect.extreme + 10)
            .blendMode(.screen)
            .opacity(0.6)
            .offset(x: -geometry.size.width * 0.25, y: -100)
        }
    }
}

// 神秘的な粒子
struct MysticParticle: View {
    let index: Int

    private var particleSize: CGFloat {
        CGFloat.random(in: 3...6)
    }

    private var horizontalPosition: CGFloat {
        let positions: [CGFloat] = [0.15, 0.35, 0.55, 0.75, 0.85]
        return UIScreen.main.bounds.width * positions[index % positions.count]
    }

    var body: some View {
        Circle()
            .fill(
                RadialGradient(
                    colors: [
                        Color.mysticalPurple.opacity(0.6),
                        Color.deepViolet.opacity(0.3),
                        Color.clear
                    ],
                    center: .center,
                    startRadius: 0,
                    endRadius: particleSize
                )
            )
            .frame(width: particleSize * 2, height: particleSize * 2)
            .shadow(
                color: Color.mysticalPurple.opacity(0.4),
                radius: 8,
                x: 0,
                y: 0
            )
            .position(x: horizontalPosition, y: UIScreen.main.bounds.height)
    }
}

// ステンドグラスのシマー効果
struct StainedGlassShimmer: View {
    var body: some View {
        GeometryReader { geometry in
            ZStack {
                // パターン1
                LinearGradient(
                    colors: [
                        Color.clear,
                        Color.deepPink.opacity(0.15),
                        Color.deepPink.opacity(0.15),
                        Color.mysticBlue.opacity(0.15),
                        Color.mysticBlue.opacity(0.15),
                        Color.clear
                    ],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                .frame(width: geometry.size.width, height: geometry.size.height)
                .scaleEffect(1.2)
                .rotationEffect(.degrees(45))

                // パターン2
                LinearGradient(
                    colors: [
                        Color.clear,
                        Color.gold.opacity(0.1),
                        Color.gold.opacity(0.1),
                        Color.errorRed.opacity(0.1),
                        Color.errorRed.opacity(0.1),
                        Color.clear
                    ],
                    startPoint: .topTrailing,
                    endPoint: .bottomLeading
                )
                .frame(width: geometry.size.width, height: geometry.size.height)
                .scaleEffect(1.2)
                .rotationEffect(.degrees(-45))

                // パターン3
                LinearGradient(
                    colors: [
                        Color.clear,
                        Color.limeGreen.opacity(0.08),
                        Color.limeGreen.opacity(0.08),
                        Color.clear
                    ],
                    startPoint: .leading,
                    endPoint: .trailing
                )
                .frame(width: geometry.size.width, height: geometry.size.height)
            }
        }
    }
}
// ランダムな神秘的粒子
struct RandomMysticParticle: View {
    let index: Int
    @State private var yOffset: CGFloat = 0
    @State private var opacity: Double = 0

    // ランダムなプロパティ
    private let startDelay = Double.random(in: 0...15)
    private let duration = Double.random(in: 10...25)
    private let particleSize = CGFloat.random(in: 2...6)
    private let horizontalPosition = CGFloat.random(in: 0.1...0.9)

    var body: some View {
        Circle()
            .fill(
                RadialGradient(
                    colors: [
                        Color.mysticalPurple.opacity(0.6),
                        Color.deepViolet.opacity(0.3),
                        Color.clear
                    ],
                    center: .center,
                    startRadius: 0,
                    endRadius: particleSize
                )
            )
            .frame(width: particleSize * 2, height: particleSize * 2)
            .shadow(
                color: Color.mysticalPurple.opacity(0.4),
                radius: 8,
                x: 0,
                y: 0
            )
            .position(
                x: UIScreen.main.bounds.width * horizontalPosition,
                y: UIScreen.main.bounds.height + yOffset
            )
            .opacity(opacity)
            .onAppear {
                // 初期遅延後にアニメーション開始
                DispatchQueue.main.asyncAfter(deadline: .now() + startDelay) {
                    withAnimation(.easeIn(duration: 1)) {
                        opacity = Double.random(in: 0.4...0.8)
                    }

                    withAnimation(
                        .linear(duration: duration)
                        .repeatForever(autoreverses: false)
                    ) {
                        yOffset = -UIScreen.main.bounds.height * 2 - 100
                    }
                }
            }
    }
}
// MARK: - Light Mode Support
struct MysticalSpaceBackgroundLight: View {
    var body: some View {
        LinearGradient(
            colors: [
                Color.AppColors.ashWhite,
                Color.AppColors.ashWhite.opacity(0.95),
                Color.lavender.opacity(0.3)
            ],
            startPoint: .top,
            endPoint: .bottom
        )
        .ignoresSafeArea()
    }
}

// MARK: - Adaptive Background
struct AdaptiveMysticalBackground: View {
    @Environment(\.colorScheme) var colorScheme

    var body: some View {
        if colorScheme == .dark {
            MysticalSpaceBackground()
        } else {
            MysticalSpaceBackgroundLight()
        }
    }
}
