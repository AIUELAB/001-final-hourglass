"""
Episode Generation Bridge - 品質ゲート統合エピソード生成

このモジュールはEpisodeGeneratorと品質ゲートシステムを統合し、
高品質なエピソードを生成します。

3層品質ゲート:
    Layer 1: EpisodeValidator (8種類の検証)
    Layer 2: FactChecker (事実関係・時系列チェック)
    Layer 3: TemplateBlocker (70+パターンのテンプレート検出)

使用方法:
    >>> from src.episode_generation_bridge import EpisodeGenerationBridge
    >>> bridge = EpisodeGenerationBridge(api_key="your-api-key")
    >>> person_data = {"person_name": "山中伸弥", "category": "科学・技術", ...}
    >>> episodes = bridge.generate_for_person(person_data, episodes_count=2)
"""

import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from src.episode_generator import EpisodeGenerator

# ロガー設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EpisodeGenerationBridge:
    """品質ゲート統合エピソード生成ブリッジ"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5"):
        """
        Args:
            api_key: Anthropic API key
            model: Claude model name
        """
        self.generator = EpisodeGenerator(api_key=api_key, model=model)

        # 品質ゲートモジュールを遅延ロード
        self.episode_validator: Optional[Callable] = None
        self.fact_checker: Optional[Any] = None
        self.template_blocker: Optional[Any] = None

    def _load_quality_gates(self):
        """品質ゲートモジュールを遅延ロード"""
        if self.episode_validator is None:
            import sys
            from pathlib import Path

            # scripts/validation/ を sys.path に追加
            sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "validation"))

            from episode_validator import validate_episode

            self.episode_validator = validate_episode

        if self.fact_checker is None:
            from src.fact_checker import FactChecker

            self.fact_checker = FactChecker()

        if self.template_blocker is None:
            from episode_quality_system.template_blocker import TemplateBlocker

            self.template_blocker = TemplateBlocker()

    def generate_for_person(
        self,
        person_data: Dict[str, Any],
        episodes_count: int = 2,
        max_retries: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        1人あたり複数エピソードを生成（品質ゲート通過後）

        Args:
            person_data: 人物データ辞書（person_name, category, person_type, birth_year, death_year）
            episodes_count: 生成本数（1-3推奨）
            max_retries: 品質ゲート失敗時のリトライ回数

        Returns:
            品質ゲート合格エピソードのリスト

        Example:
            >>> bridge = EpisodeGenerationBridge(api_key="...")
            >>> person_data = {
            ...     "person_name": "山中伸弥",
            ...     "category": "科学・技術",
            ...     "person_type": "REAL",
            ...     "birth_year": 1962,
            ...     "death_year": None
            ... }
            >>> episodes = bridge.generate_for_person(person_data, episodes_count=2)
        """
        # 品質ゲートをロード
        self._load_quality_gates()

        # 品質ゲートの初期化確認
        if self.episode_validator is None:
            raise RuntimeError("episode_validator not loaded")
        if self.fact_checker is None:
            raise RuntimeError("fact_checker not loaded")
        if self.template_blocker is None:
            raise RuntimeError("template_blocker not loaded")

        # preferred_age が指定されている場合、その年齢のみで生成（valid_agesの計算をスキップ）
        preferred_age = person_data.get("preferred_age")
        if preferred_age is not None:
            logger.info(
                f"{person_data['person_name']}: preferred_age={preferred_age} が指定されているため、"
                f"この年齢のみで{episodes_count}件のエピソード生成を開始"
            )

            # preferred_age指定時は、person_typeやbirth_yearに関わらず、指定年齢を優先
            # （FICTIONAL型でbirth_year未設定でも、preferred_ageが優先される）
            logger.info(
                f"{person_data['person_name']}: preferred_age={preferred_age} が指定されているため、"
                f"birth_year/death_yearの年齢範囲チェックをバイパスして生成"
            )
            # preferred_age のみで episodes_count 回生成
            selected_ages = [preferred_age] * episodes_count
        else:
            # preferred_age未指定の場合のみ、有効な年齢範囲を計算
            valid_ages = self._calculate_valid_age_range(person_data)
            if not valid_ages:
                logger.warning(f"{person_data['person_name']}: 有効な年齢範囲がありません")
                return []

            # 既存の年齢選択ロジック（異なる年齢で生成）
            # 優先度ベースの年齢選択を使用
            selected_ages = self._select_ages_with_priority(valid_ages, episodes_count)

        logger.info(
            f"{person_data['person_name']}: {len(selected_ages)}件のエピソード生成を開始 (年齢: {selected_ages})"
        )

        episodes = []
        failed_ages = []  # 失敗した年齢を記録

        # 選択された年齢で生成
        for age in selected_ages:
            # リトライロジック付きでエピソード生成
            episode = self._generate_single_episode_with_retry(person_data, age, max_retries)
            if episode:
                episodes.append(episode)
            else:
                failed_ages.append(age)

        # Fallbackメカニズム: 失敗した場合、代替年齢で再試行
        # preferred_age指定時は、Fallbackしない（指定年齢のみで生成）
        # Note: preferred_age is None の場合のみこのブロックに入るため、valid_agesは必ず定義済み
        if failed_ages and len(episodes) < episodes_count and preferred_age is None:
            remaining_ages = [a for a in valid_ages if a not in selected_ages and a not in failed_ages]

            if remaining_ages:
                fallback_count = episodes_count - len(episodes)
                # 優先度順に代替年齢を選択
                fallback_ages = self._select_ages_with_priority(remaining_ages, fallback_count)

                logger.info(f"{person_data['person_name']}: Fallbackモード - 代替年齢で再試行 (年齢: {fallback_ages})")

                for age in fallback_ages:
                    episode = self._generate_single_episode_with_retry(person_data, age, max_retries)
                    if episode:
                        episodes.append(episode)

        logger.info(f"{person_data['person_name']}: {len(episodes)}/{len(selected_ages)}件のエピソード生成成功")

        return episodes

    def _generate_single_episode_with_retry(
        self,
        person_data: Dict[str, Any],
        age: int,
        max_retries: int,
    ) -> Optional[Dict[str, Any]]:
        """
        リトライロジック付きで1本のエピソードを生成

        Args:
            person_data: 人物データ
            age: 年齢
            max_retries: 最大リトライ回数

        Returns:
            品質ゲート合格エピソード、または None
        """
        # 品質ゲートの初期化確認
        if self.episode_validator is None:
            raise RuntimeError("episode_validator not initialized")
        if self.fact_checker is None:
            raise RuntimeError("fact_checker not initialized")
        if self.template_blocker is None:
            raise RuntimeError("template_blocker not initialized")

        for attempt in range(max_retries):
            try:
                # エピソード生成
                episode = self._generate_single_episode(person_data, age)
                if not episode:
                    continue

                # 品質ゲート Layer 1: EpisodeValidator
                validation_issues = self.episode_validator(episode)
                critical_issues = [issue for issue in validation_issues if issue.severity == "CRITICAL"]
                if critical_issues:
                    logger.warning(
                        f"{person_data['person_name']} ({age}歳) Attempt {attempt + 1}/{max_retries}: "
                        f"EpisodeValidator rejected - {[issue.message for issue in critical_issues]}"
                    )
                    continue

                # 品質ゲート Layer 2: FactChecker
                fact_check_report = self.fact_checker.check_episode(
                    person_id=episode.get("person_id", ""),
                    person_name=episode.get("person_name", ""),
                    episode_text=episode.get("episode_text", ""),
                    birth_year=person_data.get("birth_year"),
                    metadata=episode,
                )
                critical_violations = [v for v in fact_check_report.violations if v.severity == "CRITICAL"]
                if critical_violations:
                    logger.warning(
                        f"{person_data['person_name']} ({age}歳) Attempt {attempt + 1}/{max_retries}: "
                        f"FactChecker rejected - {[v.message for v in critical_violations]}"
                    )
                    continue

                # 品質ゲート Layer 2.5: EpisodeNameValidator
                from src.validators.episode_name_validator import validate_episode_name, ValidationResult
                import re as re_module

                name_validation = validate_episode_name(
                    episode.get("person_name", ""), episode.get("episode_text", ""), strict=False
                )
                if name_validation.result == ValidationResult.MISMATCH and name_validation.text_name:
                    # 自動修正
                    original_text = episode["episode_text"]
                    episode["episode_text"] = re_module.sub(
                        rf"^(あなたと同じ[\d.]+歳のとき、){re_module.escape(name_validation.text_name)}((?:『.+?』)?は)",
                        rf"\1{episode['person_name']}\2",
                        original_text,
                    )
                    logger.info(
                        f"{person_data['person_name']} ({age}歳): "
                        f"人物名自動修正 {name_validation.text_name} → {episode['person_name']}"
                    )

                # 品質ゲート Layer 3: TemplateBlocker
                is_template, violations = self.template_blocker.check_episode(
                    episode_text=episode["episode_text"],
                    person_type=person_data.get("person_type", "REAL"),
                )
                if is_template:
                    logger.warning(
                        f"{person_data['person_name']} ({age}歳) Attempt {attempt + 1}/{max_retries}: "
                        f"TemplateBlocker rejected - {[v.pattern for v in violations]}"
                    )
                    continue

                # 全品質ゲート通過
                logger.info(f"{person_data['person_name']} ({age}歳): 品質ゲート通過 ({attempt + 1}回目)")
                return episode

            except Exception as e:
                logger.error(
                    f"{person_data['person_name']} ({age}歳) Attempt {attempt + 1}/{max_retries}: 生成エラー - {e}"
                )
                continue

        # max_retries回失敗した場合
        logger.error(f"{person_data['person_name']} ({age}歳): {max_retries}回リトライしたが品質ゲート通過できず")
        return None

    def _generate_single_episode(
        self,
        person_data: Dict[str, Any],
        age: int,
    ) -> Optional[Dict[str, Any]]:
        """
        1本のエピソードを生成

        Args:
            person_data: 人物データ
            age: 年齢

        Returns:
            エピソードデータ、または None
        """
        try:
            # award情報を取得（オプション）
            award_name = person_data.get("award_name")
            award_year = person_data.get("award_year")

            # エピソード生成
            episode = self.generator.generate(
                person_data=person_data,
                age=age,
                award_name=award_name,
                award_year=award_year,
            )

            return episode

        except Exception as e:
            logger.error(f"エピソード生成失敗: {person_data['person_name']} ({age}歳) - {e}")
            return None

    def _calculate_valid_age_range(self, person_data: Dict[str, Any]) -> List[int]:
        """
        有効な年齢範囲を計算（birth_year/death_yearから）

        Args:
            person_data: 人物データ

        Returns:
            有効な年齢のリスト

        Example:
            >>> bridge._calculate_valid_age_range({"birth_year": 1962, "death_year": None})
            [10, 11, 12, ..., 62, 63]  # 2025年現在63歳
        """
        birth_year = person_data.get("birth_year")
        death_year = person_data.get("death_year")

        if not birth_year:
            # birth_year不明の場合はデフォルト範囲（20-60歳）
            logger.warning(f"{person_data['person_name']}: birth_year不明、デフォルト範囲（20-60歳）を使用")
            return list(range(20, 61))

        current_year = datetime.now().year
        max_year = death_year if death_year else current_year

        # 有効年齢範囲: 10歳〜（death_year or 現在年）- birth_year
        min_age = 10
        max_age = min(max_year - birth_year, 90)

        if max_age < min_age:
            logger.warning(f"{person_data['person_name']}: max_age ({max_age}) < min_age ({min_age})")
            return []

        return list(range(min_age, max_age + 1))

    def _select_ages(self, valid_ages: List[int], count: int) -> List[int]:
        """
        年齢を選択（分散させる）

        Args:
            valid_ages: 有効な年齢のリスト
            count: 選択する数

        Returns:
            選択された年齢のリスト

        Example:
            >>> bridge._select_ages([20, 21, 22, ..., 60], 3)
            [25, 42, 58]  # 均等に分散
        """
        if not valid_ages:
            return []

        if len(valid_ages) <= count:
            return valid_ages

        # 均等に分散させる
        step = len(valid_ages) / count
        selected = [valid_ages[int(i * step)] for i in range(count)]

        # 重複を避けるため、念のためユニーク化
        selected = list(dict.fromkeys(selected))

        return selected

    def _select_ages_with_priority(self, valid_ages: List[int], count: int) -> List[int]:
        """
        年齢選択（優先度戦略）

        優先順位:
        1. 20代-30代（キャリア形成期）- 優先度: 高
        2. 10代（成長期）- 優先度: 中
        3. 40代以上（成熟期）- 優先度: 低

        Args:
            valid_ages: 有効な年齢のリスト
            count: 選択する数

        Returns:
            選択された年齢のリスト（優先度順）

        Example:
            >>> bridge._select_ages_with_priority([10, 11, ..., 22], 1)
            [21]  # 20代の中央値
            >>> bridge._select_ages_with_priority([10, 11, ..., 22], 2)
            [21, 15]  # 20代と10代の中央値
        """
        if not valid_ages:
            return []

        if len(valid_ages) <= count:
            return valid_ages

        # 年齢を優先度グループに分類
        prime = [a for a in valid_ages if 20 <= a <= 39]  # 優先度: 高
        teen = [a for a in valid_ages if 10 <= a <= 19]  # 優先度: 中
        mature = [a for a in valid_ages if a >= 40]  # 優先度: 低

        # 優先度順にサンプリング
        selected: List[int] = []
        for ages in [prime, teen, mature]:
            if ages and len(selected) < count:
                if count == 1 or len(selected) == count - 1:
                    # 1つだけ選ぶ場合、または最後の1つを選ぶ場合は中央値
                    median_idx = len(ages) // 2
                    selected.append(ages[median_idx])
                else:
                    # 複数選ぶ場合は均等分散
                    sample_count = min(count - len(selected), len(ages))
                    step = len(ages) / sample_count
                    for i in range(sample_count):
                        idx = int(i * step)
                        if idx < len(ages):
                            selected.append(ages[idx])

        return selected[:count]


if __name__ == "__main__":
    # 動作確認用
    import os

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY環境変数が設定されていません")
        exit(1)

    bridge = EpisodeGenerationBridge(api_key=api_key)

    # テストデータ
    person_data = {
        "person_name": "山中伸弥",
        "category": "科学・技術",
        "person_type": "REAL",
        "birth_year": 1962,
        "death_year": None,
    }

    print(f"エピソード生成ブリッジテスト: {person_data['person_name']}")

    # 年齢範囲計算テスト
    valid_ages = bridge._calculate_valid_age_range(person_data)
    print(f"\n有効な年齢範囲: {min(valid_ages)}-{max(valid_ages)}歳 ({len(valid_ages)}個)")

    # 年齢選択テスト
    selected_ages = bridge._select_ages(valid_ages, 3)
    print(f"選択された年齢: {selected_ages}")

    # エピソード生成テスト（実際にLLM呼び出し）
    print(f"\n{len(selected_ages)}件のエピソード生成中...")
    episodes = bridge.generate_for_person(person_data, episodes_count=2)

    print(f"\n生成成功: {len(episodes)}件")
    for i, episode in enumerate(episodes, 1):
        print(f"\nエピソード{i}:")
        print(f"  年齢: {episode['age']}歳")
        print(f"  テキスト: {episode['episode_text'][:80]}...")
        print(f"  文字数: {episode['char_count']}")
        print(f"  composite_score: {episode['composite_score']:.2f}")
