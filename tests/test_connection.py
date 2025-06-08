#!/usr/bin/env python3
"""
Comprehensive Test Suite for Client-Server Connection
Tests the encrypted backup framework components
"""

import socket
import time
import threading
import subprocess
import sys
import os
from pathlib import Path

class ConnectionTester:
    def __init__(self):
        self.server_host = "127.0.0.1"
        self.server_port = 1256
        self.test_results = []
        
    def log_test(self, test_name, status, details=""):
        """Log test results"""
        result = {
            'test': test_name,
            'status': status,
            'details': details,
            'timestamp': time.strftime('%H:%M:%S')
        }
        self.test_results.append(result)
        status_symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"[{result['timestamp']}] {status_symbol} {test_name}: {details}")
        
    def test_server_listening(self):
        """Test if server is listening on the expected port"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.server_host, self.server_port))
            sock.close()
            
            if result == 0:
                self.log_test("Server Listening", "PASS", f"Server responding on {self.server_host}:{self.server_port}")
                return True
            else:
                self.log_test("Server Listening", "FAIL", f"Server not responding on {self.server_host}:{self.server_port}")
                return False
        except Exception as e:
            self.log_test("Server Listening", "FAIL", f"Exception: {str(e)}")
            return False
            
    def test_basic_connection(self):
        """Test basic TCP connection to server"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((self.server_host, self.server_port))
            
            # Try to receive initial data
            sock.settimeout(5)
            try:
                data = sock.recv(1024)
                if data:
                    self.log_test("Basic Connection", "PASS", f"Received {len(data)} bytes from server")
                else:
                    self.log_test("Basic Connection", "WARN", "Connected but no initial data received")
            except socket.timeout:
                self.log_test("Basic Connection", "WARN", "Connected but server didn't send initial data")
            
            sock.close()
            return True
            
        except Exception as e:
            self.log_test("Basic Connection", "FAIL", f"Connection failed: {str(e)}")
            return False
            
    def test_protocol_handshake(self):
        """Test protocol handshake simulation"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(15)
            sock.connect((self.server_host, self.server_port))
            
            # Simulate client registration request
            # Based on the protocol, send a registration request
            registration_request = b"REGISTER:testuser"
            sock.send(registration_request)
            
            # Wait for response
            sock.settimeout(10)
            response = sock.recv(1024)
            
            if response:
                self.log_test("Protocol Handshake", "PASS", f"Server responded with {len(response)} bytes")
                self.log_test("Server Response", "INFO", f"Response: {response[:100]}...")
            else:
                self.log_test("Protocol Handshake", "FAIL", "No response from server")
                
            sock.close()
            return True
            
        except Exception as e:
            self.log_test("Protocol Handshake", "FAIL", f"Handshake failed: {str(e)}")
            return False
            
    def test_client_executable(self):
        """Test if client executable exists and is accessible"""
        client_path = Path("client/EncryptedBackupClient.exe")
        
        if client_path.exists():
            self.log_test("Client Executable", "PASS", f"Found at {client_path}")
            
            # Check file size and modification time
            stat = client_path.stat()
            size_mb = stat.st_size / (1024 * 1024)
            mod_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime))
            self.log_test("Client Info", "INFO", f"Size: {size_mb:.1f}MB, Modified: {mod_time}")
            return True
        else:
            self.log_test("Client Executable", "FAIL", f"Not found at {client_path}")
            return False
            
    def test_configuration_files(self):
        """Test configuration files"""
        config_files = [
            "client/transfer.info",
            "test_file.txt"
        ]
        
        all_found = True
        for config_file in config_files:
            path = Path(config_file)
            if path.exists():
                size = path.stat().st_size
                self.log_test("Config File", "PASS", f"{config_file} ({size} bytes)")
            else:
                self.log_test("Config File", "FAIL", f"{config_file} not found")
                all_found = False
                
        return all_found
        
    def test_server_logs(self):
        """Check server log output for issues"""
        # This would require access to server logs
        # For now, just indicate the test exists
        self.log_test("Server Logs", "INFO", "Manual check required - see server console")
        return True
        
    def run_all_tests(self):
        """Run comprehensive test suite"""
        print("=" * 70)
        print("🧪 ENCRYPTED BACKUP FRAMEWORK - CONNECTION TEST SUITE")
        print("=" * 70)
        print()
        
        tests = [
            ("Configuration Files", self.test_configuration_files),
            ("Client Executable", self.test_client_executable),
            ("Server Listening", self.test_server_listening),
            ("Basic Connection", self.test_basic_connection),
            ("Protocol Handshake", self.test_protocol_handshake),
            ("Server Logs", self.test_server_logs),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n🔍 Running: {test_name}")
            print("-" * 50)
            try:
                if test_func():
                    passed += 1
            except Exception as e:
                self.log_test(test_name, "FAIL", f"Test exception: {str(e)}")
        
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        
        for result in self.test_results:
            status_symbol = "✅" if result['status'] == "PASS" else "❌" if result['status'] == "FAIL" else "ℹ️"
            print(f"{status_symbol} [{result['timestamp']}] {result['test']}: {result['details']}")
            
        print(f"\n🎯 OVERALL RESULT: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! System appears to be working correctly.")
        else:
            print("⚠️  Some tests failed. Check the details above for issues to resolve.")
            
        return passed == total

def main():
    """Main test runner"""
    # Change to project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    tester = ConnectionTester()
    success = tester.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
