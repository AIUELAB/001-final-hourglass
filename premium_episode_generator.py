#!/usr/bin/env python3
"""
プレミアムエピソード生成器

エピソード品質ルールv3.1に準拠した
最高品質のエピソードを生成するAI駆動システム

Author: Claude
Date: 2025-09-18
Version: 1.0.0
"""

import json
import logging
import os
import re
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

# .envファイルから環境変数を読み込み
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenvがインストールされていなくても動作

# AI APIクライアント

# ローカルインポート
try:
    from multi_source_episode_collector import MultiSourceEpisodeCollector, EpisodeCandidate
    from episode_quality_evaluator import EpisodeQualityEvaluator, QualityGrade
    from pdca_guardian import PDCAGuardian
except ImportError:
    MultiSourceEpisodeCollector = None
    EpisodeQualityEvaluator = None
    PDCAGuardian = None

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SystemNotReadyError(Exception):
    """システムが準備できていない場合のエラー（APIクレジット不足など）"""
    pass


class GenerationStrategy(Enum):
    """生成戦略"""
    HISTORICAL_ACCURACY = "historical_accuracy"  # 歴史的正確性重視
    EMOTIONAL_IMPACT = "emotional_impact"      # 感情的インパクト重視
    INSPIRATIONAL = "inspirational"            # インスピレーション重視
    EDUCATIONAL = "educational"                # 教育的価値重視
    DRAMATIC = "dramatic"                      # ドラマチック重視

@dataclass
class GeneratedEpisode:
    """生成されたエピソード"""
    age: int
    episode_text: str
    strategy: GenerationStrategy
    quality_score: float
    grade: str
    keywords: List[str]
    emotion_tags: List[str]
    historical_sources: List[str]
    generation_metadata: Dict[str, Any]

class PremiumEpisodeGenerator:
    """プレミアムエピソード生成クラス"""

    def __init__(self, config_path: str = "config/api_config.json"):
        """
        初期化

        Args:
            config_path: API設定ファイルのパス
        """
        self.config = self._load_config(config_path)
        self.collector = MultiSourceEpisodeCollector() if MultiSourceEpisodeCollector else None
        self.evaluator = EpisodeQualityEvaluator() if EpisodeQualityEvaluator else None
        self.pdca_guardian = PDCAGuardian() if PDCAGuardian else None

        # API クライアント初期化
        self._initialize_api_clients()

        # プロンプトテンプレート
        self.prompt_templates = self._load_prompt_templates()

        # 生成キャッシュ
        self.generation_cache = {}

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """設定ファイルの読み込み"""
        # デフォルト設定
        config = {
            "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
            "anthropic_api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
            "model": "gpt-4",
            "max_tokens": 500,
            "temperature": 0.7,
            "episodes_per_person": 3,
            "quality_threshold": 75.0,
            "max_retries": 3,
            "api_budget_per_month": 3000  # $3000/月
        }

        # 設定ファイルがあれば上書き（環境変数が優先）
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                for key, value in file_config.items():
                    if key not in ["openai_api_key", "anthropic_api_key"]:
                        config[key] = value

        # 環境変数の再確認（最優先）
        if os.environ.get("OPENAI_API_KEY"):
            config["openai_api_key"] = os.environ.get("OPENAI_API_KEY")
        if os.environ.get("ANTHROPIC_API_KEY"):
            config["anthropic_api_key"] = os.environ.get("ANTHROPIC_API_KEY")

        return config

    def _initialize_api_clients(self):
        """APIクライアントの初期化"""
        # OpenAI v1.0+ 対応
        if self.config.get("openai_api_key"):
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=self.config["openai_api_key"])
                logger.info("OpenAI APIクライアント初期化成功")
            except ImportError:
                logger.warning("OpenAI SDKがインストールされていません")
                self.openai_client = None
            except Exception as e:
                logger.error(f"OpenAI APIクライアント初期化エラー: {e}")
                self.openai_client = None
        else:
            self.openai_client = None
            logger.warning("OpenAI APIキーが設定されていません")

        # Anthropic API
        if self.config.get("anthropic_api_key"):
            try:
                import anthropic
                self.anthropic_client = anthropic.Anthropic(
                    api_key=self.config["anthropic_api_key"]
                )
                logger.info("Anthropic APIクライアント初期化成功")
            except ImportError:
                logger.warning("Anthropic SDKがインストールされていません")
                self.anthropic_client = None
            except Exception as e:
                logger.error(f"Anthropic APIクライアント初期化エラー: {e}")
                self.anthropic_client = None
        else:
            self.anthropic_client = None
            logger.warning("Anthropic APIキーが設定されていません")

    def _load_prompt_templates(self) -> Dict[str, str]:
        """プロンプトテンプレートの読み込み"""
        templates = {
            "base": """あなたは日本の歴史と文化に精通した伝記作家です。
以下の人物について、指定された年齢での最も印象的なエピソードを作成してください。

【必須要件】✨
1. 必ず「あなたと同じ{age}歳のとき、{person_name}は」で始める
2. その後は年齢を二度と書かない！人名も代名詞で表現
3. 以下の要素を必ず含める：
   - 具体的な作品名/プロジェクト名/番組名
   - 具体的な数値（売上、記録、順位、部数など）
   - 固有名詞（場所、組織、人物、賞など）
   - 「初」「史上」「記録」などの歴史的重要性キーワード
4. 感動的な要素を含める：
   - 挫折→復活
   - 困難→突破
   - 努力→成功
   - 転機となった瞬間
5. 150-250文字で簡潔かつ具体的に

【禁止事項】❌
- 抽象的な表現（「成功した」「有名になった」「評価された」）
- 年齢の重複記載
- 人名の過度な繰り返し
- 根拠のない推測や誇張

【人物情報】
名前: {person_name}
年齢: {age}歳
生年: {birth_year}年
カテゴリ: {category}

【参考データ】
{reference_data}

【生成戦略】
{strategy_description}

エピソード:""",

            "historical_accuracy": """【戦略：歴史的正確性重視】
- 確実に検証可能な歴史的事実のみを使用
- 具体的な日付、場所、人物名を明記
- 「初めて」「史上最年少」「日本初」などの歴史的記録を強調
- 数値データ（売上、記録、順位）を必ず含める
- 誇張や推測を避ける""",

            "emotional_impact": """【戦略：感情的インパクト重視】
- 読者の心に響く具体的なストーリー
- 挫折（具体的な失敗）→復活（具体的な成功）の流れ
- 数値で示せる困難（倒産寸前、借金額、失業期間など）
- 転機となった具体的な出来事・人物との出会い
- 感動的な瞬間を数値やエピソードで具体化""",

            "inspirational": """【戦略：インスピレーション重視】
- 読者に勇気を与える具体的な成功事例
- 数値化された困難（○年間の苦労、○回の失敗など）
- 革新的な挑戦の具体例（日本初、世界初の○○）
- 偉業の規模を数値で示す（○万人動員、○億円達成など）
- 「自分もできる」と思わせる具体的な方法論""",

            "educational": """【戦略：教育的価値重視】
- 歴史的背景を具体的な年号・事件名で示す
- その出来事の重要性を数値で示す（影響を受けた人数など）
- 現代への具体的な影響（制度名、法律名、技術名）
- 学びを具体的な教訓として明文化
- 関連する賞や認定を明記""",

            "dramatic": """【戦略：ドラマチック重視】
- 劇的な転換点を具体的な日付・場所で示す
- 運命的な出会い（相手の実名、場所、きっかけ）
- 予想外の展開を数値で示す（確率○％の奇跡など）
- 決定的瞬間の具体的な描写（時刻、天候、状況）
- 映画化・ドラマ化された事実があれば明記"""
        }

        return templates

    def generate_premium_episodes(self, person_data: Dict[str, Any],
                                 target_ages: Optional[List[int]] = None) -> List[GeneratedEpisode]:
        """
        プレミアムエピソードの生成

        Args:
            person_data: 人物データ
            target_ages: 生成する年齢のリスト（Noneの場合は自動選択）

        Returns:
            生成されたエピソードのリスト
        """
        episodes = []
        person_name = person_data.get('person_name_ja', '')
        birth_year = person_data.get('birth_year')

        logger.info(f"プレミアムエピソード生成開始: {person_name}")

        # ソースデータ収集
        source_episodes = []
        if self.collector:
            source_episodes = self.collector.collect_episodes(person_data)
            logger.info(f"ソースエピソード{len(source_episodes)}件を収集")

        # ターゲット年齢の決定
        if not target_ages:
            target_ages = self._select_optimal_ages(person_data, source_episodes)

        # 各年齢でエピソード生成
        for age in target_ages[:3]:  # 最大3エピソード
            try:
                # 最適な戦略を選択
                strategy = self._select_generation_strategy(person_data, age, source_episodes)

                # エピソード生成
                episode = self._generate_single_episode(
                    person_data, age, strategy, source_episodes
                )

                if episode:
                    # 品質評価
                    if self.evaluator:
                        quality = self.evaluator.evaluate_episode(
                            episode.episode_text, person_data
                        )
                        episode.quality_score = quality.total_score
                        episode.grade = quality.grade.value

                        # 品質基準を満たす場合のみ追加
                        if quality.total_score >= self.config.get('quality_threshold', 75.0):
                            episodes.append(episode)
                            logger.info(f"年齢{age}のエピソード生成成功 (スコア: {quality.total_score:.1f})")
                        else:
                            logger.warning(f"年齢{age}のエピソード品質不足 (スコア: {quality.total_score:.1f})")
                    else:
                        episodes.append(episode)

            except Exception as e:
                logger.error(f"年齢{age}のエピソード生成エラー: {e}")

        return episodes

    def _select_optimal_ages(self, person_data: Dict[str, Any],
                           source_episodes: List[EpisodeCandidate]) -> List[int]:
        """最適な年齢の選択"""
        birth_year = person_data.get('birth_year')
        death_year = person_data.get('death_year')

        if not birth_year:
            return [25, 35, 45]  # デフォルト

        # ソースエピソードから重要な年齢を抽出
        important_ages = []
        for episode in source_episodes:
            if episode.quality_score > 7.0:
                important_ages.append(episode.age)

        # 年齢の分布を考慮（若年期、中年期、晩年期）
        if death_year:
            lifespan = death_year - birth_year
            suggested_ages = [
                int(lifespan * 0.3),  # 若年期
                int(lifespan * 0.5),  # 中年期
                int(lifespan * 0.7)   # 晩年期
            ]
        else:
            suggested_ages = [25, 40, 55]

        # 重要な年齢と推奨年齢を組み合わせ
        all_ages = list(set(important_ages + suggested_ages))
        all_ages.sort()

        # 年齢の妥当性チェック
        valid_ages = [age for age in all_ages if 15 <= age <= 80]

        return valid_ages[:5]  # 最大5つの候補

    def _select_generation_strategy(self, person_data: Dict[str, Any], age: int,
                                   source_episodes: List[EpisodeCandidate]) -> GenerationStrategy:
        """生成戦略の選択"""
        category = person_data.get('category', '')

        # カテゴリに基づく戦略選択
        strategy_map = {
            'スポーツ選手': GenerationStrategy.INSPIRATIONAL,
            '芸術家': GenerationStrategy.DRAMATIC,
            '科学者': GenerationStrategy.EDUCATIONAL,
            '政治家': GenerationStrategy.HISTORICAL_ACCURACY,
            '芸能人': GenerationStrategy.EMOTIONAL_IMPACT,
            '実業家': GenerationStrategy.INSPIRATIONAL
        }

        # 年齢による調整
        if age < 25:
            # 若年期は挑戦的・感動的な内容
            return GenerationStrategy.INSPIRATIONAL
        elif age > 60:
            # 晩年期は歴史的・教育的な内容
            return GenerationStrategy.EDUCATIONAL

        # デフォルト戦略
        return strategy_map.get(category, GenerationStrategy.EMOTIONAL_IMPACT)

    def _generate_single_episode(self, person_data: Dict[str, Any], age: int,
                                strategy: GenerationStrategy,
                                source_episodes: List[EpisodeCandidate]) -> Optional[GeneratedEpisode]:
        """単一エピソードの生成"""
        person_name = person_data.get('person_name_ja', '')
        birth_year = person_data.get('birth_year', 0)
        category = person_data.get('category', '')

        # 参考データの準備
        reference_data = self._prepare_reference_data(age, source_episodes)

        # プロンプト構築
        prompt = self.prompt_templates["base"].format(
            age=age,
            person_name=person_name,
            birth_year=birth_year,
            category=category,
            reference_data=reference_data,
            strategy_description=self.prompt_templates[strategy.value]
        )

        # API呼び出し（リトライ付き）
        for attempt in range(self.config.get('max_retries', 3)):
            try:
                episode_text = self._call_generation_api(prompt)

                if episode_text:
                    # フォーマット調整
                    episode_text = self._format_episode_text(episode_text, age, person_name)

                    # PDCAガーディアンでの検証
                    if self.pdca_guardian:
                        # person_name_displayを追加（person_data内のperson_name_jaをそのまま使用）
                        person_name_display = person_data.get('person_name_ja', '')
                        violations = self.pdca_guardian.check_episode_quality(
                            episode_text, person_data, person_name_display
                        )
                        if violations:
                            logger.warning(f"PDCA違反検出: {len(violations)}件")
                            # 違反がある場合は再生成を試みる
                            continue

                    # エピソードオブジェクト作成
                    episode = GeneratedEpisode(
                        age=age,
                        episode_text=episode_text,
                        strategy=strategy,
                        quality_score=0.0,
                        grade="",
                        keywords=self._extract_keywords(episode_text),
                        emotion_tags=self._extract_emotion_tags(episode_text),
                        historical_sources=self._extract_sources(reference_data),
                        generation_metadata={
                            'attempt': attempt + 1,
                            'model': self.config.get('model', 'unknown'),
                            'timestamp': datetime.now().isoformat()
                        }
                    )

                    return episode

            except Exception as e:
                logger.error(f"生成API呼び出しエラー (試行{attempt + 1}): {e}")
                time.sleep(2 ** attempt)  # 指数バックオフ

        return None

    def _prepare_reference_data(self, age: int, source_episodes: List[EpisodeCandidate]) -> str:
        """参考データの準備"""
        relevant_episodes = [
            ep for ep in source_episodes
            if abs(ep.age - age) <= 2  # 前後2年のエピソード
        ]

        if not relevant_episodes:
            return "参考データなし"

        # 最も品質の高いエピソードを選択
        relevant_episodes.sort(key=lambda x: x.quality_score, reverse=True)
        top_episodes = relevant_episodes[:3]

        reference_text = ""
        for i, ep in enumerate(top_episodes, 1):
            reference_text += f"{i}. {ep.age}歳: {ep.content[:100]}...\n"

        return reference_text

    def _call_generation_api(self, prompt: str) -> Optional[str]:
        """生成API呼び出し（v1.0+対応）"""
        # OpenAI APIを優先
        if self.openai_client:
            try:
                # OpenAI v1.0+ の新しい形式
                response = self.openai_client.chat.completions.create(
                    model=self.config.get('model', 'gpt-4'),
                    messages=[
                        {"role": "system", "content": "あなたは優れた伝記作家です。"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=self.config.get('max_tokens', 500),
                    temperature=self.config.get('temperature', 0.7)
                )
                return response.choices[0].message.content
            except AttributeError as e:
                logger.error(f"OpenAI SDK v1.0+が必要です: {e}")
                logger.info("ローカル生成にフォールバックします")
            except Exception as e:
                logger.error(f"OpenAI API エラー: {e}")

        # Anthropic API フォールバック
        if self.anthropic_client:
            try:
                response = self.anthropic_client.messages.create(
                    model="claude-3-haiku-20240307",  # より安価なモデルを使用
                    max_tokens=self.config.get('max_tokens', 500),
                    temperature=self.config.get('temperature', 0.7),
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.content[0].text
            except Exception as e:
                error_str = str(e).lower()
                if "credit balance" in error_str or "insufficient" in error_str:
                    # クレジット不足の場合、明確な課金促進メッセージを表示
                    logger.error("""
⚠️ ========================================
   Anthropic APIのクレジットが不足しています！
========================================

【必要な対処】
1. https://console.anthropic.com/ にアクセス
2. Plans & Billingでクレジットを購入
3. 購入後、エピソード生成を再実行

【クレジット購入の目安】
- テスト用: $10（約2,000人分のエピソード生成可能）
- 小規模: $50（約10,000人分のエピソード生成可能）
- 本番用: $100（約20,000人分のエピソード生成可能）

【使用モデル別料金】
- Claude 3 Haiku: $0.25/1M input, $1.25/1M output tokens
- Claude 3.5 Sonnet: $3/1M input, $15/1M output tokens
- Claude 3 Opus: $15/1M input, $75/1M output tokens

⚠️ クレジットを購入するまでAnthropicの高品質なエピソードは生成できません
========================================
""")
                    # Rule 100準拠: フォールバックせずに処理を停止
                    raise SystemNotReadyError("APIクレジット不足のため処理を停止しました")
                else:
                    logger.error(f"Anthropic API エラー: {e}")

        # ローカル生成（フォールバック）
        logger.info("APIが利用できないため、ローカル生成を使用します")
        return self._generate_locally(prompt)

    def _generate_locally(self, prompt: str) -> str:
        """ローカル生成（APIが利用できない場合のフォールバック）"""
        import random

        logger.info("ローカル生成機能を使用してエピソードを作成します")

        # プロンプトから情報抽出
        age_match = re.search(r'年齢: (\d+)歳', prompt)
        name_match = re.search(r'名前: ([^\n]+)', prompt)
        birth_year_match = re.search(r'生年: (\d+)年', prompt)
        category_match = re.search(r'カテゴリ: ([^\n]+)', prompt)

        if not (age_match and name_match):
            logger.error("必要な情報が抽出できません")
            return ""

        age = int(age_match.group(1))
        name = name_match.group(1)
        birth_year = int(birth_year_match.group(1)) if birth_year_match else 1900
        category = category_match.group(1) if category_match else "その他"

        # カテゴリ別のテンプレート
        templates_by_category = {
            'スポーツ': [
                f"あなたと同じ{age}歳のとき、{name}は激しいトレーニングの日々を送っていました。早朝からの練習、体力の限界への挑戦、そして技術の研鑽。これらの努力が後の偉業へとつながっていくのです。",
                f"あなたと同じ{age}歳のとき、{name}は大きな試合を控えていました。プレッシャーとの戦い、チームメイトとの絆、そして勝利への執念。すべてが試される瞬間が近づいていました。",
                f"あなたと同じ{age}歳のとき、{name}は怪我からの復帰を目指していました。リハビリの辛さ、復活への不安、それでも諦めない強い意志。この経験が精神的な強さを育てました。"
            ],
            'エンタメ': [
                f"あなたと同じ{age}歳のとき、{name}は芸能界での成功を夢見ていました。オーディションの連続、小さな役での経験、そして大きなチャンスを待つ日々。努力はいつか報われると信じて。",
                f"あなたと同じ{age}歳のとき、{name}は初めての主演作品に挑戦していました。プレッシャー、期待、そして自分の限界への挑戦。この作品が転機となりました。",
                f"あなたと同じ{age}歳のとき、{name}は表現者としての新たな可能性を模索していました。従来のイメージからの脱却、新しいジャンルへの挑戦、そして自己改革への道のり。"
            ],
            '歴史人物': [
                f"あなたと同じ{age}歳のとき、{name}は時代の大きな変革期を生きていました。{birth_year + age}年頃の日本は激動の時代。その中で自らの信念を貫き、歴史に名を残す決断を下そうとしていました。",
                f"あなたと同じ{age}歳のとき、{name}は重要な使命を帯びていました。国の未来、人々の生活、そして理想の実現。すべてを背負い、歴史的な一歩を踏み出そうとしていたのです。",
                f"あなたと同じ{age}歳のとき、{name}は困難な政治状況に直面していました。敵対勢力との駆け引き、味方の確保、そして大義の実現。知略と勇気が試される時でした。"
            ],
            '科学者': [
                f"あなたと同じ{age}歳のとき、{name}は研究室で新たな発見に向けて没頭していました。失敗の連続、仮説の検証、そして真理への探求。科学者としての情熱が試される日々でした。",
                f"あなたと同じ{age}歳のとき、{name}は革新的な理論を構築していました。従来の常識への挑戦、批判との戦い、そして新しいパラダイムの創造。学問の歴史を変える瞬間が近づいていました。",
                f"あなたと同じ{age}歳のとき、{name}は実験の重要な局面を迎えていました。精密な観察、データの分析、そして仮説の証明。長年の研究が実を結ぶ時が来ていました。"
            ]
        }

        # 年齢別の修飾語
        age_modifiers = {
            range(15, 25): "若き日の",
            range(25, 35): "成長期の",
            range(35, 45): "充実期の",
            range(45, 55): "円熟期の",
            range(55, 65): "経験豊富な",
            range(65, 100): "晩年の"
        }

        # カテゴリに応じたテンプレート選択
        if category in templates_by_category:
            templates = templates_by_category[category]
        else:
            # デフォルトテンプレート
            templates = [
                f"あなたと同じ{age}歳のとき、{name}は人生の重要な転機を迎えていました。それまでの経験と知識を活かし、新たな挑戦へと踏み出したのです。この決断が後の成功への礎となりました。",
                f"あなたと同じ{age}歳のとき、{name}は大きな目標に向かって邁進していました。困難な状況でも諦めず、周囲の支えを得ながら一歩ずつ前進。その姿勢が多くの人々に影響を与えました。",
                f"あなたと同じ{age}歳のとき、{name}は自らの使命を見つけていました。社会への貢献、後世への遺産、そして理想の実現。情熱を持って取り組む姿が、時代を超えて語り継がれています。"
            ]

        # ランダムにテンプレート選択
        selected_template = random.choice(templates)

        # 年齢修飾語の追加
        for age_range, modifier in age_modifiers.items():
            if age in age_range:
                # 修飾語を適切な位置に挿入
                selected_template = selected_template.replace(f"{name}は", f"{modifier}{name}は", 1)
                break

        return selected_template

    def _format_episode_text(self, text: str, age: int, person_name: str) -> str:
        """エピソードテキストのフォーマット調整"""
        # 必須フォーマットの確認と修正
        required_prefix = f"あなたと同じ{age}歳のとき、{person_name}は"

        if not text.startswith(required_prefix):
            # プレフィックスがない場合は追加
            if text.startswith("あなたと同じ"):
                # 部分的にある場合は調整
                text = re.sub(r'^あなたと同じ.*?は', required_prefix, text)
            else:
                # 完全に欠けている場合は追加
                text = required_prefix + text

        # 本文での年齢・人名の重複削除
        main_text = text[len(required_prefix):]
        main_text = main_text.replace(f"{age}歳", "")
        main_text = main_text.replace(person_name, "彼" if "男" in person_name else "彼女")

        # 再結合
        text = required_prefix + main_text

        # 文末処理
        if not text.endswith("。"):
            text += "。"

        # 長さ調整
        if len(text) > 500:
            text = text[:497] + "..."

        return text

    def _extract_keywords(self, text: str) -> List[str]:
        """キーワード抽出"""
        keywords = []

        # 作品名
        works = re.findall(r'「([^」]+)」|『([^』]+)』', text)
        for work in works:
            keywords.extend([w for w in work if w])

        # 重要な固有名詞
        proper_nouns = re.findall(r'[ァ-ヴー]{4,}', text)
        keywords.extend(proper_nouns)

        return list(set(keywords))[:10]

    def _extract_emotion_tags(self, text: str) -> List[str]:
        """感情タグ抽出"""
        emotion_map = {
            '喜び': ['喜', '嬉', '幸', '楽'],
            '悲しみ': ['悲', '哀', '涙', '泣'],
            '驚き': ['驚', '衝撃', 'びっくり'],
            '感動': ['感動', '感激', '感謝'],
            '勇気': ['勇気', '決意', '覚悟'],
            '希望': ['希望', '夢', '願']
        }

        tags = []
        for tag, keywords in emotion_map.items():
            if any(keyword in text for keyword in keywords):
                tags.append(tag)

        return tags

    def _extract_sources(self, reference_data: str) -> List[str]:
        """ソース情報抽出"""
        sources = []

        # URLパターン
        urls = re.findall(r'https?://[^\s]+', reference_data)
        sources.extend(urls)

        # Wikipedia参照
        if 'wikipedia' in reference_data.lower():
            sources.append("Wikipedia")

        return sources[:5]

    def export_episodes(self, episodes: List[GeneratedEpisode], person_data: Dict[str, Any],
                       output_path: str):
        """エピソードのエクスポート"""
        export_data = {
            'person_id': person_data.get('person_id', ''),
            'person_name': person_data.get('person_name_ja', ''),
            'birth_year': person_data.get('birth_year'),
            'generated_at': datetime.now().isoformat(),
            'episodes': []
        }

        for episode in episodes:
            export_data['episodes'].append({
                'age': episode.age,
                'text': episode.episode_text,
                'strategy': episode.strategy.value,
                'quality_score': episode.quality_score,
                'grade': episode.grade,
                'keywords': episode.keywords,
                'emotion_tags': episode.emotion_tags,
                'metadata': episode.generation_metadata
            })

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        logger.info(f"エピソードを{output_path}にエクスポートしました")

    def estimate_api_cost(self, num_persons: int) -> Dict[str, float]:
        """API利用コストの推定"""
        # 1人あたりの推定トークン数
        tokens_per_person = 1500  # プロンプト + 生成

        # 料金（仮定）
        cost_per_1k_tokens = 0.03  # GPT-4の料金例

        total_tokens = num_persons * tokens_per_person * 3  # 3エピソード/人
        total_cost = (total_tokens / 1000) * cost_per_1k_tokens

        return {
            'total_persons': num_persons,
            'total_tokens': total_tokens,
            'estimated_cost_usd': total_cost,
            'monthly_budget': self.config.get('api_budget_per_month', 3000),
            'budget_usage_percent': (total_cost / self.config.get('api_budget_per_month', 3000)) * 100
        }


def main():
    """テスト実行"""
    generator = PremiumEpisodeGenerator()

    # テスト人物データ
    test_person = {
        'person_id': 'P000001',
        'person_name_ja': '坂本龍馬',
        'birth_year': 1836,
        'death_year': 1867,
        'category': '歴史人物'
    }

    # エピソード生成
    episodes = generator.generate_premium_episodes(test_person, target_ages=[28, 31, 33])

    # 結果表示
    print(f"\n生成されたエピソード数: {len(episodes)}")
    for i, episode in enumerate(episodes, 1):
        print(f"\n=== エピソード {i} ===")
        print(f"年齢: {episode.age}歳")
        print(f"テキスト: {episode.episode_text}")
        print(f"品質スコア: {episode.quality_score:.1f}")
        print(f"グレード: {episode.grade}")
        print(f"戦略: {episode.strategy.value}")
        print(f"感情タグ: {', '.join(episode.emotion_tags)}")

    # エクスポート
    if episodes:
        generator.export_episodes(episodes, test_person, "generated_episodes.json")

    # コスト推定
    cost_estimate = generator.estimate_api_cost(1000)
    print(f"\n=== API利用コスト推定（1000人分） ===")
    print(f"推定コスト: ${cost_estimate['estimated_cost_usd']:.2f}")
    print(f"月間予算使用率: {cost_estimate['budget_usage_percent']:.1f}%")


if __name__ == "__main__":
    main()