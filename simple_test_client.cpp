#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <winsock2.h>
#include <ws2tcpip.h>

#pragma comment(lib, "ws2_32.lib")

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

bool initializeWinsock() {
    WSADATA wsaData;
    int result = WSAStartup(MAKEWORD(2, 2), &wsaData);
    if (result != 0) {
        std::cout << "WSAStartup failed: " << result << std::endl;
        return false;
    }
    return true;
}

void cleanupWinsock() {
    WSACleanup();
}

bool connectToServer(const std::string& ip, int port, SOCKET& sock) {
    sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (sock == INVALID_SOCKET) {
        std::cout << "Socket creation failed: " << WSAGetLastError() << std::endl;
        return false;
    }

    sockaddr_in serverAddr;
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_port = htons(port);
    inet_pton(AF_INET, ip.c_str(), &serverAddr.sin_addr);

    int result = connect(sock, (sockaddr*)&serverAddr, sizeof(serverAddr));
    if (result == SOCKET_ERROR) {
        std::cout << "Connection failed: " << WSAGetLastError() << std::endl;
        closesocket(sock);
        return false;
    }

    std::cout << "Connected to server " << ip << ":" << port << std::endl;
    return true;
}

bool sendData(SOCKET sock, const void* data, int size) {
    int sent = send(sock, (const char*)data, size, 0);
    if (sent == SOCKET_ERROR) {
        std::cout << "Send failed: " << WSAGetLastError() << std::endl;
        return false;
    }
    return sent == size;
}

bool receiveData(SOCKET sock, void* data, int size) {
    int received = recv(sock, (char*)data, size, 0);
    if (received == SOCKET_ERROR) {
        std::cout << "Receive failed: " << WSAGetLastError() << std::endl;
        return false;
    }
    return received == size;
}

int main() {
    std::cout << "=== SIAPLECLAQSET CONNECTION TEST ===" << std::endl;
    
    // Read configuration
    std::ifstream configFile("transfer.info");
    if (!configFile.is_open()) {
        std::cout << "ERROR: Cannot open transfer.info" << std::endl;
        return 1;
    }
    
    std::string serverLine, username, filename;
    std::getline(configFile, serverLine);
    std::getline(configFile, username);
    std::getline(configFile, filename);
    configFile.close();
    
    // Parse server:port
    size_t colonPos = serverLine.find(':');
    if (colonPos == std::string::npos) {
        std::cout << "ERROR: Invalid server format" << std::endl;
        return 1;
    }
    
    std::string serverIP = serverLine.substr(0, colonPos);
    int serverPort = std::stoi(serverLine.substr(colonPos + 1));
    
    std::cout << "Server: " << serverIP << ":" << serverPort << std::endl;
    std::cout << "Username: " << username << std::endl;
    std::cout << "File: " << filename << std::endl;
    
    // Initialize Winsock
    if (!initializeWinsock()) {
        return 1;
    }
    
    // Connect to server
    SOCKET sock;
    if (!connectToServer(serverIP, serverPort, sock)) {
        cleanupWinsock();
        return 1;
    }
    
    std::cout << "Connection successful!" << std::endl;
    std::cout << "Testing basic communication..." << std::endl;
    
    // Send a simple registration request
    RequestHeader req = {};
    req.version = 3;
    req.code = htons(1025); // REQ_REGISTER
    req.payload_size = htonl(username.length());
    
    if (!sendData(sock, &req, sizeof(req))) {
        closesocket(sock);
        cleanupWinsock();
        return 1;
    }
    
    if (!sendData(sock, username.c_str(), username.length())) {
        closesocket(sock);
        cleanupWinsock();
        return 1;
    }
    
    std::cout << "Registration request sent!" << std::endl;
    
    // Try to receive response
    ResponseHeader resp;
    if (receiveData(sock, &resp, sizeof(resp))) {
        std::cout << "Received response!" << std::endl;
        std::cout << "Version: " << (int)resp.version << std::endl;
        std::cout << "Code: " << ntohs(resp.code) << std::endl;
        std::cout << "Payload size: " << ntohl(resp.payload_size) << std::endl;
        
        if (ntohs(resp.code) == 1600) {
            std::cout << "SUCCESS: Server accepted registration!" << std::endl;
        } else {
            std::cout << "Server response code: " << ntohs(resp.code) << std::endl;
        }
    } else {
        std::cout << "Failed to receive response" << std::endl;
    }
    
    closesocket(sock);
    cleanupWinsock();
    
    std::cout << "Test completed. Press Enter to exit..." << std::endl;
    std::cin.get();
    
    return 0;
}