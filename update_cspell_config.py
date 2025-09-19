#!/usr/bin/env python3
"""
cSpell設定自動更新スクリプト
CSVファイルから固有名詞を自動抽出し、cSpell設定を更新する
"""

import csv
import json
import re
import os
from pathlib import Path
from typing import Set, List, Dict

class CSpellConfigUpdater:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.cspell_config_path = self.project_root / ".cspell.json"
        self.cspell_ignore_path = self.project_root / ".cspellignore"
        self.csv_patterns = ["deletion_results/*.csv", "deletion_backups/*.csv"]

    def extract_proper_nouns_from_csv(self) -> Set[str]:
        """CSVファイルから固有名詞を抽出"""
        proper_nouns = set()

        for pattern in self.csv_patterns:
            for csv_file in self.project_root.glob(pattern):
                try:
                    with open(csv_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            # person_name列から固有名詞を抽出
                            if 'person_name' in row:
                                name = row['person_name'].strip()
                                if name and self._is_proper_noun(name):
                                    proper_nouns.add(name)

                            # person_name_display列からも抽出
                            if 'person_name_display' in row:
                                display_name = row['person_name_display'].strip()
                                if display_name and self._is_proper_noun(display_name):
                                    proper_nouns.add(display_name)

                except Exception as e:
                    print(f"Error reading {csv_file}: {e}")

        return proper_nouns

    def _is_proper_noun(self, text: str) -> bool:
        """テキストが固有名詞かどうかを判定"""
        if not text or len(text) < 2:
            return False

        # 技術用語は固有名詞として扱う
        tech_terms = ['mypy', 'pycache', 'ruff', 'egg-info', 'node_modules', 'dist', 'build', 'git']
        if text.lower() in tech_terms:
            return True

        # 日本語文字を含む場合は固有名詞として扱う
        if re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', text):
            return True

        # 大文字で始まる英単語は固有名詞として扱う
        if re.match(r'^[A-Z][a-zA-Z]*$', text):
            return True

        # 特殊文字を含む場合は固有名詞として扱う
        if re.search(r'[^a-zA-Z0-9\s]', text):
            return True

        return False

    def update_cspell_config(self, new_words: Set[str]):
        """cSpell設定ファイルを更新"""
        if not self.cspell_config_path.exists():
            self._create_default_cspell_config()

        with open(self.cspell_config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # 既存の単語リストに新しい単語を追加
        existing_words = set(config.get('words', []))
        updated_words = list(existing_words | new_words)
        updated_words.sort()  # アルファベット順にソート

        config['words'] = updated_words

        # 高度な設定を追加
        config.update({
            'language': 'en,ja',
            'allowCompoundWords': True,
            'ignorePaths': [
                'deletion_results/',
                'deletion_backups/',
                'test_deletion_results_*/',
                'test_output/',
                'cache/',
                'versions/',
                'ide_cache_env/',
                '**/__pycache__/',
                '**/*.egg-info/',
                '**/.mypy_cache/',
                '**/.ruff_cache/'
            ],
            'patterns': [
                {
                    'name': 'Japanese Names',
                    'pattern': r'\b[A-Z][a-z]+\b',
                    'description': 'Japanese names and proper nouns'
                },
                {
                    'name': 'Proper Nouns',
                    'pattern': r'\b[A-Z][a-zA-Z]*\b',
                    'description': 'Proper nouns starting with capital letters'
                },
                {
                    'name': 'Mixed Language',
                    'pattern': r'\b[a-zA-Z]+[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+\b',
                    'description': 'Mixed Japanese and English text'
                }
            ]
        })

        with open(self.cspell_config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        print(f"Updated cSpell config with {len(new_words)} new words")

    def update_cspell_ignore(self):
        """cSpell除外設定を更新"""
        ignore_content = """# プロジェクト全体でcSpellを無効化
*

# 特定のファイルを無視
ultra_think_improvements/reports/DATABASE_RESTORE_REPORT_20250831_113604.md

# CSVファイルを除外
*.csv
deletion_results/
deletion_backups/
test_deletion_results_*/
test_output/

# データファイル全般を除外
*.json
*.yaml
*.yml
*.xml
*.txt
*.log
*.bak
*.backup
*.tmp
*.temp

# 特定のディレクトリを除外
cache/
versions/
ide_cache_env/
__pycache__/
*.egg-info/
.mypy_cache/
.ruff_cache/

# 自動生成されたファイルを除外
**/node_modules/
**/dist/
**/build/
**/.git/
"""

        with open(self.cspell_ignore_path, 'w', encoding='utf-8') as f:
            f.write(ignore_content)

        print("Updated cSpell ignore file")

    def _create_default_cspell_config(self):
        """デフォルトのcSpell設定を作成"""
        default_config = {
            "version": "0.2",
            "language": "en,ja",
            "allowCompoundWords": True,
            "words": [],
            "ignoreWords": [],
            "patterns": []
        }

        with open(self.cspell_config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2)

    def run(self):
        """メイン実行関数"""
        print("Starting cSpell configuration update...")

        # 固有名詞を抽出
        proper_nouns = self.extract_proper_nouns_from_csv()
        print(f"Extracted {len(proper_nouns)} proper nouns from CSV files")

        # 設定ファイルを更新
        self.update_cspell_config(proper_nouns)
        self.update_cspell_ignore()

        print("cSpell configuration update completed!")
        print(f"Total words in config: {len(proper_nouns)}")

if __name__ == "__main__":
    updater = CSpellConfigUpdater()
    updater.run()
