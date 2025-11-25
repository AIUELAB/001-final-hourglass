#!/usr/bin/env python3
"""
Cultural Character Database Restorer
====================================

This script restores Wikipedia-verified and culturally significant fictional
characters back to the Ultra Think database.

Features:
- Selective restoration based on verification results
- Database integrity maintenance
- Backup creation before modifications
- Detailed logging and reporting

Author: Claude Code
Date: 2025-08-30
"""

import csv
import json
import os
import shutil
import logging
from datetime import datetime
from typing import Dict, List, Set, Optional
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'character_restoration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CulturalCharacterRestorer:
    """Restores culturally significant fictional characters to database."""

    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Priority levels for restoration
        self.restoration_priorities = {
            'restore_high_priority': 1,
            'restore_medium_priority': 2,
            'restore_low_priority': 3
        }

        # Characters that MUST be restored (cultural icons)
        self.must_restore_characters = {
            'doraemon', 'anpanman', 'sazae-san', 'astro boy',
            'mario', 'luigi', 'peach', 'bowser', 'yoshi',
            'pikachu', 'pokemon', 'charizard', 'mewtwo',
            'link', 'zelda', 'ganondorf',
            'goku', 'vegeta', 'piccolo',
            'naruto', 'sasuke', 'sakura',
            'luffy', 'zoro', 'sanji', 'nami',
            'sonic', 'pac-man', 'mega man', 'kirby',
            'mickey mouse', 'hello kitty'
        }

    def find_latest_database_file(self, directory: str = ".") -> Optional[str]:
        """Find the latest Ultra Think database file."""
        pattern_files = []

        for filename in os.listdir(directory):
            if filename.startswith('ultra_think_') and filename.endswith('.csv'):
                # Skip backup files
                if 'backup' not in filename.lower():
                    pattern_files.append(filename)

        if not pattern_files:
            logger.error("No Ultra Think database files found")
            return None

        # Sort by modification time and get the latest
        pattern_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        latest_file = pattern_files[0]

        logger.info(f"Found latest database file: {latest_file}")
        return latest_file

    def create_backup(self, original_file: str) -> str:
        """Create backup of the original database file."""
        backup_name = f"backup_before_restoration_{self.timestamp}_{os.path.basename(original_file)}"

        try:
            shutil.copy2(original_file, backup_name)
            logger.info(f"Backup created: {backup_name}")
            return backup_name
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise

    def load_verification_results(self, results_file: str) -> Dict:
        """Load Wikipedia verification results."""
        try:
            with open(results_file, 'r', encoding='utf-8') as f:
                results = json.load(f)

            logger.info(f"Loaded verification results from: {results_file}")
            logger.info(f"High priority: {len(results.get('restore_high_priority', []))}")
            logger.info(f"Medium priority: {len(results.get('restore_medium_priority', []))}")
            logger.info(f"Low priority: {len(results.get('restore_low_priority', []))}")

            return results
        except Exception as e:
            logger.error(f"Failed to load verification results: {e}")
            raise

    def load_removed_characters(self, removed_file: str) -> Dict[str, Dict]:
        """Load removed characters data indexed by person_id."""
        characters = {}

        try:
            with open(removed_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    person_id = row.get('person_id', '')
                    if person_id:
                        # Keep only the first occurrence of each person_id
                        if person_id not in characters:
                            characters[person_id] = row

            logger.info(f"Loaded {len(characters)} unique removed characters")
            return characters

        except Exception as e:
            logger.error(f"Failed to load removed characters: {e}")
            raise

    def is_must_restore_character(self, character_data: Dict) -> bool:
        """Check if character is in the must-restore list."""
        names_to_check = [
            character_data.get('person_name', ''),
            character_data.get('person_name_ja', ''),
            character_data.get('person_name_display', '')
        ]

        for name in names_to_check:
            if name:
                normalized_name = name.lower().strip()
                for must_restore in self.must_restore_characters:
                    if must_restore in normalized_name or normalized_name in must_restore:
                        return True

        return False

    def select_characters_for_restoration(self, verification_results: Dict,
                                        removed_characters: Dict[str, Dict],
                                        priority_level: int = 2) -> List[Dict]:
        """Select characters for restoration based on priority level."""
        selected_characters = []

        # Get restoration candidates by priority
        restoration_categories = []
        if priority_level >= 1:
            restoration_categories.append('restore_high_priority')
        if priority_level >= 2:
            restoration_categories.append('restore_medium_priority')
        if priority_level >= 3:
            restoration_categories.append('restore_low_priority')

        # Collect character IDs to restore
        character_ids_to_restore = set()

        for category in restoration_categories:
            for character in verification_results.get(category, []):
                character_id = character.get('character_id', '')
                if character_id:
                    character_ids_to_restore.add(character_id)

        # Add must-restore characters regardless of verification results
        for character_id, character_data in removed_characters.items():
            if self.is_must_restore_character(character_data):
                character_ids_to_restore.add(character_id)
                logger.info(f"Adding must-restore character: {character_data.get('person_name_display', character_id)}")

        # Build final selection
        for character_id in character_ids_to_restore:
            if character_id in removed_characters:
                character_data = removed_characters[character_id].copy()

                # Find verification info if available
                verification_info = None
                for category in restoration_categories:
                    for verified_char in verification_results.get(category, []):
                        if verified_char.get('character_id') == character_id:
                            verification_info = verified_char
                            break
                    if verification_info:
                        break

                # Add verification metadata
                if verification_info:
                    character_data['cultural_score'] = verification_info.get('cultural_score', 0)
                    character_data['cultural_category'] = verification_info.get('cultural_category', 'unknown')
                    character_data['wikipedia_pages'] = len(verification_info.get('wikipedia_pages', {}))
                    character_data['restoration_reason'] = 'Wikipedia verified + Cultural significance'
                else:
                    character_data['cultural_score'] = 100  # Must-restore characters get max score
                    character_data['cultural_category'] = 'cultural_icon'
                    character_data['wikipedia_pages'] = 0
                    character_data['restoration_reason'] = 'Cultural icon - must restore'

                selected_characters.append(character_data)

        # Sort by cultural significance
        selected_characters.sort(
            key=lambda x: (x.get('cultural_score', 0), x.get('wikipedia_pages', 0)),
            reverse=True
        )

        logger.info(f"Selected {len(selected_characters)} characters for restoration")
        return selected_characters

    def restore_characters_to_database(self, database_file: str,
                                     characters_to_restore: List[Dict],
                                     create_new_file: bool = True) -> str:
        """Restore characters to the database."""
        try:
            # Load current database
            logger.info(f"Loading database: {database_file}")
            df = pd.read_csv(database_file)

            # Get current max row index
            max_row_index = df['row_index'].max() if 'row_index' in df.columns else 0

            # Prepare restoration data
            restoration_rows = []

            for i, character in enumerate(characters_to_restore, 1):
                # Create new row
                new_row = {
                    'row_index': max_row_index + i,
                    'person_id': character.get('person_id', ''),
                    'person_name': character.get('person_name', ''),
                    'person_name_ja': character.get('person_name_ja', ''),
                    'person_name_display': character.get('person_name_display', ''),
                    'occupation': character.get('occupation', ''),
                    'category': character.get('category', '架空の存在'),
                    'birth_year': None,  # Fictional characters don't have birth years
                    'recognition_score': min(character.get('cultural_score', 50), 100),
                    'is_japanese': 'Yes' if character.get('person_name_ja') else 'No',
                    'notes': f"Restored cultural character - Score: {character.get('cultural_score', 0)}, Wikipedia: {character.get('wikipedia_pages', 0)} pages"
                }

                # Add any missing columns from original database
                for col in df.columns:
                    if col not in new_row:
                        new_row[col] = None

                restoration_rows.append(new_row)

            # Create DataFrame for new characters
            restoration_df = pd.DataFrame(restoration_rows)

            # Combine with existing database
            combined_df = pd.concat([df, restoration_df], ignore_index=True)

            # Remove any duplicates by person_id (keep first occurrence)
            combined_df = combined_df.drop_duplicates(subset=['person_id'], keep='first')

            # Sort by row_index
            combined_df = combined_df.sort_values('row_index').reset_index(drop=True)

            # Generate output filename
            if create_new_file:
                base_name = os.path.splitext(database_file)[0]
                output_file = f"{base_name}_CHARACTERS_RESTORED_{self.timestamp}.csv"
            else:
                output_file = database_file

            # Save updated database
            combined_df.to_csv(output_file, index=False)

            logger.info(f"Database updated successfully: {output_file}")
            logger.info(f"Original records: {len(df)}")
            logger.info(f"Restored characters: {len(restoration_rows)}")
            logger.info(f"Final records: {len(combined_df)}")

            return output_file

        except Exception as e:
            logger.error(f"Failed to restore characters to database: {e}")
            raise

    def generate_restoration_report(self, restored_file: str,
                                  characters_restored: List[Dict],
                                  verification_results: Dict) -> str:
        """Generate comprehensive restoration report."""
        report_file = f"character_restoration_report_{self.timestamp}.md"

        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("# Cultural Character Restoration Report\n\n")
                f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**Restored Database**: {restored_file}\n\n")

                f.write("## Executive Summary\n\n")
                f.write(f"- **Characters Restored**: {len(characters_restored)}\n")
                f.write(f"- **High Priority Restorations**: {len([c for c in characters_restored if c.get('cultural_score', 0) >= 95])}\n")
                f.write(f"- **Medium Priority Restorations**: {len([c for c in characters_restored if 70 <= c.get('cultural_score', 0) < 95])}\n")
                f.write(f"- **Cultural Icons Restored**: {len([c for c in characters_restored if c.get('cultural_score', 0) >= 100])}\n\n")

                f.write("## Restored Characters by Cultural Significance\n\n")

                # Sort characters by score
                sorted_characters = sorted(characters_restored,
                                         key=lambda x: x.get('cultural_score', 0), reverse=True)

                for character in sorted_characters:
                    f.write(f"### {character.get('person_name_display', 'Unknown')}\n")
                    f.write(f"- **ID**: {character.get('person_id', '')}\n")
                    f.write(f"- **Name**: {character.get('person_name', '')}\n")
                    f.write(f"- **Japanese Name**: {character.get('person_name_ja', '')}\n")
                    f.write(f"- **Occupation**: {character.get('occupation', '')}\n")
                    f.write(f"- **Cultural Score**: {character.get('cultural_score', 0)}\n")
                    f.write(f"- **Wikipedia Pages**: {character.get('wikipedia_pages', 0)}\n")
                    f.write(f"- **Category**: {character.get('cultural_category', 'unknown')}\n")
                    f.write(f"- **Restoration Reason**: {character.get('restoration_reason', 'Cultural significance')}\n\n")

                f.write("## Cultural Impact Analysis\n\n")

                # Analyze cultural categories
                categories = {}
                for character in characters_restored:
                    cat = character.get('cultural_category', 'unknown')
                    categories[cat] = categories.get(cat, 0) + 1

                for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                    f.write(f"- **{category}**: {count} characters\n")

                f.write("\n## Wikipedia Verification Statistics\n\n")
                wiki_stats = {
                    'with_wikipedia': len([c for c in characters_restored if c.get('wikipedia_pages', 0) > 0]),
                    'without_wikipedia': len([c for c in characters_restored if c.get('wikipedia_pages', 0) == 0])
                }

                f.write(f"- **With Wikipedia Pages**: {wiki_stats['with_wikipedia']}\n")
                f.write(f"- **Without Wikipedia Pages**: {wiki_stats['without_wikipedia']}\n")
                f.write(f"- **Wikipedia Coverage**: {wiki_stats['with_wikipedia'] / len(characters_restored) * 100:.1f}%\n\n")

                f.write("## Quality Assurance\n\n")
                f.write("All restored characters meet one or more of the following criteria:\n\n")
                f.write("1. **Wikipedia Verified**: Has active Wikipedia page in major languages\n")
                f.write("2. **Cultural Icon Status**: Recognized as culturally significant (score ≥95)\n")
                f.write("3. **Must-Restore List**: Included in essential cultural characters list\n")
                f.write("4. **Franchise Significance**: Part of major entertainment franchises\n\n")

                f.write("## Next Steps\n\n")
                f.write("1. **Database Validation**: Verify restored data integrity\n")
                f.write("2. **Sync with Sheets**: Update Google Sheets with restored characters\n")
                f.write("3. **Monitoring**: Track any issues with restored characters\n")
                f.write("4. **Documentation**: Update project documentation with restoration details\n\n")

            logger.info(f"Restoration report generated: {report_file}")
            return report_file

        except Exception as e:
            logger.error(f"Failed to generate restoration report: {e}")
            raise

def main():
    """Main execution function."""
    restorer = CulturalCharacterRestorer()

    # Input files
    removed_characters_file = "removed_fictional_characters_20250831_073627.csv"

    # Find verification results file (most recent)
    verification_files = [f for f in os.listdir('.') if f.startswith('wikipedia_verification_results_') and f.endswith('.json')]

    if not verification_files:
        logger.error("No Wikipedia verification results file found. Please run wikipedia_fictional_character_verifier.py first.")
        return

    # Use most recent verification file
    verification_file = sorted(verification_files)[-1]

    # Find latest database file
    database_file = restorer.find_latest_database_file()

    if not database_file:
        logger.error("No database file found")
        return

    # Check if input files exist
    for file_path in [removed_characters_file, verification_file]:
        if not os.path.exists(file_path):
            logger.error(f"Required file not found: {file_path}")
            return

    try:
        # Create backup
        backup_file = restorer.create_backup(database_file)

        # Load data
        logger.info("Loading verification results...")
        verification_results = restorer.load_verification_results(verification_file)

        logger.info("Loading removed characters...")
        removed_characters = restorer.load_removed_characters(removed_characters_file)

        # Select characters for restoration (priority level 2 = high + medium)
        logger.info("Selecting characters for restoration...")
        characters_to_restore = restorer.select_characters_for_restoration(
            verification_results, removed_characters, priority_level=2
        )

        if not characters_to_restore:
            logger.warning("No characters selected for restoration")
            return

        # Show what will be restored
        logger.info("Characters selected for restoration:")
        for character in characters_to_restore[:10]:  # Show first 10
            name = character.get('person_name_display', character.get('person_name', 'Unknown'))
            score = character.get('cultural_score', 0)
            logger.info(f"  - {name} (Score: {score})")

        if len(characters_to_restore) > 10:
            logger.info(f"  ... and {len(characters_to_restore) - 10} more")

        # Confirm restoration
        response = input(f"\nRestore {len(characters_to_restore)} characters to database? (y/N): ").strip().lower()

        if response != 'y':
            logger.info("Restoration cancelled by user")
            return

        # Restore characters
        logger.info("Restoring characters to database...")
        restored_database_file = restorer.restore_characters_to_database(
            database_file, characters_to_restore, create_new_file=True
        )

        # Generate report
        logger.info("Generating restoration report...")
        report_file = restorer.generate_restoration_report(
            restored_database_file, characters_to_restore, verification_results
        )

        # Summary
        logger.info("=" * 60)
        logger.info("CHARACTER RESTORATION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Original database: {database_file}")
        logger.info(f"Backup created: {backup_file}")
        logger.info(f"Restored database: {restored_database_file}")
        logger.info(f"Characters restored: {len(characters_to_restore)}")
        logger.info(f"Report generated: {report_file}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Restoration failed: {e}")
        logger.error("Please check the backup file and logs for more information")
        raise

if __name__ == "__main__":
    main()
