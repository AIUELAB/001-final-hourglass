#!/usr/bin/env python3
"""
ultra_think_auto_calibrated_person_adder.py - Migrated to use UnifiedDataCollectionGateway
Migration Date: 2025-10-01 04:02:28
Original file backed up to: ultra_think_backups/ultra_think_auto_calibrated_person_adder.py.backup
"""

import sys
import os
from pathlib import Path

# UnifiedDataCollectionGatewayをインポート
sys.path.append(str(Path(__file__).parent))
from unified_data_collection_gateway import UnifiedDataCollectionGateway, ValidationLevel
from character_type_classifier import CharacterTypeClassifier

# 元のインポート（必要なもののみ保持）
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import hashlib
from ultra_think_japanese_recognition_calibrator import JapaneseRecognitionCalibrator

class MigratedAutoCalibratedPersonAdder:
    """バリデーション統合版のAutoCalibratedPersonAdder"""

    def __init__(self):
        # 統合ゲートウェイを初期化
        self.gateway = UnifiedDataCollectionGateway(
            validation_level=ValidationLevel.STANDARD
        )
        self.classifier = CharacterTypeClassifier()

        # 元の初期化コード（必要に応じて）
        # TODO: 元の初期化コードを移植

    def add_person(self, person_name: str, **kwargs):
        """
        人物追加メソッド（バリデーション統合版）

        すべての人物追加は必ずゲートウェイを通過します。
        """
        # キャラクタータイプを判定
        classification = self.classifier.classify(
            person_name,
            occupation=kwargs.get('occupation'),
            category=kwargs.get('category')
        )

        # エンティティタイプを設定
        if classification.character_type == 'fictional_character':
            kwargs['entity_type'] = 'fictional_character'
            kwargs['work_name'] = classification.work_name
        else:
            kwargs['entity_type'] = 'person'

        # ゲートウェイ経由で追加（バリデーション実行）
        success, person_data, report = self.gateway.add_person(
            person_name=person_name,
            **kwargs
        )

        if not success:
            print(f"❌ バリデーション失敗: {person_name}")
            print(f"   違反: {report.violations}")
            return None

        print(f"✅ 追加成功: {person_name} (スコア: {person_data.name_recognition:.1f})")
        return person_data

    def save_to_csv(self, output_path: str = None):
        """
        CSVファイルに保存（バリデーション済みデータのみ）
        """
        if output_path is None:
            output_path = "ultra_think_validated_{timestamp}.csv"

        # ゲートウェイから検証済みデータを取得
        self.gateway.export_to_csv(output_path)
        print(f"💾 検証済みデータを保存: {output_path}")

        # バリデーションレポートも出力
        report_path = output_path.replace('.csv', '_validation_report.json')
        self.gateway.export_validation_report(report_path)
        print(f"📊 バリデーションレポート: {report_path}")

# メイン処理
if __name__ == "__main__":
    migrated = MigratedAutoCalibratedPersonAdder()

    # 元のファイルの処理ロジックをここに移植
    # ただし、すべてのデータ追加はmigrated.add_person()を使用
    # TODO: 元のメイン処理を移植
