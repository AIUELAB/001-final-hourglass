"""
Ultra-High Quality Prompt System
==================================

Few-Shot Learning + 明示的要件を組み合わせた
超高品質エピソード生成用プロンプトテンプレート

Phase 1: Foundation - Prompt Template V3.0
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
import json
from pathlib import Path
from few_shot_database import FewShotDatabase, FewShotExample

# EPUP: 架空キャラクター用の作品名マッピング
FICTIONAL_WORK_TITLE_MAP = {
    "ピカチュウ": "ポケットモンスター",
    "サトシ": "ポケットモンスター",
    "フグ田サザエ": "サザエさん",
    "磯野カツオ": "サザエさん",
    "磯野ワカメ": "サザエさん",
    "磯野波平": "サザエさん",
    "ティファ・ロックハート": "ファイナルファンタジーVII",
    "クラウド・ストライフ": "ファイナルファンタジーVII",
    "野比のび太": "ドラえもん",
    "ドラえもん": "ドラえもん",
    "竈門炭治郎": "鬼滅の刃",
    "竈門禰豆子": "鬼滅の刃",
    "孫悟空": "ドラゴンボール",
    "モンキー・D・ルフィ": "ONE PIECE",
    "江戸川コナン": "名探偵コナン",
    "工藤新一": "名探偵コナン",
}

# EPUP: 架空キャラクター専用プロンプトテンプレート
FICTIONAL_CHARACTER_PROMPT_TEMPLATE = """あなたは{work_title}の世界観を深く理解するストーリーテラーです。

{person_name}（{work_title}のキャラクター）が{age}歳の時点での作品内エピソードを生成してください。

【重要な制約】
- このキャラクターは作品内の存在として扱い、メタ的言及は禁止
- 作品の設定・世界観に沿った内容にすること
- 「あなたと同じ{age}歳のとき」という形式で開始
- 200-250文字

【禁止フレーズ】※絶対に使用しないこと
- 「架空のキャラクター」
- 「エピソードは存在しません」
- 「実在しない」
- 「公式な描写は存在しません」
- 「申し訳ございませんが」
- 「フィクションの」
- 「設定上は」

【生成方針】
- 原作で{age}歳時点の描写があればそれを活用
- なければ、キャラクター設定から自然に導かれるエピソードを創作
- キャラクターの性格・口癖・行動パターンを維持
- 作品内の地名、イベント、関係キャラクターを活用

【出力形式】
「あなたと同じ{age}歳のとき、{person_name}は〜」という形式で、作品世界内の視点で記述してください。
"""


@dataclass
class PromptConfig:
    """プロンプト設定"""
    # 必須要素のスコア目標
    turning_point_target: int = 10
    unexpectedness_target: int = 7
    risk_taking_target: int = 7
    empathy_target: int = 7
    sensational_target: int = 10

    # Few-Shot設定
    n_few_shot_examples: int = 3
    min_example_score: float = 35.0

    # 文字数制限
    min_chars: int = 180
    max_chars: int = 250

    # 必須数値数
    min_numbers: int = 3


class UltraHighQualityPromptGenerator:
    """超高品質プロンプト生成器"""

    def __init__(self, config: Optional[PromptConfig] = None):
        """初期化"""
        self.config = config or PromptConfig()
        self.few_shot_db = FewShotDatabase()

        # Few-Shotデータベースをロード
        db_path = Path("few_shot_database.json")
        if db_path.exists():
            self._load_few_shot_db_from_json(str(db_path))
        else:
            print("⚠️ few_shot_database.json not found, loading from CSV...")
            self.few_shot_db.load_from_csv()

    def _load_few_shot_db_from_json(self, json_path: str) -> None:
        """JSONからFew-Shotデータベースをロード"""
        # 簡易的にCSVから再ロード（より確実）
        print(f"📂 Loading Few-Shot database from CSV...")
        self.few_shot_db.load_from_csv()

    def generate_prompt(
        self,
        person_name: str,
        age: int,
        category: str,
        additional_context: Optional[Dict] = None,
        person_type: str = "REAL",
        work_title: Optional[str] = None,
    ) -> str:
        """
        超高品質プロンプトを生成

        Args:
            person_name: 人物名
            age: 年齢
            category: カテゴリ（エンターテインメント、ビジネス等）
            additional_context: 追加コンテキスト
            person_type: 人物タイプ（REAL/FICTIONAL）- EPUP対応
            work_title: 作品名（架空キャラクターの場合）- EPUP対応

        Returns:
            生成されたプロンプト文字列
        """
        # EPUP: 架空キャラクターの場合は専用プロンプトを使用
        if person_type == "FICTIONAL":
            return self._generate_fictional_prompt(person_name, age, work_title)

        # 実在人物の場合は従来のプロンプト生成
        # Few-Shot例を取得
        few_shot_examples = self.few_shot_db.get_best_examples(
            category=category,
            n=self.config.n_few_shot_examples,
            min_score=self.config.min_example_score
        )

        # Few-Shot例が不足している場合は全カテゴリから取得
        if len(few_shot_examples) < self.config.n_few_shot_examples:
            print(f"⚠️ Not enough examples in '{category}', using best from all categories")
            few_shot_examples = self._get_best_overall_examples()

        # プロンプトを構築
        prompt = self._build_prompt_template(
            person_name=person_name,
            age=age,
            category=category,
            few_shot_examples=few_shot_examples,
            additional_context=additional_context
        )

        return prompt

    def _generate_fictional_prompt(
        self,
        person_name: str,
        age: int,
        work_title: Optional[str] = None,
    ) -> str:
        """
        EPUP: 架空キャラクター専用プロンプトを生成

        Args:
            person_name: キャラクター名
            age: 年齢
            work_title: 作品名（Noneの場合はマッピングから取得）

        Returns:
            架空キャラクター専用プロンプト
        """
        # 作品名の解決
        if not work_title or str(work_title).lower() in ("nan", "none", ""):
            work_title = FICTIONAL_WORK_TITLE_MAP.get(person_name, "作品")

        return FICTIONAL_CHARACTER_PROMPT_TEMPLATE.format(
            person_name=person_name,
            age=int(age),
            work_title=work_title
        )

    def _get_best_overall_examples(self) -> List[FewShotExample]:
        """全カテゴリから最良の例を取得"""
        all_examples = self.few_shot_db.examples

        def calculate_score(ex: FewShotExample) -> float:
            return (
                ex.estimated_turning_point +
                ex.estimated_unexpectedness +
                ex.estimated_risk_taking +
                ex.estimated_empathy +
                ex.estimated_sensational
            )

        scored = [(ex, calculate_score(ex)) for ex in all_examples]
        scored.sort(key=lambda x: x[1], reverse=True)

        return [ex for ex, _ in scored[:self.config.n_few_shot_examples]]

    def _build_prompt_template(
        self,
        person_name: str,
        age: int,
        category: str,
        few_shot_examples: List[FewShotExample],
        additional_context: Optional[Dict]
    ) -> str:
        """プロンプトテンプレートを構築"""

        # Few-Shot例のフォーマット
        formatted_examples = self._format_few_shot_examples(few_shot_examples)

        # 必須キーワードリスト
        keyword_lists = self._build_keyword_lists()

        # プロンプトテンプレート
        prompt = f"""# ミッション

{person_name}が{age}歳のときの**超高品質エピソード**を生成してください。

---

## 🎯 必須要素（Phase 3評価基準 - 50点満点）

### 1. 人生の転換点（目標: {self.config.turning_point_target}/10点）
- **明確な成果を数値で示す**
- **強い表現**: 「転機をもたらした」「切り開いた」「押し上げた」「確立した」
- キャリアや人生における重要な分岐点であることを明示

### 2. 意外性（目標: {self.config.unexpectedness_target}/10点）
- **逆境からの成功**を描く
- **前例のない挑戦**を強調
- キーワード: 「初めて」「前例なく」「無名から」

### 3. リスクテイキング（目標: {self.config.risk_taking_target}/10点）
- **具体的な期間**を明示（例: 3ヶ月で断行、わずか2年で）
- **前例の無さ**や**無名・若さ等の背景**を記述
- 挑戦の困難さを数値化

### 4. 共感性（目標: {self.config.empathy_target}/10点）
- **不安・葛藤を引用符で明示**: 「本当に〜？」「〜だろうか」
- **ステークホルダーの懸念**を具体的に描写
- 読者が感情移入できる要素

### 5. センセーショナル度（目標: {self.config.sensational_target}/10点）
- **具体的数値を{self.config.min_numbers}つ以上含める**
  - 金額（39億円、1兆円）
  - 人数（10万人、観客動員620万人）
  - 期間（28年間、3ヶ月）
  - 記録（4367安打、10年連続）
- **強い動詞**: 「駆け上がった」「切り開いた」「もたらした」

---

## ✅ 必須チェックリスト

生成時に以下を**必ず確認**してください：

- [ ] 年齢: **{age}歳時点**のエピソード（厳守）
- [ ] 不安・懸念: 引用符「」付きで明示
- [ ] 数値: **{self.config.min_numbers}個以上**の具体的数値
- [ ] リスク: 逆境・前例なし・若さ等を明記
- [ ] 強い動詞: 「駆け上がった」「切り開いた」「もたらした」等
- [ ] 文字数: **{self.config.min_chars}-{self.config.max_chars}文字**

### 🔍 日本語品質チェック（重要）

以下の誤字・脱字を**絶対に避けてください**：

- [ ] **助詞の脱落**: 「として」が「としの」にならないよう確認
- [ ] **助詞の誤用**: 「では」「に」「で」「を」を正確に使用
- [ ] **句読点**: 文が長い場合は読点「、」を適切に挿入
- [ ] **動詞の活用**: 「でした」「しました」等の語尾を正確に記述
- [ ] **誤字・脱字の最終確認**: 生成後に必ず全文を見直す

---

## 🌟 成功例（参考にしてください）

{formatted_examples}

---

## 📋 必須キーワードリスト

### 不安・葛藤キーワード（必須）
{keyword_lists['anxiety']}

### リスクキーワード（必須）
{keyword_lists['risk']}

### 転機キーワード（推奨）
{keyword_lists['turning_point']}

---

## 🎯 スコア目標

- **Phase 3インパクト**: 50点満点中**50点以上**
- **各要素の目標**:
  - 転換点: {self.config.turning_point_target}点
  - 意外性: {self.config.unexpectedness_target}点
  - リスクテイキング: {self.config.risk_taking_target}点
  - 共感性: {self.config.empathy_target}点
  - センセーショナル度: {self.config.sensational_target}点

---

## 📝 出力形式

**{age}歳時点のエピソードのみ**を出力してください（説明不要）。

以下の構造を推奨します：
1. 冒頭: 「あなたと同じ{age}歳のとき、{person_name}は〜」
2. 本文: 具体的な成果・数値（3つ以上）
3. 困難・懸念: 引用符付きの不安「本当に〜？」
4. リスク: 前例なし、逆境、挑戦の具体化
5. 結末: 強い動詞で転機を明示

文字数: {self.config.min_chars}-{self.config.max_chars}文字
"""

        return prompt

    def _format_few_shot_examples(self, examples: List[FewShotExample]) -> str:
        """Few-Shot例をフォーマット"""
        formatted = []

        for i, ex in enumerate(examples, 1):
            # 成功要因の分析
            success_factors = []
            if ex.has_anxiety_keywords:
                # 不安キーワードを抽出
                anxiety_found = [kw for kw in self.few_shot_db.ANXIETY_KEYWORDS if kw in ex.episode_text]
                if anxiety_found:
                    success_factors.append(f"不安: \"{anxiety_found[0]}\"")

            if ex.has_risk_keywords:
                risk_found = [kw for kw in self.few_shot_db.RISK_KEYWORDS if kw in ex.episode_text]
                if risk_found:
                    success_factors.append(f"リスク: \"{risk_found[0]}\"")

            if ex.numerical_data_count > 0:
                success_factors.append(f"数値: {ex.numerical_data_count}個")

            success_factors_str = "、".join(success_factors)

            # 推定スコア
            total_score = (
                ex.estimated_turning_point +
                ex.estimated_unexpectedness +
                ex.estimated_risk_taking +
                ex.estimated_empathy +
                ex.estimated_sensational
            )

            formatted.append(f"""
### 例{i}: {ex.person_name}（{ex.age}歳）- 推定{total_score:.0f}点合格

**エピソード**:
{ex.episode_text}

**成功要因**:
- {success_factors_str}
- 文字数: {ex.character_count}文字
- カテゴリ: {ex.category}
""")

        return "\n".join(formatted)

    def _build_keyword_lists(self) -> Dict[str, str]:
        """必須キーワードリストを構築"""
        return {
            'anxiety': ', '.join([f'「{kw}」' for kw in self.few_shot_db.ANXIETY_KEYWORDS[:8]]),
            'risk': ', '.join([f'「{kw}」' for kw in self.few_shot_db.RISK_KEYWORDS[:8]]),
            'turning_point': ', '.join([f'「{kw}」' for kw in self.few_shot_db.TURNING_POINT_KEYWORDS[:8]])
        }


def main():
    """メイン処理 - デモンストレーション"""
    print("=" * 60)
    print("🎯 Ultra-High Quality Prompt Generator Demo")
    print("=" * 60)

    # プロンプト生成器を初期化
    generator = UltraHighQualityPromptGenerator()

    # テストケース
    test_cases = [
        {"name": "新垣結衣", "age": 18, "category": "エンターテインメント"},
        {"name": "松下幸之助", "age": 56, "category": "ビジネス"},
        {"name": "イチロー", "age": 45, "category": "スポーツ"},
    ]

    for case in test_cases:
        print(f"\n{'='*60}")
        print(f"📝 Test Case: {case['name']} ({case['age']}歳)")
        print(f"{'='*60}\n")

        prompt = generator.generate_prompt(
            person_name=case['name'],
            age=case['age'],
            category=case['category']
        )

        # プロンプトの一部を表示（最初の1000文字）
        print(prompt[:1000])
        print("\n... (以下省略)\n")

        # プロンプトをファイルに保存
        output_file = Path(f"prompts/ultra_prompt_{case['name']}_{case['age']}.txt")
        output_file.parent.mkdir(exist_ok=True)
        output_file.write_text(prompt, encoding='utf-8')
        print(f"💾 Saved to: {output_file}")

    print(f"\n{'='*60}")
    print("✅ Prompt Generation Complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
