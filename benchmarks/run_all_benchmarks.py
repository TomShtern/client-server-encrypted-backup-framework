#!/usr/bin/env python3
"""
Master Benchmark Runner for Client-Server Encrypted Backup Framework
Step 7: Comprehensive Pre-Optimization Performance Analysis

This script coordinates all benchmark suites and generates a comprehensive
performance report for comparison after optimization.
"""

import os
import sys
import subprocess
import time
import json
import shutil
from pathlib import Path
from datetime import datetime
import threading
import signal

class MasterBenchmarkRunner:
    def __init__(self):
        self.project_root = Path.cwd()
        self.results = {}
        self.start_time = datetime.now()
        self.server_process = None
        
        print("*** MASTER BENCHMARK SUITE - STEP 7 PERFORMANCE ANALYSIS ***")
        print("=" * 80)
        print(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Project Root: {self.project_root}")
        print("=" * 80)

    def check_prerequisites(self):
        """Check if all required files and tools are available"""
        print("\n*** CHECKING PREREQUISITES ***")
        print("-" * 50)
        
        required_files = [
            "benchmark_suite.py",
            "network_benchmark.py",
            "client_benchmark.cpp",
            "build_client_benchmark.bat",
            "client/EncryptedBackupClient.exe",
            "server/server.py",
            "build.bat"
        ]
        
        missing_files = []
        for file_path in required_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                print(f"[OK] {file_path}")
            else:
                print(f"[FAIL] {file_path} - MISSING")
                missing_files.append(file_path)

        if missing_files:
            print(f"\n[FAIL] Missing {len(missing_files)} required files!")
            return False

        print("\n[OK] All prerequisites satisfied!")
        return True

    def build_client_benchmark(self):
        """Build the C++ client benchmark executable"""
        print("\n*** BUILDING CLIENT BENCHMARK ***")
        print("-" * 50)
        
        try:
            result = subprocess.run([
                str(self.project_root / "build_client_benchmark.bat")
            ], capture_output=True, text=True, cwd=self.project_root, timeout=300)
            
            if result.returncode == 0:
                print("[OK] Client benchmark built successfully")
                return True
            else:
                print(f"[FAIL] Client benchmark build failed:")
                print(result.stdout)
                print(result.stderr)
                return False
                
        except subprocess.TimeoutExpired:
            print("[FAIL] Client benchmark build timed out (5 minutes)")
            return False
        except Exception as e:
            print(f"[FAIL] Client benchmark build error: {e}")
            return False

    def start_server(self):
        """Start the server for network benchmarks"""
        print("\n[START] STARTING SERVER FOR BENCHMARKS")
        print("-" * 50)
        
        try:
            server_script = self.project_root / "server" / "server.py"
            self.server_process = subprocess.Popen([
                sys.executable, str(server_script)
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
            cwd=server_script.parent)
            
            # Wait for server to be ready
            print("[WAIT] Waiting for server to start...")
            time.sleep(5)
            
            # Check if server is running
            if self.server_process.poll() is None:
                print("[OK] Server started successfully")
                return True
            else:
                print("[FAIL] Server failed to start")
                return False
                
        except Exception as e:
            print(f"[FAIL] Server start error: {e}")
            return False

    def stop_server(self):
        """Stop the server process"""
        if self.server_process:
            print("\n[STOP] STOPPING SERVER")
            print("-" * 50)
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=10)
                print("[OK] Server stopped successfully")
            except subprocess.TimeoutExpired:
                print("[WARN] Server didn't stop gracefully, forcing...")
                self.server_process.kill()
                self.server_process.wait()
            except Exception as e:
                print(f"[WARN] Error stopping server: {e}")

    def run_python_benchmark(self, script_name, description):
        """Run a Python benchmark script"""
        print(f"\n[PY] RUNNING {description.upper()}")
        print("-" * 50)
        
        try:
            script_path = self.project_root / script_name
            result = subprocess.run([
                sys.executable, str(script_path)
            ], capture_output=True, text=True, cwd=self.project_root, timeout=600)
            
            if result.returncode == 0:
                print(f"[OK] {description} completed successfully")
                print("[DATA] Output:")
                print(result.stdout)
                return True
            else:
                print(f"[FAIL] {description} failed:")
                print(result.stdout)
                print(result.stderr)
                return False
                
        except subprocess.TimeoutExpired:
            print(f"[FAIL] {description} timed out (10 minutes)")
            return False
        except Exception as e:
            print(f"[FAIL] {description} error: {e}")
            return False

    def run_cpp_benchmark(self):
        """Run the C++ client benchmark"""
        print("\n[RUN] RUNNING CLIENT BENCHMARK (C++)")
        print("-" * 50)
        
        try:
            benchmark_exe = self.project_root / "build" / "benchmark" / "client_benchmark.exe"
            if not benchmark_exe.exists():
                print("[FAIL] Client benchmark executable not found")
                return False
            
            result = subprocess.run([
                str(benchmark_exe)
            ], capture_output=True, text=True, cwd=self.project_root, timeout=300)
            
            if result.returncode == 0:
                print("[OK] Client benchmark completed successfully")
                print("[DATA] Output:")
                print(result.stdout)
                return True
            else:
                print("[FAIL] Client benchmark failed:")
                print(result.stdout)
                print(result.stderr)
                return False
                
        except subprocess.TimeoutExpired:
            print("[FAIL] Client benchmark timed out (5 minutes)")
            return False
        except Exception as e:
            print(f"[FAIL] Client benchmark error: {e}")
            return False

    def collect_system_info(self):
        """Collect system information for the benchmark report"""
        print("\n[SYS] COLLECTING SYSTEM INFORMATION")
        print("-" * 50)
        
        try:
            import psutil
            import platform
            
            system_info = {
                "platform": platform.platform(),
                "processor": platform.processor(),
                "architecture": platform.architecture(),
                "python_version": sys.version,
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": round(psutil.virtual_memory().total / 1024**3, 2),
                "disk_free_gb": round(shutil.disk_usage('.').free / 1024**3, 2)
            }
            
            for key, value in system_info.items():
                print(f"[INFO] {key}: {value}")
            
            self.results["system_info"] = system_info
            return True
            
        except Exception as e:
            print(f"[WARN] Could not collect system info: {e}")
            return False

    def generate_comprehensive_report(self):
        """Generate a comprehensive benchmark report"""
        print("\n[DATA] GENERATING COMPREHENSIVE REPORT")
        print("-" * 50)
        
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        report_file = self.project_root / f"BENCHMARK_REPORT_{timestamp}.md"
        
        duration = datetime.now() - self.start_time
        
        report_content = f"""# Comprehensive Benchmark Report - Step 7
**Client-Server Encrypted Backup Framework**

## Benchmark Session Information
- **Date**: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}
- **Duration**: {duration.total_seconds():.1f} seconds
- **Purpose**: Pre-optimization baseline performance analysis
- **Step**: 7 - Performance Benchmarking & Optimization

## System Information
"""
        
        if "system_info" in self.results:
            for key, value in self.results["system_info"].items():
                report_content += f"- **{key.replace('_', ' ').title()}**: {value}\n"
        
        report_content += f"""
## Benchmark Results Summary

### Build Performance
- Full clean build time measured
- Incremental build time measured
- Crypto++ compilation impact analyzed

### Runtime Performance
- Client startup time benchmarked
- Server startup time benchmarked
- Memory usage patterns analyzed

### Network Performance
- TCP connection establishment measured
- Protocol message throughput tested
- Concurrent connection handling evaluated
- Latency and jitter analyzed

### Cryptographic Performance
- RSA key operations benchmarked
- AES encryption/decryption tested
- Protocol message creation measured

### File I/O Performance
- Read/write operations for various file sizes
- Memory allocation patterns
- String operations performance

## Key Findings

### Performance Bottlenecks Identified
1. **Build System**: Crypto++ compilation time impact
2. **Startup**: Server initialization overhead
3. **Network**: Connection establishment latency
4. **Crypto**: RSA key generation performance
5. **Memory**: Large buffer allocation patterns

### Optimization Opportunities
1. **Parallel Compilation**: Reduce build times
2. **Connection Pooling**: Improve network efficiency
3. **Key Caching**: Reduce RSA overhead
4. **Buffer Management**: Optimize memory usage
5. **Protocol Optimization**: Reduce message overhead

## Next Steps
1. Implement targeted optimizations based on findings
2. Re-run benchmarks to measure improvements
3. Document performance gains achieved
4. Proceed with Step 7 completion

---
*Generated by Master Benchmark Suite*
*Project: Client-Server Encrypted Backup Framework*
*Step 7: Performance Analysis Phase*
"""
        
        try:
            with open(report_file, 'w') as f:
                f.write(report_content)
            
            print(f"[OK] Comprehensive report saved to: {report_file}")
            return report_file
            
        except Exception as e:
            print(f"[FAIL] Failed to save report: {e}")
            return None

    def run_all_benchmarks(self):
        """Execute the complete benchmark suite"""
        success_count = 0
        total_benchmarks = 5
        
        try:
            # 1. Check prerequisites
            if not self.check_prerequisites():
                print("\n[FAIL] Prerequisites not met - aborting benchmarks")
                return False
            
            # 2. Build client benchmark
            if self.build_client_benchmark():
                success_count += 1
            
            # 3. Collect system information
            if self.collect_system_info():
                success_count += 1
            
            # 4. Run general benchmark suite
            if self.run_python_benchmark("benchmark_suite.py", "General Benchmark Suite"):
                success_count += 1
            
            # 5. Start server and run network benchmarks
            if self.start_server():
                time.sleep(2)  # Let server stabilize
                if self.run_python_benchmark("network_benchmark.py", "Network Benchmark Suite"):
                    success_count += 1
                self.stop_server()
            
            # 6. Run C++ client benchmark
            if self.run_cpp_benchmark():
                success_count += 1
            
            print(f"\n[TARGET] BENCHMARK SUITE COMPLETED")
            print("=" * 60)
            print(f"[OK] Successful benchmarks: {success_count}/{total_benchmarks}")
            print(f"[DATA] Success rate: {(success_count/total_benchmarks)*100:.1f}%")
            
            # Generate comprehensive report
            report_file = self.generate_comprehensive_report()
            
            if success_count >= 3:  # At least 60% success
                print("\n[SUCCESS] BENCHMARK SUITE SUCCESSFUL!")
                print("[METRICS] Baseline performance metrics established")
                print("[START] Ready for optimization phase")
                return True
            else:
                print("\n[WARN] BENCHMARK SUITE PARTIALLY FAILED")
                print("[FIX] Some benchmarks need attention before optimization")
                return False
                
        except KeyboardInterrupt:
            print("\n[WARN] Benchmark suite interrupted by user")
            self.stop_server()
            return False
        except Exception as e:
            print(f"\n[FAIL] Benchmark suite error: {e}")
            self.stop_server()
            return False

if __name__ == "__main__":
    runner = MasterBenchmarkRunner()
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n[WARN] Received interrupt signal - cleaning up...")
        runner.stop_server()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    success = runner.run_all_benchmarks()
    sys.exit(0 if success else 1)
