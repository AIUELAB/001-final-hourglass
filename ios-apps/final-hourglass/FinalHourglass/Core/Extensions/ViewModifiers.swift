// periphery:ignore:all - 将来使用予定のUIコンポーネント
import SwiftUI

// MARK: - Active Modifiers (使用中)

// 幻想的な発光効果を追加するモディファイア
struct MysticalGlowModifier: ViewModifier {
    let color: Color
    let radius: CGFloat
    let intensity: Double

    init(color: Color = .mysticalPurple, radius: CGFloat = 8, intensity: Double = 1.0) {
        self.color = color
        self.radius = radius
        self.intensity = intensity
    }

    func body(content: Content) -> some View {
        content
            .shadow(color: color.opacity(0.3 * intensity), radius: radius)
            .shadow(color: color.opacity(0.2 * intensity), radius: radius * 1.5)
    }
}

// MARK: - Reusable Modifiers (再利用可能・将来使用予定)

// ステンドグラスのような光の反射効果
// periphery:ignore - 再利用可能なUI Modifier
struct StainedGlassReflection: ViewModifier {
    let colors: [Color]

    func body(content: Content) -> some View {
        content
            .overlay(
                LinearGradient(
                    colors: colors.map { $0.opacity(0.1) },
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                .blendMode(.screen)
            )
    }
}

// 砂時計の砂が落ちる効果
// periphery:ignore - 再利用可能なUI Modifier
struct SandFlowEffect: ViewModifier {
    @State private var offset: CGFloat = 0
    let duration: Double

    func body(content: Content) -> some View {
        content
            .mask(
                Rectangle()
                    .fill(
                        LinearGradient(
                            colors: [.clear, .white, .white, .clear],
                            startPoint: .top,
                            endPoint: .bottom
                        )
                    )
                    .offset(y: offset)
                    .animation(
                        Animation.linear(duration: duration)
                            .repeatForever(autoreverses: false),
                        value: offset
                    )
            )
            .onAppear {
                offset = 200
            }
    }
}

// MARK: - View Extensions

extension View {
    // 既存のmysticalGlowの代わりに、より具体的な名前を使用
    func mysticalEffect(color: Color = .mysticalPurple, radius: CGFloat = 8, intensity: Double = 1.0) -> some View {
        self.modifier(MysticalGlowModifier(color: color, radius: radius, intensity: intensity))
    }

    // periphery:ignore - ステンドグラス効果（再利用可能）
    func stainedGlassReflection(colors: [Color] = [.deepPink, .mysticBlue, .gold]) -> some View {
        self.modifier(StainedGlassReflection(colors: colors))
    }

    // periphery:ignore - 砂の流れ効果（再利用可能）
    func sandFlowEffect(duration: Double = 3.0) -> some View {
        self.modifier(SandFlowEffect(duration: duration))
    }
}

// 脈動するアニメーション効果
// periphery:ignore - 再利用可能なUI Modifier
struct PulsingEffect: ViewModifier {
    @State private var scale: CGFloat = 1.0
    let minScale: CGFloat
    let maxScale: CGFloat
    let duration: Double

    func body(content: Content) -> some View {
        content
            .scaleEffect(scale)
            .animation(
                Animation.easeInOut(duration: duration)
                    .repeatForever(autoreverses: true),
                value: scale
            )
            .onAppear {
                scale = maxScale
            }
    }
}

extension View {
    // periphery:ignore - 脈動効果（再利用可能）
    func pulsing(minScale: CGFloat = 0.95, maxScale: CGFloat = 1.05, duration: Double = 2.0) -> some View {
        self.modifier(PulsingEffect(minScale: minScale, maxScale: maxScale, duration: duration))
    }
}

// MARK: - Glossy Effects (光沢効果)

// アイコンの光沢効果を修正
// periphery:ignore - 再利用可能なUI Modifier
struct GlossyIconEffect: ViewModifier {
    func body(content: Content) -> some View {
        content
            .overlay(
                GeometryReader { geometry in
                    // 45度回転した光沢
                    LinearGradient(
                        stops: [
                            Gradient.Stop(color: Color.clear, location: 0.3),
                            Gradient.Stop(color: Color.white.opacity(0.3), location: 0.5),
                            Gradient.Stop(color: Color.clear, location: 0.7)
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                    .frame(width: geometry.size.width * 2, height: geometry.size.height * 2)
                    .rotationEffect(.degrees(45))
                    .offset(x: -geometry.size.width, y: -geometry.size.height)
                    .modifier(ContinuousSlideAnimation())
                }
                .mask(
                    RoundedRectangle(cornerRadius: 6)
                        .frame(width: 28, height: 28)
                )
            )
    }
}

// 連続的なスライドアニメーション
// periphery:ignore - GlossyIconEffect内部で使用
struct ContinuousSlideAnimation: ViewModifier {
    @State private var offset = CGSize(width: 0, height: 0)

    func body(content: Content) -> some View {
        content
            .offset(offset)
            .onAppear {
                withAnimation(
                    Animation.linear(duration: 3)
                        .repeatForever(autoreverses: false)
                ) {
                    offset = CGSize(width: 56, height: 56) // 28 * 2
                }
            }
    }
}
extension View {
    // periphery:ignore - 光沢アイコン効果（再利用可能）
    func glossyIcon() -> some View {
        self.modifier(GlossyIconEffect())
    }
}
