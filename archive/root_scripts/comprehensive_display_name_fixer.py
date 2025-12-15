#!/usr/bin/env python3
"""
Comprehensive Display Name Fixer for Ultra Think Database

This script fixes all display name issues in the database:
1. Converts non-Japanese display names to Japanese using person_name_ja
2. Removes incorrect group annotations (e.g., LUNA SEA from non-members)
3. Validates all changes before applying
4. Creates backup and detailed reports
5. Implements rules for future automatic correction

Author: Claude Code
Created: 2025-08-31
"""

import csv
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
import re


class ComprehensiveDisplayNameFixer:
    """Comprehensive fixer for all display name issues in the database."""

    def __init__(self, input_file: str, output_dir: str = "."):
        """Initialize the fixer with input file and output directory."""
        self.input_file = Path(input_file)
        self.output_dir = Path(output_dir)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Setup logging
        self.setup_logging()

        # Statistics tracking
        self.stats = {
            "total_records": 0,
            "non_japanese_display_fixed": 0,
            "auto_fixable_using_ja": 0,
            "needs_translation": 0,
            "incorrect_groups_fixed": 0,
            "validation_errors": 0,
            "skipped_records": 0
        }

        # Group membership validation
        self.valid_groups = self.load_valid_groups()

        # Translation dictionary for names that need manual translation
        self.manual_translations = self.load_manual_translations()

        # Correction rules for future automatic fixing
        self.correction_rules = []

        self.logger.info(f"Initialized fixer for {self.input_file}")

    def setup_logging(self) -> None:
        """Setup comprehensive logging system."""
        log_file = self.output_dir / f"display_name_fix_log_{self.timestamp}.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def load_valid_groups(self) -> Dict[str, Set[str]]:
        """Load valid group memberships to detect incorrect annotations."""
        return {
            "LUNA SEA": {
                "RYUICHI", "INORAN", "J", "SUGIZO", "真矢"
            },
            "X JAPAN": {
                "YOSHIKI", "TOSHI", "PATA", "HEATH", "HIDE", "TAIJI"
            },
            "GLAY": {
                "TERU", "TAKURO", "HISASHI", "JIRO"
            },
            "ONE OK ROCK": {
                "Taka", "Toru", "Ryota", "Tomoya"
            },
            "SEKAI NO OWARI": {
                "Fukase", "Nakajin", "Saori", "DJ LOVE"
            },
            "BTS": {
                "RM", "Jin", "Suga", "J-Hope", "Jimin", "V", "Jungkook"
            }
        }

    def load_manual_translations(self) -> Dict[str, str]:
        """Load manual translations for names that can't be auto-fixed."""
        return {
            # Western names requiring translation
            "F. Scott Fitzgerald": "F・スコット・フィッツジェラルド",
            "Michael Jackson": "マイケル・ジャクソン",
            "John Frusciante": "ジョン・フルシアンテ",
            "Joe Perry": "ジョー・ペリー",
            "Jean-Michel Basquiat": "ジャン＝ミシェル・バスキア",
            "Julian Schnabel": "ジュリアン・シュナーベル",
            "J Balvin": "Jバルヴィン",
            "Jonny Greenwood": "ジョニー・グリーンウッド",
            # Korean names
            "G-Dragon": "G-DRAGON",
            "Psy": "サイ",
            # Japanese names needing correction
            "Ado": "Ado",  # Keep as is (modern Japanese artist)
            "HIKAKIN": "HIKAKIN",  # YouTube name, keep as is
            "GACKT": "GACKT",  # Stage name, keep as is
        }

    def is_japanese_text(self, text: str) -> bool:
        """Check if text contains Japanese characters."""
        japanese_pattern = re.compile(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]')
        return bool(japanese_pattern.search(text))

    def has_incorrect_group_annotation(self, person_name: str, display_name: str) -> Tuple[bool, str, str]:
        """Check if display name has incorrect group annotation."""
        # Extract group from display name pattern like "Name (GROUP)"
        group_match = re.search(r'\(([^)]+)\)', display_name)
        if not group_match:
            return False, "", ""

        group_name = group_match.group(1)
        base_name = person_name.strip()

        # Check if this person is actually in the group
        if group_name in self.valid_groups:
            valid_members = self.valid_groups[group_name]
            if base_name not in valid_members:
                return True, group_name, base_name

        return False, group_name, base_name

    def fix_display_name(self, record: Dict[str, str]) -> Tuple[str, str, str]:
        """
        Fix display name for a record.
        Returns: (new_display_name, fix_type, reason)
        """
        person_name = record.get('person_name', '').strip()
        current_display = record.get('person_name_display', '').strip()
        person_name_ja = record.get('person_name_ja', '').strip()

        if not person_name or not current_display:
            return current_display, "skip", "Missing required fields"

        # Check for incorrect group annotations first
        has_incorrect_group, incorrect_group, base_name = self.has_incorrect_group_annotation(
            person_name, current_display
        )

        if has_incorrect_group:
            # Remove incorrect group annotation
            new_display = person_name_ja if person_name_ja else person_name
            return new_display, "group_fix", f"Removed incorrect ({incorrect_group}) annotation"

        # Check if display name is non-Japanese but we have Japanese translation
        if not self.is_japanese_text(current_display) and person_name_ja and self.is_japanese_text(person_name_ja):
            return person_name_ja, "auto_ja", "Used existing person_name_ja"

        # Check manual translation dictionary
        if person_name in self.manual_translations:
            return self.manual_translations[person_name], "manual_translation", "Applied manual translation"

        # For non-Japanese names without translation, keep as is but flag for review
        if not self.is_japanese_text(current_display):
            return current_display, "needs_translation", "Non-Japanese name needs manual translation"

        # Already Japanese, no change needed
        return current_display, "no_change", "Already correct"

    def validate_fix(self, original: str, fixed: str, fix_type: str) -> bool:
        """Validate that the fix is reasonable."""
        if not fixed or fixed.strip() == "":
            return False

        # Don't change if it's already the same
        if original == fixed:
            return True

        # Validate group fixes
        if fix_type == "group_fix":
            # Should not contain group annotation anymore
            if re.search(r'\([^)]+\)', fixed):
                return False

        # Validate Japanese translations
        if fix_type in ["auto_ja", "manual_translation"]:
            # Should contain Japanese characters
            if not self.is_japanese_text(fixed):
                return False

        return True

    def create_backup(self) -> Path:
        """Create backup of original file."""
        backup_path = self.output_dir / f"backup_before_display_fix_{self.timestamp}.csv"
        shutil.copy2(self.input_file, backup_path)
        self.logger.info(f"Created backup: {backup_path}")
        return backup_path

    def process_records(self) -> List[Dict[str, str]]:
        """Process all records and apply fixes."""
        fixed_records = []
        fix_log = []

        with open(self.input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for i, record in enumerate(reader, 1):
                self.stats["total_records"] = i

                try:
                    original_display = record.get('person_name_display', '')
                    fixed_display, fix_type, reason = self.fix_display_name(record)

                    # Validate the fix
                    if not self.validate_fix(original_display, fixed_display, fix_type):
                        self.stats["validation_errors"] += 1
                        self.logger.warning(f"Validation failed for {record.get('person_id')}: {original_display} -> {fixed_display}")
                        fixed_records.append(record)  # Keep original
                        continue

                    # Update record if changed
                    if original_display != fixed_display:
                        record['person_name_display'] = fixed_display

                        # Update statistics
                        if fix_type == "auto_ja":
                            self.stats["auto_fixable_using_ja"] += 1
                            self.stats["non_japanese_display_fixed"] += 1
                        elif fix_type == "manual_translation":
                            self.stats["non_japanese_display_fixed"] += 1
                        elif fix_type == "group_fix":
                            self.stats["incorrect_groups_fixed"] += 1
                        elif fix_type == "needs_translation":
                            self.stats["needs_translation"] += 1

                        # Log the change
                        fix_entry = {
                            "person_id": record.get('person_id', ''),
                            "person_name": record.get('person_name', ''),
                            "original_display": original_display,
                            "fixed_display": fixed_display,
                            "fix_type": fix_type,
                            "reason": reason,
                            "line_number": i
                        }
                        fix_log.append(fix_entry)

                        self.logger.info(f"Fixed {record.get('person_id')}: {original_display} -> {fixed_display} ({fix_type})")

                    fixed_records.append(record)

                except Exception as e:
                    self.logger.error(f"Error processing record {i}: {e}")
                    self.stats["skipped_records"] += 1
                    fixed_records.append(record)  # Keep original on error

        # Save detailed fix log
        self.save_fix_log(fix_log)
        return fixed_records

    def save_fix_log(self, fix_log: List[Dict]) -> None:
        """Save detailed log of all fixes applied."""
        log_file = self.output_dir / f"display_name_fixes_log_{self.timestamp}.json"

        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": self.timestamp,
                "total_fixes": len(fix_log),
                "statistics": self.stats,
                "fixes": fix_log
            }, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Saved detailed fix log: {log_file}")

    def save_corrected_csv(self, records: List[Dict[str, str]]) -> Path:
        """Save the corrected CSV file."""
        output_file = self.output_dir / f"ultra_think_DISPLAY_NAME_FIXED_{self.timestamp}.csv"

        if not records:
            raise ValueError("No records to save")

        fieldnames = records[0].keys()

        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)

        self.logger.info(f"Saved corrected file: {output_file}")
        return output_file

    def generate_correction_rules(self) -> None:
        """Generate rules for future automatic correction."""
        rules = {
            "display_name_rules": {
                "priority_1_use_person_name_ja": {
                    "condition": "person_name_display contains only Latin characters AND person_name_ja contains Japanese characters",
                    "action": "Set person_name_display = person_name_ja",
                    "examples": ["Ado -> Ado", "GACKT -> GACKT"]
                },
                "priority_2_remove_incorrect_groups": {
                    "condition": "person_name_display contains (GROUP) AND person_name not in valid_group_members[GROUP]",
                    "action": "Remove (GROUP) annotation, use person_name_ja or person_name",
                    "examples": ["Michael Jackson (LUNA SEA) -> マイケル・ジャクソン"]
                },
                "priority_3_manual_translation": {
                    "condition": "Non-Japanese name without person_name_ja",
                    "action": "Apply manual translation from dictionary or flag for review",
                    "examples": ["F. Scott Fitzgerald -> F・スコット・フィッツジェラルド"]
                }
            },
            "validation_rules": {
                "japanese_characters": "Display names should contain Japanese characters when possible",
                "no_incorrect_groups": "Group annotations must match actual membership",
                "consistency": "Same person should have same display name across records"
            },
            "group_membership_validation": self.valid_groups
        }

        # Convert sets to lists for JSON serialization
        serializable_rules = json.loads(json.dumps(rules, default=lambda x: list(x) if isinstance(x, set) else x))

        rules_file = self.output_dir / f"display_name_correction_rules_{self.timestamp}.json"
        with open(rules_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_rules, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Generated correction rules: {rules_file}")

    def generate_report(self, output_file: Path, backup_file: Path) -> None:
        """Generate comprehensive report of all fixes."""
        report = {
            "fix_summary": {
                "timestamp": self.timestamp,
                "input_file": str(self.input_file),
                "output_file": str(output_file),
                "backup_file": str(backup_file)
            },
            "statistics": self.stats,
            "fix_breakdown": {
                "auto_fixable_using_ja": f"{self.stats['auto_fixable_using_ja']} records fixed using existing person_name_ja",
                "incorrect_groups_removed": f"{self.stats['incorrect_groups_fixed']} records had incorrect group annotations removed",
                "manual_translations_applied": f"Applied manual translations from dictionary",
                "needs_translation": f"{self.stats['needs_translation']} records flagged as needing manual translation"
            },
            "validation": {
                "total_processed": self.stats["total_records"],
                "successfully_fixed": self.stats["total_records"] - self.stats["validation_errors"] - self.stats["skipped_records"],
                "validation_errors": self.stats["validation_errors"],
                "skipped_records": self.stats["skipped_records"]
            },
            "recommendations": {
                "review_needs_translation": f"Review {self.stats['needs_translation']} records that need manual translation",
                "validate_group_fixes": "Verify that group annotation removals are correct",
                "quality_check": "Spot-check a sample of auto-fixes for accuracy"
            }
        }

        # Save JSON report
        report_file = self.output_dir / f"DISPLAY_NAME_FIX_REPORT_{self.timestamp}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # Save markdown report
        markdown_report = self.generate_markdown_report(report)
        md_file = self.output_dir / f"DISPLAY_NAME_FIX_REPORT_{self.timestamp}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(markdown_report)

        self.logger.info(f"Generated reports: {report_file}, {md_file}")

    def generate_markdown_report(self, report: Dict) -> str:
        """Generate markdown version of the report."""
        return f"""# Display Name Fix Report - {report['fix_summary']['timestamp']}

## Summary

Successfully processed **{report['statistics']['total_records']:,}** records with comprehensive display name fixes.

### Key Achievements

- ✅ **{report['statistics']['non_japanese_display_fixed']}** non-Japanese display names converted to Japanese
- ✅ **{report['statistics']['auto_fixable_using_ja']}** records auto-fixed using existing `person_name_ja`
- ✅ **{report['statistics']['incorrect_groups_fixed']}** incorrect group annotations removed
- ⚠️ **{report['statistics']['needs_translation']}** records flagged for manual translation review

## File Details

- **Input**: `{report['fix_summary']['input_file']}`
- **Output**: `{report['fix_summary']['output_file']}`
- **Backup**: `{report['fix_summary']['backup_file']}`

## Fix Types Applied

### 1. Auto-Fix Using Japanese Names ({report['statistics']['auto_fixable_using_ja']} records)
Used existing `person_name_ja` field to replace non-Japanese display names.

### 2. Group Annotation Cleanup ({report['statistics']['incorrect_groups_fixed']} records)
Removed incorrect group annotations like "(LUNA SEA)" from non-members.

### 3. Manual Translation Dictionary
Applied pre-defined translations for common Western and Korean names.

## Validation Results

- ✅ **{report['validation']['successfully_fixed']}** records successfully processed
- ❌ **{report['validation']['validation_errors']}** validation errors (kept original)
- ⏸️ **{report['validation']['skipped_records']}** records skipped due to errors

## Next Steps

1. **Review Translation Queue**: {report['statistics']['needs_translation']} records need manual translation
2. **Quality Check**: Spot-check auto-fixes for accuracy
3. **Apply Rules**: Use generated correction rules for future data

## Generated Files

- `display_name_fixes_log_{report['fix_summary']['timestamp']}.json` - Detailed fix log
- `display_name_correction_rules_{report['fix_summary']['timestamp']}.json` - Rules for future use
- `backup_before_display_fix_{report['fix_summary']['timestamp']}.csv` - Original data backup

---
*Report generated by Comprehensive Display Name Fixer*
"""

    def run(self) -> None:
        """Execute the complete fixing process."""
        try:
            self.logger.info("Starting comprehensive display name fixing process...")

            # Create backup
            backup_file = self.create_backup()

            # Process all records
            self.logger.info("Processing records and applying fixes...")
            fixed_records = self.process_records()

            # Save corrected file
            output_file = self.save_corrected_csv(fixed_records)

            # Generate rules for future use
            self.generate_correction_rules()

            # Generate comprehensive report
            self.generate_report(output_file, backup_file)

            # Log final summary
            self.logger.info(f"Process completed successfully!")
            self.logger.info(f"Total records: {self.stats['total_records']:,}")
            self.logger.info(f"Non-Japanese display names fixed: {self.stats['non_japanese_display_fixed']}")
            self.logger.info(f"Auto-fixable using person_name_ja: {self.stats['auto_fixable_using_ja']}")
            self.logger.info(f"Incorrect groups fixed: {self.stats['incorrect_groups_fixed']}")
            self.logger.info(f"Records needing translation: {self.stats['needs_translation']}")
            self.logger.info(f"Output file: {output_file}")

        except Exception as e:
            self.logger.error(f"Process failed: {e}")
            raise


def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(description="Fix all display name issues in Ultra Think database")
    parser.add_argument("input_file", help="Input CSV file path")
    parser.add_argument("--output-dir", "-o", default=".", help="Output directory (default: current)")

    args = parser.parse_args()

    # Validate input file
    if not Path(args.input_file).exists():
        print(f"Error: Input file {args.input_file} not found")
        return 1

    # Create output directory if needed
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    # Run the fixer
    fixer = ComprehensiveDisplayNameFixer(args.input_file, output_dir)
    fixer.run()

    return 0


if __name__ == "__main__":
    exit(main())
