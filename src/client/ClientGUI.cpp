// ClientGUI.cpp
#include "ClientGUI.h" // Use the correct header for declarations

// For std::wstring conversions used in ClientGUI class, and potentially by complex helpers
#include <sstream> 
#include <iomanip> 

// *** ClientGUIHelpers implementations are OUTSIDE _WIN32 block ***
// These are the stubs that should always be available for linking.
namespace ClientGUIHelpers {
    bool initializeGUI() { 
        #ifdef _WIN32
            // If on Windows, delegate to the actual GUI implementation
            return ClientGUI::getInstance() ? ClientGUI::getInstance()->initialize() : false; 
        #else
            // On other platforms, this is just a stub
            return true; // Or false, depending on desired default behavior
        #endif
    }
    void shutdownGUI() {
        #ifdef _WIN32
            if(ClientGUI::getInstance()) ClientGUI::getInstance()->shutdown();
        #else
            // Stub
        #endif
    }
    void updatePhase(const std::string& phase) { // Added const std::string& for parameter names
        #ifdef _WIN32
            if(ClientGUI::getInstance()) ClientGUI::getInstance()->updatePhase(phase);
        #else
            // Stub
        #endif
    }
    void updateOperation(const std::string& operation, bool success, const std::string& details) { // Added names
        #ifdef _WIN32
            if(ClientGUI::getInstance()) ClientGUI::getInstance()->updateOperation(operation, success, details);
        #else
            // Stub
        #endif
    }
    void updateProgress(int current, int total, const std::string& speed, const std::string& eta) { // Added names
        #ifdef _WIN32
            if(ClientGUI::getInstance()) ClientGUI::getInstance()->updateProgress(current, total, speed, eta);
        #else
            // Stub
        #endif
    }
    void updateConnectionStatus(bool connected) { // Added name
        #ifdef _WIN32
            if(ClientGUI::getInstance()) ClientGUI::getInstance()->updateConnectionStatus(connected);
        #else
            // Stub
        #endif
    }
    void updateError(const std::string& message) { // Added name
        #ifdef _WIN32
            if(ClientGUI::getInstance()) ClientGUI::getInstance()->updateError(message);
        #else
            // Stub
        #endif
    }
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

// Constructor
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

// Destructor
ClientGUI::~ClientGUI() {
    shutdown();
    DeleteCriticalSection(&statusLock);
}

// Get singleton instance
ClientGUI* ClientGUI::getInstance() {
    if (!g_clientGUI) {
        g_clientGUI = new ClientGUI();
    }
    return g_clientGUI;
}

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

bool ClientGUI::createStatusWindow() {
    statusWindow = CreateWindowExW(
        0, // Removed WS_EX_TOPMOST | WS_EX_TOOLWINDOW to show in taskbar
        STATUS_WINDOW_CLASS,
        L"Encrypted Backup Client - Status",
        WS_OVERLAPPEDWINDOW, // Changed to normal window style
        CW_USEDEFAULT, CW_USEDEFAULT, 500, 400, // Increased size
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
        SetWindowPos(statusWindow, HWND_TOP, x, y, 0, 0, SWP_NOSIZE); // Changed to HWND_TOP
        
        showStatusWindow(true); // Changed to show the window by default
    }
    
    return statusWindow != nullptr;
}

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
        
        case WM_CLOSE: {
            // Ask user what they want to do
            int result = MessageBoxW(hwnd, 
                L"What would you like to do?\n\nYes - Hide window to system tray\nNo - Exit application\nCancel - Keep window open", 
                L"Encrypted Backup Client", 
                MB_YESNOCANCEL | MB_ICONQUESTION);
            
            if (result == IDYES) {
                gui->showStatusWindow(false); // Hide to tray
            } else if (result == IDNO) {
                gui->shouldClose.store(true); 
                PostQuitMessage(0); // Exit application
            }
            // If Cancel, do nothing (keep window open)
            return 0;
        }
            
        case WM_STATUS_UPDATE: 
            InvalidateRect(hwnd, nullptr, TRUE); 
            return 0;
            
        default:
            return DefWindowProc(hwnd, msg, wParam, lParam);
    }
}

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

void ClientGUI::updateStatusWindow() {
    if (!statusWindow) return; // Only check if window exists, not if visible
    
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
      SetBkMode(hdc, TRANSPARENT);     int y = 15;
    int lineHeight = 22; 
    HFONT hFont = CreateFontW(16, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE,
                           DEFAULT_CHARSET, OUT_DEFAULT_PRECIS,
                           CLIP_DEFAULT_PRECIS, DEFAULT_QUALITY,
                           DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");
    HFONT hTitleFont = nullptr;
    HFONT hOldFont = (HFONT)SelectObject(hdc, hFont ? hFont : (HFONT)GetStockObject(DEFAULT_GUI_FONT));

    // Title
    SetTextColor(hdc, RGB(0, 51, 102)); 
    hTitleFont = CreateFontW(20, 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE,
                                DEFAULT_CHARSET, OUT_DEFAULT_PRECIS,
                                CLIP_DEFAULT_PRECIS, DEFAULT_QUALITY,
                                DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");
    SelectObject(hdc, hTitleFont ? hTitleFont : hFont);
    
    std::wstring titleText = L"🔒 Encrypted Backup Client";
    TextOutW(hdc, 15, y, titleText.c_str(), static_cast<int>(titleText.length()));
    y += 35;
    
    // Draw separator line
    HPEN hPen = CreatePen(PS_SOLID, 1, RGB(200, 200, 200));
    HPEN hOldPen = (HPEN)SelectObject(hdc, hPen);
    MoveToEx(hdc, 15, y, nullptr);
    LineTo(hdc, rect.right - 15, y);
    SelectObject(hdc, hOldPen);
    DeleteObject(hPen);
    y += 15;
      // Switch back to normal font
    SelectObject(hdc, hFont ? hFont : (HFONT)GetStockObject(DEFAULT_GUI_FONT));
    
    std::wstring connText = status.connected ? L"🟢 Connected to Server" : L"🔴 Disconnected";
    SetTextColor(hdc, status.connected ? RGB(0, 128, 0) : RGB(255, 0, 0)); 
    TextOutW(hdc, 15, y, connText.c_str(), static_cast<int>(connText.length()));
    y += lineHeight;
    
    SetTextColor(hdc, RGB(0, 0, 0)); 
    
    std::wstring phaseText = L"📋 Phase: " + std::wstring(status.phase.begin(), status.phase.end());
    TextOutW(hdc, 15, y, phaseText.c_str(), static_cast<int>(phaseText.length()));
    y += lineHeight;
      if (!status.operation.empty()) {
        std::wstring opText = L"⚙️ Operation: " + std::wstring(status.operation.begin(), status.operation.end());
        TextOutW(hdc, 15, y, opText.c_str(), static_cast<int>(opText.length()));
        y += lineHeight;
    }
      if (status.totalProgress > 0) {
        long long percentage = (status.totalProgress > 0) ? ((long long)status.progress * 100) / status.totalProgress : 0;
        std::wstring progText = L"📊 Progress: " + std::to_wstring(status.progress) + 
                               L"/" + std::to_wstring(status.totalProgress) + 
                               L" (" + std::to_wstring(percentage) + L"%)";
        TextOutW(hdc, 15, y, progText.c_str(), static_cast<int>(progText.length()));
        y += lineHeight;
        
        RECT progRect = {15, y, rect.right - 15, y + 20};
        FrameRect(hdc, &progRect, (HBRUSH)GetStockObject(BLACK_BRUSH)); 
        
        if (status.progress > 0 && status.totalProgress > 0) {
            RECT fillRect = progRect;
            fillRect.left += 1; fillRect.top += 1; fillRect.right -=1; fillRect.bottom -=1;

            fillRect.right = fillRect.left + ((fillRect.right - fillRect.left) * status.progress) / status.totalProgress;
            HBRUSH hBrush = CreateSolidBrush(RGB(0, 120, 215)); // Windows blue
            FillRect(hdc, &fillRect, hBrush);
            DeleteObject(hBrush);
        }
        y += 30; 
    }
      if (!status.speed.empty()) {
        std::wstring speedText = L"🚀 Speed: " + std::wstring(status.speed.begin(), status.speed.end());
        TextOutW(hdc, 15, y, speedText.c_str(), static_cast<int>(speedText.length()));
        y += lineHeight;
    }
    
    if (!status.eta.empty()) {
        std::wstring etaText = L"⏱️ ETA: " + std::wstring(status.eta.begin(), status.eta.end());
        TextOutW(hdc, 15, y, etaText.c_str(), static_cast<int>(etaText.length()));
        y += lineHeight;
    }
    
    if (!status.error.empty()) {
        SetTextColor(hdc, RGB(255, 0, 0)); 
        std::wstring errorText = L"❌ Error: " + std::wstring(status.error.begin(), status.error.end());
        TextOutW(hdc, 15, y, errorText.c_str(), static_cast<int>(errorText.length()));
    }
    
    // Clean up fonts
    SelectObject(hdc, hOldFont);
    if (hFont) DeleteObject(hFont);
    if (hTitleFont) DeleteObject(hTitleFont);
    ReleaseDC(statusWindow, hdc);
}

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

void ClientGUI::updateError(const std::string& error) {
    EnterCriticalSection(&statusLock);
    currentStatus.error = error;
    LeaveCriticalSection(&statusLock);
    
    if (statusWindow) {
        PostMessage(statusWindow, WM_STATUS_UPDATE, 0, 0);
    }
}

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

void ClientGUI::showPopup(const std::string& title, const std::string& message, UINT type) {
    std::wstring wTitle(title.begin(), title.end());
    std::wstring wMessage(message.begin(), message.end());
    
    MessageBoxW(statusWindowVisible.load() ? statusWindow : nullptr, wMessage.c_str(), wTitle.c_str(), type);
}

void ClientGUI::toggleStatusWindow() {
    showStatusWindow(!statusWindowVisible.load());
}

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

void ClientGUI::toggleConsoleWindow() {
    if (consoleWindow) { 
        bool visible = IsWindowVisible(consoleWindow) != FALSE;
        ShowWindow(consoleWindow, visible ? SW_HIDE : SW_SHOW);
    }
}

void ClientGUI::showConsoleWindow(bool show) {
    if (consoleWindow) {
        ShowWindow(consoleWindow, show ? SW_SHOW : SW_HIDE);
    }
}

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