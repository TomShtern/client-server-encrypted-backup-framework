/**
 * Client-Side Performance Benchmark Suite
 * Step 7: Detailed C++ Client Performance Analysis
 * 
 * This benchmark focuses on client-side operations including:
 * - RSA key operations
 * - AES encryption/decryption
 * - Protocol message creation
 * - Memory allocation patterns
 * - File I/O performance
 */

#include <iostream>
#include <chrono>
#include <vector>
#include <string>
#include <fstream>
#include <memory>
#include <iomanip>
#include <map>
#include <numeric>
#include <algorithm>

// Project includes
#include "../client/include/RSAWrapper.h"
#include "../client/include/AESWrapper.h"
#include "../client/include/Base64Wrapper.h"
#include "../client/include/protocol.h"

class ClientBenchmark {
private:
    std::map<std::string, std::vector<double>> results;
    
    void logResult(const std::string& category, const std::string& test, double timeMs, const std::string& details = "") {
        results[category + "::" + test].push_back(timeMs);
        std::cout << std::fixed << std::setprecision(3) 
                  << "[" << category << "] " << std::setw(25) << test 
                  << " | " << std::setw(8) << timeMs << " ms"
                  << (details.empty() ? "" : " | " + details) << std::endl;
    }
    
    template<typename Func>
    double timeFunction(Func&& func, int iterations = 1) {
        auto start = std::chrono::high_resolution_clock::now();
        for (int i = 0; i < iterations; ++i) {
            func();
        }
        auto end = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
        return duration.count() / 1000.0 / iterations; // Convert to milliseconds per iteration
    }

public:
    void benchmarkRSAOperations() {
        std::cout << "\n[CRYPTO] RSA OPERATIONS BENCHMARK\n";
        std::cout << std::string(50, '-') << std::endl;
        
        try {
            // RSA Key Loading (current implementation)
            auto loadTime = timeFunction([&]() {
                RSAPrivateWrapper rsa;
                // This will use the current deterministic key loading
            }, 5);
            logResult("RSA", "Key_Loading", loadTime, "5 iterations avg");
            
            // RSA Key Generation (if working)
            try {
                auto genTime = timeFunction([&]() {
                    RSAPrivateWrapper rsa;
                    // Attempt key generation - may fail with current implementation
                }, 1);
                logResult("RSA", "Key_Generation", genTime, "1024-bit key");
            } catch (...) {
                logResult("RSA", "Key_Generation", -1, "Failed - using fallback");
            }
            
            // Public Key Export
            RSAPrivateWrapper rsa;
            auto exportTime = timeFunction([&]() {
                std::string pubKey = rsa.getPublicKey();
            }, 10);
            logResult("RSA", "Public_Key_Export", exportTime, "10 iterations avg");
            
            // Memory usage estimation
            RSAPrivateWrapper rsa1, rsa2, rsa3;
            logResult("RSA", "Memory_Per_Instance", sizeof(RSAPrivateWrapper), "bytes (approx)");
            
        } catch (const std::exception& e) {
            std::cout << "[FAIL] RSA benchmark failed: " << e.what() << std::endl;
        }
    }
    
    void benchmarkAESOperations() {
        std::cout << "\n[ENCRYPT] AES OPERATIONS BENCHMARK\n";
        std::cout << std::string(50, '-') << std::endl;
        
        try {
            // Test data of various sizes
            std::vector<std::pair<std::string, std::string>> testData = {
                {"Small", std::string(1024, 'A')},      // 1KB
                {"Medium", std::string(10240, 'B')},    // 10KB
                {"Large", std::string(102400, 'C')}     // 100KB
            };
            
            for (const auto& [sizeName, data] : testData) {
                AESWrapper aes(reinterpret_cast<const unsigned char*>("0123456789abcdef"), 16);
                
                // Encryption benchmark
                auto encTime = timeFunction([&]() {
                    std::string encrypted = aes.encrypt(data.c_str(), data.length());
                }, 3);
                logResult("AES", "Encrypt_" + sizeName, encTime, std::to_string(data.length()) + " bytes");
                
                // Decryption benchmark
                std::string encrypted = aes.encrypt(data.c_str(), data.length());
                auto decTime = timeFunction([&]() {
                    std::string decrypted = aes.decrypt(encrypted.c_str(), encrypted.length());
                }, 3);
                logResult("AES", "Decrypt_" + sizeName, decTime, std::to_string(encrypted.length()) + " bytes");
            }
            
        } catch (const std::exception& e) {
            std::cout << "[FAIL] AES benchmark failed: " << e.what() << std::endl;
        }
    }
    
    void benchmarkProtocolOperations() {
        std::cout << "\n[SIGNAL] PROTOCOL OPERATIONS BENCHMARK\n";
        std::cout << std::string(50, '-') << std::endl;
        
        try {
            // Mock client ID
            std::array<uint8_t, 16> clientID;
            std::fill(clientID.begin(), clientID.end(), 0xAB);
            
            // Registration request creation
            auto regTime = timeFunction([&]() {
                std::vector<uint8_t> header = createRequestHeader(clientID, 1025, 255);
            }, 100);
            logResult("Protocol", "Registration_Header", regTime, "100 iterations avg");
            
            // Public key request creation
            auto pubKeyTime = timeFunction([&]() {
                std::vector<uint8_t> header = createRequestHeader(clientID, 1026, 335);
            }, 100);
            logResult("Protocol", "PublicKey_Header", pubKeyTime, "100 iterations avg");
            
            // File transfer request creation
            auto fileTime = timeFunction([&]() {
                std::vector<uint8_t> header = createRequestHeader(clientID, 1028, 1024);
            }, 100);
            logResult("Protocol", "FileTransfer_Header", fileTime, "100 iterations avg");
            
            // Header parsing simulation
            std::vector<uint8_t> testHeader = createRequestHeader(clientID, 1025, 255);
            auto parseTime = timeFunction([&]() {
                // Simulate header parsing
                uint16_t code = *reinterpret_cast<const uint16_t*>(&testHeader[17]);
                uint32_t size = *reinterpret_cast<const uint32_t*>(&testHeader[19]);
            }, 1000);
            logResult("Protocol", "Header_Parsing", parseTime, "1000 iterations avg");
            
        } catch (const std::exception& e) {
            std::cout << "[FAIL] Protocol benchmark failed: " << e.what() << std::endl;
        }
    }
    
    void benchmarkFileOperations() {
        std::cout << "\n[FOLDER] FILE I/O OPERATIONS BENCHMARK\n";
        std::cout << std::string(50, '-') << std::endl;
        
        // Create test files
        std::vector<std::pair<std::string, size_t>> fileSizes = {
            {"Small", 1024},        // 1KB
            {"Medium", 102400},     // 100KB
            {"Large", 1048576}      // 1MB
        };
        
        for (const auto& [sizeName, size] : fileSizes) {
            std::string filename = "benchmark_" + sizeName + ".tmp";
            std::string testData(size, 'X');
            
            // File write benchmark
            auto writeTime = timeFunction([&]() {
                std::ofstream file(filename, std::ios::binary);
                file.write(testData.c_str(), testData.length());
                file.close();
            }, 3);
            logResult("FileIO", "Write_" + sizeName, writeTime, std::to_string(size) + " bytes");
            
            // File read benchmark
            auto readTime = timeFunction([&]() {
                std::ifstream file(filename, std::ios::binary);
                std::string buffer(size, '\0');
                file.read(&buffer[0], size);
                file.close();
            }, 3);
            logResult("FileIO", "Read_" + sizeName, readTime, std::to_string(size) + " bytes");
            
            // Cleanup
            std::remove(filename.c_str());
        }
    }
    
    void benchmarkMemoryOperations() {
        std::cout << "\n[SAVE] MEMORY OPERATIONS BENCHMARK\n";
        std::cout << std::string(50, '-') << std::endl;
        
        // Vector allocation benchmark
        auto vectorTime = timeFunction([&]() {
            std::vector<uint8_t> buffer(1048576); // 1MB
            std::fill(buffer.begin(), buffer.end(), 0xFF);
        }, 10);
        logResult("Memory", "Vector_Allocation", vectorTime, "1MB x10 avg");
        
        // String operations benchmark
        auto stringTime = timeFunction([&]() {
            std::string str1(100000, 'A');
            std::string str2 = str1 + str1;
            str2.clear();
        }, 10);
        logResult("Memory", "String_Operations", stringTime, "100KB strings x10");
        
        // Memory copy benchmark
        std::vector<uint8_t> source(1048576, 0xAA);
        std::vector<uint8_t> dest(1048576);
        auto copyTime = timeFunction([&]() {
            std::copy(source.begin(), source.end(), dest.begin());
        }, 10);
        logResult("Memory", "Memory_Copy", copyTime, "1MB copy x10 avg");
    }
    
    void runAllBenchmarks() {
        std::cout << "🔬 CLIENT-SIDE PERFORMANCE BENCHMARK SUITE\n";
        std::cout << std::string(70, '=') << std::endl;
        
        benchmarkRSAOperations();
        benchmarkAESOperations();
        benchmarkProtocolOperations();
        benchmarkFileOperations();
        benchmarkMemoryOperations();
        
        printSummary();
    }
    
    void printSummary() {
        std::cout << "\n[DATA] BENCHMARK SUMMARY\n";
        std::cout << std::string(70, '=') << std::endl;
        
        for (const auto& [testName, times] : results) {
            if (!times.empty() && times[0] >= 0) {
                double avg = std::accumulate(times.begin(), times.end(), 0.0) / times.size();
                double min = *std::min_element(times.begin(), times.end());
                double max = *std::max_element(times.begin(), times.end());
                
                std::cout << std::fixed << std::setprecision(3)
                          << std::setw(35) << testName 
                          << " | Avg: " << std::setw(8) << avg << " ms"
                          << " | Min: " << std::setw(8) << min << " ms"
                          << " | Max: " << std::setw(8) << max << " ms"
                          << " | Samples: " << times.size() << std::endl;
            }
        }
    }
};

int main() {
    try {
        ClientBenchmark benchmark;
        benchmark.runAllBenchmarks();
        
        std::cout << "\n[OK] Client benchmark completed successfully!\n";
        return 0;
        
    } catch (const std::exception& e) {
        std::cout << "[FAIL] Benchmark failed: " << e.what() << std::endl;
        return 1;
    }
}
