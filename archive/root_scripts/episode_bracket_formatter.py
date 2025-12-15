#!/usr/bin/env python3
"""
エピソード括弧表示フォーマッター
Episode Bracket Display Formatter

グループメンバー・架空キャラクターの名前横に括弧でグループ名・作品名を表示する
機能を提供します。

機能:
1. グループメンバー: `髙比良くるま(令和ロマン)` のように表示
2. 架空キャラクター: `モンキー・D・ルフィ（ONE PIECE）` のように表示
3. RULE_171チェック: 括弧内ワードがエピソード本文に重複していないか検証

Created: 2025-10-02
"""

import pandas as pd
import re
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class PersonDisplayInfo:
    """人物表示情報"""
    person_name: str
    entity_type: str
    group_name: Optional[str] = None
    group_type: Optional[str] = None
    work_title: Optional[str] = None

    def get_display_name(self) -> str:
        """表示用名前を取得（括弧付き）"""

        # グループメンバーの場合
        if self.group_name:
            return f"{self.person_name}({self.group_name})"

        # 架空キャラクターの場合
        if self.work_title:
            return f"{self.person_name}（{self.work_title}）"

        # それ以外は名前のみ
        return self.person_name

    def get_bracket_word(self) -> Optional[str]:
        """括弧内ワードを取得"""
        if self.group_name:
            return self.group_name
        if self.work_title:
            return self.work_title
        return None


class EpisodeBracketFormatter:
    """エピソード括弧表示フォーマッター"""

    def __init__(self, enriched_csv_path: str):
        self.df = pd.read_csv(enriched_csv_path)

    def format_episode_text(
        self,
        person_name: str,
        user_age: int,
        episode_age: int,
        episode_text: str,
        display_info: PersonDisplayInfo
    ) -> str:
        """エピソードテキストをフォーマット

        元のフォーマット:
        `あなたと同じ30歳のとき、髙比良くるまは`

        新しいフォーマット:
        `あなたと同じ30歳のとき、髙比良くるま(令和ロマン)は`
        """

        display_name = display_info.get_display_name()

        # エピソードテキストの先頭パターンを置換
        # 通常: `あなたと同じ30歳のとき、髙比良くるまは`
        pattern = f"あなたと同じ{user_age}歳のとき、{person_name}は"
        replacement = f"あなたと同じ{user_age}歳のとき、{display_name}は"

        formatted_text = episode_text.replace(pattern, replacement, 1)

        return formatted_text

    def check_rule_171_violation(
        self,
        episode_text: str,
        display_info: PersonDisplayInfo
    ) -> Dict:
        """RULE_171違反チェック

        括弧内ワードがエピソード本文に重複していないか検証
        """

        bracket_word = display_info.get_bracket_word()

        if not bracket_word or (isinstance(bracket_word, float) and pd.isna(bracket_word)):
            # 括弧表示がない場合はチェック不要
            return {
                'valid': True,
                'violation': None,
                'message': None
            }

        # 文字列に変換
        bracket_word = str(bracket_word)

        # スペース除去版もチェック（XJAPANとX JAPANの両方を検出）
        bracket_word_nospace = bracket_word.replace(" ", "")

        # エピソード本文に括弧内ワードが含まれているか
        if bracket_word in episode_text or bracket_word_nospace in episode_text:
            return {
                'valid': False,
                'violation': 'RULE_171',
                'message': f'括弧内ワード「{bracket_word}」がエピソード本文に重複'
            }

        return {
            'valid': True,
            'violation': None,
            'message': None
        }

    def format_all_episodes(self) -> pd.DataFrame:
        """全エピソードをフォーマット"""

        formatted_df = self.df.copy()

        # 新規カラム追加
        formatted_df['person_name_display'] = None
        formatted_df['rule_171_valid'] = True
        formatted_df['rule_171_message'] = None

        for idx, row in formatted_df.iterrows():
            person_name = row['person_name']
            entity_type = row.get('entity_type', 'person')
            group_name = row.get('group_name')
            group_type = row.get('group_type')
            work_title = row.get('work_title') if 'work_title' in formatted_df.columns else None

            # PersonDisplayInfo作成
            display_info = PersonDisplayInfo(
                person_name=person_name,
                entity_type=entity_type,
                group_name=group_name,
                group_type=group_type,
                work_title=work_title
            )

            # 表示名を設定
            display_name = display_info.get_display_name()
            formatted_df.at[idx, 'person_name_display'] = display_name

            # エピソードテキストをフォーマット
            user_age = row['user_age']
            episode_age = row['episode_age']
            episode_text = row['episode_text']

            formatted_text = self.format_episode_text(
                person_name, user_age, episode_age, episode_text, display_info
            )
            formatted_df.at[idx, 'episode_text'] = formatted_text

            # RULE_171違反チェック
            violation_check = self.check_rule_171_violation(formatted_text, display_info)
            formatted_df.at[idx, 'rule_171_valid'] = violation_check['valid']
            formatted_df.at[idx, 'rule_171_message'] = violation_check['message']

        return formatted_df

    def generate_report(self, formatted_df: pd.DataFrame) -> Dict:
        """フォーマット結果レポート生成"""

        total = len(formatted_df)

        # 括弧表示の統計
        has_group = formatted_df['group_name'].notna().sum()
        has_work = formatted_df['work_title'].notna().sum() if 'work_title' in formatted_df.columns else 0
        has_bracket = has_group + has_work

        # RULE_171違反
        rule_171_violations = formatted_df[formatted_df['rule_171_valid'] == False]

        report = {
            'total_episodes': total,
            'bracket_display': {
                'total': has_bracket,
                'group_members': has_group,
                'fictional_characters': has_work
            },
            'rule_171_check': {
                'total_violations': len(rule_171_violations),
                'violations': rule_171_violations[[
                    'person_name', 'person_name_display', 'group_name', 'rule_171_message'
                ]].to_dict('records') if len(rule_171_violations) > 0 else []
            }
        }

        return report

    def export_formatted_csv(self, formatted_df: pd.DataFrame, output_path: str):
        """フォーマット済みCSVをエクスポート"""
        formatted_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"✅ フォーマット済みCSV保存: {output_path}")


def main():
    """メイン実行"""
    print("="*70)
    print("📝 エピソード括弧表示フォーマッター")
    print("="*70)

    # エンリッチCSVを読み込み
    enriched_csv = "verification_results/episodes_enriched_with_groups_20251002_103535.csv"

    formatter = EpisodeBracketFormatter(enriched_csv)

    # 全エピソードをフォーマット
    print("\n🔄 全エピソードをフォーマット中...")
    formatted_df = formatter.format_all_episodes()

    # レポート生成
    report = formatter.generate_report(formatted_df)

    # 結果表示
    print("\n" + "="*70)
    print("📊 フォーマット結果")
    print("="*70)
    print(f"総エピソード数: {report['total_episodes']}")
    print(f"\n🎭 括弧表示:")
    print(f"  合計: {report['bracket_display']['total']}")
    print(f"  グループメンバー: {report['bracket_display']['group_members']}")
    print(f"  架空キャラクター: {report['bracket_display']['fictional_characters']}")

    print(f"\n🔍 RULE_171チェック:")
    if report['rule_171_check']['total_violations'] == 0:
        print("  ✅ 違反なし")
    else:
        print(f"  ❌ 違反: {report['rule_171_check']['total_violations']}件")
        for violation in report['rule_171_check']['violations']:
            print(f"    - {violation['person_name']} ({violation['person_name_display']})")
            print(f"      {violation['rule_171_message']}")

    # フォーマット済みCSVを保存
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"verification_results/episodes_with_brackets_{timestamp}.csv"
    formatter.export_formatted_csv(formatted_df, output_path)

    print("\n" + "="*70)
    print("✅ フォーマット完了")
    print("="*70)

    return formatted_df, report


if __name__ == "__main__":
    main()
