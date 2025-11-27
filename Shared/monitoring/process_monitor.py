"""
Enhanced Subprocess Monitoring System
Provides centralized process registry, real-time metrics, and automated recovery.
"""

import logging
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import psutil

from Shared.logging.error_handler import ErrorSeverity, handle_subprocess_error

logger = logging.getLogger(__name__)


class ProcessState(Enum):
    """Process state enumeration"""

    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class ProcessMetrics:
    """Real-time process metrics"""

    timestamp: datetime
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    num_threads: int
    open_files: int
    connections: int
    io_read_bytes: int
    io_write_bytes: int
    status: str
    is_responsive: bool
    warnings: list[str] = field(default_factory=list)


@dataclass
class ProcessInfo:
    """Comprehensive process information"""

    process_id: str
    name: str
    command: list[str]
    cwd: str
    state: ProcessState
    start_time: datetime
    pid: int | None = None
    end_time: datetime | None = None
    exit_code: int | None = None
    restart_count: int = 0
    max_restarts: int = 3
    auto_restart: bool = False
    health_check_interval: float = 2.0
    metrics_history: deque[ProcessMetrics] = field(
        default_factory=lambda: deque(maxlen=100)
    )
    last_health_check: datetime | None = None
    error_count: int = 0
    last_error: str | None = None


class ProcessRegistry:
    """Centralized registry for all monitored processes"""

    def __init__(self):
        self.processes: dict[str, ProcessInfo] = {}
        self.subprocess_handles: dict[str, subprocess.Popen[str]] = {}
        self.monitoring_threads: dict[str, threading.Thread] = {}
        self.lock = threading.RLock()
        self.running = True

        # Start the main monitoring loop
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop, daemon=True
        )
        self.monitor_thread.start()

        logger.info("Process registry initialized")

    def register_process(
        self,
        process_id: str,
        name: str,
        command: list[str],
        cwd: str = ".",
        auto_restart: bool = False,
        max_restarts: int = 3,
    ) -> ProcessInfo:
        """Register a new process for monitoring"""
        with self.lock:
            process_info = ProcessInfo(
                process_id=process_id,
                name=name,
                command=command,
                cwd=cwd,
                state=ProcessState.STARTING,
                start_time=datetime.now(),
                auto_restart=auto_restart,
                max_restarts=max_restarts,
            )

            self.processes[process_id] = process_info
            logger.info(f"Registered process: {process_id} ({name})")
            return process_info

    def start_process(self, process_id: str, **popen_kwargs: Any) -> bool:
        """Start a registered process"""
        with self.lock:
            if process_id not in self.processes:
                logger.error(f"Process {process_id} not registered")
                return False

            process_info = self.processes[process_id]

            try:
                # Default subprocess arguments
                default_kwargs: dict[str, Any] = {
                    "stdout": subprocess.PIPE,
                    "stderr": subprocess.PIPE,
                    "text": True,
                    "encoding": "utf-8",
                    "cwd": process_info.cwd,
                }
                default_kwargs.update(popen_kwargs)

                # Start the subprocess
                popen: subprocess.Popen[str] = subprocess.Popen(
                    process_info.command, **default_kwargs
                )

                self.subprocess_handles[process_id] = popen
                process_info.pid = popen.pid
                process_info.state = ProcessState.RUNNING
                process_info.start_time = datetime.now()

                # Start monitoring thread for this process
                monitor_thread = threading.Thread(
                    target=self._monitor_process, args=(process_id,), daemon=True
                )
                self.monitoring_threads[process_id] = monitor_thread
                monitor_thread.start()

                logger.info(f"Started process: {process_id} (PID: {popen.pid})")
                return True

            except Exception as e:
                process_info.state = ProcessState.FAILED
                process_info.last_error = str(e)
                process_info.error_count += 1

                handle_subprocess_error(
                    message=f"Failed to start process {process_id}",
                    details=f"Command: {process_info.command}, Error: {e}",
                    component="process_registry",
                    severity=ErrorSeverity.HIGH,
                )

                logger.error(f"Failed to start process {process_id}: {e}")
                return False

    def stop_process(self, process_id: str, timeout: float = 10.0) -> bool:
        """Stop a running process gracefully"""
        with self.lock:
            if process_id not in self.subprocess_handles:
                logger.warning(f"Process {process_id} not found in subprocess handles")
                return False

            process_info = self.processes[process_id]
            popen = self.subprocess_handles[process_id]

            try:
                process_info.state = ProcessState.STOPPING

                # Try graceful termination first
                popen.terminate()

                try:
                    exit_code = popen.wait(timeout=timeout)
                    process_info.exit_code = exit_code
                    process_info.state = ProcessState.STOPPED
                    process_info.end_time = datetime.now()

                    logger.info(
                        f"Process {process_id} terminated gracefully (exit code: {exit_code})"
                    )
                    return True

                except subprocess.TimeoutExpired:
                    # Force kill if graceful termination fails
                    logger.warning(
                        f"Process {process_id} did not terminate gracefully, forcing kill"
                    )
                    popen.kill()
                    exit_code = popen.wait(timeout=5.0)
                    process_info.exit_code = exit_code
                    process_info.state = ProcessState.STOPPED
                    process_info.end_time = datetime.now()

                    logger.info(
                        f"Process {process_id} force killed (exit code: {exit_code})"
                    )
                    return True

            except Exception as e:
                process_info.state = ProcessState.FAILED
                process_info.last_error = str(e)
                process_info.error_count += 1

                logger.error(f"Error stopping process {process_id}: {e}")
                return False

            finally:
                # Clean up
                if process_id in self.subprocess_handles:
                    del self.subprocess_handles[process_id]
                if process_id in self.monitoring_threads:
                    del self.monitoring_threads[process_id]

    def get_process_info(self, process_id: str) -> ProcessInfo | None:
        """Get process information"""
        with self.lock:
            return self.processes.get(process_id)

    def get_all_processes(self) -> dict[str, ProcessInfo]:
        """Get all registered processes"""
        with self.lock:
            return self.processes.copy()

    def get_running_processes(self) -> dict[str, ProcessInfo]:
        """Get only running processes"""
        with self.lock:
            return {
                pid: info
                for pid, info in self.processes.items()
                if info.state == ProcessState.RUNNING
            }

    def _monitor_process(self, process_id: str):
        """Monitor a specific process in a dedicated thread"""
        logger.info(f"Starting monitoring for process: {process_id}")

        while self.running:
            try:
                with self.lock:
                    if process_id not in self.processes:
                        break

                    process_info = self.processes[process_id]
                    popen = self.subprocess_handles.get(process_id)

                    if not popen or process_info.state != ProcessState.RUNNING:
                        break

                # Collect metrics
                metrics = self._collect_process_metrics(popen, process_info)
                if metrics:
                    process_info.metrics_history.append(metrics)
                    process_info.last_health_check = datetime.now()

                    # Check for issues and handle them
                    self._handle_process_issues(process_id, metrics)

                # Check if process is still alive
                if popen.poll() is not None:
                    # Process has ended
                    with self.lock:
                        process_info.state = ProcessState.STOPPED
                        process_info.exit_code = popen.poll()
                        process_info.end_time = datetime.now()

                        logger.info(
                            f"Process {process_id} ended with exit code: {popen.poll()}"
                        )

                        # Handle auto-restart if enabled
                        if (
                            process_info.auto_restart
                            and process_info.restart_count < process_info.max_restarts
                        ):
                            self._restart_process(process_id)

                    break

                time.sleep(process_info.health_check_interval)

            except Exception as e:
                logger.error(f"Error monitoring process {process_id}: {e}")
                time.sleep(5)  # Wait before retrying

        logger.info(f"Stopped monitoring process: {process_id}")

    def _collect_process_metrics(
        self, popen: subprocess.Popen[str], process_info: ProcessInfo
    ) -> ProcessMetrics | None:
        """Collect comprehensive process metrics"""
        try:
            proc = psutil.Process(popen.pid)

            # Get I/O counters
            io_counters = proc.io_counters()

            metrics = ProcessMetrics(
                timestamp=datetime.now(),
                cpu_percent=proc.cpu_percent(interval=0.1),
                memory_mb=proc.memory_info().rss / 1024 / 1024,
                memory_percent=proc.memory_percent(),
                num_threads=proc.num_threads(),
                open_files=len(proc.open_files()),
                connections=len(proc.connections()),
                io_read_bytes=io_counters.read_bytes,
                io_write_bytes=io_counters.write_bytes,
                status=proc.status(),
                is_responsive=True,  # Will be updated by health checks
            )

            # Detect warnings
            metrics.warnings = self._detect_process_warnings(metrics)
            metrics.is_responsive = self._check_process_responsiveness(metrics)

            return metrics

        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.warning(
                f"Failed to collect metrics for process {process_info.name}: {e}"
            )
            return None

    def _detect_process_warnings(self, metrics: ProcessMetrics) -> list[str]:
        """Detect warning conditions from process metrics"""
        warnings: list[str] = []

        if metrics.cpu_percent > 90:
            warnings.append(f"High CPU usage: {metrics.cpu_percent:.1f}%")

        if metrics.memory_mb > 1000:  # 1GB
            warnings.append(f"High memory usage: {metrics.memory_mb:.1f}MB")

        if metrics.open_files > 100:
            warnings.append(f"Many open files: {metrics.open_files}")

        if metrics.num_threads > 50:
            warnings.append(f"Many threads: {metrics.num_threads}")

        return warnings

    def _check_process_responsiveness(self, metrics: ProcessMetrics) -> bool:
        """Check if process appears responsive"""
        # High CPU with very few threads might indicate hanging
        if metrics.cpu_percent > 95 and metrics.num_threads <= 1:
            return False

        # Process in uninterruptible sleep for too long
        if metrics.status == "disk-sleep":
            return False

        return True

    def _handle_process_issues(self, process_id: str, metrics: ProcessMetrics):
        """Handle detected process issues"""
        process_info = self.processes[process_id]

        # Report warnings to error framework
        if metrics.warnings:
            warning_msg = "; ".join(metrics.warnings)
            handle_subprocess_error(
                message=f"Process {process_id} health warning",
                details=f"Warnings: {warning_msg}",
                component="process_monitoring",
                severity=ErrorSeverity.MEDIUM,
            )

        # Handle unresponsive process
        if not metrics.is_responsive:
            process_info.error_count += 1
            handle_subprocess_error(
                message=f"Process {process_id} appears unresponsive",
                details=f"Metrics: CPU={metrics.cpu_percent:.1f}%, Threads={metrics.num_threads}, Status={metrics.status}",
                component="process_health",
                severity=ErrorSeverity.HIGH,
            )

    def _restart_process(self, process_id: str):
        """Restart a failed process"""
        process_info = self.processes[process_id]
        process_info.restart_count += 1

        logger.info(
            f"Restarting process {process_id} (attempt {process_info.restart_count}/{process_info.max_restarts})"
        )

        # Wait a bit before restarting
        time.sleep(2)

        # Start the process again
        if self.start_process(process_id):
            logger.info(f"Successfully restarted process {process_id}")
        else:
            logger.error(f"Failed to restart process {process_id}")

    def _monitoring_loop(self):
        """Main monitoring loop for registry-level tasks"""
        while self.running:
            try:
                # Perform registry-level monitoring tasks
                self._cleanup_dead_processes()
                self._log_registry_status()

                time.sleep(30)  # Run every 30 seconds

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(10)

    def _cleanup_dead_processes(self):
        """Clean up processes that are no longer running"""
        with self.lock:
            dead_processes: list[str] = []

            for process_id, process_info in self.processes.items():
                if (
                    process_info.state == ProcessState.STOPPED
                    and process_info.end_time
                    and datetime.now() - process_info.end_time > timedelta(hours=1)
                ):
                    dead_processes.append(process_id)

            for process_id in dead_processes:
                logger.info(f"Cleaning up old process record: {process_id}")
                del self.processes[process_id]

    def _log_registry_status(self):
        """Log overall registry status"""
        with self.lock:
            total = len(self.processes)
            running = len(
                [p for p in self.processes.values() if p.state == ProcessState.RUNNING]
            )
            failed = len(
                [p for p in self.processes.values() if p.state == ProcessState.FAILED]
            )

            logger.debug(
                f"Process registry status: {running} running, {failed} failed, {total} total"
            )

    def shutdown(self):
        """Shutdown the process registry"""
        logger.info("Shutting down process registry")
        self.running = False

        # Stop all running processes
        with self.lock:
            for process_id in list(self.subprocess_handles.keys()):
                self.stop_process(process_id)

        # Wait for monitoring thread to finish
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=10)


# Global process registry instance
_process_registry = None


def get_process_registry() -> ProcessRegistry:
    """Get the global process registry instance"""
    global _process_registry
    if _process_registry is None:
        _process_registry = ProcessRegistry()
    return _process_registry


def register_process(
    process_id: str, name: str, command: list[str], **kwargs
) -> ProcessInfo:
    """Convenience function to register a process"""
    return get_process_registry().register_process(process_id, name, command, **kwargs)


def start_process(process_id: str, **kwargs) -> bool:
    """Convenience function to start a process"""
    return get_process_registry().start_process(process_id, **kwargs)


def stop_process(process_id: str, **kwargs) -> bool:
    """Convenience function to stop a process"""
    return get_process_registry().stop_process(process_id, **kwargs)


def get_process_metrics(process_id: str) -> list[ProcessMetrics] | None:
    """Get process metrics history"""
    registry = get_process_registry()
    process_info = registry.get_process_info(process_id)
    if process_info:
        return list(process_info.metrics_history)
    return None
