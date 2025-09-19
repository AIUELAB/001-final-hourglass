#!/usr/bin/env python3
"""
Test Script for Audio Notification System

Comprehensive testing of notification functionality across different platforms.
Demonstrates usage examples and verifies system compatibility.
"""

import logging
import sys
import time
from pathlib import Path
from typing import Dict, List

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from notification_system import (
        AudioNotificationSystem,
        NotificationType,
        get_notification_system,
        notify_error,
        notify_success,
        notify_task_complete,
    )
except ImportError as e:
    print(f"❌ Failed to import notification system: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)


class NotificationTester:
    """Comprehensive tester for the notification system."""
    
    def __init__(self) -> None:
        """Initialize the tester."""
        self.system = AudioNotificationSystem(enabled=True)
        self.results: Dict[str, bool] = {}
        self.setup_logging()
    
    def setup_logging(self) -> None:
        """Setup logging for the test."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)
    
    def print_header(self, title: str) -> None:
        """Print a formatted header."""
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")
    
    def print_section(self, title: str) -> None:
        """Print a formatted section header."""
        print(f"\n{'-'*50}")
        print(f"  {title}")
        print(f"{'-'*50}")
    
    def test_system_status(self) -> bool:
        """Test system status and configuration."""
        self.print_section("System Status")
        
        try:
            status = self.system.get_status()
            print("✅ System Status:")
            for key, value in status.items():
                print(f"   {key}: {value}")
            return True
        except Exception as e:
            print(f"❌ System status test failed: {e}")
            return False
    
    def test_individual_notifications(self) -> bool:
        """Test each notification type individually."""
        self.print_section("Individual Notification Tests")
        
        success_count = 0
        total_count = len(NotificationType)
        
        for notification_type in NotificationType:
            try:
                print(f"🔊 Testing {notification_type.value}...")
                success = self.system.play_notification(
                    notification_type,
                    f"Test {notification_type.value} notification"
                )
                
                if success:
                    print(f"   ✅ {notification_type.value} - SUCCESS")
                    success_count += 1
                else:
                    print(f"   ❌ {notification_type.value} - FAILED")
                
                # Brief pause between tests
                time.sleep(0.5)
                
            except Exception as e:
                print(f"   ❌ {notification_type.value} - ERROR: {e}")
        
        print(f"\nIndividual Tests: {success_count}/{total_count} passed")
        return success_count == total_count
    
    def test_convenience_functions(self) -> bool:
        """Test convenience functions."""
        self.print_section("Convenience Function Tests")
        
        tests = [
            ("notify_success", lambda: notify_success("Test success message")),
            ("notify_error", lambda: notify_error("Test error message")),
            ("notify_task_complete", lambda: notify_task_complete("Test task complete")),
        ]
        
        success_count = 0
        for name, func in tests:
            try:
                print(f"🔊 Testing {name}...")
                func()
                print(f"   ✅ {name} - SUCCESS")
                success_count += 1
                time.sleep(0.3)
            except Exception as e:
                print(f"   ❌ {name} - ERROR: {e}")
        
        print(f"\nConvenience Functions: {success_count}/{len(tests)} passed")
        return success_count == len(tests)
    
    def test_notification_sequences(self) -> bool:
        """Test notification sequences."""
        self.print_section("Notification Sequence Tests")
        
        try:
            # Test startup sequence
            print("🔊 Testing startup sequence...")
            startup_sequence = [
                NotificationType.TASK_START,
                NotificationType.PROGRESS,
                NotificationType.SUCCESS
            ]
            self.system.play_sequence(startup_sequence, delay=0.2)
            print("   ✅ Startup sequence - SUCCESS")
            
            time.sleep(1)
            
            # Test error sequence
            print("🔊 Testing error sequence...")
            error_sequence = [
                NotificationType.WARNING,
                NotificationType.ERROR
            ]
            self.system.play_sequence(error_sequence, delay=0.3)
            print("   ✅ Error sequence - SUCCESS")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Sequence test - ERROR: {e}")
            return False
    
    def test_volume_control(self) -> bool:
        """Test volume control functionality."""
        self.print_section("Volume Control Tests")
        
        try:
            original_volume = self.system.volume
            
            # Test different volume levels
            volumes = [0.3, 0.7, 1.0]
            for volume in volumes:
                print(f"🔊 Testing volume {volume:.1%}...")
                self.system.set_volume(volume)
                self.system.play_notification(
                    NotificationType.INFO,
                    f"Volume test at {volume:.1%}"
                )
                time.sleep(0.5)
            
            # Restore original volume
            self.system.set_volume(original_volume)
            print("   ✅ Volume control - SUCCESS")
            return True
            
        except Exception as e:
            print(f"   ❌ Volume control - ERROR: {e}")
            return False
    
    def test_enable_disable(self) -> bool:
        """Test enable/disable functionality."""
        self.print_section("Enable/Disable Tests")
        
        try:
            # Test disable
            print("🔇 Testing disable notifications...")
            self.system.disable()
            result = self.system.play_notification(
                NotificationType.INFO,
                "This should not play (disabled)"
            )
            if result:  # Should still return True even when disabled
                print("   ✅ Disable functionality - SUCCESS")
            else:
                print("   ❌ Disable functionality - FAILED")
            
            # Test enable
            print("🔊 Testing enable notifications...")
            self.system.enable()
            result = self.system.play_notification(
                NotificationType.INFO,
                "This should play (enabled)"
            )
            if result:
                print("   ✅ Enable functionality - SUCCESS")
                return True
            else:
                print("   ❌ Enable functionality - FAILED")
                return False
                
        except Exception as e:
            print(f"   ❌ Enable/disable test - ERROR: {e}")
            return False
    
    def test_global_system(self) -> bool:
        """Test global notification system."""
        self.print_section("Global System Tests")
        
        try:
            # Test global system instance
            global_system1 = get_notification_system()
            global_system2 = get_notification_system()
            
            if global_system1 is global_system2:
                print("   ✅ Global system singleton - SUCCESS")
            else:
                print("   ❌ Global system singleton - FAILED")
                return False
            
            # Test global system functionality
            global_system1.play_notification(
                NotificationType.INFO,
                "Global system test"
            )
            print("   ✅ Global system functionality - SUCCESS")
            return True
            
        except Exception as e:
            print(f"   ❌ Global system test - ERROR: {e}")
            return False
    
    def demonstrate_usage_examples(self) -> None:
        """Demonstrate practical usage examples."""
        self.print_section("Usage Examples")
        
        examples = [
            {
                "name": "Data Processing Task",
                "sequence": [
                    (NotificationType.TASK_START, "Starting data processing..."),
                    (NotificationType.PROGRESS, "Processing 25%"),
                    (NotificationType.PROGRESS, "Processing 50%"),
                    (NotificationType.PROGRESS, "Processing 75%"),
                    (NotificationType.SUCCESS, "Data processing completed!"),
                ]
            },
            {
                "name": "Error Handling",
                "sequence": [
                    (NotificationType.TASK_START, "Starting backup..."),
                    (NotificationType.WARNING, "Disk space low"),
                    (NotificationType.ERROR, "Backup failed - insufficient space"),
                ]
            },
            {
                "name": "User Interaction",
                "sequence": [
                    (NotificationType.INFO, "Please review the results"),
                    (NotificationType.WAITING, "Waiting for user input..."),
                    (NotificationType.TASK_COMPLETE, "User input received"),
                ]
            }
        ]
        
        for example in examples:
            print(f"\n📋 Example: {example['name']}")
            for notification_type, message in example['sequence']:
                print(f"   🔊 {message}")
                self.system.play_notification(notification_type, message)
                time.sleep(0.4)
            time.sleep(1)
    
    def run_comprehensive_test(self) -> Dict[str, bool]:
        """Run all tests and return results."""
        self.print_header("Audio Notification System Test Suite")
        
        test_methods = [
            ("System Status", self.test_system_status),
            ("Individual Notifications", self.test_individual_notifications),
            ("Convenience Functions", self.test_convenience_functions),
            ("Notification Sequences", self.test_notification_sequences),
            ("Volume Control", self.test_volume_control),
            ("Enable/Disable", self.test_enable_disable),
            ("Global System", self.test_global_system),
        ]
        
        results = {}
        for test_name, test_method in test_methods:
            try:
                result = test_method()
                results[test_name] = result
                self.results[test_name] = result
            except Exception as e:
                self.logger.error(f"Test '{test_name}' failed with exception: {e}")
                results[test_name] = False
                self.results[test_name] = False
        
        return results
    
    def print_summary(self, results: Dict[str, bool]) -> None:
        """Print test summary."""
        self.print_section("Test Summary")
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        print(f"Tests Passed: {passed}/{total}")
        print(f"Success Rate: {passed/total:.1%}")
        
        print("\nDetailed Results:")
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {status} - {test_name}")
        
        if passed == total:
            print("\n🎉 All tests passed! Notification system is working correctly.")
        else:
            print(f"\n⚠️  {total - passed} test(s) failed. Check the output above for details.")


def main() -> None:
    """Main test function."""
    print("🎵 Audio Notification System Test Suite")
    print("This will test various notification sounds and features.")
    print("You should hear different sounds during this test.")
    print("\nPress Enter to start the tests, or Ctrl+C to cancel...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\n❌ Tests cancelled by user")
        return
    
    # Create tester and run tests
    tester = NotificationTester()
    results = tester.run_comprehensive_test()
    
    # Demonstrate usage examples
    print("\n" + "="*60)
    print("Would you like to see usage examples? (y/N): ", end="")
    
    try:
        response = input().strip().lower()
        if response in ['y', 'yes']:
            tester.demonstrate_usage_examples()
    except KeyboardInterrupt:
        print("\n❌ Demonstration cancelled")
    
    # Print summary
    tester.print_summary(results)
    
    # Exit with appropriate code
    if all(results.values()):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()