#!/usr/bin/env python3
"""
デスクトップの写真を美化加工
"""

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import os
from pathlib import Path
from datetime import datetime

def enhance_portrait(input_path):
    """ポートレート写真を美化加工（5バージョン作成）"""

    print(f"📷 処理開始: {input_path}")

    # 出力ディレクトリ作成
    output_dir = "/Users/admin/Desktop/enhanced_photos"
    os.makedirs(output_dir, exist_ok=True)

    base_name = Path(input_path).stem
    timestamp = datetime.now().strftime("%H%M%S")

    # 画像読み込み
    img_pil = Image.open(input_path)
    print(f"  画像サイズ: {img_pil.size}")

    results = []

    # === バージョン1: ナチュラル美化 ===
    print("  1. ナチュラル美化バージョン作成中...")
    img_v1 = img_pil.copy()

    # 明るさ補正（自然な明るさ）
    enhancer = ImageEnhance.Brightness(img_v1)
    img_v1 = enhancer.enhance(1.2)

    # コントラスト（軽め）
    enhancer = ImageEnhance.Contrast(img_v1)
    img_v1 = enhancer.enhance(1.15)

    # 色彩（自然な彩度）
    enhancer = ImageEnhance.Color(img_v1)
    img_v1 = enhancer.enhance(1.1)

    # 軽いシャープネス
    enhancer = ImageEnhance.Sharpness(img_v1)
    img_v1 = enhancer.enhance(1.2)

    output_v1 = os.path.join(output_dir, f"{base_name}_natural_{timestamp}.jpg")
    img_v1.save(output_v1, quality=95)
    results.append(("ナチュラル美化", output_v1))

    # === バージョン2: プロフェッショナル（美肌加工） ===
    print("  2. プロフェッショナルバージョン作成中...")
    img_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

    # 強力な美肌処理
    img_smooth = cv2.bilateralFilter(img_cv, 20, 100, 100)

    # さらに滑らかに
    img_smooth = cv2.bilateralFilter(img_smooth, 15, 80, 80)

    # オリジナルと美肌処理をブレンド（美肌効果を強め）
    img_blend = cv2.addWeighted(img_cv, 0.2, img_smooth, 0.8, 0)

    # 暖色系に調整（健康的な肌色）
    b, g, r = cv2.split(img_blend)
    r = np.clip(r * 1.1, 0, 255).astype(np.uint8)
    b = np.clip(b * 0.92, 0, 255).astype(np.uint8)
    img_warm = cv2.merge([b, g, r])

    # 軽いビネット効果
    rows, cols = img_warm.shape[:2]
    kernel_x = cv2.getGaussianKernel(cols, cols/2.5)
    kernel_y = cv2.getGaussianKernel(rows, rows/2.5)
    kernel = kernel_y * kernel_x.T
    mask = kernel / kernel.max()
    mask = np.stack([mask] * 3, axis=2)
    img_vignette = (img_warm * (0.5 + 0.5 * mask)).astype(np.uint8)

    # PILに戻して最終調整
    img_v2_pil = Image.fromarray(cv2.cvtColor(img_vignette, cv2.COLOR_BGR2RGB))

    # 明るさを少し上げる
    enhancer = ImageEnhance.Brightness(img_v2_pil)
    img_v2_pil = enhancer.enhance(1.15)

    output_v2 = os.path.join(output_dir, f"{base_name}_professional_{timestamp}.jpg")
    img_v2_pil.save(output_v2, quality=95)
    results.append(("プロフェッショナル", output_v2))

    # === バージョン3: SNS映え（明るく鮮やか） ===
    print("  3. SNS映えバージョン作成中...")
    img_v3 = img_pil.copy()

    # 明るく
    enhancer = ImageEnhance.Brightness(img_v3)
    img_v3 = enhancer.enhance(1.35)

    # 高コントラスト
    enhancer = ImageEnhance.Contrast(img_v3)
    img_v3 = enhancer.enhance(1.35)

    # 鮮やかに
    enhancer = ImageEnhance.Color(img_v3)
    img_v3 = enhancer.enhance(1.4)

    # くっきりシャープ
    img_v3 = img_v3.filter(ImageFilter.UnsharpMask(radius=2, percent=200, threshold=3))

    output_v3 = os.path.join(output_dir, f"{base_name}_sns_{timestamp}.jpg")
    img_v3.save(output_v3, quality=95)
    results.append(("SNS映え", output_v3))

    # === バージョン4: ソフトフォーカス（優しい印象） ===
    print("  4. ソフトフォーカスバージョン作成中...")
    img_v4 = img_pil.copy()

    # 軽くぼかす
    img_blur = img_v4.filter(ImageFilter.GaussianBlur(radius=1))

    # オリジナルとブレンド
    img_v4 = Image.blend(img_v4, img_blur, 0.3)

    # 明るく柔らかく
    enhancer = ImageEnhance.Brightness(img_v4)
    img_v4 = enhancer.enhance(1.25)

    # 優しい色合い
    enhancer = ImageEnhance.Color(img_v4)
    img_v4 = enhancer.enhance(1.05)

    output_v4 = os.path.join(output_dir, f"{base_name}_soft_{timestamp}.jpg")
    img_v4.save(output_v4, quality=95)
    results.append(("ソフトフォーカス", output_v4))

    # === バージョン5: モノクロアート ===
    print("  5. モノクロアートバージョン作成中...")
    img_v5 = img_pil.copy()

    # グレースケール変換
    img_v5 = img_v5.convert('L')

    # 高コントラスト
    img_v5 = ImageOps.autocontrast(img_v5, cutoff=1)

    # シャープ
    img_v5 = img_v5.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))

    output_v5 = os.path.join(output_dir, f"{base_name}_monochrome_{timestamp}.jpg")
    img_v5.save(output_v5, quality=95)
    results.append(("モノクロアート", output_v5))

    return results

def main():
    print("=" * 60)
    print("📸 デスクトップ写真美化加工ツール")
    print("=" * 60)

    # 処理対象画像
    image_path = "/Users/admin/Desktop/IMG_6700 2.jpg"

    if os.path.exists(image_path):
        try:
            results = enhance_portrait(image_path)

            print("\n✅ 処理完了！")
            print("-" * 60)
            print("作成されたファイル:")
            for style, path in results:
                size_kb = os.path.getsize(path) / 1024
                print(f"  📄 {style:20s}: {os.path.basename(path)}")
                print(f"      サイズ: {size_kb:.1f}KB")

            print("\n💡 各バージョンの特徴:")
            print("  1. ナチュラル美化: 自然な仕上がり、日常使い")
            print("  2. プロフェッショナル: 美肌効果強め、ビジネス向け")
            print("  3. SNS映え: 明るく鮮やか、Instagram向け")
            print("  4. ソフトフォーカス: 優しい印象、柔らかい雰囲気")
            print("  5. モノクロアート: アーティスティック、高級感")

            print(f"\n📁 保存先: /Users/admin/Desktop/enhanced_photos/")

        except Exception as e:
            print(f"❌ エラー: {e}")
    else:
        print(f"❌ 画像が見つかりません: {image_path}")

if __name__ == "__main__":
    main()