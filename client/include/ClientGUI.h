#pragma once

// These helpers are intended to be available even if the full _WIN32 GUI is not.
// Their declarations should NOT be inside #ifdef _WIN32
#include <string> // For std::string used in helpers

/**
 * @brief Initializes the client application's graphical user interface.
 *
 * @return true if the GUI was successfully initialized, false otherwise.
 */
 
/**
 * @brief Shuts down the client application's graphical user interface and releases related resources.
 */
 
/**
 * @brief Updates the GUI to display the current operational phase.
 *
 * @param phase Description of the current phase.
 */
 
/**
 * @brief Updates the GUI to reflect the current operation, including its status and optional details.
 *
 * @param operation Name or description of the operation.
 * @param success Indicates whether the operation succeeded.
 * @param details Optional additional information about the operation.
 */
 
/**
 * @brief Updates the GUI with progress information for an ongoing task.
 *
 * @param current Current progress value.
 * @param total Total value representing completion.
 * @param speed Optional string indicating current speed.
 * @param eta Optional string indicating estimated time remaining.
 */
 
/**
 * @brief Updates the GUI to indicate the application's connection status.
 *
 * @param connected true if connected, false if disconnected.
 */
 
/**
 * @brief Displays an error message in the GUI.
 *
 * @param message The error message to display.
 */
 
/**
 * @brief Shows a notification to the user with a title and message.
 *
 * @param title The notification title.
 * @param message The notification message content.
 */
namespace ClientGUIHelpers {
    bool initializeGUI();
    void shutdownGUI();
    void updatePhase(const std::string& phase);
    void updateOperation(const std::string& operation, bool success = true, const std::string& details = "");
    void updateProgress(int current, int total, const std::string& speed = "", const std::string& eta = "");
    void updateConnectionStatus(bool connected);
    void updateError(const std::string& message);
    void showNotification(const std::string& title, const std::string& message);
} // namespace ClientGUIHelpers


#ifdef _WIN32 // The ClientGUI class itself IS Windows-specific

#include <windows.h>
#include <thread>
#include <atomic>
#include <memory>
#include <shellapi.h>

// Custom Window Messages
#define WM_TRAYICON         (WM_APP + 1)
#define WM_STATUS_UPDATE    (WM_APP + 2)

// Context Menu Command IDs
#define ID_SHOW_STATUS      1001
#define ID_SHOW_CONSOLE     1002
#define ID_EXIT             1003

struct GUIStatus {
    std::string phase;
    std::string operation;
    std::string details;
    std::string error;
    std::string speed;
    std::string eta;
    bool connected;
    bool success;
    int progress;
    int totalProgress;

    GUIStatus() : connected(false), success(true), progress(0), totalProgress(0) {}
};

class ClientGUI {
public:
    static ClientGUI* getInstance();
    bool initialize();
    void shutdown();
    void updatePhase(const std::string& phase);
    void updateOperation(const std::string& operation, bool success = true, const std::string& details = "");
    void updateProgress(int current, int total, const std::string& speed = "", const std::string& eta = "");
    void updateConnectionStatus(bool connected);
    void updateError(const std::string& error);
    void showNotification(const std::string& title, const std::string& message, DWORD iconType = 0x00000001L /*NIIF_INFO*/);
    void showPopup(const std::string& title, const std::string& message, UINT type = 0x00000000L /*MB_OK*/);
    void toggleStatusWindow();
    void showStatusWindow(bool show);
    void toggleConsoleWindow();
    void showConsoleWindow(bool show);

private:
    ClientGUI();
    ~ClientGUI();
    ClientGUI(const ClientGUI&) = delete;
    ClientGUI& operator=(const ClientGUI&) = delete;
    void guiMessageLoop();
    std::thread guiThread;
    std::atomic<bool> shouldClose;
    HWND statusWindow;
    HWND hTrayWnd_;
    HWND consoleWindow;
    static LRESULT CALLBACK StatusWindowProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam);
    static LRESULT CALLBACK TrayWindowProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam);
    bool initializeTrayIcon();
    bool createStatusWindow();
    void showContextMenu(POINT pt);
    void updateStatusWindow();
    void cleanup();
    std::atomic<bool> guiInitialized;
    std::atomic<bool> statusWindowVisible;
    CRITICAL_SECTION statusLock;
    GUIStatus currentStatus;
    NOTIFYICONDATAW trayIcon;
};

#endif // _WIN32