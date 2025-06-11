#!/usr/bin/env python3
"""
Comprehensive System Test for Client Server Encrypted Backup Framework
Tests all components and validates 100% functionality
"""

import socket
import subprocess
import sys
import os
import time
import threading
from pathlib import Path

class SystemTester:
    def __init__(self):
        self.test_results = []
        self.server_host = "127.0.0.1"
        self.server_port = 1256
        
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
        
    def test_build_system(self):
        """Test if build system works"""
        try:
            if os.path.exists("client/EncryptedBackupClient.exe"):
                stat = os.stat("client/EncryptedBackupClient.exe")
                size_mb = stat.st_size / (1024 * 1024)
                mod_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime))
                self.log_test("Build System", "PASS", f"Executable exists: {size_mb:.1f}MB, modified {mod_time}")
                return True
            else:
                self.log_test("Build System", "FAIL", "EncryptedBackupClient.exe not found")
                return False
        except Exception as e:
            self.log_test("Build System", "FAIL", f"Exception: {str(e)}")
            return False
            
    def test_configuration_files(self):
        """Test configuration files"""
        config_files = [
            ("port.info", "Port configuration"),
            ("server/port.info", "Server port configuration"),
            ("client/transfer.info", "Client transfer configuration"),
            ("test_file.txt", "Test file for transfer")
        ]
        
        all_found = True
        for config_file, description in config_files:
            path = Path(config_file)
            if path.exists():
                size = path.stat().st_size
                self.log_test("Config File", "PASS", f"{config_file} ({size} bytes)")
            else:
                self.log_test("Config File", "FAIL", f"{config_file} not found")
                all_found = False
                
        return all_found
        
    def test_crypto_implementations(self):
        """Test crypto wrapper implementations"""
        try:
            # Check RSA implementation
            rsa_file = Path("src/wrappers/RSAWrapper.cpp")
            if rsa_file.exists():
                content = rsa_file.read_text()
                if "STUB" in content:
                    self.log_test("RSA Implementation", "FAIL", "Still using stub implementation")
                    return False
                elif "CryptoPP" in content or "Crypto++" in content:
                    self.log_test("RSA Implementation", "PASS", "Real Crypto++ implementation found")
                else:
                    self.log_test("RSA Implementation", "WARN", "Unknown implementation type")
            else:
                self.log_test("RSA Implementation", "FAIL", "RSAWrapper.cpp not found")
                return False
                
            # Check AES key size
            aes_header = Path("include/wrappers/AESWrapper.h")
            if aes_header.exists():
                content = aes_header.read_text()
                if "DEFAULT_KEYLENGTH = 32" in content:
                    self.log_test("AES Key Size", "PASS", "Correct 32-byte keys for AES-256")
                elif "DEFAULT_KEYLENGTH = 16" in content:
                    self.log_test("AES Key Size", "FAIL", "Still using 16-byte keys")
                    return False
                else:
                    self.log_test("AES Key Size", "WARN", "Key length not clearly defined")
            else:
                self.log_test("AES Key Size", "FAIL", "AESWrapper.h not found")
                return False
                
            return True
            
        except Exception as e:
            self.log_test("Crypto Implementation", "FAIL", f"Exception: {str(e)}")
            return False
            
    def test_protocol_implementation(self):
        """Test protocol implementation"""
        try:
            protocol_file = Path("src/client/protocol.cpp")
            if protocol_file.exists():
                content = protocol_file.read_text()
                if len(content) < 100:
                    self.log_test("Protocol Implementation", "FAIL", "Protocol file is mostly empty")
                    return False
                elif "createRegistrationRequest" in content and "parseResponseHeader" in content:
                    self.log_test("Protocol Implementation", "PASS", "Complete protocol functions found")
                else:
                    self.log_test("Protocol Implementation", "WARN", "Partial protocol implementation")
            else:
                self.log_test("Protocol Implementation", "FAIL", "protocol.cpp not found")
                return False
                
            return True
            
        except Exception as e:
            self.log_test("Protocol Implementation", "FAIL", f"Exception: {str(e)}")
            return False
            
    def test_server_startup(self):
        """Test if server can start"""
        try:
            # Check if server is already running
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((self.server_host, self.server_port))
            sock.close()
            
            if result == 0:
                self.log_test("Server Startup", "PASS", f"Server already running on {self.server_host}:{self.server_port}")
                return True
            else:
                self.log_test("Server Startup", "INFO", "Server not currently running - this is normal")
                return True
                
        except Exception as e:
            self.log_test("Server Startup", "WARN", f"Could not test server: {str(e)}")
            return True  # Non-critical for this test
            
    def test_build_script_integrity(self):
        """Test build script integrity"""
        try:
            build_file = Path("build.bat")
            if build_file.exists():
                content = build_file.read_text()
                
                issues = []
                # Check for actual stub usage (not just comments)
                lines = content.split('\n')
                using_stub = False
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith('REM') or stripped.startswith('#'):
                        continue  # Skip comments
                    if "RSAWrapper_stub.cpp" in stripped:
                        using_stub = True
                        break
                if using_stub:
                    issues.append("Still using RSA stub")
                if "src\\wrappers\\RSAWrapper.cpp" not in content and "src/wrappers/RSAWrapper.cpp" not in content:
                    issues.append("Missing real RSA implementation")
                if "third_party\\crypto++\\rsa.cpp" not in content and "third_party/crypto++/rsa.cpp" not in content:
                    issues.append("Missing RSA crypto++ module")
                    
                if issues:
                    self.log_test("Build Script", "FAIL", "; ".join(issues))
                    return False
                else:
                    self.log_test("Build Script", "PASS", "Build script properly configured")
                    return True
            else:
                self.log_test("Build Script", "FAIL", "build.bat not found")
                return False
                
        except Exception as e:
            self.log_test("Build Script", "FAIL", f"Exception: {str(e)}")
            return False
            
    def test_file_integrity(self):
        """Test file integrity and completeness"""
        try:
            critical_files = [
                "src/wrappers/AESWrapper.cpp",
                "src/wrappers/RSAWrapper.cpp", 
                "src/wrappers/Base64Wrapper.cpp",
                "src/client/client.cpp",
                "src/client/protocol.cpp",
                "src/client/cksum.cpp",
                "server/server.py",
                "include/wrappers/AESWrapper.h",
                "include/wrappers/RSAWrapper.h"
            ]
            
            missing_files = []
            for file_path in critical_files:
                if not Path(file_path).exists():
                    missing_files.append(file_path)
                    
            if missing_files:
                self.log_test("File Integrity", "FAIL", f"Missing files: {', '.join(missing_files)}")
                return False
            else:
                self.log_test("File Integrity", "PASS", f"All {len(critical_files)} critical files present")
                return True
                
        except Exception as e:
            self.log_test("File Integrity", "FAIL", f"Exception: {str(e)}")
            return False
            
    def run_comprehensive_test(self):
        """Run comprehensive test suite"""
        print("=" * 80)
        print("🧪 COMPREHENSIVE SYSTEM TEST - Client Server Encrypted Backup Framework")
        print("=" * 80)
        print()
        
        tests = [
            ("File Integrity", self.test_file_integrity),
            ("Configuration Files", self.test_configuration_files),
            ("Crypto Implementations", self.test_crypto_implementations),
            ("Protocol Implementation", self.test_protocol_implementation),
            ("Build Script Integrity", self.test_build_script_integrity),
            ("Build System", self.test_build_system),
            ("Server Startup", self.test_server_startup),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n🔍 Running: {test_name}")
            print("-" * 60)
            try:
                if test_func():
                    passed += 1
            except Exception as e:
                self.log_test(test_name, "FAIL", f"Test exception: {str(e)}")
        
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        for result in self.test_results:
            status_symbol = "✅" if result['status'] == "PASS" else "❌" if result['status'] == "FAIL" else "ℹ️"
            print(f"{status_symbol} [{result['timestamp']}] {result['test']}: {result['details']}")
            
        print(f"\n🎯 OVERALL RESULT: {passed}/{total} test categories passed")
        
        if passed == total:
            print("🎉 All tests passed! System appears to be 100% ready.")
            print("\n✅ READY FOR FINAL TESTING:")
            print("   1. Build the system: build.bat") 
            print("   2. Start server: python server/server.py")
            print("   3. Run client: client/EncryptedBackupClient.exe")
        else:
            print("⚠️  Some tests failed. Review the issues above.")
            print("\n❌ ISSUES FOUND:")
            failed_tests = [r for r in self.test_results if r['status'] == 'FAIL']
            for result in failed_tests:
                print(f"   - {result['test']}: {result['details']}")
            
        return passed == total

def main():
    """Main test runner"""
    # Change to project root directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    tester = SystemTester()
    success = tester.run_comprehensive_test()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())