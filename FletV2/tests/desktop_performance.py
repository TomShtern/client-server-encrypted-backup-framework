"""
Desktop Performance Testing Suite

This module provides comprehensive performance testing utilities for desktop applications,
including memory usage monitoring, CPU usage benchmarks, response time validation, and stress testing.

Compatible with Flet 0.28.3 and Windows 11 desktop applications.
"""

import time
import psutil
import threading
import logging
from typing import Dict, List, Any, Callable, Optional, Tuple
from dataclasses import dataclass, field
from contextlib import contextmanager
import gc
import tracemalloc

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics data"""
    test_name: str
    start_time: float
    end_time: float
    duration: float = field(init=False)
    memory_usage_mb: float = field(init=False)
    peak_memory_mb: float = field(init=False)
    cpu_usage_percent: float = field(init=False)
    gc_collections: int = field(init=False)
    operations_per_second: float = field(init=False)
    passed: bool = True
    error_message: Optional[str] = None


@dataclass
class MemorySnapshot:
    """Memory usage snapshot"""
    rss_mb: float  # Resident Set Size in MB
    vms_mb: float  # Virtual Memory Size in MB
    percent: float  # Memory percentage
    heap_objects: int = 0
    timestamp: float = field(default_factory=time.time)


class PerformanceMonitor:
    """
    Real-time performance monitoring for desktop applications

    Features:
    - Memory usage tracking
    - CPU usage monitoring
    - Response time measurement
    - Memory leak detection
    - Performance benchmarking
    """

    def __init__(self):
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.metrics_history: List[MemorySnapshot] = []
        self.start_time: Optional[float] = None
        self.process = psutil.Process()

    def start_monitoring(self, interval: float = 1.0):
        """Start real-time performance monitoring"""
        if self.monitoring:
            return

        self.monitoring = True
        self.start_time = time.time()
        self.metrics_history = []

        def monitor_loop():
            while self.monitoring:
                try:
                    # Get memory usage
                    memory_info = self.process.memory_info()
                    memory_percent = self.process.memory_percent()

                    # Get memory snapshot
                    snapshot = MemorySnapshot(
                        rss_mb=memory_info.rss / 1024 / 1024,
                        vms_mb=memory_info.vms / 1024 / 1024,
                        percent=memory_percent,
                        timestamp=time.time()
                    )

                    self.metrics_history.append(snapshot)

                    # Keep only last 1000 snapshots
                    if len(self.metrics_history) > 1000:
                        self.metrics_history = self.metrics_history[-1000:]

                except Exception as e:
                    logger.error(f"Error in performance monitoring: {e}")

                time.sleep(interval)

        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Performance monitoring started")

    def stop_monitoring(self) -> Dict[str, Any]:
        """Stop monitoring and return summary statistics"""
        if not self.monitoring:
            return {}

        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)

        if not self.metrics_history:
            return {}

        # Calculate statistics
        memory_values = [s.rss_mb for s in self.metrics_history]
        cpu_samples = [self.process.cpu_percent() for _ in range(3)]  # Quick CPU sampling

        return {
            "duration_seconds": time.time() - self.start_time if self.start_time else 0,
            "memory_stats": {
                "avg_mb": sum(memory_values) / len(memory_values),
                "min_mb": min(memory_values),
                "max_mb": max(memory_values),
                "current_mb": memory_values[-1] if memory_values else 0
            },
            "cpu_avg_percent": sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0,
            "samples_collected": len(self.metrics_history)
        }

    def get_current_memory_usage(self) -> MemorySnapshot:
        """Get current memory usage snapshot"""
        try:
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()

            return MemorySnapshot(
                rss_mb=memory_info.rss / 1024 / 1024,
                vms_mb=memory_info.vms / 1024 / 1024,
                percent=memory_percent,
                timestamp=time.time()
            )
        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return MemorySnapshot(rss_mb=0, vms_mb=0, percent=0)

    def check_memory_leak(self, threshold_mb: float = 50.0) -> bool:
        """Check for potential memory leak"""
        if len(self.metrics_history) < 100:
            return False

        # Compare memory usage from 100 samples ago to now
        old_memory = self.metrics_history[-100].rss_mb
        current_memory = self.metrics_history[-1].rss_mb

        return (current_memory - old_memory) > threshold_mb


class PerformanceTestSuite:
    """
    Comprehensive performance testing suite for desktop applications

    Features:
    - Large dataset handling tests
    - Memory usage monitoring
    - CPU usage benchmarks
    - Response time validation
    - Leak detection
    - Stress testing
    """

    def __init__(self):
        self.monitor = PerformanceMonitor()
        self.test_results: List[PerformanceMetrics] = []
        self.current_test: Optional[str] = None

    @contextmanager
    def measure_performance(self, test_name: str):
        """Context manager for performance measurement"""
        # Start monitoring
        self.current_test = test_name
        self.monitor.start_monitoring(interval=0.5)

        # Get initial memory
        initial_memory = self.monitor.get_current_memory_usage()
        gc.collect()  # Clean up before test
        gc.collect()

        # Start memory tracing
        tracemalloc.start()

        start_time = time.time()
        try:
            metrics = PerformanceMetrics(test_name=test_name, start_time=start_time)
            yield metrics
        except Exception as e:
            # Handle test failure
            end_time = time.time()
            metrics = PerformanceMetrics(
                test_name=test_name,
                start_time=start_time,
                end_time=end_time,
                passed=False,
                error_message=str(e)
            )
            yield metrics
        finally:
            # Calculate metrics
            end_time = time.time()
            metrics.end_time = end_time
            metrics.duration = end_time - start_time

            # Get current memory and peak
            current_memory = self.monitor.get_current_memory_usage()
            current, peak = tracemalloc.get_traced_memory()

            metrics.memory_usage_mb = current_memory.rss_mb
            metrics.peak_memory_mb = current_memory.rss_mb
            metrics.gc_collections = gc.collect()  # Force collection and count

            # Stop monitoring
            monitor_stats = self.monitor.stop_monitoring()
            if monitor_stats:
                metrics.cpu_usage_percent = monitor_stats.get("cpu_avg_percent", 0)

            # Store result
            self.test_results.append(metrics)
            self.current_test = None

            tracemalloc.stop()

    def test_datatable_performance(
        self,
        data_generator: Callable[[], List[Dict[str, Any]]],
        operations: List[str],
        max_response_time_ms: float = 100.0
    ) -> List[PerformanceMetrics]:
        """Test DataTable performance with large datasets"""
        logger.info(f"Starting DataTable performance test with {len(operations)} operations")

        results = []

        for operation in operations:
            logger.info(f"Testing DataTable operation: {operation}")

            with self.measure_performance(f"datatable_{operation}") as metrics:
                try:
                    # Generate test data
                    start_operation = time.time()
                    data = data_generator()

                    if operation == "create":
                        # Test DataTable creation
                        import flet as ft
                        dt = ft.DataTable(
                            columns=[ft.DataColumn(ft.Text(f"Col {i}")) for i in range(10)],
                            rows=[ft.DataRow(cells=[ft.DataCell(ft.Text(f"Data {i}-{j}")) for j in range(10)]) for i in range(len(data))]
                        )

                        # Simulate rendering
                        dt.update()

                    elif operation == "sort":
                        # Test sorting performance
                        sorted_data = sorted(data, key=lambda x: x.get('id', 0))

                    elif operation == "filter":
                        # Test filtering performance
                        filtered_data = [item for item in data if item.get('value', 0) > 50]

                    elif operation == "search":
                        # Test search performance
                        search_term = "test"
                        results_found = [item for item in data if search_term in str(item.get('name', '')).lower()]

                    end_operation = time.time()

                    # Calculate operations per second
                    if metrics.duration > 0:
                        metrics.operations_per_second = len(data) / metrics.duration

                    # Validate response time
                    if (end_operation - start_operation) * 1000 > max_response_time_ms:
                        metrics.passed = False
                        metrics.error_message = f"Response time exceeded threshold: {(end_operation - start_operation) * 1000:.2f}ms > {max_response_time_ms}ms"

                except Exception as e:
                    logger.error(f"Error in DataTable test {operation}: {e}")
                    metrics.passed = False
                    metrics.error_message = str(e)

                results.append(metrics)

        return results

    def test_memory_usage_with_large_datasets(
        self,
        dataset_sizes: List[int],
        create_function: Callable[[int], Any],
        memory_threshold_mb: float = 500.0
    ) -> List[PerformanceMetrics]:
        """Test memory usage with progressively larger datasets"""
        logger.info(f"Starting memory usage test with dataset sizes: {dataset_sizes}")

        results = []

        for size in dataset_sizes:
            logger.info(f"Testing memory usage with dataset size: {size}")

            with self.measure_performance(f"memory_test_{size}") as metrics:
                try:
                    # Create dataset
                    start_time = time.time()
                    obj = create_function(size)
                    creation_time = time.time() - start_time

                    # Force garbage collection to see what's retained
                    initial_gc = gc.collect()

                    # Get memory usage after creation
                    current_memory = self.monitor.get_current_memory_usage()
                    metrics.memory_usage_mb = current_memory.rss_mb

                    # Check memory threshold
                    if current_memory.rss_mb > memory_threshold_mb:
                        metrics.passed = False
                        metrics.error_message = f"Memory usage exceeded threshold: {current_memory.rss_mb:.2f}MB > {memory_threshold_mb}MB"

                    # Test object cleanup
                    del obj
                    cleanup_gc = gc.collect()

                except Exception as e:
                    logger.error(f"Error in memory test for size {size}: {e}")
                    metrics.passed = False
                    metrics.error_message = str(e)

                results.append(metrics)

        return results

    def test_long_session_stability(
        self,
        duration_minutes: int = 10,
        operation_interval: float = 1.0,
        operation_function: Callable[[], Any] = None
    ) -> PerformanceMetrics:
        """Test application stability over long sessions"""
        logger.info(f"Starting long session stability test for {duration_minutes} minutes")

        with self.measure_performance("long_session_stability") as metrics:
            try:
                start_time = time.time()
                end_time = start_time + (duration_minutes * 60)
                operation_count = 0

                while time.time() < end_time:
                    # Perform test operation
                    if operation_function:
                        operation_function()

                    operation_count += 1

                    # Check for memory leaks periodically
                    if operation_count % 10 == 0:
                        if self.monitor.check_memory_leak(threshold_mb=20.0):
                            logger.warning(f"Potential memory leak detected at operation {operation_count}")

                    time.sleep(operation_interval)

                # Calculate operations per second
                total_duration = time.time() - start_time
                if total_duration > 0:
                    metrics.operations_per_second = operation_count / total_duration

                # Check final memory usage
                final_memory = self.monitor.get_current_memory_usage()
                metrics.memory_usage_mb = final_memory.rss_mb

            except Exception as e:
                logger.error(f"Error in long session test: {e}")
                metrics.passed = False
                metrics.error_message = str(e)

        return metrics

    def test_cpu_usage_benchmarks(
        self,
        cpu_intensive_tasks: List[Tuple[str, Callable[[], Any]]],
        max_cpu_percent: float = 80.0
    ) -> List[PerformanceMetrics]:
        """Test CPU usage with various tasks"""
        logger.info(f"Starting CPU usage benchmark test with {len(cpu_intensive_tasks)} tasks")

        results = []

        for task_name, task_function in cpu_intensive_tasks:
            logger.info(f"Testing CPU usage with task: {task_name}")

            with self.measure_performance(f"cpu_test_{task_name}") as metrics:
                try:
                    # Monitor CPU usage during task
                    start_cpu = psutil.cpu_percent(interval=1.0)

                    # Execute task
                    start_time = time.time()
                    task_function()
                    end_time = time.time()

                    # Get CPU usage after task
                    end_cpu = psutil.cpu_percent(interval=1.0)

                    metrics.cpu_usage_percent = (start_cpu + end_cpu) / 2

                    # Check CPU threshold
                    if metrics.cpu_usage_percent > max_cpu_percent:
                        metrics.passed = False
                        metrics.error_message = f"CPU usage exceeded threshold: {metrics.cpu_usage_percent:.1f}% > {max_cpu_percent}%"

                except Exception as e:
                    logger.error(f"Error in CPU test {task_name}: {e}")
                    metrics.passed = False
                    metrics.error_message = str(e)

                results.append(metrics)

        return results

    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        if not self.test_results:
            return {"error": "No test results available"}

        passed_tests = sum(1 for r in self.test_results if r.passed)
        total_tests = len(self.test_results)

        # Calculate statistics
        durations = [r.duration for r in self.test_results]
        memory_usage = [r.memory_usage_mb for r in self.test_results if r.memory_usage_mb > 0]
        cpu_usage = [r.cpu_usage_percent for r in self.test_results if r.cpu_usage_percent > 0]

        return {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0
            },
            "performance_stats": {
                "avg_duration": sum(durations) / len(durations) if durations else 0,
                "min_duration": min(durations) if durations else 0,
                "max_duration": max(durations) if durations else 0,
                "avg_memory_mb": sum(memory_usage) / len(memory_usage) if memory_usage else 0,
                "max_memory_mb": max(memory_usage) if memory_usage else 0,
                "avg_cpu_percent": sum(cpu_usage) / len(cpu_usage) if cpu_usage else 0,
                "max_cpu_percent": max(cpu_usage) if cpu_usage else 0
            },
            "failed_tests": [
                {
                    "test_name": r.test_name,
                    "error": r.error_message,
                    "duration": r.duration,
                    "memory_mb": r.memory_usage_mb
                }
                for r in self.test_results if not r.passed
            ],
            "all_results": [
                {
                    "test_name": r.test_name,
                    "passed": r.passed,
                    "duration": r.duration,
                    "memory_mb": r.memory_usage_mb,
                    "cpu_percent": r.cpu_usage_percent,
                    "ops_per_second": r.operations_per_second
                }
                for r in self.test_results
            ]
        }


# Test data generators and functions
def generate_test_data(size: int) -> List[Dict[str, Any]]:
    """Generate test data for performance testing"""
    return [
        {
            "id": i,
            "name": f"Test Item {i}",
            "value": i * 10,
            "description": f"Description for test item {i}",
            "category": f"Category {(i % 5) + 1}",
            "timestamp": time.time() - (size - i)
        }
        for i in range(size)
    ]


def create_large_datatable(size: int) -> ft.DataTable:
    """Create a large DataTable for testing"""
    import flet as ft

    columns = [
        ft.DataColumn(ft.Text(f"Column {i}", weight=ft.FontWeight.BOLD))
        for i in range(10)
    ]

    rows = []
    for i in range(size):
        cells = [
            ft.DataCell(ft.Text(f"Row {i}, Col {j}"))
            for j in range(10)
        ]
        rows.append(ft.DataRow(cells=cells))

    return ft.DataTable(columns=columns, rows=rows)


def cpu_intensive_calculation(iterations: int = 100000) -> float:
    """CPU intensive calculation for testing"""
    result = 0.0
    for i in range(iterations):
        result += (i * i) / (i + 1)
    return result


def run_desktop_performance_tests() -> Dict[str, Any]:
    """Run comprehensive desktop performance tests"""
    suite = PerformanceTestSuite()

    print("🚀 Starting Desktop Performance Test Suite")
    print("=" * 50)

    # Test 1: DataTable performance with different sizes
    print("\n📊 Testing DataTable Performance...")
    dataset_sizes = [100, 500, 1000, 5000]
    operations = ["create", "sort", "filter", "search"]

    for size in dataset_sizes:
        data_gen = lambda: generate_test_data(size)
        results = suite.test_datatable_performance(data_gen, operations)

        for result in results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"   {status} {result.test_name}: {result.duration:.3f}s, {result.memory_usage_mb:.1f}MB")

    # Test 2: Memory usage with large datasets
    print("\n💾 Testing Memory Usage...")
    memory_sizes = [1000, 5000, 10000, 25000]

    def create_dataset(size):
        return generate_test_data(size)

    memory_results = suite.test_memory_usage_with_large_datasets(memory_sizes, create_dataset)

    for result in memory_results:
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"   {status} {result.test_name}: {result.memory_usage_mb:.1f}MB")

    # Test 3: CPU usage benchmarks
    print("\n⚡ Testing CPU Usage...")
    cpu_tasks = [
        ("calculation", lambda: cpu_intensive_calculation(50000)),
        ("sorting", lambda: sorted([i % 1000 for i in range(10000)], reverse=True)),
        ("string_processing", lambda: ["test".upper() for i in range(10000)])
    ]

    cpu_results = suite.test_cpu_usage_benchmarks(cpu_tasks)

    for result in cpu_results:
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"   {status} {result.test_name}: {result.cpu_usage_percent:.1f}% CPU")

    # Test 4: Long session stability (shortened for demo)
    print("\n⏱️ Testing Session Stability...")

    def simple_operation():
        # Simple operation to simulate user activity
        data = generate_test_data(100)
        sorted(data)
        len(data)

    stability_result = suite.test_long_session_stability(
        duration_minutes=1,  # Shortened for demo
        operation_interval=0.1,
        operation_function=simple_operation
    )

    status = "✅ PASS" if stability_result.passed else "❌ FAIL"
    print(f"   {status} Long session test: {stability_result.duration:.1f}s, {stability_result.operations_per_second:.1f} ops/sec")

    # Generate final report
    print("\n" + "=" * 50)
    print("📈 Performance Test Report")
    print("=" * 50)

    report = suite.generate_performance_report()

    print(f"Total Tests: {report['summary']['total_tests']}")
    print(f"Passed: {report['summary']['passed_tests']}")
    print(f"Failed: {report['summary']['failed_tests']}")
    print(f"Success Rate: {report['summary']['success_rate']:.1f}%")

    print("\nPerformance Statistics:")
    print(f"Average Duration: {report['performance_stats']['avg_duration']:.3f}s")
    print(f"Average Memory: {report['performance_stats']['avg_memory_mb']:.1f}MB")
    print(f"Average CPU: {report['performance_stats']['avg_cpu_percent']:.1f}%")

    if report['failed_tests']:
        print("\n❌ Failed Tests:")
        for failed in report['failed_tests']:
            print(f"   - {failed['test_name']}: {failed['error']}")

    return report


if __name__ == "__main__":
    # Run tests when executed directly
    run_desktop_performance_tests()