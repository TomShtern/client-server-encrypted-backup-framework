// WebServerBackend.cpp - Simple HTTP API Server for HTML Client
// Provides REST API endpoints for the new HTML GUI client

#include "WebServerBackend.h"
#include <iostream>
#include <fstream>
#include <string>
#include <thread>
#include <map>
#include <mutex>
#include <chrono>
#include <sstream>
#include <ctime>
#include <vector>
#include <atomic>
#include <memory>
#include <functional>

// Boost includes
#include <boost/asio.hpp>
#include <boost/beast.hpp>
#include <boost/beast/http.hpp>

// Namespace aliases
namespace beast = boost::beast;
namespace http = beast::http;
namespace net = boost::asio;
using tcp = boost::asio::ip::tcp;

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "ws2_32.lib")
#else
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#endif

// Function pointers for backup operations
std::function<bool()> g_backup_callback = nullptr;  // Legacy callback
std::function<bool(const WebServerBackend::BackupConfig&)> g_backup_callback_with_config = nullptr;  // New callback

// Simple JSON object for responses
class JsonObject {
private:
    std::map<std::string, std::string> data_;

public:
    void set(const std::string& key, const std::string& value) {
        data_[key] = value;
    }

    void set(const std::string& key, bool value) {
        data_[key] = value ? "true" : "false";
    }

    void set(const std::string& key, int value) {
        data_[key] = std::to_string(value);
    }

    std::string serialize() const {
        std::ostringstream ss;
        ss << "{";
        bool first = true;
        for (const auto& pair : data_) {
            if (!first) ss << ",";
            ss << "\"" << pair.first << "\":\"" << pair.second << "\"";
            first = false;
        }
        ss << "}";
        return ss.str();
    }
};

// Application state management
class BackupState {
private:
    std::mutex mutex_;
    std::string phase_ = "DISCONNECTED";
    std::string status_ = "Ready to connect";
    int progress_ = 0;
    bool connected_ = false;
    std::string client_id_ = "";
    std::string server_address_ = "127.0.0.1:1256";
    std::string username_ = "";
    std::map<std::string, std::string> stats_;
    std::vector<std::string> logs_;

public:
    // Thread-safe getters
    std::string getPhase() {
        std::lock_guard<std::mutex> lock(mutex_);
        return phase_;
    }

    std::string getStatus() {
        std::lock_guard<std::mutex> lock(mutex_);
        return status_;
    }

    int getProgress() {
        std::lock_guard<std::mutex> lock(mutex_);
        return progress_;
    }

    bool isConnected() {
        std::lock_guard<std::mutex> lock(mutex_);
        return connected_;
    }

    std::string getClientId() {
        std::lock_guard<std::mutex> lock(mutex_);
        return client_id_;
    }

    // Thread-safe setters
    void setPhase(const std::string& phase) {
        std::lock_guard<std::mutex> lock(mutex_);
        phase_ = phase;
    }

    void setStatus(const std::string& status) {
        std::lock_guard<std::mutex> lock(mutex_);
        status_ = status;
    }

    void setProgress(int progress) {
        std::lock_guard<std::mutex> lock(mutex_);
        progress_ = progress;
    }

    void setConnected(bool connected) {
        std::lock_guard<std::mutex> lock(mutex_);
        connected_ = connected;
    }

    void setClientId(const std::string& id) {
        std::lock_guard<std::mutex> lock(mutex_);
        client_id_ = id;
    }

    void addLog(const std::string& message) {
        std::lock_guard<std::mutex> lock(mutex_);
        logs_.push_back(message);
        if (logs_.size() > 100) { // Keep only last 100 logs
            logs_.erase(logs_.begin());
        }
    }
      // Get current state as JSON
    JsonObject getStateJson() {
        std::lock_guard<std::mutex> lock(mutex_);
        JsonObject state;
        state.set("phase", phase_);
        state.set("status", status_);
        state.set("progress", progress_);
        state.set("connected", connected_);
        state.set("client_id", client_id_);
        state.set("server_address", server_address_);
        state.set("username", username_);
        return state;
    }
};

// Global application state
BackupState g_state;

// Static file cache for performance
class StaticFileCache {
private:
    std::mutex cache_mutex_;
    std::string cached_html_;
    bool html_loaded_;

public:
    StaticFileCache() : html_loaded_(false) {}

    std::string getHTML() {
        std::lock_guard<std::mutex> lock(cache_mutex_);

        if (!html_loaded_) {
            try {
                std::ifstream file("Client/Client-gui/NewGUIforClient.html");
                if (file.is_open()) {
                    cached_html_ = std::string((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
                    html_loaded_ = true;
                    std::cout << "Static file cache: HTML loaded (" << cached_html_.size() << " bytes)" << std::endl;
                } else {
                    return ""; // Return empty string if file can't be opened
                }
            } catch (const std::exception& e) {
                std::cerr << "Error loading HTML file: " << e.what() << std::endl;
                return "";
            }
        }

        return cached_html_;
    }

    void clearCache() {
        std::lock_guard<std::mutex> lock(cache_mutex_);
        cached_html_.clear();
        html_loaded_ = false;
        std::cout << "Static file cache: Cache cleared" << std::endl;
    }
};

// Global static file cache
StaticFileCache g_static_cache;

// CORS headers for web client
void add_cors_headers(http::response<http::string_body>& res) {
    res.set(http::field::access_control_allow_origin, "*");
    res.set(http::field::access_control_allow_methods, "GET, POST, PUT, DELETE, OPTIONS");
    res.set(http::field::access_control_allow_headers, "Content-Type, Authorization");
}

// Determine content type based on file extension
std::string get_content_type(const std::string& path) {
    // Use C++17 compatible string operations instead of ends_with
    if (path.length() >= 5 && path.substr(path.length() - 5) == ".html") return "text/html";
    if (path.length() >= 4 && path.substr(path.length() - 4) == ".css") return "text/css";
    if (path.length() >= 3 && path.substr(path.length() - 3) == ".js") return "application/javascript";
    if (path.length() >= 5 && path.substr(path.length() - 5) == ".json") return "application/json";
    if (path.length() >= 4 && path.substr(path.length() - 4) == ".png") return "image/png";
    if (path.length() >= 4 && path.substr(path.length() - 4) == ".jpg") return "image/jpeg";
    if (path.length() >= 5 && path.substr(path.length() - 5) == ".jpeg") return "image/jpeg";
    if (path.length() >= 4 && path.substr(path.length() - 4) == ".gif") return "image/gif";
    if (path.length() >= 4 && path.substr(path.length() - 4) == ".svg") return "image/svg+xml";
    if (path.length() >= 4 && path.substr(path.length() - 4) == ".ico") return "image/x-icon";
    if (path.length() >= 5 && path.substr(path.length() - 5) == ".woff") return "font/woff";
    if (path.length() >= 6 && path.substr(path.length() - 6) == ".woff2") return "font/woff2";
    if (path.length() >= 4 && path.substr(path.length() - 4) == ".ttf") return "font/ttf";
    if (path.length() >= 4 && path.substr(path.length() - 4) == ".eot") return "application/vnd.ms-fontobject";
    return "application/octet-stream"; // Default binary type
}

// Read a file and return its contents as a string
std::string read_file(const std::string& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file.is_open()) {
        return ""; // Return empty string if file can't be opened
    }
    return std::string((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
}

// Serve a static file
http::response<http::string_body> serve_file(const std::string& path) {
    http::response<http::string_body> res;
    res.version(11); // HTTP/1.1
    res.set(http::field::server, "CyberBackup-WebAPI/1.0");
    res.set(http::field::content_type, get_content_type(path).c_str());

    try {
        std::ifstream file(path, std::ios::binary);
        if (file.is_open()) {
            // Read file content
            std::string content((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
            file.close();

            res.result(http::status::ok);
            res.body() = content;
        } else {
            // File not found
            res.result(http::status::not_found);
            res.body() = "File not found: " + path;
        }
    } catch (const std::exception& e) {
        // Error reading file
        res.result(http::status::internal_server_error);
        res.body() = "Error reading file: " + path + " - " + e.what();
    }

    res.prepare_payload();
    return res;
}

// Handle HTTP requests
template<class Body, class Allocator>
http::response<http::string_body>
handle_request(http::request<Body, http::basic_fields<Allocator>>&& req) {
    // Create response
    http::response<http::string_body> res;
    res.version(req.version());
    res.set(http::field::server, "CyberBackup-WebAPI/1.0");
    add_cors_headers(res);

    // Handle CORS preflight
    if (req.method() == http::verb::options) {
        res.result(http::status::ok);
        res.body() = "";
        res.prepare_payload();
        return res;
    }

    auto const target = req.target();

    // Handle static file requests
    if (req.method() == http::verb::get) {
        std::string file_path;

        // Determine the file path based on the request target
        std::string target_str(target);
        if (target_str == "/" || target_str == "/index.html" || target_str == "/NewGUIforClient.html") {
            // Serve the main HTML file
            std::string html_content = g_static_cache.getHTML();
            if (!html_content.empty()) {
                res.result(http::status::ok);
                res.set(http::field::content_type, "text/html");
                res.body() = html_content;
                res.prepare_payload();
                return res;
            } else {
                // If we can't load the HTML file, return a 404
                res.result(http::status::not_found);
                res.set(http::field::content_type, "text/plain");
                res.body() = "File not found";
                res.prepare_payload();
                return res;
            }
        } else if (target_str.length() >= 8 && target_str.substr(0, 8) == "/styles/" ||
                   target_str.length() >= 9 && target_str.substr(0, 9) == "/scripts/") {
            // Serve CSS and JS files
            file_path = "Client/Client-gui" + std::string(target);
            std::string file_content = read_file(file_path);
            if (!file_content.empty()) {
                res.result(http::status::ok);
                res.set(http::field::content_type, get_content_type(file_path).c_str());
                res.body() = file_content;
                res.prepare_payload();
                return res;
            } else {
                // If we can't load the file, return a 404
                res.result(http::status::not_found);
                res.set(http::field::content_type, "text/plain");
                res.body() = "File not found";
                res.prepare_payload();
                return res;
            }
        }
        // For other static files in the root directory
        else if (target_str.length() >= 1 && target_str[0] == '/') {
            file_path = "Client/Client-gui" + std::string(target);
            std::string file_content = read_file(file_path);
            if (!file_content.empty()) {
                res.result(http::status::ok);
                res.set(http::field::content_type, get_content_type(file_path).c_str());
                res.body() = file_content;
                res.prepare_payload();
                return res;
            }
        }
    }

    try {        // GET /api/status - Get current application state
        if (req.method() == http::verb::get && target == "/api/status") {
            auto state = g_state.getStateJson();
            res.result(http::status::ok);
            res.body() = state.serialize();
        }

        // POST /api/connect - Connect to backup server
        else if (req.method() == http::verb::post && target == "/api/connect") {
            try {
                // Parse JSON request body to get server config
                std::string body = req.body();
                std::string server = "127.0.0.1:1256"; // default
                std::string username = "user"; // default
                std::string filepath = ""; // No default file - will be set during backup

                // Simple JSON parsing - look for server, port, username, filepath
                size_t server_pos = body.find("\"server\":\"");
                if (server_pos != std::string::npos) {
                    server_pos += 10; // Skip "server":"
                    size_t end_pos = body.find("\"", server_pos);
                    if (end_pos != std::string::npos) {
                        server = body.substr(server_pos, end_pos - server_pos);
                    }
                }

                size_t port_pos = body.find("\"port\":");
                if (port_pos != std::string::npos) {
                    port_pos += 7; // Skip "port":
                    size_t end_pos = body.find_first_of(",}", port_pos);
                    if (end_pos != std::string::npos) {
                        std::string port_str = body.substr(port_pos, end_pos - port_pos);
                        server += ":" + port_str;
                    }
                }

                size_t username_pos = body.find("\"username\":\"");
                if (username_pos != std::string::npos) {
                    username_pos += 12; // Skip "username":"
                    size_t end_pos = body.find("\"", username_pos);
                    if (end_pos != std::string::npos) {
                        username = body.substr(username_pos, end_pos - username_pos);
                    }
                }

                size_t filepath_pos = body.find("\"filepath\":\"");
                if (filepath_pos != std::string::npos) {
                    filepath_pos += 12; // Skip "filepath":"
                    size_t end_pos = body.find("\"", filepath_pos);
                    if (end_pos != std::string::npos) {
                        filepath = body.substr(filepath_pos, end_pos - filepath_pos);
                    }
                }

                // Parse the request body to get server config
                // For now, we'll update the transfer.info file with the new config
                // and let the backup operation handle the actual connection

                g_state.setPhase("CONNECTING");
                g_state.setStatus("Updating configuration...");
                g_state.addLog("Connection request received for " + server);

                // Update transfer.info with the new configuration
                try {
                    std::ofstream file("transfer.info");
                    if (file.is_open()) {
                        file << server << std::endl;
                        file << username << std::endl;
                        // Only write filepath if one was provided, otherwise leave empty for later
                        if (!filepath.empty()) {
                            file << filepath << std::endl;
                        } else {
                            file << "PLACEHOLDER_FOR_UPLOADED_FILE" << std::endl;
                        }
                        file.close();

                        g_state.setConnected(true);
                        g_state.setClientId("CLIENT_" + std::to_string(time(nullptr)));
                        g_state.setPhase("CONNECTED");
                        g_state.setStatus("Configuration updated - ready for backup");
                        g_state.addLog("Configuration updated for " + server + " as " + username);
                    } else {
                        throw std::runtime_error("Failed to update transfer.info");
                    }
                } catch (const std::exception& e) {
                    g_state.setPhase("FAILED");
                    g_state.setStatus("Configuration update failed");
                    g_state.addLog("Failed to update configuration: " + std::string(e.what()));
                    throw;
                }

                JsonObject response;
                response.set("success", true);
                response.set("message", "Connected successfully");
                response.set("client_id", g_state.getClientId());

                res.result(http::status::ok);
                res.body() = response.serialize();
            } catch (const std::exception& e) {
                JsonObject response;
                response.set("success", false);
                response.set("error", e.what());
                res.result(http::status::bad_request);
                res.body() = response.serialize();
            }
        }

        // POST /api/start_backup - Start backup operation (GUI endpoint)
        else if (req.method() == http::verb::post && target == "/api/start_backup") {
            try {
                // Check if we have the new config-based callback, prefer it over legacy
                if (g_backup_callback_with_config == nullptr && g_backup_callback == nullptr) {
                    JsonObject response;
                    response.set("success", false);
                    response.set("error", "Backup service not available");
                    res.result(http::status::service_unavailable);
                    res.body() = response.serialize();
                } else {
                    // Parse multipart/form-data to extract both file and configuration
                    std::string body = req.body();
                    std::string content_type = std::string(req[http::field::content_type]);

                    // Initialize configuration with defaults that can be overridden
                    WebServerBackend::BackupConfig config;
                    config.serverIP = "127.0.0.1";
                    config.serverPort = 1256;
                    config.username = "testuser";

                    std::string filename = "uploaded_file.txt";
                    std::string file_data;

                    // Parse multipart form data to extract both config and file
                    // This simple parser looks for form fields and file data
                    size_t pos = 0;
                    while (pos < body.size()) {
                        // Find next boundary
                        size_t boundary_start = body.find("Content-Disposition:", pos);
                        if (boundary_start == std::string::npos) break;

                        size_t name_start = body.find("name=\"", boundary_start);
                        if (name_start != std::string::npos) {
                            name_start += 6; // Skip 'name="'
                            size_t name_end = body.find("\"", name_start);
                            if (name_end != std::string::npos) {
                                std::string field_name = body.substr(name_start, name_end - name_start);

                                // Find data start (after double CRLF)
                                size_t data_start = body.find("\r\n\r\n", boundary_start);
                                if (data_start != std::string::npos) {
                                    data_start += 4;
                                    size_t data_end = body.find("\r\n--", data_start);
                                    if (data_end == std::string::npos) {
                                        data_end = body.size();
                                    }

                                    std::string field_value = body.substr(data_start, data_end - data_start);

                                    // Parse configuration fields
                                    if (field_name == "server" && !field_value.empty()) {
                                        config.serverIP = field_value;
                                    } else if (field_name == "port" && !field_value.empty()) {
                                        try {
                                            config.serverPort = static_cast<uint16_t>(std::stoi(field_value));
                                        } catch (...) {
                                            // Keep default port on parse error
                                        }
                                    } else if (field_name == "username" && !field_value.empty()) {
                                        config.username = field_value;
                                    } else if (field_name == "file") {
                                        // This is the file data
                                        size_t filename_pos = body.find("filename=\"", boundary_start);
                                        if (filename_pos != std::string::npos) {
                                            filename_pos += 10;
                                            size_t filename_end = body.find("\"", filename_pos);
                                            if (filename_end != std::string::npos) {
                                                filename = body.substr(filename_pos, filename_end - filename_pos);
                                            }
                                        }
                                        file_data = field_value;
                                    }
                                }
                            }
                        }
                        pos = boundary_start + 1;
                    }

                    if (!file_data.empty()) {
                        // Save the uploaded file temporarily
                        std::ofstream outfile(filename, std::ios::binary);
                        if (outfile.is_open()) {
                            outfile.write(file_data.c_str(), file_data.size());
                            outfile.close();

                            // Set the filepath in configuration
                            config.filepath = filename;

                            // Update transfer.info with the uploaded file path
                            try {
                                std::ofstream transfer_file("transfer.info");
                                if (transfer_file.is_open()) {
                                    transfer_file << config.serverIP << ":" << config.serverPort << std::endl;
                                    transfer_file << config.username << std::endl;
                                    transfer_file << filename << std::endl;
                                    transfer_file.close();
                                }
                            } catch (const std::exception& e) {
                                std::cerr << "Warning: Failed to update transfer.info: " << e.what() << std::endl;
                            }

                            g_state.setPhase("BACKUP_IN_PROGRESS");
                            g_state.setStatus("Starting backup...");
                            g_state.setProgress(0);
                            g_state.addLog("Backup operation started for " + filename);

                            // REMOVED: Progress simulation - using real progress only

                            // Start backup in a separate thread with configuration
                            std::thread backup_thread([config]() {
                                bool success = false;

                                // Prefer new config-based callback if available
                                if (g_backup_callback_with_config != nullptr) {
                                    success = g_backup_callback_with_config(config);
                                } else if (g_backup_callback != nullptr) {
                                    // Fall back to legacy callback (still needs transfer.info)
                                    // Create temporary transfer.info for backward compatibility
                                    std::ofstream temp_config("transfer.info");
                                    if (temp_config.is_open()) {
                                        temp_config << config.serverIP << ":" << config.serverPort << std::endl;
                                        temp_config << config.username << std::endl;
                                        temp_config << config.filepath << std::endl;
                                        temp_config.close();
                                    }
                                    success = g_backup_callback();
                                }

                                 if (success) {
                                    g_state.setPhase("COMPLETED");
                                    g_state.setStatus("Backup completed successfully");
                                    g_state.addLog("Backup completed for " + config.filepath);
                                } else {
                                    g_state.setPhase("FAILED");
                                    g_state.setStatus("Backup failed");
                                    g_state.addLog("Backup failed for " + config.filepath);
                                }
                            });
                            backup_thread.detach();

                            JsonObject response;
                            response.set("success", true);
                            response.set("message", "File uploaded and backup started");
                            response.set("filename", filename);
                            response.set("server", config.serverIP + ":" + std::to_string(config.serverPort));
                            response.set("username", config.username);
                            response.set("task_id", "BACKUP_" + std::to_string(time(nullptr)));

                            res.result(http::status::ok);
                            res.set(http::field::content_type, "application/json");
                            res.body() = response.serialize();
                        } else {
                            JsonObject response;
                            response.set("success", false);
                            response.set("error", "Failed to save uploaded file");
                            res.result(http::status::internal_server_error);
                            res.body() = response.serialize();
                        }
                    } else {
                        JsonObject response;
                        response.set("success", false);
                        response.set("error", "No file data received");
                        res.result(http::status::bad_request);
                        res.body() = response.serialize();
                    }
                }
            } catch (const std::exception& e) {
                std::cerr << "Error in /api/start_backup: " << e.what() << std::endl;
                JsonObject response;
                response.set("success", false);
                response.set("error", "Server error: " + std::string(e.what()));
                res.result(http::status::internal_server_error);
                res.set(http::field::content_type, "application/json");
                res.body() = response.serialize();
            }
        }
          // POST /api/backup - Start backup operation
        else if (req.method() == http::verb::post && target == "/api/backup") {
            try {
                if (g_backup_callback == nullptr) {
                    JsonObject response;
                    response.set("success", false);
                    response.set("error", "Backup service not available");
                    res.result(http::status::service_unavailable);
                    res.body() = response.serialize();
                } else {
                    g_state.setPhase("BACKUP_IN_PROGRESS");
                    g_state.setStatus("Starting backup...");
                    g_state.setProgress(0);
                    g_state.addLog("Backup operation started");

                    // REMOVED: Progress simulation - using real progress only

                    // Start backup in a separate thread to avoid blocking the HTTP response
                    std::thread backup_thread([&]() {
                        bool success = g_backup_callback();
                        if (success) {
                            g_state.setPhase("COMPLETED");
                            g_state.setStatus("Backup completed successfully");
                            g_state.setProgress(100);
                            g_state.addLog("Backup completed successfully");
                        } else {
                            g_state.setPhase("FAILED");
                            g_state.setStatus("Backup failed");
                            g_state.setProgress(0);
                            g_state.addLog("Backup operation failed");
                        }
                    });
                    backup_thread.detach(); // Let it run independently

                    JsonObject response;
                    response.set("success", true);
                    response.set("message", "Backup started");
                    response.set("task_id", "BACKUP_" + std::to_string(time(nullptr)));

                    res.result(http::status::ok);
                    res.body() = response.serialize();
                }
            } catch (const std::exception& e) {
                JsonObject response;
                response.set("success", false);
                response.set("error", e.what());
                res.result(http::status::bad_request);
                res.body() = response.serialize();
            }
        }

        // POST /api/stop - Stop current operation
        else if (req.method() == http::verb::post && target == "/api/stop") {
            g_state.setPhase("STOPPED");
            g_state.setStatus("Operation stopped");
            g_state.setProgress(0);
            g_state.addLog("Operation stopped by user");

            JsonObject response;
            response.set("success", true);
            response.set("message", "Operation stopped");

            res.result(http::status::ok);
            res.body() = response.serialize();
        }

        // POST /api/pause - Pause current operation
        else if (req.method() == http::verb::post && target == "/api/pause") {
            g_state.setPhase("PAUSED");
            g_state.setStatus("Operation paused");
            g_state.addLog("Operation paused by user");

            JsonObject response;
            response.set("success", true);
            response.set("message", "Operation paused");

            res.result(http::status::ok);
            res.body() = response.serialize();
        }

        // POST /api/resume - Resume paused operation
        else if (req.method() == http::verb::post && target == "/api/resume") {
            g_state.setPhase("BACKUP_IN_PROGRESS");
            g_state.setStatus("Operation resumed");
            g_state.addLog("Operation resumed by user");

            JsonObject response;
            response.set("success", true);
            response.set("message", "Operation resumed");

            res.result(http::status::ok);
            res.body() = response.serialize();
        }

        // Unknown endpoint
        else {
            JsonObject response;
            response.set("error", "Endpoint not found");
            res.result(http::status::not_found);
            res.body() = response.serialize();
        }
    } catch (const std::exception& e) {
        JsonObject response;
        response.set("error", std::string("Server error: ") + e.what());
        res.result(http::status::internal_server_error);
        res.body() = response.serialize();
    }

    res.prepare_payload();
    return res;
}

// HTTP session handler
class HttpSession : public std::enable_shared_from_this<HttpSession> {
private:
    tcp::socket socket_;
    beast::flat_buffer buffer_;
    http::request<http::string_body> req_;

public:
    explicit HttpSession(tcp::socket&& socket) : socket_(std::move(socket)) {}

    void run() {
        do_read();
    }

private:
    void do_read() {
        auto self = shared_from_this();
        http::async_read(socket_, buffer_, req_,
            [self](beast::error_code ec, std::size_t bytes_transferred) {
                boost::ignore_unused(bytes_transferred);
                if (!ec) {
                    self->handle_request();
                }
            });
    }

    void handle_request() {
        auto response = ::handle_request(std::move(req_));
        auto sp = std::make_shared<http::response<http::string_body>>(std::move(response));

        auto self = shared_from_this();
        http::async_write(socket_, *sp,
            [self, sp](beast::error_code ec, std::size_t bytes_transferred) {
                boost::ignore_unused(bytes_transferred);
                self->socket_.shutdown(tcp::socket::shutdown_send, ec);
            });
    }
};

// HTTP server listener
class HttpListener : public std::enable_shared_from_this<HttpListener> {
private:
    net::io_context& ioc_;
    tcp::acceptor acceptor_;

public:
    HttpListener(net::io_context& ioc, tcp::endpoint endpoint)
        : ioc_(ioc), acceptor_(net::make_strand(ioc)) {
        beast::error_code ec;

        acceptor_.open(endpoint.protocol(), ec);
        if (ec) {
            std::cerr << "Failed to open acceptor: " << ec.message() << std::endl;
            return;
        }

        acceptor_.set_option(net::socket_base::reuse_address(true), ec);
        if (ec) {
            std::cerr << "Failed to set reuse_address: " << ec.message() << std::endl;
            return;
        }

        acceptor_.bind(endpoint, ec);
        if (ec) {
            std::cerr << "Failed to bind: " << ec.message() << std::endl;
            return;
        }

        acceptor_.listen(net::socket_base::max_listen_connections, ec);
        if (ec) {
            std::cerr << "Failed to listen: " << ec.message() << std::endl;
            return;
        }

        std::cout << "HTTP API Server listening on " << endpoint << std::endl;
    }

    void run() {
        do_accept();
    }

private:
    void do_accept() {
        auto self = shared_from_this();
        acceptor_.async_accept(net::make_strand(ioc_),
            [self](beast::error_code ec, tcp::socket socket) {
                if (!ec) {
                    std::make_shared<HttpSession>(std::move(socket))->run();
                }
                self->do_accept();
            });
    }
};

// REMOVED: Progress simulation functions - these created fake progress
// Real progress should come from actual backup operations, not simulation

// Function pointers moved to top of file

// Implementation class for PIMPL idiom
class WebServerBackend::Impl {
public:
    std::unique_ptr<net::io_context> ioc_;
    std::shared_ptr<HttpListener> listener_;
    std::thread server_thread_;
    std::atomic<bool> running_;

    Impl() : running_(false) {}

    ~Impl() {
        stop();
    }

    bool start(const std::string& address = "127.0.0.1", unsigned short port = 9090) {
        if (running_) {
            return false; // Already running
        }

        try {
            auto const addr = net::ip::make_address(address);
            ioc_ = std::make_unique<net::io_context>(1);

            // Initialize application state
            g_state.setPhase("READY");
            g_state.setStatus("Web API server ready");
            g_state.addLog("CyberBackup Web API Server started");

            // Create HTTP listener
            listener_ = std::make_shared<HttpListener>(*ioc_, tcp::endpoint{addr, port});
            listener_->run();

            // Progress simulation will be started on-demand when needed

            // Start server thread
            server_thread_ = std::thread([this]() {
                try {
                    ioc_->run();
                } catch (const std::exception& e) {
                    std::cerr << "WebServer error: " << e.what() << std::endl;
                }
            });

            running_ = true;
            std::cout << "CyberBackup Web API Server started on port " << port << std::endl;
            std::cout << "Ready to serve HTML client requests..." << std::endl;

            return true;

        } catch (const std::exception& e) {
            std::cerr << "Failed to start WebServer: " << e.what() << std::endl;
            return false;
        }
    }

    void stop() {
        if (!running_) {
            return;
        }

        running_ = false;

        if (ioc_) {
            ioc_->stop();
        }

        if (server_thread_.joinable()) {
            server_thread_.join();
        }

        // REMOVED: Progress simulation stop call

        std::cout << "WebServer stopped" << std::endl;
    }

    bool isRunning() const {
        return running_;
    }
};

// Public interface implementation
WebServerBackend::WebServerBackend() : pImpl_(std::make_unique<Impl>()) {}

WebServerBackend::~WebServerBackend() = default;

bool WebServerBackend::start(const std::string& address, unsigned short port) {
    return pImpl_->start(address, port);
}

void WebServerBackend::stop() {
    pImpl_->stop();
}

bool WebServerBackend::isRunning() const {
    return pImpl_->isRunning();
}

void WebServerBackend::setBackupCallback(std::function<bool()> callback) {
    g_backup_callback = callback;
}

void WebServerBackend::setBackupCallbackWithConfig(std::function<bool(const BackupConfig&)> callback) {
    g_backup_callback_with_config = callback;
}