cmake_minimum_required(VERSION 3.10)
project(EncryptedBackupClient LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)

# --- Disable Crypto++ assembly optimizations for portable build ---
add_definitions(-DCRYPTOPP_DISABLE_ASM)
add_definitions(-DCRYPTOPP_DISABLE_SSE2)
add_definitions(-DCRYPTOPP_DISABLE_SSSE3)
add_definitions(-DCRYPTOPP_DISABLE_SSE4)
add_definitions(-DCRYPTOPP_DISABLE_AVX)
add_definitions(-DCRYPTOPP_DISABLE_AVX2)
# Use portable C++ implementations to avoid assembly dependencies
add_definitions(-DCRYPTOPP_NO_CPU_FEATURE_PROBES=1)
add_definitions(-DCRYPTOPP_DISABLE_ASM=1)
# Force disable Microsoft-style inline assembly and enable GNU-style inline assembly
add_definitions(-DCRYPTOPP_MS_STYLE_INLINE_ASSEMBLY=0)
add_definitions(-DCRYPTOPP_GNU_STYLE_INLINE_ASSEMBLY=1)
# Disable the external assembly function dependency
add_definitions(-DCRYPTOPP_DISABLE_X86ASM)
add_definitions(-DCRYPTOPP_DISABLE_X64ASM)

# --- Windows-specific definitions ---
add_definitions(-D_WIN32_WINNT=0x0601)  # Windows 7 or later

# --- User-supplied library paths ---
set(BOOST_ROOT "C:/Users/tom7s/Downloads/boost_1_88_0/boost_1_88_0")

# --- Include directories ---
include_directories(include)
include_directories(${BOOST_ROOT})
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/../third_party)  # For #include <cryptopp/xxx.h>

# --- Collect source files ---
file(GLOB SOURCES "src/*.cpp")
file(GLOB CRYPTOPP_SOURCES "../third_party/cryptopp/*.cpp")

add_executable(client ${SOURCES} ${CRYPTOPP_SOURCES})

target_include_directories(client PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include 
    ${BOOST_ROOT}
    ${CMAKE_CURRENT_SOURCE_DIR}/../third_party
)

# If you need to link with Boost libraries (e.g., for Boost.Asio with separate .lib), add them here
# find_package(Boost REQUIRED)
# target_link_libraries(client Boost::boost)
