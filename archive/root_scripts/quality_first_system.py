#!/usr/bin/env python3
"""
品質優先システム（Quality-First System）
Quality-First validation and processing system

このシステムは品質を最優先とし、不確実なデータでの処理継続を禁止します。
エラーを隠蔽せず、早期に問題を顕在化させることで、
人間による何度ものファクトチェックを防ぎます。
"""

import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import traceback

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QualityGate(Enum):
    """品質ゲートの定義"""
    SYSTEM_READY = "システム準備確認"
    DATA_QUALITY = "データ品質検証"
    SCORE_VALIDITY = "スコア妥当性確認"
    STATISTICAL_CHECK = "統計的整合性チェック"
    SAMPLE_VALIDATION = "サンプル検証"


class QualityStatus(Enum):
    """品質ステータス"""
    PASSED = "合格"
    FAILED = "不合格"
    WARNING = "警告"
    SKIPPED = "スキップ"


@dataclass
class QualityCheckResult:
    """品質チェック結果"""
    gate: QualityGate
    status: QualityStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class QualityMetrics:
    """品質メトリクス"""
    api_response_rate: float = 0.0  # API応答実データ率
    deletion_rate: float = 0.0      # 削除率
    famous_person_min_score: float = 0.0  # 有名人最低スコア
    dummy_data_count: int = 0       # ダミーデータ検出数
    total_processed: int = 0        # 処理総数
    errors_count: int = 0           # エラー数


class SystemNotReadyError(Exception):
    """システム未準備エラー"""
    pass


class DataQualityError(Exception):
    """データ品質エラー"""
    pass


class ScoreAnomalyError(Exception):
    """スコア異常エラー"""
    pass


class QualityGateError(Exception):
    """品質ゲートエラー"""
    pass


class QualityFirstSystem:
    """品質優先システム"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初期化

        Args:
            config: 設定（品質基準値など）
        """
        self.config = config or self._get_default_config()
        self.metrics = QualityMetrics()
        self.check_results: List[QualityCheckResult] = []
        self.audit_log: List[Dict[str, Any]] = []

    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定を取得"""
        return {
            'thresholds': {
                'api_response_rate': 0.95,      # 95%以上
                'deletion_rate_min': 0.10,      # 10%以上
                'deletion_rate_max': 0.20,      # 20%以下
                'famous_person_min_score': 7.0,  # 7.0以上
                'dummy_data_tolerance': 0        # 0件（許容なし）
            },
            'famous_persons': [
                {'id': 'P000013', 'name': 'HIKAKIN', 'min_score': 7.0},
                {'id': 'P000001', 'name': '宮崎駿', 'min_score': 8.0},
                {'id': 'P000002', 'name': 'ビートたけし', 'min_score': 7.5},
            ],
            'fail_fast': True,  # Fail-Fast原則を有効化
            'require_all_gates': True  # すべての品質ゲート通過を必須
        }

    def validate_system_ready(self,
                            api_configs: Dict[str, bool]) -> QualityCheckResult:
        """
        システム準備状態の検証

        Args:
            api_configs: API設定状態 {'brave_api': bool, 'google_api': bool}

        Returns:
            品質チェック結果

        Raises:
            SystemNotReadyError: システムが未準備の場合
        """
        self._audit("SYSTEM_READY_CHECK", {"api_configs": api_configs})

        # API設定チェック
        if not any(api_configs.values()):
            result = QualityCheckResult(
                gate=QualityGate.SYSTEM_READY,
                status=QualityStatus.FAILED,
                message="APIが1つも設定されていません",
                details=api_configs
            )
            self.check_results.append(result)

            if self.config['fail_fast']:
                raise SystemNotReadyError(
                    "API未設定のため処理を中止します。"
                    "環境変数にBRAVE_API_KEYまたはGOOGLE_API_KEYを設定してください。"
                )
            return result

        result = QualityCheckResult(
            gate=QualityGate.SYSTEM_READY,
            status=QualityStatus.PASSED,
            message="システム準備完了",
            details=api_configs
        )
        self.check_results.append(result)
        return result

    def validate_data_quality(self,
                            data: Dict[str, Any],
                            source: str = "unknown") -> QualityCheckResult:
        """
        データ品質の検証

        Args:
            data: 検証対象データ
            source: データソース

        Returns:
            品質チェック結果

        Raises:
            DataQualityError: データ品質が基準未満の場合
        """
        self._audit("DATA_QUALITY_CHECK", {"source": source, "data_keys": list(data.keys())})

        # ダミーデータ検出
        dummy_indicators = [
            data.get('total_results') == 0,
            data.get('results') == [],
            data.get('source') == 'fallback',
            data.get('source') == 'simulated',
            'TODO' in str(data),
            'FIXME' in str(data)
        ]

        if any(dummy_indicators):
            self.metrics.dummy_data_count += 1
            result = QualityCheckResult(
                gate=QualityGate.DATA_QUALITY,
                status=QualityStatus.FAILED,
                message="ダミーデータを検出しました",
                details={
                    'indicators': dummy_indicators,
                    'data_sample': str(data)[:200]
                }
            )
            self.check_results.append(result)

            if self.config['fail_fast']:
                raise DataQualityError(
                    f"ダミーデータ検出: {source}のデータが信頼できません。"
                    f"実際のAPI応答を取得してください。"
                )
            return result

        # データ完全性チェック
        required_fields = ['total_results', 'results']
        missing_fields = [f for f in required_fields if f not in data]

        if missing_fields:
            result = QualityCheckResult(
                gate=QualityGate.DATA_QUALITY,
                status=QualityStatus.WARNING,
                message="必須フィールドが不足",
                details={'missing_fields': missing_fields}
            )
            self.check_results.append(result)
            return result

        result = QualityCheckResult(
            gate=QualityGate.DATA_QUALITY,
            status=QualityStatus.PASSED,
            message="データ品質基準を満たしています",
            details={'source': source}
        )
        self.check_results.append(result)
        return result

    def validate_score(self,
                      person_id: str,
                      person_name: str,
                      score: float) -> QualityCheckResult:
        """
        スコアの妥当性検証

        Args:
            person_id: 人物ID
            person_name: 人物名
            score: 計算されたスコア

        Returns:
            品質チェック結果

        Raises:
            ScoreAnomalyError: スコアが異常な場合
        """
        self._audit("SCORE_VALIDATION", {
            "person_id": person_id,
            "person_name": person_name,
            "score": score
        })

        # スコア範囲チェック
        if not 0 <= score <= 10:
            result = QualityCheckResult(
                gate=QualityGate.SCORE_VALIDITY,
                status=QualityStatus.FAILED,
                message="スコアが範囲外",
                details={'score': score, 'expected_range': '0-10'}
            )
            self.check_results.append(result)

            if self.config['fail_fast']:
                raise ScoreAnomalyError(
                    f"{person_name}のスコア{score}が異常です（0-10の範囲外）"
                )
            return result

        # 有名人の最低スコアチェック
        for famous_person in self.config['famous_persons']:
            if person_id == famous_person['id']:
                if score < famous_person['min_score']:
                    result = QualityCheckResult(
                        gate=QualityGate.SCORE_VALIDITY,
                        status=QualityStatus.FAILED,
                        message=f"有名人{famous_person['name']}のスコアが低すぎます",
                        details={
                            'actual_score': score,
                            'minimum_required': famous_person['min_score']
                        }
                    )
                    self.check_results.append(result)

                    if self.config['fail_fast']:
                        raise ScoreAnomalyError(
                            f"{famous_person['name']}のスコア{score}が"
                            f"最低基準{famous_person['min_score']}未満です。"
                            f"Web検索APIが正しく動作していない可能性があります。"
                        )
                    return result

        result = QualityCheckResult(
            gate=QualityGate.SCORE_VALIDITY,
            status=QualityStatus.PASSED,
            message="スコア妥当性確認OK",
            details={'score': score}
        )
        self.check_results.append(result)
        return result

    def validate_statistics(self,
                           total: int,
                           deleted: int,
                           scores: List[float]) -> QualityCheckResult:
        """
        統計的整合性の検証

        Args:
            total: 総数
            deleted: 削除数
            scores: スコアリスト

        Returns:
            品質チェック結果
        """
        self._audit("STATISTICAL_CHECK", {
            "total": total,
            "deleted": deleted,
            "score_count": len(scores)
        })

        deletion_rate = deleted / total if total > 0 else 0
        self.metrics.deletion_rate = deletion_rate

        # 削除率チェック
        min_rate = self.config['thresholds']['deletion_rate_min']
        max_rate = self.config['thresholds']['deletion_rate_max']

        if not min_rate <= deletion_rate <= max_rate:
            result = QualityCheckResult(
                gate=QualityGate.STATISTICAL_CHECK,
                status=QualityStatus.FAILED,
                message=f"削除率{deletion_rate:.1%}が異常です",
                details={
                    'deletion_rate': deletion_rate,
                    'expected_range': f'{min_rate:.0%}-{max_rate:.0%}',
                    'total': total,
                    'deleted': deleted
                }
            )
            self.check_results.append(result)

            if deletion_rate > 0.45:  # 45%超は明らかに異常
                if self.config['fail_fast']:
                    raise QualityGateError(
                        f"削除率{deletion_rate:.1%}は異常に高い値です。"
                        f"Web検索スコアが正しく計算されていない可能性があります。"
                    )
            return result

        result = QualityCheckResult(
            gate=QualityGate.STATISTICAL_CHECK,
            status=QualityStatus.PASSED,
            message="統計的整合性OK",
            details={'deletion_rate': deletion_rate}
        )
        self.check_results.append(result)
        return result

    def run_all_gates(self,
                     context: Dict[str, Any]) -> bool:
        """
        すべての品質ゲートを実行

        Args:
            context: 検証コンテキスト

        Returns:
            すべて合格した場合True

        Raises:
            QualityGateError: いずれかのゲートで失敗した場合
        """
        gates_passed = []

        try:
            # Gate 1: システム準備
            if 'api_configs' in context:
                result = self.validate_system_ready(context['api_configs'])
                gates_passed.append(result.status == QualityStatus.PASSED)

            # Gate 2: データ品質
            if 'data' in context:
                for data_item in context['data']:
                    result = self.validate_data_quality(
                        data_item['data'],
                        data_item.get('source', 'unknown')
                    )
                    gates_passed.append(result.status == QualityStatus.PASSED)

            # Gate 3: スコア妥当性
            if 'scores' in context:
                for score_item in context['scores']:
                    result = self.validate_score(
                        score_item['person_id'],
                        score_item['person_name'],
                        score_item['score']
                    )
                    gates_passed.append(result.status == QualityStatus.PASSED)

            # Gate 4: 統計的整合性
            if 'statistics' in context:
                stats = context['statistics']
                result = self.validate_statistics(
                    stats['total'],
                    stats['deleted'],
                    stats.get('scores', [])
                )
                gates_passed.append(result.status == QualityStatus.PASSED)

            # すべてのゲートが合格したか確認
            all_passed = all(gates_passed) if gates_passed else False

            if not all_passed and self.config['require_all_gates']:
                failed_gates = [
                    r.gate.value for r in self.check_results
                    if r.status == QualityStatus.FAILED
                ]
                raise QualityGateError(
                    f"品質ゲート失敗: {', '.join(failed_gates)}"
                )

            return all_passed

        except Exception as e:
            self._audit("QUALITY_GATE_ERROR", {
                "error": str(e),
                "traceback": traceback.format_exc()
            })
            raise

    def _audit(self, action: str, details: Dict[str, Any]):
        """
        監査ログ記録

        Args:
            action: アクション名
            details: 詳細情報
        """
        entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'details': details
        }
        self.audit_log.append(entry)
        logger.info(f"AUDIT: {action} - {json.dumps(details, ensure_ascii=False)[:200]}")

    def export_audit_log(self, filepath: str):
        """
        監査ログのエクスポート

        Args:
            filepath: 出力ファイルパス
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.audit_log, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"監査ログを出力: {filepath}")

    def get_summary(self) -> Dict[str, Any]:
        """
        品質チェックサマリーの取得

        Returns:
            サマリー情報
        """
        return {
            'metrics': {
                'api_response_rate': self.metrics.api_response_rate,
                'deletion_rate': self.metrics.deletion_rate,
                'dummy_data_count': self.metrics.dummy_data_count,
                'errors_count': self.metrics.errors_count
            },
            'gates': {
                'total': len(self.check_results),
                'passed': len([r for r in self.check_results if r.status == QualityStatus.PASSED]),
                'failed': len([r for r in self.check_results if r.status == QualityStatus.FAILED]),
                'warnings': len([r for r in self.check_results if r.status == QualityStatus.WARNING])
            },
            'failed_checks': [
                {
                    'gate': r.gate.value,
                    'message': r.message,
                    'details': r.details
                }
                for r in self.check_results if r.status == QualityStatus.FAILED
            ]
        }


def main():
    """テスト実行"""
    print("="*60)
    print("品質優先システム (Quality-First System)")
    print("="*60)

    # システム初期化
    qf_system = QualityFirstSystem()

    # テストケース1: API未設定
    print("\n🔍 Test 1: API未設定のケース")
    try:
        qf_system.validate_system_ready({'brave_api': False, 'google_api': False})
    except SystemNotReadyError as e:
        print(f"✅ 期待通りエラー: {e}")

    # テストケース2: ダミーデータ検出
    print("\n🔍 Test 2: ダミーデータ検出")
    dummy_data = {'total_results': 0, 'results': [], 'source': 'simulated'}
    try:
        qf_system.validate_data_quality(dummy_data, "test_api")
    except DataQualityError as e:
        print(f"✅ 期待通りエラー: {e}")

    # テストケース3: 有名人の低スコア検出
    print("\n🔍 Test 3: HIKAKINの低スコア検出")
    try:
        qf_system.validate_score('P000013', 'HIKAKIN', 3.3)
    except ScoreAnomalyError as e:
        print(f"✅ 期待通りエラー: {e}")

    # テストケース4: 削除率異常
    print("\n🔍 Test 4: 削除率45.6%の異常検出")
    try:
        qf_system.validate_statistics(4701, 2145, [])
    except QualityGateError as e:
        print(f"✅ 期待通りエラー: {e}")

    # サマリー表示
    print("\n📊 品質チェックサマリー:")
    summary = qf_system.get_summary()
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    # 監査ログ出力
    qf_system.export_audit_log('quality_audit.json')
    print("\n✅ 品質優先システムのテスト完了")


if __name__ == "__main__":
    main()
