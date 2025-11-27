"""
GUI Integration for Enhanced Process Monitoring
Provides visual components for displaying process metrics and health status.
"""

import logging
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import Any

from .process_monitor import ProcessMetrics, ProcessState, get_process_registry

logger = logging.getLogger(__name__)


class ProcessMonitorWidget:
    """Widget for displaying process monitoring information"""

    def __init__(
        self, parent: Any, title: str = "Process Monitor", update_interval: float = 2.0
    ) -> None:
        self.parent = parent
        self.title = title
        self.update_interval = update_interval
        self.running = False
        self.update_thread: threading.Thread | None = None

        # Create the main frame
        self.frame = ttk.LabelFrame(parent, text=title, padding="10")

        # Create the UI components
        self._create_widgets()

        # Start the update loop
        self.start_monitoring()

    def _create_widgets(self) -> None:
        """Create the UI widgets"""
        # Process list frame
        list_frame = ttk.Frame(self.frame)
        list_frame.pack(fill="both", expand=True, pady=(0, 10))

        # Process list with scrollbar
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill="both", expand=True)

        # Treeview for process list
        columns = ("Name", "State", "PID", "CPU%", "Memory MB", "Threads", "Warnings")
        self.process_tree = ttk.Treeview(
            list_container, columns=columns, show="headings", height=8
        )

        # Configure column headings and widths
        for col in columns:
            self.process_tree.heading(col, text=col)
            if col == "Name":
                self.process_tree.column(col, width=150)
            elif col == "State":
                self.process_tree.column(col, width=80)
            elif col == "PID":
                self.process_tree.column(col, width=60)
            elif col == "CPU%":
                self.process_tree.column(col, width=60)
            elif col == "Memory MB":
                self.process_tree.column(col, width=80)
            elif col == "Threads":
                self.process_tree.column(col, width=60)
            elif col == "Warnings":
                self.process_tree.column(col, width=200)

        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(
            list_container, orient="vertical", command=self.process_tree.yview
        )  # type: ignore
        self.process_tree.configure(yscrollcommand=scrollbar.set)

        # Pack treeview and scrollbar
        self.process_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Status frame
        status_frame = ttk.Frame(self.frame)
        status_frame.pack(fill="x", pady=(10, 0))

        # Status labels
        self.status_label = ttk.Label(status_frame, text="Monitoring: 0 processes")
        self.status_label.pack(side="left")

        self.last_update_label = ttk.Label(status_frame, text="Last update: Never")
        self.last_update_label.pack(side="right")

        # Control buttons
        button_frame = ttk.Frame(self.frame)
        button_frame.pack(fill="x", pady=(10, 0))

        self.refresh_button = ttk.Button(
            button_frame, text="Refresh", command=self.refresh_now
        )
        self.refresh_button.pack(side="left", padx=(0, 5))

        self.clear_button = ttk.Button(
            button_frame, text="Clear", command=self.clear_display
        )
        self.clear_button.pack(side="left")

    def start_monitoring(self) -> None:
        """Start the monitoring update loop"""
        if not self.running:
            self.running = True
            self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
            self.update_thread.start()
            logger.info("Process monitor widget started")

    def stop_monitoring(self) -> None:
        """Stop the monitoring update loop"""
        self.running = False
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=5)
        logger.info("Process monitor widget stopped")

    def _update_loop(self) -> None:
        """Main update loop running in background thread"""
        while self.running:
            try:
                # Schedule GUI update on main thread
                self.parent.after(0, self._update_display)
                time.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error in process monitor update loop: {e}")
                time.sleep(5)

    def _update_display(self) -> None:
        """Update the display with current process information"""
        try:
            registry = get_process_registry()
            processes = registry.get_all_processes()

            # Clear existing items
            for item in self.process_tree.get_children():
                self.process_tree.delete(item)

            # Add current processes
            running_count = 0
            for _, process_info in processes.items():
                # Get latest metrics if available
                metrics = None
                if process_info.metrics_history:
                    metrics = process_info.metrics_history[-1]

                # Determine display values
                name = process_info.name
                state = process_info.state.value
                pid = str(process_info.pid) if process_info.pid else "N/A"

                if metrics:
                    cpu_percent = f"{metrics.cpu_percent:.1f}"
                    memory_mb = f"{metrics.memory_mb:.1f}"
                    threads = str(metrics.num_threads)
                    warnings = (
                        "; ".join(metrics.warnings) if metrics.warnings else "None"
                    )
                else:
                    cpu_percent = "N/A"
                    memory_mb = "N/A"
                    threads = "N/A"
                    warnings = "No metrics"

                # Add to tree
                item_id = self.process_tree.insert(
                    "",
                    "end",
                    values=(
                        name,
                        state,
                        pid,
                        cpu_percent,
                        memory_mb,
                        threads,
                        warnings,
                    ),
                )

                # Color code by state
                if process_info.state == ProcessState.RUNNING:
                    running_count += 1
                    self.process_tree.set(item_id, "State", "🟢 " + state)
                elif process_info.state == ProcessState.FAILED:
                    self.process_tree.set(item_id, "State", "🔴 " + state)
                elif process_info.state == ProcessState.STOPPING:
                    self.process_tree.set(item_id, "State", "🟡 " + state)
                else:
                    self.process_tree.set(item_id, "State", "⚪ " + state)

                # Highlight warnings
                if metrics and metrics.warnings:
                    self.process_tree.set(item_id, "Warnings", "⚠️ " + warnings)

            # Update status
            total_count = len(processes)
            self.status_label.config(
                text=f"Monitoring: {running_count}/{total_count} processes"
            )
            self.last_update_label.config(
                text=f"Last update: {datetime.now().strftime('%H:%M:%S')}"
            )

        except Exception as e:
            logger.error(f"Error updating process monitor display: {e}")
            self.status_label.config(text=f"Error: {e}")

    def refresh_now(self) -> None:
        """Force an immediate refresh"""
        self._update_display()

    def clear_display(self) -> None:
        """Clear the display"""
        for item in self.process_tree.get_children():
            self.process_tree.delete(item)
        self.status_label.config(text="Display cleared")
        self.last_update_label.config(text="Last update: Never")

    def pack(self, **kwargs: Any) -> None:
        """Pack the widget"""
        self.frame.pack(**kwargs)

    def grid(self, **kwargs: Any) -> None:
        """Grid the widget"""
        self.frame.grid(**kwargs)

    def destroy(self) -> None:
        """Destroy the widget and stop monitoring"""
        self.stop_monitoring()
        self.frame.destroy()


class ProcessMetricsChart:
    """Chart widget for displaying process metrics over time"""

    def __init__(
        self, parent: Any, process_id: str, title: str = "Process Metrics"
    ) -> None:
        self.parent = parent
        self.process_id = process_id
        self.title = title

        # Create the main frame
        self.frame = ttk.LabelFrame(parent, text=title, padding="10")

        # Metrics data storage with proper typing
        self.timestamps: list[datetime] = []
        self.cpu_percent: list[float] = []
        self.memory_mb: list[float] = []
        self.threads: list[int] = []

        self.metrics_data: dict[str, Any] = {
            "timestamps": self.timestamps,
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "threads": self.threads,
        }

        # Create the UI
        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create the chart widgets"""
        # Info frame
        info_frame = ttk.Frame(self.frame)
        info_frame.pack(fill="x", pady=(0, 10))

        self.process_label = ttk.Label(info_frame, text=f"Process: {self.process_id}")
        self.process_label.pack(side="left")

        self.status_label = ttk.Label(info_frame, text="Status: Unknown")
        self.status_label.pack(side="right")

        # Metrics display frame
        metrics_frame = ttk.Frame(self.frame)
        metrics_frame.pack(fill="both", expand=True)

        # Current metrics labels
        current_frame = ttk.LabelFrame(
            metrics_frame, text="Current Metrics", padding="5"
        )
        current_frame.pack(fill="x", pady=(0, 10))

        self.cpu_label = ttk.Label(current_frame, text="CPU: N/A")
        self.cpu_label.grid(row=0, column=0, sticky="w", padx=(0, 20))

        self.memory_label = ttk.Label(current_frame, text="Memory: N/A")
        self.memory_label.grid(row=0, column=1, sticky="w", padx=(0, 20))

        self.threads_label = ttk.Label(current_frame, text="Threads: N/A")
        self.threads_label.grid(row=0, column=2, sticky="w")

        # Simple text-based chart (could be enhanced with matplotlib)
        chart_frame = ttk.LabelFrame(metrics_frame, text="Metrics History", padding="5")
        chart_frame.pack(fill="both", expand=True)

        self.chart_text = tk.Text(chart_frame, height=10, width=60, font=("Courier", 9))
        chart_scrollbar = ttk.Scrollbar(
            chart_frame, orient="vertical", command=self.chart_text.yview
        )  # type: ignore
        self.chart_text.configure(yscrollcommand=chart_scrollbar.set)

        self.chart_text.pack(side="left", fill="both", expand=True)
        chart_scrollbar.pack(side="right", fill="y")

    def update_metrics(self) -> None:
        """Update the metrics display"""
        try:
            registry = get_process_registry()
            process_info = registry.get_process_info(self.process_id)

            if not process_info:
                self.status_label.config(text="Status: Process not found")
                return

            # Update status
            self.status_label.config(text=f"Status: {process_info.state.value}")

            # Get latest metrics
            if process_info.metrics_history:
                latest = process_info.metrics_history[-1]

                # Update current metrics labels
                self.cpu_label.config(text=f"CPU: {latest.cpu_percent:.1f}%")
                self.memory_label.config(text=f"Memory: {latest.memory_mb:.1f}MB")
                self.threads_label.config(text=f"Threads: {latest.num_threads}")

                # Update chart data
                self._update_chart_data(latest)
            else:
                self.cpu_label.config(text="CPU: N/A")
                self.memory_label.config(text="Memory: N/A")
                self.threads_label.config(text="Threads: N/A")

        except Exception as e:
            logger.error(f"Error updating process metrics chart: {e}")
            self.status_label.config(text=f"Error: {e}")

    def _update_chart_data(self, metrics: ProcessMetrics) -> None:
        """Update the chart with new metrics data"""
        # Add new data point
        # Store metrics data in methods that use the typed lists directly
        self.timestamps.append(metrics.timestamp)
        self.cpu_percent.append(metrics.cpu_percent)
        self.memory_mb.append(metrics.memory_mb)
        self.threads.append(metrics.num_threads)

        # Keep only last 50 data points
        max_points = 50
        for data_list in [
            self.timestamps,
            self.cpu_percent,
            self.memory_mb,
            self.threads,
        ]:
            if len(data_list) > max_points:
                data_list[:] = data_list[-max_points:]

        # Update text chart
        self._render_text_chart()

    def _render_text_chart(self) -> None:
        """Render a simple text-based chart"""
        self.chart_text.delete(1.0, tk.END)

        if not self.timestamps:
            self.chart_text.insert(tk.END, "No data available")
            return

        # Create simple text chart
        lines: list[str] = []
        lines.append("Time        CPU%   Memory(MB)  Threads")
        lines.append("-" * 40)

        for i in range(len(self.timestamps)):
            timestamp = self.timestamps[i]
            cpu = self.cpu_percent[i]
            memory = self.memory_mb[i]
            threads = self.threads[i]

            time_str = timestamp.strftime("%H:%M:%S")
            line = f"{time_str}  {cpu:5.1f}  {memory:8.1f}  {threads:7d}"
            lines.append(line)

        # Show only last 20 lines
        display_lines = lines[-22:]  # Include header
        self.chart_text.insert(tk.END, "\n".join(display_lines))

        # Scroll to bottom
        self.chart_text.see(tk.END)

    def pack(self, **kwargs: Any) -> None:
        """Pack the widget"""
        self.frame.pack(**kwargs)

    def grid(self, **kwargs: Any) -> None:
        """Grid the widget"""
        self.frame.grid(**kwargs)

    def destroy(self) -> None:
        """Destroy the widget"""
        self.frame.destroy()


def create_process_monitor_tab(
    notebook: Any, title: str = "Process Monitor"
) -> tuple[Any, ProcessMonitorWidget]:
    """Create a process monitor tab for a notebook widget"""
    # Create tab frame
    tab_frame = ttk.Frame(notebook)
    notebook.add(tab_frame, text=title)

    # Create main container with scrollable area
    canvas = tk.Canvas(tab_frame)
    scrollbar = ttk.Scrollbar(tab_frame, orient="vertical", command=canvas.yview)  # type: ignore
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    # Pack canvas and scrollbar
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Create process monitor widget
    monitor_widget = ProcessMonitorWidget(scrollable_frame, title="Active Processes")
    monitor_widget.pack(fill="both", expand=True, pady=(0, 20))

    return tab_frame, monitor_widget
