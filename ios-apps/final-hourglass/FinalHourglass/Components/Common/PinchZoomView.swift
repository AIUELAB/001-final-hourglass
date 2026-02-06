// periphery:ignore:all - 将来使用予定のUIコンポーネント
import SwiftUI

/// ピンチズーム機能を提供するビューラッパー
struct PinchZoomView<Content: View>: View {
    @State private var currentZoom = 1.0
    @State private var totalZoom = 1.0
    @State private var offset: CGSize = .zero
    @State private var lastOffset: CGSize = .zero
    @GestureState private var magnifyBy = 1.0

    let content: Content
    let minScale: CGFloat
    let maxScale: CGFloat

    init(
        minScale: CGFloat = 0.5,
        maxScale: CGFloat = 3.0,
        @ViewBuilder content: () -> Content
    ) {
        self.minScale = minScale
        self.maxScale = maxScale
        self.content = content()
    }

    var body: some View {
        GeometryReader { geometry in
            content
                .scaleEffect(totalZoom * magnifyBy)
                .offset(offset)
                .gesture(
                    SimultaneousGesture(
                        MagnificationGesture()
                            .updating($magnifyBy) { currentState, gestureState, _ in
                                gestureState = currentState
                            }
                            .onEnded { value in
                                totalZoom = min(max(totalZoom * value, minScale), maxScale)

                                // ズームが1.0に近い場合は自動的にリセット
                                if abs(totalZoom - 1.0) < 0.1 {
                                    withAnimation(.spring()) {
                                        resetZoom()
                                    }
                                }

                                // オフセットの境界チェック
                                limitOffset(in: geometry.size)
                            },
                        DragGesture()
                            .onChanged { value in
                                if totalZoom > 1.0 {
                                    offset = CGSize(
                                        width: lastOffset.width + value.translation.width,
                                        height: lastOffset.height + value.translation.height
                                    )
                                }
                            }
                            .onEnded { _ in
                                lastOffset = offset
                                limitOffset(in: geometry.size)
                            }
                    )
                )
                .onTapGesture(count: 2) {
                    withAnimation(.spring()) {
                        if totalZoom > 1.0 {
                            resetZoom()
                        } else {
                            totalZoom = 2.0
                        }
                    }
                }
                .frame(width: geometry.size.width, height: geometry.size.height)
                .clipped()
        }
    }

    private func resetZoom() {
        totalZoom = 1.0
        currentZoom = 1.0
        offset = .zero
        lastOffset = .zero
    }

    // オフセットを境界内に制限
    private func limitOffset(in size: CGSize) {
        let scaledWidth = size.width * totalZoom
        let scaledHeight = size.height * totalZoom

        let maxX = max(0, (scaledWidth - size.width) / 2)
        let maxY = max(0, (scaledHeight - size.height) / 2)

        withAnimation(.spring(response: 0.3, dampingFraction: 0.8)) {
            offset.width = min(max(offset.width, -maxX), maxX)
            offset.height = min(max(offset.height, -maxY), maxY)
            lastOffset = offset
        }
    }
}

// MARK: - Convenience Modifier
extension View {
    /// ビューにピンチズーム機能を追加
    func pinchZoomable(minScale: CGFloat = 0.5, maxScale: CGFloat = 3.0) -> some View {
        PinchZoomView(minScale: minScale, maxScale: maxScale) {
            self
        }
    }
}
