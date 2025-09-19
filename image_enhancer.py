#!/usr/bin/env python3
"""
写真を自動的にイケメン加工するスクリプト
"""

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import os
from pathlib import Path

def enhance_face_image(input_path, output_path=None):
    """顔写真を美化加工"""

    # 出力パスの設定
    if output_path is None:
        base = Path(input_path).stem
        ext = Path(input_path).suffix
        output_path = f"{base}_enhanced{ext}"

    # 画像読み込み（PIL）
    img_pil = Image.open(input_path)

    # 1. 明るさ調整（少し明るく）
    enhancer = ImageEnhance.Brightness(img_pil)
    img_pil = enhancer.enhance(1.2)  # 20%明るく

    # 2. コントラスト調整（少しメリハリを）
    enhancer = ImageEnhance.Contrast(img_pil)
    img_pil = enhancer.enhance(1.15)  # 15%コントラスト増

    # 3. 色の鮮やかさ調整
    enhancer = ImageEnhance.Color(img_pil)
    img_pil = enhancer.enhance(1.1)  # 10%鮮やかに

    # 4. シャープネス（輪郭を少しシャープに）
    enhancer = ImageEnhance.Sharpness(img_pil)
    img_pil = enhancer.enhance(1.2)

    # OpenCVに変換して高度な処理
    img_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

    # 5. 美肌処理（bilateral filterで肌を滑らかに）
    img_smooth = cv2.bilateralFilter(img_cv, 9, 75, 75)

    # 6. 元画像と美肌処理をブレンド（自然な仕上がりに）
    img_blend = cv2.addWeighted(img_cv, 0.3, img_smooth, 0.7, 0)

    # 7. 温かみのある色調に（少し暖色系に）
    # BGRなので、Bを少し下げ、Rを少し上げる
    b, g, r = cv2.split(img_blend)
    b = np.clip(b * 0.95, 0, 255).astype(np.uint8)
    r = np.clip(r * 1.05, 0, 255).astype(np.uint8)
    img_warm = cv2.merge([b, g, r])

    # 8. ビネット効果（周辺を少し暗く）
    rows, cols = img_warm.shape[:2]

    # ビネットマスク作成
    X_resultant_kernel = cv2.getGaussianKernel(cols, cols/4)
    Y_resultant_kernel = cv2.getGaussianKernel(rows, rows/4)
    kernel = Y_resultant_kernel * X_resultant_kernel.T
    mask = kernel / kernel.max()

    # マスクを3チャンネルに拡張
    mask = np.stack([mask] * 3, axis=2)

    # ビネット適用（弱めに）
    img_vignette = (img_warm * (0.7 + 0.3 * mask)).astype(np.uint8)

    # 保存
    cv2.imwrite(output_path, img_vignette)

    print(f"✅ 画像を加工しました: {output_path}")

    # 処理前後のサイズ情報
    original_size = os.path.getsize(input_path) / 1024  # KB
    new_size = os.path.getsize(output_path) / 1024  # KB

    print(f"📊 ファイルサイズ: {original_size:.1f}KB → {new_size:.1f}KB")

    return output_path

def create_stylized_version(input_path, style="anime"):
    """スタイル変換版を作成"""

    base = Path(input_path).stem
    ext = Path(input_path).suffix

    # 画像読み込み
    img = cv2.imread(input_path)

    if style == "anime":
        # アニメ風
        # エッジを保持しながら滑らかに
        img_smooth = cv2.bilateralFilter(img, 15, 80, 80)
        img_smooth = cv2.bilateralFilter(img_smooth, 15, 80, 80)  # 2回適用

        # エッジ検出
        gray = cv2.cvtColor(img_smooth, cv2.COLOR_BGR2GRAY)
        edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                      cv2.THRESH_BINARY, 9, 10)

        # エッジを反転して線画に
        edges = cv2.cvtColor(255 - edges, cv2.COLOR_GRAY2BGR)

        # 線画と滑らか画像を合成
        edges = edges / 255.0
        img_smooth = img_smooth / 255.0
        img_anime = img_smooth * edges
        img_anime = (img_anime * 255).astype(np.uint8)

        # 色を鮮やかに
        img_anime_pil = Image.fromarray(cv2.cvtColor(img_anime, cv2.COLOR_BGR2RGB))
        enhancer = ImageEnhance.Color(img_anime_pil)
        img_anime_pil = enhancer.enhance(1.5)

        output_path = f"{base}_anime{ext}"
        img_anime_pil.save(output_path)

    elif style == "sketch":
        # スケッチ風
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        inv_gray = 255 - gray
        blur = cv2.GaussianBlur(inv_gray, (21, 21), 0)
        inv_blur = 255 - blur
        sketch = cv2.divide(gray, inv_blur, scale=256.0)

        output_path = f"{base}_sketch{ext}"
        cv2.imwrite(output_path, sketch)

    elif style == "oil":
        # 油絵風
        img_oil = cv2.stylization(img, sigma_s=60, sigma_r=0.4)
        output_path = f"{base}_oil{ext}"
        cv2.imwrite(output_path, img_oil)

    print(f"✅ {style}スタイル版を作成: {output_path}")
    return output_path

def batch_process_images(folder_path):
    """フォルダ内の全画像を処理"""

    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
    processed = 0

    for file_path in Path(folder_path).glob('*'):
        if file_path.suffix.lower() in image_extensions:
            print(f"\n処理中: {file_path.name}")
            try:
                # 基本的な美化処理
                enhance_face_image(str(file_path))

                # スタイル版も作成（オプション）
                # create_stylized_version(str(file_path), "anime")

                processed += 1
            except Exception as e:
                print(f"❌ エラー: {e}")

    print(f"\n✅ {processed}枚の画像を処理しました")

def main():
    print("=" * 60)
    print("📸 画像美化加工ツール")
    print("=" * 60)

    # テスト用：単一画像の処理
    # ここに画像パスを指定してください
    image_paths = [
        # 画像ファイルのパスをここに追加
        # 例: "/Users/admin/Desktop/photo1.jpg"
    ]

    if not image_paths:
        print("⚠️ 処理する画像のパスを指定してください")
        print("スクリプトのimage_pathsリストに画像パスを追加してください")
        return

    for img_path in image_paths:
        if os.path.exists(img_path):
            print(f"\n処理開始: {img_path}")

            # 基本的な美化処理
            enhanced = enhance_face_image(img_path)

            # アニメ風バージョンも作成
            # create_stylized_version(img_path, "anime")

            # スケッチ風バージョン
            # create_stylized_version(img_path, "sketch")

        else:
            print(f"❌ ファイルが見つかりません: {img_path}")

    print("\n✅ 処理完了！")

if __name__ == "__main__":
    main()