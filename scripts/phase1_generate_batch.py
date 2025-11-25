#!/usr/bin/env python3
"""
Phase 1: バッチエピソード生成スクリプト

phase1_pilot_persons.jsonの20人全員のエピソードを一括生成します。
進捗状況をリアルタイムで表示し、失敗時のリトライ機能も実装。
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 単一エピソード生成クラスをインポート
from scripts.phase1_generate_episode_single import EpisodeGeneratorSingle


class BatchEpisodeGenerator:
    """バッチエピソード生成クラス"""

    def __init__(self, pilot_persons_file: str = "phase1_pilot_persons.json"):
        self.pilot_persons_file = pilot_persons_file
        self.generator = EpisodeGeneratorSingle()
        self.results = {
            "success": [],
            "failed": [],
            "skipped": [],
        }

    def load_pilot_persons(self) -> List[Dict[str, Any]]:
        """パイロット人物リストをロード"""
        try:
            with open(self.pilot_persons_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data["persons"]
        except Exception as e:
            print(f"❌ ファイル読み込みエラー: {e}")
            return []

    def check_existing_episodes(self, person_id: str) -> bool:
        """既存エピソードの確認"""
        cursor = self.generator.conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) as count
            FROM episodes
            WHERE person_id = ?
        """,
            (person_id,),
        )
        row = cursor.fetchone()
        return row["count"] > 0

    def generate_batch(self, max_retries: int = 2, skip_existing: bool = True):
        """バッチ生成実行"""
        persons = self.load_pilot_persons()

        if not persons:
            print("❌ 人物リストが空です")
            return

        total = len(persons)
        print(f"\n{'=' * 70}")
        print("  Phase 1: バッチエピソード生成")
        print(f"{'=' * 70}")
        print(f"\n対象人数: {total}人")
        print(f"リトライ回数: 最大{max_retries}回")
        print(f"既存スキップ: {'有効' if skip_existing else '無効'}")
        print()

        for idx, person in enumerate(persons, 1):
            person_id = person["person_id"]
            person_name = person["person_name_ja"]

            print(f"\n{'─' * 70}")
            print(f"[{idx}/{total}] {person_name} ({person_id})")
            print(f"{'─' * 70}")

            # 既存チェック
            if skip_existing and self.check_existing_episodes(person_id):
                print("⏭️ スキップ: 既にエピソードが存在します")
                self.results["skipped"].append(
                    {"person_id": person_id, "person_name": person_name, "reason": "already_exists"}
                )
                continue

            # リトライループ
            success = False
            for attempt in range(max_retries + 1):
                if attempt > 0:
                    print(f"\n🔄 リトライ {attempt}/{max_retries}...")
                    time.sleep(2)  # API レート制限対策

                try:
                    success = self.generator.generate_single_episode(person_id, auto_approve=True)

                    if success:
                        print("✅ 成功")
                        self.results["success"].append(
                            {"person_id": person_id, "person_name": person_name, "attempts": attempt + 1}
                        )
                        break

                except Exception as e:
                    print(f"❌ エラー: {e}")
                    if attempt == max_retries:
                        print("⚠️ リトライ上限に達しました")

            # 失敗記録
            if not success:
                self.results["failed"].append(
                    {"person_id": person_id, "person_name": person_name, "attempts": max_retries + 1}
                )

            # 進捗表示
            completed = len(self.results["success"])
            failed = len(self.results["failed"])
            skipped = len(self.results["skipped"])
            progress = (idx / total) * 100

            print(f"\n📊 進捗: {idx}/{total} ({progress:.1f}%)")
            print(f"   ✅ 成功: {completed} | ❌ 失敗: {failed} | ⏭️ スキップ: {skipped}")

            # API レート制限対策（次の人物まで待機）
            if idx < total:
                time.sleep(1)

    def print_summary(self):
        """結果サマリーを表示"""
        total = len(self.results["success"]) + len(self.results["failed"]) + len(self.results["skipped"])
        success_count = len(self.results["success"])
        failed_count = len(self.results["failed"])
        skipped_count = len(self.results["skipped"])

        print(f"\n{'=' * 70}")
        print("  バッチ生成完了サマリー")
        print(f"{'=' * 70}")
        print("\n📊 全体結果:")
        print(f"   対象人数: {total}人")
        print(f"   ✅ 成功: {success_count}人 ({success_count/total*100:.1f}%)")
        print(f"   ❌ 失敗: {failed_count}人 ({failed_count/total*100:.1f}%)")
        print(f"   ⏭️ スキップ: {skipped_count}人 ({skipped_count/total*100:.1f}%)")

        if self.results["success"]:
            print("\n✅ 成功した人物:")
            for r in self.results["success"]:
                attempts_str = f"({r['attempts']}回目)" if r["attempts"] > 1 else ""
                print(f"   - {r['person_name']} {attempts_str}")

        if self.results["failed"]:
            print("\n❌ 失敗した人物:")
            for r in self.results["failed"]:
                print(f"   - {r['person_name']} ({r['attempts']}回試行)")

        if self.results["skipped"]:
            print("\n⏭️ スキップした人物:")
            for r in self.results["skipped"]:
                print(f"   - {r['person_name']} ({r['reason']})")

        print(f"\n{'=' * 70}")

        # 結果をファイルに保存
        self.save_results()

    def save_results(self):
        """結果をファイルに保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"phase1_batch_results_{timestamp}.json"

        output = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_persons": len(self.results["success"])
                + len(self.results["failed"])
                + len(self.results["skipped"]),
                "success_count": len(self.results["success"]),
                "failed_count": len(self.results["failed"]),
                "skipped_count": len(self.results["skipped"]),
            },
            "results": self.results,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"\n💾 結果を保存: {output_file}")

    def close(self):
        """クリーンアップ"""
        self.generator.close()


def main():
    """メイン処理"""
    print("=" * 70)
    print("  Phase 1: バッチエピソード生成")
    print("=" * 70)

    # コマンドライン引数
    skip_existing = "--force" not in sys.argv
    max_retries = 2

    if "--retries" in sys.argv:
        try:
            retries_idx = sys.argv.index("--retries")
            max_retries = int(sys.argv[retries_idx + 1])
        except (IndexError, ValueError):
            print("⚠️ --retries の値が不正です。デフォルト(2)を使用します")

    generator = BatchEpisodeGenerator()

    try:
        generator.generate_batch(max_retries=max_retries, skip_existing=skip_existing)
        generator.print_summary()

        success_rate = (
            len(generator.results["success"])
            / (len(generator.results["success"]) + len(generator.results["failed"]))
            * 100
            if (len(generator.results["success"]) + len(generator.results["failed"])) > 0
            else 0
        )

        if success_rate >= 90:
            print(f"\n🎉 Phase 1成功基準達成！ (成功率: {success_rate:.1f}% >= 90%)")
            return 0
        else:
            print(f"\n⚠️ 成功率不足: {success_rate:.1f}% < 90%")
            print("   失敗した人物の再生成が必要です")
            return 1

    finally:
        generator.close()


if __name__ == "__main__":
    sys.exit(main())
