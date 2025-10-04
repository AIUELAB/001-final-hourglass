#!/usr/bin/env python3
"""
強制バリデーションパイプライン
すべてのエピソード生成が必ず通過する強制実行メカニズム

このパイプラインを回避することは不可能
"""

import json
import hashlib
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import sys
import traceback

sys.path.append(str(Path(__file__).parent))
from unified_validation_system import UnifiedValidationSystem, ValidationResult, ValidationLevel


@dataclass
class PipelineStage:
    """パイプラインステージ"""
    name: str
    validator: Callable
    required: bool = True  # このステージは必須か
    blocking: bool = True  # 失敗時に後続処理をブロックするか
    retry_count: int = 0   # リトライ回数


@dataclass
class PipelineLog:
    """パイプライン実行ログ"""
    timestamp: str
    episode_hash: str
    person_name: str
    stage_name: str
    success: bool
    error_message: Optional[str] = None
    duration_ms: float = 0


@dataclass
class PipelineResult:
    """パイプライン実行結果"""
    success: bool
    final_episode: Optional[str] = None
    validation_result: Optional[ValidationResult] = None
    stages_passed: List[str] = field(default_factory=list)
    stages_failed: List[str] = field(default_factory=list)
    logs: List[PipelineLog] = field(default_factory=list)
    total_duration_ms: float = 0
    error_summary: Optional[str] = None


class MandatoryPipeline:
    """強制バリデーションパイプライン"""

    def __init__(self, log_file: str = "pipeline_audit.json"):
        """
        初期化

        Args:
            log_file: 監査ログファイルパス
        """
        self.validation_system = UnifiedValidationSystem()
        self.stages = self._initialize_stages()
        self.log_file = Path(log_file)
        self.bypass_attempts = []  # バイパス試行記録

        # パイプラインの整合性チェック
        self._verify_pipeline_integrity()

    def _initialize_stages(self) -> List[PipelineStage]:
        """パイプラインステージを初期化"""
        return [
            PipelineStage(
                name="pre_validation",
                validator=self._pre_validation,
                required=True,
                blocking=True
            ),
            PipelineStage(
                name="content_validation",
                validator=self._content_validation,
                required=True,
                blocking=True
            ),
            PipelineStage(
                name="quality_check",
                validator=self._quality_check,
                required=True,
                blocking=True
            ),
            PipelineStage(
                name="final_approval",
                validator=self._final_approval,
                required=True,
                blocking=True
            )
        ]

    def _verify_pipeline_integrity(self):
        """パイプライン整合性を検証"""
        # パイプラインが改竄されていないことを確認
        expected_stages = ["pre_validation", "content_validation", "quality_check", "final_approval"]
        actual_stages = [stage.name for stage in self.stages]

        if actual_stages != expected_stages:
            raise RuntimeError(
                f"パイプライン整合性エラー: ステージが改竄されています\n"
                f"期待: {expected_stages}\n"
                f"実際: {actual_stages}"
            )

    def process(self, episode: str, person_name: str, age: int = 30,
                metadata: Optional[Dict] = None) -> PipelineResult:
        """
        エピソードをパイプライン処理

        Args:
            episode: エピソード文
            person_name: 人物名
            age: 年齢
            metadata: 追加メタデータ

        Returns:
            PipelineResult: 処理結果
        """
        start_time = time.time()
        episode_hash = hashlib.md5(episode.encode()).hexdigest()

        result = PipelineResult(
            success=False,
            final_episode=episode
        )

        # コンテキスト情報
        context = {
            'episode': episode,
            'person_name': person_name,
            'age': age,
            'metadata': metadata or {},
            'episode_hash': episode_hash
        }

        # 各ステージを実行
        for stage in self.stages:
            stage_start = time.time()
            stage_success = False
            error_message = None

            try:
                # ステージ実行
                stage_result = stage.validator(context)
                stage_success = stage_result.get('success', False)

                if stage_success:
                    result.stages_passed.append(stage.name)
                    # コンテキストを更新
                    if 'updated_episode' in stage_result:
                        context['episode'] = stage_result['updated_episode']
                        result.final_episode = stage_result['updated_episode']
                    if 'validation_result' in stage_result:
                        result.validation_result = stage_result['validation_result']
                else:
                    result.stages_failed.append(stage.name)
                    error_message = stage_result.get('error', 'Unknown error')

                    # ブロッキングステージで失敗した場合
                    if stage.blocking:
                        result.error_summary = f"Stage '{stage.name}' failed: {error_message}"
                        break

            except Exception as e:
                # ステージでエラー発生
                stage_success = False
                error_message = str(e)
                result.stages_failed.append(stage.name)
                result.error_summary = f"Stage '{stage.name}' error: {error_message}"

                if stage.blocking:
                    break

            # ログ記録
            stage_duration = (time.time() - stage_start) * 1000
            log_entry = PipelineLog(
                timestamp=datetime.now().isoformat(),
                episode_hash=episode_hash,
                person_name=person_name,
                stage_name=stage.name,
                success=stage_success,
                error_message=error_message,
                duration_ms=stage_duration
            )
            result.logs.append(log_entry)

        # 全ステージ成功チェック
        result.success = len(result.stages_failed) == 0
        result.total_duration_ms = (time.time() - start_time) * 1000

        # 監査ログ保存
        self._save_audit_log(result)

        # バイパス試行検出
        if not result.success:
            self._detect_bypass_attempt(context, result)

        return result

    def _pre_validation(self, context: Dict) -> Dict:
        """事前検証ステージ"""
        episode = context['episode']
        person_name = context['person_name']

        # 基本チェック
        if not episode or not person_name:
            return {
                'success': False,
                'error': 'エピソードまたは人物名が空です'
            }

        # 最小長チェック
        if len(episode) < 50:
            return {
                'success': False,
                'error': f'エピソードが短すぎます: {len(episode)}文字'
            }

        # 必須要素チェック
        if person_name not in episode:
            return {
                'success': False,
                'error': f'エピソードに人物名「{person_name}」が含まれていません'
            }

        age = context['age']
        if f'{age}歳' not in episode:
            return {
                'success': False,
                'error': f'エピソードに年齢「{age}歳」が含まれていません'
            }

        return {'success': True}

    def _content_validation(self, context: Dict) -> Dict:
        """コンテンツ検証ステージ"""
        episode = context['episode']
        person_name = context['person_name']
        age = context['age']

        # 統合バリデーションシステムで検証
        validation_result = self.validation_system.validate(
            episode=episode,
            person_name=person_name,
            age=age,
            strict_mode=True
        )

        if not validation_result.is_valid:
            # 最も深刻な問題を報告
            critical_issues = [
                issue for issue in validation_result.issues
                if issue.level in [ValidationLevel.CRITICAL, ValidationLevel.ERROR]
            ]

            error_messages = []
            for issue in critical_issues[:3]:  # 最初の3つ
                error_messages.append(f"{issue.message}")

            return {
                'success': False,
                'error': ' / '.join(error_messages),
                'validation_result': validation_result
            }

        return {
            'success': True,
            'validation_result': validation_result
        }

    def _quality_check(self, context: Dict) -> Dict:
        """品質チェックステージ"""
        episode = context['episode']

        # 品質スコアチェック（前のステージで取得）
        if 'validation_result' in context:
            validation_result = context['validation_result']
        else:
            # 再検証が必要な場合
            validation_result = self.validation_system.validate(
                episode=episode,
                person_name=context['person_name'],
                age=context['age']
            )

        # スコア基準
        MIN_SCORE = 70.0

        if validation_result.score < MIN_SCORE:
            return {
                'success': False,
                'error': f'品質スコア不足: {validation_result.score:.1f} < {MIN_SCORE}'
            }

        return {
            'success': True,
            'validation_result': validation_result
        }

    def _final_approval(self, context: Dict) -> Dict:
        """最終承認ステージ"""
        episode = context['episode']

        # 最終的な整合性チェック
        # 文字数の最終確認
        if not (132 <= len(episode) <= 250):
            return {
                'success': False,
                'error': f'最終文字数チェック失敗: {len(episode)}文字'
            }

        # フォーマットの最終確認
        if not episode.startswith('あなたと同じ'):
            return {
                'success': False,
                'error': 'フォーマットエラー: 「あなたと同じ」で開始していません'
            }

        if not episode.endswith('。'):
            return {
                'success': False,
                'error': 'フォーマットエラー: 句点で終了していません'
            }

        return {'success': True}

    def _save_audit_log(self, result: PipelineResult):
        """監査ログを保存"""
        try:
            # 既存ログ読み込み
            if self.log_file.exists():
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            else:
                logs = []

            # 新規ログ追加
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'success': result.success,
                'stages_passed': result.stages_passed,
                'stages_failed': result.stages_failed,
                'total_duration_ms': result.total_duration_ms,
                'error_summary': result.error_summary
            }
            logs.append(log_entry)

            # 最新100件のみ保持
            logs = logs[-100:]

            # ログ保存
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"監査ログ保存エラー: {e}")

    def _detect_bypass_attempt(self, context: Dict, result: PipelineResult):
        """バイパス試行を検出"""
        # 同一エピソードの連続失敗を検出
        episode_hash = context['episode_hash']

        self.bypass_attempts.append({
            'timestamp': datetime.now().isoformat(),
            'episode_hash': episode_hash,
            'person_name': context['person_name'],
            'failure_stage': result.stages_failed[0] if result.stages_failed else 'unknown'
        })

        # 直近10回で同じエピソードが3回以上失敗
        recent_attempts = self.bypass_attempts[-10:]
        same_episode_count = sum(1 for a in recent_attempts if a['episode_hash'] == episode_hash)

        if same_episode_count >= 3:
            print(f"⚠️ 警告: バイパス試行を検出しました")
            print(f"  エピソード: {context['episode'][:50]}...")
            print(f"  失敗回数: {same_episode_count}")
            print(f"  失敗ステージ: {result.stages_failed}")

    def get_stats(self) -> Dict:
        """統計情報を取得"""
        if not self.log_file.exists():
            return {
                'total_processed': 0,
                'success_count': 0,
                'failure_count': 0,
                'success_rate': 0,
                'bypass_attempts': len(self.bypass_attempts)
            }

        with open(self.log_file, 'r', encoding='utf-8') as f:
            logs = json.load(f)

        total = len(logs)
        success = sum(1 for log in logs if log['success'])

        return {
            'total_processed': total,
            'success_count': success,
            'failure_count': total - success,
            'success_rate': success / total * 100 if total > 0 else 0,
            'bypass_attempts': len(self.bypass_attempts)
        }


def test_mandatory_pipeline():
    """強制パイプラインのテスト"""
    pipeline = MandatoryPipeline()

    test_cases = [
        {
            'name': 'テンプレート文章',
            'episode': 'あなたと同じ30歳のとき、大谷翔平は素晴らしい活躍をした。',
            'person_name': '大谷翔平',
            'age': 30,
            'expected': False
        },
        {
            'name': '正常なエピソード',
            'episode': 'あなたと同じ38歳のとき、村上春樹は「ノルウェイの森」を発表し上下巻430万部の大ベストセラーとなった。「風の歌を聴け」「羊をめぐる冒険」に続く作品で、40か国以上で翻訳された。',
            'person_name': '村上春樹',
            'age': 38,
            'expected': True
        },
        {
            'name': '人物名なし',
            'episode': 'あなたと同じ25歳のとき、素晴らしい成果を達成した。',
            'person_name': 'イチロー',
            'age': 25,
            'expected': False
        },
        {
            'name': '文字数不足',
            'episode': 'あなたと同じ29歳のとき、大谷翔平はMVPを獲得。',
            'person_name': '大谷翔平',
            'age': 29,
            'expected': False
        }
    ]

    print("強制バリデーションパイプラインテスト")
    print("=" * 60)

    for test_case in test_cases:
        print(f"\n■ {test_case['name']}")
        print(f"  エピソード: {test_case['episode'][:50]}...")

        result = pipeline.process(
            episode=test_case['episode'],
            person_name=test_case['person_name'],
            age=test_case['age']
        )

        status = "✅ 成功" if result.success else "❌ 失敗"
        print(f"  結果: {status}")

        if result.success:
            print(f"  通過ステージ: {' → '.join(result.stages_passed)}")
            if result.validation_result:
                print(f"  品質スコア: {result.validation_result.score:.1f}/100")
        else:
            print(f"  失敗ステージ: {result.stages_failed}")
            print(f"  エラー: {result.error_summary}")

        print(f"  処理時間: {result.total_duration_ms:.1f}ms")

        # 期待結果との比較
        if result.success == test_case['expected']:
            print(f"  ✅ テスト成功")
        else:
            print(f"  ❌ テスト失敗（期待と異なる）")

    # 統計表示
    print(f"\n{'=' * 60}")
    print("パイプライン統計:")
    stats = pipeline.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    test_mandatory_pipeline()