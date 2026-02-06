// periphery:ignore:all - 将来使用予定
import SwiftUI

/// 砂時計の形状を定義するカスタムShape
struct HourglassShape: Shape {
    var neckRatio: CGFloat = 0.15  // ネック部分の太さの比率
    var curveIntensity: CGFloat = 0.3  // カーブの強さ

    func path(in rect: CGRect) -> Path {
        var path = Path()

        let width = rect.width
        let height = rect.height
        let centerX = rect.midX
        let centerY = rect.midY

        // ネック部分の幅
        let neckWidth = width * neckRatio

        // コントロールポイントの計算
        let topCurveControl = CGPoint(x: centerX, y: height * 0.15)
        let bottomCurveControl = CGPoint(x: centerX, y: height * 0.85)

        // 左側の輪郭
        path.move(to: CGPoint(x: rect.minX, y: rect.minY))

        // 上部のカーブ（左側）
        path.addQuadCurve(
            to: CGPoint(x: centerX - neckWidth/2, y: centerY),
            control: CGPoint(x: rect.minX + width * curveIntensity, y: topCurveControl.y)
        )

        // 下部のカーブ（左側）
        path.addQuadCurve(
            to: CGPoint(x: rect.minX, y: rect.maxY),
            control: CGPoint(x: rect.minX + width * curveIntensity, y: bottomCurveControl.y)
        )

        // 底部のライン
        path.addLine(to: CGPoint(x: rect.maxX, y: rect.maxY))

        // 下部のカーブ（右側）
        path.addQuadCurve(
            to: CGPoint(x: centerX + neckWidth/2, y: centerY),
            control: CGPoint(x: rect.maxX - width * curveIntensity, y: bottomCurveControl.y)
        )

        // 上部のカーブ（右側）
        path.addQuadCurve(
            to: CGPoint(x: rect.maxX, y: rect.minY),
            control: CGPoint(x: rect.maxX - width * curveIntensity, y: topCurveControl.y)
        )

        // 頂部のラインで閉じる
        path.closeSubpath()

        return path
    }
}

/// 砂時計の枠（ガラス部分）を描画する
struct HourglassFrame: Shape {
    var thickness: CGFloat = 4
    var neckRatio: CGFloat = 0.15

    func path(in rect: CGRect) -> Path {
        let outerRect = rect
        let innerRect = rect.insetBy(dx: thickness, dy: thickness)

        var path = Path()

        // 外側の砂時計
        path.addPath(HourglassShape(neckRatio: neckRatio).path(in: outerRect))

        // 内側の砂時計を引く（中空にする）
        path.addPath(HourglassShape(neckRatio: neckRatio + 0.02).path(in: innerRect))

        return path
    }
}

/// 砂の形状（上部）
struct TopSandShape: Shape {
    var progress: Double  // 0.0 (満杯) から 1.0 (空)

    func path(in rect: CGRect) -> Path {
        var path = Path()

        if progress >= 1.0 {
            return path  // 完全に空
        }

        let sandHeight = rect.height * 0.5 * (1.0 - progress)
        let centerX = rect.midX
        let neckWidth = rect.width * 0.15

        // 砂の上面（少し曲線を持たせる）
        let sandTop = rect.minY + (rect.height * 0.5 - sandHeight)

        path.move(to: CGPoint(x: rect.minX, y: sandTop))

        // 上面の曲線
        path.addQuadCurve(
            to: CGPoint(x: rect.maxX, y: sandTop),
            control: CGPoint(x: centerX, y: sandTop + 5)
        )

        // 右側の壁に沿って下へ
        if sandHeight > rect.height * 0.35 {
            // ネックより上の場合
            path.addLine(to: CGPoint(x: rect.maxX, y: rect.minY))
            path.addLine(to: CGPoint(x: rect.minX, y: rect.minY))
        } else {
            // ネックに到達している場合
            let neckY = rect.midY
            let slope = (rect.width - neckWidth) / (rect.height * 0.5)
            let xOffset = slope * (neckY - sandTop)

            path.addLine(to: CGPoint(x: rect.maxX - xOffset, y: neckY))
            path.addLine(to: CGPoint(x: rect.minX + xOffset, y: neckY))
        }

        path.closeSubpath()

        return path
    }
}

/// 砂の形状（下部）
struct BottomSandShape: Shape {
    var progress: Double  // 0.0 (空) から 1.0 (満杯)

    func path(in rect: CGRect) -> Path {
        var path = Path()

        if progress <= 0.0 {
            return path  // 完全に空
        }

        let sandHeight = rect.height * 0.5 * progress
        let centerX = rect.midX
        let centerY = rect.midY

        // 砂の底から積み上げる
        let sandTop = rect.maxY - sandHeight

        path.move(to: CGPoint(x: rect.minX, y: rect.maxY))
        path.addLine(to: CGPoint(x: rect.maxX, y: rect.maxY))

        if sandHeight < rect.height * 0.35 {
            // ネックより下の場合
            path.addLine(to: CGPoint(x: rect.maxX, y: sandTop))

            // 上面の曲線（中央に山：ネック直下が最初に溜まる）
            path.addQuadCurve(
                to: CGPoint(x: rect.minX, y: sandTop),
                control: CGPoint(x: centerX, y: sandTop - 10)
            )
        } else {
            // ネックを超えている場合
            let neckWidth = rect.width * 0.15
            let slope = (rect.width - neckWidth) / (rect.height * 0.5)
            let xOffset = slope * (sandTop - centerY)

            path.addLine(to: CGPoint(x: rect.maxX - xOffset, y: sandTop))
            path.addQuadCurve(
                to: CGPoint(x: rect.minX + xOffset, y: sandTop),
                control: CGPoint(x: centerX, y: sandTop - 12)
            )
        }

        path.closeSubpath()

        return path
    }
}
