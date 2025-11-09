#!/usr/bin/env python3
"""
Quality Gate System - エピソード品質の絶対的保証システム

このシステムはすべてのエピソード生成の単一エントリーポイントとして機能し、
品質基準を満たさないエピソードの生成を物理的に不可能にします。
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import csv
from dataclasses import dataclass, asdict
from enum import Enum

# 既存モジュールのインポート
from pdca_guardian import PDCAGuardian
from src.fact_checker import FactChecker

# Phase 4.2: FactCheckerQualityGate統合
from rules.rule_191_fact_checker_system import FactCheckerQualityGate

# Phase 4 (2025-11-01): 日本語品質チェッカーv2統合
# Phase 4.3 (2025-11-04): v3に更新 - 「となっました」問題を完全解決
from src.japanese_quality_checker_v3 import JapaneseQualityCheckerV3


class ApprovalStatus(Enum):
    """承認ステータス"""
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


@dataclass
class ValidationResult:
    """検証結果"""
    status: ApprovalStatus
    score: float
    violations: List[str]
    suggestions: List[str]
    details: Dict


@dataclass
class Episode:
    """エピソードデータ構造"""
    person_name: str
    person_name_display: Optional[str]
    user_age: int
    episode_age: int
    episode_type: str
    episode_content: str
    empathy_score: float
    memory_score: float
    record_score: float
    weighted_score: float

    def to_dict(self) -> Dict:
        return asdict(self)


class QualityGateSystem:
    """
    品質ゲートシステムメインクラス

    すべてのエピソード生成はこのクラスを通過する必要があり、
    品質基準を満たさないものは自動的に拒否されます。
    """

    def __init__(self, config_path: str = "quality_gate_config.json"):
        """初期化"""
        self.config = self._load_config(config_path)
        self.pdca_guardian = PDCAGuardian()
        self.fact_checker = FactChecker()

        # Phase 4.2: FactCheckerQualityGate統合
        self.fact_checker_gate = FactCheckerQualityGate()

        # Phase 4 (2025-11-01): 日本語品質チェッカーv2統合
        # Phase 4.3 (2025-11-04): v3に更新 - 「となっました」問題を完全解決
        self.japanese_checker = JapaneseQualityCheckerV3(strict_mode=True)

        # 品質基準
        self.MIN_QUALITY_SCORE = self.config.get("min_quality_score", 8.0)
        self.MAX_REJECTION_RATE = self.config.get("max_rejection_rate", 0.2)

        # 統計情報
        self.stats = {
            "total_attempts": 0,
            "approved": 0,
            "rejected": 0,
            "violations_by_type": {},
            "fact_check_passed": 0,  # Phase 4.2
            "fact_check_failed": 0,  # Phase 4.2
            "japanese_quality_passed": 0,  # Phase 4 (2025-11-01)
            "japanese_quality_failed": 0,  # Phase 4 (2025-11-01)
            "japanese_quality_auto_fixed": 0  # Phase 4 (2025-11-01)
        }

        # 環境変数でゲート承認を管理
        self._clear_approval()

    def _load_config(self, config_path: str) -> Dict:
        """設定ファイルを読み込み"""
        if Path(config_path).exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "min_quality_score": 8.0,
            "max_rejection_rate": 0.2,
            "enable_parallel_validation": True,
            "strict_mode": True
        }

    def _clear_approval(self):
        """承認フラグをクリア"""
        if 'QUALITY_GATE_APPROVED' in os.environ:
            del os.environ['QUALITY_GATE_APPROVED']

    def _grant_approval(self):
        """承認フラグを設定"""
        os.environ['QUALITY_GATE_APPROVED'] = 'true'

    def validate_episode_sync(self, episode_data: Dict) -> ValidationResult:
        """
        エピソードを検証（同期版）

        Args:
            episode_data: エピソードデータ

        Returns:
            ValidationResult: 検証結果

        Note:
            Phase 4.9 (2025-11-01): 同期コードから呼び出すためのラッパーメソッド
            内部でasyncio.run()を使用してvalidate_episode()を実行
        """
        import asyncio
        return asyncio.run(self.validate_episode(episode_data))

    async def validate_episode(self, episode_data: Dict) -> ValidationResult:
        """
        エピソードを検証

        Args:
            episode_data: エピソードデータ

        Returns:
            ValidationResult: 検証結果
        """
        violations = []
        suggestions = []
        scores = {}

        # 1. PDCAルールチェック（156ルール）
        episode_text = episode_data.get('episode_content', '')
        age = episode_data.get('episode_age', 0)
        person_name_display = episode_data.get('person_name_display', episode_data.get('person_name', ''))

        pdca_violations = []

        # 【RCA-Kaizen追加】禁止セクションチェック（【評価】等）
        forbidden_sections = ['【評価】', '【検証】', '【分析】', '【コメント】', '【考察】']
        for section in forbidden_sections:
            if section in episode_text:
                violations.append(f"RULE_192_FORBIDDEN_SECTION: エピソード本文に{section}セクションが含まれています")
                suggestions.append(f"{section}セクションを削除してください。エピソード本文は純粋な物語のみで構成すること")
                self.stats["violations_by_type"]["RULE_192"] = \
                    self.stats["violations_by_type"].get("RULE_192", 0) + 1

        # 【RCA-Kaizen追加】年齢表現繰り返しチェック（RULE_193）
        age_str = f"{age}歳"
        age_count = episode_text.count(age_str)

        # 基準: 年齢表現は2回まで許容（冒頭の「あなたと同じ〜歳のとき」＋1回まで）
        if age_count >= 3:
            severity = "HIGH" if age_count >= 4 else "MEDIUM"
            violations.append(f"RULE_193_AGE_REPETITION: 年齢表現「{age_str}」が{age_count}回出現（許容: 2回まで、重大度: {severity}）")
            suggestions.append(f"年齢表現「{age_str}」を削減してください。冒頭の「あなたと同じ{age}歳のとき」以外は1回までに抑えること")
            self.stats["violations_by_type"]["RULE_193"] = \
                self.stats["violations_by_type"].get("RULE_193", 0) + 1

        # 【RCA-Kaizen追加】空白行チェック（RULE_194）
        newline_count = episode_text.count('\n')
        has_double_newline = '\n\n' in episode_text

        # 基準: 改行は1回のみ（2段落構成）、連続改行（\n\n）は禁止
        if newline_count > 1 or has_double_newline:
            severity = "HIGH" if newline_count > 2 else "MEDIUM"
            violations.append(f"RULE_194_BLANK_LINE: 不要な空白行が検出されました（改行: {newline_count}回、期待値: 1回）")
            suggestions.append("段落間は改行1回のみとし、空白行（連続改行）を削除してください")
            self.stats["violations_by_type"]["RULE_194"] = \
                self.stats["violations_by_type"].get("RULE_194", 0) + 1

        # 【RCA-Kaizen追加】架空エピソード注釈チェック（RULE_195）
        fictional_markers = ['※このエピソードは架空', '※架空のエピソード', '※実在の人物', '※注：この']
        for marker in fictional_markers:
            if marker in episode_text:
                violations.append(f"RULE_195_FICTIONAL_MARKER: 架空エピソードの注釈が検出されました")
                suggestions.append("架空エピソード注釈を削除してください。本番環境では実在の人物のみを扱います")
                self.stats["violations_by_type"]["RULE_195"] = \
                    self.stats["violations_by_type"].get("RULE_195", 0) + 1
                break

        # 【RCA-Kaizen追加】専門分野整合性チェック（RULE_196）
        # LLMハルシネーション防止: 柔道選手がボクシング記述を持つ等の誤認を検出
        sport_incompatibility = {
            # 柔道選手が絶対に持ち得ないキーワード
            '柔道': ['ボクシング', 'K-1', 'キックボクシング', 'WBC', 'WBA', 'WBO', 'IBF', 'リング', 'ノックアウト'],
            # サッカー選手が絶対に持ち得ないキーワード
            'サッカー': ['野球', 'プロ野球', 'ホームラン', '甲子園', '投手', '打者', '本塁打', '柔道', '一本'],
            # 野球選手が絶対に持ち得ないキーワード
            '野球': ['サッカー', 'Jリーグ', 'ワールドカップ', 'ゴール', 'PK', '柔道', '内股'],
            # ボクサーが絶対に持ち得ないキーワード
            'ボクシング': ['柔道', '内股', '背負投', '寝技', 'サッカー', 'ゴール'],
            # K-1選手が絶対に持ち得ないキーワード
            'K-1': ['柔道', '内股', '野球', 'ホームラン', 'サッカー', 'ゴール']
        }

        # 人物名から専門分野を推定（簡易版）
        detected_specialty = None
        category = episode_data.get('category', '')

        # カテゴリがスポーツの場合、エピソード内容から専門分野を判定
        if 'スポーツ' in category:
            for specialty, _ in sport_incompatibility.items():
                if specialty in episode_text:
                    detected_specialty = specialty
                    break

        # 専門分野が検出された場合、不適切なキーワードをチェック
        if detected_specialty:
            incompatible_keywords = sport_incompatibility[detected_specialty]
            found_incompatible = [kw for kw in incompatible_keywords if kw in episode_text]

            if found_incompatible:
                violations.append(
                    f"RULE_196_FACT_CHECK: 専門分野の不一致が検出されました - "
                    f"{detected_specialty}選手のエピソードに不適切なキーワード: {', '.join(found_incompatible)}"
                )
                suggestions.append(
                    f"{detected_specialty}選手のエピソードから、{', '.join(found_incompatible)}に関する記述を削除してください。"
                    f"異なるスポーツの情報が混入している可能性があります（LLMハルシネーション）"
                )
                self.stats["violations_by_type"]["RULE_196"] = \
                    self.stats["violations_by_type"].get("RULE_196", 0) + 1

        # エピソード品質チェック
        quality_violations = self.pdca_guardian.check_episode_quality(episode_text, age, person_name_display)
        if quality_violations:
            for v in quality_violations:
                violations.append(f"RULE_{v.get('rule_number', '000')}: {v.get('message', '')}")
                suggestions.append(v.get('suggestion', '改善してください'))

        # 感情的価値チェック
        emotional_violations = self.pdca_guardian.check_emotional_value(episode_data)
        if emotional_violations:
            for v in emotional_violations:
                violations.append(f"感情価値: {v.get('message', '')}")
                suggestions.append(v.get('suggestion', ''))

        # センセーショナル価値チェック
        sensational_violations = self.pdca_guardian.check_sensational_value(episode_data)
        if sensational_violations:
            for v in sensational_violations:
                violations.append(f"センセーショナル: {v.get('message', '')}")
                suggestions.append(v.get('suggestion', ''))

        # 2. 事実確認（Phase 4.2: FactCheckerQualityGate使用）
        if self.config.get("enable_fact_checking", True):
            try:
                # FactCheckerQualityGateを使用した高度な事実検証
                fact_check_passed, fact_check_error = self.fact_checker_gate.validate(
                    episode_text=episode_text,
                    person_name=person_name_display,
                    strict_mode=False  # 警告として扱う
                )

                if fact_check_error is not None:  # 検証失敗
                    violations.append(f"事実検証失敗: {fact_check_error}")
                    suggestions.append("「初の〜」表現の事実を確認してください")
                    self.stats["fact_check_failed"] += 1
                else:  # 検証合格
                    self.stats["fact_check_passed"] += 1
                    scores['fact_check'] = 10.0  # 満点

            except Exception as e:
                violations.append(f"事実確認エラー: {str(e)}")
                self.stats["fact_check_failed"] += 1

        # 2.5. 日本語品質チェック（Phase 4, 2025-11-01）
        if self.config.get("enable_japanese_quality_check", True):
            try:
                japanese_result = self.japanese_checker.fix(episode_text, dry_run=False)

                if not japanese_result.is_valid:
                    # 問題が検出された場合
                    if japanese_result.changes_made > 0:
                        # 自動修正が実施された場合
                        episode_data['episode_content'] = japanese_result.fixed_text
                        episode_text = japanese_result.fixed_text  # 更新されたテキストを使用
                        self.stats["japanese_quality_auto_fixed"] += 1

                        # 警告として記録（自動修正済み）
                        for issue in japanese_result.issues:
                            suggestions.append(
                                f"[自動修正済み] {issue.pattern_name}: {issue.description} "
                                f"(重要度: {issue.severity.value})"
                            )
                    else:
                        # 自動修正できない問題がある場合
                        self.stats["japanese_quality_failed"] += 1
                        for issue in japanese_result.issues:
                            violations.append(
                                f"RULE_300_JAPANESE_QUALITY: {issue.pattern_name} - {issue.description}"
                            )
                            suggestions.append(issue.suggestion)
                else:
                    # 問題なし
                    self.stats["japanese_quality_passed"] += 1
                    scores['japanese_quality'] = 10.0  # 満点

            except Exception as e:
                violations.append(f"日本語品質チェックエラー: {str(e)}")
                self.stats["japanese_quality_failed"] += 1

        # 3. 品質スコア計算
        quality_score = self._calculate_quality_score(episode_data)
        scores['quality'] = quality_score

        if quality_score < self.MIN_QUALITY_SCORE:
            violations.append(f"品質スコア不足: {quality_score:.2f} < {self.MIN_QUALITY_SCORE}")
            suggestions.append("エピソードの内容を改善してスコアを向上させてください")

        # 4. グループ名チェック（RULE_154）
        if self._is_group_name(episode_data.get('person_name', '')):
            violations.append("RULE_154: グループ名が個人名として使用されています")
            suggestions.append("グループメンバーの個人名を使用し、person_name_displayでグループ帰属を示してください")

        # 5. 節目重要度チェック（RULE_153）
        milestone_score = self._evaluate_milestone_importance(episode_data)
        scores['milestone'] = milestone_score

        if milestone_score < 7.0:
            violations.append(f"RULE_153: 節目重要度が低い: {milestone_score:.1f}")
            suggestions.append("より重要な節目（デビュー、開始、初など）を選択してください")

        # 最終判定
        if violations:
            status = ApprovalStatus.REJECTED
            if len(violations) <= 2 and quality_score >= 7.0:
                status = ApprovalStatus.NEEDS_REVISION
        else:
            status = ApprovalStatus.APPROVED

        # 統計更新
        self._update_statistics(status, violations)

        return ValidationResult(
            status=status,
            score=quality_score,
            violations=violations,
            suggestions=suggestions,
            details=scores
        )

    async def _verify_facts(self, episode_data: Dict) -> Dict:
        """事実確認（非同期）"""
        try:
            # FactCheckerを使用した検証
            is_valid = self.fact_checker.verify_person_existence(
                episode_data.get('person_name', '')
            )

            if not is_valid:
                return {
                    'valid': False,
                    'reason': '人物の実在性が確認できません',
                    'suggestion': 'Wikipedia等で人物情報を確認してください'
                }

            # 年齢の妥当性チェック
            age = episode_data.get('episode_age', 0)
            if age < 0 or age > 120:
                return {
                    'valid': False,
                    'reason': f'年齢が不適切: {age}',
                    'suggestion': '正しい年齢を設定してください'
                }

            return {'valid': True}

        except Exception as e:
            return {
                'valid': False,
                'reason': str(e),
                'suggestion': 'API接続を確認してください'
            }

    def _calculate_quality_score(self, episode_data: Dict) -> float:
        """品質スコアを計算"""
        # 既存のスコアを使用
        weighted_score = episode_data.get('weighted_score', 0)
        empathy_score = episode_data.get('empathy_score', 0)
        memory_score = episode_data.get('memory_score', 0)
        record_score = episode_data.get('record_score', 0)

        # 加重平均
        quality_score = (
            weighted_score * 0.4 +
            empathy_score * 0.2 +
            memory_score * 0.2 +
            record_score * 0.2
        )

        return min(10.0, quality_score)

    def _is_group_name(self, name: str) -> bool:
        """グループ名かどうかを判定"""
        group_indicators = [
            'YOASOBI', 'SEKAI NO OWARI', 'サザンオールスターズ',
            'AKB48', '乃木坂46', '嵐', 'SMAP', 'なでしこジャパン',
            'ジャパン', 'チーム', '軍団', '一座', '楽団', 'ズ'
        ]
        return any(indicator in name for indicator in group_indicators)

    def _evaluate_milestone_importance(self, episode_data: Dict) -> float:
        """節目の重要度を評価"""
        content = episode_data.get('episode_content', '')
        episode_type = episode_data.get('episode_type', '')

        # 重要な節目のキーワード
        high_importance = ['開始', 'デビュー', '誕生', '初', '最初', '創業', '結成']
        medium_importance = ['達成', '受賞', '優勝', '完成', '発表']
        low_importance = ['周年', '継続', '記念', '現在']

        score = 5.0  # 基準スコア

        # キーワードによる加点・減点
        for keyword in high_importance:
            if keyword in content or keyword in episode_type:
                score += 2.0

        for keyword in medium_importance:
            if keyword in content or keyword in episode_type:
                score += 1.0

        for keyword in low_importance:
            if keyword in content or keyword in episode_type:
                score -= 1.0

        return min(10.0, max(0.0, score))

    def _update_statistics(self, status: ApprovalStatus, violations: List[str]):
        """統計情報を更新"""
        self.stats["total_attempts"] += 1

        if status == ApprovalStatus.APPROVED:
            self.stats["approved"] += 1
        else:
            self.stats["rejected"] += 1

            # 違反タイプ別に集計
            for violation in violations:
                rule_name = violation.split(':')[0] if ':' in violation else violation
                self.stats["violations_by_type"][rule_name] = \
                    self.stats["violations_by_type"].get(rule_name, 0) + 1

    async def generate_episodes(self,
                               count: Optional[int] = None,
                               min_quality: float = None) -> List[Episode]:
        """
        品質保証されたエピソードを生成

        Args:
            count: 生成数（Noneの場合は品質基準を満たす限り継続）
            min_quality: 最小品質スコア

        Returns:
            承認されたエピソードのリスト
        """
        if min_quality is None:
            min_quality = self.MIN_QUALITY_SCORE

        approved_episodes = []
        attempt_count = 0
        max_attempts = 1000  # 安全装置

        print(f"\n🚀 Quality Gate System 起動")
        print(f"最小品質スコア: {min_quality}")
        print(f"目標生成数: {count if count else '無制限（品質優先）'}\n")

        while attempt_count < max_attempts:
            attempt_count += 1

            # エピソード候補を生成（ここは仮実装）
            candidate = self._generate_candidate()

            # 検証
            result = await self.validate_episode(candidate)

            if result.status == ApprovalStatus.APPROVED:
                episode = Episode(**candidate)
                approved_episodes.append(episode)
                print(f"✅ [{len(approved_episodes)}] {episode.person_name} "
                      f"(Score: {result.score:.2f})")

                if count and len(approved_episodes) >= count:
                    break

            elif result.status == ApprovalStatus.NEEDS_REVISION:
                print(f"🔧 要修正: {candidate['person_name']}")
                for suggestion in result.suggestions:
                    print(f"   → {suggestion}")

            else:
                print(f"❌ 却下: {candidate['person_name']}")
                if result.violations:
                    print(f"   違反: {result.violations[0]}")

        # 統計レポート
        self._generate_report(approved_episodes)

        return approved_episodes

    def _generate_candidate(self) -> Dict:
        """エピソード候補を生成（仮実装）"""
        # 実際の実装では既存のジェネレーターロジックを統合
        return {
            'person_name': 'テスト太郎',
            'person_name_display': None,
            'user_age': 30,
            'episode_age': 20,
            'episode_type': 'achievement',
            'episode_content': 'デビュー作品が大ヒット',
            'empathy_score': 8.5,
            'memory_score': 8.0,
            'record_score': 7.5,
            'weighted_score': 8.2
        }

    def _generate_report(self, approved_episodes: List[Episode]):
        """品質レポートを生成"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'statistics': self.stats,
            'approval_rate': (
                self.stats['approved'] / self.stats['total_attempts'] * 100
                if self.stats['total_attempts'] > 0 else 0
            ),
            'approved_count': len(approved_episodes),
            'average_score': (
                sum(ep.weighted_score for ep in approved_episodes) / len(approved_episodes)
                if approved_episodes else 0
            ),
            'top_violations': sorted(
                self.stats['violations_by_type'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }

        # レポートを保存
        with open('quality_gate_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n📊 品質レポート:")
        print(f"承認率: {report['approval_rate']:.1f}%")
        print(f"平均スコア: {report['average_score']:.2f}")

        if report['top_violations']:
            print(f"\n頻出違反TOP5:")
            for rule, count in report['top_violations'][:5]:
                print(f"  - {rule}: {count}回")

    def save_approved_episodes(self, episodes: List[Episode], filename: str = None):
        """承認されたエピソードをCSVで保存"""
        if not episodes:
            print("保存するエピソードがありません")
            return

        # 承認フラグを一時的に設定
        self._grant_approval()

        try:
            if filename is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"quality_gate_approved_{timestamp}.csv"

            # UTF-8 BOMでExcel対応
            with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
                fieldnames = [
                    'person_name', 'person_name_display', 'user_age',
                    'episode_age', 'episode_type', 'episode_content',
                    'empathy_score', 'memory_score', 'record_score', 'weighted_score'
                ]

                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for episode in episodes:
                    writer.writerow(episode.to_dict())

            print(f"\n✅ {len(episodes)}件のエピソードを保存: {filename}")

        finally:
            # 承認フラグをクリア
            self._clear_approval()


async def main():
    """メインエントリーポイント"""
    system = QualityGateSystem()

    # 品質保証されたエピソードを生成
    episodes = await system.generate_episodes(count=10, min_quality=8.0)

    if episodes:
        system.save_approved_episodes(episodes)
    else:
        print("品質基準を満たすエピソードが生成できませんでした")


if __name__ == "__main__":
    # 非同期実行
    asyncio.run(main())