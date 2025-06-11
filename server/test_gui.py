#!/usr/bin/env python3
"""
Test script for ServerGUI functionality
Tests the GUI integration without running the full server
"""

import time
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ServerGUI import (
    initialize_server_gui, shutdown_server_gui, update_server_status,
    update_client_stats, update_transfer_stats, update_maintenance_stats,
    show_server_error, show_server_success, show_server_notification
)

def test_gui_functionality():
    """Test all GUI functionality"""
    print("Testing Server GUI functionality...")
    
    # Test 1: Initialize GUI
    print("1. Testing GUI initialization...")
    if not initialize_server_gui():
        print("❌ GUI initialization failed!")
        return False
    print("✅ GUI initialized successfully")
    
    # Wait for GUI to fully load
    time.sleep(2)
    
    # Test 2: Server status updates
    print("2. Testing server status updates...")
    update_server_status(True, "127.0.0.1", 8080)
    time.sleep(1)
    print("✅ Server status updated")
    
    # Test 3: Client statistics
    print("3. Testing client statistics updates...")
    update_client_stats(connected=3, total=10, active_transfers=2)
    time.sleep(1)
    print("✅ Client stats updated")
    
    # Test 4: Transfer statistics
    print("4. Testing transfer statistics...")
    update_transfer_stats(bytes_transferred=1024*1024*100, last_activity="2025-06-04 21:25:00")
    time.sleep(1)
    print("✅ Transfer stats updated")
    
    # Test 5: Maintenance statistics
    print("5. Testing maintenance statistics...")
    maintenance_stats = {
        'files_cleaned': 5,
        'partial_files_cleaned': 3,
        'clients_cleaned': 1,
        'last_cleanup': '2025-06-04 21:20:00'
    }
    update_maintenance_stats(maintenance_stats)
    time.sleep(1)
    print("✅ Maintenance stats updated")
    
    # Test 6: Error messages
    print("6. Testing error messages...")
    show_server_error("Test error message")
    time.sleep(2)
    print("✅ Error message displayed")
    
    # Test 7: Success messages
    print("7. Testing success messages...")
    show_server_success("Test success message")
    time.sleep(2)
    print("✅ Success message displayed")
    
    # Test 8: Notifications
    print("8. Testing notifications...")
    show_server_notification("Test Notification", "This is a test notification message")
    time.sleep(2)
    print("✅ Notification displayed")
    
    # Test 9: Multiple rapid updates
    print("9. Testing rapid updates...")
    for i in range(5):
        update_client_stats(connected=i+1)
        update_transfer_stats(bytes_transferred=(i+1)*1024*1024)
        time.sleep(0.5)
    print("✅ Rapid updates handled")
    
    # Test 10: Server stop status
    print("10. Testing server stop status...")
    update_server_status(False)
    time.sleep(1)
    print("✅ Server stop status updated")
    
    print("\n🎉 All GUI tests completed successfully!")
    print("The GUI window should be visible with all the test data.")
    print("You can interact with the GUI window to test system tray and other features.")
    print("Press Ctrl+C to exit...")
    
    return True

def main():
    """Main test function"""
    try:
        if test_gui_functionality():
            # Keep the GUI running for manual testing
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nShutting down GUI test...")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("Cleaning up...")
        shutdown_server_gui()
        print("Test completed.")

if __name__ == "__main__":
    main()
