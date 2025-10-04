#!/usr/bin/env python3
"""
2エピソード簡易テスト

目的: システムが正常に動作することを短時間で確認
"""

import csv
import json
import time
from datetime import datetime

from batch_high_quality_generator import BatchHighQualityGenerator


def main():
    """メイン処理"""

    print(f"\n{'='*80}")
    print(f"2エピソード簡易テスト")
    print(f"{'='*80}\n")

    # テストデータ（2件のみ）
    test_episodes = [
        {
            'person_name': 'Ado',
            'episode_age': '21',
            'episode_id': 'EP001',
            'episode_text': 'あなたと同じ21歳のとき、Adoはロサンゼルス公演で3000人の会場を完売させ、海外進出に成功した。',
            'wikipedia_summary': None
        },
        {
            'person_name': '新垣結衣',
            'episode_age': '18',
            'episode_id': 'EP052',
            'episode_text': 'あなたと同じ18歳のとき、新垣結衣は江崎グリコのポッキーCM「ポッキーダンス」に出演し、芸能界でのブレイクを果たした。',
            'wikipedia_summary': None
        }
    ]

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # prompt_optimizedモードでテスト
    print(f"【モード: prompt_optimized】\n")

    batch_gen = BatchHighQualityGenerator(
        provider="openai",
        mode="prompt_optimized",
        max_workers=2,
        pass_threshold=60
    )

    result = batch_gen.process_episodes_list(
        test_episodes,
        output_csv=f"test_2episodes_prompt_optimized_{timestamp}.csv",
        verbose=True
    )

    print(f"\n{'='*80}")
    print(f"✅ 2エピソード簡易テスト完了")
    print(f"{'='*80}\n")

    print(f"平均スコア: {result.avg_score:.1f}点")
    print(f"合格率: {result.pass_rate*100:.1f}%")
    print(f"処理時間: {result.processing_time:.1f}秒")
    print(f"推定コスト: ${result.total_cost:.4f}")


if __name__ == '__main__':
    main()
