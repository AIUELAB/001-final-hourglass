#!/usr/bin/env python3
"""
エピソード検証システム

生成されたエピソードの品質と妥当性を最終検証し、
本番環境への適合性を確認するシステム

Author: Claude
Date: 2025-09-18
Version: 1.0.0
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np

# ローカルインポート
try:
    from pdca_guardian import PDCAGuardian
    from episode_quality_evaluator import EpisodeQualityEvaluator, QualityGrade
except ImportError:
    PDCAGuardian = None
    EpisodeQualityEvaluator = None
    QualityGrade = None

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ValidationResult(Enum):
    """検証結果"""
    PASSED = "passed"          # 合格
    FAILED = "failed"          # 不合格
    WARNING = "warning"        # 警告付き合格
    NEEDS_REVIEW = "needs_review"  # 要レビュー

@dataclass
class ValidationReport:
    """検証レポート"""
    episode_id: str
    person_name: str
    age: int
    result: ValidationResult
    quality_score: float
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class EpisodeValidationSystem:
    """エピソード検証システムクラス"""

    def __init__(self, validation_config_path: str = "config/validation_config.json"):
        """
        初期化

        Args:
            validation_config_path: 検証設定ファイルのパス
        """
        self.config = self._load_validation_config(validation_config_path)
        self.pdca_guardian = PDCAGuardian() if PDCAGuardian else None
        self.quality_evaluator = EpisodeQualityEvaluator() if EpisodeQualityEvaluator else None
        self.validation_cache = {}

        # 検証ルール
        self.validation_rules = self._initialize_validation_rules()

        # 既知の有名人データ（サンプル検証用）
        self.known_persons = self._load_known_persons()

    def _load_validation_config(self, config_path: str) -> Dict[str, Any]:
        """検証設定の読み込み"""
        # デフォルト設定
        default_config = {
            "quality_threshold": 75.0,
            "strict_mode": True,
            "check_historical_accuracy": True,
            "check_emotional_appropriateness": True,
            "check_format_compliance": True,
            "check_content_appropriateness": True,
            "max_violations_allowed": 2,
            "required_grade": "B",
            "sample_validation_required": True
        }

        # ファイルから読み込み（存在する場合）
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                default_config.update(loaded_config)
        except FileNotFoundError:
            logger.info("検証設定ファイルが見つかりません。デフォルト設定を使用します。")

        return default_config

    def _initialize_validation_rules(self) -> Dict[str, Any]:
        """検証ルールの初期化"""
        rules = {
            "format_rules": {
                "required_prefix": r"あなたと同じ\d+歳のとき、.+は",
                "min_length": 100,
                "max_length": 500,
                "must_end_with": "。"
            },
            "content_rules": {
                "forbidden_words": [
                    "死亡", "自殺", "殺害", "暴力", "薬物",
                    "スキャンダル", "逮捕", "犯罪"
                ],
                "required_elements": {
                    "specificity": ["「", "」", "『", "』", r"\d+"],
                    "impact": ["初", "史上", "達成", "成功", "克服"]
                }
            },
            "quality_rules": {
                "min_specificity_score": 60,
                "min_impact_score": 60,
                "min_emotional_score": 50
            }
        }

        return rules

    def _load_known_persons(self) -> Dict[str, Dict[str, Any]]:
        """既知の有名人データ読み込み"""
        return {
            "HIKAKIN": {
                "birth_year": 1989,
                "min_recognition_score": 8.0,
                "known_achievements": ["YouTuber", "ビートボックス"]
            },
            "イチロー": {
                "birth_year": 1973,
                "min_recognition_score": 9.0,
                "known_achievements": ["メジャーリーグ", "安打記録"]
            },
            "宮崎駿": {
                "birth_year": 1941,
                "min_recognition_score": 9.0,
                "known_achievements": ["アニメ監督", "ジブリ"]
            }
        }

    def validate_episode(self, episode_data: Dict[str, Any]) -> ValidationReport:
        """
        エピソードの検証

        Args:
            episode_data: エピソードデータ

        Returns:
            検証レポート
        """
        episode_id = episode_data.get('episode_id', 'unknown')
        person_name = episode_data.get('person_name', '')
        age = episode_data.get('age', 0)
        episode_text = episode_data.get('episode_text', '')

        # キャッシュチェック
        cache_key = f"{episode_id}_{hash(episode_text)}"
        if cache_key in self.validation_cache:
            return self.validation_cache[cache_key]

        # 検証レポート初期化
        report = ValidationReport(
            episode_id=episode_id,
            person_name=person_name,
            age=age,
            result=ValidationResult.PASSED,
            quality_score=0.0
        )

        # 各検証項目の実行
        validation_checks = [
            (self._validate_format, "フォーマット検証"),
            (self._validate_content, "コンテンツ検証"),
            (self._validate_quality, "品質検証"),
            (self._validate_appropriateness, "適切性検証"),
            (self._validate_historical_accuracy, "歴史的正確性検証")
        ]

        for check_func, check_name in validation_checks:
            try:
                check_result = check_func(episode_text, episode_data, report)
                if not check_result:
                    logger.warning(f"{check_name}に失敗: {person_name} ({age}歳)")
            except Exception as e:
                logger.error(f"{check_name}エラー: {e}")
                report.violations.append(f"{check_name}エラー: {str(e)}")

        # 最終判定
        report.result = self._determine_final_result(report)

        # キャッシュ保存
        self.validation_cache[cache_key] = report

        return report

    def _validate_format(self, text: str, episode_data: Dict[str, Any],
                        report: ValidationReport) -> bool:
        """フォーマット検証"""
        if not self.config.get('check_format_compliance', True):
            return True

        rules = self.validation_rules['format_rules']
        passed = True

        # プレフィックスチェック
        if not re.match(rules['required_prefix'], text):
            report.violations.append("必須フォーマット違反: プレフィックスが不正")
            passed = False

        # 長さチェック
        if len(text) < rules['min_length']:
            report.violations.append(f"文字数不足: {len(text)}文字 (最小: {rules['min_length']})")
            passed = False
        elif len(text) > rules['max_length']:
            report.violations.append(f"文字数超過: {len(text)}文字 (最大: {rules['max_length']})")
            passed = False

        # 終端チェック
        if not text.endswith(rules['must_end_with']):
            report.warnings.append("文末が句点で終わっていません")

        # 年齢・名前の重複チェック
        age_match = re.search(r'あなたと同じ(\d+)歳のとき', text)
        if age_match:
            age_str = age_match.group(1)
            main_text = text[age_match.end():]

            if f"{age_str}歳" in main_text:
                report.violations.append("年齢の重複記載（RULE_115違反）")
                passed = False

            person_name = episode_data.get('person_name', '')
            if person_name and main_text.count(person_name) > 2:
                report.warnings.append("人名の過度な繰り返し")

        return passed

    def _validate_content(self, text: str, episode_data: Dict[str, Any],
                         report: ValidationReport) -> bool:
        """コンテンツ検証"""
        rules = self.validation_rules['content_rules']
        passed = True

        # 禁止ワードチェック
        for forbidden in rules['forbidden_words']:
            if forbidden in text:
                report.violations.append(f"不適切な内容: '{forbidden}'が含まれています")
                passed = False

        # 必須要素チェック
        has_specificity = False
        for pattern in rules['required_elements']['specificity']:
            if re.search(pattern, text):
                has_specificity = True
                break

        if not has_specificity:
            report.warnings.append("具体性が不足しています")

        # 抽象的表現チェック
        abstract_words = ['活躍', '頑張', '成長', '期待', '注目']
        abstract_count = sum(1 for word in abstract_words if word in text)
        if abstract_count > 2:
            report.warnings.append("抽象的な表現が多すぎます")

        return passed

    def _validate_quality(self, text: str, episode_data: Dict[str, Any],
                         report: ValidationReport) -> bool:
        """品質検証"""
        if not self.quality_evaluator:
            logger.warning("品質評価器が利用できません")
            return True

        # 品質評価実行
        person_data = {
            'person_id': episode_data.get('person_id', ''),
            'person_name_ja': episode_data.get('person_name', ''),
            'birth_year': episode_data.get('birth_year')
        }

        quality_result = self.quality_evaluator.evaluate_episode(text, person_data)
        report.quality_score = quality_result.total_score

        # スコアチェック
        if quality_result.total_score < self.config.get('quality_threshold', 75.0):
            report.violations.append(
                f"品質スコア不足: {quality_result.total_score:.1f} " +
                f"(必要: {self.config.get('quality_threshold', 75.0)})"
            )
            return False

        # グレードチェック
        required_grade = self.config.get('required_grade', 'B')
        grade_order = {'S': 5, 'A': 4, 'B': 3, 'C': 2, 'D': 1}

        if grade_order.get(quality_result.grade.value, 0) < grade_order.get(required_grade, 3):
            report.violations.append(
                f"グレード不足: {quality_result.grade.value} (必要: {required_grade}以上)"
            )
            return False

        # 改善提案を追加
        report.suggestions.extend(quality_result.suggestions[:3])

        return True

    def _validate_appropriateness(self, text: str, episode_data: Dict[str, Any],
                                 report: ValidationReport) -> bool:
        """適切性検証"""
        if not self.config.get('check_content_appropriateness', True):
            return True

        age = episode_data.get('age', 0)
        person_name = episode_data.get('person_name', '')

        # 年齢の妥当性
        if age < 5:
            report.warnings.append("5歳未満のエピソードは信憑性に欠ける可能性があります")
        elif age > 90:
            report.warnings.append("90歳以上のエピソードは対象読者に適さない可能性があります")

        # 感情的適切性
        if self.config.get('check_emotional_appropriateness', True):
            negative_emotions = ['死', '病', '失敗', '挫折', '苦悩']
            negative_count = sum(1 for emotion in negative_emotions if emotion in text)

            positive_emotions = ['成功', '達成', '喜び', '希望', '夢']
            positive_count = sum(1 for emotion in positive_emotions if emotion in text)

            if negative_count > positive_count * 2:
                report.warnings.append("ネガティブな内容が多すぎる可能性があります")

        return True

    def _validate_historical_accuracy(self, text: str, episode_data: Dict[str, Any],
                                     report: ValidationReport) -> bool:
        """歴史的正確性検証"""
        if not self.config.get('check_historical_accuracy', True):
            return True

        birth_year = episode_data.get('birth_year')
        age = episode_data.get('age', 0)

        if not birth_year:
            return True

        # 年代の計算
        event_year = birth_year + age

        # 時代錯誤チェック
        anachronisms = [
            ('インターネット', 1990),
            ('スマートフォン', 2007),
            ('YouTube', 2005),
            ('Twitter', 2006),
            ('AI', 1950),
            ('コンピュータ', 1940)
        ]

        for term, min_year in anachronisms:
            if term in text and event_year < min_year:
                report.violations.append(
                    f"時代錯誤: {event_year}年に'{term}'は存在しません"
                )
                return False

        return True

    def _determine_final_result(self, report: ValidationReport) -> ValidationResult:
        """最終結果判定"""
        violation_count = len(report.violations)
        warning_count = len(report.warnings)

        # 厳格モード
        if self.config.get('strict_mode', True):
            if violation_count > 0:
                return ValidationResult.FAILED
            elif warning_count > 2:
                return ValidationResult.NEEDS_REVIEW
            elif warning_count > 0:
                return ValidationResult.WARNING
            else:
                return ValidationResult.PASSED

        # 通常モード
        else:
            max_violations = self.config.get('max_violations_allowed', 2)
            if violation_count > max_violations:
                return ValidationResult.FAILED
            elif violation_count > 0:
                return ValidationResult.NEEDS_REVIEW
            elif warning_count > 3:
                return ValidationResult.WARNING
            else:
                return ValidationResult.PASSED

    def validate_batch(self, episodes: List[Dict[str, Any]]) -> pd.DataFrame:
        """バッチ検証"""
        reports = []

        for episode in episodes:
            report = self.validate_episode(episode)
            reports.append({
                'episode_id': report.episode_id,
                'person_name': report.person_name,
                'age': report.age,
                'result': report.result.value,
                'quality_score': report.quality_score,
                'violations': len(report.violations),
                'warnings': len(report.warnings),
                'violation_details': ', '.join(report.violations[:2]),
                'warning_details': ', '.join(report.warnings[:2])
            })

        return pd.DataFrame(reports)

    def validate_known_persons(self, episodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """既知の有名人での妥当性検証"""
        if not self.config.get('sample_validation_required', True):
            return {'skipped': True}

        results = {
            'passed': 0,
            'failed': 0,
            'details': []
        }

        for episode in episodes:
            person_name = episode.get('person_name', '')

            if person_name in self.known_persons:
                known_data = self.known_persons[person_name]

                # 生年チェック
                if 'birth_year' in episode and episode['birth_year'] != known_data['birth_year']:
                    results['failed'] += 1
                    results['details'].append(
                        f"{person_name}: 生年不一致 " +
                        f"(期待: {known_data['birth_year']}, 実際: {episode['birth_year']})"
                    )
                    continue

                # 認識スコアチェック
                if 'recognition_score' in episode:
                    if episode['recognition_score'] < known_data['min_recognition_score']:
                        results['failed'] += 1
                        results['details'].append(
                            f"{person_name}: 認識スコア不足 " +
                            f"(最小: {known_data['min_recognition_score']}, 実際: {episode['recognition_score']})"
                        )
                        continue

                # 成功
                results['passed'] += 1

        return results

    def generate_validation_report(self, reports_df: pd.DataFrame, output_path: str):
        """検証レポート生成"""
        summary = {
            'total_episodes': len(reports_df),
            'passed': len(reports_df[reports_df['result'] == 'passed']),
            'failed': len(reports_df[reports_df['result'] == 'failed']),
            'warning': len(reports_df[reports_df['result'] == 'warning']),
            'needs_review': len(reports_df[reports_df['result'] == 'needs_review']),
            'average_quality_score': reports_df['quality_score'].mean(),
            'pass_rate': (len(reports_df[reports_df['result'] == 'passed']) / len(reports_df)) * 100
        }

        # 違反の集計
        all_violations = []
        for details in reports_df['violation_details']:
            if details:
                all_violations.extend(details.split(', '))

        violation_counts = pd.Series(all_violations).value_counts().to_dict()

        # レポート作成
        report = {
            'timestamp': datetime.now().isoformat(),
            'config': self.config,
            'summary': summary,
            'violation_statistics': violation_counts,
            'details': reports_df.to_dict('records')
        }

        # JSON出力
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # CSV出力も
        csv_path = output_path.replace('.json', '.csv')
        reports_df.to_csv(csv_path, index=False, encoding='utf-8-sig')

        logger.info(f"検証レポートを出力: {output_path}")

        # サマリー表示
        print(f"""
=== エピソード検証サマリー ===
総エピソード数: {summary['total_episodes']}
合格: {summary['passed']} ({summary['passed'] / summary['total_episodes'] * 100:.1f}%)
不合格: {summary['failed']} ({summary['failed'] / summary['total_episodes'] * 100:.1f}%)
警告: {summary['warning']}
要レビュー: {summary['needs_review']}
平均品質スコア: {summary['average_quality_score']:.1f}
合格率: {summary['pass_rate']:.1f}%

主な違反内容:""")

        for violation, count in list(violation_counts.items())[:5]:
            print(f"  - {violation}: {count}件")


def main():
    """テスト実行"""
    validator = EpisodeValidationSystem()

    # テストエピソード
    test_episodes = [
        {
            'episode_id': 'EP001',
            'person_name': '坂本龍馬',
            'age': 30,
            'birth_year': 1836,
            'episode_text': 'あなたと同じ30歳のとき、坂本龍馬は幕府の開国派であった勝海舟を討つつもりで、赤坂・氷川神社近くの屋敷を訪れました。ところが、勝が語った世界の情勢や海軍の必要性、日本の未来像に強い衝撃を受けます。この出会いがきっかけとなり、やがて海援隊の設立や大政奉還へとつながっていきました。',
            'recognition_score': 8.5
        },
        {
            'episode_id': 'EP002',
            'person_name': 'HIKAKIN',
            'age': 25,
            'birth_year': 1989,
            'episode_text': 'あなたと同じ25歳のとき、HIKAKINはYouTubeで「ヒカキンTV」を本格始動させ、毎日動画投稿を開始しました。スーパーの店員として働きながら、深夜に動画編集を続ける日々。「Beatbox」動画が世界的に話題となり、登録者数が急増。日本のYouTuber文化の先駆者となる道を歩み始めました。',
            'recognition_score': 8.8
        },
        {
            'episode_id': 'EP003',
            'person_name': '架空の人物',
            'age': 20,
            'episode_text': 'あなたと同じ20歳のとき、架空の人物は活躍していました。',
            'recognition_score': 2.0
        }
    ]

    # バッチ検証
    reports_df = validator.validate_batch(test_episodes)

    # 結果表示
    print("\n=== 検証結果 ===")
    print(reports_df.to_string())

    # 既知人物検証
    known_results = validator.validate_known_persons(test_episodes)
    print(f"\n=== 既知人物検証 ===")
    print(f"合格: {known_results.get('passed', 0)}")
    print(f"不合格: {known_results.get('failed', 0)}")

    # レポート生成
    validator.generate_validation_report(reports_df, "validation_report.json")


if __name__ == "__main__":
    main()