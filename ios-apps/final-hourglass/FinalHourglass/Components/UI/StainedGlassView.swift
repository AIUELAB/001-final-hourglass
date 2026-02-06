// periphery:ignore:all - 将来使用予定のUIコンポーネント
//
//  StainedGlassView.swift
//  LastHourglass
//
//  ステンドグラス効果を生成するビューコンポーネント
//  背景や装飾として使用可能
//

import SwiftUI

struct StainedGlassView: View {
    // MARK: - Configuration
    var segments: Int = 8
    var animationDuration: Double = AnimationTiming.eternal
    var opacity: Double = 0.4

    // MARK: - State
    @State private var rotation: Double = 0
    @State private var shimmer: Double = 0.15

    // MARK: - Body
    var body: some View {
        ZStack {
            // 背景パターン
            StainedGlassBackground()
                .opacity(shimmer)

            // カテドラルの光
            CathedralLight()

            // ガラスセグメント
            ForEach(0..<segments, id: \.self) { index in
                GlassSegment(
                    index: index,
                    totalSegments: segments
                )
            }
            .opacity(opacity)

            // 回転する光輪
            LightRing()
                .rotationEffect(.degrees(rotation))
        }
        .onAppear {
            // アニメーション開始
            withAnimation(
                .linear(duration: animationDuration)
                .repeatForever(autoreverses: false)
            ) {
                rotation = 360
            }

            withAnimation(
                .easeInOut(duration: animationDuration)
                .repeatForever(autoreverses: true)
            ) {
                shimmer = 0.25
            }
        }
    }
}

// MARK: - Subcomponents

// ステンドグラス背景パターン
struct StainedGlassBackground: View {
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
                .rotationEffect(.degrees(-45))

                // パターン3
                LinearGradient(
                    colors: [
                        Color.clear,
                        Color.limeGreen.opacity(0.08),
                        Color.limeGreen.opacity(0.08),
                        Color.clear
                    ],
                    startPoint: .top,
                    endPoint: .bottom
                )
            }
            .frame(width: geometry.size.width, height: geometry.size.height)
        }
    }
}

// カテドラルの光効果
struct CathedralLight: View {
    var body: some View {
        GeometryReader { geometry in
            LinearGradient(
                stops: [
                    .init(color: Color.gold.opacity(0.2), location: 0),
                    .init(color: Color.deepPink.opacity(0.25), location: 0.1),
                    .init(color: Color.deepViolet.opacity(0.2), location: 0.2),
                    .init(color: Color.deepViolet.opacity(0.2), location: 0.3),
                    .init(color: Color.mysticBlue.opacity(0.25), location: 0.4),
                    .init(color: Color.skyBlue.opacity(0.2), location: 0.5),
                    .init(color: Color.skyBlue.opacity(0.15), location: 0.6),
                    .init(color: Color.limeGreen.opacity(0.15), location: 0.7),
                    .init(color: Color.amber.opacity(0.15), location: 0.8),
                    .init(color: Color.errorRed.opacity(0.1), location: 0.9),
                    .init(color: Color.clear, location: 1.0)
                ],
                startPoint: .top,
                endPoint: .bottom
            )
            .frame(width: geometry.size.width * 0.8)
            .position(x: geometry.size.width / 2, y: geometry.size.height * 0.3)
            .blur(radius: BlurEffect.extreme)
            .blendMode(.screen)
            .opacity(0.8)
        }
    }
}

// 個別のガラスセグメント
struct GlassSegment: View {
    let index: Int
    let totalSegments: Int

    private var segmentColor: Color {
        let colors: [Color] = [
            .deepPink, .skyBlue, .gold, .errorRed,
            .limeGreen, .amber, .deepViolet, .mysticBlue
        ]
        return colors[index % colors.count]
    }

    private var position: (x: CGFloat, y: CGFloat) {
        let angle = Double(index) / Double(totalSegments) * 2 * .pi
        let radius: CGFloat = 80
        return (
            x: CGFloat(cos(angle)) * radius,
            y: CGFloat(sin(angle)) * radius
        )
    }

    var body: some View {
        GeometryReader { geometry in
            Group {
                if index < 4 {
                    // 大きなセグメント
                    TriangleShape()
                        .fill(
                            RadialGradient(
                                colors: [
                                    segmentColor.opacity(0.4),
                                    segmentColor.opacity(0.3),
                                    segmentColor.opacity(0.4)
                                ],
                                center: .center,
                                startRadius: 0,
                                endRadius: 100
                            )
                        )
                        .frame(width: 60, height: 70)
                        .overlay(
                            TriangleShape()
                                .stroke(Color.black.opacity(0.6), lineWidth: 2)
                        )
                        .shadow(
                            color: segmentColor.opacity(0.4),
                            radius: 30,
                            x: 0,
                            y: 0
                        )
                } else {
                    // 小さなセグメント
                    Circle()
                        .fill(
                            RadialGradient(
                                colors: [
                                    segmentColor.opacity(0.4),
                                    segmentColor.opacity(0.3)
                                ],
                                center: .center,
                                startRadius: 0,
                                endRadius: 20
                            )
                        )
                        .frame(width: 30, height: 30)
                        .overlay(
                            Circle()
                                .stroke(Color.black.opacity(0.6), lineWidth: 2)
                        )
                        .shadow(
                            color: segmentColor.opacity(0.4),
                            radius: 15,
                            x: 0,
                            y: 0
                        )
                }
            }
            .position(
                x: geometry.size.width / 2 + position.x,
                y: geometry.size.height / 2 + position.y
            )
        }
    }
}

// 回転する光輪
struct LightRing: View {
    var body: some View {
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
            .shadow(
                color: Color.mysticalPurple.opacity(0.3),
                radius: 20,
                x: 0,
                y: 0
            )
            .blur(radius: 1)
    }
}

// 三角形シェイプ
struct TriangleShape: Shape {
    func path(in rect: CGRect) -> Path {
        var path = Path()
        path.move(to: CGPoint(x: rect.midX, y: rect.minY))
        path.addLine(to: CGPoint(x: rect.maxX, y: rect.maxY))
        path.addLine(to: CGPoint(x: rect.minX, y: rect.maxY))
        path.closeSubpath()
        return path
    }
}
