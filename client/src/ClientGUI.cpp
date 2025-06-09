// ClientGUI.cpp
#include "ClientGUI.h" // Use the correct header for declarations

// For std::wstring conversions used in ClientGUI class, and potentially by complex helpers
#include <sstream> 
#include <iomanip> 

// *** ClientGUIHelpers implementations are OUTSIDE _WIN32 block ***
// These are the stubs that should always be available for linking.
namespace ClientGUIHelpers {
    /**
     * @brief Initializes the graphical user interface for the client application.
     *
     * On Windows, starts the GUI thread and creates necessary windows and tray icon. On other platforms, this function is a stub and returns true.
     * @return true if the GUI was successfully initialized or not required; false if initialization failed on Windows.
     */
    bool initializeGUI() { 
        #ifdef _WIN32
            // If on Windows, delegate to the actual GUI implementation
            return ClientGUI::getInstance() ? ClientGUI::getInstance()->initialize() : false; 
        #else
            // On other platforms, this is just a stub
            return true; // Or false, depending on desired default behavior
        #endif
    }
    /**
     * @brief Shuts down the GUI client and cleans up associated resources.
     *
     * On Windows, this signals the GUI thread to exit and removes GUI elements such as the tray icon and status window. On other platforms, this function does nothing.
     */
    void shutdownGUI() {
        #ifdef _WIN32
            if(ClientGUI::getInstance()) ClientGUI::getInstance()->shutdown();
        #else
            // Stub
        #endif
    }
    /**
     * @brief Updates the current phase displayed in the GUI.
     *
     * Sets the phase string shown in the status window and tray tooltip, if the GUI is available.
     *
     * @param phase The new phase description to display.
     */
    void updatePhase(const std::string& phase) { // Added const std::string& for parameter names
        #ifdef _WIN32
            if(ClientGUI::getInstance()) ClientGUI::getInstance()->updatePhase(phase);
        #else
            // Stub
        #endif
    }
    /**
     * @brief Updates the GUI with the current operation status.
     *
     * Reflects the specified operation, its success state, and additional details in the GUI status display.
     */
    void updateOperation(const std::string& operation, bool success, const std::string& details) { // Added names
        #ifdef _WIN32
            if(ClientGUI::getInstance()) ClientGUI::getInstance()->updateOperation(operation, success, details);
        #else
            // Stub
        #endif
    }
    /**
     * @brief Updates the GUI with the current progress, speed, and estimated time remaining.
     *
     * @param current The current progress value.
     * @param total The total value representing completion.
     * @param speed The current speed as a string (e.g., "5 MB/s").
     * @param eta The estimated time remaining as a string (e.g., "2m 30s").
     */
    void updateProgress(int current, int total, const std::string& speed, const std::string& eta) { // Added names
        #ifdef _WIN32
            if(ClientGUI::getInstance()) ClientGUI::getInstance()->updateProgress(current, total, speed, eta);
        #else
            // Stub
        #endif
    }
    /**
     * @brief Updates the GUI to reflect the current connection status.
     *
     * @param connected True if the client is connected; false otherwise.
     */
    void updateConnectionStatus(bool connected) { // Added name
        #ifdef _WIN32
            if(ClientGUI::getInstance()) ClientGUI::getInstance()->updateConnectionStatus(connected);
        #else
            // Stub
        #endif
    }
    /**
     * @brief Updates the GUI to display the specified error message.
     *
     * On Windows, forwards the error message to the client GUI for display. On other platforms, this function has no effect.
     *
     * @param message The error message to display in the GUI.
     */
    void updateError(const std::string& message) { // Added name
        #ifdef _WIN32
            if(ClientGUI::getInstance()) ClientGUI::getInstance()->updateError(message);
        #else
            // Stub
        #endif
    }
    /**
     * @brief Displays a notification to the user with the specified title and message.
     *
     * On Windows, shows a system tray balloon notification. On other platforms, this function has no effect.
     *
     * @param title The notification title.
     * @param message The notification message content.
     */
    void showNotification(const std::string& title, const std::string& message) { // Added names
        #ifdef _WIN32
            if(ClientGUI::getInstance()) ClientGUI::getInstance()->showNotification(title, message);
        #else
            // Stub
        #endif
    }
} // namespace ClientGUIHelpers


#ifdef _WIN32 // All ClientGUI class specific implementations remain Windows-only

// Required for ClientGUI class if not already included via ClientGUI.h
#include <windowsx.h> // For GDI macros, etc., if used (e.g. GET_X_LPARAM)
#include <commctrl.h> // For some constants, though not heavily used

// Static instance for singleton pattern
static ClientGUI* g_clientGUI = nullptr;

// Window class names
static const wchar_t* STATUS_WINDOW_CLASS = L"EncryptedBackupStatusWindow";
static const wchar_t* TRAY_WINDOW_CLASS = L"EncryptedBackupTrayWindow";

/**
 * @brief Constructs a ClientGUI instance and initializes GUI-related members.
 *
 * Initializes synchronization primitives, tray icon data, and default status values for the GUI client.
 */
ClientGUI::ClientGUI() 
    : statusWindow(nullptr)
    , hTrayWnd_(nullptr) 
    , consoleWindow(GetConsoleWindow())
    , statusWindowVisible(false)
    , shouldClose(false)
    , guiInitialized(false) 
{
    InitializeCriticalSection(&statusLock);
    ZeroMemory(&trayIcon, sizeof(trayIcon));
    
    currentStatus.phase = "Initializing";
    currentStatus.connected = false;
    currentStatus.progress = 0;
    currentStatus.totalProgress = 100;
}

/**
 * @brief Cleans up resources used by the ClientGUI instance.
 *
 * Shuts down the GUI and deletes the critical section used for status synchronization.
 */
ClientGUI::~ClientGUI() {
    shutdown();
    DeleteCriticalSection(&statusLock);
}

/**
 * @brief Returns the singleton instance of the ClientGUI class.
 *
 * Creates the instance if it does not already exist.
 *
 * @return Pointer to the singleton ClientGUI instance.
 */
ClientGUI* ClientGUI::getInstance() {
    if (!g_clientGUI) {
        g_clientGUI = new ClientGUI();
    }
    return g_clientGUI;
}

/**
 * @brief Initializes the GUI by registering window classes and starting the GUI thread.
 *
 * Registers the status and tray window classes, launches the GUI message loop in a separate thread, and waits for the GUI to become ready. Returns true if initialization succeeds, or false if any step fails.
 *
 * @return true if the GUI was successfully initialized; false otherwise.
 */
bool ClientGUI::initialize() {
    if (guiInitialized.load()) {
        return true; 
    }
    
    try {
        WNDCLASSEXW wc = {};
        wc.cbSize = sizeof(WNDCLASSEXW);
        wc.lpfnWndProc = StatusWindowProc;
        wc.hInstance = GetModuleHandle(nullptr);
        wc.hbrBackground = (HBRUSH)(COLOR_WINDOW + 1);
        wc.lpszClassName = STATUS_WINDOW_CLASS;
        wc.hIcon = LoadIcon(GetModuleHandle(nullptr), IDI_APPLICATION); 
        wc.hCursor = LoadCursor(nullptr, IDC_ARROW);
        
        if (!RegisterClassExW(&wc)) {
            return false;
        }
        
        wc.lpfnWndProc = TrayWindowProc;
        wc.lpszClassName = TRAY_WINDOW_CLASS;
        wc.hbrBackground = nullptr; 
        wc.hIcon = nullptr; 
        
        if (!RegisterClassExW(&wc)) {
            UnregisterClassW(STATUS_WINDOW_CLASS, GetModuleHandle(nullptr)); 
            return false;
        }
        
        guiThread = std::thread(&ClientGUI::guiMessageLoop, this);
        
        int attempts = 0;
        while (!guiInitialized.load() && attempts < 50) { 
            Sleep(100);
            attempts++;
        }
        
        return guiInitialized.load();
        
    } catch (...) {
        return false;
    }
}

/**
 * @brief Runs the GUI thread message loop for the client application.
 *
 * Initializes the hidden tray window, tray icon, and status window, then enters the Windows message loop to process GUI events until shutdown is requested. Cleans up resources and destroys windows on exit.
 */
void ClientGUI::guiMessageLoop() {
    try {
        hTrayWnd_ = CreateWindowExW(0, TRAY_WINDOW_CLASS, L"EncryptedBackupTrayHiddenWindow", 0, 0, 0, 0, 0, 
                                   HWND_MESSAGE, nullptr, GetModuleHandle(nullptr), this);
        
        if (!hTrayWnd_) {
            return;
        }
        
        if (!initializeTrayIcon()) { 
            DestroyWindow(hTrayWnd_);
            hTrayWnd_ = nullptr;
            return;
        }
        
        if (!createStatusWindow()) {
            cleanup(); 
            DestroyWindow(hTrayWnd_);
            hTrayWnd_ = nullptr;
            return;
        }
        
        guiInitialized.store(true); 
        
        MSG msg;
        while (!shouldClose.load()) {
            BOOL result = GetMessage(&msg, nullptr, 0, 0);
            if (result == 0) { 
                break;
            }
            if (result == -1) { 
                break;
            }
            
            TranslateMessage(&msg);
            DispatchMessage(&msg);
        }
        
    } catch (...) {
        // Log exception
    }

    cleanup(); 
    if (hTrayWnd_) {
        DestroyWindow(hTrayWnd_);
        hTrayWnd_ = nullptr;
    }
    guiInitialized.store(false); 
}

/**
 * @brief Initializes the system tray icon for the client application.
 *
 * Sets up the tray icon with default tooltip and notification information, and adds it to the Windows system tray.
 *
 * @return true if the tray icon was successfully added; false otherwise.
 */
bool ClientGUI::initializeTrayIcon() {
    if (!hTrayWnd_) return false; 

    ZeroMemory(&trayIcon, sizeof(trayIcon));
    
    trayIcon.cbSize = sizeof(NOTIFYICONDATAW);
    trayIcon.hWnd = hTrayWnd_; 
    trayIcon.uID = 1; 
    trayIcon.uFlags = NIF_ICON | NIF_MESSAGE | NIF_TIP | NIF_INFO;
    trayIcon.uCallbackMessage = WM_TRAYICON; 
    
    trayIcon.hIcon = LoadIcon(GetModuleHandle(nullptr), IDI_APPLICATION); 
    if (!trayIcon.hIcon) {
        trayIcon.hIcon = LoadIcon(nullptr, IDI_APPLICATION); 
    }
    
    wcsncpy_s(trayIcon.szTip, ARRAYSIZE(trayIcon.szTip), L"Encrypted Backup Client", _TRUNCATE);

    wcsncpy_s(trayIcon.szInfo, ARRAYSIZE(trayIcon.szInfo), L"Client is initializing...", _TRUNCATE);
    wcsncpy_s(trayIcon.szInfoTitle, ARRAYSIZE(trayIcon.szInfoTitle), L"Backup Client", _TRUNCATE);
    trayIcon.dwInfoFlags = NIIF_INFO; 
    
    return Shell_NotifyIconW(NIM_ADD, &trayIcon) == TRUE;
}

/**
 * @brief Creates and initializes the status window for displaying client status.
 *
 * The window is created as a topmost, tool window with a caption and system menu, centered on the screen, and initially hidden.
 *
 * @return true if the status window was successfully created; false otherwise.
 */
bool ClientGUI::createStatusWindow() {
    statusWindow = CreateWindowExW(
        WS_EX_TOPMOST | WS_EX_TOOLWINDOW, 
        STATUS_WINDOW_CLASS,
        L"Backup Client Status",
        WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU, 
        CW_USEDEFAULT, CW_USEDEFAULT, 400, 300, 
        nullptr, 
        nullptr, 
        GetModuleHandle(nullptr), 
        this     
    );
    
    if (statusWindow) {
        RECT rc;
        GetWindowRect(statusWindow, &rc);
        int winWidth = rc.right - rc.left;
        int winHeight = rc.bottom - rc.top;
        int screenWidth = GetSystemMetrics(SM_CXSCREEN);
        int screenHeight = GetSystemMetrics(SM_CYSCREEN);
        int x = (screenWidth - winWidth) / 2;
        int y = (screenHeight - winHeight) / 2;
        SetWindowPos(statusWindow, HWND_TOPMOST, x, y, 0, 0, SWP_NOSIZE);
        
        showStatusWindow(false); 
    }
    
    return statusWindow != nullptr;
}

/**
 * @brief Window procedure for the status window, handling painting, close, and update messages.
 *
 * Processes window messages for the status window, including repainting the window, hiding it on close, and triggering updates when status changes. All other messages are passed to the default window procedure.
 *
 * @param hwnd Handle to the status window.
 * @param msg Window message identifier.
 * @param wParam Additional message information.
 * @param lParam Additional message information.
 * @return LRESULT Result of message processing.
 */
LRESULT CALLBACK ClientGUI::StatusWindowProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    ClientGUI* gui = nullptr;
    
    if (msg == WM_NCCREATE) {
        CREATESTRUCT* cs = reinterpret_cast<CREATESTRUCT*>(lParam);
        gui = static_cast<ClientGUI*>(cs->lpCreateParams);
        SetWindowLongPtr(hwnd, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(gui));
    } else {
        gui = reinterpret_cast<ClientGUI*>(GetWindowLongPtr(hwnd, GWLP_USERDATA));
    }
    
    if (!gui) { 
        return DefWindowProc(hwnd, msg, wParam, lParam);
    }

    switch (msg) {
        case WM_PAINT: {
            PAINTSTRUCT ps;
            HDC hdc = BeginPaint(hwnd, &ps);
            gui->updateStatusWindow(); 
            EndPaint(hwnd, &ps);
            return 0;
        }
        
        case WM_CLOSE:
            gui->showStatusWindow(false); 
            return 0;
            
        case WM_STATUS_UPDATE: 
            InvalidateRect(hwnd, nullptr, TRUE); 
            return 0;
            
        default:
            return DefWindowProc(hwnd, msg, wParam, lParam);
    }
}

/**
 * @brief Window procedure for the hidden tray window handling tray icon events and context menu commands.
 *
 * Processes custom tray icon messages, context menu selections, and standard window messages for the tray window. Handles right-click to show the context menu, double-click to toggle the status window, and menu commands to show/hide windows or exit the application.
 *
 * @param hwnd Handle to the tray window.
 * @param msg Window message identifier.
 * @param wParam Additional message information.
 * @param lParam Additional message information.
 * @return LRESULT Result of message processing, or result from DefWindowProc for unhandled messages.
 */
LRESULT CALLBACK ClientGUI::TrayWindowProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    ClientGUI* gui = nullptr;

    if (msg == WM_NCCREATE) {
        CREATESTRUCT* cs = reinterpret_cast<CREATESTRUCT*>(lParam);
        gui = static_cast<ClientGUI*>(cs->lpCreateParams);
        SetWindowLongPtr(hwnd, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(gui));
    } else {
        gui = reinterpret_cast<ClientGUI*>(GetWindowLongPtr(hwnd, GWLP_USERDATA));
    }

    if (!gui) { 
        return DefWindowProc(hwnd, msg, wParam, lParam);
    }
    
    switch (msg) {
        case WM_TRAYICON: 
            if (lParam == WM_RBUTTONUP) { 
                POINT pt;
                GetCursorPos(&pt);
                gui->showContextMenu(pt);
            } else if (lParam == WM_LBUTTONDBLCLK) { 
                gui->toggleStatusWindow();
            }
            return 0;
            
        case WM_COMMAND: 
            switch (LOWORD(wParam)) {
                case ID_SHOW_STATUS:
                    gui->toggleStatusWindow();
                    break;
                case ID_SHOW_CONSOLE:
                    gui->toggleConsoleWindow();
                    break;
                case ID_EXIT:
                    gui->shouldClose.store(true); 
                    PostQuitMessage(0);           
                    break;
            }
            return 0;
            
        default:
            return DefWindowProc(hwnd, msg, wParam, lParam);
    }
}

/**
 * @brief Displays the system tray context menu at the specified screen position.
 *
 * Shows a popup menu with options to show or hide the status window, toggle the console window, and exit the application. The menu is displayed at the given screen coordinates.
 *
 * @param pt The screen coordinates where the context menu should appear.
 */
void ClientGUI::showContextMenu(POINT pt) {
    if (!hTrayWnd_) return; 

    HMENU menu = CreatePopupMenu();
    if (!menu) return;
    
    AppendMenuW(menu, MF_STRING, ID_SHOW_STATUS, 
               statusWindowVisible.load() ? L"Hide Status Window" : L"Show Status Window");
    AppendMenuW(menu, MF_STRING, ID_SHOW_CONSOLE, L"Toggle Console");
    AppendMenuW(menu, MF_SEPARATOR, 0, nullptr);
    AppendMenuW(menu, MF_STRING, ID_EXIT, L"Exit");
    
    SetForegroundWindow(hTrayWnd_); 
    
    TrackPopupMenu(menu, TPM_RIGHTBUTTON | TPM_BOTTOMALIGN | TPM_LEFTALIGN, 
                   pt.x, pt.y, 0, 
                   hTrayWnd_, 
                   nullptr);
    
    DestroyMenu(menu); 
}

/**
 * @brief Repaints the status window with the latest client status information.
 *
 * Displays connection status, phase, operation, progress (with percentage and progress bar), speed, ETA, and error messages in the status window. Colors and formatting are used to highlight connection and error states.
 */
void ClientGUI::updateStatusWindow() {
    if (!statusWindow || !IsWindowVisible(statusWindow)) return; 
    
    GUIStatus status; 
    {
        EnterCriticalSection(&statusLock);
        status = currentStatus; 
        LeaveCriticalSection(&statusLock);
    }
    
    HDC hdc = GetDC(statusWindow);
    if (!hdc) return;
    
    RECT rect;
    GetClientRect(statusWindow, &rect);
    
    FillRect(hdc, &rect, (HBRUSH)(COLOR_WINDOW + 1));
    
    SetBkMode(hdc, TRANSPARENT); 
    
    int y = 10;
    int lineHeight = 20; 
    HFONT hFont = (HFONT)GetStockObject(DEFAULT_GUI_FONT); 
    HFONT hOldFont = (HFONT)SelectObject(hdc, hFont);

    std::wstring connText = status.connected ? L"✓ Connected" : L"✗ Disconnected";
    SetTextColor(hdc, status.connected ? RGB(0, 128, 0) : RGB(255, 0, 0)); 
    TextOutW(hdc, 10, y, connText.c_str(), static_cast<int>(connText.length()));
    y += lineHeight;
    
    SetTextColor(hdc, RGB(0, 0, 0)); 
    
    std::wstring phaseText = L"Phase: " + std::wstring(status.phase.begin(), status.phase.end());
    TextOutW(hdc, 10, y, phaseText.c_str(), static_cast<int>(phaseText.length()));
    y += lineHeight;
    
    if (!status.operation.empty()) {
        std::wstring opText = L"Operation: " + std::wstring(status.operation.begin(), status.operation.end());
        TextOutW(hdc, 10, y, opText.c_str(), static_cast<int>(opText.length()));
        y += lineHeight;
    }
    
    if (status.totalProgress > 0) {
        long long percentage = (status.totalProgress > 0) ? ((long long)status.progress * 100) / status.totalProgress : 0;
        std::wstring progText = L"Progress: " + std::to_wstring(status.progress) + 
                               L"/" + std::to_wstring(status.totalProgress) + 
                               L" (" + std::to_wstring(percentage) + L"%)";
        TextOutW(hdc, 10, y, progText.c_str(), static_cast<int>(progText.length()));
        y += lineHeight;
        
        RECT progRect = {10, y, rect.right - 10, y + 15};
        FrameRect(hdc, &progRect, (HBRUSH)GetStockObject(BLACK_BRUSH)); 
        
        if (status.progress > 0 && status.totalProgress > 0) {
            RECT fillRect = progRect;
            fillRect.left += 1; fillRect.top += 1; fillRect.right -=1; fillRect.bottom -=1;

            fillRect.right = fillRect.left + ((fillRect.right - fillRect.left) * status.progress) / status.totalProgress;
            FillRect(hdc, &fillRect, (HBRUSH)GetStockObject(DKGRAY_BRUSH)); 
        }
        y += 25; 
    }
    
    if (!status.speed.empty()) {
        std::wstring speedText = L"Speed: " + std::wstring(status.speed.begin(), status.speed.end());
        TextOutW(hdc, 10, y, speedText.c_str(), static_cast<int>(speedText.length()));
        y += lineHeight;
    }
    
    if (!status.eta.empty()) {
        std::wstring etaText = L"ETA: " + std::wstring(status.eta.begin(), status.eta.end());
        TextOutW(hdc, 10, y, etaText.c_str(), static_cast<int>(etaText.length()));
        y += lineHeight;
    }
    
    if (!status.error.empty()) {
        SetTextColor(hdc, RGB(255, 0, 0)); 
        std::wstring errorText = L"Error: " + std::wstring(status.error.begin(), status.error.end());
        TextOutW(hdc, 10, y, errorText.c_str(), static_cast<int>(errorText.length()));
    }
    
    SelectObject(hdc, hOldFont); 
    ReleaseDC(statusWindow, hdc);
}

/**
 * @brief Updates the current phase displayed in the GUI and tray icon tooltip.
 *
 * Sets the phase string in the status data, triggers a status window repaint if visible, and updates the tray icon tooltip to reflect the new phase.
 *
 * @param phase The new phase description to display.
 */
void ClientGUI::updatePhase(const std::string& phase) {
    EnterCriticalSection(&statusLock);
    currentStatus.phase = phase;
    LeaveCriticalSection(&statusLock);
    
    if (statusWindow) {
        PostMessage(statusWindow, WM_STATUS_UPDATE, 0, 0);
    }
    
    if (guiInitialized.load() && hTrayWnd_) {
        std::wstring tooltip = L"Backup Client - " + std::wstring(phase.begin(), phase.end());
        wcsncpy_s(trayIcon.szTip, ARRAYSIZE(trayIcon.szTip), tooltip.c_str(), _TRUNCATE);
        Shell_NotifyIconW(NIM_MODIFY, &trayIcon);
    }
}

/**
 * @brief Updates the current operation status displayed in the GUI.
 *
 * Sets the operation name, success state, and details. If the operation failed and details are provided, the error message is updated accordingly; if successful, any previous error is cleared. Triggers a status window update if visible.
 */
void ClientGUI::updateOperation(const std::string& operation, bool success, const std::string& details) {
    EnterCriticalSection(&statusLock);
    currentStatus.operation = operation;
    currentStatus.success = success;
    currentStatus.details = details;
    if (!success && !details.empty()) {
        currentStatus.error = details; 
    } else if (success) {
        currentStatus.error.clear(); 
    }
    LeaveCriticalSection(&statusLock);
    
    if (statusWindow) {
        PostMessage(statusWindow, WM_STATUS_UPDATE, 0, 0);
    }
}

/**
 * @brief Updates the progress, speed, and estimated time remaining displayed in the status window.
 *
 * Updates the current and total progress values, transfer speed, and ETA shown in the GUI. Triggers a status window refresh if it is visible.
 *
 * @param current Current progress value.
 * @param total Total progress value.
 * @param speed Human-readable transfer speed string (e.g., "5 MB/s").
 * @param eta Estimated time remaining string (e.g., "2m 30s").
 */
void ClientGUI::updateProgress(int current, int total, const std::string& speed, const std::string& eta) {
    EnterCriticalSection(&statusLock);
    currentStatus.progress = current;
    currentStatus.totalProgress = total;
    currentStatus.speed = speed;
    currentStatus.eta = eta;
    LeaveCriticalSection(&statusLock);
    
    if (statusWindow) {
        PostMessage(statusWindow, WM_STATUS_UPDATE, 0, 0);
    }
}

/**
 * @brief Updates the connection status displayed in the GUI.
 *
 * Sets the internal connection status and refreshes the status window and tray icon to reflect the new state.
 *
 * @param connected True if the client is connected; false otherwise.
 */
void ClientGUI::updateConnectionStatus(bool connected) {
    EnterCriticalSection(&statusLock);
    currentStatus.connected = connected;
    LeaveCriticalSection(&statusLock);
    
    if (statusWindow) {
        PostMessage(statusWindow, WM_STATUS_UPDATE, 0, 0);
    }
    
    if (guiInitialized.load() && hTrayWnd_) { 
         Shell_NotifyIconW(NIM_MODIFY, &trayIcon);
    }
}

/**
 * @brief Updates the displayed error message in the GUI.
 *
 * Sets the current error message and triggers a status window update if visible.
 *
 * @param error The error message to display.
 */
void ClientGUI::updateError(const std::string& error) {
    EnterCriticalSection(&statusLock);
    currentStatus.error = error;
    LeaveCriticalSection(&statusLock);
    
    if (statusWindow) {
        PostMessage(statusWindow, WM_STATUS_UPDATE, 0, 0);
    }
}

/**
 * @brief Displays a notification balloon from the system tray icon.
 *
 * Shows a balloon tooltip with the specified title, message, and icon type using the tray icon.
 *
 * @param title The title of the notification balloon.
 * @param message The message content of the notification balloon.
 * @param iconType The icon type for the notification (e.g., NIIF_INFO, NIIF_WARNING).
 */
void ClientGUI::showNotification(const std::string& title, const std::string& message, DWORD iconType) {
    if (!guiInitialized.load() || !hTrayWnd_) return; 
    
    std::wstring wTitle(title.begin(), title.end());
    std::wstring wMessage(message.begin(), message.end());
    
    wcsncpy_s(trayIcon.szInfoTitle, ARRAYSIZE(trayIcon.szInfoTitle), wTitle.c_str(), _TRUNCATE);
    wcsncpy_s(trayIcon.szInfo, ARRAYSIZE(trayIcon.szInfo), wMessage.c_str(), _TRUNCATE);
    trayIcon.dwInfoFlags = iconType; 
    
    trayIcon.uFlags |= NIF_INFO; 

    Shell_NotifyIconW(NIM_MODIFY, &trayIcon);
}

/**
 * @brief Displays a modal message box with the specified title, message, and type.
 *
 * The message box is parented to the status window if it is visible; otherwise, it is unparented.
 *
 * @param title The title of the message box.
 * @param message The message to display.
 * @param type The type of message box (e.g., MB_OK, MB_ICONERROR).
 */
void ClientGUI::showPopup(const std::string& title, const std::string& message, UINT type) {
    std::wstring wTitle(title.begin(), title.end());
    std::wstring wMessage(message.begin(), message.end());
    
    MessageBoxW(statusWindowVisible.load() ? statusWindow : nullptr, wMessage.c_str(), wTitle.c_str(), type);
}

/**
 * @brief Toggles the visibility of the status window.
 *
 * If the status window is currently visible, it will be hidden; if hidden, it will be shown.
 */
void ClientGUI::toggleStatusWindow() {
    showStatusWindow(!statusWindowVisible.load());
}

/**
 * @brief Shows or hides the status window.
 *
 * When shown, the status window is brought to the foreground, set as topmost, and repainted.
 *
 * @param show If true, displays the status window; if false, hides it.
 */
void ClientGUI::showStatusWindow(bool show) {
    if (!statusWindow) return;
    
    statusWindowVisible.store(show);
    ShowWindow(statusWindow, show ? SW_SHOW : SW_HIDE);
    
    if (show) {
        SetForegroundWindow(statusWindow); 
        SetWindowPos(statusWindow, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE); 
        InvalidateRect(statusWindow, nullptr, TRUE); 
    }
}

/**
 * @brief Toggles the visibility of the console window.
 *
 * If the console window is currently visible, it will be hidden; if hidden, it will be shown.
 */
void ClientGUI::toggleConsoleWindow() {
    if (consoleWindow) { 
        bool visible = IsWindowVisible(consoleWindow) != FALSE;
        ShowWindow(consoleWindow, visible ? SW_HIDE : SW_SHOW);
    }
}

/**
 * @brief Shows or hides the console window.
 *
 * @param show If true, the console window is shown; if false, it is hidden.
 */
void ClientGUI::showConsoleWindow(bool show) {
    if (consoleWindow) {
        ShowWindow(consoleWindow, show ? SW_SHOW : SW_HIDE);
    }
}

/**
 * @brief Shuts down the GUI by signaling the GUI thread to exit and waiting for its termination.
 *
 * If the GUI is initialized or the GUI thread is running, this method signals the thread to close, posts a quit or wake message to ensure the message loop exits, and joins the thread to complete shutdown.
 */
void ClientGUI::shutdown() {
    if (!guiInitialized.load() && !guiThread.joinable()) { 
         return;
    }
    
    shouldClose.store(true); 
    
    // Try to post a WM_QUIT message to the GUI thread's message queue.
    // GetThreadId requires Windows XP SP1 or later.
    // guiThread.native_handle() gives the underlying thread handle.
    DWORD guiThreadId = GetThreadId(guiThread.native_handle());
    if (guiThreadId != 0) { // Check if GetThreadId was successful
       PostThreadMessage(guiThreadId, WM_QUIT, 0, 0);
    } else if (hTrayWnd_) { 
        // Fallback if GetThreadId failed, try posting to one of its windows.
        // This isn't as direct but can wake up GetMessage.
         PostMessage(hTrayWnd_, WM_NULL, 0, 0); // Wake GetMessage
    }


    if (guiThread.joinable()) {
        guiThread.join();
    }
}

/**
 * @brief Cleans up GUI resources by removing the tray icon and destroying the status window.
 *
 * This method is called during shutdown to ensure that all GUI-related resources are properly released.
 */
void ClientGUI::cleanup() {
    if (hTrayWnd_ && trayIcon.hWnd) { 
        trayIcon.uFlags = 0; 
        Shell_NotifyIconW(NIM_DELETE, &trayIcon);
        trayIcon.hWnd = nullptr; 
    }
    
    if (statusWindow) {
        DestroyWindow(statusWindow);
        statusWindow = nullptr;
    }
    // UnregisterClassW calls are optional as OS cleans up, but good practice for DLLs
    // HINSTANCE hInstance = GetModuleHandle(nullptr);
    // UnregisterClassW(STATUS_WINDOW_CLASS, hInstance);
    // UnregisterClassW(TRAY_WINDOW_CLASS, hInstance);
}

#endif // _WIN32