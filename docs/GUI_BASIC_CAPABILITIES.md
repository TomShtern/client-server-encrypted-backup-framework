# GUI Basic Capabilities

## Overview
This document summarizes the basic capabilities, integration details, and design decisions for the GUI components of the Encrypted Backup Framework, as discussed and implemented in this project. It is intended as a reference for agents or developers who need to understand the GUI's role, how it works, and how it was integrated into the system.

---

## 1. Server GUI (Python, tkinter)

### Core Capabilities
- **Real-time Dashboard:** Displays server status, client statistics, transfer statistics, and maintenance information.
- **System Tray Integration:** Uses `pystray` and `Pillow` to provide a tray icon with menu actions (show/hide, exit, etc.).
- **Thread-Safe Updates:** All updates to the GUI are queued and processed in the GUI thread, ensuring thread safety.
- **Status Sections:**
  - Server status (running/stopped, address, uptime)
  - Client stats (connected, total, active transfers)
  - Transfer stats (bytes transferred, last activity)
  - Maintenance stats (files cleaned, partials cleaned, clients cleaned, last cleanup)
  - Error/success/info messages
- **Control Buttons:** Hide window, show console (stub), exit server.
- **Popup Notifications:** Info and error popups via `messagebox`.
- **Graceful Fallback:** If optional dependencies (pystray, Pillow) are missing, tray features are disabled but the main GUI still works.

### Design Decisions & Changes
- **Window Visibility:**
  - Originally, the window started hidden (`self.root.withdraw()`).
  - Changed to show the window by default for better user experience.
- **System Tray:**
  - Tray icon and menu are created in a background thread if dependencies are available.
  - Tray menu allows showing/hiding the main window and exiting the server.
- **Threading:**
  - The GUI runs in its own thread (`self.gui_thread`).
  - All updates from the server are placed in a `queue.Queue` and processed in the GUI thread.
- **Error Handling:**
  - All GUI operations are wrapped in try/except blocks to prevent crashes from propagating to the server.
- **API for Server Integration:**
  - Helper functions (`update_server_status`, `update_client_stats`, etc.) allow the server to update the GUI from any thread.
- **Testing:**
  - The file can be run standalone to test GUI features without the server.

### Integration Points
- **Server Startup:** GUI is initialized in the server's constructor. If initialization fails, the server continues in console mode.
- **Server Events:** All major server events (start, stop, client connect/disconnect, file transfer, maintenance) trigger GUI updates.
- **Shutdown:** GUI is shut down gracefully when the server exits.

---

## 2. Client GUI (C++/Windows, not shown here)
- **Native Windows GUI:** Provides a window for file selection, backup progress, and status.
- **System Tray:** May minimize to tray (behavior similar to server GUI).
- **Status/Progress:** Shows connection status, transfer progress, and notifications.
- **Build/Run:** Built with MSVC, run as `EncryptedBackupClient.exe`.

---

## 3. Key Changes Made (Why & What)
- **Window Visibility Fix:**
  - Users reported not seeing the server GUI window. The code was changed to show the window by default (removed `self.root.withdraw()`).
- **Type Safety:**
  - Type hints and queue update types were improved for better static analysis and robustness.
- **Sticky Parameter Fix:**
  - Fixed tkinter `sticky` parameters to use strings (e.g., "ew") instead of tuples, for compatibility.
- **Graceful Degradation:**
  - If tray dependencies are missing, the GUI still works (tray is just disabled).
- **Testing Script:**
  - A Python test script was created to exercise all GUI update functions for manual and automated testing.

---

## 4. Troubleshooting & Usage
- **If GUI Window Is Not Visible:**
  - Ensure the process is running (check Task Manager).
  - The window should now appear by default; if not, check for errors in the console.
  - If minimized to tray, use the tray icon to restore.
- **Dependencies:**
  - `tkinter` (built-in), `pystray`, `Pillow` (optional, for tray icon).
- **Running Standalone:**
  - Run `python ServerGUI.py` to test the GUI without the server.
- **Integration:**
  - The server will automatically use the GUI if available; otherwise, it runs in console mode.

---

## 5. Reference: Example API Usage
```python
from ServerGUI import (
    initialize_server_gui, shutdown_server_gui, update_server_status,
    update_client_stats, update_transfer_stats, update_maintenance_stats,
    show_server_error, show_server_success, show_server_notification
)

initialize_server_gui()
update_server_status(True, "127.0.0.1", 8080)
update_client_stats(connected=2, total=5, active_transfers=1)
update_transfer_stats(bytes_transferred=1024*1024*50)
show_server_success("Backup completed!")
shutdown_server_gui()
```

---

## 6. Summary
- The GUI provides a robust, user-friendly, and thread-safe interface for monitoring and controlling the encrypted backup server.
- All major server events are reflected in the GUI in real time.
- The design is modular, resilient to missing dependencies, and easy to extend.
- This document should be referenced by any agent or developer working on GUI-related features or troubleshooting GUI issues in this project.
