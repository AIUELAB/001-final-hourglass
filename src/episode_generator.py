"""
Episode Generator - エピソード生成ロジック

このモジュールは generate_episodes_by_age_range.py から抽出された
コア生成ロジックを提供します。

使用方法:
    >>> from src.episode_generator import EpisodeGenerator
    >>> generator = EpisodeGenerator(api_key="your-api-key")
    >>> person_data = {"person_name": "山中伸弥", "category": "科学・技術", "person_type": "REAL"}
    >>> episode = generator.generate(person_data, age=47)
"""

import hashlib
from datetime import datetime
from typing import Any, Dict, Optional

import anthropic


# 年代別プロンプトカスタマイズ辞書
AGE_PROMPTS = {
    "30s": {
        "life_stage_tag": "壮年期の挑戦",
        "description": "キャリア確立期",
        "themes": "・キャリアの転換点や独立の決断\n・家庭と仕事の両立における挑戦\n・専門性の確立と社会的認知の獲得",
    },
    "40s": {
        "life_stage_tag": "円熟期の飛躍",
        "description": "リーダーシップ発揮期",
        "themes": "・経験を活かした大きな挑戦や変革\n・組織やプロジェクトでのリーダーシップ\n・専門分野での影響力の拡大",
    },
    "50s": {
        "life_stage_tag": "熟練期の深化",
        "description": "専門性の極致",
        "themes": "・長年の経験が結実した成果\n・後進の育成や知恵の継承\n・専門性の深化と新たな境地の開拓",
    },
    "60s": {
        "life_stage_tag": "円熟期の新境地",
        "description": "経験知の体系化",
        "themes": "・キャリアの集大成となる業績\n・経験知の体系化と社会還元\n・定年後の新たな挑戦や社会貢献",
    },
    "70s": {
        "life_stage_tag": "晩年の挑戦",
        "description": "人生の知恵の結晶",
        "themes": "・晩年特有の知恵や円熟した判断\n・年齢を超えた活力と挑戦\n・次世代へのメッセージ",
    },
    "80s": {
        "life_stage_tag": "晩年の挑戦",
        "description": "人生の知恵の結晶",
        "themes": "・超高齢期の活躍と挑戦\n・長寿の知恵と経験の価値\n・生涯現役の姿勢",
    },
    "90s": {
        "life_stage_tag": "超高齢期の奇跡",
        "description": "長寿の知恵",
        "themes": "・90代以上の驚異的な活躍\n・歴史の生き証人としての価値\n・人生100年時代のロールモデル",
    },
}


class EpisodeGenerator:
    """エピソード生成エンジン"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5"):
        """
        Args:
            api_key: Anthropic API key
            model: Claude model name
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def generate_prompt(
        self,
        person_name: str,
        category: str,
        age: int,
        award_name: Optional[str] = None,
        award_year: Optional[str] = None,
        death_year: Optional[int] = None,
    ) -> str:
        """
        エピソード生成用プロンプトを作成

        Args:
            person_name: 人物名
            category: カテゴリ
            age: 年齢
            award_name: 業績名（オプション）
            award_year: 業績年（オプション）
            death_year: 没年（オプション、award_year矛盾チェック用）

        Returns:
            生成用プロンプト
        """
        # 年代キーを取得
        age_key = self._get_age_range_key(age)
        age_config = AGE_PROMPTS.get(age_key, AGE_PROMPTS["70s"])

        # award_yearとdeath_yearの矛盾チェック
        include_award_year = True
        if death_year and award_year:
            try:
                award_year_int = int(award_year)
                # 死後の業績年は含めない（メタ的表現を防ぐ）
                if award_year_int > death_year:
                    include_award_year = False
            except ValueError:
                pass

        prompt = f"""あなたは、人物の人生における印象的なエピソードを生成する専門家です。

以下の人物について、**{age}歳のとき（{age_config["description"]}）** の印象的なエピソードを日本語で生成してください。

人物名: {person_name}
カテゴリ: {category}
年齢: {age}歳（{age_config["life_stage_tag"]}）"""

        if award_name:
            prompt += f"""
この時期の重要な業績/出来事: {award_name}"""
            if award_year and include_award_year:
                prompt += f" ({award_year}年)"

        prompt += f"""

エピソードの要件:
1. 「あなたと同じ{age}歳のとき、{person_name}は〜」という形式で始める
2. この年代特有の視点を含める:
{age_config["themes"]}
3. 具体的な事実や出来事を含める
4. 200-300文字程度
5. educational_valueのある内容
6. 事実に基づいた内容（架空の内容は避ける）

❌ 絶対禁止される表現:
- 「すでにこの世を去っていました」「亡くなった後」「死去した後」などのメタ的な死の言及
- 「未来のこと」「まだ到達していない」などの時系列の矛盾
- 「年齢設定を変更」「申し訳ありませんが」などの生成失敗の言及
- 「このキャラクターは架空です」「実在しないため」などのメタ的説明

注意: この人物のこの年齢のエピソードが不明確な場合は、一般的に知られている事実に基づいて推測してください。
人物が指定年齢で存命だった場合、その時期の活動や功績を中心に記述してください。

エピソードテキスト:"""

        return prompt

    def call_anthropic_api(self, prompt: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        """
        Anthropic APIを呼び出してエピソードを生成

        Args:
            prompt: 生成用プロンプト
            max_tokens: 最大トークン数
            temperature: 温度パラメータ

        Returns:
            生成されたエピソードテキスト

        Raises:
            Exception: API呼び出しエラー
        """
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )

        # Type assertion for mypy - content[0] is TextBlock with .text attribute
        content_block = message.content[0]
        result: str = str(getattr(content_block, "text", "")).strip()
        return result

    def calculate_scores(self, episode_text: str) -> Dict[str, float]:
        """
        品質スコアを計算

        Args:
            episode_text: エピソードテキスト

        Returns:
            スコア辞書
        """
        char_count = len(episode_text)
        scores = {
            "memorability_score": 8.5,
            "empathy_score": 7.5,
            "surprise_score": 8.0,
            "generation_quality_score": 8.5,
            "educational_value": 8.0,
            "story_quality": 8.5,
            "factual_density": 8.5,
        }

        # 文字数に応じて調整
        if char_count < 150:
            for key in scores:
                scores[key] -= 1.0
        elif char_count > 300:
            for key in scores:
                scores[key] += 0.5

        scores["composite_score"] = sum(scores.values()) / len(scores) * 10

        return scores

    def generate(
        self,
        person_data: Dict[str, Any],
        age: int,
        award_name: Optional[str] = None,
        award_year: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        エピソードを生成（高レベルAPI）

        Args:
            person_data: 人物データ辞書（person_name, category, person_type必須）
            age: 年齢
            award_name: 業績名（オプション）
            award_year: 業績年（オプション）

        Returns:
            エピソードデータ辞書

        Raises:
            KeyError: 必須フィールドが不足
            Exception: 生成エラー
        """
        # 必須フィールドチェック
        required_fields = ["person_name", "category", "person_type"]
        for field in required_fields:
            if field not in person_data:
                raise KeyError(f"Missing required field: {field}")

        person_name = person_data["person_name"]
        category = person_data["category"]
        person_type = person_data["person_type"]
        death_year = person_data.get("death_year")

        # プロンプト生成
        prompt = self.generate_prompt(
            person_name=person_name,
            category=category,
            age=age,
            award_name=award_name,
            award_year=award_year,
            death_year=death_year,
        )

        # LLM呼び出し
        episode_text = self.call_anthropic_api(prompt)

        # 【品質ゲート】人物名整合性バリデーション
        from src.validators.episode_name_validator import validate_episode_name, ValidationResult
        import re as re_module

        validation = validate_episode_name(person_name, episode_text, strict=False)
        if validation.result == ValidationResult.MISMATCH and validation.text_name:
            # 自動修正: 本文冒頭を person_name に置換
            episode_text = re_module.sub(
                rf"^(あなたと同じ[\d.]+歳のとき、){re_module.escape(validation.text_name)}((?:『.+?』)?は)",
                rf"\1{person_name}\2",
                episode_text,
            )

        # スコア計算
        scores = self.calculate_scores(episode_text)

        # 年代を設定
        nendai = self._get_nendai(age)

        # age_configを取得
        age_key = self._get_age_range_key(age)
        age_config = AGE_PROMPTS.get(age_key, AGE_PROMPTS["70s"])

        # award_levelの決定
        award_level_value = self._determine_award_level(award_name)

        # person_idを生成
        person_id = self._generate_person_id(person_name)

        # エピソードデータを構築
        episode = {
            "episode_id": "",  # 後でCSV統合時に付与
            "person_id": person_id,
            "person_name": person_name,
            "episode_count": "",
            "age": age,
            "category": category,
            "char_count": len(episode_text),
            "episode_text": episode_text,
            "episode_type": "ACHIEVEMENT",
            "fact_check_result": "",
            "group_name": "",
            "is_group_member": False,
            "person_type": person_type,
            "quality_score": "",
            "年代": nendai,
            "source": "LLM_GENERATED",
            "tier": "",
            "week": "",
            "work_title": "",
            "generation_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fame_tier": "",
            "wikipedia_ja": "",
            "textbook": "",
            "award_level": award_level_value,
            "notoriety": "",
            "fame_score": 7.0,
            "composite_score": scores["composite_score"],
            "fame_score_updated_at": "",
            "episode_fame_tier": "",
            "episode_fame_score": 7.0,
            "episode_fame_score_updated_at": "",
            "人生の節目タグ": age_config["life_stage_tag"],
            **scores,  # スコア辞書をマージ
        }

        return episode

    def _get_age_range_key(self, age: int) -> str:
        """年齢から年代キー（30s, 40s, etc.）を取得"""
        if 30 <= age <= 39:
            return "30s"
        elif 40 <= age <= 49:
            return "40s"
        elif 50 <= age <= 59:
            return "50s"
        elif 60 <= age <= 69:
            return "60s"
        elif 70 <= age <= 79:
            return "70s"
        elif 80 <= age <= 89:
            return "80s"
        elif age >= 90:
            return "90s"
        else:
            return "70s"  # デフォルト

    def _get_nendai(self, age: int) -> str:
        """年齢から年代カラムの値を取得"""
        if age < 20:
            return "10代"
        elif age < 30:
            return "20代"
        elif age < 40:
            return "30代"
        elif age < 50:
            return "40代"
        elif age < 60:
            return "50代"
        else:
            return "60歳以上"

    def _determine_award_level(self, award_name: Optional[str]) -> str:
        """業績から award_level を決定"""
        if not award_name:
            return ""

        if "ノーベル" in award_name:
            return "NOBEL"
        elif any(x in award_name for x in ["フィールズ", "プリツカー", "チューリング", "ラスカー"]):
            return "INTERNATIONAL_TOP"
        elif any(x in award_name for x in ["アカデミー", "オスカー", "カンヌ", "グラミー", "文化勲章"]):
            return "INTERNATIONAL"
        elif "国民栄誉賞" in award_name:
            return "NATIONAL"
        else:
            return "AWARD"

    def _generate_person_id(self, person_name: str) -> str:
        """person_nameからperson_idを生成"""
        hash_obj = hashlib.md5(person_name.encode("utf-8"), usedforsecurity=False)
        hash_hex = hash_obj.hexdigest()[:7].upper()
        return f"P{hash_hex}"


if __name__ == "__main__":
    # 動作確認用
    import os

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY環境変数が設定されていません")
        exit(1)

    generator = EpisodeGenerator(api_key=api_key)

    # テストデータ
    person_data = {
        "person_name": "山中伸弥",
        "category": "科学・技術",
        "person_type": "REAL",
        "birth_year": 1962,
        "death_year": None,
    }

    print(f"エピソード生成テスト: {person_data['person_name']}")

    # プロンプト生成テスト
    prompt = generator.generate_prompt(
        person_name=str(person_data["person_name"]),
        category=str(person_data["category"]),
        age=47,
        award_name="iPS細胞の作製に成功",
        award_year="2007",
    )
    print(f"\nプロンプト:\n{prompt[:300]}...\n")

    # エピソード生成テスト
    print("エピソード生成中...")
    episode = generator.generate(
        person_data=person_data,
        age=47,
        award_name="iPS細胞の作製に成功",
        award_year="2007",
    )

    print("\n生成成功:")
    print(f"  エピソードテキスト: {episode['episode_text'][:100]}...")
    print(f"  文字数: {episode['char_count']}")
    print(f"  composite_score: {episode['composite_score']:.2f}")
    print(f"  人生の節目タグ: {episode['人生の節目タグ']}")
