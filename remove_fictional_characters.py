#!/usr/bin/env python3
"""
Fictional Character Remover for Ultra Think Database
=================================================

Removes fictional characters and empty entries from the latest ultra_think CSV file.
Includes comprehensive detection patterns and detailed reporting.

Features:
- Comprehensive fictional character detection
- Empty data cleaning
- Safe backup creation
- Detailed removal reports
- Validation and statistics

Usage:
    python remove_fictional_characters.py
"""

import csv
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Tuple, Set
import pandas as pd
from pathlib import Path


class FictionalCharacterRemover:
    """Removes fictional characters and empty entries from Ultra Think database."""
    
    def __init__(self):
        self.fictional_patterns = self._load_fictional_patterns()
        self.removed_entries = []
        self.stats = {
            'total_entries': 0,
            'fictional_removed': 0,
            'empty_removed': 0,
            'valid_entries': 0
        }
        
    def _load_fictional_patterns(self) -> Dict[str, List[str]]:
        """Load comprehensive fictional character detection patterns."""
        return {
            # Anime/Manga Characters
            'anime_manga': [
                # SPY×FAMILY
                'フォージャー', 'Forger', 'アーニャ', 'Anya', 'ロイド', 'Loid', 'ヨル', 'Yor',
                
                # Naruto
                'うずまき', 'Uzumaki', 'ナルト', 'Naruto', 'サスケ', 'Sasuke', 'サクラ', 'Sakura',
                'カカシ', 'Kakashi', 'イタチ', 'Itachi', 'ガアラ', 'Gaara',
                
                # One Piece
                'モンキー・D・ルフィ', 'Monkey D. Luffy', 'ルフィ', 'Luffy', 'ゾロ', 'Zoro',
                'ナミ', 'Nami', 'サンジ', 'Sanji', 'チョッパー', 'Chopper',
                
                # Dragon Ball
                '孫悟空', 'Son Goku', '悟空', 'Goku', 'ベジータ', 'Vegeta', 'ピッコロ', 'Piccolo',
                'フリーザ', 'Frieza', 'セル', 'Cell', '魔人ブウ', 'Majin Buu',
                
                # Attack on Titan
                'エレン・イェーガー', 'Eren Yeager', 'ミカサ', 'Mikasa', 'アルミン', 'Armin',
                'リヴァイ', 'Levi', 'エルヴィン', 'Erwin',
                
                # Death Note
                '夜神月', 'Light Yagami', 'リューク', 'Ryuk', 'ミサ', 'Misa',
                # Note: Excluded single letter 'L' to avoid false positives with names like Lincoln
                
                # Demon Slayer
                '竈門炭治郎', 'Tanjiro Kamado', '我妻善逸', 'Zenitsu Agatsuma',
                '嘴平伊之助', 'Inosuke Hashibira', '竈門禰豆子', 'Nezuko Kamado',
                
                # Other Popular Anime
                'セーラームーン', 'Sailor Moon', 'ちびうさ', 'Chibiusa',
                'クレヨンしんちゃん', 'Crayon Shin-chan', 'しんのすけ', 'Shinnosuke',
                'のび太', 'Nobita', 'しずか', 'Shizuka', 'ジャイアン', 'Gian', 'スネ夫', 'Suneo'
            ],
            
            # Video Game Characters (Only specific full names to avoid false positives)
            'video_games': [
                # Mario Series (full character names)
                'Mario Bros', 'Super Mario', 'Luigi Mario', 'Princess Peach', 'Bowser Koopa',
                'マリオブラザーズ', 'スーパーマリオ', 'ピーチ姫', 'クッパ大王', 'キノピオ',
                
                # Pokémon (full character names)
                'ピカチュウ', 'Pikachu', 'Ash Ketchum', 'Satoshi Pokemon', 'Team Rocket',
                'ロケット団', 'ポケモン', 'Pokemon Trainer',
                
                # Legend of Zelda (full names)
                'Legend of Zelda', 'Princess Zelda', 'Ganondorf Dragmire', 'ゼルダの伝説',
                
                # Sonic (full names)
                'Sonic the Hedgehog', 'Miles Tails Prower', 'Knuckles the Echidna',
                'ソニック・ザ・ヘッジホッグ',
                
                # Final Fantasy (full names)
                'Cloud Strife', 'Sephiroth Final Fantasy', 'Tifa Lockhart',
                'ファイナルファンタジー', 'Final Fantasy',
                
                # Street Fighter (full names or unique identifiers)
                'Street Fighter', 'Chun-Li', 'ストリートファイター', '春麗'
                # Note: Removed common substrings like 'Ryu', 'Ken', 'Mario', 'Yoshi', 'Link' etc.
            ],
            
            # Cartoon Characters
            'cartoons': [
                # Disney
                'ミッキーマウス', 'Mickey Mouse', 'ミニーマウス', 'Minnie Mouse',
                'ドナルドダック', 'Donald Duck', 'グーフィー', 'Goofy',
                'プルート', 'Pluto', 'チップとデール', 'Chip and Dale',
                
                # Studio Ghibli
                'トトロ', 'Totoro', 'カオナシ', 'No-Face', 'ハウル', 'Howl',
                'ソフィー', 'Sophie', '千尋', 'Chihiro',
                
                # Japanese Characters
                'アンパンマン', 'Anpanman', 'バイキンマン', 'Baikinman',
                'ドキンちゃん', 'Dokin-chan', 'コキンちゃん', 'Kokin-chan',
                
                # International Cartoons
                'スヌーピー', 'Snoopy', 'チャーリー・ブラウン', 'Charlie Brown',
                'ガーフィールド', 'Garfield', 'トムとジェリー', 'Tom and Jerry'
            ],
            
            # Fictional Occupations (Japanese)
            'fictional_occupations': [
                '架空のキャラクター', '架空キャラクター', 'ヒーロー', 'キャラクター',
                '魔法使い', '忍者', '海賊', '魔王', '勇者', '王子', '王女',
                'アニメキャラクター', 'マンガキャラクター', 'ゲームキャラクター'
            ],
            
            # Generic Fictional Indicators
            'generic_patterns': [
                '（SPY×FAMILY）', '（NARUTO）', '（ONE PIECE）', '（ドラゴンボール）',
                '（進撃の巨人）', '（鬼滅の刃）', '（ポケモン）', '（マリオ）',
                '（ゼルダ）', '（ソニック）', '（ファイナルファンタジー）',
                '（ディズニー）', '（ジブリ）', '（アンパンマン）'
            ],
            
            # Category-based Detection
            'fictional_categories': [
                '架空の存在', '架空', 'fictional', 'anime', 'manga', 'cartoon',
                'video game', 'game character', 'animated character'
            ],
            
            # Nationality Patterns (Fictional)
            'fictional_nationalities': [
                '架空', 'fictional', '不明'  # Sometimes fictional characters have "不明" nationality
            ]
        }
    
    def _is_precise_match(self, pattern: str, text: str) -> bool:
        """
        More precise pattern matching to avoid false positives.
        
        Args:
            pattern: The pattern to search for
            text: The text to search in
            
        Returns:
            bool: True if there's a precise match
        """
        if not pattern or not text:
            return False
        
        # For very short patterns (1-2 characters), require exact match or word boundary
        if len(pattern) <= 2:
            # Exact match
            if pattern == text:
                return True
            # Word boundary match (pattern as whole word)
            import re
            word_pattern = r'\b' + re.escape(pattern) + r'\b'
            return bool(re.search(word_pattern, text, re.IGNORECASE))
        
        # For longer patterns, use contains but avoid common false positives
        if pattern in text:
            # Avoid false positives with common substrings in real names
            false_positive_patterns = [
                ('Link', 'Lincoln'),  # Lincoln contains Link
                ('Ken', 'Kennedy'),   # Kennedy contains Ken
                ('Mario', 'Marionettte'), # Example of substring issues
                ('Yoshi', 'Yoshikawa'),  # Yoshikawa contains Yoshi
                ('Yoshi', 'Yoshino'),    # Yoshino contains Yoshi  
                ('Ryu', 'Ryunosuke'),    # Ryunosuke contains Ryu
                ('Sonic', 'Masonic'),    # Masonic contains Sonic
                ('Cloud', 'McCloud'),    # McCloud contains Cloud
                ('Ken', 'Kennedy'),      # Kennedy contains Ken
                ('Ken', 'Kenneth'),      # Kenneth contains Ken
                ('Tails', 'Details'),    # Details contains Tails
                ('Nami', 'Namie'),       # Namie contains Nami (Amuro Namie)
            ]
            
            for fp_pattern, fp_full in false_positive_patterns:
                if pattern == fp_pattern and fp_full.lower() in text.lower():
                    return False
            
            return True
        
        return False
    
    def find_latest_csv(self) -> str:
        """Find the latest ultra_think CSV file."""
        pattern = "ultra_think_*.csv"
        csv_files = list(Path('.').glob(pattern))
        
        if not csv_files:
            raise FileNotFoundError("No ultra_think CSV files found")
        
        # Sort by modification time, get the latest
        latest_file = max(csv_files, key=lambda f: f.stat().st_mtime)
        print(f"📁 Found latest CSV: {latest_file}")
        return str(latest_file)
    
    def is_fictional_character(self, row: Dict) -> Tuple[bool, str]:
        """
        Determine if a row represents a fictional character.
        
        Returns:
            Tuple[bool, str]: (is_fictional, reason)
        """
        person_name = str(row.get('person_name', '')).strip()
        person_name_ja = str(row.get('person_name_ja', '')).strip()
        person_name_display = str(row.get('person_name_display', '')).strip()
        occupation = str(row.get('occupation', '')).strip()
        category = str(row.get('category', '')).strip()
        nationality = str(row.get('nationality', '')).strip()
        extended_data = str(row.get('extended_data', ''))
        
        # Check if extended_data contains is_fictional: TRUE
        if 'is_fictional' in extended_data and 'TRUE' in extended_data:
            return True, "Extended data indicates fictional character"
        
        # Check occupation for fictional indicators
        for pattern in self.fictional_patterns['fictional_occupations']:
            if pattern in occupation:
                return True, f"Fictional occupation: {occupation}"
        
        # Check category for fictional indicators
        for pattern in self.fictional_patterns['fictional_categories']:
            if pattern in category:
                return True, f"Fictional category: {category}"
        
        # Check all name fields against patterns
        names_to_check = [person_name, person_name_ja, person_name_display]
        
        for pattern_type, patterns in self.fictional_patterns.items():
            if pattern_type in ['fictional_occupations', 'fictional_categories', 'fictional_nationalities']:
                continue  # Already checked above
                
            for pattern in patterns:
                for name in names_to_check:
                    # More precise pattern matching to avoid false positives
                    if self._is_precise_match(pattern, name):
                        return True, f"Name pattern match ({pattern_type}): {pattern} in {name}"
        
        # Check for generic fictional patterns in text fields
        text_fields = [person_name, person_name_ja, person_name_display, occupation]
        for field in text_fields:
            for pattern in self.fictional_patterns['generic_patterns']:
                if pattern in field:
                    return True, f"Generic fictional pattern: {pattern} in {field}"
        
        return False, ""
    
    def is_empty_entry(self, row: Dict) -> bool:
        """Check if entry has empty person_name."""
        person_name = str(row.get('person_name', '')).strip()
        return len(person_name) == 0
    
    def process_csv(self, input_file: str) -> str:
        """
        Process the CSV file and remove fictional characters and empty entries.
        
        Returns:
            str: Path to the cleaned CSV file
        """
        print(f"📖 Reading CSV file: {input_file}")
        
        # Create backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"backup_before_fictional_removal_{timestamp}.csv"
        
        # Read the CSV file
        df = pd.read_csv(input_file)
        original_count = len(df)
        self.stats['total_entries'] = original_count
        
        print(f"📊 Original entries: {original_count:,}")
        
        # Create backup
        df.to_csv(backup_file, index=False, encoding='utf-8')
        print(f"💾 Backup created: {backup_file}")
        
        valid_rows = []
        
        # Process each row
        for index, row in df.iterrows():
            row_dict = row.to_dict()
            
            # Check for empty entries
            if self.is_empty_entry(row_dict):
                self.removed_entries.append({
                    'row_index': index,
                    'person_id': row_dict.get('person_id', ''),
                    'person_name': row_dict.get('person_name', ''),
                    'person_name_ja': row_dict.get('person_name_ja', ''),
                    'person_name_display': row_dict.get('person_name_display', ''),
                    'occupation': row_dict.get('occupation', ''),
                    'category': row_dict.get('category', ''),
                    'removal_reason': 'Empty person_name field'
                })
                self.stats['empty_removed'] += 1
                continue
            
            # Check for fictional characters
            is_fictional, reason = self.is_fictional_character(row_dict)
            if is_fictional:
                self.removed_entries.append({
                    'row_index': index,
                    'person_id': row_dict.get('person_id', ''),
                    'person_name': row_dict.get('person_name', ''),
                    'person_name_ja': row_dict.get('person_name_ja', ''),
                    'person_name_display': row_dict.get('person_name_display', ''),
                    'occupation': row_dict.get('occupation', ''),
                    'category': row_dict.get('category', ''),
                    'removal_reason': reason
                })
                self.stats['fictional_removed'] += 1
                continue
            
            # Keep valid entries
            valid_rows.append(row_dict)
        
        self.stats['valid_entries'] = len(valid_rows)
        
        # Create cleaned DataFrame
        cleaned_df = pd.DataFrame(valid_rows)
        
        # Generate output filename
        output_file = f"ultra_think_FICTIONAL_REMOVED_{timestamp}.csv"
        
        # Save cleaned data
        cleaned_df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"✅ Cleaned file saved: {output_file}")
        
        return output_file
    
    def generate_reports(self, output_file: str) -> None:
        """Generate detailed reports of the removal process."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Removed entries CSV report
        removed_csv = f"removed_fictional_characters_{timestamp}.csv"
        removed_df = pd.DataFrame(self.removed_entries)
        if not removed_df.empty:
            removed_df.to_csv(removed_csv, index=False, encoding='utf-8')
            print(f"📋 Removed entries report: {removed_csv}")
        
        # 2. Summary statistics JSON
        stats_json = f"fictional_removal_stats_{timestamp}.json"
        detailed_stats = {
            'summary': self.stats,
            'removal_breakdown': self._get_removal_breakdown(),
            'pattern_matches': self._get_pattern_matches(),
            'timestamp': timestamp,
            'input_file': self.find_latest_csv(),
            'output_file': output_file,
            'backup_file': f"backup_before_fictional_removal_{timestamp}.csv"
        }
        
        with open(stats_json, 'w', encoding='utf-8') as f:
            json.dump(detailed_stats, f, ensure_ascii=False, indent=2)
        print(f"📊 Statistics report: {stats_json}")
        
        # 3. Detailed markdown report
        report_md = f"FICTIONAL_REMOVAL_REPORT_{timestamp}.md"
        self._generate_markdown_report(report_md, detailed_stats)
        print(f"📝 Detailed report: {report_md}")
    
    def _get_removal_breakdown(self) -> Dict:
        """Get breakdown of removal reasons."""
        breakdown = {}
        for entry in self.removed_entries:
            reason = entry['removal_reason']
            reason_type = reason.split(':')[0] if ':' in reason else reason
            breakdown[reason_type] = breakdown.get(reason_type, 0) + 1
        return breakdown
    
    def _get_pattern_matches(self) -> Dict:
        """Get pattern matching statistics."""
        pattern_stats = {}
        for entry in self.removed_entries:
            reason = entry['removal_reason']
            if 'pattern match' in reason.lower():
                # Extract pattern type from reason
                if '(' in reason and ')' in reason:
                    pattern_type = reason.split('(')[1].split(')')[0]
                    pattern_stats[pattern_type] = pattern_stats.get(pattern_type, 0) + 1
        return pattern_stats
    
    def _generate_markdown_report(self, filename: str, stats: Dict) -> None:
        """Generate detailed markdown report."""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"# Fictional Character Removal Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Summary Statistics\n\n")
            f.write(f"- **Original entries:** {stats['summary']['total_entries']:,}\n")
            f.write(f"- **Fictional characters removed:** {stats['summary']['fictional_removed']:,}\n")
            f.write(f"- **Empty entries removed:** {stats['summary']['empty_removed']:,}\n")
            f.write(f"- **Valid entries remaining:** {stats['summary']['valid_entries']:,}\n")
            f.write(f"- **Total removed:** {stats['summary']['fictional_removed'] + stats['summary']['empty_removed']:,}\n")
            
            removal_percentage = ((stats['summary']['fictional_removed'] + stats['summary']['empty_removed']) / stats['summary']['total_entries']) * 100
            f.write(f"- **Removal percentage:** {removal_percentage:.2f}%\n\n")
            
            if stats['removal_breakdown']:
                f.write("## Removal Breakdown\n\n")
                for reason, count in sorted(stats['removal_breakdown'].items(), key=lambda x: x[1], reverse=True):
                    f.write(f"- **{reason}:** {count:,} entries\n")
                f.write("\n")
            
            if stats['pattern_matches']:
                f.write("## Pattern Match Statistics\n\n")
                for pattern_type, count in sorted(stats['pattern_matches'].items(), key=lambda x: x[1], reverse=True):
                    f.write(f"- **{pattern_type}:** {count:,} matches\n")
                f.write("\n")
            
            f.write("## Files Generated\n\n")
            f.write(f"- **Cleaned database:** `{stats['output_file']}`\n")
            f.write(f"- **Backup file:** `{stats['backup_file']}`\n")
            f.write(f"- **Removed entries:** `removed_fictional_characters_{stats['timestamp']}.csv`\n")
            f.write(f"- **Statistics:** `fictional_removal_stats_{stats['timestamp']}.json`\n\n")
            
            f.write("## Detection Patterns Used\n\n")
            f.write("### Anime/Manga Characters\n")
            f.write("- SPY×FAMILY characters (Forger family)\n")
            f.write("- Naruto universe characters\n")
            f.write("- One Piece characters\n")
            f.write("- Dragon Ball characters\n")
            f.write("- Attack on Titan characters\n")
            f.write("- Death Note characters\n")
            f.write("- Demon Slayer characters\n")
            f.write("- Other popular anime/manga\n\n")
            
            f.write("### Video Game Characters\n")
            f.write("- Mario series characters\n")
            f.write("- Pokémon characters\n")
            f.write("- Legend of Zelda characters\n")
            f.write("- Sonic characters\n")
            f.write("- Final Fantasy characters\n")
            f.write("- Street Fighter characters\n\n")
            
            f.write("### Cartoon Characters\n")
            f.write("- Disney characters\n")
            f.write("- Studio Ghibli characters\n")
            f.write("- Anpanman characters\n")
            f.write("- International cartoon characters\n\n")
            
            f.write("### Detection Methods\n")
            f.write("1. **Name Pattern Matching:** Direct character name detection\n")
            f.write("2. **Occupation Analysis:** Fictional occupations (架空のキャラクター, ヒーロー, etc.)\n")
            f.write("3. **Category Analysis:** Fictional categories (架空の存在, etc.)\n")
            f.write("4. **Extended Data:** JSON metadata with is_fictional flag\n")
            f.write("5. **Generic Patterns:** Series identifiers in parentheses\n\n")
            
            if self.removed_entries:
                f.write("## Sample Removed Entries\n\n")
                # Show first 10 removed entries as examples
                for i, entry in enumerate(self.removed_entries[:10]):
                    f.write(f"### Entry {i+1}\n")
                    f.write(f"- **Person ID:** {entry['person_id']}\n")
                    f.write(f"- **Name:** {entry['person_name']}\n")
                    f.write(f"- **Name (JP):** {entry['person_name_ja']}\n")
                    f.write(f"- **Display Name:** {entry['person_name_display']}\n")
                    f.write(f"- **Occupation:** {entry['occupation']}\n")
                    f.write(f"- **Category:** {entry['category']}\n")
                    f.write(f"- **Removal Reason:** {entry['removal_reason']}\n\n")
    
    def print_summary(self) -> None:
        """Print summary of the removal process."""
        print("\n" + "="*60)
        print("🎯 FICTIONAL CHARACTER REMOVAL SUMMARY")
        print("="*60)
        print(f"📊 Original entries:      {self.stats['total_entries']:,}")
        print(f"🎭 Fictional removed:     {self.stats['fictional_removed']:,}")
        print(f"🗑️  Empty entries removed: {self.stats['empty_removed']:,}")
        print(f"✅ Valid entries kept:    {self.stats['valid_entries']:,}")
        
        total_removed = self.stats['fictional_removed'] + self.stats['empty_removed']
        removal_percentage = (total_removed / self.stats['total_entries']) * 100 if self.stats['total_entries'] > 0 else 0
        
        print(f"📉 Total removed:         {total_removed:,} ({removal_percentage:.2f}%)")
        print("="*60)
        
        if self.removed_entries:
            breakdown = self._get_removal_breakdown()
            print("\n🔍 REMOVAL BREAKDOWN:")
            for reason, count in sorted(breakdown.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total_removed) * 100 if total_removed > 0 else 0
                print(f"   • {reason}: {count:,} ({percentage:.1f}%)")


def main():
    """Main function to run the fictional character removal process."""
    print("🚀 Starting Fictional Character Removal Process")
    print("=" * 50)
    
    try:
        # Initialize remover
        remover = FictionalCharacterRemover()
        
        # Find latest CSV file
        input_file = remover.find_latest_csv()
        
        # Process the file
        output_file = remover.process_csv(input_file)
        
        # Generate reports
        remover.generate_reports(output_file)
        
        # Print summary
        remover.print_summary()
        
        print(f"\n✅ Process completed successfully!")
        print(f"📁 Cleaned file: {output_file}")
        print(f"📋 Check reports for detailed analysis")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())