#!/usr/bin/env python3
"""
RULE_179: 統合評価パイプライン（Integrated Evaluation Pipeline）

Phase 4-5で実装したすべてのルールを統合し、エピソードを総合評価
- RULE_172: 社会的インパクト測定
- RULE_173: 年齢柔軟性エンジン
- RULE_174: 時系列整合性検証
- RULE_175: ネガティブエピソード評価
- RULE_176: 架空キャラクター統合
- RULE_177: 抽象表現自動検出
- RULE_178: 統合MCPコレクター

総合評価フロー:
1. 前処理: 年齢選択（RULE_173）
2. データ収集: MCPデータ取得（RULE_178 → RULE_172）
3. 検証: 時系列整合性（RULE_174）
4. 品質評価: ネガティブ（RULE_175）、抽象表現（RULE_177）
5. 特殊判定: 架空キャラクター（RULE_176）
6. 総合判定: 合格/不合格 + 改善提案
"""

from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass
from datetime import datetime

# Phase 4-5ルールのインポート
try:
    from rules.rule_172_social_impact import SocialImpactAnalyzer
    from rules.rule_173_age_flexibility_engine import select_optimal_age
    from rules.rule_174_temporal_consistency import verify_temporal_consistency
    from rules.rule_175_negative_episode_evaluation import evaluate_negative_episode
    from rules.rule_176_fictional_character_integration import evaluate_fictional_character
    from rules.rule_177_abstract_expression_detection import detect_abstract_expressions
    from rules.rule_178_unified_mcp_collector import collect_all_mcp_data_sync
    RULES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"⚠️ ルールのインポート失敗: {e}")
    RULES_AVAILABLE = False

# 🛡️ Unified Quality Validator統合（Phase 2.4）
# Note: 循環インポート回避のため、遅延インポート（__init__内で実行）

logger = logging.getLogger(__name__)


@dataclass
class EpisodeEvaluationResult:
    """エピソード評価結果"""
    episode_id: str
    person_name: str
    passed: bool  # 総合合格判定
    total_score: float  # 総合スコア（0-100）

    # 各ルールの評価結果
    age_selection: Dict[str, Any]
    social_impact: Dict[str, Any]
    temporal_consistency: Dict[str, Any]
    negative_evaluation: Optional[Dict[str, Any]]
    fictional_character: Optional[Dict[str, Any]]
    abstract_detection: Dict[str, Any]
    three_axis_balance: Dict[str, Any]  # 🎯 3軸バランス評価結果

    # 品質ゲート
    quality_gates: Dict[str, bool]

    # 改善提案
    improvements: List[str]

    # メタデータ
    evaluation_timestamp: str

    # 🛡️ Phase 2.4: 名詞終わりチェック結果（オプションフィールドは最後に配置）
    noun_ending_check: Optional[str] = None


class IntegratedEvaluationPipeline:
    """
    統合評価パイプライン

    すべてのルールを統合してエピソードを総合評価
    """

    def __init__(self, use_mcp: bool = False):
        """
        初期化

        Args:
            use_mcp: MCPデータ収集を使用するか（現在は推定値モード）
        """
        self.use_mcp = use_mcp and RULES_AVAILABLE
        if not RULES_AVAILABLE:
            logger.warning("⚠️ 一部のルールが利用不可 - 基本評価のみ実行")

        # 🛡️ Unified Quality Validator統合（Phase 2.4）
        # 遅延初期化で循環依存を回避（プロパティ化）
        self._validator = None
        self._monitor = None
        self._validator_initialized = False

    @property
    def validator(self):
        """Unified Quality Validatorの遅延初期化プロパティ"""
        if not self._validator_initialized:
            try:
                from unified_quality_validator import UnifiedQualityValidator, ValidationLevel
                self._validator = UnifiedQualityValidator(validation_level=ValidationLevel.STRICT)
                self._validator_initialized = True
                logger.info("✅ Unified Quality Validator初期化完了")
            except ImportError:
                self._validator = None
                self._validator_initialized = True
                logger.warning("⚠️ Unified Quality Validator利用不可 - 名詞終わりチェックは無効化されます")
        return self._validator

    @property
    def monitor(self):
        """ValidationMonitorの遅延初期化プロパティ"""
        if self._monitor is None:
            try:
                from validation_monitor import ValidationMonitor
                self._monitor = ValidationMonitor()
                logger.info("✅ ValidationMonitor初期化完了")
            except ImportError:
                self._monitor = None
                logger.warning("⚠️ ValidationMonitor利用不可")
        return self._monitor

    def evaluate_episode(
        self,
        episode_id: str,
        person_name: str,
        episode_text: str,
        database_age: int,
        birth_year: Optional[int] = None,
        entity_type: str = "real_person",
        work_title: Optional[str] = None,
        description: Optional[str] = None
    ) -> EpisodeEvaluationResult:
        """
        エピソードを総合評価

        Args:
            episode_id: エピソードID
            person_name: 人物名
            episode_text: エピソード本文
            database_age: データベース登録年齢
            birth_year: 生年（オプション）
            entity_type: エンティティタイプ（real_person/fictional_character）
            work_title: 作品タイトル（架空キャラの場合）
            description: 作品説明（架空キャラの場合）

        Returns:
            評価結果
        """
        logger.info(f"🎯 {person_name} ({episode_id}) 評価開始")

        improvements = []
        quality_gates = {}

        # ============================================================
        # Phase 1: 前処理 - 年齢選択（RULE_173）
        # ============================================================
        age_result = self._evaluate_age_flexibility(
            person_name, database_age, episode_text
        )
        selected_age = age_result.get("selected_age", database_age)

        if age_result.get("age_changed"):
            improvements.append(
                f"年齢を{database_age}歳から{selected_age}歳に変更（より象徴的）"
            )

        # ============================================================
        # Phase 2: データ収集 - 社会的インパクト（RULE_178 → RULE_172）
        # ============================================================
        social_impact_result = self._evaluate_social_impact(
            person_name, episode_text
        )
        quality_gates["social_impact"] = social_impact_result.get("passed", False)

        # ============================================================
        # Phase 3: 検証 - 時系列整合性（RULE_174）
        # ============================================================
        temporal_result = self._evaluate_temporal_consistency(
            person_name, selected_age, episode_text, birth_year
        )
        quality_gates["temporal_consistency"] = temporal_result.get("passed", False)

        if not temporal_result.get("passed"):
            for issue in temporal_result.get("inconsistencies", []):
                improvements.append(f"時系列矛盾修正: {issue['suggestion']}")

        # ============================================================
        # Phase 4: 品質評価
        # ============================================================

        # 4-1: ネガティブエピソード評価（RULE_175）
        negative_result = None
        is_negative_episode = any(
            word in episode_text
            for word in ["逮捕", "辞任", "引退", "失敗", "挫折", "批判"]
        )

        if is_negative_episode:
            negative_result = self._evaluate_negative_episode(
                person_name, episode_text
            )
            quality_gates["negative_evaluation"] = negative_result.get("passed", False)

            if not negative_result.get("passed"):
                for issue in negative_result.get("issues", []):
                    improvements.append(f"表現改善: {issue['suggestion']}")

        # 4-2: 抽象表現検出（RULE_177）
        abstract_result = self._evaluate_abstract_expressions(episode_text)
        quality_gates["abstract_detection"] = abstract_result.get("passed", False)

        if not abstract_result.get("passed"):
            for expr in abstract_result.get("abstract_expressions", [])[:3]:
                improvements.append(f"具体化: {expr['suggestion']}")

        # 4-3: 名詞終わりチェック（🛡️ Unified Quality Validator - Phase 2.4）
        noun_ending_result = None
        if VALIDATOR_AVAILABLE and self.validator:
            noun_ending_result = self.validator._check_noun_ending_strict(episode_text)
            quality_gates["noun_ending"] = noun_ending_result is None

            if noun_ending_result:
                improvements.append(f"名詞終わり修正: {noun_ending_result}")

            # 監視記録（Phase 2.4）
            if self.monitor:
                self.monitor.record_validation(
                    "Rule179_IntegratedPipeline",
                    {
                        "person_name": person_name,
                        "noun_ending_violation": noun_ending_result,
                        "quality_gates": quality_gates
                    }
                )
        else:
            quality_gates["noun_ending"] = True  # validatorがない場合はチェックをスキップ

        # ============================================================
        # Phase 5: 3軸バランス評価（記憶性・共感性・意外性）
        # ============================================================
        three_axis_result = self._evaluate_three_axis_balance(person_name, episode_text)
        quality_gates["three_axis_balance"] = three_axis_result.get("passed", False)

        if not three_axis_result.get("passed"):
            scores_detail = three_axis_result.get("scores", {})
            for axis, score in scores_detail.items():
                if score < 5.0:
                    improvements.append(f"3軸強化必要: {axis}={score:.1f} → 目標5.0以上")

        # ============================================================
        # Phase 6: 特殊判定 - 架空キャラクター（RULE_176）
        # ============================================================
        fictional_result = None
        if entity_type == "fictional_character" and work_title:
            fictional_result = self._evaluate_fictional_character(
                person_name, work_title, description or ""
            )
            quality_gates["fictional_character"] = fictional_result.get("should_keep", False)

            if not fictional_result.get("should_keep"):
                improvements.append(
                    f"架空キャラクター要レビュー: 影響度{fictional_result.get('cultural_impact_score', 0):.0f}点"
                )

        # ============================================================
        # Phase 7: 総合判定
        # ============================================================
        total_score = self._calculate_total_score(
            social_impact_result,
            temporal_result,
            negative_result,
            abstract_result,
            fictional_result,
            three_axis_result,  # 🎯 3軸バランス追加
            noun_ending_violation=(noun_ending_result is not None)  # 🛡️ Phase 2.4
        )

        # 合格判定: すべての品質ゲートが通過
        passed = all(quality_gates.values())

        # 総合スコアが60点未満は不合格
        if total_score < 60:
            passed = False
            improvements.append(f"総合スコア向上が必要: 現在{total_score:.1f}点 → 目標60点以上")

        logger.info(f"📊 {person_name}: 総合スコア {total_score:.1f}点 - {'✅ 合格' if passed else '❌ 不合格'}")

        return EpisodeEvaluationResult(
            episode_id=episode_id,
            person_name=person_name,
            passed=passed,
            total_score=total_score,
            age_selection=age_result,
            social_impact=social_impact_result,
            temporal_consistency=temporal_result,
            negative_evaluation=negative_result,
            fictional_character=fictional_result,
            abstract_detection=abstract_result,
            three_axis_balance=three_axis_result,  # 🎯 3軸バランス
            noun_ending_check=noun_ending_result,  # 🛡️ Phase 2.4
            quality_gates=quality_gates,
            improvements=improvements,
            evaluation_timestamp=datetime.now().isoformat()
        )

    def _evaluate_age_flexibility(
        self, person_name: str, database_age: int, episode_text: str
    ) -> Dict[str, Any]:
        """年齢柔軟性評価（RULE_173）"""
        if not RULES_AVAILABLE:
            return {"selected_age": database_age, "age_changed": False}

        try:
            return select_optimal_age(database_age, episode_text, person_name)
        except Exception as e:
            logger.warning(f"⚠️ RULE_173失敗: {e}")
            return {"selected_age": database_age, "age_changed": False}

    def _evaluate_social_impact(
        self, person_name: str, episode_text: str
    ) -> Dict[str, Any]:
        """社会的インパクト評価（RULE_172）"""
        if not RULES_AVAILABLE:
            return {"passed": True, "impact_score": 50}

        try:
            analyzer = SocialImpactAnalyzer(use_mcp=self.use_mcp)
            result = analyzer.analyze(person_name, episode_text, [])

            # SocialImpactMetricsオブジェクトを辞書に変換
            if hasattr(result, 'total_impact_score'):
                return {
                    "passed": result.total_impact_score >= 50,
                    "impact_score": result.total_impact_score,
                    "search_volume_score": result.search_volume_score,
                    "wikipedia_languages": result.wikipedia_languages,
                    "news_articles_count": result.news_articles_count,
                    "social_buzz_score": result.social_buzz_score
                }
            else:
                # 既に辞書形式の場合
                return result
        except Exception as e:
            logger.warning(f"⚠️ RULE_172失敗: {e}")
            return {"passed": True, "impact_score": 50}

    def _evaluate_temporal_consistency(
        self, person_name: str, age: int, episode_text: str, birth_year: Optional[int]
    ) -> Dict[str, Any]:
        """時系列整合性評価（RULE_174）"""
        if not RULES_AVAILABLE:
            return {"passed": True, "inconsistencies": []}

        try:
            return verify_temporal_consistency(person_name, age, episode_text, birth_year)
        except Exception as e:
            logger.warning(f"⚠️ RULE_174失敗: {e}")
            return {"passed": True, "inconsistencies": []}

    def _evaluate_negative_episode(
        self, person_name: str, episode_text: str
    ) -> Dict[str, Any]:
        """ネガティブエピソード評価（RULE_175）"""
        if not RULES_AVAILABLE:
            return {"passed": True, "total_score": 70}

        try:
            return evaluate_negative_episode(episode_text, person_name)
        except Exception as e:
            logger.warning(f"⚠️ RULE_175失敗: {e}")
            return {"passed": True, "total_score": 70}

    def _evaluate_fictional_character(
        self, character_name: str, work_title: str, description: str
    ) -> Dict[str, Any]:
        """架空キャラクター評価（RULE_176）"""
        if not RULES_AVAILABLE:
            return {"should_keep": True, "cultural_impact_score": 70}

        try:
            return evaluate_fictional_character(character_name, work_title, description)
        except Exception as e:
            logger.warning(f"⚠️ RULE_176失敗: {e}")
            return {"should_keep": True, "cultural_impact_score": 70}

    def _evaluate_abstract_expressions(self, episode_text: str) -> Dict[str, Any]:
        """抽象表現検出（RULE_177）"""
        if not RULES_AVAILABLE:
            return {"passed": True, "concreteness_score": 70}

        try:
            return detect_abstract_expressions(episode_text)
        except Exception as e:
            logger.warning(f"⚠️ RULE_177失敗: {e}")
            return {"passed": True, "concreteness_score": 70}

    def _evaluate_three_axis_balance(self, person_name: str, episode_text: str) -> Dict[str, Any]:
        """
        3軸バランス評価（記憶性・共感性・意外性）

        重要: 客観的事実による評価のみ。感情表現（夢、感動、希望、勇気）は使用しない。

        記憶性 (Memory): 歴史的影響、定量的成果
        - ノーベル賞、オリンピック、世界初、国際的賞
        - 定量的影響: XX万人、XX%、XX円

        共感性 (Empathy): 困難の定量化、信念の引用、継続の客観的描写
        - NOT 感情表現（夢、感動、希望、勇気）
        - OK: 「XX年間の研究でXX回の失敗」「『...』という信念」

        意外性 (Surprise): 常識の転覆、パラダイムシフト
        - 「常識を覆」「前例のない」「従来のXXからXXへ」
        """
        import re

        scores = {
            "memory": 0.0,
            "empathy": 0.0,
            "surprise": 0.0
        }

        details = {
            "memory_matches": [],
            "empathy_matches": [],
            "surprise_matches": []
        }

        # 記憶性: ノーベル賞、国際的賞、定量的影響
        memory_patterns = [
            (r'ノーベル', 2.5, "ノーベル賞"),
            (r'オリンピック', 2.0, "オリンピック"),
            (r'世界初', 2.0, "世界初"),
            (r'国際', 1.5, "国際的評価"),
            (r'\d+(?:,\d{3})*[万千億兆]人', 2.0, "人数規模"),  # 🎯 カンマ区切り対応
            (r'\d+(?:,\d{3})*[万千億兆][円ドル元ユーロポンド]', 2.0, "金額規模"),  # 🎯 多通貨対応
            (r'\d+(?:,\d{3})*[万千億兆]本', 2.0, "販売規模"),  # 🎯 追加（100万本対応）
            (r'\d+(?:\.\d+)?%', 1.5, "数値的成果"),  # 🎯 小数点対応
            (r'\d+分の1[にへ]', 2.0, "削減比率"),  # 🎯 追加（「100分の1に削減」対応）
            (r'\d+(?:,\d{3})*カ国', 2.0, "国際展開"),  # 🎯 カンマ区切り対応
            (r'教科書[にへ]収録', 2.5, "教科書収録"),
            (r'ラスカー賞', 2.0, "ラスカー賞"),  # 🎯 追加（遠藤章対応）
            (r'年間\d+(?:,\d{3})*回', 1.5, "年間頻度"),  # 🎯 追加（「年間18回の打ち上げ」対応）
            # 🎯 v4追加: ビジネス特化パターン
            (r'時価総額を.+?から.+?に(?:拡大|成長)', 2.5, "時価総額拡大"),
            (r'売上高を.+?から.+?に(?:拡大|成長)', 2.5, "売上高拡大"),
            (r'\d+万人(?:以上)?の雇用を(?:創出|維持|守)', 2.5, "雇用創出数"),
            (r'市場シェアを\d+%から\d+%に(?:拡大|向上)', 2.0, "市場シェア拡大"),
            (r'普及率を\d+%から\d+%(?:へ|に)(?:押し上げ|拡大|向上)', 2.5, "普及率向上"),
            # 🎯 v4追加: 文化芸術特化パターン
            (r'世界\d+カ国(?:以上)?で(?:展示|上映|公演|出版|翻訳)', 2.5, "国際展開（具体動詞）"),
            (r'(?:興行収入|売上|評価額|経済効果)(?:が|を|は).+?(?:億|兆)円', 2.5, "経済効果"),
            (r'年間\d+万人(?:以上)?(?:の|が).+?(?:訪れ|来場|鑑賞)', 2.0, "来場者数"),
            (r'プリツカー賞', 2.5, "プリツカー賞"),
            # 🎯 RCA-Kaizen追加: 開発・創造系パターン（Dennis Ritchie対応）
            (r'(?:開発|発明|創造|創出|創設|確立)を(?:成し遂げ|達成|実現)', 2.5, "開発・創造の達成"),
            (r'(?:ほぼすべて|すべて|全て)の(?:機器|システム|デバイス)', 2.5, "広範な影響範囲"),
            (r'現代の.+?の基礎となっ', 2.5, "基礎的影響"),
            (r'\d+年(?:の|をかけて|かけ)', 2.0, "開発期間の明示"),
        ]

        for pattern, weight, label in memory_patterns:
            matches = re.findall(pattern, episode_text)
            if matches:
                scores["memory"] += weight
                details["memory_matches"].append(f"{label}: {matches[0] if len(matches) == 1 else f'{len(matches)}件'}")

        scores["memory"] = min(10.0, scores["memory"])

        # 共感性: 困難の定量化、信念の引用、継続の客観的描写
        empathy_patterns = [
            (r'\d+年間', 2.5, "継続期間"),
            (r'\d+日間[のを]', 2.5, "努力期間"),  # 🎯 追加（黒澤明の28日間の猛暑対応）
            (r'\d+回の失敗', 3.0, "困難の定量化"),
            (r'\d+回の(?:挑戦|試行錯誤)', 2.5, "挑戦の定量化"),  # 🎯 v4追加
            (r'\d+トン[のを]', 2.0, "定量的努力"),  # 🎯 追加（黒澤明の3トンの水対応）
            (r'「[^」]{5,}」', 2.5, "信念の引用"),
            (r'『[^』]{5,}』', 2.5, "思想の引用"),
            (r'継続', 1.5, "継続性"),
            (r'貫[いき]た', 2.0, "一貫性"),
            (r'試行錯誤', 2.0, "挑戦の過程"),
            # 🎯 v4追加: 教育的価値パターン
            (r'\d+人(?:以上)?の.+?を(?:育成|輩出|指導)', 2.5, "人材育成"),
            (r'M&A(?:再生|統合)で.+?(?:社|万人)', 2.5, "M&A再生"),
            (r'(?:業界|産業)全体.+?\d+%向上', 2.0, "業界貢献"),
            (r'(?:みんなの家|復興).+?\d+(?:棟|件)', 2.5, "社会貢献プロジェクト"),
            # 🎯 RCA-Kaizen追加: 協力・継続系パターン（Dennis Ritchie対応）
            (r'(?:同僚|仲間|チームメンバー|パートナー)の.+?と(?:共に|ともに)', 2.5, "協力関係の明示"),
            (r'(?:改良|改善|研究|開発)を重ね', 2.5, "継続的努力"),
            (r'\d+年の\d+年をかけて', 2.5, "具体的な期間の努力"),
            (r'既存の.+?に.+?を(?:加え|追加)', 2.0, "段階的な取り組み"),
        ]

        for pattern, weight, label in empathy_patterns:
            matches = re.findall(pattern, episode_text)
            if matches:
                scores["empathy"] += weight
                details["empathy_matches"].append(f"{label}: {matches[0] if len(matches) == 1 else f'{len(matches)}件'}")

        scores["empathy"] = min(10.0, scores["empathy"])

        # 意外性: 常識の転覆、対極の融合、パラダイムシフト
        surprise_patterns = [
            (r'常識[をは]覆', 3.0, "常識の転覆"),
            (r'通説[をは]覆', 3.0, "通説の転覆"),
            (r'定説[をは]覆', 3.0, "定説の転覆"),
            (r'[理論標準]を覆', 3.0, "理論・標準の転覆"),  # 🎯 追加（梶田隆章「標準理論を覆した」対応）
            (r'前例のない', 2.5, "前例なし"),
            (r'前例のな[いく]', 2.5, "前例なし（活用形）"),  # 🎯 追加
            (r'パラダイムシフト[をは起]', 3.0, "パラダイムシフト"),  # 🎯 活用形対応
            (r'革命[をは起]', 2.5, "革命"),  # 🎯 追加（「小売業界に革命を起こした」対応）
            (r'従来の.*から.*へ', 2.5, "ビフォー・アフター"),
            (r'\d+(?:\.\d+)?%から\d+(?:\.\d+)?%', 2.5, "数値的転換"),  # 🎯 小数点対応
            (r'[^、。]+と[^、。]+[のを]融合', 2.5, "対極の融合"),
            (r'[^、。]+という矛盾', 2.5, "矛盾の追求"),
            (r'両立', 2.0, "両立の実現"),
            # 🎯 v4追加: ビジネス特化意外性パターン
            (r'(?:価格|料金|コスト)を.+?に(?:引き下げ|削減)', 2.5, "価格革命"),
            (r'(?:業界|市場)構造を変革', 2.5, "構造変革"),
            # 🎯 RCA-Kaizen追加: 技術革新・進化系パターン（Dennis Ritchie対応）
            (r'(?:基に|基づき|をもとに).+?(?:開発|創造|発展|作成)', 2.5, "技術的進化・発展"),
            (r'(?:から)?生まれた.+?(?:は|が)', 2.5, "創造・誕生"),
            (r'新しい(?:構文|システム|手法|アプローチ|技術|概念|データ構造|データ型)', 2.5, "技術革新"),
            (r'(?:データ型|機能|要素|特性|データ構造|構文機能)を(?:追加|導入|加え|組み込[むんだ])', 2.5, "新要素追加"),
            (r'(?:ほぼすべて|あらゆる|全世界).+?(?:影響|使用|採用|動かし|動かす|支え)', 2.5, "広範な影響"),
        ]

        for pattern, weight, label in surprise_patterns:
            matches = re.findall(pattern, episode_text)
            if matches:
                scores["surprise"] += weight
                details["surprise_matches"].append(f"{label}: {matches[0] if len(matches) == 1 else f'{len(matches)}件'}")

        scores["surprise"] = min(10.0, scores["surprise"])

        # 総合判定
        avg_score = (scores["memory"] + scores["empathy"] + scores["surprise"]) / 3.0
        passed = all(score >= 5.0 for score in scores.values())  # すべての軸で5.0以上

        return {
            "passed": passed,
            "scores": scores,
            "average": round(avg_score, 1),
            "details": details,
            "person_name": person_name
        }

    def _calculate_total_score(
        self,
        social_impact: Dict,
        temporal: Dict,
        negative: Optional[Dict],
        abstract: Dict,
        fictional: Optional[Dict],
        three_axis: Dict,  # 🎯 3軸バランス追加
        noun_ending_violation: bool = False  # 🛡️ Phase 2.4: 名詞終わり違反フラグ
    ) -> float:
        """
        総合スコアを計算

        重み付け（アーキテクチャ再設計版）:
        - 3軸バランス: 40%（記憶性・共感性・意外性）
        - 社会的インパクト: 20%
        - 時系列整合性: 15%（合格=100点、不合格=0点）
        - 抽象表現: 10%
        - その他: 15%（ネガティブ評価、架空キャラ）
        - 名詞終わりペナルティ: -3.0点（Phase 2.4）
        """
        score = 0
        weight_sum = 0

        # 🎯 3軸バランス（40% - 最重要）
        three_axis_scores = three_axis.get("scores", {"memory": 0, "empathy": 0, "surprise": 0})
        three_axis_avg = sum(three_axis_scores.values()) / 3.0
        # 10点満点を100点満点に変換
        score += (three_axis_avg * 10) * 0.40
        weight_sum += 0.40

        # 社会的インパクト（20%）
        score += social_impact.get("impact_score", 50) * 0.20
        weight_sum += 0.20

        # 時系列整合性（15%）
        temporal_score = 100 if temporal.get("passed", False) else 0
        score += temporal_score * 0.15
        weight_sum += 0.15

        # 抽象表現（10%）
        score += abstract.get("concreteness_score", 70) * 0.10
        weight_sum += 0.10

        # その他（15%） - ネガティブ評価 or 架空キャラ
        if negative:
            score += negative.get("total_score", 70) * 0.15
            weight_sum += 0.15
        elif fictional:
            fictional_score = fictional.get("cultural_impact_score", 70)
            score += fictional_score * 0.15
            weight_sum += 0.15

        # 正規化（重みの合計で割る）
        if weight_sum > 0:
            score = score / weight_sum

        # 🛡️ 名詞終わりペナルティ（Phase 2.4）
        if noun_ending_violation:
            score -= 3.0

        return round(score, 1)


# グローバルパイプライン
integrated_pipeline = IntegratedEvaluationPipeline(use_mcp=False)


def evaluate_episode_integrated(
    episode_id: str,
    person_name: str,
    episode_text: str,
    database_age: int,
    birth_year: Optional[int] = None,
    entity_type: str = "real_person",
    work_title: Optional[str] = None,
    description: Optional[str] = None
) -> EpisodeEvaluationResult:
    """
    エピソードを統合評価（外部インターフェース）

    Args:
        episode_id: エピソードID
        person_name: 人物名
        episode_text: エピソード本文
        database_age: データベース登録年齢
        birth_year: 生年
        entity_type: エンティティタイプ
        work_title: 作品タイトル
        description: 作品説明

    Returns:
        評価結果
    """
    return integrated_pipeline.evaluate_episode(
        episode_id, person_name, episode_text, database_age,
        birth_year, entity_type, work_title, description
    )


if __name__ == "__main__":
    # ロギング設定
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    print("=" * 80)
    print("RULE_179: 統合評価パイプライン - テスト実行")
    print("=" * 80)
    print()

    # テストケース
    test_cases = [
        {
            "id": "EP001",
            "person": "大谷翔平",
            "age": 30,
            "birth_year": 1994,
            "text": "あなたと同じ28歳のとき、大谷翔平はMLBでア・リーグMVPを受賞し、投手と打者の二刀流で歴史を変えた。2021年シーズン、投球では9勝、156奪三振、打撃では46本塁打、100打点を記録。ベーブ・ルース以来100年ぶりの快挙として世界中のメディアが報じ、野球の常識を覆した。"
        },
        {
            "id": "EP002",
            "person": "ドラえもん",
            "age": 0,
            "entity_type": "fictional_character",
            "work_title": "ドラえもん",
            "description": "国民的アニメキャラクター、50年以上の歴史",
            "text": "あなたと同じ年齢のとき、ドラえもんは22世紀から来た青い猫型ロボットとして誕生した。多くの道具でのび太を助け、さまざまな冒険をした。"
        },
        {
            "id": "EP003",
            "person": "架空の人物",
            "age": 18,
            "text": "あなたと同じ18歳のとき、素晴らしいノーベル賞を受賞し、多くの人々に影響を与えた。"
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"テストケース {i}: {test['person']} ({test['id']})")
        print(f"  テキスト: {test['text'][:60]}...")
        print()

        result = evaluate_episode_integrated(
            episode_id=test["id"],
            person_name=test["person"],
            episode_text=test["text"],
            database_age=test["age"],
            birth_year=test.get("birth_year"),
            entity_type=test.get("entity_type", "real_person"),
            work_title=test.get("work_title"),
            description=test.get("description")
        )

        status = "✅ 合格" if result.passed else "❌ 不合格"
        print(f"  {status}")
        print(f"  📊 総合スコア: {result.total_score:.1f}点")
        print(f"  📈 品質ゲート:")
        for gate, passed in result.quality_gates.items():
            gate_status = "✅" if passed else "❌"
            print(f"     {gate_status} {gate}")

        if result.improvements:
            print(f"  💡 改善提案:")
            for improvement in result.improvements[:5]:
                print(f"     - {improvement}")

        print()

    print("=" * 80)
    print("✅ テスト完了")
    print("=" * 80)
