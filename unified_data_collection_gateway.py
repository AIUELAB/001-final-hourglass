#!/usr/bin/env python3
"""
統一データ収集ゲートウェイ
すべての人物データ追加を一元管理し、バリデーションを強制適用する

このゲートウェイを通らずにデータを追加することは禁止
"""

import json
import csv
import os
import sys
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum
import pandas as pd

# プロジェクトパスを追加
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent / 'episode_quality_system'))

# 既存バリデーションシステムのインポート
from pdca_guardian import PDCAGuardian, ViolationType
from episode_quality_system.optimized_validation_system import OptimizedValidationSystem
from episode_quality_system.unified_validation_system import UnifiedValidationSystem
from episode_quality_system.mandatory_pipeline import MandatoryPipeline

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)


class EntityType(Enum):
    """エンティティタイプ"""
    REAL_PERSON = "real_person"
    FICTIONAL_CHARACTER = "fictional_character"
    GROUP = "group"
    UNKNOWN = "unknown"


class ValidationLevel(Enum):
    """バリデーションレベル"""
    STRICT = "strict"      # 厳格（すべてのルール適用）
    STANDARD = "standard"  # 標準（重要なルールのみ）
    LENIENT = "lenient"    # 寛容（最小限のチェック）


@dataclass
class PersonData:
    """人物データ構造"""
    person_name: str
    person_name_ja: Optional[str] = None
    person_name_display: Optional[str] = None
    entity_type: EntityType = EntityType.UNKNOWN
    category: str = 'その他'
    nationality: str = '不明'
    occupation: str = ''
    birth_year: Optional[int] = None
    name_recognition: float = 0.0
    work_name: Optional[str] = None  # 架空キャラクターの作品名
    wikipedia_url: Optional[str] = None
    validated: bool = False
    validation_score: float = 0.0
    validation_issues: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationReport:
    """バリデーションレポート"""
    passed: bool
    score: float
    critical_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: List[str] = field(default_factory=list)
    pdca_violations: List[Dict] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class UnifiedDataCollectionGateway:
    """統一データ収集ゲートウェイ"""

    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        """
        初期化

        Args:
            validation_level: バリデーションレベル
        """
        self.validation_level = validation_level

        # バリデーションシステムの初期化
        self.pdca_guardian = PDCAGuardian()
        self.optimized_validator = OptimizedValidationSystem()
        self.unified_validator = UnifiedValidationSystem()
        self.mandatory_pipeline = MandatoryPipeline()

        # データベースパス
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)

        self.master_db_path = self.data_dir / "master_persons_database.json"
        self.validation_log_path = self.data_dir / "validation_log.json"

        # マスターデータベースの読み込み
        self.master_database = self._load_master_database()

        # バリデーションログ
        self.validation_log = []

        # 統計情報
        self.stats = {
            "total_added": 0,
            "total_rejected": 0,
            "validation_bypassed": 0,
            "fictional_characters": 0,
            "real_persons": 0
        }

        logger.info(f"統一データ収集ゲートウェイ初期化完了 (レベル: {validation_level.value})")

    def _load_master_database(self) -> Dict[str, PersonData]:
        """マスターデータベースの読み込み"""
        if self.master_db_path.exists():
            try:
                with open(self.master_db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {k: PersonData(**v) for k, v in data.items()}
            except Exception as e:
                logger.error(f"データベース読み込みエラー: {e}")
                return {}
        return {}

    def _save_master_database(self):
        """マスターデータベースの保存"""
        try:
            data = {k: asdict(v) for k, v in self.master_database.items()}
            with open(self.master_db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"データベース保存完了: {len(self.master_database)}件")
        except Exception as e:
            logger.error(f"データベース保存エラー: {e}")

    def _detect_entity_type(self, person_data: PersonData) -> EntityType:
        """エンティティタイプの自動判定"""

        # occupation から判定
        occupation = person_data.occupation.lower() if person_data.occupation else ""

        # 架空キャラクターのキーワード
        fictional_keywords = [
            '架空', 'キャラクター', 'アニメ', 'マンガ', '漫画',
            'ゲーム', '小説', 'ドラマ', '映画', '作品'
        ]

        # グループのキーワード
        group_keywords = [
            'グループ', 'バンド', 'チーム', 'ユニット', 'コンビ',
            'トリオ', '団体', '組', 'band', 'group', 'team'
        ]

        # 架空キャラクター判定
        for keyword in fictional_keywords:
            if keyword in occupation:
                return EntityType.FICTIONAL_CHARACTER

        # 作品名があれば架空キャラクターの可能性大
        if person_data.work_name:
            return EntityType.FICTIONAL_CHARACTER

        # グループ判定
        for keyword in group_keywords:
            if keyword in occupation or keyword in (person_data.category or ''):
                return EntityType.GROUP

        # デフォルトは実在人物
        return EntityType.REAL_PERSON

    def _validate_person(self, person_data: PersonData) -> ValidationReport:
        """人物データのバリデーション"""

        report = ValidationReport(passed=True, score=100.0)

        # 1. 必須フィールドチェック
        if not person_data.person_name:
            report.critical_issues.append("人物名が未設定")
            report.passed = False
            report.score -= 30

        # 2. エンティティタイプ別バリデーション
        if person_data.entity_type == EntityType.FICTIONAL_CHARACTER:
            # 架空キャラクターは作品名必須
            if not person_data.work_name:
                report.warnings.append("架空キャラクターに作品名が未設定")
                report.score -= 10

        elif person_data.entity_type == EntityType.REAL_PERSON:
            # 実在人物は生年チェック
            if person_data.birth_year:
                current_year = datetime.now().year
                if person_data.birth_year > current_year:
                    report.critical_issues.append(f"生年が未来: {person_data.birth_year}")
                    report.passed = False
                elif person_data.birth_year < 1800:
                    report.warnings.append(f"生年が古すぎる可能性: {person_data.birth_year}")

        # 3. PDCAガーディアンチェック（STRICTモードのみ）
        if self.validation_level == ValidationLevel.STRICT:
            # データを辞書形式に変換
            data_dict = asdict(person_data)
            violations = self.pdca_guardian.check_violations(data_dict, context="person_add")

            for violation in violations:
                if violation.get("priority") == "CRITICAL":
                    report.critical_issues.append(f"PDCA違反: {violation['message']}")
                    report.passed = False
                    report.score -= 20
                elif violation.get("priority") == "HIGH":
                    report.warnings.append(f"PDCA警告: {violation['message']}")
                    report.score -= 5

                report.pdca_violations.append(violation)

        # 4. 知名度スコアチェック
        if person_data.name_recognition < 0 or person_data.name_recognition > 10:
            report.warnings.append(f"知名度スコア範囲外: {person_data.name_recognition}")
            person_data.name_recognition = max(0, min(10, person_data.name_recognition))

        # 5. 重複チェック
        key = self._create_person_key(person_data)
        if key in self.master_database:
            report.critical_issues.append(f"重複: {key} は既に存在")
            report.passed = False
            report.score = 0

        return report

    def _create_person_key(self, person_data: PersonData) -> str:
        """人物のユニークキー生成"""
        # 表示名 > 日本語名 > 英語名の優先順位
        name = person_data.person_name_display or person_data.person_name_ja or person_data.person_name
        # 特殊文字を正規化
        name = name.strip().replace(' ', '_').replace('　', '_')
        return name

    def add_person(self,
                  person_name: str,
                  **kwargs) -> Tuple[bool, Optional[PersonData], ValidationReport]:
        """
        人物データの追加（バリデーション強制適用）

        Args:
            person_name: 人物名
            **kwargs: その他のフィールド

        Returns:
            (成功フラグ, 追加されたデータ, バリデーションレポート)
        """
        # PersonDataオブジェクト作成
        person_data = PersonData(
            person_name=person_name,
            person_name_ja=kwargs.get('person_name_ja'),
            person_name_display=kwargs.get('person_name_display'),
            category=kwargs.get('category', 'その他'),
            nationality=kwargs.get('nationality', '不明'),
            occupation=kwargs.get('occupation', ''),
            birth_year=kwargs.get('birth_year'),
            name_recognition=kwargs.get('name_recognition', 0.0),
            work_name=kwargs.get('work_name'),
            wikipedia_url=kwargs.get('wikipedia_url'),
            metadata=kwargs.get('metadata', {})
        )

        # エンティティタイプの自動判定
        if kwargs.get('entity_type'):
            person_data.entity_type = EntityType(kwargs['entity_type'])
        else:
            person_data.entity_type = self._detect_entity_type(person_data)

        # バリデーション実行
        report = self._validate_person(person_data)
        person_data.validated = report.passed
        person_data.validation_score = report.score
        person_data.validation_issues = report.critical_issues + report.warnings

        # ログ記録
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "person_name": person_name,
            "entity_type": person_data.entity_type.value,
            "validation_passed": report.passed,
            "validation_score": report.score,
            "issues": person_data.validation_issues
        }
        self.validation_log.append(log_entry)

        # バリデーション結果に基づく処理
        if report.passed or self.validation_level == ValidationLevel.LENIENT:
            # データベースに追加
            key = self._create_person_key(person_data)
            self.master_database[key] = person_data
            self._save_master_database()

            # 統計更新
            self.stats["total_added"] += 1
            if person_data.entity_type == EntityType.FICTIONAL_CHARACTER:
                self.stats["fictional_characters"] += 1
            elif person_data.entity_type == EntityType.REAL_PERSON:
                self.stats["real_persons"] += 1

            logger.info(f"✅ 追加成功: {key} (タイプ: {person_data.entity_type.value}, スコア: {report.score:.1f})")
            return True, person_data, report

        else:
            # 追加拒否
            self.stats["total_rejected"] += 1
            logger.warning(f"❌ 追加拒否: {person_name} - {report.critical_issues}")
            return False, None, report

    def add_persons_batch(self, persons_list: List[Dict]) -> Dict[str, Any]:
        """
        複数人物の一括追加

        Args:
            persons_list: 人物データのリスト

        Returns:
            処理結果のサマリー
        """
        results = {
            "successful": [],
            "failed": [],
            "total": len(persons_list)
        }

        for person_dict in persons_list:
            success, data, report = self.add_person(**person_dict)

            if success:
                results["successful"].append({
                    "name": person_dict.get('person_name'),
                    "data": asdict(data) if data else None
                })
            else:
                results["failed"].append({
                    "name": person_dict.get('person_name'),
                    "reasons": report.critical_issues
                })

        # サマリー表示
        logger.info(f"""
        ========== バッチ処理完了 ==========
        総数: {results['total']}
        成功: {len(results['successful'])}
        失敗: {len(results['failed'])}
        ====================================
        """)

        return results

    def export_to_csv(self, output_path: str = None) -> str:
        """
        データベースをCSVエクスポート

        Args:
            output_path: 出力先パス

        Returns:
            出力ファイルパス
        """
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"unified_persons_database_{timestamp}.csv"

        # DataFrameに変換
        data_list = []
        for key, person_data in self.master_database.items():
            data_dict = asdict(person_data)
            data_dict['key'] = key
            data_list.append(data_dict)

        df = pd.DataFrame(data_list)

        # UTF-8 BOM付きで保存（Excel対応）
        df.to_csv(output_path, index=False, encoding='utf-8-sig')

        logger.info(f"CSVエクスポート完了: {output_path} ({len(df)}件)")
        return output_path

    def get_statistics(self) -> Dict[str, Any]:
        """統計情報の取得"""
        return {
            **self.stats,
            "database_size": len(self.master_database),
            "validation_level": self.validation_level.value,
            "entity_type_distribution": self._get_entity_type_distribution()
        }

    def _get_entity_type_distribution(self) -> Dict[str, int]:
        """エンティティタイプ別の分布"""
        distribution = {}
        for person_data in self.master_database.values():
            entity_type = person_data.entity_type.value
            distribution[entity_type] = distribution.get(entity_type, 0) + 1
        return distribution

    def enforce_validation_on_existing_files(self) -> Dict[str, Any]:
        """
        既存のCSVファイルにバリデーションを適用
        ultra_think系のファイルをチェックして統合
        """
        results = {
            "files_processed": [],
            "total_records": 0,
            "validated_records": 0,
            "rejected_records": 0
        }

        # ultra_think系のCSVファイルを検索
        for csv_file in Path(".").glob("ultra_think*.csv"):
            logger.info(f"処理中: {csv_file}")

            try:
                df = pd.read_csv(csv_file, encoding='utf-8-sig')

                for _, row in df.iterrows():
                    person_dict = row.to_dict()

                    # データ形式を正規化
                    normalized_data = {
                        "person_name": person_dict.get('person_name', ''),
                        "person_name_ja": person_dict.get('person_name_ja'),
                        "person_name_display": person_dict.get('person_name_display'),
                        "category": person_dict.get('category', 'その他'),
                        "nationality": person_dict.get('nationality', '不明'),
                        "occupation": person_dict.get('occupation', ''),
                        "birth_year": person_dict.get('birth_year'),
                        "name_recognition": person_dict.get('name_recognition', 0.0)
                    }

                    # バリデーション適用
                    success, _, _ = self.add_person(**normalized_data)

                    results["total_records"] += 1
                    if success:
                        results["validated_records"] += 1
                    else:
                        results["rejected_records"] += 1

                results["files_processed"].append(str(csv_file))

            except Exception as e:
                logger.error(f"ファイル処理エラー: {csv_file} - {e}")

        logger.info(f"""
        ========== 既存ファイル検証完了 ==========
        処理ファイル数: {len(results['files_processed'])}
        総レコード数: {results['total_records']}
        検証成功: {results['validated_records']}
        検証失敗: {results['rejected_records']}
        ==========================================
        """)

        return results


# CLIインターフェース
def main():
    """メインエントリーポイント"""
    import argparse

    parser = argparse.ArgumentParser(description="統一データ収集ゲートウェイ")
    parser.add_argument("action", choices=["add", "batch", "export", "stats", "validate-existing"],
                       help="実行アクション")
    parser.add_argument("--name", help="人物名")
    parser.add_argument("--file", help="バッチ処理用JSONファイル")
    parser.add_argument("--output", help="出力ファイルパス")
    parser.add_argument("--level", choices=["strict", "standard", "lenient"],
                       default="standard", help="バリデーションレベル")

    args = parser.parse_args()

    # ゲートウェイ初期化
    level_map = {
        "strict": ValidationLevel.STRICT,
        "standard": ValidationLevel.STANDARD,
        "lenient": ValidationLevel.LENIENT
    }
    gateway = UnifiedDataCollectionGateway(level_map[args.level])

    if args.action == "add":
        if not args.name:
            print("❌ --name オプションが必要です")
            sys.exit(1)

        success, data, report = gateway.add_person(args.name)
        if success:
            print(f"✅ 追加成功: {data.person_name}")
        else:
            print(f"❌ 追加失敗: {report.critical_issues}")

    elif args.action == "batch":
        if not args.file:
            print("❌ --file オプションが必要です")
            sys.exit(1)

        with open(args.file, 'r', encoding='utf-8') as f:
            persons_list = json.load(f)

        results = gateway.add_persons_batch(persons_list)
        print(f"成功: {len(results['successful'])}, 失敗: {len(results['failed'])}")

    elif args.action == "export":
        output_path = gateway.export_to_csv(args.output)
        print(f"✅ エクスポート完了: {output_path}")

    elif args.action == "stats":
        stats = gateway.get_statistics()
        print(json.dumps(stats, ensure_ascii=False, indent=2))

    elif args.action == "validate-existing":
        results = gateway.enforce_validation_on_existing_files()
        print(f"✅ 既存ファイル検証完了")
        print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()