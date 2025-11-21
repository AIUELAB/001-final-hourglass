#!/usr/bin/env python3
"""
RULE_172: 社会的インパクト測定システム

MCPサーバー（brave-search, firecrawl）を活用した客観的データ収集
- Googleトレンドスコア（検索ボリューム）
- Wikipedia編集履歴と言語数
- ニュース記事数
- SNSバズ度（推定）

Phase 4.1: MCP統合対応
- use_mcp=True: 実データ取得（brave-search）
- use_mcp=False: 推定値使用（フォールバック）
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import re
import logging

# Phase 4.1: MCP統合モジュール
try:
    from rules.rule_172_mcp_integration import get_real_social_impact_data_sync
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class SocialImpactMetrics:
    """社会的インパクトメトリクス"""
    search_volume_score: int  # 検索ボリュームスコア（0-100）
    wikipedia_languages: int  # Wikipedia言語数
    news_articles_count: int  # ニュース記事数（推定）
    social_buzz_score: int    # SNSバズ度（推定0-100）
    total_impact_score: float # 総合インパクトスコア
    evidence: List[str]


class SocialImpactAnalyzer:
    """
    社会的インパクト分析エンジン

    Phase 4.1: MCP統合実装済み
    - use_mcp=True: brave-searchで実データ取得
    - use_mcp=False: テキスト解析による推定値使用（フォールバック）
    """

    # 影響度判定基準
    HIGH_IMPACT_THRESHOLD = 80
    MEDIUM_IMPACT_THRESHOLD = 50
    LOW_IMPACT_THRESHOLD = 30

    def __init__(self, use_mcp: bool = True):
        """
        初期化

        Args:
            use_mcp: MCPサーバーを使用するか（デフォルト: True）
        """
        self.use_mcp = use_mcp and MCP_AVAILABLE
        if self.use_mcp:
            logger.info("✅ RULE_172: MCP統合モード（実データ取得）")
        else:
            logger.info("⚠️ RULE_172: 推定モード（テキスト解析）")

    def estimate_search_volume(self, person_name: str, episode_keywords: List[str]) -> int:
        """
        検索ボリュームを推定（Phase 2: テキストベース、Phase 3: MCP統合）

        Args:
            person_name: 人物名
            episode_keywords: エピソードキーワード

        Returns:
            検索ボリュームスコア（0-100）
        """
        # Phase 2: キーワードベース推定
        # RULE_200: ギネス・世界記録キーワード追加（石ノ森章太郎事例対応）
        high_volume_keywords = [
            "ノーベル賞", "オリンピック", "ワールドカップ", "金メダル",
            "世界記録", "MVP", "世界選手権", "アカデミー賞",
            # RULE_200追加キーワード
            "ギネス", "ギネス世界記録", "ギネスブック", "世界最多", "史上最多",
            "世界初", "日本初", "史上初", "世界一", "日本一",
            "文化勲章", "紫綬褒章", "国民栄誉賞", "人間国宝",
            "殿堂入り", "レジェンド", "パイオニア"
        ]

        medium_volume_keywords = [
            "受賞", "優勝", "金獅子賞", "初", "記録", "逮捕",
            "社会現象", "ベストセラー", "億", "創業"
        ]

        score = 60  # ベーススコア（上げる）

        for keyword in episode_keywords:
            if keyword in high_volume_keywords:
                score += 20  # 増加
            elif keyword in medium_volume_keywords:
                score += 10

        return min(score, 100)

    def estimate_wikipedia_impact(self, person_name: str, episode_text: str) -> int:
        """
        Wikipedia影響度を推定（言語数の代理指標）

        Args:
            person_name: 人物名
            episode_text: エピソード本文

        Returns:
            推定Wikipedia言語数（1-50）
        """
        # 国際的なキーワードがあれば多言語と推定
        international_keywords = [
            "世界", "国際", "グローバル", "ノーベル", "オリンピック",
            "アカデミー", "ワールド", "海外", "外国"
        ]

        # 日本語のみのキーワード
        domestic_keywords = ["日本", "国内", "東京", "日本人"]

        international_count = sum(1 for kw in international_keywords if kw in episode_text)
        domestic_count = sum(1 for kw in domestic_keywords if kw in episode_text)

        if international_count >= 2:
            return 20  # 20言語以上と推定
        elif international_count >= 1:
            return 10  # 10言語程度
        else:
            return 3   # 日本語+英語+アルファ

    def estimate_news_coverage(self, episode_text: str) -> int:
        """
        ニュース記事数を推定

        Args:
            episode_text: エピソード本文

        Returns:
            推定記事数
        """
        # 社会的影響の大きさから推定
        major_event_keywords = [
            "衝撃", "社会現象", "話題", "注目", "初めて", "記録",
            "逮捕", "受賞", "優勝", "革新"
        ]

        count = sum(1 for kw in major_event_keywords if kw in episode_text)

        # 推定記事数
        if count >= 3:
            return 1000  # 大きなニュース
        elif count >= 2:
            return 500
        elif count >= 1:
            return 100
        else:
            return 50

    def estimate_social_buzz(self, episode_text: str) -> int:
        """
        SNSバズ度を推定

        Args:
            episode_text: エピソード本文

        Returns:
            バズ度スコア（0-100）
        """
        # バズりやすいキーワード
        viral_keywords = [
            "社会現象", "一夜にして", "バズ", "話題", "再生回数",
            "万人", "億回", "YouTube", "Twitter", "SNS", "CM"
        ]

        # 数値が含まれているか（バズの証拠）
        has_numbers = bool(re.search(r'\d+億|\d+万', episode_text))

        score = 30  # ベーススコア

        for keyword in viral_keywords:
            if keyword in episode_text:
                score += 15

        if has_numbers:
            score += 20

        return min(score, 100)

    def analyze(
        self,
        person_name: str,
        episode_text: str,
        episode_keywords: Optional[List[str]] = None
    ) -> SocialImpactMetrics:
        """
        社会的インパクトを分析

        Args:
            person_name: 人物名
            episode_text: エピソード本文
            episode_keywords: エピソードキーワード

        Returns:
            社会的インパクトメトリクス
        """
        if episode_keywords is None:
            # テキストから簡易的にキーワード抽出
            episode_keywords = [
                word for word in [
                    "ノーベル賞", "オリンピック", "金メダル", "受賞",
                    "逮捕", "社会現象", "ベストセラー", "創業"
                ] if word in episode_text
            ]

        # Phase 4.1: MCP統合による実データ取得
        if self.use_mcp:
            try:
                # MCPサーバーから実データ取得
                event_keywords = " ".join(episode_keywords[:3])  # 上位3キーワード
                mcp_data = get_real_social_impact_data_sync(person_name, event_keywords)

                search_score = mcp_data['search_volume_score']
                wiki_languages = mcp_data['wikipedia_languages']
                news_count = mcp_data['news_articles_count']
                data_source = "実データ（MCP）"
                logger.info(f"✅ {person_name}: MCP実データ取得成功")

            except Exception as e:
                logger.warning(f"⚠️ MCP失敗、推定値にフォールバック: {e}")
                self.use_mcp = False  # 一時的に推定モードに切り替え

        # 推定値モード（フォールバック）
        if not self.use_mcp:
            search_score = self.estimate_search_volume(person_name, episode_keywords)
            wiki_languages = self.estimate_wikipedia_impact(person_name, episode_text)
            news_count = self.estimate_news_coverage(episode_text)
            data_source = "推定値（テキスト解析）"

        # SNSバズ度は常にテキスト解析（MCPサーバー未対応）
        buzz_score = self.estimate_social_buzz(episode_text)

        # 総合スコア計算（重み付け平均、より寛容に）
        total_score = (
            search_score * 0.4 +           # 検索ボリューム重視
            min(wiki_languages * 3, 100) * 0.2 +  # Wikipedia影響
            min(news_count / 5, 100) * 0.2 +      # ニュース記事（係数調整）
            buzz_score * 0.2               # SNSバズ度
        )

        # エビデンス収集
        evidence = [
            f"データソース: {data_source}",
            f"検索ボリューム: {search_score}点",
            f"Wikipedia言語数: {wiki_languages}言語",
            f"ニュース記事数: {news_count}件",
            f"SNSバズ度: {buzz_score}点",
            f"総合インパクトスコア: {total_score:.1f}点"
        ]

        return SocialImpactMetrics(
            search_volume_score=search_score,
            wikipedia_languages=wiki_languages,
            news_articles_count=news_count,
            social_buzz_score=buzz_score,
            total_impact_score=total_score,
            evidence=evidence
        )

    def evaluate(self, person_name: str, episode_text: str) -> Dict:
        """
        エピソードの社会的インパクトを評価

        Args:
            person_name: 人物名
            episode_text: エピソード本文

        Returns:
            評価結果
        """
        metrics = self.analyze(person_name, episode_text)

        # 判定
        if metrics.total_impact_score >= self.HIGH_IMPACT_THRESHOLD:
            impact_level = "HIGH"
            passed = True
        elif metrics.total_impact_score >= self.MEDIUM_IMPACT_THRESHOLD:
            impact_level = "MEDIUM"
            passed = True
        elif metrics.total_impact_score >= self.LOW_IMPACT_THRESHOLD:
            impact_level = "LOW"
            passed = False
        else:
            impact_level = "MINIMAL"
            passed = False

        return {
            "passed": passed,
            "impact_level": impact_level,
            "total_score": metrics.total_impact_score,
            "metrics": {
                "search_volume": metrics.search_volume_score,
                "wikipedia_languages": metrics.wikipedia_languages,
                "news_articles": metrics.news_articles_count,
                "social_buzz": metrics.social_buzz_score
            },
            "evidence": metrics.evidence,
            "threshold": self.MEDIUM_IMPACT_THRESHOLD,
            "rule_id": "RULE_172",
            "rule_name": "社会的インパクト測定"
        }


# グローバルインスタンス
impact_analyzer = SocialImpactAnalyzer()


def evaluate_social_impact(person_name: str, episode_text: str) -> Dict:
    """
    社会的インパクトを評価（外部インターフェース）

    Args:
        person_name: 人物名
        episode_text: エピソード本文

    Returns:
        評価結果
    """
    return impact_analyzer.evaluate(person_name, episode_text)


if __name__ == "__main__":
    # テストケース
    test_cases = [
        {
            "person": "大江健三郎",
            "text": "あなたと同じ59歳のとき、大江健三郎はノーベル文学賞を受賞し、日本人8人目の受賞者となった。23歳で芥川賞『飼育』から36年、知的障害の長男・光との関係を描いた『個人的な体験』『万延元年のフットボール』など、人間の尊厳を問う作品が世界的に評価された。授賞式で日本語スピーチを行い、日本文学の独自性を示した。"
        },
        {
            "person": "新垣結衣",
            "text": "あなたと同じ18歳のとき、新垣結衣は江崎グリコのポッキーCM「ポッキーダンス」に出演し、一夜にして全国区のスターとなった。沖縄から上京3年目の無名モデルが軽快なリズムで踊る姿が若者の心を掴み、社会現象に。YouTube再生回数1億回突破、ポッキー売上は前年比120%を記録した。"
        },
        {
            "person": "堀江貴文",
            "text": "あなたと同じ38歳のとき、堀江貴文は証券取引法違反で逮捕された。24歳で起業したオン・ザ・エッヂは2000年に売上高100億円、株価100倍に成長しライブドアに改称。ニッポン放送買収、プロ野球参入など次々と挑戦したが、株式分割を繰り返した資金調達が法に抵触し実刑判決を受けた。時代の寵児の転落は日本経済界に衝撃を与えた。"
        }
    ]

    print("=" * 80)
    print("RULE_172: 社会的インパクト測定システム - テスト実行")
    print("=" * 80)
    print()

    for i, test in enumerate(test_cases, 1):
        print(f"テストケース {i}: {test['person']}")
        print(f"  テキスト: {test['text'][:60]}...")
        print()

        result = evaluate_social_impact(test["person"], test["text"])

        status = "✅ 合格" if result["passed"] else "❌ 不合格"
        print(f"  {status}")
        print(f"  📊 総合スコア: {result['total_score']:.1f}点")
        print(f"  📈 インパクトレベル: {result['impact_level']}")
        print(f"  📋 メトリクス:")
        for key, value in result["metrics"].items():
            print(f"     - {key}: {value}")
        print()

    print("=" * 80)
    print("✅ テスト完了")
    print("=" * 80)
    print()
    print("Note: Phase 3でMCPサーバー（brave-search）統合予定")
