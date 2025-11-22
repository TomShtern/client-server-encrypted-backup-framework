"""
MEMORY LEAK FIXES VALIDATION TESTS
==================================

PURPOSE: Validate that memory leak fixes work correctly
TESTS: Streaming file operations, memory-efficient transfers, cleanup
COVERAGE: API server, file transfer manager, utilities

This test suite ensures that:
1. Large files are processed using streaming (not loaded into memory)
2. Transfer states are cleaned up properly
3. Memory bounds are enforced
4. Resource cleanup works on both success and failure cases
"""

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from Shared.utils.streaming_file_utils import (
    calculate_file_hash_streaming,
    read_file_chunks,
    StreamingFileReader,
    MemoryUsageTracker
)
from Shared.utils.memory_efficient_file_transfer import (
    MemoryEfficientTransferManager,
    TransferConfig
)


class TestStreamingFileUtils(unittest.TestCase):
    """Test streaming file utilities for memory efficiency."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_data = b'A' * 1024 * 1024  # 1MB test data
        self.test_file = None

    def tearDown(self):
        """Clean up test fixtures."""
        if self.test_file and os.path.exists(self.test_file):
            os.remove(self.test_file)

    def _create_test_file(self, size_mb=1):
        """Create a test file of specified size."""
        self.test_file = tempfile.mktemp(suffix='.test')
        with open(self.test_file, 'wb') as f:
            f.write(b'A' * (size_mb * 1024 * 1024))
        return self.test_file

    def test_calculate_file_hash_streaming_small_file(self):
        """Test streaming hash calculation on small files."""
        self._create_test_file(1)  # 1MB file

        # Test streaming hash calculation
        hash_result = calculate_file_hash_streaming(self.test_file, 'sha256')
        self.assertIsNotNone(hash_result)
        self.assertEqual(len(hash_result), 64)  # SHA256 hex length

        # Verify against traditional method
        import hashlib
        with open(self.test_file, 'rb') as f:
            expected_hash = hashlib.sha256(f.read()).hexdigest()

        self.assertEqual(hash_result, expected_hash)

    def test_calculate_file_hash_streaming_large_file(self):
        """Test streaming hash calculation on large files."""
        self._create_test_file(10)  # 10MB file

        # Monitor memory usage during hash calculation
        tracker = MemoryUsageTracker()
        hash_result = calculate_file_hash_streaming(self.test_file, 'sha256')

        self.assertIsNotNone(hash_result)

        # Memory usage should be reasonable (less than file size)
        memory_delta = tracker.get_memory_delta()
        file_size = os.path.getsize(self.test_file)

        # Memory usage should be significantly less than file size
        # (allowing some overhead for Python objects)
        self.assertLess(memory_delta, file_size * 0.5)

    def test_read_file_chunks(self):
        """Test chunked file reading."""
        self._create_test_file(1)  # 1MB file
        chunk_size = 64 * 1024  # 64KB chunks

        chunks = list(read_file_chunks(self.test_file, chunk_size))
        expected_chunks = (1024 * 1024) // chunk_size

        self.assertEqual(len(chunks), expected_chunks)
        self.assertEqual(sum(len(chunk) for chunk in chunks), 1024 * 1024)

    def test_streaming_file_reader_context_manager(self):
        """Test StreamingFileReader context manager."""
        self._create_test_file(1)  # 1MB file

        with StreamingFileReader(self.test_file, chunk_size=1024) as reader:
            chunks = list(reader.read_all_chunks())
            total_size = sum(len(chunk) for chunk in chunks)

        self.assertEqual(total_size, 1024 * 1024)

        # File should be properly closed
        # (Can't directly test file handle closure, but context manager should work)

    def test_calculate_file_hash_nonexistent_file(self):
        """Test hash calculation with nonexistent file."""
        result = calculate_file_hash_streaming('/nonexistent/file', 'sha256')
        self.assertIsNone(result)

    def test_memory_usage_tracker(self):
        """Test memory usage tracking."""
        tracker = MemoryUsageTracker()
        initial_delta = tracker.get_memory_delta()

        # Allocate some memory
        data = b'A' * (10 * 1024 * 1024)  # 10MB

        tracker.update_peak()
        peak_delta = tracker.get_peak_delta()

        # Clean up
        del data

        # Peak should be at least as much as initial allocation
        self.assertGreaterEqual(peak_delta, initial_delta)


class TestMemoryEfficientTransferManager(unittest.TestCase):
    """Test memory-efficient transfer manager."""

    def setUp(self):
        """Set up test fixtures."""
        # Use a test configuration
        self.config = TransferConfig(
            max_concurrent_transfers=5,
            max_chunks_per_file=100,
            max_chunk_memory_mb=10,  # 10MB limit for testing
            cleanup_interval_seconds=1,  # Fast cleanup for tests
            abandoned_transfer_timeout=2,  # 2 second timeout for tests
            memory_pressure_threshold_mb=5  # Low threshold for testing
        )
        self.manager = MemoryEfficientTransferManager(self.config)
        self.client_id = b'\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10'

    def tearDown(self):
        """Clean up test fixtures."""
        if self.manager:
            self.manager.shutdown()

    def test_create_transfer_within_limits(self):
        """Test creating transfers within memory limits."""
        result = self.manager.create_transfer(
            self.client_id, 'test_file.txt', 10, 1024
        )
        self.assertTrue(result)

    def test_create_transfer_exceeds_limits(self):
        """Test creating transfers that exceed memory limits."""
        # Fill up to the concurrent transfer limit
        for i in range(self.config.max_concurrent_transfers):
            result = self.manager.create_transfer(
                self.client_id, f'file_{i}.txt', 10, 1024
            )
            self.assertTrue(result)

        # Next transfer should fail
        result = self.manager.create_transfer(
            self.client_id, 'file_overflow.txt', 10, 1024
        )
        self.assertFalse(result)

    def test_add_packet_within_memory_limits(self):
        """Test adding packets within memory limits."""
        self.manager.create_transfer(self.client_id, 'test_file.txt', 5, 1024)

        # Add packets within memory limit
        small_chunk = b'A' * 1024  # 1KB
        result = self.manager.add_packet(self.client_id, 'test_file.txt', 1, small_chunk)
        self.assertTrue(result)

    def test_add_packet_exceeds_memory_limits(self):
        """Test adding packets that exceed memory limits."""
        self.manager.create_transfer(self.client_id, 'test_file.txt', 5, 1024)

        # Add a chunk that exceeds memory limit
        large_chunk = b'A' * (self.config.max_chunk_memory_mb * 1024 * 1024 + 1)
        result = self.manager.add_packet(self.client_id, 'test_file.txt', 1, large_chunk)
        self.assertFalse(result)

    def test_transfer_completion_and_cleanup(self):
        """Test transfer completion and automatic cleanup."""
        filename = 'test_file.txt'
        total_packets = 3

        # Create transfer
        self.manager.create_transfer(self.client_id, filename, total_packets, 1024)

        # Add all packets
        for i in range(1, total_packets + 1):
            chunk = f'packet_{i}'.encode()
            result = self.manager.add_packet(self.client_id, filename, i, chunk)
            self.assertTrue(result)

        # Verify transfer is complete
        transfer_state = self.manager.get_transfer_state(self.client_id, filename)
        self.assertIsNotNone(transfer_state)
        self.assertTrue(transfer_state.is_complete())

        # Remove transfer
        result = self.manager.remove_transfer(self.client_id, filename, "completed")
        self.assertTrue(result)

        # Verify transfer is gone
        transfer_state = self.manager.get_transfer_state(self.client_id, filename)
        self.assertIsNone(transfer_state)

    def test_abandoned_transfer_cleanup(self):
        """Test automatic cleanup of abandoned transfers."""
        # Create a transfer but don't complete it
        self.manager.create_transfer(self.client_id, 'abandoned_file.txt', 10, 1024)

        # Wait for timeout
        time.sleep(self.config.abandoned_transfer_timeout + 1)

        # Trigger cleanup
        self.manager._perform_cleanup()

        # Transfer should be cleaned up
        transfer_state = self.manager.get_transfer_state(self.client_id, 'abandoned_file.txt')
        self.assertIsNone(transfer_state)

    def test_memory_pressure_cleanup(self):
        """Test cleanup under memory pressure."""
        # Create transfers with large chunks to trigger memory pressure
        for i in range(3):
            self.manager.create_transfer(self.client_id, f'large_file_{i}.txt', 5, 1024)
            # Add large chunks (but within individual transfer limits)
            large_chunk = b'A' * (self.config.max_chunk_memory_mb * 1024 * 1024 // 2)
            self.manager.add_packet(self.client_id, f'large_file_{i}.txt', 1, large_chunk)

        # Trigger memory pressure cleanup
        self.manager._aggressive_cleanup()

        # Some transfers should be evicted
        stats = self.manager.get_statistics()
        self.assertLess(stats['active_transfers'], 3)

    def test_transfer_statistics(self):
        """Test transfer manager statistics."""
        # Create some transfers
        self.manager.create_transfer(self.client_id, 'file1.txt', 5, 1024)
        self.manager.create_transfer(self.client_id, 'file2.txt', 3, 512)

        # Add some packets
        self.manager.add_packet(self.client_id, 'file1.txt', 1, b'data1')
        self.manager.add_packet(self.client_id, 'file1.txt', 2, b'data2')

        # Get statistics
        stats = self.manager.get_statistics()

        self.assertEqual(stats['total_transfers'], 2)
        self.assertEqual(stats['active_transfers'], 2)
        self.assertGreater(stats['current_memory_mb'], 0)


class TestMemoryLeakFixesIntegration(unittest.TestCase):
    """Integration tests for memory leak fixes."""

    def test_api_server_streaming_hash_replacement(self):
        """Test that API server uses streaming hash calculation."""
        # Create a test file
        test_file = tempfile.mktemp(suffix='.test')
        try:
            with open(test_file, 'wb') as f:
                f.write(b'A' * (5 * 1024 * 1024))  # 5MB file

            # Test the streaming hash function that replaces the old one
            from Shared.utils.streaming_file_utils import calculate_file_hash_streaming

            # Monitor memory
            tracker = MemoryUsageTracker()
            hash_result = calculate_file_hash_streaming(test_file, 'sha256')

            # Verify result is valid
            self.assertIsNotNone(hash_result)
            self.assertEqual(len(hash_result), 64)

            # Verify memory usage is bounded
            memory_delta = tracker.get_memory_delta()
            file_size = os.path.getsize(test_file)

            # Memory should be much less than file size
            self.assertLess(memory_delta, file_size * 0.1)

        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_file_transfer_memory_bounds(self):
        """Test that file transfer manager respects memory bounds."""
        manager = MemoryEfficientTransferManager(TransferConfig(
            max_concurrent_transfers=2,
            max_chunk_memory_mb=1  # 1MB limit
        ))

        try:
            client_id = b'\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10'

            # Create transfer
            result = manager.create_transfer(client_id, 'test.txt', 3, 1024)
            self.assertTrue(result)

            # Add small chunk (should succeed)
            result = manager.add_packet(client_id, 'test.txt', 1, b'small_data')
            self.assertTrue(result)

            # Try to add large chunk (should fail)
            large_chunk = b'A' * (2 * 1024 * 1024)  # 2MB
            result = manager.add_packet(client_id, 'test.txt', 2, large_chunk)
            self.assertFalse(result)

        finally:
            manager.shutdown()


def run_memory_efficiency_test():
    """Run a simple memory efficiency test."""
    print("Testing memory efficiency of streaming operations...")

    # Create a large test file
    test_file = tempfile.mktemp(suffix='.test')
    file_size_mb = 50  # 50MB test file

    print(f"Creating {file_size_mb}MB test file...")
    with open(test_file, 'wb') as f:
        f.write(b'A' * (file_size_mb * 1024 * 1024))

    try:
        # Test streaming hash calculation
        print("Testing streaming hash calculation...")
        tracker = MemoryUsageTracker()
        start_time = time.time()

        hash_result = calculate_file_hash_streaming(test_file, 'sha256')

        end_time = time.time()
        memory_delta = tracker.get_memory_delta()

        print("Hash calculation completed:")
        print(f"  File size: {file_size_mb}MB")
        print(f"  Time: {end_time - start_time:.2f}s")
        print(f"  Memory delta: {memory_delta / (1024*1024):.2f}MB")
        print(f"  Hash: {hash_result[:16]}...")
        print(f"  Memory efficiency: {file_size_mb / (memory_delta / (1024*1024)):.1f}x")

        # Test traditional method for comparison
        print("\nTesting traditional method for comparison...")
        tracker2 = MemoryUsageTracker()
        start_time = time.time()

        import hashlib
        with open(test_file, 'rb') as f:
            traditional_hash = hashlib.sha256(f.read()).hexdigest()

        end_time = time.time()
        memory_delta2 = tracker2.get_memory_delta()

        print("Traditional method:")
        print(f"  Time: {end_time - start_time:.2f}s")
        print(f"  Memory delta: {memory_delta2 / (1024*1024):.2f}MB")
        if memory_delta2 > 0:
            print(f"  Memory efficiency: {file_size_mb / (memory_delta2 / (1024*1024)):.1f}x")
        else:
            print("  Memory efficiency: N/A (memory delta too small to measure)")

        # Verify results match
        assert hash_result == traditional_hash, "Hash results don't match!"
        print("\n✓ Hash results match - streaming implementation is correct!")

    finally:
        if os.path.exists(test_file):
            os.remove(test_file)


if __name__ == '__main__':
    print("Running Memory Leak Fixes Validation Tests")
    print("=" * 50)

    # Run the memory efficiency test first
    run_memory_efficiency_test()
    print("\n" + "=" * 50)

    # Run unit tests
    unittest.main(verbosity=2)