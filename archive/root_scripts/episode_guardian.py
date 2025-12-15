#!/usr/bin/env python3
"""
EpisodeGuardian - 統合ルール管理・検証システム

すべてのエピソード検証ルールを一元管理し、グループ混入等の問題を防止する

著者: Claude Code
日付: 2025-10-01
バージョン: 1.0.0
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

# 既存システムのインポート
try:
    from unified_validation_system_with_persistence import (
        create_validator,
        ValidationResult as UnifiedValidationResult
    )
    UNIFIED_VALIDATOR_AVAILABLE = True
except ImportError:
    UNIFIED_VALIDATOR_AVAILABLE = False
    logging.warning("unified_validation_system_with_persistence が利用できません")

try:
    from auto_collect_bracket_metadata import FictionalCharacterDetector
    FICTIONAL_DETECTOR_AVAILABLE = True
except ImportError:
    FICTIONAL_DETECTOR_AVAILABLE = False
    logging.warning("FictionalCharacterDetector が利用できません")


class Severity(Enum):
    """ルール違反の重要度"""
    CRITICAL = "CRITICAL"  # 即座に失格
    WARNING = "WARNING"    # 警告、但し合格可能
    INFO = "INFO"          # 情報のみ


@dataclass
class ValidationResult:
    """検証結果"""
    is_valid: bool
    severity: Severity = Severity.INFO
    message: str = ""
    failed_rules: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    episode: Optional[Dict] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class EntityTypeValidator:
    """Entity Type検証（個人/グループ/架空キャラクターの区別）"""

    def __init__(self, known_groups: Set[str]):
        self.known_groups = known_groups
        self.group_keywords = [
            '結成', 'メンバー', 'バンド', '人組', 'グループ',
            'デビュー', 'コンビ', 'ユニット', 'チーム'
        ]
        # FictionalCharacterDetectorの初期化
        if FICTIONAL_DETECTOR_AVAILABLE:
            self.fictional_detector = FictionalCharacterDetector()
        else:
            self.fictional_detector = None

    def validate(self, episode: Dict) -> ValidationResult:
        """
        Entity Typeの検証

        ルール:
        0. 架空キャラクター判定 → 即座に失格（最優先）
        1. person_nameが既知のグループ名リストに含まれる → 即座に失格
        2. エピソードテキストにグループ特有の表現 → 警告
        3. 個人名パターンマッチング → 通過
        """
        person_name = episode['person_name']
        episode_text = episode.get('episode_text', '')
        category = episode.get('category', '')

        # ルール0: 架空キャラクター検出（CRITICAL - 最優先）
        if self.fictional_detector:
            entity_type, confidence = self.fictional_detector.detect_from_category(category)

            if entity_type == 'fictional_character':
                return ValidationResult(
                    is_valid=False,
                    severity=Severity.CRITICAL,
                    message=f'{person_name}は架空キャラクターです（信頼度: {confidence:.1%}）。実在人物のみ登録可能です。',
                    failed_rules=['ENTITY_TYPE_000_FICTIONAL'],
                    suggestions=[
                        'データベースのentity_typeを確認してください',
                        '架空キャラクターは別システムで管理されます'
                    ],
                    episode=episode
                )

        # ルール1: グループ名ブラックリスト（CRITICAL）
        if person_name in self.known_groups:
            return ValidationResult(
                is_valid=False,
                severity=Severity.CRITICAL,
                message=f'{person_name}はグループです。個人のみ登録可能です。',
                failed_rules=['ENTITY_TYPE_001'],
                suggestions=['個人の名前のみ使用してください'],
                episode=episode
            )

        # ルール2: グループ特有表現の検出
        detected_keywords = [kw for kw in self.group_keywords if kw in episode_text]

        if len(detected_keywords) >= 2:
            # 個人がグループを結成した話かチェック
            if 'を結成' in episode_text or 'と結成' in episode_text:
                # 個人の話 → 通過
                pass
            else:
                # グループ自体の話の可能性
                return ValidationResult(
                    is_valid=False,
                    severity=Severity.WARNING,
                    message=f'グループ関連表現を複数検出: {", ".join(detected_keywords)}',
                    failed_rules=['ENTITY_TYPE_002'],
                    suggestions=['個人の話であることを明確にしてください'],
                    episode=episode
                )

        # ルール3: 個人名パターンマッチング
        if not self._is_person_name(person_name):
            return ValidationResult(
                is_valid=False,
                severity=Severity.WARNING,
                message=f'{person_name}は個人名パターンに一致しません',
                failed_rules=['ENTITY_TYPE_003'],
                suggestions=['日本人名または海外人名のパターンを確認してください'],
                episode=episode
            )

        return ValidationResult(is_valid=True, message='Entity Type検証: 通過')

    def _is_person_name(self, name: str) -> bool:
        """個人名パターンかどうか判定"""
        # 日本人名（漢字2-5文字）
        if 2 <= len(name) <= 5:
            if any('\u4e00' <= c <= '\u9fff' for c in name):
                return True

        # 海外人名（スペース区切り）
        if ' ' in name and not any(c in name for c in ['&', 'and', 'the']):
            parts = name.split()
            if len(parts) == 2 and all(p[0].isupper() for p in parts):
                return True

        # カタカナのみ（6文字以内）
        if len(name) <= 6:
            if all('\u30A0' <= c <= '\u30FF' for c in name):
                return True

        return False


class EpisodeGuardian:
    """
    エピソードデータベースの統合ルール管理・検証システム

    すべてのルールを一元管理し、漏れなく適用する
    """

    VERSION = "1.0.0"
    LAST_UPDATED = "2025-10-01"

    def __init__(self, config_path: Optional[str] = None):
        """
        初期化

        Args:
            config_path: 設定ファイルのパス（デフォルト: episode_guardian_config.json）
        """
        self.config = self._load_config(config_path)
        self.logger = self._setup_logger()

        # 既知のグループ名を読み込み
        self.known_groups = self._load_known_groups()

        # 検証器の初期化
        self.entity_type_validator = EntityTypeValidator(self.known_groups)

        # 既存システムの統合
        if UNIFIED_VALIDATOR_AVAILABLE:
            self.unified_validator = create_validator()
        else:
            self.unified_validator = None
            self.logger.warning("統合検証システムが利用できません")

        # 統計情報
        self.metrics = {
            'total_validations': 0,
            'failed_validations': 0,
            'entity_type_failures': 0,
            'group_detections': []
        }

    def validate_episode(self, episode: Dict) -> ValidationResult:
        """
        すべてのルールを適用してエピソードを検証

        検証順序:
        1. Entity Typeチェック（最優先）
        2. 形式チェック（文字数、定型文等）
        3. 内容チェック（具体性、事実確認）

        Args:
            episode: エピソードデータ

        Returns:
            ValidationResult: 検証結果
        """
        self.metrics['total_validations'] += 1

        # 1. Entity Typeチェック（最優先・CRITICAL）
        entity_result = self.entity_type_validator.validate(episode)

        if not entity_result.is_valid and entity_result.severity == Severity.CRITICAL:
            # CRITICALの場合は即座に失格
            self.metrics['failed_validations'] += 1
            self.metrics['entity_type_failures'] += 1
            self.metrics['group_detections'].append({
                'name': episode['person_name'],
                'timestamp': datetime.now().isoformat(),
                'rule': entity_result.failed_rules[0]
            })

            self.logger.error(
                f"Entity Type検証失敗: {episode['person_name']}",
                extra={'episode': episode, 'result': entity_result}
            )

            return entity_result

        # 2. 形式チェック（既存システム + 新ルール）
        format_result = self._validate_format_rules(episode)
        if not format_result.is_valid and format_result.severity == Severity.CRITICAL:
            self.metrics['failed_validations'] += 1
            return format_result

        if self.unified_validator and self.config.get('use_unified_validator', True):
            try:
                unified_result = self.unified_validator.validate_episode(episode)

                if not unified_result.is_valid:
                    self.metrics['failed_validations'] += 1

                    return ValidationResult(
                        is_valid=False,
                        severity=Severity.CRITICAL,
                        message=f"形式検証失敗: {'; '.join([v.message for v in unified_result.violations])}",
                        failed_rules=['FORMAT_CHECK'],
                        suggestions=[],
                        episode=episode
                    )
            except Exception as e:
                self.logger.error(f"統合検証システムエラー: {e}")

        # 3. 内容チェック（新ルール）
        content_result = self._validate_content_rules(episode)
        if not content_result.is_valid and content_result.severity == Severity.CRITICAL:
            self.metrics['failed_validations'] += 1
            return content_result

        # すべての検証を通過
        self.logger.info(f"検証合格: {episode['person_name']}")
        return ValidationResult(is_valid=True, message='すべての検証を通過')

    def _load_config(self, config_path: Optional[str]) -> Dict:
        """設定ファイルを読み込み"""
        if config_path is None:
            config_path = "episode_guardian_config.json"

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # デフォルト設定
            return {
                "episode_guardian": {
                    "version": self.VERSION,
                    "strict_mode": True,
                    "use_unified_validator": True
                },
                "known_groups_sources": [
                    "group_member_database.py",
                    "manual_group_list"
                ],
                "logging": {
                    "level": "INFO",
                    "file": "logs/episode_guardian.log"
                }
            }

    def _setup_logger(self) -> logging.Logger:
        """ロガーの設定"""
        logger = logging.getLogger('EpisodeGuardian')
        logger.setLevel(self.config.get('logging', {}).get('level', 'INFO'))

        # ログファイルハンドラ
        log_file = self.config.get('logging', {}).get('file', 'logs/episode_guardian.log')
        try:
            handler = logging.FileHandler(log_file, encoding='utf-8')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        except Exception:
            # ログファイルが作成できない場合はコンソールのみ
            pass

        return logger

    def _load_known_groups(self) -> Set[str]:
        """既知のグループ名を読み込み"""
        groups = set()

        # group_member_database.pyから読み込み
        try:
            from group_member_database import GROUP_MEMBERS_DATABASE
            groups.update(GROUP_MEMBERS_DATABASE.keys())
        except ImportError:
            self.logger.warning("group_member_database.pyが読み込めません")

        # 手動リスト（ハードコード）
        groups.update([
            'サカナクション', 'XJAPAN', 'X JAPAN', 'SEKAI NO OWARI',
            "L'Arc~en~Ciel", 'BTS', 'GLAY', "B'z", 'Mr.Children',
            'EXILE', '嵐', 'ピース', 'キングコング', 'SAKEROCK',
            'BUMP OF CHICKEN', 'RADWIMPS', 'UVERworld',
            'ONE OK ROCK', 'AKB48', 'モーニング娘。'
        ])

        self.logger.info(f"既知のグループ: {len(groups)}件")
        return groups

    def get_metrics(self) -> Dict:
        """統計情報を取得"""
        return self.metrics

    def reset_metrics(self):
        """統計情報をリセット"""
        self.metrics = {
            'total_validations': 0,
            'failed_validations': 0,
            'entity_type_failures': 0,
            'group_detections': []
        }

    def _validate_format_rules(self, episode: Dict) -> ValidationResult:
        """
        フォーマット検証（FORMAT_005 + FORMAT_006「あなたと同じ」必須）

        Args:
            episode: エピソード辞書

        Returns:
            ValidationResult: 検証結果
        """
        import re

        text = episode.get('episode_text', '')
        age = episode.get('episode_age', 0)

        # FORMAT_006: 「あなたと同じ◯歳のとき」で始まるか（CRITICAL）
        expected_start = f"あなたと同じ{age}歳のとき"
        if not text.startswith(expected_start):
            return ValidationResult(
                is_valid=False,
                severity=Severity.CRITICAL,
                message=f'エピソードは「{expected_start}」で始まる必要があります',
                failed_rules=['FORMAT_006'],
                suggestions=[f'文頭を「{expected_start}」に変更してください'],
                episode=episode
            )

        # FORMAT_005: 相対的時間表現の検出（WARNING）
        try:
            from episode_guardian_rules import FORMAT_RULES
            rule = FORMAT_RULES.get('FORMAT_005')
            if rule:
                pattern = rule['pattern']
                matches = re.findall(pattern, text)

                if matches:
                    return ValidationResult(
                        is_valid=True,  # WARNINGなので合格
                        severity=Severity.WARNING,
                        message=rule['error_message'].format(matches=', '.join(matches)),
                        failed_rules=['FORMAT_005'],
                        suggestions=rule['suggestions'],
                        episode=episode
                    )
        except ImportError:
            pass

        return ValidationResult(is_valid=True, message='フォーマット検証合格')

    def _validate_content_rules(self, episode: Dict) -> ValidationResult:
        """
        CONTENT_004（定番エピソード要件）とCONTENT_005（年齢時点での事実のみ）を検証

        Args:
            episode: エピソード辞書

        Returns:
            ValidationResult: 検証結果
        """
        from episode_guardian_rules import CONTENT_RULES
        import re

        # CONTENT_005: 年齢時点での事実のみ（CRITICAL）
        rule_005 = CONTENT_RULES.get('CONTENT_005')
        if rule_005:
            text = episode.get('episode_text', '')
            patterns = rule_005['forbidden_patterns']

            matches = []
            for pattern in patterns:
                found = re.findall(pattern, text)
                matches.extend(found)

            if matches:
                return ValidationResult(
                    is_valid=False,
                    severity=Severity.CRITICAL,
                    message=rule_005['error_message'].format(matches=', '.join(matches)),
                    failed_rules=['CONTENT_005'],
                    suggestions=rule_005['suggestions'],
                    episode=episode
                )

        # CONTENT_004: 定番エピソード要件（WARNING）
        rule_004 = CONTENT_RULES.get('CONTENT_004')
        if rule_004:
            person_name = episode.get('person_name', '')
            text = episode.get('episode_text', '')

            iconic_keywords = rule_004['iconic_episodes'].get(person_name, [])

            if iconic_keywords:
                # 定番キーワードのいずれかが含まれているか確認
                has_iconic = any(keyword in text for keyword in iconic_keywords)

                if not has_iconic:
                    return ValidationResult(
                        is_valid=True,  # WARNINGなので合格
                        severity=Severity.WARNING,
                        message=rule_004['error_message'].format(
                            person_name=person_name,
                            keywords=', '.join(iconic_keywords)
                        ),
                        failed_rules=['CONTENT_004'],
                        suggestions=rule_004['suggestions'],
                        episode=episode
                    )

        return ValidationResult(is_valid=True, message='CONTENT検証合格')


def create_episode_guardian(config_path: Optional[str] = None) -> EpisodeGuardian:
    """
    EpisodeGuardianインスタンスを作成

    Args:
        config_path: 設定ファイルのパス

    Returns:
        EpisodeGuardian: インスタンス
    """
    return EpisodeGuardian(config_path)


if __name__ == "__main__":
    # デモ実行
    print("="*80)
    print("EpisodeGuardian デモ実行")
    print("="*80 + "\n")

    guardian = create_episode_guardian()

    # テストケース1: 個人（合格）
    episode_person = {
        "person_name": "羽生結弦",
        "episode_age": 19,
        "episode_text": "あなたと同じ19歳のとき、羽生結弦はソチ五輪でフィギュアスケート男子シングル金メダルを獲得した。",
        "category": "スポーツ",
        "user_age": 19
    }

    result1 = guardian.validate_episode(episode_person)
    print(f"テスト1（個人）: {result1.is_valid}")
    print(f"  メッセージ: {result1.message}\n")

    # テストケース2: グループ（失格）
    episode_group = {
        "person_name": "サカナクション",
        "episode_age": 5,
        "episode_text": "あなたがバンドを始めるとき、サカナクションは結成5年目でメジャーブレイクを果たした。",
        "category": "音楽",
        "user_age": 5
    }

    result2 = guardian.validate_episode(episode_group)
    print(f"テスト2（グループ）: {result2.is_valid}")
    print(f"  メッセージ: {result2.message}")
    print(f"  失敗ルール: {result2.failed_rules}\n")

    # 統計情報
    metrics = guardian.get_metrics()
    print("="*80)
    print("統計情報")
    print("="*80)
    print(f"総検証数: {metrics['total_validations']}")
    print(f"失敗数: {metrics['failed_validations']}")
    print(f"Entity Type失敗: {metrics['entity_type_failures']}")
    print(f"グループ検出: {len(metrics['group_detections'])}件")
