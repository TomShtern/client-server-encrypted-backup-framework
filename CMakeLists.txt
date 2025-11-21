# ============================================================================
# VCPKG TOOLCHAIN AUTO-DETECTION (must be before project())
# ============================================================================
# This section automatically finds and configures the vcpkg toolchain if not
# explicitly provided via -DCMAKE_TOOLCHAIN_FILE=...
#
# Supports three independent build methods:
# 1. CMake Presets (recommended): cmake --preset default
# 2. Auto-detection: cmake -B build (finds vcpkg automatically)
# 3. Explicit: cmake -B build -DCMAKE_TOOLCHAIN_FILE=vcpkg/scripts/buildsystems/vcpkg.cmake

if(NOT DEFINED CMAKE_TOOLCHAIN_FILE)
    # Search for vcpkg toolchain in common locations
    set(VCPKG_TOOLCHAIN_CANDIDATES
        "${CMAKE_SOURCE_DIR}/vcpkg/scripts/buildsystems/vcpkg.cmake"
        "$ENV{VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake"
        "C:/vcpkg/scripts/buildsystems/vcpkg.cmake"
    )

    foreach(TOOLCHAIN_PATH ${VCPKG_TOOLCHAIN_CANDIDATES})
        if(EXISTS "${TOOLCHAIN_PATH}")
            set(CMAKE_TOOLCHAIN_FILE "${TOOLCHAIN_PATH}" CACHE FILEPATH "vcpkg toolchain file")
            message(STATUS "Auto-detected vcpkg toolchain: ${TOOLCHAIN_PATH}")
            break()
        endif()
    endforeach()

    if(NOT DEFINED CMAKE_TOOLCHAIN_FILE)
        message(WARNING
            "vcpkg toolchain not found. Dependencies may not be available.\n"
            "To fix this, use one of the following methods:\n"
            "  1. CMake Presets (recommended): cmake --preset default\n"
            "  2. Explicit toolchain: cmake -B build -DCMAKE_TOOLCHAIN_FILE=vcpkg/scripts/buildsystems/vcpkg.cmake\n"
            "  3. Environment variable: set VCPKG_ROOT=path/to/vcpkg"
        )
    endif()
else()
    message(STATUS "Using vcpkg toolchain: ${CMAKE_TOOLCHAIN_FILE}")
endif()

# ============================================================================
# PROJECT CONFIGURATION
# ============================================================================

cmake_minimum_required(VERSION 3.15)
cmake_policy(SET CMP0167 NEW)
project(EncryptedBackupClient VERSION 1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(WIN32)
    add_compile_definitions(
        WIN32_LEAN_AND_MEAN
        NOMINMAX
        _WIN32_WINNT=0x0601
    )
endif()

# ============================================================================
# BUILD CONFIGURATION
# ============================================================================

add_executable(EncryptedBackupClient
    Client/cpp/main.cpp
    Client/cpp/client.cpp
    Client/cpp/WebServerBackend.cpp
    Client/deps/CompressionWrapper.cpp
    Client/deps/RSAWrapper.cpp
    Client/deps/AESWrapper.cpp
    Client/deps/Base64Wrapper.cpp
    Client/deps/crc.cpp
)

target_include_directories(EncryptedBackupClient PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/Client/cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/Client/deps
    ${CMAKE_CURRENT_SOURCE_DIR}/Client/deps/shared
)

# ============================================================================
# DEPENDENCY MANAGEMENT
# ============================================================================

find_package(Boost CONFIG QUIET COMPONENTS asio beast iostreams)

if(NOT Boost_FOUND)
    message(STATUS "Config-based Boost discovery failed, trying traditional FindBoost...")
    find_package(Boost REQUIRED COMPONENTS system thread)

    if(NOT Boost_FOUND)
        message(FATAL_ERROR
            "Boost not found! Please install Boost using vcpkg:\n"
            "  vcpkg/vcpkg.exe install boost-asio boost-beast boost-iostreams --triplet x64-windows\n"
            "Or ensure vcpkg toolchain is properly configured."
        )
    endif()
endif()

find_package(cryptopp CONFIG REQUIRED)
find_package(ZLIB REQUIRED)
find_package(sentry CONFIG REQUIRED)

target_link_libraries(EncryptedBackupClient PRIVATE
    Boost::asio
    Boost::beast
    Boost::iostreams
    cryptopp::cryptopp
    ZLIB::ZLIB
    sentry::sentry
)

if(WIN32)
    target_link_libraries(EncryptedBackupClient PRIVATE
        ws2_32
    )
endif()

# ============================================================================
# COMPILER CONFIGURATION
# ============================================================================

if(MSVC)
    target_compile_options(EncryptedBackupClient PRIVATE
        /W4
        /permissive-
    )
    set_property(TARGET EncryptedBackupClient PROPERTY
        MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL"
    )
else()
    target_compile_options(EncryptedBackupClient PRIVATE
        -Wall -Wextra -pedantic
    )
endif()

# ============================================================================
# BUILD OUTPUT
# ============================================================================

set_target_properties(EncryptedBackupClient PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY_DEBUG "${CMAKE_BINARY_DIR}/Debug"
    RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_BINARY_DIR}/Release"
)

message(STATUS "")
message(STATUS "========================================")
message(STATUS "CyberBackup 3.0 - C++ Client Build")
message(STATUS "========================================")
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "Generator: ${CMAKE_GENERATOR}")
message(STATUS "Toolchain: ${CMAKE_TOOLCHAIN_FILE}")
message(STATUS "========================================")
message(STATUS "")
