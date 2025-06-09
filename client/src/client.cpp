// Client.cpp
// Encrypted File Backup System - Enhanced Client Implementation
// Fully compliant with project specifications

#include <iostream>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <string>
#include <vector>
#include <array>
#include <cstring>
#include <algorithm>
#include <chrono>
#include <thread>
//#include <filesystem>
#include <atomic>
#include <ctime>

// Boost.Asio for cross-platform networking
#include <boost/asio.hpp>
#include <boost/system/error_code.hpp>
#include <boost/bind/bind.hpp>

// Windows console control
#ifdef _WIN32
#include <windows.h>
#include <io.h>
#include <fcntl.h>
#endif

// Required wrapper includes (provided by project)
#include "cksum.h"
#include "AESWrapper.h"
#include "Base64Wrapper.h"
#include "RSAWrapper.h"

// Optional GUI support
#ifdef _WIN32
#include "ClientGUI.h"
#endif

// Protocol constants
constexpr uint8_t CLIENT_VERSION = 3;
constexpr uint8_t SERVER_VERSION = 3;

// Request codes
constexpr uint16_t REQ_REGISTER = 1025;
constexpr uint16_t REQ_SEND_PUBLIC_KEY = 1026;
constexpr uint16_t REQ_RECONNECT = 1027;
constexpr uint16_t REQ_SEND_FILE = 1028;
constexpr uint16_t REQ_CRC_OK = 1029;
constexpr uint16_t REQ_CRC_RETRY = 1030;
constexpr uint16_t REQ_CRC_ABORT = 1031;

// Response codes
constexpr uint16_t RESP_REGISTER_OK = 1600;
constexpr uint16_t RESP_REGISTER_FAIL = 1601;
constexpr uint16_t RESP_PUBKEY_AES_SENT = 1602;
constexpr uint16_t RESP_FILE_OK = 1603;
constexpr uint16_t RESP_ACK = 1604;
constexpr uint16_t RESP_RECONNECT_AES_SENT = 1605;
constexpr uint16_t RESP_RECONNECT_FAIL = 1606;
constexpr uint16_t RESP_ERROR = 1607;

// Size constants
constexpr size_t CLIENT_ID_SIZE = 16;
constexpr size_t MAX_NAME_SIZE = 255;
constexpr size_t RSA_KEY_SIZE = 162; // Updated for 1024-bit keys in DER format
constexpr size_t AES_KEY_SIZE = 32;
constexpr size_t MAX_PACKET_SIZE = 1024 * 1024;  // 1MB per packet
constexpr size_t OPTIMAL_BUFFER_SIZE = 64 * 1024; // 64KB for file reading

// Other constants
constexpr int MAX_RETRIES = 3;
constexpr int SOCKET_TIMEOUT_MS = 30000; // 30 seconds
constexpr int RECONNECT_DELAY_MS = 5000; // 5 seconds between reconnect attempts
constexpr int KEEPALIVE_INTERVAL = 60;   // 60 seconds

// Protocol structures
#pragma pack(push, 1)
struct RequestHeader {
    uint8_t client_id[16];
    uint8_t version;
    uint16_t code;
    uint32_t payload_size;
};

struct ResponseHeader {
    uint8_t version;
    uint16_t code;
    uint32_t payload_size;
};
#pragma pack(pop)

// Transfer statistics structure
struct TransferStats {
    std::chrono::steady_clock::time_point startTime;
    std::chrono::steady_clock::time_point lastUpdateTime;
    size_t totalBytes;
    size_t transferredBytes;
    size_t lastTransferredBytes;
    double currentSpeed;
    double averageSpeed;
    int estimatedTimeRemaining;
    
    /**
                       * @brief Initializes transfer statistics with zeroed values.
                       *
                       * Sets all fields related to file transfer progress, speed, and estimated time remaining to their initial states.
                       */
                      TransferStats() : totalBytes(0), transferredBytes(0), lastTransferredBytes(0),
                      currentSpeed(0.0), averageSpeed(0.0), estimatedTimeRemaining(0) {}
    
    /**
     * @brief Resets all transfer statistics to their initial state.
     *
     * Sets counters, speeds, and timers to zero and updates the start time for a new transfer session.
     */
    void reset() {
        startTime = std::chrono::steady_clock::now();
        lastUpdateTime = startTime;
        transferredBytes = 0;
        lastTransferredBytes = 0;
        currentSpeed = 0.0;
        averageSpeed = 0.0;
        estimatedTimeRemaining = 0;
    }
    
    /**
     * @brief Updates transfer statistics with the latest transferred byte count.
     *
     * Recalculates current speed, average speed, and estimated time remaining based on the new total of transferred bytes.
     *
     * @param newBytes The updated total number of bytes transferred so far.
     */
    void update(size_t newBytes) {
        auto now = std::chrono::steady_clock::now();
        transferredBytes = newBytes;
        
        // Calculate current speed
        auto timeSinceLastUpdate = std::chrono::duration_cast<std::chrono::milliseconds>(now - lastUpdateTime).count();
        if (timeSinceLastUpdate > 0) {
            currentSpeed = ((transferredBytes - lastTransferredBytes) * 1000.0) / timeSinceLastUpdate;
        }
        
        // Calculate average speed
        auto totalTime = std::chrono::duration_cast<std::chrono::milliseconds>(now - startTime).count();
        if (totalTime > 0) {
            averageSpeed = (transferredBytes * 1000.0) / totalTime;
        }
        
        // Calculate estimated time remaining
        if (averageSpeed > 0 && totalBytes > transferredBytes) {
            estimatedTimeRemaining = static_cast<int>((totalBytes - transferredBytes) / averageSpeed);
        }
        
        lastUpdateTime = now;
        lastTransferredBytes = transferredBytes;
    }
};

// Enhanced error codes for better debugging
enum class ErrorType {
    NONE,
    NETWORK,
    FILE_IO,
    PROTOCOL,
    CRYPTO,
    CONFIG,
    AUTHENTICATION,
    SERVER_ERROR
};

class Client {
private:
    // Boost.Asio networking
    boost::asio::io_context ioContext;
    std::unique_ptr<boost::asio::ip::tcp::socket> socket;
    std::string serverIP;
    uint16_t serverPort;
    bool connected;
    std::atomic<bool> keepAliveEnabled;
    
    // Client info
    std::array<uint8_t, CLIENT_ID_SIZE> clientID;
    std::string username;
    std::string filepath;
    
    // Crypto
    RSAPrivateWrapper* rsaPrivate;
    std::string aesKey;
    
    // Retry counters
    int fileRetries;
    int crcRetries;
    int reconnectAttempts;
    
    // Transfer statistics
    TransferStats stats;
    
    // Console output control
    HANDLE hConsole;
    CONSOLE_SCREEN_BUFFER_INFO consoleInfo;
    WORD savedAttributes;
    
    // Error tracking
    ErrorType lastError;
    std::string lastErrorDetails;
    
    // Performance metrics
    std::chrono::steady_clock::time_point operationStartTime;

public:
    Client();
    ~Client();
    
    // Main interface
    bool initialize();
    bool run();
    
private:
    // Configuration
    bool readTransferInfo();
    bool validateConfiguration();
    bool loadMeInfo();
    bool saveMeInfo();
    bool loadPrivateKey();
    bool savePrivateKey();
      // Network operations
    bool connectToServer();
    void closeConnection();
    bool sendRequest(uint16_t code, const std::vector<uint8_t>& payload = {});
    bool receiveResponse(ResponseHeader& header, std::vector<uint8_t>& payload);
    bool testConnection();
    void enableKeepAlive();
    
    // Protocol operations
    bool performRegistration();
    bool performReconnection();
    bool sendPublicKey();
    bool transferFile();
    bool sendFilePacket(const std::string& filename, const std::string& encryptedData, 
                       uint32_t originalSize, uint16_t packetNum, uint16_t totalPackets);
    bool verifyCRC(uint32_t serverCRC, const std::vector<uint8_t>& originalData, const std::string& filename);
    
    // Crypto operations
    bool generateRSAKeys();
    bool decryptAESKey(const std::vector<uint8_t>& encryptedKey);
    std::string encryptFile(const std::vector<uint8_t>& data);
    
    // Utility functions
    std::vector<uint8_t> readFile(const std::string& path);
    std::string bytesToHex(const uint8_t* data, size_t size);
    std::vector<uint8_t> hexToBytes(const std::string& hex);
    uint32_t calculateCRC32(const uint8_t* data, size_t size);
    std::string formatBytes(size_t bytes);
    std::string formatDuration(int seconds);
    std::string getCurrentTimestamp();
    
    // Visual feedback
    void displayStatus(const std::string& operation, bool success, const std::string& details = "");
    void displayProgress(const std::string& operation, size_t current, size_t total);
    void displayTransferStats();
    void displaySplashScreen();
    void clearLine();
    void displayConnectionInfo();
    void displayError(const std::string& message, ErrorType type = ErrorType::NONE);
    void displaySeparator();
    void displayPhase(const std::string& phase);
    void displaySummary();
};

/**
 * @brief Constructs a Client instance and initializes member variables.
 *
 * Sets default values for connection state, retry counters, cryptographic pointers, and client ID. On Windows, initializes console handles and attempts to start the optional GUI, continuing gracefully if GUI initialization fails.
 */
Client::Client() : socket(nullptr), connected(false), rsaPrivate(nullptr), 
                   fileRetries(0), crcRetries(0), reconnectAttempts(0),
                   keepAliveEnabled(false), lastError(ErrorType::NONE) {
    std::fill(clientID.begin(), clientID.end(), 0);
    
#ifdef _WIN32
    hConsole = GetStdHandle(STD_OUTPUT_HANDLE);
    GetConsoleScreenBufferInfo(hConsole, &consoleInfo);
    savedAttributes = consoleInfo.wAttributes;
    
    // Initialize GUI (optional - graceful failure)
    try {
        ClientGUIHelpers::initializeGUI();
    } catch (...) {
        // GUI initialization failed - continue without GUI
    }
#endif
}

/**
 * @brief Cleans up resources used by the Client, including network connections, cryptographic keys, and console or GUI state.
 *
 * Disables keep-alive, closes any open server connection, deletes the RSA private key, restores console attributes on Windows, and attempts to gracefully shut down the optional GUI.
 */
Client::~Client() {
    keepAliveEnabled = false;
    closeConnection();
    if (rsaPrivate) {
        delete rsaPrivate;
    }
#ifdef _WIN32
    SetConsoleTextAttribute(hConsole, savedAttributes);
    
    // Shutdown GUI (optional - graceful failure)
    try {
        ClientGUIHelpers::shutdownGUI();
    } catch (...) {
        // GUI shutdown failed - continue cleanup
    }
#endif
}

/**
 * @brief Initializes the client by loading configuration and preparing cryptographic keys.
 *
 * Reads configuration files, validates parameters, and loads or generates the RSA key pair required for secure communication. Displays initialization status and progress.
 *
 * @return true if initialization succeeds; false if configuration is invalid or key preparation fails.
 */
bool Client::initialize() {
    operationStartTime = std::chrono::steady_clock::now();
    displaySplashScreen();
    
    displayPhase("Initialization");
    
    displayStatus("System initialization", true, "Starting client v1.0");
    
    if (!readTransferInfo()) {
        return false;
    }
    
    if (!validateConfiguration()) {
        return false;
    }

    // Pre-generate or load RSA keys during initialization to avoid delays during registration
    displayStatus("Preparing RSA keys", true, "1024-bit key pair for encryption");

    // Try to load existing keys first to avoid regeneration
    if (loadPrivateKey()) {
        displayStatus("RSA keys loaded", true, "Using cached key pair");
    } else {
        displayStatus("Generating RSA keys", true, "Creating new 1024-bit key pair...");
        if (!generateRSAKeys()) {
            return false;
        }
        // Save the generated keys for future use
        savePrivateKey();
    }

    displayStatus("Initialization complete", true, "Ready to connect");
    return true;
}

/**
 * @brief Executes the main client workflow for connecting, authenticating, and transferring a file.
 *
 * Attempts to connect to the server with retries, performs authentication via registration or reconnection, and transfers the configured file with retry logic. Displays progress and status updates throughout the process.
 *
 * @return true if the file transfer completes successfully; false if any critical step fails.
 */
bool Client::run() {
    displayPhase("Connection Setup");
    
    displayStatus("Connecting to server", true, serverIP + ":" + std::to_string(serverPort));
    
    // Try to connect with retries
    bool connectedSuccessfully = false;
    for (int attempt = 1; attempt <= 3 && !connectedSuccessfully; attempt++) {
        if (attempt > 1) {
            displayStatus("Connection attempt", true, "Retry " + std::to_string(attempt) + " of 3");
            std::this_thread::sleep_for(std::chrono::milliseconds(RECONNECT_DELAY_MS));
        }
        
        if (connectToServer()) {
            connectedSuccessfully = true;
        }
    }
    
    if (!connectedSuccessfully) {
        displayError("Failed to connect after 3 attempts", ErrorType::NETWORK);
        return false;
    }
      displayConnectionInfo();
    
    // Test connection quality - Skip for now as test request causes server error
    // if (!testConnection()) {
    //     displayStatus("Connection test", false, "Poor connection quality detected");
    // }
    
    // Enable keep-alive for long transfers
    enableKeepAlive();
    
    displayPhase("Authentication");
    
    // Check if we have existing registration
    bool hasRegistration = loadMeInfo();
    
    if (hasRegistration) {
        displayStatus("Client credentials", true, "Found existing registration");
        displayStatus("Attempting reconnection", true, "Client: " + username);
        
        // Load private key
        if (!loadPrivateKey()) {
            displayStatus("Loading private key", false, "Key not found");
            hasRegistration = false;
        } else {
            // Try reconnection
            if (!performReconnection()) {
                displayStatus("Reconnection", false, "Server rejected - will register as new client");
                hasRegistration = false;
            }
        }
    }
    
    if (!hasRegistration) {
        displayStatus("Registering new client", true, username);
        
        if (!performRegistration()) {
            return false;
        }
        
        if (!sendPublicKey()) {
            return false;
        }
    }
    
    displayPhase("File Transfer");
    
    // Transfer the file with retry logic
    bool transferSuccess = false;
    fileRetries = 0;
    
    while (fileRetries < MAX_RETRIES && !transferSuccess) {
        if (fileRetries > 0) {
            displayStatus("File transfer", false, "Retrying (attempt " + 
                         std::to_string(fileRetries + 1) + " of " + std::to_string(MAX_RETRIES) + ")");
            std::this_thread::sleep_for(std::chrono::seconds(2));
        }
        
        if (transferFile()) {
            transferSuccess = true;
        } else {
            fileRetries++;
        }
    }
    
    if (!transferSuccess) {
        displayError("File transfer failed after " + std::to_string(MAX_RETRIES) + " attempts", ErrorType::NETWORK);
        return false;
    }
    
    displayPhase("Transfer Complete");
    displaySummary();
    
    return true;
}

/**
 * @brief Reads and parses the transfer.info configuration file.
 *
 * Loads the server address and port, username, and file path from the transfer.info file.
 * Validates the format and value constraints for each field. Reports configuration errors if any field is missing or invalid.
 *
 * @return true if the configuration is successfully loaded and valid; false otherwise.
 */
bool Client::readTransferInfo() {
    std::ifstream file("transfer.info");
    if (!file.is_open()) {
        displayError("Cannot open transfer.info", ErrorType::CONFIG);
        return false;
    }
    
    std::string line;
    
    // Line 1: server:port
    if (!std::getline(file, line)) {
        displayError("Invalid transfer.info format - missing server address", ErrorType::CONFIG);
        return false;
    }
    
    size_t colonPos = line.find(':');
    if (colonPos == std::string::npos) {
        displayError("Invalid server address format (expected IP:port)", ErrorType::CONFIG);
        return false;
    }
    
    serverIP = line.substr(0, colonPos);
    try {
        serverPort = static_cast<uint16_t>(std::stoi(line.substr(colonPos + 1)));
    } catch (...) {
        displayError("Invalid port number", ErrorType::CONFIG);
        return false;
    }
    
    // Line 2: username
    if (!std::getline(file, username) || username.empty()) {
        displayError("Invalid username - cannot be empty", ErrorType::CONFIG);
        return false;
    }
    
    if (username.length() > 100) {
        displayError("Username too long (max 100 characters)", ErrorType::CONFIG);
        return false;
    }
    
    // Line 3: filepath
    if (!std::getline(file, filepath) || filepath.empty()) {
        displayError("Invalid file path - cannot be empty", ErrorType::CONFIG);
        return false;
    }
    
    displayStatus("Configuration loaded", true, "transfer.info parsed successfully");
    return true;
}

/**
 * @brief Validates the client configuration parameters before starting the backup process.
 *
 * Checks that the server IP and port are set, verifies the existence and non-emptiness of the specified file, and updates transfer statistics with the file size.
 * Displays status and error messages for each validation step.
 *
 * @return true if all configuration parameters are valid; false otherwise.
 */
bool Client::validateConfiguration() {
    displayStatus("Validating configuration", true, "Checking parameters");
    
    // Validate server IP (Boost.Asio will handle IP validation during connect)
    if (serverIP.empty()) {
        displayError("Invalid IP address: empty", ErrorType::CONFIG);
        return false;
    }
    
    // Validate port
    if (serverPort == 0 || serverPort > 65535) {
        displayError("Invalid port number: " + std::to_string(serverPort), ErrorType::CONFIG);
        return false;
    }
    
    // Validate file exists and get size
    std::ifstream testFile(filepath, std::ios::binary);
    if (!testFile.is_open()) {
        displayError("File not found: " + filepath, ErrorType::FILE_IO);
        return false;
    }
    
    testFile.seekg(0, std::ios::end);
    stats.totalBytes = testFile.tellg();
    testFile.close();
    
    if (stats.totalBytes == 0) {
        displayError("File is empty: " + filepath, ErrorType::FILE_IO);
        return false;
    }
    
    displayStatus("File validation", true, filepath + " (" + formatBytes(stats.totalBytes) + ")");
    displayStatus("Server validation", true, serverIP + ":" + std::to_string(serverPort));
    displayStatus("Username validation", true, username);
    
    return true;
}

/**
 * @brief Loads client information from the "me.info" file.
 *
 * Reads the username and client ID from "me.info" and verifies that they match the expected values and format. The client ID is parsed from hexadecimal and stored internally. The private key is not loaded by this function.
 *
 * @return true if the information is successfully loaded and validated; false otherwise.
 */
bool Client::loadMeInfo() {
    std::ifstream file("me.info");
    if (!file.is_open()) {
        return false;
    }
    
    std::string line;
    
    // Line 1: username
    if (!std::getline(file, line) || line != username) {
        return false;
    }
    
    // Line 2: UUID hex
    if (!std::getline(file, line) || line.length() != 32) {
        return false;
    }
    
    auto bytes = hexToBytes(line);
    if (bytes.size() != CLIENT_ID_SIZE) {
        return false;
    }
    std::copy(bytes.begin(), bytes.end(), clientID.begin());
    
    displayStatus("Client ID loaded", true, "UUID: " + line.substr(0, 8) + "...");
    
    // Line 3: private key base64 (we'll load separately)
    return true;
}

/**
 * @brief Saves the client's username, ID, and private key to the me.info file.
 *
 * Writes the username, client ID in hexadecimal, and the base64-encoded RSA private key to "me.info".
 * Returns false if the file cannot be created or opened.
 *
 * @return true if the information was successfully saved; false otherwise.
 */
bool Client::saveMeInfo() {
    std::ofstream file("me.info");
    if (!file.is_open()) {
        displayError("Cannot create me.info", ErrorType::FILE_IO);
        return false;
    }
    
    file << username << "\n";
    std::string hexId = bytesToHex(clientID.data(), CLIENT_ID_SIZE);
    file << hexId << "\n";
    
    if (rsaPrivate) {
        std::string privateKey = rsaPrivate->getPrivateKey();
        std::string encoded = Base64Wrapper::encode(privateKey);
        file << encoded << "\n";
    }
    
    displayStatus("Client info saved", true, "me.info created");
    return true;
}

/**
 * @brief Loads the RSA private key from local storage.
 *
 * Attempts to load the private key from the binary file `priv.key`. If unavailable or invalid, tries to load a base64-encoded key from `me.info`, decodes it, and caches it to `priv.key`. Returns true on success, false otherwise.
 *
 * @return true if the private key was successfully loaded; false otherwise.
 */
bool Client::loadPrivateKey() {
    // Try priv.key first
    std::ifstream keyFile("priv.key", std::ios::binary);
    if (keyFile.is_open()) {
        std::string keyData((std::istreambuf_iterator<char>(keyFile)), std::istreambuf_iterator<char>());
        keyFile.close();
        
        try {
            // priv.key contains binary DER data, use the char* constructor
            rsaPrivate = new RSAPrivateWrapper(keyData.c_str(), keyData.length());
            displayStatus("Private key loaded", true, "From priv.key");
            return true;
        } catch (const std::exception& e) {
            displayStatus("Loading private key", false, std::string("Failed to parse priv.key: ") + e.what());
            delete rsaPrivate;
            rsaPrivate = nullptr;
        }
    }
    
    // Try me.info
    std::ifstream infoFile("me.info");
    if (!infoFile.is_open()) {
        return false;
    }
    
    std::string line;
    std::getline(infoFile, line); // skip username
    std::getline(infoFile, line); // skip UUID
    
    if (!std::getline(infoFile, line) || line.empty()) {
        return false;
    }
      try {
        std::string decoded = Base64Wrapper::decode(line);
        rsaPrivate = new RSAPrivateWrapper(decoded);
        
        // Save to priv.key
        std::ofstream privKey("priv.key", std::ios::binary);
        if (privKey.is_open()) {
            privKey.write(decoded.c_str(), decoded.length());
            displayStatus("Private key cached", true, "Saved to priv.key");
        }
        
        return true;
    } catch (...) {
        if (rsaPrivate) {
            delete rsaPrivate;
            rsaPrivate = nullptr;
        }
        return false;
    }
}

/**
 * @brief Saves the RSA private key to a file in binary format.
 *
 * Attempts to write the current RSA private key to "priv.key". Returns false if the key is unavailable or the file cannot be created.
 * @return true if the private key was successfully saved; false otherwise.
 */
bool Client::savePrivateKey() {
    if (!rsaPrivate) return false;
    
    std::string privateKey = rsaPrivate->getPrivateKey();
    std::ofstream file("priv.key", std::ios::binary);
    if (!file.is_open()) {
        displayError("Cannot create priv.key", ErrorType::FILE_IO);
        return false;
    }
    
    file.write(privateKey.c_str(), privateKey.length());
    displayStatus("Private key saved", true, "priv.key created");
    return true;
}

/**
 * @brief Establishes a TCP connection to the configured server.
 *
 * Attempts to resolve the server address and connect via TCP. Verifies the connection, sets socket options, and updates connection status. On failure, logs the error and resets the connection state.
 *
 * @return true if the connection is successfully established, false otherwise.
 */
bool Client::connectToServer() {
    try {
        socket = std::make_unique<boost::asio::ip::tcp::socket>(ioContext);
        
        boost::asio::ip::tcp::resolver resolver(ioContext);
        boost::asio::ip::tcp::resolver::results_type endpoints = 
            resolver.resolve(serverIP, std::to_string(serverPort));
        
        displayStatus("Connecting", true, "Establishing TCP connection...");
        
        boost::asio::connect(*socket, endpoints);

        // Verify the connection is actually established
        if (!socket->is_open()) {
            displayError("Socket failed to open", ErrorType::NETWORK);
            return false;
        }

        // Get the actual connected endpoint for verification
        auto localEndpoint = socket->local_endpoint();
        auto remoteEndpoint = socket->remote_endpoint();

        displayStatus("Connection verified", true,
                     "Local: " + localEndpoint.address().to_string() + ":" + std::to_string(localEndpoint.port()) +
                     " -> Remote: " + remoteEndpoint.address().to_string() + ":" + std::to_string(remoteEndpoint.port()));

        // Set socket options for timeouts and keep-alive
        socket->set_option(boost::asio::ip::tcp::no_delay(true));

        // Small delay to ensure connection is fully established
        std::this_thread::sleep_for(std::chrono::milliseconds(100));

        connected = true;
        displayStatus("Connected", true, "TCP connection established");
        
        // Update GUI connection status (optional)
        try {
            ClientGUIHelpers::updateConnectionStatus(true);
        } catch (...) {
            // GUI update failed - continue without GUI
        }
        
        return true;
        
    } catch (const std::exception& e) {        displayError("Connection failed: " + std::string(e.what()), ErrorType::NETWORK);
        socket.reset();
        connected = false;
        
        // Update GUI connection status (optional)
        try {
            ClientGUIHelpers::updateConnectionStatus(false);
        } catch (...) {
            // GUI update failed - continue without GUI
        }
        
        return false;
    }
}

/**
 * @brief Tests the connection to the server and measures latency.
 *
 * Sends a minimal request to the server and calculates the round-trip time. Returns true if the latency is less than one second, indicating a good connection.
 *
 * @return true if the connection latency is under one second, false otherwise.
 */
bool Client::testConnection() {
    auto start = std::chrono::steady_clock::now();
    
    // Send a small test request (empty payload)
    if (!sendRequest(0, {})) {
        return false;
    }
    
    auto end = std::chrono::steady_clock::now();
    auto latency = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
    
    displayStatus("Connection test", true, "Latency: " + std::to_string(latency) + "ms");
    return latency < 1000; // Good if under 1 second
}

/**
 * @brief Enables TCP keep-alive on the client socket to maintain a stable connection.
 *
 * Attempts to set the keep-alive option on the active socket. Updates connection status accordingly.
 */
void Client::enableKeepAlive() {
    if (socket && socket->is_open()) {
        try {
            socket->set_option(boost::asio::socket_base::keep_alive(true));
            keepAliveEnabled = true;
            displayStatus("Keep-alive", true, "Enabled for stable connection");
        } catch (const std::exception& e) {
            displayStatus("Keep-alive", false, "Could not enable: " + std::string(e.what()));
        }
    }
}

/**
 * @brief Closes the current TCP connection to the server and updates connection status.
 *
 * Releases the socket resource, marks the client as disconnected, and updates the GUI connection status if available.
 */
void Client::closeConnection() {
    if (socket && socket->is_open()) {
        try {
            socket->close();
        } catch (const std::exception&) {
            // Ignore errors during close
        }    }
    socket.reset();
    connected = false;
    
    // Update GUI connection status (optional)
    try {
        ClientGUIHelpers::updateConnectionStatus(false);
    } catch (...) {
        // GUI update failed - continue without GUI
    }
}

/**
 * @brief Sends a protocol request to the server with the specified code and payload.
 *
 * Constructs and transmits a request header in little-endian format, followed by the optional payload, over the established TCP connection. Returns false if the client is not connected or if any transmission error occurs.
 *
 * @param code Protocol request code to send.
 * @param payload Optional request payload data.
 * @return true if the request and payload are sent successfully; false otherwise.
 */
bool Client::sendRequest(uint16_t code, const std::vector<uint8_t>& payload) {
    if (!connected || !socket || !socket->is_open()) {
        displayError("Not connected to server", ErrorType::NETWORK);
        return false;
    }
    
    try {
        // CRITICAL FIX: Manually construct header bytes in little-endian format
        // The Python server expects little-endian format explicitly
        std::vector<uint8_t> headerBytes(23);  // RequestHeader is 23 bytes total

        // Client ID (16 bytes) - copy as-is
        std::copy(clientID.begin(), clientID.end(), headerBytes.begin());

        // Version (1 byte) - byte 16
        headerBytes[16] = CLIENT_VERSION;

        // Code (2 bytes, little-endian) - bytes 17-18
        headerBytes[17] = code & 0xFF;        // Low byte
        headerBytes[18] = (code >> 8) & 0xFF; // High byte

        // Payload size (4 bytes, little-endian) - bytes 19-22
        uint32_t payload_size_val = static_cast<uint32_t>(payload.size());
        headerBytes[19] = payload_size_val & 0xFF;         // Byte 0
        headerBytes[20] = (payload_size_val >> 8) & 0xFF;  // Byte 1
        headerBytes[21] = (payload_size_val >> 16) & 0xFF; // Byte 2
        headerBytes[22] = (payload_size_val >> 24) & 0xFF; // Byte 3
        
        // Debug: show header values for important requests
        if (code == REQ_REGISTER || code == REQ_RECONNECT || code == REQ_SEND_PUBLIC_KEY) {
            displayStatus("Debug: Request header", true,
                         "Version=" + std::to_string(CLIENT_VERSION) +
                         ", Code=" + std::to_string(code) +
                         ", PayloadSize=" + std::to_string(payload_size_val));

            // Add hex dump of header bytes for debugging
            std::stringstream hexDump;
            hexDump << "Header hex: ";
            for (size_t i = 0; i < headerBytes.size(); ++i) {
                hexDump << std::hex << std::setfill('0') << std::setw(2) << static_cast<int>(headerBytes[i]) << " ";
            }
            displayStatus("Debug: Header bytes", true, hexDump.str());
        }
        
        // Send header
        size_t headerBytesSent = boost::asio::write(*socket, boost::asio::buffer(headerBytes));
        if (headerBytesSent != headerBytes.size()) {
            displayError("Failed to send complete header", ErrorType::NETWORK);
            return false;
        }

        // Send payload if any
        if (!payload.empty()) {
            size_t payloadBytes = boost::asio::write(*socket, boost::asio::buffer(payload));
            if (payloadBytes != payload.size()) {
                displayError("Failed to send complete payload", ErrorType::NETWORK);
                return false;
            }
        }

        // Force flush the socket to ensure data is sent immediately
        ioContext.poll();

        // Debug: confirm data was sent for important requests
        if (code == REQ_REGISTER || code == REQ_RECONNECT || code == REQ_SEND_PUBLIC_KEY) {
            displayStatus("Debug: Data sent", true,
                         "Header: " + std::to_string(headerBytesSent) + " bytes, " +
                         "Payload: " + std::to_string(payload.size()) + " bytes");
        }

        return true;
        
    } catch (const std::exception& e) {
        displayError("Failed to send request: " + std::string(e.what()), ErrorType::NETWORK);
        return false;
    }
}

/**
 * @brief Receives a response from the server and populates the header and payload.
 *
 * Reads the response header from the server, validates the protocol version, checks for error codes, and reads the payload if present. Returns false if the connection is not open, the server version is invalid, an error code is received, or a network exception occurs.
 *
 * @param header Reference to a ResponseHeader struct to be filled with the received header data.
 * @param payload Reference to a vector to be filled with the response payload, if any.
 * @return true if the response is successfully received and valid; false otherwise.
 */
bool Client::receiveResponse(ResponseHeader& header, std::vector<uint8_t>& payload) {
    if (!connected || !socket || !socket->is_open()) {
        displayError("Not connected to server", ErrorType::NETWORK);
        return false;
    }
    
    try {
        // Receive header
        boost::asio::read(*socket, boost::asio::buffer(&header, sizeof(header)));
        
        // Check version
        if (header.version != SERVER_VERSION) {
            displayError("Invalid server version: " + std::to_string(header.version), ErrorType::PROTOCOL);
            return false;
        }
        
        // Check for error response
        if (header.code == RESP_ERROR) {
            displayError("Server returned general error", ErrorType::SERVER_ERROR);
            return false;
        }
        
        // Receive payload if any
        payload.clear();
        if (header.payload_size > 0) {
            payload.resize(header.payload_size);
            boost::asio::read(*socket, boost::asio::buffer(payload));
        }
        
        return true;
        
    } catch (const std::exception& e) {
        displayError("Failed to receive response: " + std::string(e.what()), ErrorType::NETWORK);
        return false;
    }
}

/**
 * @brief Registers the client with the server using the current username and RSA keys.
 *
 * Sends a registration request containing the username to the server. On success, receives and stores a new client ID, and saves registration information and the RSA private key locally. Returns false if registration fails due to protocol errors, authentication issues, or file I/O problems.
 *
 * @return true if registration succeeds and client information is saved; false otherwise.
 */
bool Client::performRegistration() {
    displayStatus("Starting registration", true, "Using pre-generated RSA keys");

    // RSA keys should already be generated during initialization
    if (!rsaPrivate) {
        displayError("RSA keys not available for registration", ErrorType::CRYPTO);
        return false;
    }
    
    // Prepare registration payload
    std::vector<uint8_t> payload(MAX_NAME_SIZE, 0);
    std::copy(username.begin(), username.end(), payload.begin());
      displayStatus("Sending registration", true, "Username: " + username);
    
    // Debug: show what we're sending
    displayStatus("Debug: Registration packet", true, 
                 "Payload size=" + std::to_string(payload.size()) + 
                 " bytes, Username='" + username + "'");
    
    // Send registration request
    if (!sendRequest(REQ_REGISTER, payload)) {
        return false;
    }
    
    // Receive response
    ResponseHeader header;
    std::vector<uint8_t> responsePayload;
    if (!receiveResponse(header, responsePayload)) {
        return false;
    }
    
    if (header.code == RESP_REGISTER_FAIL) {
        displayError("Registration failed: Username already exists", ErrorType::AUTHENTICATION);
        return false;
    }
    
    if (header.code != RESP_REGISTER_OK || responsePayload.size() != CLIENT_ID_SIZE) {
        displayError("Invalid registration response", ErrorType::PROTOCOL);
        return false;
    }
    
    // Store client ID
    std::copy(responsePayload.begin(), responsePayload.end(), clientID.begin());
    
    // Save info
    if (!saveMeInfo() || !savePrivateKey()) {
        displayError("Failed to save registration info", ErrorType::FILE_IO);
        return false;
    }
    
    displayStatus("Registration", true, "New client ID: " + bytesToHex(clientID.data(), 8) + "...");
    return true;
}

/**
 * @brief Attempts to reconnect to the server using the stored client credentials.
 *
 * Sends a reconnection request with the client's username, receives an encrypted AES key from the server, and decrypts it using the stored RSA private key. Returns true if reconnection and authentication succeed, false otherwise.
 *
 * @return true if reconnection and AES key decryption are successful; false otherwise.
 */
bool Client::performReconnection() {
    // Prepare reconnection payload
    std::vector<uint8_t> payload(MAX_NAME_SIZE, 0);
    std::copy(username.begin(), username.end(), payload.begin());
    
    displayStatus("Sending reconnection", true, "Client ID: " + bytesToHex(clientID.data(), 8) + "...");
    
    // Send reconnection request
    if (!sendRequest(REQ_RECONNECT, payload)) {
        return false;
    }
    
    // Receive response
    ResponseHeader header;
    std::vector<uint8_t> responsePayload;
    if (!receiveResponse(header, responsePayload)) {
        return false;
    }
    
    if (header.code == RESP_RECONNECT_FAIL) {
        return false;
    }
    
    if (header.code != RESP_RECONNECT_AES_SENT || responsePayload.size() <= CLIENT_ID_SIZE) {
        displayError("Invalid reconnection response", ErrorType::PROTOCOL);
        return false;
    }
    
    // Extract encrypted AES key
    std::vector<uint8_t> encryptedKey(responsePayload.begin() + CLIENT_ID_SIZE, responsePayload.end());
    
    displayStatus("Decrypting AES key", true, "Using stored RSA private key");
    
    // Decrypt AES key
    if (!decryptAESKey(encryptedKey)) {
        return false;
    }
    
    displayStatus("Reconnection", true, "Successfully authenticated");
    return true;
}

/**
 * @brief Sends the client's RSA public key to the server and establishes an AES-256 session key.
 *
 * Prepares and transmits a payload containing the username and RSA public key to the server. Upon receiving the server's response, extracts and decrypts the AES key for secure file transfer. Returns false if any step fails, including missing RSA keys, protocol errors, or decryption failure.
 *
 * @return true if the public key is sent and the AES key is successfully established; false otherwise.
 */
bool Client::sendPublicKey() {
    if (!rsaPrivate) {
        displayError("No RSA keys available", ErrorType::CRYPTO);
        return false;
    }
    
    // Prepare payload
    std::vector<uint8_t> payload(MAX_NAME_SIZE + RSA_KEY_SIZE, 0);
    
    // Add username
    std::copy(username.begin(), username.end(), payload.begin());
    
    // Add public key
    char publicKeyBuffer[RSAPublicWrapper::KEYSIZE];
    rsaPrivate->getPublicKey(publicKeyBuffer, RSAPublicWrapper::KEYSIZE);
    std::copy(publicKeyBuffer, publicKeyBuffer + RSAPublicWrapper::KEYSIZE, payload.begin() + MAX_NAME_SIZE);
    
    displayStatus("Sending public key", true, "RSA 1024-bit public key");
    
    // Send request
    if (!sendRequest(REQ_SEND_PUBLIC_KEY, payload)) {
        return false;
    }
    
    // Receive response
    ResponseHeader header;
    std::vector<uint8_t> responsePayload;
    if (!receiveResponse(header, responsePayload)) {
        return false;
    }
    
    if (header.code != RESP_PUBKEY_AES_SENT || responsePayload.size() <= CLIENT_ID_SIZE) {
        displayError("Invalid public key response", ErrorType::PROTOCOL);
        return false;
    }
    
    // Extract encrypted AES key
    std::vector<uint8_t> encryptedKey(responsePayload.begin() + CLIENT_ID_SIZE, responsePayload.end());
    
    displayStatus("Received AES key", true, "Encrypted with RSA");
    
    // Decrypt AES key
    if (!decryptAESKey(encryptedKey)) {
        return false;
    }
    
    displayStatus("Key exchange", true, "AES-256 key established");
    return true;
}

/**
 * @brief Encrypts and transfers the configured file to the server in encrypted packets.
 *
 * Reads the specified file, encrypts its contents using AES-256-CBC, splits the encrypted data into packets, and sends each packet to the server. After all packets are sent, waits for the server's CRC response and verifies file integrity.
 *
 * @return true if the file is successfully transferred and verified; false otherwise.
 */
bool Client::transferFile() {
    // Read file
    displayStatus("Reading file", true, filepath);
    auto fileData = readFile(filepath);
    if (fileData.empty()) {
        displayError("Cannot read file or file is empty", ErrorType::FILE_IO);
        return false;
    }
    
    stats.totalBytes = fileData.size();
    stats.reset();
    
    // Extract filename
    std::string filename = filepath;
    size_t lastSlash = filename.find_last_of("/\\");
    if (lastSlash != std::string::npos) {
        filename = filename.substr(lastSlash + 1);
    }
    
    displayStatus("File details", true, "Name: " + filename + ", Size: " + formatBytes(stats.totalBytes));
    displayStatus("Encrypting file", true, "AES-256-CBC encryption");
    
    // Encrypt file
    std::string encryptedData = encryptFile(fileData);
    if (encryptedData.empty()) {
        return false;
    }
    
    displayStatus("Encryption complete", true, "Encrypted size: " + formatBytes(encryptedData.size()));
    
    // Calculate packets
    size_t encryptedSize = encryptedData.size();
    uint16_t totalPackets = static_cast<uint16_t>((encryptedSize + MAX_PACKET_SIZE - 1) / MAX_PACKET_SIZE);
    
    displayStatus("Transfer preparation", true, "Splitting into " + std::to_string(totalPackets) + " packets");
    displaySeparator();
    
    // Send packets
    for (uint16_t packet = 1; packet <= totalPackets; packet++) {
        size_t offset = (packet - 1) * MAX_PACKET_SIZE;
        size_t chunkSize = std::min(MAX_PACKET_SIZE, encryptedSize - offset);
        
        std::string chunk = encryptedData.substr(offset, chunkSize);
        
        if (!sendFilePacket(filename, chunk, static_cast<uint32_t>(fileData.size()), packet, totalPackets)) {
            return false;
        }
        
        stats.update(offset + chunkSize);
        displayProgress("Transferring", stats.transferredBytes, encryptedData.size());
        
        if (packet % 10 == 0 || packet == totalPackets) {
            displayTransferStats();
        }
    }
    
    displaySeparator();
    displayStatus("Transfer complete", true, "All packets sent successfully");
    displayStatus("Waiting for server", true, "Server calculating CRC...");
    
    // Receive CRC response
    ResponseHeader header;
    std::vector<uint8_t> responsePayload;
    if (!receiveResponse(header, responsePayload)) {
        return false;
    }
    
    if (header.code != RESP_FILE_OK || responsePayload.size() < 279) {
        displayError("Invalid file transfer response", ErrorType::PROTOCOL);
        return false;
    }
    
    // Extract CRC
    uint32_t serverCRC;
    std::memcpy(&serverCRC, responsePayload.data() + 275, 4);
    
    // Verify CRC
    return verifyCRC(serverCRC, fileData, filename);
}

/**
 * @brief Sends a single encrypted file packet to the server.
 *
 * Constructs and transmits a file packet containing metadata (encrypted size, original size, packet number, total packets, and filename) along with the encrypted file data as part of the file transfer process.
 *
 * @param filename Name of the file being transferred.
 * @param encryptedData Encrypted chunk of file data for this packet.
 * @param originalSize Size of the original (unencrypted) data in this packet.
 * @param packetNum Sequence number of this packet (starting from 1).
 * @param totalPackets Total number of packets for the file transfer.
 * @return true if the packet was sent successfully; false otherwise.
 */
bool Client::sendFilePacket(const std::string& filename, const std::string& encryptedData,
                           uint32_t originalSize, uint16_t packetNum, uint16_t totalPackets) {
    // Create payload
    std::vector<uint8_t> payload;
    
    // Add metadata
    uint32_t encryptedSize = static_cast<uint32_t>(encryptedData.size());
    payload.insert(payload.end(), reinterpret_cast<uint8_t*>(&encryptedSize),
                   reinterpret_cast<uint8_t*>(&encryptedSize) + 4);
    
    payload.insert(payload.end(), reinterpret_cast<uint8_t*>(&originalSize),
                   reinterpret_cast<uint8_t*>(&originalSize) + 4);
    
    payload.insert(payload.end(), reinterpret_cast<uint8_t*>(&packetNum),
                   reinterpret_cast<uint8_t*>(&packetNum) + 2);
    
    payload.insert(payload.end(), reinterpret_cast<uint8_t*>(&totalPackets),
                   reinterpret_cast<uint8_t*>(&totalPackets) + 2);
    
    // Add filename (255 bytes)
    std::vector<uint8_t> filenameBytes(255, 0);
    std::copy(filename.begin(), filename.end(), filenameBytes.begin());
    payload.insert(payload.end(), filenameBytes.begin(), filenameBytes.end());
    
    // Add encrypted data
    payload.insert(payload.end(), encryptedData.begin(), encryptedData.end());
    
    return sendRequest(REQ_SEND_FILE, payload);
}

/**
 * @brief Verifies file integrity by comparing CRC32 checksums with the server and handles retry logic.
 *
 * Compares the CRC32 checksum calculated from the original file data with the checksum provided by the server. If the checksums match, confirms integrity and notifies the server. If they do not match, attempts to retry the file transfer up to a maximum number of retries. Aborts the operation if the maximum retries are exceeded.
 *
 * @param serverCRC The CRC32 checksum received from the server.
 * @param originalData The original file data used to calculate the local CRC32.
 * @param filename The name of the file being verified.
 * @return true if the CRCs match or a retry succeeds; false if verification fails after maximum retries.
 */
bool Client::verifyCRC(uint32_t serverCRC, const std::vector<uint8_t>& originalData, const std::string& filename) {
    displayStatus("Calculating CRC", true, "Using cksum algorithm");
    
    uint32_t clientCRC = calculateCRC32(originalData.data(), originalData.size());
    
    displayStatus("CRC verification", true, "Server: " + std::to_string(serverCRC) + 
                  ", Client: " + std::to_string(clientCRC));
    
    // Prepare filename payload
    std::vector<uint8_t> payload(255, 0);
    std::copy(filename.begin(), filename.end(), payload.begin());
    
    if (serverCRC == clientCRC) {
        displayStatus("CRC verification", true, "✓ Checksums match - file integrity confirmed");
        sendRequest(REQ_CRC_OK, payload);
        
        // Wait for ACK
        ResponseHeader header;
        std::vector<uint8_t> responsePayload;
        receiveResponse(header, responsePayload);
        
        return true;
    } else {
        crcRetries++;
        if (crcRetries < MAX_RETRIES) {
            displayStatus("CRC verification", false, "Mismatch - Retry " + std::to_string(crcRetries) + " of " + std::to_string(MAX_RETRIES));
            sendRequest(REQ_CRC_RETRY, payload);
            
            // Reset CRC retries for next attempt
            int savedRetries = crcRetries;
            crcRetries = 0;
            
            // Retry the transfer
            bool result = transferFile();
            
            // Restore retry count if transfer failed
            if (!result) {
                crcRetries = savedRetries;
            }
            
            return result;
        } else {
            displayStatus("CRC verification", false, "Maximum retries exceeded - aborting");
            sendRequest(REQ_CRC_ABORT, payload);
            return false;
        }
    }
}

/**
 * @brief Generates a new RSA private key for the client.
 *
 * Attempts to create a new RSA private key and stores it in the client instance. Returns true on success, or false if key generation fails.
 * @return true if the RSA key was generated successfully, false otherwise.
 */
bool Client::generateRSAKeys() {
    try {
        auto start = std::chrono::steady_clock::now();
        rsaPrivate = new RSAPrivateWrapper();
        auto end = std::chrono::steady_clock::now();

        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
        displayStatus("RSA key generation", true, "512-bit keys generated in " + std::to_string(duration) + "ms");
        return true;
    } catch (const std::exception& e) {
        displayError("Failed to generate RSA keys: " + std::string(e.what()), ErrorType::CRYPTO);
        return false;
    } catch (...) {
        displayError("Failed to generate RSA keys: Unknown exception", ErrorType::CRYPTO);
        return false;
    }
}

/**
 * @brief Decrypts an AES key using the client's RSA private key.
 *
 * Attempts to decrypt the provided RSA-encrypted AES key and validates its size. Reports errors if the private key is unavailable, decryption fails, or the resulting key is not 256 bits.
 *
 * @param encryptedKey The RSA-encrypted AES key as a byte vector.
 * @return true if decryption and validation succeed; false otherwise.
 */
bool Client::decryptAESKey(const std::vector<uint8_t>& encryptedKey) {
    if (!rsaPrivate) {
        displayError("No RSA private key available", ErrorType::CRYPTO);
        return false;
    }
    
    try {
        std::string encrypted(reinterpret_cast<const char*>(encryptedKey.data()), encryptedKey.size());
        aesKey = rsaPrivate->decrypt(encrypted);
        
        if (aesKey.size() != AES_KEY_SIZE) {
            displayError("Invalid AES key size: " + std::to_string(aesKey.size()) + " bytes (expected 32)", ErrorType::CRYPTO);
            return false;
        }
        
        displayStatus("AES key decrypted", true, "256-bit key ready");
        return true;
    } catch (...) {
        displayError("Failed to decrypt AES key", ErrorType::CRYPTO);
        return false;
    }
}

/**
 * @brief Encrypts file data using AES-256-CBC with a static zero IV.
 *
 * Encrypts the provided data buffer using the stored 32-byte AES key in CBC mode with a static initialization vector of all zeros, as required by the protocol. Returns the encrypted data as a string, or an empty string if encryption fails or the key is invalid.
 *
 * @param data The file data to encrypt.
 * @return std::string The encrypted data, or an empty string on failure.
 */
std::string Client::encryptFile(const std::vector<uint8_t>& data) {
    if (aesKey.empty()) {
        displayError("No AES key available", ErrorType::CRYPTO);
        return "";
    }
      try {
        auto start = std::chrono::steady_clock::now();
        // Debug: Check actual AES key size
        displayStatus("AES key debug", true, "Key size: " + std::to_string(aesKey.size()) + " bytes");
        
        if (aesKey.size() != 32) {
            displayError("Invalid AES key size: " + std::to_string(aesKey.size()) + " bytes (expected 32)", ErrorType::CRYPTO);
            return "";
        }
        
        // Use 32-byte key and static IV of all zeros for protocol compliance
        AESWrapper aes(reinterpret_cast<const unsigned char*>(aesKey.c_str()), 32, true);
        std::string result = aes.encrypt(reinterpret_cast<const char*>(data.data()), data.size());
        auto end = std::chrono::steady_clock::now();
        
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
        double speed = (data.size() / 1024.0 / 1024.0) / (duration / 1000.0);
        
        displayStatus("Encryption performance", true, 
                     std::to_string(duration) + "ms (" + 
                     std::to_string(static_cast<int>(speed)) + " MB/s)");
        
        return result;
    } catch (...) {
        displayError("Failed to encrypt file", ErrorType::CRYPTO);
        return "";
    }
}

/**
 * @brief Reads the contents of a file into a byte vector.
 *
 * Opens the specified file in binary mode and reads its entire contents into a vector of bytes.
 * Returns an empty vector if the file cannot be opened.
 *
 * @param path Path to the file to be read.
 * @return std::vector<uint8_t> Vector containing the file's contents, or empty if the file cannot be opened.
 */
std::vector<uint8_t> Client::readFile(const std::string& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file.is_open()) {
        return {};
    }
    
    file.seekg(0, std::ios::end);
    size_t size = file.tellg();
    file.seekg(0, std::ios::beg);
    
    std::vector<uint8_t> data(size);
    
    // Read in chunks for better performance
    size_t bytesRead = 0;
    while (bytesRead < size) {
        size_t toRead = std::min(OPTIMAL_BUFFER_SIZE, size - bytesRead);
        file.read(reinterpret_cast<char*>(data.data() + bytesRead), toRead);
        bytesRead += file.gcount();
    }
    
    return data;
}

/**
 * @brief Converts a byte array to its hexadecimal string representation.
 *
 * @param data Pointer to the byte array.
 * @param size Number of bytes to convert.
 * @return std::string Hexadecimal string representing the input bytes.
 */
std::string Client::bytesToHex(const uint8_t* data, size_t size) {
    std::stringstream ss;
    ss << std::hex << std::setfill('0');
    for (size_t i = 0; i < size; i++) {
        ss << std::setw(2) << static_cast<int>(data[i]);
    }
    return ss.str();
}

/**
 * @brief Converts a hexadecimal string to a vector of bytes.
 *
 * The input string must have an even length and contain only valid hexadecimal characters.
 *
 * @param hex Hexadecimal string to convert.
 * @return std::vector<uint8_t> Byte vector representing the decoded data.
 */
std::vector<uint8_t> Client::hexToBytes(const std::string& hex) {
    std::vector<uint8_t> bytes;
    for (size_t i = 0; i < hex.length(); i += 2) {
        std::string byteString = hex.substr(i, 2);
        bytes.push_back(static_cast<uint8_t>(std::stoi(byteString, nullptr, 16)));
    }
    return bytes;
}

/**
 * @brief Calculates the CRC32 checksum of the given data buffer.
 *
 * @param data Pointer to the data buffer.
 * @param size Number of bytes in the buffer.
 * @return uint32_t CRC32 checksum value.
 */
uint32_t Client::calculateCRC32(const uint8_t* data, size_t size) {
    return calculateCRC(data, size);
}

/**
 * @brief Converts a byte count to a human-readable string with appropriate units.
 *
 * Formats the given number of bytes into a string using B, KB, MB, or GB units with two decimal places.
 *
 * @param bytes The number of bytes to format.
 * @return std::string The formatted string representing the size in human-readable units.
 */
std::string Client::formatBytes(size_t bytes) {
    const char* sizes[] = {"B", "KB", "MB", "GB"};
    int order = 0;
    double size = static_cast<double>(bytes);
    
    while (size >= 1024 && order < 3) {
        order++;
        size /= 1024;
    }
    
    std::stringstream ss;
    ss << std::fixed << std::setprecision(2) << size << " " << sizes[order];
    return ss.str();
}

/**
 * @brief Converts a duration in seconds to a human-readable string.
 *
 * Formats the duration as "Xs", "Ym Zs", or "Wh Xm" depending on the length.
 *
 * @param seconds Duration in seconds.
 * @return std::string Human-readable duration string.
 */
std::string Client::formatDuration(int seconds) {
    if (seconds < 60) {
        return std::to_string(seconds) + "s";
    } else if (seconds < 3600) {
        int minutes = seconds / 60;
        int secs = seconds % 60;
        return std::to_string(minutes) + "m " + std::to_string(secs) + "s";
    } else {
        int hours = seconds / 3600;
        int minutes = (seconds % 3600) / 60;
        return std::to_string(hours) + "h " + std::to_string(minutes) + "m";
    }
}

/**
 * @brief Returns the current local time as a string in HH:MM:SS format.
 *
 * @return std::string Current timestamp formatted as hours, minutes, and seconds.
 */
std::string Client::getCurrentTimestamp() {
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    std::stringstream ss;
    ss << std::put_time(std::localtime(&time_t), "%H:%M:%S");
    return ss.str();
}

/**
 * @brief Displays a timestamped status message for an operation, indicating success or failure.
 *
 * Shows the operation name with a colored status indicator and optional details. On Windows, also updates the GUI status if available.
 *
 * @param operation Name or description of the operation.
 * @param success Whether the operation succeeded.
 * @param details Optional additional information to display.
 */
void Client::displayStatus(const std::string& operation, bool success, const std::string& details) {
#ifdef _WIN32
    clearLine();
    
    std::cout << "[" << getCurrentTimestamp() << "] ";
    
    if (success) {
        SetConsoleTextAttribute(hConsole, FOREGROUND_GREEN | FOREGROUND_INTENSITY);
        std::cout << "[OK] ";
    } else {
        SetConsoleTextAttribute(hConsole, FOREGROUND_RED | FOREGROUND_INTENSITY);
        std::cout << "[FAIL] ";
    }
    
    SetConsoleTextAttribute(hConsole, savedAttributes);
    std::cout << operation;
    
    if (!details.empty()) {
        SetConsoleTextAttribute(hConsole, FOREGROUND_INTENSITY);
        std::cout << " - " << details;
        SetConsoleTextAttribute(hConsole, savedAttributes);
    }
    std::cout << std::endl;
    
    // Update GUI operation status (optional)
    try {
        ClientGUIHelpers::updateOperation(operation, success, details);
    } catch (...) {
        // GUI update failed - continue without GUI
    }
#else
    std::cout << "[" << getCurrentTimestamp() << "] ";
    std::cout << (success ? "[OK] " : "[FAIL] ") << operation;
    if (!details.empty()) {
        std::cout << " - " << details;
    }
    std::cout << std::endl;
#endif
}

/**
 * @brief Displays a progress bar for the current operation in the console.
 *
 * Shows the percentage completed and bytes transferred out of the total, updating in place. On Windows, uses colored output and optionally updates GUI progress if available.
 *
 * @param operation Name or description of the current operation.
 * @param current Number of bytes or units completed.
 * @param total Total number of bytes or units to complete.
 */
void Client::displayProgress(const std::string& operation, size_t current, size_t total) {
    if (total == 0) return;
    
    int percentage = static_cast<int>((current * 100) / total);
    
#ifdef _WIN32
    clearLine();
    std::cout << operation << " [";
    
    const int barWidth = 40;
    int pos = (barWidth * current) / total;
    
    SetConsoleTextAttribute(hConsole, FOREGROUND_GREEN | FOREGROUND_INTENSITY);
    for (int i = 0; i < pos; i++) std::cout << "█";
    
    SetConsoleTextAttribute(hConsole, FOREGROUND_GREEN);
    for (int i = pos; i < barWidth; i++) std::cout << "░";
    
    SetConsoleTextAttribute(hConsole, savedAttributes);
    std::cout << "] " << std::setw(3) << percentage << "% (" 
              << formatBytes(current) << "/" << formatBytes(total) << ")\r";
    std::cout.flush();
    
    if (current >= total) {
        std::cout << std::endl;
    }
    
    // Update GUI progress (optional)
    try {
        std::string speed = "";
        std::string eta = "";
        if (stats.currentSpeed > 0) {
            speed = formatBytes(static_cast<size_t>(stats.currentSpeed)) + "/s";
        }
        if (stats.estimatedTimeRemaining > 0) {
            eta = formatDuration(stats.estimatedTimeRemaining);
        }
        ClientGUIHelpers::updateProgress(static_cast<int>(current), static_cast<int>(total), speed, eta);
    } catch (...) {
        // GUI update failed - continue without GUI
    }
#else
    std::cout << "\r" << operation << " " << percentage << "% (" 
              << formatBytes(current) << "/" << formatBytes(total) << ")";
    std::cout.flush();
    if (current >= total) {
        std::cout << std::endl;
    }
#endif
}

/**
 * @brief Displays current file transfer statistics including speed, average speed, and estimated time remaining.
 *
 * Shows a formatted summary of transfer performance metrics in the console, with colored output on Windows.
 */
void Client::displayTransferStats() {
#ifdef _WIN32
    SetConsoleTextAttribute(hConsole, FOREGROUND_BLUE | FOREGROUND_GREEN | FOREGROUND_INTENSITY);
    std::cout << "\r[STATS] ";
    SetConsoleTextAttribute(hConsole, savedAttributes);
    
    std::cout << "Speed: " << formatBytes(static_cast<size_t>(stats.currentSpeed)) << "/s | "
              << "Avg: " << formatBytes(static_cast<size_t>(stats.averageSpeed)) << "/s | "
              << "ETA: " << formatDuration(stats.estimatedTimeRemaining) << "    " << std::endl;
#else
    std::cout << "\n[STATS] Speed: " << formatBytes(static_cast<size_t>(stats.currentSpeed)) << "/s | "
              << "Avg: " << formatBytes(static_cast<size_t>(stats.averageSpeed)) << "/s | "
              << "ETA: " << formatDuration(stats.estimatedTimeRemaining) << std::endl;
#endif
}

/**
 * @brief Displays the client splash screen with version, build date, protocol, and encryption details.
 *
 * Clears the console and prints a formatted banner summarizing client version, build information, protocol version, and encryption algorithms.
 * Uses colored output on Windows.
 */
void Client::displaySplashScreen() {
#ifdef _WIN32
    system("cls");
    
    SetConsoleTextAttribute(hConsole, FOREGROUND_BLUE | FOREGROUND_GREEN | FOREGROUND_INTENSITY);
    std::cout << "\n╔════════════════════════════════════════════╗\n";
    std::cout << "║     ENCRYPTED FILE BACKUP CLIENT v1.0      ║\n";
    std::cout << "╚════════════════════════════════════════════╝\n";
    
    SetConsoleTextAttribute(hConsole, savedAttributes);
    std::cout << "  Build Date: " << __DATE__ << " " << __TIME__ << "\n";
    std::cout << "  Protocol Version: " << static_cast<int>(CLIENT_VERSION) << "\n";
    std::cout << "  Encryption: RSA-1024 + AES-256-CBC\n\n";
#else
    std::cout << "\n============================================\n";
    std::cout << "     ENCRYPTED FILE BACKUP CLIENT v1.0      \n";
    std::cout << "============================================\n";
    std::cout << "  Build Date: " << __DATE__ << " " << __TIME__ << "\n";
    std::cout << "  Protocol Version: " << static_cast<int>(CLIENT_VERSION) << "\n";
    std::cout << "  Encryption: RSA-1024 + AES-256-CBC\n\n";
#endif
}

/**
 * @brief Clears the current console line.
 *
 * Overwrites or erases the current line in the console output, ensuring that any previous content is removed before new output is displayed. Uses platform-specific methods for Windows and other systems.
 */
void Client::clearLine() {
#ifdef _WIN32
    std::cout << "\r" << std::string(120, ' ') << "\r";
    std::cout.flush();
#else
    std::cout << "\r\033[K";
    std::cout.flush();
#endif
}

/**
 * @brief Displays the current connection and transfer configuration details.
 *
 * Prints the server address, client username, file path, and file size to the console.
 */
void Client::displayConnectionInfo() {
    displaySeparator();
    std::cout << "Connection Details:\n";
    std::cout << "  Server Address: " << serverIP << ":" << serverPort << "\n";
    std::cout << "  Client Name: " << username << "\n";
    std::cout << "  File to Transfer: " << filepath << "\n";
    std::cout << "  File Size: " << formatBytes(stats.totalBytes) << "\n";
    displaySeparator();
}

/**
 * @brief Displays an error message with categorized error type.
 *
 * Sets the last error type and details, prints a formatted error message to the console with appropriate category tags, and updates the GUI error status and notification if available.
 */
void Client::displayError(const std::string& message, ErrorType type) {
    lastError = type;
    lastErrorDetails = message;
    
    // Temporarily show actual error message for debugging
    // Check if this is a server error response
    // if (message.find("server") != std::string::npos || 
    //     message.find("response") != std::string::npos ||
    //     type == ErrorType::SERVER_ERROR) {
    //     std::cerr << "server responded with an error" << std::endl;
    // } else {
#ifdef _WIN32
        SetConsoleTextAttribute(hConsole, FOREGROUND_RED | FOREGROUND_INTENSITY);
        std::cerr << "[ERROR] ";
        SetConsoleTextAttribute(hConsole, savedAttributes);
#else
        std::cerr << "[ERROR] ";
#endif
        
        switch (type) {
            case ErrorType::NETWORK:
                std::cerr << "[NETWORK] ";
                break;
            case ErrorType::FILE_IO:
                std::cerr << "[FILE] ";
                break;
            case ErrorType::PROTOCOL:
                std::cerr << "[PROTOCOL] ";
                break;
            case ErrorType::CRYPTO:
                std::cerr << "[CRYPTO] ";
                break;
            case ErrorType::CONFIG:
                std::cerr << "[CONFIG] ";
                break;            case ErrorType::AUTHENTICATION:
                std::cerr << "[AUTH] ";
                break;
            default:
                break;
        }
          std::cerr << message << std::endl;
    
    // Update GUI error status and show notification (optional)
    try {
        ClientGUIHelpers::updateError(message);
        ClientGUIHelpers::showNotification("Backup Error", message);
    } catch (...) {
        // GUI update failed - continue without GUI
    }
    // }
}

/**
 * @brief Prints a horizontal separator line to the console.
 *
 * On Windows, uses a bold line character and restores console attributes; on other platforms, uses a standard dash.
 */
void Client::displaySeparator() {
#ifdef _WIN32
    SetConsoleTextAttribute(hConsole, FOREGROUND_INTENSITY);
    std::cout << std::string(60, '─') << std::endl;
    SetConsoleTextAttribute(hConsole, savedAttributes);
#else
    std::cout << std::string(60, '-') << std::endl;
#endif
}

/**
 * @brief Displays the current operation phase with visual emphasis.
 *
 * Prints the specified phase to the console with formatting and color (on Windows), and updates the GUI phase indicator if available.
 *
 * @param phase Name or description of the current phase.
 */
void Client::displayPhase(const std::string& phase) {
#ifdef _WIN32
    std::cout << "\n";
    SetConsoleTextAttribute(hConsole, FOREGROUND_BLUE | FOREGROUND_GREEN | FOREGROUND_INTENSITY);
    std::cout << "▶ " << phase << std::endl;
    SetConsoleTextAttribute(hConsole, savedAttributes);
    displaySeparator();
    
    // Update GUI phase (optional)
    try {
        ClientGUIHelpers::updatePhase(phase);
    } catch (...) {
        // GUI update failed - continue without GUI
    }
#else
    std::cout << "\n> " << phase << std::endl;
    displaySeparator();
#endif
}

/**
 * @brief Displays a summary of the completed file backup operation.
 *
 * Prints a formatted summary including file name, size, duration, average speed, server address, and timestamp. Also shows a completion notification if GUI support is available.
 */
void Client::displaySummary() {
    auto endTime = std::chrono::steady_clock::now();
    auto totalDuration = std::chrono::duration_cast<std::chrono::seconds>(endTime - operationStartTime).count();
    
    displaySeparator();
#ifdef _WIN32
    SetConsoleTextAttribute(hConsole, FOREGROUND_GREEN | FOREGROUND_INTENSITY);
    std::cout << "✓ BACKUP COMPLETED SUCCESSFULLY\n";
    SetConsoleTextAttribute(hConsole, savedAttributes);
#else
    std::cout << "✓ BACKUP COMPLETED SUCCESSFULLY\n";
#endif
    
    std::cout << "\nTransfer Summary:\n";
    std::cout << "  File: " << filepath << "\n";
    std::cout << "  Size: " << formatBytes(stats.totalBytes) << "\n";
    std::cout << "  Duration: " << formatDuration(static_cast<int>(totalDuration)) << "\n";
    std::cout << "  Average Speed: " << formatBytes(static_cast<size_t>(stats.averageSpeed)) << "/s\n";    std::cout << "  Server: " << serverIP << ":" << serverPort << "\n";
    std::cout << "  Timestamp: " << getCurrentTimestamp() << "\n";
    displaySeparator();
    
    // Show GUI completion notification (optional)
    try {
        std::string successMessage = "File backup completed successfully!\n\nFile: " + filepath + 
                                   "\nSize: " + formatBytes(stats.totalBytes) + 
                                   "\nDuration: " + formatDuration(static_cast<int>(totalDuration));
        ClientGUIHelpers::showNotification("Backup Complete", successMessage);
    } catch (...) {
        // GUI notification failed - continue without GUI
    }
}

/**
 * @brief Entry point for the encrypted file backup client application.
 *
 * Initializes the client, performs configuration and authentication, and executes the file backup process. Handles errors and displays notifications via console and optional GUI on Windows.
 *
 * @return int Returns 0 on successful backup, or 1 on failure or exception.
 */
int main() {
    try {
        Client client;

        if (!client.initialize()) {
            std::cerr << "Fatal: Client initialization failed" << std::endl;
#ifdef _WIN32
            // Show error notification via GUI if available
            try {
                ClientGUIHelpers::showNotification("Backup Error", "Client initialization failed");
                ClientGUIHelpers::updateError("Initialization failed");
            } catch (...) {}

            // Keep window open to show error
            std::cout << "\nPress Enter to exit...";
            std::cin.get();
#endif
            return 1;
        }

        if (!client.run()) {
            std::cerr << "Fatal: File backup failed" << std::endl;
#ifdef _WIN32
            // Show error notification via GUI if available
            try {
                ClientGUIHelpers::showNotification("Backup Error", "File backup operation failed");
                ClientGUIHelpers::updateError("Backup failed");
            } catch (...) {}

            // Keep window open to show error
            std::cout << "\nPress Enter to exit...";
            std::cin.get();
#endif
            return 1;
        }

        std::cout << "\nBackup completed successfully!" << std::endl;

#ifdef _WIN32
        // Show success notification via GUI if available
        try {
            ClientGUIHelpers::showNotification("Backup Complete", "File backup completed successfully!");
            ClientGUIHelpers::updatePhase("Backup Complete");
        } catch (...) {}

        // Keep window open to show success
        std::cout << "\nPress Enter to exit...";
        std::cin.get();
#endif

        return 0;

    } catch (const std::exception& e) {
        std::cerr << "Fatal exception: " << e.what() << std::endl;
#ifdef _WIN32
        try {
            ClientGUIHelpers::showNotification("Critical Error", std::string("Exception: ") + e.what());
            ClientGUIHelpers::updateError(std::string("Critical error: ") + e.what());
        } catch (...) {}

        std::cout << "\nPress Enter to exit...";
        std::cin.get();
#endif
        return 1;
    } catch (...) {
        std::cerr << "Fatal: Unknown exception occurred" << std::endl;
#ifdef _WIN32
        try {
            ClientGUIHelpers::showNotification("Critical Error", "Unknown exception occurred");
            ClientGUIHelpers::updateError("Unknown critical error");
        } catch (...) {}

        std::cout << "\nPress Enter to exit...";
        std::cin.get();
#endif
        return 1;
    }
}