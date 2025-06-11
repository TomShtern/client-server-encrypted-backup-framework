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
#include "../../include/client/cksum.h"
#include "../../include/wrappers/AESWrapper.h"
#include "../../include/wrappers/Base64Wrapper.h"
#include "../../include/wrappers/RSAWrapper.h"

// Optional GUI support
#ifdef _WIN32
#include "../../include/client/ClientGUI.h"
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
    
    TransferStats() : totalBytes(0), transferredBytes(0), lastTransferredBytes(0),
                      currentSpeed(0.0), averageSpeed(0.0), estimatedTimeRemaining(0) {}
    
    void reset() {
        startTime = std::chrono::steady_clock::now();
        lastUpdateTime = startTime;
        transferredBytes = 0;
        lastTransferredBytes = 0;
        currentSpeed = 0.0;
        averageSpeed = 0.0;
        estimatedTimeRemaining = 0;
    }
    
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

// Constructor
Client::Client() : socket(nullptr), connected(false), rsaPrivate(nullptr), 
                   fileRetries(0), crcRetries(0), reconnectAttempts(0),
                   keepAliveEnabled(false), lastError(ErrorType::NONE) {
    std::fill(clientID.begin(), clientID.end(), 0);
    
#ifdef _WIN32
    hConsole = GetStdHandle(STD_OUTPUT_HANDLE);
    GetConsoleScreenBufferInfo(hConsole, &consoleInfo);
    savedAttributes = consoleInfo.wAttributes;
      // Initialize GUI (optional - graceful failure)
    // Temporarily disabled for debugging
    // try {
    //     ClientGUIHelpers::initializeGUI();
    // } catch (...) {
    //     // GUI initialization failed - continue without GUI
    // }
#endif
}

// Destructor
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

// Initialize client
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

// Main client run function
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

// Read transfer.info configuration
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

// Validate configuration
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

// Load me.info
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

// Save me.info
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

// Load private key
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

// Save private key
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

// Connect to server
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

// Test connection quality
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

// Enable keep-alive
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

// Close connection
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

// Send request to server
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

// Receive response from server
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

// Perform registration
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

// Perform reconnection
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

// Send public key
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

// Transfer file
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

// Send file packet
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

// Verify CRC
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

// Generate RSA keys
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

// Decrypt AES key
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

// Encrypt file with AES
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

// Read file
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

// Convert bytes to hex string
std::string Client::bytesToHex(const uint8_t* data, size_t size) {
    std::stringstream ss;
    ss << std::hex << std::setfill('0');
    for (size_t i = 0; i < size; i++) {
        ss << std::setw(2) << static_cast<int>(data[i]);
    }
    return ss.str();
}

// Convert hex string to bytes
std::vector<uint8_t> Client::hexToBytes(const std::string& hex) {
    std::vector<uint8_t> bytes;
    for (size_t i = 0; i < hex.length(); i += 2) {
        std::string byteString = hex.substr(i, 2);
        bytes.push_back(static_cast<uint8_t>(std::stoi(byteString, nullptr, 16)));
    }
    return bytes;
}

// Calculate CRC32 using provided wrapper
uint32_t Client::calculateCRC32(const uint8_t* data, size_t size) {
    return calculateCRC(data, size);
}

// Format bytes to human readable
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

// Format duration to human readable
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

// Get current timestamp
std::string Client::getCurrentTimestamp() {
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    std::stringstream ss;
    ss << std::put_time(std::localtime(&time_t), "%H:%M:%S");
    return ss.str();
}

// Visual feedback functions
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

void Client::clearLine() {
#ifdef _WIN32
    std::cout << "\r" << std::string(120, ' ') << "\r";
    std::cout.flush();
#else
    std::cout << "\r\033[K";
    std::cout.flush();
#endif
}

void Client::displayConnectionInfo() {
    displaySeparator();
    std::cout << "Connection Details:\n";
    std::cout << "  Server Address: " << serverIP << ":" << serverPort << "\n";
    std::cout << "  Client Name: " << username << "\n";
    std::cout << "  File to Transfer: " << filepath << "\n";
    std::cout << "  File Size: " << formatBytes(stats.totalBytes) << "\n";
    displaySeparator();
}

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

void Client::displaySeparator() {
#ifdef _WIN32
    SetConsoleTextAttribute(hConsole, FOREGROUND_INTENSITY);
    std::cout << std::string(60, '─') << std::endl;
    SetConsoleTextAttribute(hConsole, savedAttributes);
#else
    std::cout << std::string(60, '-') << std::endl;
#endif
}

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

// Main function
int main() {
    // Write to a log file so we can see what's happening
    std::ofstream logFile("client_debug.log", std::ios::app);
    logFile << "=== ENCRYPTED BACKUP CLIENT DEBUG MODE ===" << std::endl;
    logFile << "Application started at: " << __DATE__ << " " << __TIME__ << std::endl;
    logFile.flush();
    
    // Also try console output
    std::cout << "=== ENCRYPTED BACKUP CLIENT DEBUG MODE ===" << std::endl;
    std::cout << "Console application started!" << std::endl;
    std::cout << "Starting client with console output..." << std::endl;

    try {
        logFile << "About to create client object..." << std::endl;
        logFile.flush();
        std::cout << "About to create client object..." << std::endl;
        std::cout.flush();
        
        Client client;
        logFile << "Client object created successfully!" << std::endl;
        logFile.flush();
        std::cout << "Client object created successfully!" << std::endl;

        std::cout << "About to initialize client..." << std::endl;
        std::cout.flush();
        
        if (!client.initialize()) {
            std::cerr << "Fatal: Client initialization failed" << std::endl;
            std::cout << "\nPress Enter to exit...";
            std::cin.get();
            return 1;
        }

        std::cout << "Client initialized successfully. Starting backup operation..." << std::endl;
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