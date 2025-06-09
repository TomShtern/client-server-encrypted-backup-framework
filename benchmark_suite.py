#!/usr/bin/env python3
"""
Comprehensive Benchmark Suite for Client-Server Encrypted Backup Framework
Step 7: Pre-Optimization Performance Analysis

This suite benchmarks all aspects of the system before optimization to establish
baseline performance metrics for comparison after improvements.
"""

import os
import sys
import time
import subprocess
import threading
import socket
import psutil
import json
import statistics
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

class BenchmarkSuite:
    def __init__(self):
        """
        Initializes the benchmark suite, setting up result storage, project paths, and test files.
        
        Creates test files of varying sizes for benchmarking and prints initialization details to the console.
        """
        self.results = {}
        self.start_time = datetime.now()
        self.project_root = Path.cwd()
        self.client_exe = self.project_root / "client" / "EncryptedBackupClient.exe"
        self.server_script = self.project_root / "server" / "server.py"
        self.build_script = self.project_root / "build.bat"
        
        # Test files for benchmarking
        self.test_files = {
            "small": self.create_test_file("small_test.txt", 1024),  # 1KB
            "medium": self.create_test_file("medium_test.txt", 1024 * 100),  # 100KB
            "large": self.create_test_file("large_test.txt", 1024 * 1024),  # 1MB
        }
        
        print("*** ENCRYPTED BACKUP FRAMEWORK - COMPREHENSIVE BENCHMARK SUITE ***")
        print("=" * 70)
        print(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Project Root: {self.project_root}")
        print("=" * 70)

    def create_test_file(self, filename, size_bytes):
        """
        Creates a file with the specified name and size filled with repeated "A" characters.
        
        Args:
            filename: Name of the file to create.
            size_bytes: Size of the file in bytes.
        
        Returns:
            The path to the created test file.
        """
        filepath = self.project_root / filename
        content = "A" * size_bytes
        with open(filepath, 'w') as f:
            f.write(content)
        return filepath

    def log_benchmark(self, category, test_name, result, unit="ms", details=""):
        """
        Logs a benchmark result under the specified category and test name.
        
        Records the result value, unit, details, and timestamp in a structured format within the results dictionary. Prints a status message indicating success or failure based on the result value.
        """
        if category not in self.results:
            self.results[category] = {}
        
        self.results[category][test_name] = {
            "value": result,
            "unit": unit,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        
        status = "[OK]" if result > 0 else "[FAIL]"
        print(f"{status} {category:20} | {test_name:25} | {result:8.2f} {unit:5} | {details}")

    def benchmark_build_performance(self):
        """
        Measures and logs the performance of clean and incremental builds using project build scripts.
        
        Performs a clean build by running the clean script followed by the build script, timing the process. Then measures the time for an incremental build with no changes. Results are logged with success status and timing information.
        """
        print("\n*** BUILD PERFORMANCE BENCHMARKS ***")
        print("-" * 50)
        
        # Clean build benchmark
        if self.build_script.exists():
            # Clean first
            subprocess.run([str(self.project_root / "clean.bat")], 
                         capture_output=True, shell=True, cwd=self.project_root)
            
            # Time full build
            start_time = time.time()
            result = subprocess.run([str(self.build_script)], 
                                  capture_output=True, shell=True, cwd=self.project_root)
            build_time = (time.time() - start_time) * 1000
            
            success = result.returncode == 0
            self.log_benchmark("Build", "Full_Clean_Build", build_time if success else -1, 
                             "ms", f"Success: {success}")
            
            # Incremental build (no changes)
            start_time = time.time()
            result = subprocess.run([str(self.build_script)], 
                                  capture_output=True, shell=True, cwd=self.project_root)
            incremental_time = (time.time() - start_time) * 1000
            
            self.log_benchmark("Build", "Incremental_Build", incremental_time if success else -1, 
                             "ms", "No changes")

    def benchmark_startup_performance(self):
        """
        Measures the server application's startup time by launching it multiple times and recording the duration until its TCP port is ready.
        
        For each of three attempts, starts the server process, waits up to 10 seconds for port 1256 to become available, logs the measured startup time if successful, or logs a failure if the timeout is reached. Terminates the server process after each attempt.
        """
        print("\n*** STARTUP PERFORMANCE BENCHMARKS ***")
        print("-" * 50)
        
        # Server startup benchmark
        if self.server_script.exists():
            for attempt in range(3):  # Average of 3 attempts
                start_time = time.time()
                
                # Start server process
                server_process = subprocess.Popen([
                    sys.executable, str(self.server_script)
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=self.server_script.parent)
                
                # Wait for server to be ready (check port 1256)
                server_ready = False
                timeout = 10  # 10 second timeout
                check_start = time.time()
                
                while time.time() - check_start < timeout:
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(0.1)
                        result = sock.connect_ex(('127.0.0.1', 1256))
                        sock.close()
                        if result == 0:
                            server_ready = True
                            break
                    except:
                        pass
                    time.sleep(0.1)
                
                startup_time = (time.time() - start_time) * 1000
                
                # Clean shutdown
                server_process.terminate()
                server_process.wait(timeout=5)
                
                if server_ready:
                    self.log_benchmark("Startup", f"Server_Startup_Attempt_{attempt+1}", 
                                     startup_time, "ms", "Port 1256 ready")
                else:
                    self.log_benchmark("Startup", f"Server_Startup_Attempt_{attempt+1}", 
                                     -1, "ms", "Timeout")
                
                time.sleep(1)  # Brief pause between attempts

    def benchmark_memory_usage(self):
        """
        Measures the server's memory and CPU usage after startup.
        
        Launches the server script, waits for stabilization, then records resident set size (RSS), virtual memory size (VMS) in megabytes, and CPU usage percentage over a 1-second interval. Logs results or failure if the process is not found. Terminates the server process after measurement.
        """
        print("\n*** MEMORY USAGE BENCHMARKS ***")
        print("-" * 50)
        
        # Server memory usage
        if self.server_script.exists():
            server_process = subprocess.Popen([
                sys.executable, str(self.server_script)
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=self.server_script.parent)
            
            time.sleep(2)  # Let server stabilize
            
            try:
                process = psutil.Process(server_process.pid)
                memory_info = process.memory_info()
                
                self.log_benchmark("Memory", "Server_RSS_Memory", 
                                 memory_info.rss / 1024 / 1024, "MB", "Resident Set Size")
                self.log_benchmark("Memory", "Server_VMS_Memory", 
                                 memory_info.vms / 1024 / 1024, "MB", "Virtual Memory Size")
                
                # CPU usage sample
                cpu_percent = process.cpu_percent(interval=1.0)
                self.log_benchmark("Memory", "Server_CPU_Usage", 
                                 cpu_percent, "%", "1-second sample")
                
            except psutil.NoSuchProcess:
                self.log_benchmark("Memory", "Server_Memory", -1, "MB", "Process not found")
            finally:
                server_process.terminate()
                server_process.wait(timeout=5)

    def benchmark_crypto_performance(self):
        """
        Benchmarks the execution time of RSA cryptographic test executables.
        
        Runs each available RSA test executable multiple times, measures execution durations, and logs the average and standard deviation of successful runs.
        """
        print("\n*** CRYPTO PERFORMANCE BENCHMARKS ***")
        print("-" * 50)
        
        # Test RSA test executables if they exist
        rsa_tests = [
            self.project_root / "tests" / "test_rsa_final.exe",
            self.project_root / "tests" / "test_rsa_wrapper_final.exe"
        ]
        
        for test_exe in rsa_tests:
            if test_exe.exists():
                test_name = test_exe.stem
                
                # Run multiple times for average
                times = []
                for i in range(5):
                    start_time = time.time()
                    result = subprocess.run([str(test_exe)], 
                                          capture_output=True, cwd=test_exe.parent)
                    execution_time = (time.time() - start_time) * 1000
                    
                    if result.returncode == 0:
                        times.append(execution_time)
                
                if times:
                    avg_time = statistics.mean(times)
                    std_dev = statistics.stdev(times) if len(times) > 1 else 0
                    self.log_benchmark("Crypto", f"{test_name}_Average", avg_time, "ms", 
                                     f"±{std_dev:.2f}ms (n={len(times)})")

    def benchmark_file_operations(self):
        """
        Benchmarks file read and write performance for test files of various sizes.
        
        Measures the time taken to read and write each prepared test file, logging the duration and byte count for both operations. Temporary files created during write benchmarks are deleted after use.
        """
        print("\n*** FILE I/O BENCHMARKS ***")
        print("-" * 50)
        
        for size_name, filepath in self.test_files.items():
            # File read benchmark
            start_time = time.time()
            with open(filepath, 'r') as f:
                content = f.read()
            read_time = (time.time() - start_time) * 1000
            
            self.log_benchmark("FileIO", f"Read_{size_name}", read_time, "ms", 
                             f"{len(content)} bytes")
            
            # File write benchmark
            temp_file = filepath.with_suffix('.tmp')
            start_time = time.time()
            with open(temp_file, 'w') as f:
                f.write(content)
            write_time = (time.time() - start_time) * 1000
            
            self.log_benchmark("FileIO", f"Write_{size_name}", write_time, "ms", 
                             f"{len(content)} bytes")
            
            # Cleanup
            if temp_file.exists():
                temp_file.unlink()

    def benchmark_network_performance(self):
        """
        Measures the time required to establish TCP connections to localhost on port 1256.
        
        Attempts three TCP connections, recording the connection time in milliseconds for each attempt. Logs success or failure for each connection attempt.
        """
        print("\n*** NETWORK PERFORMANCE BENCHMARKS ***")
        print("-" * 50)
        
        # Basic TCP connection benchmark
        for attempt in range(3):
            start_time = time.time()
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                sock.connect(('127.0.0.1', 1256))
                connect_time = (time.time() - start_time) * 1000
                sock.close()
                
                self.log_benchmark("Network", f"TCP_Connect_Attempt_{attempt+1}", 
                                 connect_time, "ms", "localhost:1256")
            except Exception as e:
                self.log_benchmark("Network", f"TCP_Connect_Attempt_{attempt+1}", 
                                 -1, "ms", f"Failed: {str(e)[:30]}")

    def run_all_benchmarks(self):
        """
        Runs all benchmark tests in sequence, handling exceptions and ensuring cleanup.
        
        Executes the full suite of benchmarks for build performance, startup latency, memory usage, cryptographic operations, file I/O, and network connectivity. Any exceptions encountered during benchmarking are caught and reported, and all temporary test files are cleaned up afterward.
        """
        try:
            self.benchmark_build_performance()
            self.benchmark_startup_performance()
            self.benchmark_memory_usage()
            self.benchmark_crypto_performance()
            self.benchmark_file_operations()
            self.benchmark_network_performance()
            
        except Exception as e:
            print(f"[ERROR] Benchmark error: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        """
        Deletes all test files created for benchmarking to clean up resources.
        """
        for filepath in self.test_files.values():
            if filepath.exists():
                filepath.unlink()

    def save_results(self):
        """
        Saves all benchmark results and system metadata to a timestamped JSON file in the project root.
        
        Returns:
            Path to the saved JSON results file.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = self.project_root / f"benchmark_results_{timestamp}.json"

        summary = {
            "metadata": {
                "timestamp": self.start_time.isoformat(),
                "duration_seconds": (datetime.now() - self.start_time).total_seconds(),
                "system_info": {
                    "platform": sys.platform,
                    "python_version": sys.version,
                    "cpu_count": psutil.cpu_count(),
                    "memory_total_gb": psutil.virtual_memory().total / 1024**3
                }
            },
            "results": self.results
        }

        with open(results_file, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"\nResults saved to: {results_file}")
        return results_file

if __name__ == "__main__":
    suite = BenchmarkSuite()
    suite.run_all_benchmarks()
    results_file = suite.save_results()
    
    print("\n" + "=" * 70)
    print("*** BENCHMARK SUITE COMPLETED ***")
    print("=" * 70)
