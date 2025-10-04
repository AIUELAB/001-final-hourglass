#!/usr/bin/env python3
"""
エピソード自動改善システム
LLMを使用してインパクト不足のエピソードを自動的に改善
"""

import csv
import os
import sys
import time
import gc
from typing import Dict, List, Optional
from dataclasses import dataclass
from openai import OpenAI

from episode_guardian import create_episode_guardian
from optimized_episode_evaluator import OptimizedEpisodeEvaluator


@dataclass
class ImprovementResult:
    """改善結果"""
    episode_id: str
    person_name: str
    episode_age: int
    original_text: str
    improved_text: str
    original_score: int
    improved_score: int
    phase: str
    success: bool
    error_message: Optional[str] = None


class EpisodeAutoImprover:
    """エピソード自動改善システム"""

    def __init__(self, api_key: Optional[str] = None, batch_size: int = 5):
        """
        Args:
            api_key: OpenAI APIキー
            batch_size: バッチサイズ
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY環境変数が設定されていません")

        self.client = OpenAI(api_key=self.api_key)
        self.guardian = create_episode_guardian()
        self.evaluator = OptimizedEpisodeEvaluator(use_llm=False, batch_size=1)
        self.batch_size = batch_size

        # 成功例（3件）
        self.successful_examples = """
【成功例1: Ado（37点）】
あなたと同じ21歳のとき、Adoはロサンゼルス公演で3000人の会場を完売させ、海外進出に成功した。「うっせぇわ」で顔を公開せずに紅白歌合戦出場とBillboardJapan年間1位を獲得し、匿名アーティストという新しい成功モデルを確立した。YouTubeでの楽曲は若者を中心に広範な支持を集め、新時代の音楽シーンを象徴する存在となった。

【成功例2: 又吉直樹（34点）】
あなたと同じ34歳のとき、又吉直樹は10年間書き続けた小説が芥川賞を受賞し、お笑い芸人から作家への転身を果たした。「火花」は初版10万部が即完売、誰も予想しなかった道に挑んだ決断が、心の奥底から湧き上がる感動を呼び、夢を追う人々に希望を与えた。

【成功例3: 室伏広治（31点）】
あなたと同じ29歳のとき、室伏広治は84m86cmの世界歴代2位記録を樹立し、日本人初の世界陸上ハンマー投げ金メダルを獲得した。父から受け継いだ技術と、数えきれない試練を乗り越えた努力が結実した瞬間、涙が止まらなかった。20個のメダルへと続く栄光の始まりだった。
"""

    def determine_phase(self, score: int) -> str:
        """スコアからPhaseを判定"""
        if score < 10:
            return "phase1"  # 完全書き直し
        elif score < 20:
            return "phase2"  # 部分強化
        else:
            return "phase3"  # 微調整

    def generate_improvement_prompt(
        self,
        episode_text: str,
        person_name: str,
        episode_age: int,
        current_score: int,
        phase: str
    ) -> str:
        """改善用プロンプトを生成"""

        if phase == "phase1":
            # Phase 1: 完全書き直し
            return f"""あなたはエピソード改善の専門家です。
以下のエピソードを、感情的インパクトの高いエピソードに完全に書き直してください。

【人物名】
{person_name}

【年齢】
{episode_age}歳

【現在のエピソード】
{episode_text}

【現在のスコア】
{current_score}/50点

【目標スコア】
30点以上（50点満点）

【絶対禁止表現】
❌ 未来表現: その後、後に、続く、のちに、やがて、将来、これが〜へと続く
❌ 主観表現: 劇的、驚異的、壮大な、素晴らしい、偉大な、圧倒的、見事な
❌ 推測表現: だろう、かもしれない、と思われる

【必須要素（各10点）】
1. 人生の転換点: 明確な「before → after」の変化
2. 意外性: 予想外の展開・方法・決断
3. リスクテイキング: 具体的な挑戦・リスク
4. 共感性: 読者が感情移入できる要素
5. センセーショナル度: 印象に残るインパクト

【推奨要素】
✓ 感情表現: 涙、感動、決意、緊張、不安、希望、喜び
✓ 具体的数値: 金額、人数、順位、記録
✓ 転換点: 人生の大きな決断、方向転換
✓ リスク: 具体的な困難、挑戦

【成功例】
{self.successful_examples}

【制約】
- 文字数: 150文字前後（±10文字）
- 数値を具体的に含める
- 感情表現を含める
- すべて事実に基づく
- 「あなたと同じ{episode_age}歳のとき、」で始める

【出力形式】
改善されたエピソード本文のみを出力してください。説明や解説は不要です。"""

        elif phase == "phase2":
            # Phase 2: 部分強化
            return f"""以下のエピソードを改善してください。

【人物名】
{person_name}

【年齢】
{episode_age}歳

【現在のエピソード】
{episode_text}

【現在のスコア】
{current_score}/50点（あと{30-current_score}点で合格）

【目標スコア】
30点以上

【絶対禁止表現】
❌ 未来表現: その後、後に、続く、のちに、やがて、将来
❌ 主観表現: 劇的、驚異的、壮大な、素晴らしい、偉大な

【改善指示】
現在のエピソードの良い部分は保持しつつ、以下を追加・強化してください：
1. 感情表現: 涙、感動、決意、希望、不安（1-2箇所）
2. 具体的な挑戦やリスク
3. 意外性のある展開
4. 数値をより具体的に

【成功例の要素】
- 又吉直樹: 「10年間書き続けた」「初版10万部即完売」「心の奥底から湧き上がる感動」
- 室伏広治: 「84m86cm」「涙が止まらなかった」「数えきれない試練」

【制約】
- 文字数: 150文字前後
- 事実に基づく
- 「あなたと同じ{episode_age}歳のとき、」で始める

【出力形式】
改善されたエピソード本文のみを出力してください。"""

        else:  # phase3
            # Phase 3: 微調整
            return f"""以下のエピソードを微調整してください。

【人物名】
{person_name}

【年齢】
{episode_age}歳

【現在のエピソード】
{episode_text}

【現在のスコア】
{current_score}/50点（あと{30-current_score}点で合格）

【絶対禁止表現】
❌ 未来表現: その後、後に、続く、のちに、やがて、将来
❌ 主観表現: 劇的、驚異的、壮大な、素晴らしい、偉大な

【調整指示】
以下のいずれか1-2点を追加して30点以上を目指してください：
- 感情表現: 涙、感動、決意、希望、不安を1-2箇所追加
- 数値をより具体的に（金額、人数、順位など）
- 意外性のある一文を追加
- 具体的な困難・挑戦を明示

【制約】
- 文字数: 150文字前後
- 大きく変えない（微調整のみ）
- 元の良い部分は保持
- 「あなたと同じ{episode_age}歳のとき、」で始める

【出力形式】
改善されたエピソード本文のみを出力してください。"""

    def improve_episode(
        self,
        episode: Dict,
        current_score: int
    ) -> ImprovementResult:
        """
        1つのエピソードを改善

        Args:
            episode: エピソードデータ
            current_score: 現在のスコア

        Returns:
            ImprovementResult: 改善結果
        """
        episode_id = episode['episode_id']
        person_name = episode['person_name']
        episode_age = int(episode['episode_age'])
        original_text = episode['episode_text']

        phase = self.determine_phase(current_score)

        try:
            # LLMで改善
            prompt = self.generate_improvement_prompt(
                original_text, person_name, episode_age, current_score, phase
            )

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "あなたはプロのエピソードライターです。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )

            improved_text = response.choices[0].message.content.strip()

            # ルール準拠チェック
            test_episode = episode.copy()
            test_episode['episode_text'] = improved_text
            validation_result = self.guardian.validate_episode(test_episode)

            if not validation_result.is_valid:
                return ImprovementResult(
                    episode_id=episode_id,
                    person_name=person_name,
                    episode_age=episode_age,
                    original_text=original_text,
                    improved_text=improved_text,
                    original_score=current_score,
                    improved_score=0,
                    phase=phase,
                    success=False,
                    error_message=f"ルール違反: {validation_result.message}"
                )

            # 改善後のスコア評価
            improved_result = self.evaluator.evaluate_lightweight(test_episode)
            improved_score = improved_result.impact_keyword_score

            return ImprovementResult(
                episode_id=episode_id,
                person_name=person_name,
                episode_age=episode_age,
                original_text=original_text,
                improved_text=improved_text,
                original_score=current_score,
                improved_score=improved_score,
                phase=phase,
                success=improved_score >= 30
            )

        except Exception as e:
            return ImprovementResult(
                episode_id=episode_id,
                person_name=person_name,
                episode_age=episode_age,
                original_text=original_text,
                improved_text=original_text,
                original_score=current_score,
                improved_score=current_score,
                phase=phase,
                success=False,
                error_message=str(e)
            )

    def improve_all(
        self,
        csv_path: str,
        evaluation_csv: str,
        target_phases: Optional[List[str]] = None
    ) -> List[ImprovementResult]:
        """
        全エピソードを改善

        Args:
            csv_path: 元のエピソードCSV
            evaluation_csv: 評価結果CSV
            target_phases: 対象Phase（Noneの場合は全Phase）

        Returns:
            List[ImprovementResult]: 改善結果リスト
        """
        # 元のエピソードを読み込み
        episodes = self._load_episodes(csv_path)
        episodes_dict = {ep['episode_id']: ep for ep in episodes}

        # 評価結果を読み込み
        scores = self._load_evaluation_scores(evaluation_csv)

        # 改善対象を抽出
        targets = []
        for episode_id, score in scores.items():
            phase = self.determine_phase(score)
            if target_phases is None or phase in target_phases:
                if episode_id in episodes_dict:
                    targets.append((episodes_dict[episode_id], score, phase))

        print(f"\n{'='*80}")
        print(f"エピソード自動改善システム")
        print(f"{'='*80}")
        print(f"対象エピソード: {len(targets)}件")
        if target_phases:
            print(f"対象Phase: {', '.join(target_phases)}")
        print(f"バッチサイズ: {self.batch_size}")
        print(f"{'='*80}\n")

        results = []
        start_time = time.time()

        for i in range(0, len(targets), self.batch_size):
            batch = targets[i:i+self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(targets) + self.batch_size - 1) // self.batch_size

            print(f"[バッチ {batch_num}/{total_batches}] 処理中...", flush=True)
            batch_start = time.time()

            for episode, score, phase in batch:
                print(f"  {episode['episode_id']} {episode['person_name']} "
                      f"({score}点 → {phase}) ", end='', flush=True)

                result = self.improve_episode(episode, score)
                results.append(result)

                if result.success:
                    print(f"✅ {result.improved_score}点")
                else:
                    print(f"❌ {result.error_message or '失敗'}")

                # APIレート制限対策
                time.sleep(1)

            batch_time = time.time() - batch_start
            print(f"  バッチ完了 ({batch_time:.1f}秒)\n")

            # ガベージコレクション
            gc.collect()

        total_time = time.time() - start_time
        print(f"\n{'='*80}")
        print(f"改善完了: {total_time:.1f}秒")
        print(f"{'='*80}\n")

        return results

    def _load_episodes(self, csv_path: str) -> List[Dict]:
        """CSVからエピソードを読み込み"""
        episodes = []
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                episodes.append({
                    'episode_id': row['episode_id'],
                    'person_name': row['person_name'],
                    'episode_age': int(row['episode_age']),
                    'episode_text': row['episode_text'],
                    'category': row.get('category', '')
                })
        return episodes

    def _load_evaluation_scores(self, csv_path: str) -> Dict[str, int]:
        """評価結果からスコアを読み込み"""
        scores = {}
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                episode_id = row['episode_id']
                score = int(row['impact_keyword_score'])
                scores[episode_id] = score
        return scores

    def save_results(self, results: List[ImprovementResult], output_path: str):
        """改善結果をCSVに保存"""
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            fieldnames = [
                'episode_id', 'person_name', 'episode_age', 'phase',
                'original_score', 'improved_score', 'success',
                'original_text', 'improved_text', 'error_message'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for r in results:
                writer.writerow({
                    'episode_id': r.episode_id,
                    'person_name': r.person_name,
                    'episode_age': r.episode_age,
                    'phase': r.phase,
                    'original_score': r.original_score,
                    'improved_score': r.improved_score,
                    'success': r.success,
                    'original_text': r.original_text,
                    'improved_text': r.improved_text,
                    'error_message': r.error_message or ''
                })

    def get_summary_report(self, results: List[ImprovementResult]) -> str:
        """改善結果のサマリーレポート"""
        total = len(results)
        success = sum(1 for r in results if r.success)

        phase1 = [r for r in results if r.phase == 'phase1']
        phase2 = [r for r in results if r.phase == 'phase2']
        phase3 = [r for r in results if r.phase == 'phase3']

        report = f"""
{'='*80}
改善結果サマリー
{'='*80}

総処理数: {total}件
成功: {success}件 ({success/total*100:.1f}%)
失敗: {total-success}件

Phase別:
  Phase 1（完全書き直し）: {len(phase1)}件 → {sum(1 for r in phase1 if r.success)}件成功
  Phase 2（部分強化）: {len(phase2)}件 → {sum(1 for r in phase2 if r.success)}件成功
  Phase 3（微調整）: {len(phase3)}件 → {sum(1 for r in phase3 if r.success)}件成功

スコア改善:
  平均改善: {sum(r.improved_score - r.original_score for r in results)/total:.1f}点

{'='*80}
"""
        return report


def main():
    """メイン処理"""
    if len(sys.argv) < 3:
        print("使用方法: python3 episode_auto_improver.py <episodes.csv> <evaluation.csv> [--phase phase1|phase2|phase3]")
        sys.exit(1)

    episodes_csv = sys.argv[1]
    evaluation_csv = sys.argv[2]

    # Phase指定
    target_phases = None
    if '--phase' in sys.argv:
        idx = sys.argv.index('--phase')
        if idx + 1 < len(sys.argv):
            target_phases = [sys.argv[idx + 1]]

    output_path = episodes_csv.replace('.csv', '_improved.csv')

    improver = EpisodeAutoImprover(batch_size=5)

    # 改善実行
    results = improver.improve_all(episodes_csv, evaluation_csv, target_phases)

    # サマリー表示
    print(improver.get_summary_report(results))

    # 結果保存
    improver.save_results(results, output_path)
    print(f"✅ 改善結果を保存: {output_path}\n")


if __name__ == '__main__':
    main()
