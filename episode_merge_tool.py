"""
Episode Merge Tool
==================

新規生成エピソードを既存データベースとマージするツール

機能:
- 既存エピソードとの重複チェック
- 品質スコアに基づく選択的マージ
- バックアップ作成
- 統計レポート生成

実行コマンド:
    python3 episode_merge_tool.py --new episodes_generated.csv --existing episodes_validated_100.csv --output episodes_merged.csv
"""

import argparse
import csv
import json
from typing import List, Dict, Set
from datetime import datetime
from pathlib import Path
import shutil


class EpisodeMergeTool:
    """エピソードマージツール"""

    def __init__(
        self,
        min_gate_score: float = 8.0,
        min_total_score: float = 25.0,
        prefer_new: bool = False
    ):
        """
        初期化

        Args:
            min_gate_score: 最小Gateスコア
            min_total_score: 最小総合スコア
            prefer_new: 重複時に新規エピソードを優先
        """
        self.min_gate_score = min_gate_score
        self.min_total_score = min_total_score
        self.prefer_new = prefer_new

        self.stats = {
            'existing_count': 0,
            'new_count': 0,
            'merged_count': 0,
            'duplicates': 0,
            'quality_rejected': 0,
            'new_added': 0,
            'replaced': 0
        }

    def load_csv(self, csv_path: str) -> List[Dict]:
        """CSVファイルを読み込み"""
        episodes = []
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                episodes.append(row)
        return episodes

    def create_backup(self, original_path: str) -> str:
        """バックアップを作成"""
        backup_path = f"{original_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(original_path, backup_path)
        print(f"📦 Backup created: {backup_path}")
        return backup_path

    def normalize_episode(self, episode: Dict) -> Dict:
        """エピソードデータを正規化"""
        normalized = {
            'person_name': episode.get('person_name') or episode.get('name', ''),
            'episode_age': int(episode.get('episode_age') or episode.get('age', 0)),
            'category': episode.get('category', ''),
            'episode_text': episode.get('episode_text', ''),
            'character_count': int(episode.get('character_count') or len(episode.get('episode_text', ''))),
        }

        # スコア情報
        gate_score = episode.get('gate_score')
        llm_score = episode.get('llm_score')
        total_score = episode.get('total_score')

        # 既存データの場合はemotional_impact_scoreを使用
        if not gate_score and episode.get('emotional_impact_score'):
            gate_score = float(episode.get('emotional_impact_score', 0)) / 5  # 50点→10点換算

        normalized.update({
            'gate_score': float(gate_score) if gate_score and gate_score != '' else None,
            'llm_score': float(llm_score) if llm_score and llm_score != '' else None,
            'total_score': float(total_score) if total_score and total_score != '' else None,
        })

        # その他の情報を保持
        for key in ['person_id', 'birth_year', 'iterations', 'tokens_used',
                    'generation_time', 'generated_at', 'success']:
            if key in episode:
                normalized[key] = episode[key]

        return normalized

    def get_episode_key(self, episode: Dict) -> str:
        """エピソードの一意キーを生成"""
        return f"{episode['person_name']}_{episode['episode_age']}"

    def check_quality(self, episode: Dict) -> bool:
        """品質基準を満たすかチェック"""
        gate_score = episode.get('gate_score')
        total_score = episode.get('total_score')

        # Gateスコアチェック
        if gate_score is not None and gate_score < self.min_gate_score:
            return False

        # 総合スコアチェック（存在する場合）
        if total_score is not None and total_score < self.min_total_score:
            return False

        # 文字数チェック
        char_count = episode.get('character_count', 0)
        if char_count < 180 or char_count > 250:
            return False

        return True

    def select_better_episode(self, existing: Dict, new: Dict) -> Dict:
        """より良いエピソードを選択"""
        # prefer_newフラグがある場合は新規を優先
        if self.prefer_new:
            return new

        # 総合スコアで比較
        existing_score = existing.get('total_score') or existing.get('gate_score', 0)
        new_score = new.get('total_score') or new.get('gate_score', 0)

        if new_score > existing_score:
            return new
        else:
            return existing

    def merge(
        self,
        existing_episodes: List[Dict],
        new_episodes: List[Dict]
    ) -> List[Dict]:
        """
        エピソードをマージ

        Args:
            existing_episodes: 既存エピソードリスト
            new_episodes: 新規エピソードリスト

        Returns:
            マージ済みエピソードリスト
        """
        print(f"\n{'='*80}")
        print(f"🔄 Episode Merge Process")
        print(f"{'='*80}")

        # 既存エピソードを正規化してインデックス化
        existing_map = {}
        for ep in existing_episodes:
            normalized = self.normalize_episode(ep)
            key = self.get_episode_key(normalized)
            existing_map[key] = normalized

        self.stats['existing_count'] = len(existing_map)
        print(f"📊 Existing episodes: {self.stats['existing_count']}")

        # 新規エピソードを処理
        merged_map = existing_map.copy()

        for ep in new_episodes:
            normalized = self.normalize_episode(ep)
            key = self.get_episode_key(normalized)

            # 品質チェック
            if not self.check_quality(normalized):
                self.stats['quality_rejected'] += 1
                print(f"❌ Quality rejected: {normalized['person_name']} ({normalized['episode_age']}歳)")
                continue

            # 重複チェック
            if key in merged_map:
                self.stats['duplicates'] += 1
                # より良いエピソードを選択
                better = self.select_better_episode(merged_map[key], normalized)
                if better == normalized:
                    merged_map[key] = normalized
                    self.stats['replaced'] += 1
                    print(f"🔄 Replaced: {normalized['person_name']} ({normalized['episode_age']}歳)")
                else:
                    print(f"⏭️ Kept existing: {normalized['person_name']} ({normalized['episode_age']}歳)")
            else:
                merged_map[key] = normalized
                self.stats['new_added'] += 1
                print(f"✅ Added new: {normalized['person_name']} ({normalized['episode_age']}歳)")

        self.stats['new_count'] = len(new_episodes)
        self.stats['merged_count'] = len(merged_map)

        return list(merged_map.values())

    def save_merged(self, episodes: List[Dict], output_path: str) -> None:
        """マージ結果を保存（UTF-8 BOM付き）"""
        # フィールド名を決定
        all_fields = set()
        for ep in episodes:
            all_fields.update(ep.keys())

        # 優先順位付きフィールドリスト
        priority_fields = [
            'person_id',
            'person_name',
            'episode_age',
            'category',
            'episode_text',
            'character_count',
            'gate_score',
            'llm_score',
            'total_score',
            'iterations',
            'tokens_used',
            'generation_time',
            'generated_at'
        ]

        # フィールド順序を決定
        fieldnames = [f for f in priority_fields if f in all_fields]
        fieldnames.extend(sorted(all_fields - set(fieldnames)))

        # UTF-8 BOM付きで保存
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for ep in episodes:
                # None値を空文字列に変換
                row = {k: (v if v is not None else '') for k, v in ep.items()}
                writer.writerow(row)

        print(f"\n💾 Merged episodes saved to: {output_path}")

    def print_statistics(self) -> None:
        """統計情報を表示"""
        print(f"\n{'='*80}")
        print(f"📊 Merge Statistics")
        print(f"{'='*80}")
        print(f"Existing Episodes: {self.stats['existing_count']}")
        print(f"New Episodes: {self.stats['new_count']}")
        print(f"Quality Rejected: {self.stats['quality_rejected']}")
        print(f"Duplicates Found: {self.stats['duplicates']}")
        print(f"Replaced: {self.stats['replaced']}")
        print(f"New Added: {self.stats['new_added']}")
        print(f"Total Merged: {self.stats['merged_count']}")
        print(f"{'='*80}\n")

    def save_report(self, output_path: str) -> None:
        """レポートをJSON形式で保存"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'statistics': self.stats,
            'settings': {
                'min_gate_score': self.min_gate_score,
                'min_total_score': self.min_total_score,
                'prefer_new': self.prefer_new
            }
        }

        report_path = output_path.replace('.csv', '_report.json')
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"📄 Report saved to: {report_path}")


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="Episode Merge Tool")

    parser.add_argument(
        '--new',
        required=True,
        help='New episodes CSV file'
    )
    parser.add_argument(
        '--existing',
        required=True,
        help='Existing episodes CSV file'
    )
    parser.add_argument(
        '--output',
        default=f'episodes_merged_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
        help='Output CSV file'
    )

    parser.add_argument(
        '--min-gate-score',
        type=float,
        default=8.0,
        help='Minimum gate score (default: 8.0)'
    )
    parser.add_argument(
        '--min-total-score',
        type=float,
        default=25.0,
        help='Minimum total score (default: 25.0)'
    )
    parser.add_argument(
        '--prefer-new',
        action='store_true',
        help='Prefer new episodes on conflict'
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Skip backup creation'
    )

    args = parser.parse_args()

    try:
        # マージツール初期化
        merger = EpisodeMergeTool(
            min_gate_score=args.min_gate_score,
            min_total_score=args.min_total_score,
            prefer_new=args.prefer_new
        )

        # バックアップ作成
        if not args.no_backup:
            merger.create_backup(args.existing)

        # エピソード読み込み
        print(f"📂 Loading existing episodes: {args.existing}")
        existing = merger.load_csv(args.existing)

        print(f"📂 Loading new episodes: {args.new}")
        new = merger.load_csv(args.new)

        # マージ実行
        merged = merger.merge(existing, new)

        # 保存
        merger.save_merged(merged, args.output)

        # 統計表示
        merger.print_statistics()

        # レポート保存
        merger.save_report(args.output)

        print(f"✅ Merge complete!")
        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
