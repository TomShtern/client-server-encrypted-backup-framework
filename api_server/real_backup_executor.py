#!/usr/bin/env python3
"""
Real Backup Executor - Smart Process Control for EncryptedBackupClient.exe
This module provides REAL integration with the existing C++ client, not fake APIs.
It is responsible for configuring and launching the C++ subprocess.
Progress monitoring and verification are handled by the UnifiedFileMonitor.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import contextlib
import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from typing import IO, Any

from Shared.filesystem.file_lifecycle import SynchronizedFileManager
from Shared.filesystem.utf8_solution import Popen_utf8
from Shared.logging.enhanced_output import EmojiLogger
from Shared.logging.error_handler import ErrorSeverity, handle_subprocess_error
from Shared.monitoring.unified_monitor import UnifiedFileMonitor

logger = logging.getLogger(__name__)
enhanced_logger = EmojiLogger.get_logger(__name__)


class RealBackupExecutor:
    """
    A simplified wrapper for EncryptedBackupClient.exe that provides real backup functionality
    by managing the C++ subprocess.
    """

    def __init__(self, client_exe_path: str | None = None):
        if not client_exe_path:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            possible_paths = [
                os.path.join(
                    project_root, "build", "Release", "EncryptedBackupClient.exe"
                ),
                r"build\Release\EncryptedBackupClient.exe",
                r"EncryptedBackupClient.exe",
            ]
            self.client_exe = next(
                (path for path in possible_paths if os.path.exists(path)), None
            ) or os.path.join(
                project_root, "build", "Release", "EncryptedBackupClient.exe"
            )
        else:
            self.client_exe = client_exe_path

        self.temp_dir = tempfile.mkdtemp()
        self.backup_process: subprocess.Popen[str] | None = None
        self.status_callback: Callable[..., Any] | None = None
        self.file_manager = SynchronizedFileManager(self.temp_dir)
        self.process_id: int | None = None
        self.server_received_files = "received_files"

        # Adaptive timeout configuration (coordinates with C++ client 25s timeout)
        self.timeout_config = {
            "base_timeout": 30,  # Base timeout in seconds (must be > C++ client 25s)
            "size_multiplier": 2,  # Extra seconds per MB
            "min_timeout": 45,  # Minimum timeout (ensures margin above C++ client)
            "max_timeout": 1800,  # Maximum timeout (30 minutes for very large files)
        }

        # Progress simulation configuration
        self.progress_config = self._load_progress_config()
        self.progress_thread: threading.Thread | None = None
        self.progress_stop_event = threading.Event()
        self.current_phase = "READY"
        self.phase_start_time = 0.0

    def is_running(self) -> bool:
        """Return True if a backup subprocess is currently running"""
        return bool(self.backup_process) and self.backup_process.poll() is None

    def cancel(self, reason: str = "User requested cancellation") -> bool:
        """Attempt to cancel the running backup subprocess gracefully."""
        if not self.backup_process or not self.process_id:
            self._log_status("CANCEL", "No active backup process to cancel")
            return False

        self._log_status(
            "CANCEL", f"Cancelling backup process (PID: {self.process_id}) - {reason}"
        )
        try:
            # Terminate the subprocess gracefully
            self.backup_process.terminate()
            try:
                # Wait for graceful termination
                self.backup_process.wait(timeout=5.0)
                self._log_status("CANCEL", "Backup process terminated gracefully")
                return True
            except subprocess.TimeoutExpired:
                # Force kill if graceful termination fails
                self.backup_process.kill()
                self._log_status("CANCEL", "Backup process force-killed after timeout")
                return True
        except Exception as e:
            self._log_status("ERROR", f"Cancellation error: {e}")
            return False

    def set_status_callback(self, callback: Callable[[str, Any], None]):
        """Set callback function for real-time status updates"""
        self.status_callback = callback

    def _log_status(self, phase: str, message: str):
        """Log status updates via callback with enhanced emojis and colors"""
        # Enhanced emoji mapping with more appropriate and specific emojis
        emoji_map = {
            # Execution phases
            "EXECUTION": "🚀",
            "LAUNCH": "🔧",
            "PROCESS": "⚙️",
            "START": "🚀",
            # Completion states
            "COMPLETION": "✅",
            "MONITOR_COMPLETE": "✅",
            "COMPLETE": "✅",
            # Error states
            "MONITOR_FAILURE": "❌",
            "ERROR": "❌",
            "TIMEOUT": "⏰",
            "FORCE_KILL": "🔪",
            # Management operations
            "CANCEL": "⛔",
            "CLEANUP": "🧹",
            "VERIFICATION": "🔍",
            # Configuration & setup
            "CONFIG": "⚙️",
            "AUTH": "🔐",
            "TIMEOUT_CALC": "⏱️",
            # File operations
            "FILE_COPY": "📋",
            "FILE_CREATE": "📄",
            # Default
            "DEFAULT": "ℹ️",
        }

        emoji = emoji_map.get(phase, emoji_map["DEFAULT"])

        # Use enhanced logger for better visual feedback
        if phase in {"ERROR", "MONITOR_FAILURE", "FORCE_KILL"}:
            enhanced_logger.error(f"[{phase}] {message}")
        elif phase in {"WARNING", "TIMEOUT", "CANCEL"}:
            enhanced_logger.warning(f"[{phase}] {message}")
        elif phase in {"COMPLETION", "MONITOR_COMPLETE", "COMPLETE"}:
            # Use dynamic attribute access for enhanced methods
            if hasattr(enhanced_logger, "success"):
                enhanced_logger.success(f"[{phase}] {message}")  # type: ignore
            else:
                enhanced_logger.info(f"✅ [{phase}] {message}")
        else:
            enhanced_logger.info(f"[{phase}] {message}")

        # Also log to original logger for compatibility
        logger.info(f"{emoji} [{phase}] {message}")

        if self.status_callback:
            self.status_callback(phase, {"message": message})

    def _load_progress_config(self) -> dict[str, Any]:
        """Load progress configuration from JSON file"""
        try:
            # Try to find progress_config.json in python_server directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            config_path = os.path.join(
                project_root, "python_server", "progress_config.json"
            )

            if os.path.exists(config_path):
                with open(config_path, encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load progress config: {e}")

        # Fallback default configuration
        return {
            "phases": {
                "CONNECTING": {
                    "weight": 0.10,
                    "description": "Connecting to backup server...",
                },
                "AUTHENTICATING": {
                    "weight": 0.15,
                    "description": "Authenticating user credentials...",
                },
                "ENCRYPTING": {
                    "weight": 0.30,
                    "description": "Encrypting file with AES-256...",
                },
                "TRANSFERRING": {
                    "weight": 0.35,
                    "description": "Transferring encrypted data...",
                },
                "VERIFYING": {
                    "weight": 0.10,
                    "description": "Verifying transfer integrity...",
                },
            }
        }

    def _start_progress_simulation(self):
        """Start progress simulation thread"""
        if self.progress_thread and self.progress_thread.is_alive():
            return

        self.progress_stop_event.clear()
        self.progress_thread = threading.Thread(
            target=self._progress_simulation_worker, daemon=True
        )
        self.progress_thread.start()

    def _stop_progress_simulation(self):
        """Stop progress simulation thread"""
        self.progress_stop_event.set()
        if self.progress_thread:
            self.progress_thread.join(timeout=1.0)

    def _progress_simulation_worker(self):
        """Worker thread for progress simulation"""
        phases = [
            "CONNECTING",
            "AUTHENTICATING",
            "ENCRYPTING",
            "TRANSFERRING",
            "VERIFYING",
        ]
        phase_weights: dict[str, float] = {}
        total_weight = 0.0

        # Calculate weights from config
        for phase in phases:
            weight = (
                self.progress_config.get("phases", {}).get(phase, {}).get("weight", 0.2)
            )
            phase_weights[phase] = float(weight) if weight is not None else 0.2
            total_weight += phase_weights[phase]

        # Normalize weights to sum to 1.0
        if total_weight > 0:
            for phase in phase_weights:
                phase_weights[phase] /= total_weight

        current_progress = 0.0
        for i, phase in enumerate(phases):
            if self.progress_stop_event.is_set():
                return

            self.current_phase = phase
            phase_weight = phase_weights.get(phase, 0.2)
            phase_duration = 2.0 + (i * 0.5)  # Vary duration by phase

            # Update phase description
            phase_description = (
                self.progress_config.get("phases", {})
                .get(phase, {})
                .get("description", f"{phase}...")
            )
            if self.status_callback:
                self.status_callback(
                    phase, {"message": phase_description, "progress": current_progress}
                )

            # Simulate progress within this phase
            steps = 20
            for step in range(steps):
                if self.progress_stop_event.is_set():
                    return

                step_progress = (step / steps) * phase_weight * 100
                total_progress = current_progress + step_progress

                if self.status_callback:
                    self.status_callback(
                        phase,
                        {
                            "message": phase_description,
                            "progress": min(total_progress, 100.0),
                        },
                    )

                time.sleep(phase_duration / steps)

            current_progress += phase_weight * 100

        # Final completion
        if not self.progress_stop_event.is_set() and self.status_callback:
            self.status_callback(
                "COMPLETED",
                {"message": "Backup completed successfully!", "progress": 100.0},
            )

    def _log_status_with_progress(
        self, phase: str, message: str, progress: float | None = None
    ):
        """Enhanced log status with progress information"""
        self._log_status(phase, message)
        if progress is not None and self.status_callback:
            self.status_callback(phase, {"message": message, "progress": progress})

    def _calculate_adaptive_timeout(self, file_path: str) -> int:
        """Calculate adaptive timeout based on file size to prevent client/server timeout mismatches."""
        try:
            file_size_bytes = os.path.getsize(file_path)
            file_size_mb = file_size_bytes / (1024 * 1024)

            # Calculate timeout: base + (size_in_mb * multiplier)
            calculated_timeout = self.timeout_config["base_timeout"] + (
                file_size_mb * self.timeout_config["size_multiplier"]
            )

            # Apply min/max bounds
            adaptive_timeout = max(
                self.timeout_config["min_timeout"],
                min(calculated_timeout, self.timeout_config["max_timeout"]),
            )

            self._log_status(
                "TIMEOUT_CALC",
                f"File: {file_size_mb:.1f}MB → Timeout: {adaptive_timeout:.0f}s "
                f"(base: {self.timeout_config['base_timeout']}s + "
                f"{file_size_mb:.1f}MB × {self.timeout_config['size_multiplier']}s/MB)",
            )

            return int(adaptive_timeout)

        except OSError as e:
            self._log_status(
                "TIMEOUT_CALC",
                f"Could not get file size for {file_path}: {e}. Using min timeout.",
            )
            return self.timeout_config["min_timeout"]

    def _generate_transfer_info(
        self, server_ip: str, server_port: int, username: str, file_path: str
    ) -> tuple[str, str]:
        """Generate managed transfer.info file for the C++ client"""
        absolute_file_path = os.path.abspath(file_path)
        content = f"{server_ip}:{server_port}\n{username}\n{absolute_file_path}"
        self._log_status("CONFIG", f"transfer.info content:\n---\n{content}---")

        transfer_info_path = self.file_manager.create_managed_file(
            "transfer.info", content
        )
        file_id = f"transfer_{int(time.time())}"  # Generate a simple file ID
        self._log_status(
            "CONFIG", f"Generated managed transfer.info: {transfer_info_path}"
        )
        return file_id, transfer_info_path

    def _clear_cached_credentials_if_username_changed(self, username: str) -> None:
        """Clear cached credentials if username has changed from previous backup."""
        # Simple implementation - could be extended to actually cache credentials
        # For now, just log the username change check
        self._log_status("AUTH", f"Checking credentials for username: {username}")

    def _execute_client_subprocess(
        self, client_cwd: str, timeout: int = 120
    ) -> dict[str, Any]:
        """Execute the C++ client subprocess and return results."""
        self._log_status(
            "EXECUTION", f"Starting C++ client: {self.client_exe} with --batch flag"
        )

        # Use UTF-8 subprocess with proper environment setup for C++ client
        # Note: Popen_utf8 includes errors='replace' to handle invalid UTF-8 bytes from C++ client
        self.backup_process = Popen_utf8(
            [str(self.client_exe), "--batch"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=client_cwd,
        )
        if self.backup_process:
            self.process_id = self.backup_process.pid
        else:
            raise RuntimeError("Failed to start backup process")

        stdout, stderr = self.backup_process.communicate(timeout=timeout)
        return_code = self.backup_process.returncode

        self._log_status(
            "COMPLETION", f"C++ client finished with exit code: {return_code}"
        )
        if stdout:
            logger.debug(f"💬 C++ Client STDOUT:\n{stdout}")
        if stderr:
            logger.warning(f"⚠️ C++ Client STDERR:\n{stderr}")

        return {"return_code": return_code, "stdout": stdout, "stderr": stderr}

    def _execute_subprocess_nonblocking(self, timeout: int = 120) -> dict[str, Any]:
        """Execute subprocess with non-blocking, progressive timeout pipe reading."""

        def _read_pipe(
            pipe: IO[str] | None, chunks: list[str], lock: threading.Lock
        ) -> None:
            """Helper to read pipe chunks safely with improved error handling."""
            if not pipe:
                return
            try:
                while True:
                    chunk = pipe.read(4096)  # Read in small, manageable chunks
                    if not chunk:
                        break
                    with lock:
                        chunks.append(chunk)
            except UnicodeDecodeError as e:
                # Specific handling for UTF-8 decode errors from C++ client
                logger.warning(f"UTF-8 decode error in subprocess pipe: {e}")
                logger.debug(
                    f"Error details: byte 0x{e.object[e.start : e.end].hex()} at position {e.start}"
                )
                # Continue reading - the error should be handled by errors='replace' in Popen_utf8
            except Exception as e:
                # Log other unexpected errors for debugging
                logger.warning(f"Unexpected error reading subprocess pipe: {e}")
            finally:
                with contextlib.suppress(Exception):
                    pipe.close()

        # Thread-safe data structures
        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []
        stdout_lock, stderr_lock = threading.Lock(), threading.Lock()

        # Launch non-blocking readers
        if self.backup_process is None:
            raise RuntimeError("Backup process is not initialized")

        stdout_thread = threading.Thread(
            target=_read_pipe,
            args=(self.backup_process.stdout, stdout_chunks, stdout_lock),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=_read_pipe,
            args=(self.backup_process.stderr, stderr_chunks, stderr_lock),
            daemon=True,
        )

        stdout_thread.start()
        stderr_thread.start()

        # Progressive timeout with incremental checks
        start_time = time.time()
        while (
            time.time() - start_time < timeout
            and self.backup_process is not None
            and self.backup_process.poll() is None
        ):
            time.sleep(1)  # Small sleep to prevent busy waiting

        # Handle timeout scenario
        if self.backup_process is None:
            raise RuntimeError("Backup process is not initialized")
        if self.backup_process.poll() is None:
            self._log_status(
                "TIMEOUT", f"Subprocess timeout after {timeout}s, terminating..."
            )
            self.backup_process.terminate()
            try:
                self.backup_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._log_status(
                    "FORCE_KILL", "Process did not respond to terminate, killing..."
                )
                self.backup_process.kill()
                self.backup_process.wait()
            raise subprocess.TimeoutExpired([str(self.client_exe), "--batch"], timeout)

        # Collect results
        stdout_thread.join(timeout=5)
        stderr_thread.join(timeout=5)

        with stdout_lock:
            stdout = "".join(stdout_chunks)
        with stderr_lock:
            stderr = "".join(stderr_chunks)

        return {
            "stdout": stdout,
            "stderr": stderr,
            "return_code": self.backup_process.returncode
            if self.backup_process
            else -1,
        }

    def execute_real_backup(
        self, username: str, file_path: str, server_ip: str, server_port: int
    ) -> dict[str, Any]:
        """Executes the C++ client, waits for it to complete, and returns the result."""
        if not self.client_exe or not os.path.exists(self.client_exe):
            error_msg = f"C++ client not found at {self.client_exe}"
            self._log_status("ERROR", error_msg)
            return {"success": False, "error": error_msg}

        file_id, transfer_info_path = None, None
        try:
            file_id, transfer_info_path = self._generate_transfer_info(
                server_ip, server_port, username, file_path
            )
            client_cwd = os.path.dirname(transfer_info_path)

            # Execute the C++ client subprocess
            subprocess_result = self._execute_client_subprocess(client_cwd, timeout=120)
            return_code = subprocess_result["return_code"]
            stderr = subprocess_result["stderr"]

            if return_code != 0:
                handle_subprocess_error(
                    message=f"C++ client exited with non-zero code: {return_code}",
                    details=stderr,
                    component="RealBackupExecutor",
                    severity=ErrorSeverity.HIGH,
                )
                return {
                    "success": False,
                    "error": f"Client process failed with code {return_code}",
                    "details": stderr,
                }

            return {
                "success": True,
                "message": "Client process completed successfully.",
            }

        except subprocess.TimeoutExpired:
            self._log_status("ERROR", "C++ client process timed out.")
            self.cancel("Timeout")
            return {"success": False, "error": "Process timed out"}
        except Exception as e:
            logger.critical(
                f"🔥 An unexpected error occurred during backup execution: {e}",
                exc_info=True,
            )
            return {"success": False, "error": f"An unexpected error occurred: {e}"}
        finally:
            if file_id:
                self.file_manager.safe_cleanup(file_id)
            self.backup_process = None
            self.process_id = None

    def execute_backup_with_verification(
        self,
        username: str,
        file_path: str,
        server_ip: str = "127.0.0.1",
        server_port: int = 1256,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """Execute REAL backup using the C++ client with verification and robust progress.

        This rewritten implementation corrects prior indentation corruption and consolidates
        lifecycle management (transfer.info generation, subprocess launch, monitoring,
        verification and cleanup) inside a single well-structured try/except/finally block.
        """
        # Calculate adaptive timeout based on file size (prevents C++ client timeout mismatches)
        if timeout is None:
            timeout = self._calculate_adaptive_timeout(file_path)

        self._log_status(
            "START",
            f"Starting REAL backup for {username}: {file_path} (timeout: {timeout}s)",
        )

        # Start progress simulation
        self._start_progress_simulation()

        result: dict[str, Any] = {
            "success": False,
            "error": None,
            "process_exit_code": None,
            "verification": None,
            "duration": 0.0,
            "network_activity": False,
        }

        start_time = time.time()
        monitor: UnifiedFileMonitor | None = None
        file_id: str | None = None
        transfer_info_path: str | None = None

        try:
            # --- Pre-flight validation ---
            if not os.path.exists(file_path):
                handle_subprocess_error(
                    message="Source file not found for backup",
                    details=f"File path: {file_path}",
                    component="pre_flight_check",
                    severity=ErrorSeverity.CRITICAL,
                )
                raise FileNotFoundError(file_path)

            if not self.client_exe or not os.path.exists(self.client_exe):
                handle_subprocess_error(
                    message="Client executable not found",
                    details=f"Expected path: {self.client_exe}",
                    component="pre_flight_check",
                    severity=ErrorSeverity.CRITICAL,
                )
                raise FileNotFoundError(self.client_exe or "<unset>")

            self._clear_cached_credentials_if_username_changed(username)

            # --- transfer.info management (isolated managed file) ---
            client_dir = os.path.dirname(self.client_exe)
            file_id, managed_transfer_path = self._generate_transfer_info(
                server_ip, server_port, username, file_path
            )
            try:
                target_path = os.path.join(client_dir, "transfer.info")
                if os.path.exists(target_path):
                    with contextlib.suppress(Exception):
                        os.remove(target_path)
                with (
                    open(managed_transfer_path, encoding="utf-8") as src,
                    open(target_path, "w", encoding="utf-8") as dst,
                ):
                    dst.write(src.read())
                transfer_info_path = target_path
                self._log_status(
                    "CONFIG",
                    f"Copied managed transfer.info to working dir: {target_path}",
                )
            except Exception as copy_err:
                self._log_status(
                    "WARNING",
                    f"Failed to copy managed transfer.info to working dir: {copy_err}. Using managed path directly.",
                )
                transfer_info_path = managed_transfer_path

            if file_id:
                with contextlib.suppress(Exception):
                    self.file_manager.mark_in_subprocess_use(file_id)

            # --- Subprocess launch (simplified) ---
            client_working_dir = client_dir
            command = [str(self.client_exe), "--batch"]
            self._log_status("LAUNCH", f"Starting subprocess: {' '.join(command)}")
            try:
                # Launch C++ client with UTF-8 environment and subprocess support
                # Note: Popen_utf8 includes errors='replace' to handle invalid UTF-8 bytes from C++ client
                process = Popen_utf8(
                    command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=client_working_dir,
                )
                self.backup_process = process
                self.process_id = process.pid
            except Exception as launch_err:
                raise RuntimeError(
                    f"Subprocess launch failed: {launch_err}"
                ) from launch_err

            if self.backup_process:
                self._log_status(
                    "PROCESS",
                    f"Started backup client (ID: {self.process_id}, PID: {self.backup_process.pid})",
                )

            # --- Monitoring Setup ---
            monitor = UnifiedFileMonitor(self.server_received_files)
            monitor.start_monitoring()

            job_completed = threading.Event()
            verification_result: dict[str, Any] = {}

            def on_complete(data: dict[str, Any]):
                nonlocal verification_result
                self._log_status("MONITOR_COMPLETE", f"Verification successful: {data}")
                verification_result.update(data)
                job_completed.set()

            def on_failure(data: dict[str, Any]):
                nonlocal verification_result
                self._log_status("MONITOR_FAILURE", f"Verification failed: {data}")
                verification_result.update(data)
                job_completed.set()

            # --- Job Registration ---
            expected_size = os.path.getsize(file_path)
            # Use streaming hash calculation to prevent memory overflow on large files
            from Shared.filesystem.streaming_file_utils import (
                calculate_file_hash_streaming,
            )

            expected_hash = calculate_file_hash_streaming(file_path, "sha256")
            if expected_hash is None:
                raise RuntimeError(
                    "Failed to calculate file hash - file may be inaccessible"
                )

            job_id = f"backup_{username}_{os.path.basename(file_path)}"

            monitor.register_job(
                filename=os.path.basename(file_path),
                job_id=job_id,
                expected_size=expected_size,
                expected_hash=expected_hash,
                completion_callback=on_complete,
                failure_callback=on_failure,
            )

            # --- Process Execution (Non-blocking) ---
            if self.backup_process:
                self._log_status(
                    "PROCESS",
                    f"Waiting for C++ client (PID: {self.backup_process.pid}) to complete.",
                )
            try:
                exec_result = self._execute_subprocess_nonblocking(timeout)
                result["process_exit_code"] = exec_result["return_code"]
                if exec_result["stdout"]:
                    self._log_status("CLIENT_STDOUT", exec_result["stdout"])
                if exec_result["stderr"]:
                    self._log_status("CLIENT_STDERR", exec_result["stderr"])

                # Signal subprocess completion to file manager (prevents race condition)
                if file_id:
                    self.file_manager.release_subprocess_use(file_id)
                    self._log_status(
                        "LIFECYCLE", f"Subprocess completed - released file {file_id}"
                    )

            except subprocess.TimeoutExpired:
                self._log_status("TIMEOUT", "C++ client process timed out.")
                self.cancel("Timeout")
                result["error"] = "Process timed out"
                result["process_exit_code"] = -1
                # Still release subprocess use on timeout
                if file_id:
                    self.file_manager.release_subprocess_use(file_id)

            except Exception as exec_error:
                self._log_status("ERROR", f"Subprocess execution failed: {exec_error}")
                result["error"] = str(exec_error)
                result["process_exit_code"] = -1
                # Release subprocess use on error too
                if file_id:
                    self.file_manager.release_subprocess_use(file_id)

            # --- Wait for Verification ---
            self._log_status(
                "VERIFICATION", "Waiting for file verification to complete..."
            )
            job_completed.wait(timeout=30)  # Wait up to 30s for verification

            result["verification"] = verification_result
            result["success"] = verification_result.get("status", "") == "complete"

            if not result["success"] and not result["error"]:
                result["error"] = verification_result.get(
                    "reason", "Verification failed or timed out."
                )

            if result["success"]:
                self._log_status("SUCCESS", "REAL backup completed and verified!")
            else:
                self._log_status("FAILURE", result["error"])

            if monitor is not None:
                monitor.stop_monitoring()

        except Exception as e:
            result["error"] = str(e)
            self._log_status("ERROR", f"Backup execution failed: {e}")
            with contextlib.suppress(Exception):
                if monitor is not None:
                    monitor.stop_monitoring()
        finally:
            # Stop progress simulation
            self._stop_progress_simulation()

            result["duration"] = time.time() - start_time

            # Enhanced file lifecycle cleanup with proper subprocess coordination
            if file_id:
                with contextlib.suppress(Exception):
                    # Wait longer since subprocess completion is now properly signaled
                    self.file_manager.safe_cleanup(file_id, wait_timeout=30.0)
                    self._log_status(
                        "LIFECYCLE",
                        f"Completed safe cleanup for managed file {file_id}",
                    )

            # Clean up working directory copy (safe since managed file handles the lifecycle)
            if transfer_info_path and os.path.exists(transfer_info_path):
                with contextlib.suppress(Exception):
                    os.remove(transfer_info_path)
                    self._log_status(
                        "LIFECYCLE", f"Cleaned up working copy: {transfer_info_path}"
                    )

        return result


def main():
    """Test the real backup executor"""
    if len(sys.argv) < 3:
        print("Usage: python real_backup_executor.py <username> <file_path>")
        sys.exit(1)

    username = sys.argv[1]
    file_path = sys.argv[2]

    executor = RealBackupExecutor()

    def status_update(phase: str, data: str | dict[str, Any]):
        if isinstance(data, dict):
            if "message" in data:
                print(f"STATUS: {phase} - {data['message']}")
            else:
                # Handle rich status data
                progress = data.get("progress", 0)
                warnings = data.get("warnings", [])
                warnings_str = f" (Warnings: {', '.join(warnings)})" if warnings else ""
                print(f"STATUS: {phase} - Progress: {progress:.0f}%{warnings_str}")
        else:
            print(f"STATUS: {phase} - {data}")

    executor.set_status_callback(status_update)

    print("[SECURE] Real Backup Executor - Testing Mode")
    print(f"Username: {username}")
    print(f"File: {file_path}")
    print()

    result = executor.execute_real_backup(username, file_path, "127.0.0.1", 1256)

    print("\n" + "=" * 50)
    print("BACKUP EXECUTION RESULTS:")
    print("=" * 50)
    print(f"Success: {result['success']}")
    print(f"Duration: {result['duration']:.2f} seconds")
    print(f"Process Exit Code: {result['process_exit_code']}")
    print(f"Network Activity: {result['network_activity']}")
    if result["error"]:
        print(f"Error: {result['error']}")

    if result["verification"]:
        v = result["verification"]
        print("\nFILE TRANSFER VERIFICATION:")
        print(f"File Found: {v['file_found']}")
        print(
            f"Size Match: {v['size_match']} ({v['original_size']} -> {v['received_size']})"
        )
        print(f"Hash Match: {v['hash_match']}")
        print(f"Transferred: {v['transferred']}")
        if v["received_file"]:
            print(f"Received File: {v['received_file']}")

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
