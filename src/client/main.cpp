#include <iostream>
#include <thread>
#include <chrono>
#include <atomic>
#include "../../include/client/ClientGUI.h"

// Forward declaration - we need to include the actual client class
class Client;

// Declare the actual client run function
extern bool runBackupClient();

// Global state for GUI-client communication
std::atomic<bool> backupRequested{false};
std::atomic<bool> backupInProgress{false};
std::atomic<bool> shouldExit{false};

int main() {
    std::cout << "💒 Encrypted Backup Client v3.0 - Starting...\n";

    try {
        // Initialize GUI first
        std::cout << "Initializing GUI..." << std::endl;
        if (ClientGUIHelpers::initializeGUI()) {
            std::cout << "GUI initialized successfully!" << std::endl;

            // Update GUI with initial status
            ClientGUIHelpers::updatePhase("🚀 ULTRA MODERN Backup Client - Ready");
            ClientGUIHelpers::updateConnectionStatus(false);
            ClientGUIHelpers::updateOperation("Ready to connect", true, "Click 'Start Backup' to begin");

            // Set up GUI callbacks for actual functionality
            #ifdef _WIN32
            if (ClientGUI::getInstance()) {
                ClientGUI* gui = ClientGUI::getInstance();

                // Connect the Start Backup button to actual backup functionality
                gui->setRetryCallback([]() {
                    std::cout << "🔄 Buckup requested from GUI..." << std::endl;
                    backupRequested.store(true);
                    gui->updateOperation("Backup starting...", true, "Initializing backup process");
                    gui->setBackupState(true, false);
                });

                gui->showStatusWindow(true);
                std::cout << "🖥🏰  Enhanced GUI window forced to show!" << std::endl;
            }
            #endif

            std::cout << "🏯 ULTRA MODERN GUI window should now be visible!" << std::endl;
            std::cout << "📱 Look for the 'ULTRA MODERN Backup Client' window on your screen!" << std::endl;
            std::cout << "💥 Press Enter to start backup client or use GUI buttons..." << std::endl;

            // Start background thread to handle backup requests
            std::thread backupThread([&]() {
                while (!shouldExit.load()) {
                    if (backupRequested.load() && !backupInProgress.load()) {
                        backupRequested.store(false);
                        backupInProgress.store(true);

                        // Update GUI to show backup in progress
                        ClientGUIHelpers::updatePhase("👔 Backup in Progress");
                        ClientGUIHelpers::updateOperation("Running backup...", true, "Connecting to server");

                        // Run the actual backup
                        bool success = runBackupClient();

                        // Update GUI with results
                        if (success) {
                            ClientGUIHelpers::updatePhase("✅ Backup Complete");
                            ClientGUIHelpers::updateOperation("Backup successful", true, "File transferred successfully");
                            ClientGUIHelpers::showNotification("Backup Complete", "File backup completed successfully", 0x00000001L);
                        } else {
                            ClientGUIHelpers::updatePhase("❌ Backup Failed");
                            ClientGUIHelpers::updateOperation("Backup failed", false, "Check logs for details");
                            ClientGUIHelpers::showNotification("Backup Failed", "Backup operation failed", 0x00000003L);
                        }

                        backupInProgress.store(false);
                        if (ClientGUI::getInstance()) {
                            ClientGUI::getInstance()->setBackupState(false, false);
                        }
                    }
                    std::this_thread::sleep_for(std::chrono::milliseconds(100));
                }
            });

            std::cin.get();

            // User pressed Enter - trigger backup
            std::cout << "🚀 Starting backup process..." << std::endl;
            backupRequested.store(true);

            // Wait for backup to complete
            while (backupInProgress.load() || backupRequested.load()) {
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
            }

            std::cout << "Press Enter to exit..." << std::endl;
            std::cin.get();

            // Cleanup
            shouldExit.store(true);
            backupThread.join();

            return 0;
        }
    } catch (const std::exception& e) {
        std::cout << "💥 Critical error: " << e.what() << std::endl;
        std::cout << "Press Enter to exit..." << std::endl;
        std::cin.get();
        return 1;
    } catch (...) {
        std::cout << "💥 Unknown critical error occurred.\n";
        std::cout << "Press Enter to exit..." << std::endl;
        std::cin.get();
        return 1;
    }
}
