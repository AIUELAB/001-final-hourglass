#!/usr/bin/env python3
"""
Audio Notification Integration Examples

Demonstrates various ways to integrate audio notifications into
data processing scripts, automation tasks, and quality checks.
"""

import logging
import random
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from notification_integration import (
    notification_context,
    notify_automation_task,
    notify_data_processing,
    notify_data_quality_check,
    notify_task_progress,
    notify_with_sound,
    quick_notify_error,
    quick_notify_info,
    quick_notify_progress,
    quick_notify_success,
    quick_notify_warning,
    setup_notification_logging,
)
from notification_system import NotificationType


def basic_notification_examples() -> None:
    """Demonstrate basic notification usage."""
    print("\n📢 Basic Notification Examples")
    print("=" * 50)
    
    # Simple success notification
    print("✅ Data processing completed successfully!")
    quick_notify_success("Data processing completed")
    time.sleep(0.5)
    
    # Error notification
    print("❌ Failed to connect to database")
    quick_notify_error("Database connection failed")
    time.sleep(0.5)
    
    # Warning notification
    print("⚠️  Disk space is running low")
    quick_notify_warning("Low disk space")
    time.sleep(0.5)
    
    # Info notification
    print("ℹ️  Starting backup process")
    quick_notify_info("Backup started")
    time.sleep(0.5)


@notify_data_quality_check
def data_quality_example() -> Dict[str, int]:
    """Example data quality check with notification decorators."""
    print("Running comprehensive data quality check...")
    
    # Simulate quality check steps
    checks = [
        "Checking for null values",
        "Validating data types", 
        "Checking for duplicates",
        "Verifying constraints",
        "Checking data completeness"
    ]
    
    results = {"passed": 0, "failed": 0}
    
    for i, check in enumerate(checks):
        print(f"  [{i+1}/{len(checks)}] {check}...")
        time.sleep(0.3)  # Simulate processing time
        
        # Randomly pass or fail checks for demo
        if random.random() > 0.2:  # 80% pass rate
            results["passed"] += 1
            quick_notify_progress(f"✅ {check} - PASSED")
        else:
            results["failed"] += 1
            quick_notify_warning(f"❌ {check} - FAILED")
    
    print(f"Quality check completed: {results['passed']} passed, {results['failed']} failed")
    return results


@notify_data_processing
def data_transformation_example(records: int = 1000) -> bool:
    """Example data transformation with progress notifications."""
    print(f"Transforming {records} records...")
    
    batch_size = 100
    processed = 0
    
    for batch_start in range(0, records, batch_size):
        batch_end = min(batch_start + batch_size, records)
        batch_records = batch_end - batch_start
        
        # Simulate processing time
        time.sleep(0.1)
        processed += batch_records
        
        progress_pct = (processed / records) * 100
        print(f"  Processed {processed}/{records} records ({progress_pct:.1f}%)")
        
        # Send progress notification every 25%
        if progress_pct % 25 == 0:
            quick_notify_progress(f"Processing {progress_pct:.0f}% complete")
    
    print("Data transformation completed successfully")
    return True


@notify_automation_task
def automated_backup_example() -> None:
    """Example automated backup task."""
    print("Starting automated backup process...")
    
    tasks = [
        "Creating backup directory",
        "Compressing data files",
        "Uploading to cloud storage",
        "Verifying backup integrity",
        "Cleaning up temporary files"
    ]
    
    for i, task in enumerate(tasks):
        print(f"  [{i+1}/{len(tasks)}] {task}...")
        time.sleep(0.4)  # Simulate task time
        
        # Simulate occasional warnings
        if random.random() < 0.2:  # 20% chance of warning
            quick_notify_warning(f"Warning during {task.lower()}")
    
    print("Automated backup completed successfully")


def context_manager_example() -> None:
    """Demonstrate context manager usage."""
    print("\n🔄 Context Manager Example")
    print("=" * 50)
    
    with notification_context(task_name="database migration") as progress:
        steps = [
            "Backing up current database",
            "Running schema migrations",
            "Migrating data",
            "Updating indexes",
            "Verifying migration"
        ]
        
        for i, step in enumerate(steps):
            print(f"  [{i+1}/{len(steps)}] {step}...")
            progress(step)
            time.sleep(0.3)
            
            # Simulate potential error on last step
            if i == len(steps) - 1 and random.random() < 0.3:
                raise Exception("Migration verification failed")
    
    print("Database migration completed successfully!")


@notify_task_progress(total_steps=5)
def multi_step_process_example() -> List[str]:
    """Example multi-step process with automatic progress tracking."""
    print("Executing multi-step data collection process...")
    
    steps = [
        "Initializing collectors",
        "Gathering data from APIs",
        "Processing raw data",
        "Applying quality filters",
        "Generating final report"
    ]
    
    results = []
    for i, step in enumerate(steps):
        print(f"  Step {i+1}: {step}...")
        time.sleep(0.4)
        
        # Progress notifications are handled by decorator
        step_result = f"Completed: {step}"
        results.append(step_result)
        
        # Send manual progress for detailed tracking
        progress_pct = ((i + 1) / len(steps)) * 100
        if progress_pct % 20 == 0:
            quick_notify_progress(f"Multi-step process {progress_pct:.0f}% complete")
    
    return results


def error_handling_example() -> None:
    """Demonstrate error handling with notifications."""
    print("\n⚠️  Error Handling Example")
    print("=" * 50)
    
    @notify_with_sound(NotificationType.TASK_START, "Testing error handling")
    def failing_function() -> None:
        """Function that deliberately fails."""
        print("Attempting risky operation...")
        time.sleep(0.5)
        raise ValueError("Simulated error for demonstration")
    
    try:
        failing_function()
    except ValueError as e:
        print(f"Caught error: {e}")
        quick_notify_error(f"Operation failed: {e}")


def logging_integration_example() -> None:
    """Demonstrate logging integration with notifications."""
    print("\n📝 Logging Integration Example")
    print("=" * 50)
    
    # Setup notification logging
    setup_notification_logging(level=logging.INFO)
    
    # Create logger
    logger = logging.getLogger(__name__)
    
    # Test different log levels
    logger.info("This is an info message")
    time.sleep(0.3)
    
    logger.warning("This is a warning message")
    time.sleep(0.3)
    
    logger.error("This is an error message")
    time.sleep(0.3)
    
    print("Logging integration demonstrated")


def simulation_data_pipeline() -> None:
    """Simulate a complete data pipeline with notifications."""
    print("\n🏭 Complete Data Pipeline Simulation")
    print("=" * 50)
    
    pipeline_steps = [
        ("Data Ingestion", data_ingestion_step),
        ("Data Validation", data_validation_step),
        ("Data Transformation", data_transformation_step),
        ("Quality Assurance", quality_assurance_step),
        ("Data Export", data_export_step),
    ]
    
    with notification_context(task_name="data pipeline") as progress:
        for step_name, step_func in pipeline_steps:
            print(f"\n--- {step_name} ---")
            progress(f"Starting {step_name.lower()}")
            
            try:
                step_func()
                quick_notify_success(f"{step_name} completed")
            except Exception as e:
                print(f"Error in {step_name}: {e}")
                quick_notify_error(f"{step_name} failed")
                raise
    
    print("\n✅ Complete data pipeline executed successfully!")


def data_ingestion_step() -> None:
    """Simulate data ingestion."""
    sources = ["API endpoint", "CSV files", "Database tables", "JSON feeds"]
    for source in sources:
        print(f"  Ingesting from {source}...")
        time.sleep(0.2)


def data_validation_step() -> None:
    """Simulate data validation."""
    validations = ["Schema validation", "Range checks", "Format validation"]
    for validation in validations:
        print(f"  Running {validation}...")
        time.sleep(0.2)
        
        # Simulate occasional validation warning
        if random.random() < 0.3:
            quick_notify_warning(f"Minor issue in {validation.lower()}")


def data_transformation_step() -> None:
    """Simulate data transformation."""
    transformations = ["Normalization", "Aggregation", "Enrichment", "Cleaning"]
    for transformation in transformations:
        print(f"  Applying {transformation}...")
        time.sleep(0.3)


def quality_assurance_step() -> None:
    """Simulate quality assurance."""
    qa_checks = ["Completeness check", "Accuracy verification", "Consistency check"]
    for check in qa_checks:
        print(f"  Performing {check}...")
        time.sleep(0.2)


def data_export_step() -> None:
    """Simulate data export."""
    exports = ["Generate CSV", "Update database", "Create reports"]
    for export in exports:
        print(f"  {export}...")
        time.sleep(0.2)


def interactive_notification_demo() -> None:
    """Interactive demo for testing different notifications."""
    print("\n🎮 Interactive Notification Demo")
    print("=" * 50)
    
    options = {
        "1": ("Success", lambda: quick_notify_success("Demo success notification")),
        "2": ("Error", lambda: quick_notify_error("Demo error notification")),
        "3": ("Warning", lambda: quick_notify_warning("Demo warning notification")),
        "4": ("Info", lambda: quick_notify_info("Demo info notification")),
        "5": ("Progress", lambda: quick_notify_progress("Demo progress notification")),
        "6": ("Data Quality Check", data_quality_example),
        "7": ("Data Processing", lambda: data_transformation_example(500)),
        "8": ("Automation Task", automated_backup_example),
    }
    
    while True:
        print("\nChoose a notification to test:")
        for key, (name, _) in options.items():
            print(f"  {key}) {name}")
        print("  q) Quit")
        
        choice = input("\nEnter your choice: ").strip().lower()
        
        if choice == 'q':
            break
        elif choice in options:
            try:
                print(f"\n🔊 Playing {options[choice][0]} notification...")
                options[choice][1]()
                print("✅ Notification completed")
            except Exception as e:
                print(f"❌ Error: {e}")
                quick_notify_error(f"Demo error: {e}")
        else:
            print("Invalid choice. Please try again.")


def main() -> None:
    """Main example function."""
    print("🎵 Audio Notification Integration Examples")
    print("=" * 60)
    print("This demonstrates various ways to integrate notifications")
    print("into your data processing and automation scripts.")
    
    examples = [
        ("Basic Notifications", basic_notification_examples),
        ("Data Quality Check", lambda: data_quality_example()),
        ("Data Transformation", lambda: data_transformation_example(500)),
        ("Automated Backup", automated_backup_example),
        ("Context Manager", context_manager_example),
        ("Multi-Step Process", lambda: multi_step_process_example()),
        ("Error Handling", error_handling_example),
        ("Logging Integration", logging_integration_example),
        ("Complete Pipeline", simulation_data_pipeline),
    ]
    
    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}) {name}")
    print("  a) Run all examples")
    print("  i) Interactive demo")
    print("  q) Quit")
    
    while True:
        choice = input("\nSelect an example (1-{}, a, i, q): ".format(len(examples))).strip().lower()
        
        if choice == 'q':
            break
        elif choice == 'a':
            # Run all examples
            for name, func in examples:
                print(f"\n{'='*60}")
                print(f"Running: {name}")
                print('='*60)
                try:
                    func()
                    time.sleep(1)
                except Exception as e:
                    print(f"Error in {name}: {e}")
                    quick_notify_error(f"Example failed: {name}")
            print(f"\n{'='*60}")
            print("All examples completed!")
            break
        elif choice == 'i':
            interactive_notification_demo()
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(examples):
                name, func = examples[idx]
                print(f"\n{'='*60}")
                print(f"Running: {name}")
                print('='*60)
                try:
                    func()
                    quick_notify_success(f"Example completed: {name}")
                except Exception as e:
                    print(f"Error in {name}: {e}")
                    quick_notify_error(f"Example failed: {name}")
            else:
                print("Invalid choice. Please try again.")
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()