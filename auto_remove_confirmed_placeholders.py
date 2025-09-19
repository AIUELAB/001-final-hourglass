#!/usr/bin/env python3
"""
Auto-Remove Confirmed Placeholders

This script automatically removes the confirmed placeholder IDs (P001452-P001460)
with full backup and logging capabilities.

Based on the comprehensive placeholder_detector_and_remover.py
"""

import csv
import json
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Configuration
CONFIG = {
    'input_file': 'ultra_think_master_cleaned.csv',
    'backup_dir': 'emergency_backups',
    'report_dir': 'placeholder_reports'
}

# Confirmed placeholders to remove
CONFIRMED_PLACEHOLDERS = {
    'P001452', 'P001453', 'P001454', 'P001455', 'P001456',
    'P001457', 'P001458', 'P001459', 'P001460'
}

def setup_logging() -> logging.Logger:
    """Setup logging for the removal process"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Create directories
    Path(CONFIG['backup_dir']).mkdir(exist_ok=True)
    Path(CONFIG['report_dir']).mkdir(exist_ok=True)
    
    log_file = Path(CONFIG['report_dir']) / f'confirmed_placeholder_removal_{timestamp}.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Auto-removal system initialized - Log: {log_file}")
    return logger

def create_backup(input_file: Path, backup_dir: Path, logger: logging.Logger) -> str:
    """Create timestamped backup of original file"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = backup_dir / f"backup_before_confirmed_removal_{timestamp}.csv"
    
    try:
        shutil.copy2(input_file, backup_path)
        logger.info(f"✅ Backup created: {backup_path}")
        return str(backup_path)
    except Exception as e:
        logger.error(f"❌ Failed to create backup: {e}")
        raise

def load_data(input_file: Path, logger: logging.Logger) -> List[Dict]:
    """Load CSV data"""
    try:
        if not input_file.exists():
            logger.error(f"❌ Input file not found: {input_file}")
            return []
        
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            records = list(reader)
        
        logger.info(f"📊 Loaded {len(records):,} records from {input_file}")
        return records
        
    except Exception as e:
        logger.error(f"❌ Error loading data: {e}")
        return []

def find_confirmed_placeholders(records: List[Dict], logger: logging.Logger) -> Tuple[List[Dict], List[Dict]]:
    """Find and separate confirmed placeholders from valid records"""
    confirmed_records = []
    valid_records = []
    
    for record in records:
        person_id = record.get('person_id', '')
        if person_id in CONFIRMED_PLACEHOLDERS:
            confirmed_records.append(record)
        else:
            valid_records.append(record)
    
    logger.info(f"🎯 Found {len(confirmed_records)} confirmed placeholders to remove")
    logger.info(f"✅ Keeping {len(valid_records):,} valid records")
    
    # Log details of confirmed placeholders
    for record in confirmed_records:
        person_id = record.get('person_id', '')
        person_name = record.get('person_name', '').strip()
        person_name_ja = record.get('person_name_ja', '').strip()
        logger.info(f"   📋 {person_id}: {person_name} / {person_name_ja}")
    
    return confirmed_records, valid_records

def save_cleaned_data(valid_records: List[Dict], input_file: Path, logger: logging.Logger) -> str:
    """Save the cleaned data to a new file"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    cleaned_path = input_file.parent / f"ultra_think_CONFIRMED_PLACEHOLDERS_REMOVED_{timestamp}.csv"
    
    try:
        with open(cleaned_path, 'w', newline='', encoding='utf-8') as f:
            if valid_records:
                writer = csv.DictWriter(f, fieldnames=valid_records[0].keys())
                writer.writeheader()
                writer.writerows(valid_records)
        
        logger.info(f"💾 Cleaned file saved: {cleaned_path}")
        return str(cleaned_path)
        
    except Exception as e:
        logger.error(f"❌ Error saving cleaned data: {e}")
        raise

def create_removal_report(confirmed_records: List[Dict], input_file: Path, 
                         backup_path: str, cleaned_path: str, 
                         report_dir: Path, logger: logging.Logger) -> str:
    """Create detailed removal report"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = report_dir / f"confirmed_placeholder_removal_report_{timestamp}.json"
    
    removal_report = {
        'timestamp': timestamp,
        'operation': 'confirmed_placeholder_removal',
        'input_file': str(input_file),
        'backup_file': backup_path,
        'output_file': cleaned_path,
        'removal_summary': {
            'total_removed': len(confirmed_records),
            'placeholder_ids': list(CONFIRMED_PLACEHOLDERS),
            'records_removed': [
                {
                    'person_id': r.get('person_id', ''),
                    'person_name': r.get('person_name', '').strip(),
                    'person_name_ja': r.get('person_name_ja', '').strip(),
                    'episode_id': r.get('episode_id', ''),
                    'created_at': r.get('created_at', '')
                }
                for r in confirmed_records
            ]
        },
        'statistics': {
            'original_count': len(confirmed_records) + len([r for r in [] if r]),  # Will be filled
            'removed_count': len(confirmed_records),
            'remaining_count': None  # Will be filled
        }
    }
    
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(removal_report, f, indent=2, ensure_ascii=False)
        
        # Also create markdown report
        md_report_path = report_dir / f"confirmed_placeholder_removal_report_{timestamp}.md"
        create_markdown_report(removal_report, md_report_path)
        
        logger.info(f"📋 Reports created: {report_path}, {md_report_path}")
        return str(report_path)
        
    except Exception as e:
        logger.error(f"❌ Error creating report: {e}")
        raise

def create_markdown_report(report_data: Dict, output_path: Path):
    """Create human-readable markdown report"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# Confirmed Placeholder Removal Report\n\n")
        f.write(f"**Timestamp**: {report_data['timestamp']}\n")
        f.write(f"**Operation**: {report_data['operation']}\n")
        f.write(f"**Input File**: {report_data['input_file']}\n")
        f.write(f"**Backup File**: {report_data['backup_file']}\n")
        f.write(f"**Output File**: {report_data['output_file']}\n\n")
        
        f.write("## Removal Summary\n\n")
        summary = report_data['removal_summary']
        f.write(f"**Total Records Removed**: {summary['total_removed']}\n")
        f.write(f"**Placeholder IDs Targeted**: {', '.join(summary['placeholder_ids'])}\n\n")
        
        f.write("### Removed Records\n\n")
        for record in summary['records_removed']:
            f.write(f"- **{record['person_id']}**: {record['person_name']} / {record['person_name_ja']}\n")
            f.write(f"  - Episode ID: {record['episode_id']}\n")
            f.write(f"  - Created: {record['created_at']}\n\n")
        
        f.write("## Operation Result\n\n")
        f.write("✅ **SUCCESS**: All confirmed placeholders (P001452-P001460) have been successfully removed.\n\n")
        f.write("### Safety Measures\n\n")
        f.write("- ✅ Full backup created before removal\n")
        f.write("- ✅ Only targeted placeholder IDs removed\n")
        f.write("- ✅ All other records preserved\n")
        f.write("- ✅ Detailed logging and reporting\n")
        f.write("- ✅ Rollback capability available\n\n")
        
        f.write("### Next Steps\n\n")
        f.write("1. **Verify Results**: Check the cleaned file to ensure correct removal\n")
        f.write("2. **Update References**: Update any scripts/processes to use the new file\n")
        f.write("3. **Archive Backup**: Keep the backup file for potential rollback\n")
        f.write("4. **Quality Check**: Run data quality validation on the cleaned dataset\n")

def main() -> int:
    """Main execution function"""
    print("🗑️ Confirmed Placeholder Auto-Removal System")
    print("=" * 50)
    print(f"🎯 Target: Remove P001452-P001460 ({len(CONFIRMED_PLACEHOLDERS)} IDs)")
    print()
    
    # Initialize
    logger = setup_logging()
    input_file = Path(CONFIG['input_file'])
    backup_dir = Path(CONFIG['backup_dir'])
    report_dir = Path(CONFIG['report_dir'])
    
    try:
        # Step 1: Load data
        print("📊 Loading data...")
        records = load_data(input_file, logger)
        if not records:
            print("❌ Failed to load data. Exiting.")
            return 1
        
        # Step 2: Create backup
        print("💾 Creating backup...")
        backup_path = create_backup(input_file, backup_dir, logger)
        
        # Step 3: Find confirmed placeholders
        print("🔍 Identifying confirmed placeholders...")
        confirmed_records, valid_records = find_confirmed_placeholders(records, logger)
        
        if not confirmed_records:
            print("ℹ️ No confirmed placeholders found. Nothing to remove.")
            logger.info("No confirmed placeholders found")
            return 0
        
        # Step 4: Save cleaned data
        print("💾 Saving cleaned data...")
        cleaned_path = save_cleaned_data(valid_records, input_file, logger)
        
        # Step 5: Create report
        print("📋 Creating removal report...")
        report_path = create_removal_report(
            confirmed_records, input_file, backup_path, 
            cleaned_path, report_dir, logger
        )
        
        # Step 6: Display summary
        print()
        print("✅ REMOVAL COMPLETED SUCCESSFULLY")
        print(f"   📊 Original Records: {len(records):,}")
        print(f"   🗑️ Records Removed: {len(confirmed_records):,}")
        print(f"   ✅ Records Remaining: {len(valid_records):,}")
        print(f"   📄 Cleaned File: {cleaned_path}")
        print(f"   💾 Backup File: {backup_path}")
        print(f"   📋 Report: {report_path}")
        print()
        print("🔒 Safety Features:")
        print("   ✅ Full backup created")
        print("   ✅ Only confirmed placeholders removed")
        print("   ✅ Detailed logging and reporting")
        print("   ✅ Rollback capability available")
        
        logger.info("Confirmed placeholder removal completed successfully")
        return 0
        
    except Exception as e:
        print(f"❌ Error during removal: {e}")
        logger.error(f"Fatal error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())