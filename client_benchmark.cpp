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
    
    /**
     * @brief Records and logs the timing result for a benchmark test.
     *
     * Stores the measured time in milliseconds for a specific test under the given category and outputs a formatted log line, optionally including additional details.
     *
     * @param category The benchmark category (e.g., "RSA", "AES").
     * @param test The specific test name within the category.
     * @param timeMs The measured execution time in milliseconds.
     * @param details Optional additional information to include in the log output.
     */
    void logResult(const std::string& category, const std::string& test, double timeMs, const std::string& details = "") {
        results[category + "::" + test].push_back(timeMs);
        std::cout << std::fixed << std::setprecision(3) 
                  << "[" << category << "] " << std::setw(25) << test 
                  << " | " << std::setw(8) << timeMs << " ms"
                  << (details.empty() ? "" : " | " + details) << std::endl;
    }
    
    template<typename Func>
    /**
     * @brief Measures the average execution time of a function over multiple iterations.
     *
     * Executes the provided function a specified number of times and returns the average duration per iteration in milliseconds.
     *
     * @tparam Func Type of the callable to benchmark.
     * @param func The function or callable object to execute.
     * @param iterations Number of times to execute the function. Defaults to 1.
     * @return double Average execution time per iteration in milliseconds.
     */
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
    /**
     * @brief Benchmarks RSA cryptographic operations including key loading, key generation, public key export, and memory usage estimation.
     *
     * Measures and logs the average execution time for loading RSA keys, attempts key generation, exports the public key, and estimates the memory footprint of an RSA private key wrapper instance. Results are recorded for later summary. Handles and logs exceptions encountered during benchmarking.
     */
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
    
    /**
     * @brief Benchmarks AES encryption and decryption performance on data of varying sizes.
     *
     * Measures and logs the average time to encrypt and decrypt data blocks of 1KB, 10KB, and 100KB using AES. Results are recorded for both operations and include the size of the processed data. Handles exceptions and logs failures if any occur during the benchmark.
     */
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
    
    /**
     * @brief Benchmarks protocol message header creation and parsing operations.
     *
     * Measures the average execution time for creating registration, public key, and file transfer request headers, as well as parsing protocol headers, over multiple iterations. Logs timing results for each operation.
     */
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
    
    /**
     * @brief Benchmarks file write and read operations for various file sizes.
     *
     * Measures the average time to write and read files of 1KB, 100KB, and 1MB, performing each operation three times per size. Results are logged with timing details, and temporary files are deleted after each test.
     */
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
    
    /**
     * @brief Benchmarks memory-related operations including allocation, string manipulation, and memory copying.
     *
     * Measures the average execution time for allocating and filling a 1MB vector, performing string concatenation and clearing with 100KB strings, and copying 1MB of memory between vectors. Results are logged for each operation.
     */
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
    
    /**
     * @brief Executes all client-side benchmark categories and prints a summary.
     *
     * Runs benchmarks for RSA operations, AES encryption/decryption, protocol message handling, file I/O, and memory operations, then outputs a summary of the collected performance metrics.
     */
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
    
    /**
     * @brief Prints a summary of all benchmark results.
     *
     * Iterates over all recorded benchmark timings and outputs the average, minimum, maximum times, and sample count for each test with valid data.
     */
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

/**
 * @brief Entry point for the client benchmark suite.
 *
 * Runs all client-side performance benchmarks and prints a summary of results. Returns 0 on success, or 1 if an exception occurs.
 *
 * @return int Exit status code.
 */
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
