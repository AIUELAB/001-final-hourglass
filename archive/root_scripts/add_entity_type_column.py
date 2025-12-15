#!/usr/bin/env python3
"""
entity_typeカラムを追加してデータベースを改善

個人 (person) とグループ (group) を明確に区別

著者: Claude Code
日付: 2025-10-01
"""

import csv
from typing import Dict, List
import re


class EntityTypeClassifier:
    """エンティティタイプ分類器"""

    # グループ/バンドの明確な識別パターン
    KNOWN_GROUPS = {
        'サカナクション': 'group',
        'XJAPAN': 'group',
        'X JAPAN': 'group',
        'SEKAI NO OWARI': 'group',
        "L'Arc~en~Ciel": 'group',
        'BTS': 'group',
        'GLAY': 'group',
        "B'z": 'group',
        'Mr.Children': 'group',
        'EXILE': 'group',
        '嵐': 'group',
    }

    # グループを示すキーワード（エピソードテキスト内）
    GROUP_KEYWORDS = [
        '結成', 'メンバー', 'バンド', '人組', 'グループ',
        'デビュー', 'コンビ', 'ユニット', 'チーム'
    ]

    def classify(self, name: str, episode_text: str, category: str) -> tuple[str, str]:
        """
        エンティティタイプを分類

        Returns:
            (entity_type, confidence_reason)
        """
        # 1. 既知のグループか確認
        if name in self.KNOWN_GROUPS:
            return 'group', f'既知のグループ: {name}'

        # 2. 個人がグループを結成した話かチェック（優先）
        if '結成' in episode_text:
            # 「○○を結成」「○○と結成」→ 個人が誰かとグループを作った
            if 'を結成' in episode_text or 'と結成' in episode_text:
                return 'person', '個人がグループを結成した話'
            # 「○○は結成」→ グループ自体の話
            elif 'は結成' in episode_text:
                # person_nameがグループ名かチェック
                # グループ名の場合のみgroupと判定
                if episode_text.startswith('あなたがバンド'):
                    return 'group', 'グループの結成年を記述'

        # 3. 個人名のパターン判定（グループ判定より優先）

        # 3a. 日本人の名前（漢字フルネーム）
        if self._is_japanese_person_name(name):
            return 'person', '日本人の名前パターン'

        # 3b. 海外の人名（スペース区切り）
        if ' ' in name and not any(c in name for c in ['&', 'and', 'the']):
            # "Steve Jobs", "Bill Gates" など
            parts = name.split()
            if len(parts) == 2 and parts[0][0].isupper() and parts[1][0].isupper():
                return 'person', '海外の人名パターン'

        # 3c. カタカナのみ（個人の可能性が高い）
        if self._is_katakana_only(name) and len(name) <= 6:
            return 'person', 'カタカナ個人名'

        # 4. グループ関連表現のチェック（個人名パターン判定後）
        group_evidence = []
        for keyword in self.GROUP_KEYWORDS:
            if keyword in episode_text:
                group_evidence.append(keyword)

        # グループの強い証拠があるか（個人名でない場合のみ適用）
        if len(group_evidence) >= 2:
            return 'group', f'グループ関連表現: {", ".join(group_evidence[:3])}'

        # 5. デフォルト: 個人と判定
        return 'person', 'デフォルト判定（個人）'

    def _is_japanese_person_name(self, name: str) -> bool:
        """日本人の名前パターンか判定"""
        # 2-5文字の漢字・ひらがな
        if 2 <= len(name) <= 5:
            # 漢字を含む
            if any('\u4e00' <= c <= '\u9fff' for c in name):
                return True
        return False

    def _is_katakana_only(self, name: str) -> bool:
        """カタカナのみか判定"""
        katakana_pattern = re.compile(r'^[\u30A0-\u30FF]+$')
        return bool(katakana_pattern.match(name))


def main():
    """メイン処理"""
    input_csv = "episodes_final_perfect_20251001.csv"
    output_csv = "episodes_with_entity_type_20251001.csv"

    print("="*80)
    print("entity_typeカラムの追加")
    print("="*80 + "\n")

    # CSVを読み込み
    with open(input_csv, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    classifier = EntityTypeClassifier()

    stats = {
        'person': 0,
        'group': 0
    }

    print("分類中...\n")

    for i, row in enumerate(rows, start=1):
        name = row['person_name']
        text = row['episode_text']
        category = row['category']

        # 分類
        entity_type, reason = classifier.classify(name, text, category)

        # 新しいカラムを追加
        row['entity_type'] = entity_type
        row['classification_reason'] = reason

        stats[entity_type] += 1

        # グループの場合は表示
        if entity_type == 'group':
            print(f"{row['episode_id']}: {name} → GROUP")
            print(f"  理由: {reason}")
            print(f"  テキスト: {text[:60]}...")
            print()

        # 進捗表示
        if i % 20 == 0:
            print(f"進捗: {i}/100 件完了")

    # 出力
    # カラム順序を整理
    ordered_fields = [
        'episode_id',
        'entity_type',  # NEW
        'person_name',
        'episode_age',
        'episode_text',
        'episode_type',
        'character_count',
        'category',
        'is_valid',
        'violation_count',
        'emotional_impact_score',
        'specificity_score',
        'has_numerical_data',
        'has_proper_nouns',
        'fact_check_status',
        'created_date',
        'classification_reason'  # NEW
    ]

    with open(output_csv, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=ordered_fields)
        writer.writeheader()
        writer.writerows(rows)

    # 統計表示
    print(f"\n{'='*80}")
    print("分類結果")
    print(f"{'='*80}\n")
    print(f"👤 個人 (person): {stats['person']}件 ({stats['person']}%)")
    print(f"👥 グループ (group): {stats['group']}件 ({stats['group']}%)")
    print(f"\n出力ファイル: {output_csv}")
    print("="*80 + "\n")

    # グループのリストを表示
    print("="*80)
    print("検出されたグループ一覧")
    print("="*80 + "\n")

    groups = [row for row in rows if row['entity_type'] == 'group']
    for group in groups:
        print(f"- {group['episode_id']}: {group['person_name']} ({group['category']})")


if __name__ == "__main__":
    main()
