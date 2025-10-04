#!/usr/bin/env python3
"""
デュアルエピソード生成システム
各有名人につき、定番エピソードと意外性エピソードの2つを生成
"""

import os
from typing import Dict, Any, Tuple, Optional, List
from dataclasses import dataclass
from enum import Enum
import anthropic
from unified_validation_system_with_persistence import create_validator


class EpisodeType(Enum):
    """エピソードタイプ"""
    ICONIC = "iconic"  # 定番エピソード
    UNEXPECTED = "unexpected"  # 意外性エピソード


@dataclass
class EpisodeRequest:
    """エピソード生成リクエスト"""
    person_id: str
    person_name: str
    display_name: str
    user_age: int
    occupation: str
    category: str
    google_search_count: int
    wikipedia_url: Optional[str] = None
    birth_year: Optional[int] = None


@dataclass
class GeneratedEpisode:
    """生成されたエピソード"""
    person_id: str
    person_name: str
    display_name: str
    episode_type: EpisodeType
    episode_text: str
    episode_age: int
    is_valid: bool
    validation_result: Any


class DualEpisodeGenerator:
    """
    デュアルエピソード生成システム
    定番エピソードと意外性エピソードの2つを生成
    """

    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        config_path: Optional[str] = None,
        auto_correct: bool = True,
        reject_on_failure: bool = True
    ):
        """
        初期化

        Args:
            anthropic_api_key: Anthropic APIキー
            config_path: 統合検証システム設定ファイルパス
            auto_correct: 自動修正を有効にするか
            reject_on_failure: 検証失敗時に拒否するか
        """
        self.api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY環境変数が設定されていません")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.validator = create_validator(config_path)
        self.auto_correct = auto_correct
        self.reject_on_failure = reject_on_failure

    def generate_episodes_for_person(
        self,
        request: EpisodeRequest
    ) -> Tuple[Optional[GeneratedEpisode], Optional[GeneratedEpisode]]:
        """
        1人の有名人につき2つのエピソードを生成

        Args:
            request: エピソード生成リクエスト

        Returns:
            (定番エピソード, 意外性エピソード) のタプル
        """
        iconic_episode = self._generate_single_episode(request, EpisodeType.ICONIC)
        unexpected_episode = self._generate_single_episode(request, EpisodeType.UNEXPECTED)

        return iconic_episode, unexpected_episode

    def _generate_single_episode(
        self,
        request: EpisodeRequest,
        episode_type: EpisodeType
    ) -> Optional[GeneratedEpisode]:
        """
        単一エピソードを生成

        Args:
            request: エピソード生成リクエスト
            episode_type: エピソードタイプ（定番 or 意外性）

        Returns:
            生成されたエピソード、失敗時はNone
        """
        # LLMでエピソードテキストと年齢を生成
        episode_data = self._call_llm(request, episode_type)
        if not episode_data:
            return None

        # 統合検証システムで検証
        episode_dict = {
            "episode_id": f"{request.person_id}_{episode_type.value}",
            "person_id": request.person_id,
            "person_name": request.person_name,
            "display_name": request.display_name,
            "episode_text": episode_data["episode_text"],
            "episode_age": episode_data["episode_age"],
            "user_age": request.user_age,
            "occupation": request.occupation,
            "category": request.category
        }

        validation_result = self.validator.validate_episode(episode_dict)

        # 自動修正
        if not validation_result.is_valid and self.auto_correct:
            episode_dict = self._attempt_auto_correction(episode_dict, validation_result)
            validation_result = self.validator.validate_episode(episode_dict)

        # 検証失敗時の処理
        if not validation_result.is_valid and self.reject_on_failure:
            return None

        return GeneratedEpisode(
            person_id=request.person_id,
            person_name=request.person_name,
            display_name=request.display_name,
            episode_type=episode_type,
            episode_text=episode_dict["episode_text"],
            episode_age=episode_dict["episode_age"],
            is_valid=validation_result.is_valid,
            validation_result=validation_result
        )

    def _call_llm(
        self,
        request: EpisodeRequest,
        episode_type: EpisodeType
    ) -> Optional[Dict[str, Any]]:
        """
        LLMを呼び出してエピソードテキストと年齢を生成

        Args:
            request: エピソード生成リクエスト
            episode_type: エピソードタイプ

        Returns:
            {"episode_text": str, "episode_age": int}、失敗時はNone
        """
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(request, episode_type)

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",  # 最新モデル
                max_tokens=1024,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            # レスポンスをパース
            response_text = message.content[0].text
            return self._parse_llm_response(response_text)

        except Exception as e:
            print(f"LLM呼び出しエラー: {e}")
            return None

    def _build_system_prompt(self) -> str:
        """システムプロンプトを構築"""
        return """あなたは有名人のエピソード生成システムです。

【重要な制約 - 必ず守ること】
1. **文字数**: 必ず130文字以上250文字以内
2. **年号・日付禁止**: 「2013年」「2020年代」「令和元年」などの年号を絶対に含めない
3. **主観表現禁止**: 以下の表現を絶対に使わない
   - 素晴らしい、すごい、驚異的、圧倒的
   - 感動的、劇的、衝撃的、奇跡的
   - 伝説的、壮大な
4. **数値データ必須**: 具体的な数値（〇〇歳、〇〇本、〇〇回、〇〇億円など）を含める
5. **固有名詞必須**: 大会名、チーム名、作品名などの具体的な固有名詞を含める
6. **年齢重複禁止**: 同じ年齢を2回以上書かない
7. **客観的事実のみ**: 検証可能な具体的事実のみを記述

【出力フォーマット】
以下のJSON形式で出力してください：
```json
{
  "episode_text": "エピソードテキスト（130-250文字）",
  "episode_age": 年齢（整数）
}
```

【エピソード選択基準】
- **定番エピソード**: その人を最も象徴する有名な出来事（誰もが知っている代表的な業績）
- **意外性エピソード**: あまり知られていない意外な事実（マイナーだが興味深い出来事）"""

    def _build_user_prompt(
        self,
        request: EpisodeRequest,
        episode_type: EpisodeType
    ) -> str:
        """ユーザープロンプトを構築"""
        type_description = {
            EpisodeType.ICONIC: "最も定番の有名なエピソード（誰もが知っている代表的な業績）",
            EpisodeType.UNEXPECTED: "最も意外性のあるエピソード（あまり知られていない興味深い事実）"
        }

        prompt = f"""以下の有名人について、{type_description[episode_type]}を生成してください。

【人物情報】
- 名前: {request.person_name}
- 表示名: {request.display_name}
- ユーザー年齢: {request.user_age}歳
- 職業: {request.occupation}
- カテゴリ: {request.category}
- Google検索数: {request.google_search_count:,}回"""

        if request.birth_year:
            prompt += f"\n- 生年: {request.birth_year}年"

        if request.wikipedia_url:
            prompt += f"\n- Wikipedia: {request.wikipedia_url}"

        prompt += f"""

【エピソードタイプ】
{type_description[episode_type]}

【重要な指示】
- 文字数は必ず130-250文字
- 年号・日付は絶対に含めない
- 主観表現は絶対に使わない
- 数値データと固有名詞を必ず含める
- {request.user_age}歳前後の出来事を選択
- エピソードの年齢を推定して記載

JSON形式で出力してください。"""

        return prompt

    def _parse_llm_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """LLMレスポンスをパース"""
        import json
        import re

        # JSONブロックを抽出
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # JSON形式でない場合は全体をJSONとして解釈
            json_str = response_text

        try:
            data = json.loads(json_str)

            # 必須フィールドの確認
            if "episode_text" not in data or "episode_age" not in data:
                return None

            return {
                "episode_text": data["episode_text"],
                "episode_age": int(data["episode_age"])
            }
        except (json.JSONDecodeError, ValueError) as e:
            print(f"LLMレスポンスのパースエラー: {e}")
            return None

    def _attempt_auto_correction(
        self,
        episode: Dict[str, Any],
        validation_result: Any
    ) -> Dict[str, Any]:
        """自動修正を試みる"""
        corrected_text = episode["episode_text"]

        # 年号・日付の削除
        import re
        temporal_patterns = [
            r'\d{4}年(?:\d{1,2}月)?(?:\d{1,2}日)?',
            r'(?:明治|大正|昭和|平成|令和)\d{1,2}年',
            r'\d{4}年代',
        ]
        for pattern in temporal_patterns:
            corrected_text = re.sub(pattern, '', corrected_text)

        # 主観表現の削除
        subjective_keywords = [
            "素晴らしい", "すごい", "驚異的", "圧倒的",
            "感動的", "劇的", "衝撃的", "奇跡的",
            "伝説的", "壮大な"
        ]
        for keyword in subjective_keywords:
            corrected_text = corrected_text.replace(keyword, '')

        # 空白の整理
        corrected_text = re.sub(r'\s+', '', corrected_text)

        episode["episode_text"] = corrected_text
        return episode

    def generate_batch(
        self,
        requests: List[EpisodeRequest],
        output_csv_path: str = "dual_episodes_output.csv"
    ) -> List[Tuple[Optional[GeneratedEpisode], Optional[GeneratedEpisode]]]:
        """
        複数人物のエピソードをバッチ生成

        Args:
            requests: エピソード生成リクエストのリスト
            output_csv_path: 出力CSVファイルパス

        Returns:
            生成されたエピソードのリスト
        """
        import csv
        from datetime import datetime

        results = []
        successful_count = 0
        failed_count = 0

        print(f"\n{'='*80}")
        print(f"バッチエピソード生成 - {len(requests)}人")
        print(f"{'='*80}\n")

        for i, request in enumerate(requests, 1):
            print(f"[{i}/{len(requests)}] {request.display_name} のエピソード生成中...")

            iconic, unexpected = self.generate_episodes_for_person(request)
            results.append((iconic, unexpected))

            # 成功/失敗カウント
            if iconic and iconic.is_valid:
                successful_count += 1
            else:
                failed_count += 1

            if unexpected and unexpected.is_valid:
                successful_count += 1
            else:
                failed_count += 1

            print(f"  定番: {'✅' if iconic and iconic.is_valid else '❌'}")
            print(f"  意外性: {'✅' if unexpected and unexpected.is_valid else '❌'}\n")

        # CSV出力
        self._export_to_csv(results, output_csv_path)

        # サマリー表示
        print(f"\n{'='*80}")
        print("バッチ処理完了")
        print(f"{'='*80}")
        print(f"総エピソード数: {len(requests) * 2}件")
        print(f"成功: {successful_count}件")
        print(f"失敗: {failed_count}件")
        print(f"成功率: {successful_count / (len(requests) * 2) * 100:.1f}%")
        print(f"\nCSV出力: {output_csv_path}")
        print(f"{'='*80}\n")

        return results

    def _export_to_csv(
        self,
        results: List[Tuple[Optional[GeneratedEpisode], Optional[GeneratedEpisode]]],
        output_path: str
    ):
        """結果をCSV出力"""
        import csv

        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)

            # ヘッダー
            writer.writerow([
                "person_id",
                "person_name",
                "display_name",
                "episode_type",
                "episode_text",
                "episode_age",
                "is_valid",
                "violation_count",
                "character_count"
            ])

            # データ行
            for iconic, unexpected in results:
                if iconic:
                    writer.writerow([
                        iconic.person_id,
                        iconic.person_name,
                        iconic.display_name,
                        "iconic",
                        iconic.episode_text,
                        iconic.episode_age,
                        iconic.is_valid,
                        len(iconic.validation_result.violations) if not iconic.is_valid else 0,
                        len(iconic.episode_text)
                    ])

                if unexpected:
                    writer.writerow([
                        unexpected.person_id,
                        unexpected.person_name,
                        unexpected.display_name,
                        "unexpected",
                        unexpected.episode_text,
                        unexpected.episode_age,
                        unexpected.is_valid,
                        len(unexpected.validation_result.violations) if not unexpected.is_valid else 0,
                        len(unexpected.episode_text)
                    ])


def main():
    """テスト実行"""
    # .envファイルから環境変数を読み込み
    from dotenv import load_dotenv
    load_dotenv()

    generator = DualEpisodeGenerator()

    # テストデータ
    test_request = EpisodeRequest(
        person_id="P000001",
        person_name="イチロー",
        display_name="イチロー",
        user_age=35,
        occupation="プロ野球選手",
        category="スポーツ",
        google_search_count=5000000,
        birth_year=1973,
        wikipedia_url="https://ja.wikipedia.org/wiki/イチロー"
    )

    print("=" * 80)
    print("デュアルエピソード生成システム - テスト実行")
    print("=" * 80)
    print(f"\n対象人物: {test_request.display_name}")
    print(f"ユーザー年齢: {test_request.user_age}歳")
    print(f"職業: {test_request.occupation}")
    print(f"カテゴリ: {test_request.category}")
    print("\n" + "-" * 80)

    # エピソード生成
    iconic_episode, unexpected_episode = generator.generate_episodes_for_person(test_request)

    # 結果表示
    print("\n【定番エピソード】")
    if iconic_episode:
        print(f"✅ 生成成功")
        print(f"エピソードテキスト: {iconic_episode.episode_text}")
        print(f"エピソード年齢: {iconic_episode.episode_age}歳")
        print(f"文字数: {len(iconic_episode.episode_text)}文字")
        print(f"検証結果: {'合格' if iconic_episode.is_valid else '不合格'}")
        if not iconic_episode.is_valid:
            print(f"違反数: {iconic_episode.validation_result.violation_count}")
    else:
        print("❌ 生成失敗")

    print("\n" + "-" * 80)
    print("\n【意外性エピソード】")
    if unexpected_episode:
        print(f"✅ 生成成功")
        print(f"エピソードテキスト: {unexpected_episode.episode_text}")
        print(f"エピソード年齢: {unexpected_episode.episode_age}歳")
        print(f"文字数: {len(unexpected_episode.episode_text)}文字")
        print(f"検証結果: {'合格' if unexpected_episode.is_valid else '不合格'}")
        if not unexpected_episode.is_valid:
            print(f"違反数: {unexpected_episode.validation_result.violation_count}")
    else:
        print("❌ 生成失敗")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
