#!/usr/bin/env python3
"""
アップロードされた画像を自動的に美化加工
"""

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import os
from pathlib import Path
from datetime import datetime

def enhance_portrait(input_path, output_base=None):
    """ポートレート写真を美化加工（複数バージョン作成）"""

    if output_base is None:
        output_base = Path(input_path).stem

    # 画像読み込み
    img_pil = Image.open(input_path)

    # オリジナルのサイズを保持
    original_size = img_pil.size

    results = []

    # === バージョン1: ナチュラル美化 ===
    img_v1 = img_pil.copy()

    # 明るさ補正
    enhancer = ImageEnhance.Brightness(img_v1)
    img_v1 = enhancer.enhance(1.25)

    # コントラスト
    enhancer = ImageEnhance.Contrast(img_v1)
    img_v1 = enhancer.enhance(1.2)

    # 色彩強調
    enhancer = ImageEnhance.Color(img_v1)
    img_v1 = enhancer.enhance(1.15)

    # シャープネス
    enhancer = ImageEnhance.Sharpness(img_v1)
    img_v1 = enhancer.enhance(1.3)

    output_v1 = f"{output_base}_natural.jpg"
    img_v1.save(output_v1, quality=95)
    results.append(("ナチュラル美化", output_v1))

    # === バージョン2: プロフェッショナル仕上げ ===
    img_v2 = img_pil.copy()

    # OpenCVで高度な処理
    img_cv = cv2.cvtColor(np.array(img_v2), cv2.COLOR_RGB2BGR)

    # 美肌処理
    img_smooth = cv2.bilateralFilter(img_cv, 15, 80, 80)
    img_smooth = cv2.bilateralFilter(img_smooth, 15, 80, 80)

    # オリジナルとブレンド
    img_blend = cv2.addWeighted(img_cv, 0.3, img_smooth, 0.7, 0)

    # 暖色系に調整
    b, g, r = cv2.split(img_blend)
    r = np.clip(r * 1.08, 0, 255).astype(np.uint8)
    b = np.clip(b * 0.95, 0, 255).astype(np.uint8)
    img_warm = cv2.merge([b, g, r])

    # ビネット効果
    rows, cols = img_warm.shape[:2]
    kernel_x = cv2.getGaussianKernel(cols, cols/3)
    kernel_y = cv2.getGaussianKernel(rows, rows/3)
    kernel = kernel_y * kernel_x.T
    mask = kernel / kernel.max()
    mask = np.stack([mask] * 3, axis=2)
    img_vignette = (img_warm * (0.6 + 0.4 * mask)).astype(np.uint8)

    # PILに戻して保存
    img_v2_final = Image.fromarray(cv2.cvtColor(img_vignette, cv2.COLOR_BGR2RGB))

    # 明度と彩度の最終調整
    enhancer = ImageEnhance.Brightness(img_v2_final)
    img_v2_final = enhancer.enhance(1.1)
    enhancer = ImageEnhance.Color(img_v2_final)
    img_v2_final = enhancer.enhance(1.2)

    output_v2 = f"{output_base}_professional.jpg"
    img_v2_final.save(output_v2, quality=95)
    results.append(("プロフェッショナル", output_v2))

    # === バージョン3: ハイコントラスト（SNS映え） ===
    img_v3 = img_pil.copy()

    # 強めのコントラスト
    enhancer = ImageEnhance.Contrast(img_v3)
    img_v3 = enhancer.enhance(1.4)

    # 明るさ
    enhancer = ImageEnhance.Brightness(img_v3)
    img_v3 = enhancer.enhance(1.3)

    # 彩度を高め
    enhancer = ImageEnhance.Color(img_v3)
    img_v3 = enhancer.enhance(1.35)

    # エッジ強調
    img_v3 = img_v3.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))

    output_v3 = f"{output_base}_high_contrast.jpg"
    img_v3.save(output_v3, quality=95)
    results.append(("ハイコントラスト", output_v3))

    # === バージョン4: アート風 ===
    img_v4 = np.array(img_pil)
    img_v4 = cv2.cvtColor(img_v4, cv2.COLOR_RGB2BGR)

    # 油絵風エフェクト
    img_oil = cv2.edgePreservingFilter(img_v4, flags=2, sigma_s=50, sigma_r=0.4)

    # 色調整
    img_oil_pil = Image.fromarray(cv2.cvtColor(img_oil, cv2.COLOR_BGR2RGB))
    enhancer = ImageEnhance.Color(img_oil_pil)
    img_oil_pil = enhancer.enhance(1.3)

    output_v4 = f"{output_base}_artistic.jpg"
    img_oil_pil.save(output_v4, quality=95)
    results.append(("アート風", output_v4))

    # === バージョン5: モノクロ高級感 ===
    img_v5 = img_pil.copy()

    # グレースケール変換
    img_v5 = img_v5.convert('L')

    # コントラスト強調
    img_v5 = ImageOps.autocontrast(img_v5, cutoff=2)

    # シャープネス
    img_v5 = img_v5.filter(ImageFilter.UnsharpMask(radius=1, percent=100, threshold=3))

    output_v5 = f"{output_base}_monochrome.jpg"
    img_v5.save(output_v5, quality=95)
    results.append(("モノクロ高級", output_v5))

    return results

def main():
    print("=" * 60)
    print("📸 画像美化加工ツール - 複数バージョン作成")
    print("=" * 60)

    # アップロードされた画像を処理
    # 実際の画像パスはReadツールで取得する必要があります
    # ここではサンプルパスを使用

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 処理対象画像（仮のパス）
    images_to_process = [
        "photo1.jpg",  # 1枚目の写真
        "photo2.jpg",  # 2枚目の写真（親指を立てている写真）
    ]

    all_results = []

    for i, img_path in enumerate(images_to_process, 1):
        if os.path.exists(img_path):
            print(f"\n📷 画像{i}を処理中...")
            output_base = f"enhanced_photo{i}_{timestamp}"

            try:
                results = enhance_portrait(img_path, output_base)
                all_results.extend(results)

                print(f"✅ 画像{i}の処理完了！")
                for style, path in results:
                    print(f"  - {style}: {path}")

            except Exception as e:
                print(f"❌ エラー: {e}")
        else:
            print(f"⚠️ 画像{i}が見つかりません: {img_path}")

    if all_results:
        print("\n" + "=" * 60)
        print("✅ すべての処理が完了しました！")
        print("=" * 60)
        print("\n作成されたファイル:")
        for style, path in all_results:
            size_kb = os.path.getsize(path) / 1024 if os.path.exists(path) else 0
            print(f"  📄 {style:15s}: {path} ({size_kb:.1f}KB)")

        print("\n💡 ヒント:")
        print("  - 'natural': 自然な美化、日常使い向け")
        print("  - 'professional': ビジネス・LinkedIn向け")
        print("  - 'high_contrast': Instagram・SNS向け")
        print("  - 'artistic': クリエイティブな用途向け")
        print("  - 'monochrome': プロフェッショナルな印象")

if __name__ == "__main__":
    main()
