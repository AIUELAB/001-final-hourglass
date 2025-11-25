#!/usr/bin/env python3
"""
Phase 4: 失敗3件のエピソード修正システム
名詞止め修正と文字数調整を実施
"""

import pandas as pd
import anthropic
import os
import json
from datetime import datetime
from typing import Dict, Tuple
import time
import shutil

class FailedEpisodeFixer:
    """失敗エピソード修正システム"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY環境変数が設定されていません")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.fix_log = []

        # 修正対象3件
        self.failed_episodes = {
            'P043': {
                '人物名': '玉置浩二',
                '年齢': 24,
                'エピソード': '安全地帯「ワインレッドの心」発表',
                '問題': '名詞止め（丁寧体率80%）',
                '修正指示': '「記録」などの名詞止めを「記録しました」などの丁寧体に変更。すべての文を「です・ます調」で終わらせる。'
            },
            'P154': {
                '人物名': '西野亮廣',
                '年齢': 37,
                'エピソード': '「えんとつ町のプペル」ヒット',
                '問題': '名詞止め（丁寧体率75%）',
                '修正指示': '「達成」などの名詞止めを「達成しました」などの丁寧体に変更。すべての文を「です・ます調」で終わらせる。'
            },
            'P164': {
                '人物名': '三木谷浩史',
                '年齢': 32,
                'エピソード': '楽天創業',
                '問題': '文字数超過（286文字）',
                '修正指示': '文字数を280文字以内に削減。不要な修飾語や重複表現を削除し、簡潔にする。丁寧体は維持。'
            }
        }

    def fix_episode(self, person_id: str, fix_data: Dict) -> Tuple[str, Dict]:
        """
        エピソードを修正

        Args:
            person_id: 人物ID
            fix_data: 修正データ

        Returns:
            (修正後エピソード, メタデータ)
        """

        prompt = f"""以下のエピソードを修正してください。

【人物情報】
人物名: {fix_data['人物名']}
年齢: {fix_data['年齢']}歳
エピソード内容: {fix_data['エピソード']}

【問題点】
{fix_data['問題']}

【修正指示】
{fix_data['修正指示']}

【エピソード生成ルール（厳守）】
1. **すべての文を丁寧体（です・ます調）で終わらせる**
2. **名詞止めは絶対に使わない**（例: 「記録」→「記録しました」）
3. **文字数: 175-280文字厳守**
4. 固有名詞・数値・日付を正確に
5. 「あなたと同じ{fix_data['年齢']}歳のとき、{fix_data['人物名']}は...」で始める
6. 社会的影響・歴史的意義を強調
7. 簡潔で読みやすい文章にする

【重要】
- 文末は必ず「ました」「でした」「ます」「です」のいずれかで終わること
- 名詞、形容詞、動詞の連用形で文を終わらせないこと

【修正後のエピソード】
"""

        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            fixed_episode = message.content[0].text.strip()

            # メタデータ
            metadata = {
                'person_id': person_id,
                'person_name': fix_data['人物名'],
                'age': fix_data['年齢'],
                'episode_title': fix_data['エピソード'],
                'problem': fix_data['問題'],
                'length': len(fixed_episode),
                'tokens_used': message.usage.input_tokens + message.usage.output_tokens,
                'success': True
            }

            return fixed_episode, metadata

        except Exception as e:
            print(f"❌ エラー（{fix_data['人物名']}）: {e}")
            metadata = {
                'person_id': person_id,
                'person_name': fix_data['人物名'],
                'error': str(e),
                'success': False
            }
            return None, metadata

    def validate_episode(self, episode: str) -> Dict:
        """エピソードを検証"""
        from rules.rule_190_polite_tone_validator import PoliteToneValidator

        validator = PoliteToneValidator()
        result = validator.validate(episode)

        return {
            'polite_tone_valid': result['valid'],
            'polite_rate': result['polite_rate'],
            'length': len(episode),
            'length_valid': 175 <= len(episode) <= 280,
            'issues': result.get('issues', [])
        }

    def fix_failed_episodes(self, input_file: str, output_file: str) -> Dict:
        """
        失敗3件のエピソードを修正

        Args:
            input_file: 入力CSVファイル
            output_file: 出力CSVファイル

        Returns:
            修正統計情報
        """

        # バックアップ作成
        backup_dir = "backups/episode_replacement"
        os.makedirs(backup_dir, exist_ok=True)
        backup_file = f"{backup_dir}/{os.path.basename(input_file)}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(input_file, backup_file)
        print(f"✅ バックアップ作成: {backup_file}")

        # データ読み込み
        df = pd.read_csv(input_file)

        print("\n" + "=" * 70)
        print("Phase 4: 失敗3件エピソード修正")
        print("=" * 70)

        successful_fixes = 0
        failed_fixes = 0
        validation_results = []

        for person_id, fix_data in self.failed_episodes.items():
            print(f"\n[{successful_fixes + failed_fixes + 1}/3] {fix_data['人物名']}")
            print(f"修正内容: {fix_data['問題']}")

            # エピソード修正
            fixed_episode, metadata = self.fix_episode(person_id, fix_data)

            if fixed_episode:
                # 検証
                validation = self.validate_episode(fixed_episode)

                print(f"修正後文字数: {len(fixed_episode)}文字")
                print(f"丁寧体率: {validation['polite_rate']:.1f}%")

                if validation['polite_tone_valid'] and validation['length_valid']:
                    # データベース更新
                    df.loc[df['人物ID'] == person_id, 'エピソード本文'] = fixed_episode
                    df.loc[df['人物ID'] == person_id, '年齢'] = fix_data['年齢']
                    df.loc[df['人物ID'] == person_id, '文字数'] = len(fixed_episode)

                    print("✅ 修正成功")
                    successful_fixes += 1
                else:
                    print(f"⚠️ 検証失敗: 丁寧体率{validation['polite_rate']:.1f}%, 文字数{len(fixed_episode)}")
                    if validation['issues']:
                        for issue in validation['issues'][:3]:
                            print(f"   - {issue}")
                    failed_fixes += 1

                validation_results.append({
                    **metadata,
                    **validation
                })

                self.fix_log.append({
                    **metadata,
                    **validation
                })
            else:
                print("❌ 修正失敗")
                failed_fixes += 1

            # レート制限対策
            time.sleep(1)

        # 出力
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n✅ 修正完了: {output_file}")

        # 統計情報
        stats = {
            'total_fixes': len(self.failed_episodes),
            'successful_fixes': successful_fixes,
            'failed_fixes': failed_fixes,
            'success_rate': f"{successful_fixes / len(self.failed_episodes) * 100:.1f}%",
            'total_tokens': sum(log.get('tokens_used', 0) for log in self.fix_log if log.get('success')),
            'fix_log': self.fix_log,
            'validation_results': validation_results
        }

        return stats


def main():
    """メイン処理"""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    input_file = "final_hourglass_high_priority_20251008_210211.csv"
    output_file = f"final_hourglass_phase4_complete_{timestamp}.csv"

    print("=" * 70)
    print("Phase 4: 失敗3件エピソード修正システム")
    print("=" * 70)

    # 環境変数チェック
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ エラー: ANTHROPIC_API_KEY環境変数が設定されていません")
        return

    # 修正実行
    fixer = FailedEpisodeFixer()

    try:
        stats = fixer.fix_failed_episodes(input_file, output_file)

        # 結果レポート
        print("\n" + "=" * 70)
        print("📊 修正結果サマリー")
        print("=" * 70)
        print(f"総修正対象: {stats['total_fixes']}件")
        print(f"成功: {stats['successful_fixes']}件")
        print(f"失敗: {stats['failed_fixes']}件")
        print(f"成功率: {stats['success_rate']}")
        print(f"使用トークン数: {stats['total_tokens']:,}トークン")
        print(f"推定コスト: ${stats['total_tokens'] * 0.000003:.2f}")

        # ログ保存
        log_file = f"fix_failed_episodes_log_{timestamp}.json"
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        print(f"\n📝 ログ保存: {log_file}")

    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
