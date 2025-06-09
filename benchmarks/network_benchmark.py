#!/usr/bin/env python3
"""
Network Performance Benchmark Suite
Step 7: Detailed Network Protocol Analysis

This benchmark focuses on network-specific performance including:
- TCP connection establishment
- Protocol message throughput
- Latency measurements
- Concurrent connection handling
- Data transfer rates
"""

import socket
import time
import threading
import statistics
import struct
import sys
from datetime import datetime
import json

class NetworkBenchmark:
    def __init__(self, server_host='127.0.0.1', server_port=1256):
        self.server_host = server_host
        self.server_port = server_port
        self.results = {}
        
        print("*** NETWORK PERFORMANCE BENCHMARK SUITE ***")
        print("=" * 60)
        print(f"Target: {server_host}:{server_port}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

    def log_result(self, category, test_name, value, unit="ms", details=""):
        """Log benchmark results"""
        if category not in self.results:
            self.results[category] = {}
        
        self.results[category][test_name] = {
            "value": value,
            "unit": unit,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        
        status = "[OK]" if value >= 0 else "[FAIL]"
        print(f"{status} {category:15} | {test_name:25} | {value:8.3f} {unit:5} | {details}")

    def check_server_availability(self):
        """Check if server is running and accessible"""
        print("\n*** SERVER AVAILABILITY CHECK ***")
        print("-" * 40)
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            start_time = time.time()
            result = sock.connect_ex((self.server_host, self.server_port))
            connect_time = (time.time() - start_time) * 1000
            sock.close()
            
            if result == 0:
                self.log_result("Availability", "Server_Reachable", connect_time, "ms", "Success")
                return True
            else:
                self.log_result("Availability", "Server_Reachable", -1, "ms", f"Failed: {result}")
                return False
                
        except Exception as e:
            self.log_result("Availability", "Server_Reachable", -1, "ms", f"Error: {str(e)[:30]}")
            return False

    def benchmark_connection_performance(self):
        """Benchmark TCP connection establishment"""
        print("\n*** CONNECTION PERFORMANCE ***")
        print("-" * 40)
        
        connection_times = []
        successful_connections = 0
        
        for i in range(10):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                
                start_time = time.time()
                result = sock.connect_ex((self.server_host, self.server_port))
                connect_time = (time.time() - start_time) * 1000
                
                if result == 0:
                    connection_times.append(connect_time)
                    successful_connections += 1
                
                sock.close()
                time.sleep(0.1)  # Brief pause between connections
                
            except Exception as e:
                print(f"Connection {i+1} failed: {e}")
        
        if connection_times:
            avg_time = statistics.mean(connection_times)
            min_time = min(connection_times)
            max_time = max(connection_times)
            std_dev = statistics.stdev(connection_times) if len(connection_times) > 1 else 0
            
            self.log_result("Connection", "Average_Connect_Time", avg_time, "ms", 
                          f"±{std_dev:.2f}ms")
            self.log_result("Connection", "Min_Connect_Time", min_time, "ms", "Best case")
            self.log_result("Connection", "Max_Connect_Time", max_time, "ms", "Worst case")
            self.log_result("Connection", "Success_Rate", 
                          (successful_connections / 10) * 100, "%", 
                          f"{successful_connections}/10")

    def benchmark_protocol_messages(self):
        """Benchmark protocol message creation and parsing"""
        print("\n*** PROTOCOL MESSAGE PERFORMANCE ***")
        print("-" * 40)
        
        # Test protocol header creation (Version 3 format)
        client_id = b'\xAB' * 16  # Mock client ID
        
        # Registration message (Code 1025)
        start_time = time.time()
        for _ in range(1000):
            header = struct.pack('<16sBHI', client_id, 3, 1025, 255)
        reg_time = (time.time() - start_time) * 1000
        self.log_result("Protocol", "Registration_Header_1000x", reg_time, "ms", "Code 1025")
        
        # Public key message (Code 1026)
        start_time = time.time()
        for _ in range(1000):
            header = struct.pack('<16sBHI', client_id, 3, 1026, 335)
        pubkey_time = (time.time() - start_time) * 1000
        self.log_result("Protocol", "PublicKey_Header_1000x", pubkey_time, "ms", "Code 1026")
        
        # File transfer message (Code 1028)
        start_time = time.time()
        for _ in range(1000):
            header = struct.pack('<16sBHI', client_id, 3, 1028, 1024)
        file_time = (time.time() - start_time) * 1000
        self.log_result("Protocol", "FileTransfer_Header_1000x", file_time, "ms", "Code 1028")
        
        # Header parsing benchmark
        test_header = struct.pack('<16sBHI', client_id, 3, 1025, 255)
        start_time = time.time()
        for _ in range(10000):
            parsed_id, version, code, size = struct.unpack('<16sBHI', test_header)
        parse_time = (time.time() - start_time) * 1000
        self.log_result("Protocol", "Header_Parsing_10000x", parse_time, "ms", "23-byte headers")

    def benchmark_data_transfer(self):
        """Benchmark data transfer rates"""
        print("\n*** DATA TRANSFER PERFORMANCE ***")
        print("-" * 40)
        
        # Test different payload sizes
        test_sizes = [
            ("Small", 1024),      # 1KB
            ("Medium", 10240),    # 10KB
            ("Large", 102400),    # 100KB
        ]
        
        for size_name, size in test_sizes:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10.0)
                sock.connect((self.server_host, self.server_port))
                
                # Create test data
                test_data = b'X' * size
                
                # Send data and measure time
                start_time = time.time()
                sock.sendall(test_data)
                send_time = (time.time() - start_time) * 1000
                
                # Calculate throughput
                throughput_mbps = (size * 8) / (send_time / 1000) / 1_000_000
                
                self.log_result("Transfer", f"Send_{size_name}", send_time, "ms", 
                              f"{size} bytes")
                self.log_result("Transfer", f"Throughput_{size_name}", throughput_mbps, "Mbps", 
                              f"{size} bytes")
                
                sock.close()
                time.sleep(0.5)  # Brief pause between tests
                
            except Exception as e:
                self.log_result("Transfer", f"Send_{size_name}", -1, "ms", 
                              f"Failed: {str(e)[:30]}")

    def benchmark_concurrent_connections(self):
        """Benchmark concurrent connection handling"""
        print("\n*** CONCURRENT CONNECTION PERFORMANCE ***")
        print("-" * 40)
        
        def connect_worker(worker_id, results_list):
            """Worker function for concurrent connections"""
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10.0)
                
                start_time = time.time()
                sock.connect((self.server_host, self.server_port))
                connect_time = (time.time() - start_time) * 1000
                
                # Hold connection briefly
                time.sleep(0.5)
                sock.close()
                
                results_list.append(connect_time)
                
            except Exception as e:
                results_list.append(-1)
        
        # Test with different numbers of concurrent connections
        for num_connections in [5, 10, 20]:
            threads = []
            connection_results = []
            
            start_time = time.time()
            
            # Start all connection threads
            for i in range(num_connections):
                thread = threading.Thread(target=connect_worker, 
                                        args=(i, connection_results))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            total_time = (time.time() - start_time) * 1000
            
            # Analyze results
            successful = [t for t in connection_results if t >= 0]
            success_rate = len(successful) / num_connections * 100
            
            self.log_result("Concurrent", f"Connections_{num_connections}", total_time, "ms", 
                          f"Total time for {num_connections}")
            self.log_result("Concurrent", f"Success_Rate_{num_connections}", success_rate, "%", 
                          f"{len(successful)}/{num_connections}")
            
            if successful:
                avg_connect = statistics.mean(successful)
                self.log_result("Concurrent", f"Avg_Connect_{num_connections}", avg_connect, "ms", 
                              f"Average per connection")

    def benchmark_latency(self):
        """Benchmark network latency"""
        print("\n*** LATENCY PERFORMANCE ***")
        print("-" * 40)
        
        latencies = []
        
        for i in range(20):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                
                # Measure round-trip time
                start_time = time.time()
                sock.connect((self.server_host, self.server_port))
                
                # Send minimal data and close immediately
                sock.send(b'PING')
                latency = (time.time() - start_time) * 1000
                latencies.append(latency)
                
                sock.close()
                time.sleep(0.1)
                
            except Exception:
                pass
        
        if latencies:
            avg_latency = statistics.mean(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            std_dev = statistics.stdev(latencies) if len(latencies) > 1 else 0
            
            self.log_result("Latency", "Average_RTT", avg_latency, "ms", f"±{std_dev:.2f}ms")
            self.log_result("Latency", "Min_RTT", min_latency, "ms", "Best case")
            self.log_result("Latency", "Max_RTT", max_latency, "ms", "Worst case")
            self.log_result("Latency", "Jitter", std_dev, "ms", "Standard deviation")

    def run_all_benchmarks(self):
        """Execute complete network benchmark suite"""
        if not self.check_server_availability():
            print("\n[FAIL] Server not available - skipping network benchmarks")
            print("TIP: Start the server with: python server/server.py")
            return False
        
        try:
            self.benchmark_connection_performance()
            self.benchmark_protocol_messages()
            self.benchmark_data_transfer()
            self.benchmark_concurrent_connections()
            self.benchmark_latency()
            return True
            
        except Exception as e:
            print(f"[ERROR] Network benchmark error: {e}")
            return False

    def save_results(self):
        """Save benchmark results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"network_benchmark_results_{timestamp}.json"

        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        print(f"\nNetwork results saved to: {results_file}")
        return results_file

if __name__ == "__main__":
    benchmark = NetworkBenchmark()
    
    if benchmark.run_all_benchmarks():
        benchmark.save_results()
        print("\n[OK] Network benchmark completed successfully!")
    else:
        print("\n[FAIL] Network benchmark failed!")
        sys.exit(1)
