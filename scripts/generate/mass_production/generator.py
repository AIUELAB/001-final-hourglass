#!/usr/bin/env python3
"""
並列エピソード生成モジュール

asyncioベースの高スループット生成パイプライン
"""

import asyncio
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .config import FORBIDDEN_PATTERNS, GenerationConfig, REQUIRED_PATTERNS

# システムプロンプト取得関数をインポート
try:
    from scripts.sage.prompts.category_prompts import get_system_prompt, get_static_system_prompt
except ImportError:
    # フォールバック: 関数が見つからない場合はNoneを返す
    def get_system_prompt(person_name: str, age: int) -> str | None:
        return None

    def get_static_system_prompt() -> str | None:
        return None


@dataclass
class GenerationResult:
    """生成結果"""

    person_id: str
    person_name: str
    age: int
    category: str
    episode_text: str
    variation: int
    template_style: str
    generation_time_ms: int
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationInput:
    """生成入力"""

    person_id: str
    person_name: str
    age: int
    category: str
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    additional_context: Optional[str] = None


class PromptBuilder:
    """プロンプトビルダー"""

    # 共通の文体ルール（全スタイルに適用）
    WRITING_RULES = """
【文体ルール（絶対遵守）】
- すべての文を丁寧語（です・ます調）で終える
- 主語は「{person_name}は」「彼は」「彼女は」を使用
- 「私は」「私の」「私が」は絶対に使用しない
- 冒頭は必ず「あなたと同じ{age}歳のとき、{person_name}は」で開始

【禁止文末】
- 「〜だ。」「〜である。」「〜た。」「〜ていた。」（常体禁止）
"""

    STYLES = {
        "factual": {
            "name": "事実重視",
            "instruction": """以下の構成で記述してください:
1. 西暦年号を2つ以上含める（例: 1995年、2003年）
2. 固有名詞を5つ以上含める（人名、作品名、組織名、地名など）
3. 数値データを3つ以上含める（記録、金額、順位など）
4. 「」で囲んだ作品名・イベント名を2つ以上含める

禁止表現:
- 「〜と言われている」「〜かもしれない」などの曖昧表現
- 「その後の活躍につながった」などの抽象表現
- 推測や伝聞に基づく記述""",
            "tone": "客観的・報道的（丁寧語）",
        },
        "narrative": {
            "name": "物語調",
            "instruction": """出来事の経緯や背景を時系列で描写し、臨場感のある文章にしてください。
年号と固有名詞を必ず含めること。
※丁寧語（です・ます調）で記述すること。""",
            "tone": "描写的・没入感のある（丁寧語）",
        },
        "inspirational": {
            "name": "インスピレーション",
            "instruction": """困難の克服や成長の瞬間に焦点を当て、読者に気づきを与える内容にしてください。
年号と固有名詞を必ず含めること。
※丁寧語（です・ます調）で記述すること。""",
            "tone": "感動的・啓発的（丁寧語）",
        },
    }

    def __init__(self, forbidden_patterns: Optional[List[str]] = None):
        self.forbidden_patterns = forbidden_patterns or FORBIDDEN_PATTERNS

    def build(
        self,
        input_data: GenerationInput,
        style: str = "factual",
        variation: int = 0,
    ) -> str:
        style_info = self.STYLES.get(style, self.STYLES["factual"])
        age_context = self._get_age_context(input_data.age)
        forbidden_list = "\n".join(f"- {p}" for p in self.forbidden_patterns)

        # 文体ルールを人物名・年齢で埋める
        writing_rules = self.WRITING_RULES.format(
            person_name=input_data.person_name,
            age=input_data.age,
        )

        prompt = f"""# エピソード生成タスク

## 対象人物
- 名前: {input_data.person_name}
- 年齢: {input_data.age}歳
- カテゴリ: {input_data.category}
{f"- 生年: {input_data.birth_year}年" if input_data.birth_year else ""}
{f"- 没年: {input_data.death_year}年" if input_data.death_year else ""}

{writing_rules}

## 生成スタイル: {style_info['name']}
{style_info['instruction']}
トーン: {style_info['tone']}

## 必須要件
1. 冒頭は必ず「あなたと同じ{input_data.age}歳のとき、{input_data.person_name}は」で開始
2. 西暦年号を最低1つ含める
3. 具体的な数値を最低3つ含める
4. 固有名詞を最低5つ含める
5. 300〜400文字で完結させる
6. すべての文を「です」「ます」「でした」「ました」で終える

## 禁止事項
{forbidden_list}
- 「私は」「私の」「私が」などの一人称表現
- 「〜だ。」「〜である。」などの常体文末

## 年齢コンテキスト
{age_context}

{f"## 追加情報{chr(10)}{input_data.additional_context}" if input_data.additional_context else ""}

## 出力形式
エピソードテキストのみを出力してください（丁寧語で）。
"""
        return prompt

    def _get_age_context(self, age: int) -> str:
        if age < 20:
            return "若年期: 学業、才能の発見、デビュー、初期の挑戦などに焦点"
        elif age < 30:
            return "青年期: キャリア形成、転機、重要な決断、飛躍のきっかけなどに焦点"
        elif age < 40:
            return "壮年期前半: 成功の確立、代表作、大きな成果、リーダーシップなどに焦点"
        elif age < 50:
            return "壮年期後半: 円熟、新たな挑戦、影響力の拡大、転換点などに焦点"
        elif age < 60:
            return "成熟期: 集大成、後進育成、新分野への展開、社会貢献などに焦点"
        else:
            return "晩年期: 最後の大仕事、功績の認知、名誉、継承などに焦点"

    def get_prompt_stats(self, input_data: GenerationInput) -> dict:
        """プロンプト統計を取得（デバッグ用）"""
        prompt = self.build(input_data)
        return {
            "char_count": len(prompt),
            "estimated_tokens": len(prompt) // 2,  # 日本語は約2文字/トークン
            "builder": "standard",
        }


class CompactPromptBuilder:
    """
    圧縮版プロンプトビルダー（Phase 2最適化）

    目標: トークン数 -30%（品質維持）
    手法:
    - 冗長なヘッダー・フォーマット削除
    - インライン形式で情報密度向上
    - 短縮キーワード使用
    """

    # 圧縮版年齢コンテキスト
    AGE_CONTEXT_COMPACT = {
        (0, 20): "若年期:学業/才能発見/デビュー",
        (20, 30): "青年期:キャリア形成/転機/決断",
        (30, 40): "壮年前半:成功確立/代表作/リーダーシップ",
        (40, 50): "壮年後半:円熟/新挑戦/影響力拡大",
        (50, 60): "成熟期:集大成/後進育成/社会貢献",
        (60, 200): "晩年期:最後の大仕事/功績認知/継承",
    }

    def __init__(self, forbidden_patterns: Optional[List[str]] = None):
        self.forbidden_patterns = forbidden_patterns or FORBIDDEN_PATTERNS

    def build(
        self,
        input_data: GenerationInput,
        style: str = "factual",
        variation: int = 0,
    ) -> str:
        """圧縮版プロンプトを生成"""
        age_ctx = self._get_age_context_compact(input_data.age)
        forbidden_inline = "/".join(self.forbidden_patterns[:4])  # 主要4件のみ

        # 生年・没年情報（あれば）
        year_info = ""
        if input_data.birth_year:
            year_info += f"生{input_data.birth_year}"
        if input_data.death_year:
            year_info += f"没{input_data.death_year}"

        prompt = f"""EP生成|{input_data.person_name}|{input_data.age}歳|{input_data.category}{f"|{year_info}" if year_info else ""}

開始文:「あなたと同じ{input_data.age}歳のとき、」
必須:年号≥1/数値≥3/固有名詞≥5/「」作品名≥2
禁止:{forbidden_inline}
焦点:{age_ctx}
{f"補足:{input_data.additional_context[:100]}" if input_data.additional_context else ""}
300-400字,EPテキストのみ出力"""
        return prompt

    def _get_age_context_compact(self, age: int) -> str:
        """圧縮版年齢コンテキスト"""
        for (min_age, max_age), context in self.AGE_CONTEXT_COMPACT.items():
            if min_age <= age < max_age:
                return context
        return "晩年期:功績認知/継承"

    def get_prompt_stats(self, input_data: GenerationInput) -> dict:
        """プロンプト統計を取得"""
        prompt = self.build(input_data)
        return {
            "char_count": len(prompt),
            "estimated_tokens": len(prompt) // 2,
            "builder": "compact",
        }


def create_prompt_builder(compact: bool = False) -> PromptBuilder:
    """プロンプトビルダーを作成（ファクトリー関数）"""
    if compact:
        return CompactPromptBuilder()
    return PromptBuilder()


class ParallelGenerator:
    """並列エピソード生成器"""

    def __init__(
        self,
        llm_client: Any,
        config: Optional[GenerationConfig] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        enable_cache: bool = False,  # H4最適化: Prompt Caching
    ):
        self.llm = llm_client
        self.config = config or GenerationConfig()
        self.enable_cache = enable_cache  # H4: キャッシュ有効化フラグ
        # Phase 2: 設定に応じてプロンプトビルダー選択
        if prompt_builder is not None:
            self.prompt_builder = prompt_builder
        else:
            self.prompt_builder = create_prompt_builder(compact=self.config.use_compact_prompt)

        # H4: キャッシュ統計
        self.cache_stats = {
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "total_cached_requests": 0,
        }

    async def generate_batch(
        self,
        inputs: List[GenerationInput],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[GenerationResult]:
        semaphore = asyncio.Semaphore(self.config.max_workers)
        completed = 0
        total = len(inputs) * self.config.candidates_per_input

        async def generate_one(
            input_data: GenerationInput,
            variation: int,
        ) -> GenerationResult:
            nonlocal completed

            async with semaphore:
                style = self._get_style_for_variation(variation)
                prompt = self.prompt_builder.build(input_data, style, variation)

                # H4最適化: キャッシュモード時は静的システムプロンプトを使用
                if self.enable_cache:
                    system_prompt = get_static_system_prompt()
                else:
                    system_prompt = get_system_prompt(input_data.person_name, input_data.age)

                start_time = time.time()
                try:
                    text = await self._generate_with_retry(prompt, system_prompt)
                    elapsed_ms = int((time.time() - start_time) * 1000)

                    result = GenerationResult(
                        person_id=input_data.person_id,
                        person_name=input_data.person_name,
                        age=input_data.age,
                        category=input_data.category,
                        episode_text=text,
                        variation=variation,
                        template_style=style,
                        generation_time_ms=elapsed_ms,
                        success=True,
                    )
                except Exception as e:
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    result = GenerationResult(
                        person_id=input_data.person_id,
                        person_name=input_data.person_name,
                        age=input_data.age,
                        category=input_data.category,
                        episode_text="",
                        variation=variation,
                        template_style=style,
                        generation_time_ms=elapsed_ms,
                        success=False,
                        error_message=str(e),
                    )

                completed += 1
                if progress_callback:
                    progress_callback(completed, total)

                return result

        tasks = [generate_one(inp, var) for inp in inputs for var in range(self.config.candidates_per_input)]

        results = await asyncio.gather(*tasks)
        return list(results)

    async def _generate_with_retry(self, prompt: str, system_prompt: str | None = None) -> str:
        last_error = None

        for attempt in range(self.config.max_retries):
            try:
                # H4最適化: キャッシュモード時はキャッシュ付き生成を使用
                if self.enable_cache and system_prompt and hasattr(self.llm, "generate_with_cache_async"):
                    text, cache_info = await asyncio.wait_for(
                        self.llm.generate_with_cache_async(system_prompt, prompt),
                        timeout=self.config.timeout_seconds,
                    )
                    # キャッシュ統計を更新
                    self.cache_stats["cache_creation_input_tokens"] += cache_info.get("cache_creation", 0)
                    self.cache_stats["cache_read_input_tokens"] += cache_info.get("cache_read", 0)
                    self.cache_stats["total_cached_requests"] += 1
                else:
                    text = await asyncio.wait_for(
                        self.llm.generate_async(prompt, system_prompt),
                        timeout=self.config.timeout_seconds,
                    )
                return text
            except asyncio.TimeoutError:
                last_error = f"Timeout after {self.config.timeout_seconds}s"
            except Exception as e:
                last_error = str(e)

            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(2**attempt)

        raise RuntimeError(f"Generation failed after {self.config.max_retries} attempts: {last_error}")

    def _get_style_for_variation(self, variation: int) -> str:
        styles = list(PromptBuilder.STYLES.keys())
        return styles[variation % len(styles)]

    def generate_sync(
        self,
        inputs: List[GenerationInput],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[GenerationResult]:
        return asyncio.run(self.generate_batch(inputs, progress_callback))


class MockLLMClient:
    """テスト用モックLLMクライアント"""

    def __init__(self, delay: float = 0.1):
        self.delay = delay
        self.call_count = 0

    async def generate_async(self, prompt: str, system_prompt: str | None = None) -> str:
        await asyncio.sleep(self.delay)
        self.call_count += 1

        name_match = re.search(r"名前: (.+)", prompt)
        age_match = re.search(r"年齢: (\d+)歳", prompt)

        name = name_match.group(1) if name_match else "テスト太郎"
        age = age_match.group(1) if age_match else "30"

        # 丁寧語（です・ます調）でモック応答を返す
        return f"あなたと同じ{age}歳のとき、{name}は1985年に重要な転機を迎えました。東京で開催された国際会議に参加し、100人以上の専門家と交流しました。その後3年間で5つの革新的なプロジェクトを立ち上げ、総額1億円の資金を調達しました。"


class TextValidator:
    """生成テキストバリデーター"""

    def __init__(
        self,
        required_patterns: Optional[Dict[str, str]] = None,
        forbidden_patterns: Optional[List[str]] = None,
    ):
        self.required_patterns = required_patterns or REQUIRED_PATTERNS
        self.forbidden_patterns = forbidden_patterns or FORBIDDEN_PATTERNS

    def validate(self, text: str, age: int) -> tuple[bool, List[str]]:
        errors = []

        expected_prefix = f"あなたと同じ{age}歳のとき、"
        if not text.startswith(expected_prefix):
            errors.append(f"冒頭が「{expected_prefix}」で始まっていません")

        year_pattern = self.required_patterns.get("year", r"\d{4}年")
        years = re.findall(year_pattern, text)
        if len(years) < 1:
            errors.append("年号（XXXX年）が含まれていません")

        number_pattern = self.required_patterns.get("number", r"\d+")
        numbers = re.findall(number_pattern, text)
        if len(numbers) < 3:
            errors.append(f"数値が不足しています（{len(numbers)}/3）")

        # 固有名詞チェック（「」内、『』内、カタカナ3文字以上）
        proper_noun_pattern = r"「[^」]+」|『[^』]+』|[\u30A0-\u30FF]{3,}"
        proper_nouns = re.findall(proper_noun_pattern, text)
        if len(proper_nouns) < 5:
            errors.append(f"固有名詞が不足しています（{len(proper_nouns)}/5）")

        if len(text) < 250:
            errors.append(f"文字数が不足しています（{len(text)}/250〜400）")
        elif len(text) > 500:
            errors.append(f"文字数が超過しています（{len(text)}/250〜400）")

        for pattern in self.forbidden_patterns:
            if re.search(pattern, text):
                errors.append(f"禁止表現が含まれています: {pattern}")

        return len(errors) == 0, errors


def main():
    """デモ実行"""
    print("=== 並列生成デモ ===")

    client = MockLLMClient(delay=0.05)
    generator = ParallelGenerator(client)

    inputs = [
        GenerationInput(
            person_id="P001",
            person_name="山田太郎",
            age=30,
            category="科学・技術",
            birth_year=1970,
        ),
        GenerationInput(
            person_id="P002",
            person_name="鈴木花子",
            age=25,
            category="芸術・文化",
            birth_year=1980,
        ),
    ]

    def progress(completed: int, total: int):
        print(f"\r進捗: {completed}/{total}", end="", flush=True)

    start = time.time()
    results = generator.generate_sync(inputs, progress)
    elapsed = time.time() - start

    print(f"\n\n生成完了: {len(results)}件 ({elapsed:.2f}秒)")
    print(f"LLM呼び出し回数: {client.call_count}")


if __name__ == "__main__":
    main()
