import SwiftUI

/// 個別の砂粒子
struct SandParticle: Identifiable {
    let id = UUID()
    var position: CGPoint
    var velocity: CGVector
    var size: CGFloat
    var opacity: Double
    var lifespan: Double
    var age: Double = 0
    var rotationAngle: Double = 0

    init(startPosition: CGPoint, size: CGFloat = 1.5) {
        self.position = startPosition
        self.velocity = CGVector(
            dx: Double.random(in: -0.5...0.5),
            dy: Double.random(in: 2...4)
        )
        self.size = size * CGFloat.random(in: 0.8...1.2)
        self.opacity = 1.0
        self.lifespan = Double.random(in: 1.5...2.5)
        self.rotationAngle = Double.random(in: 0...360)
    }

    mutating func update(deltaTime: Double, in bounds: CGRect, neckWidth: CGFloat) {
        // 重力と速度の更新
        velocity.dy += 9.8 * deltaTime * 10  // 重力加速度

        // 位置の更新
        position.x += velocity.dx * deltaTime * 10
        position.y += velocity.dy * deltaTime * 10

        // 回転
        rotationAngle += deltaTime * 180

        // 年齢とフェードアウト
        age += deltaTime
        if age > lifespan - 0.5 {
            opacity = max(0, (lifespan - age) * 2)
        }

        // 横方向の制限（ネック部分での収束）
        let centerX = bounds.midX

        if abs(position.x - centerX) > neckWidth / 2 {
            position.x = centerX + (position.x > centerX ? neckWidth/2 : -neckWidth/2)
            velocity.dx *= -0.3  // 反発
        }
    }

    var isDead: Bool {
        age >= lifespan
    }
}

/// 砂のパーティクルシステム
struct SandParticleSystem: View {
    @State private var particles: [SandParticle] = []
    @State private var lastUpdateTime = Date()

    let isActive: Bool
    let emissionRate: Int
    let sandColor: Color
    let size: CGSize
    let neckWidth: CGFloat

    private let timer = Timer.publish(every: 1/60, on: .main, in: .common).autoconnect()

    init(
        isActive: Bool = true,
        emissionRate: Int = 5,
        sandColor: Color = Color(red: 0.9, green: 0.7, blue: 0.4),
        size: CGSize = CGSize(width: 200, height: 300),
        neckWidth: CGFloat = 16
    ) {
        self.isActive = isActive
        self.emissionRate = emissionRate
        self.sandColor = sandColor
        self.size = size
        self.neckWidth = neckWidth
    }

    var body: some View {
        Canvas { context, _ in
            for particle in particles {
                let particleRect = CGRect(
                    x: particle.position.x - particle.size/2,
                    y: particle.position.y - particle.size/2,
                    width: particle.size,
                    height: particle.size
                )

                context.opacity = particle.opacity

                // 砂粒子を描画（小さな円または多角形）
                context.fill(
                    Path(ellipseIn: particleRect),
                    with: .color(sandColor)
                )

                // ハイライト効果
                let highlightRect = CGRect(
                    x: particleRect.minX + particle.size * 0.2,
                    y: particleRect.minY + particle.size * 0.2,
                    width: particle.size * 0.3,
                    height: particle.size * 0.3
                )

                context.opacity = particle.opacity * 0.5
                context.fill(
                    Path(ellipseIn: highlightRect),
                    with: .color(.white.opacity(0.6))
                )
            }
        }
        .frame(width: size.width, height: size.height)
        .onReceive(timer) { _ in
            updateParticles()
        }
    }

    private func updateParticles() {
        let currentTime = Date()
        let deltaTime = currentTime.timeIntervalSince(lastUpdateTime)
        lastUpdateTime = currentTime

        // 【RCA-20260123】負のdeltaTimeはスキップ（システム時刻変更対策）
        guard deltaTime > 0 else { return }

        // 既存パーティクルの更新
        particles = particles.compactMap { particle in
            var updatedParticle = particle
            updatedParticle.update(
                deltaTime: deltaTime,
                in: CGRect(origin: .zero, size: size),
                neckWidth: neckWidth
            )

            // 死んだパーティクルを削除
            return updatedParticle.isDead ? nil : updatedParticle
        }

        // 新しいパーティクルの生成
        if isActive && particles.count < 100 {  // 最大100個に制限
            // 【RCA-20260123】max(0,...)で負値からの保護
            let particlesToEmit = max(0, Int(Double(emissionRate) * deltaTime)) + (Double.random(in: 0...1) < 0.3 ? 1 : 0)

            for _ in 0..<particlesToEmit {
                // ネック中心から放出（中央の堆積山から崩れる見た目に寄せる）
                let startX = size.width/2 + CGFloat.random(in: -neckWidth/4...neckWidth/4)
                let startY = size.height/2 + 2

                particles.append(
                    SandParticle(
                        startPosition: CGPoint(x: startX, y: startY),
                        size: 2.0
                    )
                )
            }
        }
    }
}

/// 流れ落ちる砂のアニメーション
struct FallingSandStream: View {
    let isAnimating: Bool
    let sandColor: Color
    let streamWidth: CGFloat

    @State private var animationPhase: Double = 0

    var body: some View {
        GeometryReader { geometry in
            ZStack {
                // メインストリーム
                Rectangle()
                    .fill(
                        LinearGradient(
                            gradient: Gradient(stops: [
                                .init(color: sandColor.opacity(0.3), location: 0.0),
                                .init(color: sandColor.opacity(0.8), location: 0.3),
                                .init(color: sandColor.opacity(0.8), location: 0.7),
                                .init(color: sandColor.opacity(0.3), location: 1.0)
                            ]),
                            startPoint: .top,
                            endPoint: .bottom
                        )
                    )
                    .frame(width: streamWidth)
                    .mask(
                        LinearGradient(
                            gradient: Gradient(stops: [
                                .init(color: .clear, location: 0.0),
                                .init(color: .black, location: 0.1 + sin(animationPhase) * 0.05),
                                .init(color: .black, location: 0.9 - sin(animationPhase) * 0.05),
                                .init(color: .clear, location: 1.0)
                            ]),
                            startPoint: .top,
                            endPoint: .bottom
                        )
                    )

                // 流れのテクスチャ
                ForEach(0..<3) { index in
                    Rectangle()
                        .fill(sandColor.opacity(0.2))
                        .frame(width: streamWidth * 0.6)
                        .offset(y: geometry.size.height * (animationPhase + Double(index) / 3.0))
                        .mask(
                            LinearGradient(
                                gradient: Gradient(colors: [
                                    .clear,
                                    .black,
                                    .clear
                                ]),
                                startPoint: .top,
                                endPoint: .bottom
                            )
                        )
                }
            }
            .frame(width: streamWidth)
            .position(x: geometry.size.width / 2, y: geometry.size.height / 2)
        }
        .onAppear {
            if isAnimating {
                withAnimation(
                    Animation.linear(duration: 1.5)
                        .repeatForever(autoreverses: false)
                ) {
                    animationPhase = 1.0
                }
            }
        }
    }
}
