#!/usr/bin/env python3
"""
Comprehensive Placeholder Detection and Removal System

This script implements multiple detection methods to identify and safely remove placeholder entries:
- Pattern matching for synthetic names
- Metadata analysis for identical timestamps/scores
- Sequential naming patterns
- Batch creation detection
- Empty/default value analysis
- Similarity clustering

Author: Claude Code
Created: 2025-08-31
Version: 1.0
"""

import csv
import json
import re
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
import hashlib
from difflib import SequenceMatcher

# Configuration
CONFIG = {
    'input_file': 'ultra_think_master_cleaned.csv',
    'backup_dir': 'emergency_backups',
    'report_dir': 'placeholder_reports',
    'batch_time_threshold': 5.0,  # seconds
    'similarity_threshold': 0.85,
    'confidence_threshold': 0.7,
    'max_rollback_age_hours': 24
}

@dataclass
class PlaceholderDetection:
    """Data structure for placeholder detection results"""
    person_id: str
    person_name: str
    person_name_ja: str
    confidence: float
    detection_methods: List[str]
    reasoning: List[str]
    metadata: Dict
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL

class PlaceholderDetector:
    """Comprehensive placeholder detection and removal system"""

    def __init__(self, input_file: str):
        self.input_file = Path(input_file)
        self.backup_dir = Path(CONFIG['backup_dir'])
        self.report_dir = Path(CONFIG['report_dir'])

        # Create directories first
        self.backup_dir.mkdir(exist_ok=True)
        self.report_dir.mkdir(exist_ok=True)

        self.logger = self._setup_logging()

        # Data storage
        self.records = []
        self.detections: List[PlaceholderDetection] = []
        self.confirmed_placeholders = {
            'P001452', 'P001453', 'P001454', 'P001455', 'P001456',
            'P001457', 'P001458', 'P001459', 'P001460'
        }

    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive logging"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = self.report_dir / f'placeholder_detection_{timestamp}.log'

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )

        logger = logging.getLogger(__name__)
        logger.info(f"Placeholder Detection System initialized - Log: {log_file}")
        return logger

    def load_data(self) -> bool:
        """Load CSV data with comprehensive error handling"""
        try:
            if not self.input_file.exists():
                self.logger.error(f"Input file not found: {self.input_file}")
                return False

            with open(self.input_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.records = list(reader)

            self.logger.info(f"Loaded {len(self.records)} records from {self.input_file}")
            return True

        except Exception as e:
            self.logger.error(f"Error loading data: {e}")
            return False

    def detect_pattern_placeholders(self) -> List[PlaceholderDetection]:
        """Detect placeholders using pattern matching"""
        detections = []

        # Comprehensive pattern definitions
        patterns = {
            'synthetic_names': [
                r'リーチ\[.+\]', r'Person\[\d+\]', r'Test\d*', r'Placeholder\d*',
                r'Sample\d*', r'Example\d*', r'Dummy\d*', r'Mock\d*',
                r'Default\d*', r'Template\d*', r'Demo\d*', r'Temp\d*'
            ],
            'generic_names': [
                r'^Test$', r'^Sample$', r'^Example$', r'^Dummy$', r'^Mock$',
                r'^Default$', r'^Template$', r'^Demo$', r'^Temp$', r'^Placeholder$'
            ],
            'sequential_patterns': [
                r'Person[_\-]?\d+', r'User[_\-]?\d+', r'人物[_\-]?\d+',
                r'テスト[_\-]?\d+', r'サンプル[_\-]?\d+'
            ],
            'bracket_patterns': [
                r'\[.+\]', r'【.+】', r'<.+>', r'\{.+\}'
            ]
        }

        for record in self.records:
            person_id = record.get('person_id', '')
            person_name = record.get('person_name', '').strip()
            person_name_ja = record.get('person_name_ja', '').strip()

            detected_patterns = []
            reasoning = []

            # Check all patterns
            for pattern_type, pattern_list in patterns.items():
                for pattern in pattern_list:
                    if (re.search(pattern, person_name, re.IGNORECASE) or
                        re.search(pattern, person_name_ja, re.IGNORECASE)):
                        detected_patterns.append(f"pattern_{pattern_type}")
                        reasoning.append(f"Matches {pattern_type} pattern: {pattern}")

            if detected_patterns:
                confidence = min(0.95, 0.7 + len(detected_patterns) * 0.1)
                detections.append(PlaceholderDetection(
                    person_id=person_id,
                    person_name=person_name,
                    person_name_ja=person_name_ja,
                    confidence=confidence,
                    detection_methods=detected_patterns,
                    reasoning=reasoning,
                    metadata={'pattern_matches': len(detected_patterns)},
                    risk_level='HIGH'
                ))

        self.logger.info(f"Pattern detection found {len(detections)} placeholders")
        return detections

    def detect_metadata_placeholders(self) -> List[PlaceholderDetection]:
        """Detect placeholders using metadata analysis"""
        detections = []

        # Group by metadata patterns
        timestamp_groups = defaultdict(list)
        score_groups = defaultdict(list)

        for record in self.records:
            created_at = record.get('created_at', '')
            name_recognition = record.get('name_recognition', '')
            accuracy_score = record.get('accuracy_score', '')

            if created_at:
                # Group by minute precision
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    minute_key = dt.strftime('%Y-%m-%d %H:%M')
                    timestamp_groups[minute_key].append(record)
                except:
                    pass

            # Group by identical scores
            if name_recognition and accuracy_score:
                score_key = f"{name_recognition}_{accuracy_score}"
                score_groups[score_key].append(record)

        # Detect suspicious timestamp clusters
        for timestamp, records in timestamp_groups.items():
            if len(records) >= 5:  # 5+ records in same minute
                for record in records:
                    person_id = record.get('person_id', '')
                    person_name = record.get('person_name', '').strip()
                    person_name_ja = record.get('person_name_ja', '').strip()

                    # Check for other suspicious indicators
                    suspicious_indicators = []
                    if not record.get('birth_year'):
                        suspicious_indicators.append('missing_birth_year')
                    if record.get('nationality') == '不明':
                        suspicious_indicators.append('unknown_nationality')
                    if record.get('occupation') == '不明':
                        suspicious_indicators.append('unknown_occupation')

                    if suspicious_indicators:
                        confidence = 0.6 + len(suspicious_indicators) * 0.1
                        detections.append(PlaceholderDetection(
                            person_id=person_id,
                            person_name=person_name,
                            person_name_ja=person_name_ja,
                            confidence=confidence,
                            detection_methods=['metadata_timestamp_cluster'],
                            reasoning=[
                                f"Part of {len(records)} records created in minute {timestamp}",
                                f"Suspicious indicators: {', '.join(suspicious_indicators)}"
                            ],
                            metadata={
                                'cluster_size': len(records),
                                'timestamp': timestamp,
                                'suspicious_indicators': suspicious_indicators
                            },
                            risk_level='MEDIUM'
                        ))

        # Detect identical score patterns
        for score_key, records in score_groups.items():
            if len(records) >= 10 and score_key in ['50_3', '50_50', '0_0']:
                for record in records:
                    person_id = record.get('person_id', '')
                    if person_id not in [d.person_id for d in detections]:
                        person_name = record.get('person_name', '').strip()
                        person_name_ja = record.get('person_name_ja', '').strip()

                        detections.append(PlaceholderDetection(
                            person_id=person_id,
                            person_name=person_name,
                            person_name_ja=person_name_ja,
                            confidence=0.5,
                            detection_methods=['metadata_identical_scores'],
                            reasoning=[
                                f"Part of {len(records)} records with identical scores: {score_key}",
                                "Identical scores suggest batch generation"
                            ],
                            metadata={
                                'score_pattern': score_key,
                                'cluster_size': len(records)
                            },
                            risk_level='LOW'
                        ))

        self.logger.info(f"Metadata detection found {len(detections)} placeholders")
        return detections

    def detect_similarity_clusters(self) -> List[PlaceholderDetection]:
        """Detect placeholders using name similarity clustering (optimized)"""
        detections = []

        # First, group by exact names to avoid expensive similarity checks
        exact_groups = defaultdict(list)
        for record in self.records:
            person_name = record.get('person_name', '').strip()
            person_name_ja = record.get('person_name_ja', '').strip()
            primary_name = person_name_ja if person_name_ja else person_name

            if primary_name:
                exact_groups[primary_name].append(record)

        # Only check similarity for names that appear multiple times or are very short
        name_groups = defaultdict(list)
        processed_names = set()

        for primary_name, records in exact_groups.items():
            if len(records) >= 3 or len(primary_name) <= 5:  # Suspicious patterns
                if primary_name not in processed_names:
                    name_groups[primary_name].extend(records)
                    processed_names.add(primary_name)

                    # Only check similarity for suspicious names
                    if len(primary_name) <= 5:  # Short names are more likely to be similar
                        for other_name, other_records in exact_groups.items():
                            if (other_name != primary_name and
                                other_name not in processed_names and
                                len(other_name) <= 8):  # Limit comparison scope

                                similarity = SequenceMatcher(None, primary_name, other_name).ratio()
                                if similarity > CONFIG['similarity_threshold']:
                                    name_groups[primary_name].extend(other_records)
                                    processed_names.add(other_name)

        # Detect suspicious similarity clusters
        for group_name, records in name_groups.items():
            if len(records) >= 3:  # 3+ very similar names
                # Check if they have incremental IDs or timestamps
                person_ids = [r.get('person_id', '') for r in records]
                timestamps = [r.get('created_at', '') for r in records]

                # Check for incremental patterns
                incremental_ids = self._check_incremental_pattern(person_ids)
                close_timestamps = self._check_timestamp_proximity(timestamps)

                if incremental_ids or close_timestamps:
                    for record in records:
                        person_id = record.get('person_id', '')
                        person_name = record.get('person_name', '').strip()
                        person_name_ja = record.get('person_name_ja', '').strip()

                        reasoning = [
                            f"Part of {len(records)} similar names cluster: {group_name}"
                        ]
                        methods = ['similarity_cluster']

                        if incremental_ids:
                            reasoning.append("Sequential person IDs detected")
                            methods.append('incremental_ids')

                        if close_timestamps:
                            reasoning.append("Created within close time proximity")
                            methods.append('timestamp_proximity')

                        confidence = 0.7 if incremental_ids and close_timestamps else 0.6

                        detections.append(PlaceholderDetection(
                            person_id=person_id,
                            person_name=person_name,
                            person_name_ja=person_name_ja,
                            confidence=confidence,
                            detection_methods=methods,
                            reasoning=reasoning,
                            metadata={
                                'cluster_size': len(records),
                                'group_name': group_name,
                                'incremental_ids': incremental_ids,
                                'close_timestamps': close_timestamps
                            },
                            risk_level='MEDIUM'
                        ))

        self.logger.info(f"Similarity detection found {len(detections)} placeholders")
        return detections

    def _check_incremental_pattern(self, ids: List[str]) -> bool:
        """Check if IDs follow incremental pattern"""
        if len(ids) < 2:
            return False

        # Extract numeric parts
        numeric_parts = []
        for id_str in ids:
            numbers = re.findall(r'\d+', id_str)
            if numbers:
                numeric_parts.append(int(numbers[-1]))  # Use last number

        if len(numeric_parts) < 2:
            return False

        # Check if they're sequential or have small gaps
        numeric_parts.sort()
        gaps = [numeric_parts[i+1] - numeric_parts[i] for i in range(len(numeric_parts)-1)]

        # Allow gaps of 1-3 for sequential patterns
        return all(1 <= gap <= 3 for gap in gaps)

    def _check_timestamp_proximity(self, timestamps: List[str]) -> bool:
        """Check if timestamps are very close together"""
        if len(timestamps) < 2:
            return False

        parsed_times = []
        for ts in timestamps:
            if ts:
                try:
                    # Handle multiple datetime formats
                    if 'T' in ts:
                        if ts.endswith('Z'):
                            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                        elif '+' in ts or 'T' in ts:
                            dt = datetime.fromisoformat(ts)
                        else:
                            dt = datetime.fromisoformat(ts)
                    else:
                        continue
                    parsed_times.append(dt)
                except:
                    continue

        if len(parsed_times) < 2:
            return False

        parsed_times.sort()
        # Check if all created within threshold
        time_span = (parsed_times[-1] - parsed_times[0]).total_seconds()
        return time_span <= CONFIG['batch_time_threshold']

    def detect_confirmed_placeholders(self) -> List[PlaceholderDetection]:
        """Detect the specifically confirmed placeholder IDs"""
        detections = []

        for record in self.records:
            person_id = record.get('person_id', '')

            if person_id in self.confirmed_placeholders:
                person_name = record.get('person_name', '').strip()
                person_name_ja = record.get('person_name_ja', '').strip()

                detections.append(PlaceholderDetection(
                    person_id=person_id,
                    person_name=person_name,
                    person_name_ja=person_name_ja,
                    confidence=1.0,
                    detection_methods=['confirmed_placeholder'],
                    reasoning=['Confirmed placeholder ID from P001452-P001460 range'],
                    metadata={'confirmed': True},
                    risk_level='CRITICAL'
                ))

        self.logger.info(f"Confirmed placeholder detection found {len(detections)} placeholders")
        return detections

    def detect_empty_default_values(self) -> List[PlaceholderDetection]:
        """Detect placeholders with empty or default values"""
        detections = []

        for record in self.records:
            person_id = record.get('person_id', '')
            person_name = record.get('person_name', '').strip()
            person_name_ja = record.get('person_name_ja', '').strip()

            # Critical field checks
            empty_indicators = []
            if not person_name and not person_name_ja:
                empty_indicators.append('empty_names')

            if not record.get('birth_year'):
                empty_indicators.append('missing_birth_year')

            if record.get('nationality') in ['不明', '', None]:
                empty_indicators.append('unknown_nationality')

            if record.get('occupation') in ['不明', '', None]:
                empty_indicators.append('unknown_occupation')

            if record.get('era') in ['不明', '', None]:
                empty_indicators.append('unknown_era')

            # Check for default/placeholder values
            default_indicators = []
            if record.get('name_recognition') == '50':
                default_indicators.append('default_recognition_score')

            if record.get('accuracy_score') in ['3', '0']:
                default_indicators.append('default_accuracy_score')

            if record.get('episode_title') in ['無題のエピソード', '', None]:
                default_indicators.append('default_episode_title')

            # Require multiple indicators for detection
            total_indicators = len(empty_indicators) + len(default_indicators)
            if total_indicators >= 3:
                confidence = min(0.8, 0.4 + total_indicators * 0.1)

                detections.append(PlaceholderDetection(
                    person_id=person_id,
                    person_name=person_name,
                    person_name_ja=person_name_ja,
                    confidence=confidence,
                    detection_methods=['empty_default_values'],
                    reasoning=[
                        f"Multiple empty/default indicators: {total_indicators}",
                        f"Empty fields: {', '.join(empty_indicators)}",
                        f"Default values: {', '.join(default_indicators)}"
                    ],
                    metadata={
                        'empty_indicators': empty_indicators,
                        'default_indicators': default_indicators,
                        'total_indicators': total_indicators
                    },
                    risk_level='MEDIUM'
                ))

        self.logger.info(f"Empty/default detection found {len(detections)} placeholders")
        return detections

    def run_all_detections(self) -> List[PlaceholderDetection]:
        """Run all detection methods and consolidate results"""
        self.logger.info("Starting comprehensive placeholder detection...")
        print("🔍 Running detection methods:")

        all_detections = []

        # Run all detection methods
        detection_methods = [
            ("Confirmed Placeholders", self.detect_confirmed_placeholders),
            ("Pattern Matching", self.detect_pattern_placeholders),
            ("Metadata Analysis", self.detect_metadata_placeholders),
            ("Similarity Clustering", self.detect_similarity_clusters),
            ("Empty/Default Values", self.detect_empty_default_values)
        ]

        for name, method in detection_methods:
            try:
                print(f"   ⏳ {name}...", end=" ", flush=True)
                detections = method()
                all_detections.extend(detections)
                print(f"✅ Found {len(detections)} placeholders")
                self.logger.info(f"{method.__name__} completed successfully")
            except Exception as e:
                print(f"❌ Error")
                self.logger.error(f"Error in {method.__name__}: {e}")

        # Consolidate duplicates (same person_id)
        consolidated = {}
        for detection in all_detections:
            person_id = detection.person_id
            if person_id in consolidated:
                # Merge detection methods and reasoning
                existing = consolidated[person_id]
                existing.detection_methods.extend(detection.detection_methods)
                existing.reasoning.extend(detection.reasoning)
                existing.confidence = max(existing.confidence, detection.confidence)
                existing.metadata.update(detection.metadata)
                # Use highest risk level
                risk_levels = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'CRITICAL': 4}
                if risk_levels[detection.risk_level] > risk_levels[existing.risk_level]:
                    existing.risk_level = detection.risk_level
            else:
                consolidated[person_id] = detection

        self.detections = list(consolidated.values())
        self.logger.info(f"Consolidated {len(all_detections)} detections into {len(self.detections)} unique placeholders")

        return self.detections

    def create_backup(self) -> str:
        """Create timestamped backup of original file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = self.backup_dir / f"backup_before_placeholder_removal_{timestamp}.csv"

        try:
            shutil.copy2(self.input_file, backup_path)
            self.logger.info(f"Backup created: {backup_path}")
            return str(backup_path)
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            raise

    def generate_comprehensive_report(self) -> str:
        """Generate detailed analysis report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = self.report_dir / f"placeholder_detection_report_{timestamp}.json"

        # Categorize detections by risk level and confidence
        by_risk = defaultdict(list)
        by_confidence = defaultdict(list)
        by_methods = defaultdict(list)

        for detection in self.detections:
            by_risk[detection.risk_level].append(detection)

            conf_level = 'HIGH' if detection.confidence >= 0.8 else 'MEDIUM' if detection.confidence >= 0.6 else 'LOW'
            by_confidence[conf_level].append(detection)

            for method in detection.detection_methods:
                by_methods[method].append(detection)

        report_data = {
            'summary': {
                'total_records': len(self.records),
                'total_detections': len(self.detections),
                'detection_rate': round(len(self.detections) / len(self.records) * 100, 2),
                'timestamp': timestamp
            },
            'risk_analysis': {
                risk: {
                    'count': len(detections),
                    'percentage': round(len(detections) / len(self.detections) * 100, 2) if self.detections else 0
                }
                for risk, detections in by_risk.items()
            },
            'confidence_analysis': {
                conf: {
                    'count': len(detections),
                    'percentage': round(len(detections) / len(self.detections) * 100, 2) if self.detections else 0
                }
                for conf, detections in by_confidence.items()
            },
            'method_analysis': {
                method: {
                    'count': len(detections),
                    'percentage': round(len(detections) / len(self.detections) * 100, 2) if self.detections else 0
                }
                for method, detections in by_methods.items()
            },
            'detections': [asdict(d) for d in self.detections],
            'recommendations': self._generate_recommendations()
        }

        # Write report
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        # Also create human-readable report
        md_report_path = self.report_dir / f"placeholder_detection_report_{timestamp}.md"
        self._create_markdown_report(report_data, md_report_path)

        self.logger.info(f"Reports generated: {report_path}, {md_report_path}")
        return str(report_path)

    def _generate_recommendations(self) -> Dict:
        """Generate safety recommendations"""
        recommendations = {
            'immediate_removal': [],
            'review_required': [],
            'investigate_further': []
        }

        for detection in self.detections:
            if detection.risk_level == 'CRITICAL' or detection.confidence >= 0.9:
                recommendations['immediate_removal'].append(detection.person_id)
            elif detection.risk_level in ['HIGH', 'MEDIUM'] and detection.confidence >= 0.7:
                recommendations['review_required'].append(detection.person_id)
            else:
                recommendations['investigate_further'].append(detection.person_id)

        return recommendations

    def _create_markdown_report(self, report_data: Dict, output_path: Path):
        """Create human-readable markdown report"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# Placeholder Detection Report\n\n")
            f.write(f"**Generated**: {report_data['summary']['timestamp']}\n")
            f.write(f"**Total Records**: {report_data['summary']['total_records']:,}\n")
            f.write(f"**Placeholders Detected**: {report_data['summary']['total_detections']:,}\n")
            f.write(f"**Detection Rate**: {report_data['summary']['detection_rate']}%\n\n")

            f.write("## Risk Level Analysis\n\n")
            for risk, data in report_data['risk_analysis'].items():
                f.write(f"- **{risk}**: {data['count']} records ({data['percentage']}%)\n")

            f.write("\n## Detection Methods\n\n")
            for method, data in report_data['method_analysis'].items():
                f.write(f"- **{method}**: {data['count']} detections ({data['percentage']}%)\n")

            f.write("\n## Recommendations\n\n")
            recs = report_data['recommendations']
            f.write(f"### Immediate Removal ({len(recs['immediate_removal'])} records)\n")
            f.write("High confidence placeholders that should be removed immediately:\n")
            for pid in recs['immediate_removal'][:10]:  # Show first 10
                f.write(f"- {pid}\n")
            if len(recs['immediate_removal']) > 10:
                f.write(f"- ... and {len(recs['immediate_removal']) - 10} more\n")

            f.write(f"\n### Review Required ({len(recs['review_required'])} records)\n")
            f.write("Medium confidence detections requiring human review:\n")
            for pid in recs['review_required'][:10]:
                f.write(f"- {pid}\n")
            if len(recs['review_required']) > 10:
                f.write(f"- ... and {len(recs['review_required']) - 10} more\n")

            f.write("\n## Top 20 Detections by Confidence\n\n")
            sorted_detections = sorted(report_data['detections'], key=lambda x: x['confidence'], reverse=True)
            for i, det in enumerate(sorted_detections[:20], 1):
                f.write(f"### {i}. {det['person_id']} (Confidence: {det['confidence']:.2f})\n")
                f.write(f"**Name**: {det['person_name']} / {det['person_name_ja']}\n")
                f.write(f"**Risk Level**: {det['risk_level']}\n")
                f.write(f"**Detection Methods**: {', '.join(det['detection_methods'])}\n")
                f.write("**Reasoning**:\n")
                for reason in det['reasoning']:
                    f.write(f"- {reason}\n")
                f.write("\n")

    def safe_remove_placeholders(self, confidence_threshold: float = None) -> Tuple[int, str]:
        """Safely remove placeholders with comprehensive validation"""
        if confidence_threshold is None:
            confidence_threshold = CONFIG['confidence_threshold']

        # Create backup first
        backup_path = self.create_backup()

        # Filter records to remove
        to_remove = [d for d in self.detections if d.confidence >= confidence_threshold]
        remove_ids = {d.person_id for d in to_remove}

        self.logger.info(f"Removing {len(to_remove)} placeholders with confidence >= {confidence_threshold}")

        # Filter records
        original_count = len(self.records)
        cleaned_records = [r for r in self.records if r.get('person_id', '') not in remove_ids]
        removed_count = original_count - len(cleaned_records)

        # Write cleaned file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        cleaned_path = self.input_file.parent / f"ultra_think_PLACEHOLDER_CLEANED_{timestamp}.csv"

        try:
            with open(cleaned_path, 'w', newline='', encoding='utf-8') as f:
                if cleaned_records:
                    writer = csv.DictWriter(f, fieldnames=cleaned_records[0].keys())
                    writer.writeheader()
                    writer.writerows(cleaned_records)

            # Create removal log
            removal_log = {
                'timestamp': timestamp,
                'original_file': str(self.input_file),
                'backup_file': backup_path,
                'cleaned_file': str(cleaned_path),
                'original_count': original_count,
                'removed_count': removed_count,
                'remaining_count': len(cleaned_records),
                'confidence_threshold': confidence_threshold,
                'removed_records': [asdict(d) for d in to_remove]
            }

            log_path = self.report_dir / f"removal_log_{timestamp}.json"
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(removal_log, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Successfully removed {removed_count} records")
            self.logger.info(f"Cleaned file: {cleaned_path}")
            self.logger.info(f"Removal log: {log_path}")

            return removed_count, str(cleaned_path)

        except Exception as e:
            self.logger.error(f"Error during removal: {e}")
            # Restore from backup if something went wrong
            if backup_path and Path(backup_path).exists():
                shutil.copy2(backup_path, self.input_file)
                self.logger.info(f"Restored original file from backup")
            raise

    def rollback(self, backup_file: str) -> bool:
        """Rollback to previous version"""
        try:
            backup_path = Path(backup_file)
            if not backup_path.exists():
                self.logger.error(f"Backup file not found: {backup_path}")
                return False

            # Check backup age
            backup_time = datetime.fromtimestamp(backup_path.stat().st_mtime)
            age_hours = (datetime.now() - backup_time).total_seconds() / 3600

            if age_hours > CONFIG['max_rollback_age_hours']:
                self.logger.warning(f"Backup is {age_hours:.1f} hours old (max: {CONFIG['max_rollback_age_hours']})")
                response = input("Continue with rollback? (y/N): ")
                if response.lower() != 'y':
                    return False

            # Create backup of current state before rollback
            current_backup = self.create_backup()

            # Perform rollback
            shutil.copy2(backup_path, self.input_file)

            self.logger.info(f"Successfully rolled back to: {backup_path}")
            self.logger.info(f"Previous state backed up to: {current_backup}")

            return True

        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return False

def main():
    """Main execution function"""
    print("🔍 Comprehensive Placeholder Detection and Removal System")
    print("=" * 60)

    # Initialize detector
    detector = PlaceholderDetector(CONFIG['input_file'])

    # Load data
    if not detector.load_data():
        print("❌ Failed to load data. Exiting.")
        return 1

    # Run detections
    print("\n🔍 Running comprehensive placeholder detection...")
    detections = detector.run_all_detections()

    # Generate report
    print(f"\n📊 Generating comprehensive analysis report...")
    report_path = detector.generate_comprehensive_report()

    # Display summary
    print(f"\n📈 DETECTION SUMMARY")
    print(f"   Total Records: {len(detector.records):,}")
    print(f"   Placeholders Found: {len(detections):,}")
    print(f"   Detection Rate: {len(detections) / len(detector.records) * 100:.2f}%")

    # Risk level breakdown
    risk_counts = {}
    for detection in detections:
        risk_counts[detection.risk_level] = risk_counts.get(detection.risk_level, 0) + 1

    print(f"\n🎯 RISK LEVEL BREAKDOWN")
    for risk in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        count = risk_counts.get(risk, 0)
        if count > 0:
            print(f"   {risk}: {count:,} records")

    # Method breakdown
    method_counts = {}
    for detection in detections:
        for method in detection.detection_methods:
            method_counts[method] = method_counts.get(method, 0) + 1

    print(f"\n🔧 DETECTION METHOD BREAKDOWN")
    for method, count in sorted(method_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"   {method}: {count:,} detections")

    print(f"\n📋 Report generated: {report_path}")
    print(f"📋 Check the reports directory for detailed analysis")

    # Ask for removal
    high_conf = len([d for d in detections if d.confidence >= 0.8])
    confirmed = len([d for d in detections if 'confirmed_placeholder' in d.detection_methods])

    print(f"\n⚡ REMOVAL RECOMMENDATIONS")
    print(f"   High Confidence (≥0.8): {high_conf:,} records")
    print(f"   Confirmed Placeholders: {confirmed:,} records")

    if confirmed > 0:
        response = input(f"\n🗑️  Remove {confirmed} confirmed placeholders? (y/N): ")
        if response.lower() == 'y':
            removed_count, cleaned_file = detector.safe_remove_placeholders(confidence_threshold=0.99)
            print(f"✅ Successfully removed {removed_count:,} confirmed placeholders")
            print(f"📄 Cleaned file: {cleaned_file}")

    if high_conf > confirmed:
        response = input(f"\n🗑️  Remove {high_conf} high-confidence placeholders? (y/N): ")
        if response.lower() == 'y':
            removed_count, cleaned_file = detector.safe_remove_placeholders(confidence_threshold=0.8)
            print(f"✅ Successfully removed {removed_count:,} high-confidence placeholders")
            print(f"📄 Cleaned file: {cleaned_file}")

    print(f"\n✅ Placeholder detection and removal completed successfully!")
    print(f"📊 Check the placeholder_reports/ directory for detailed analysis")

    return 0

if __name__ == "__main__":
    exit(main())
