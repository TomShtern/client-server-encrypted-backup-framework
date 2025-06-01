cmake_minimum_required(VERSION 3.15)

# Force MSVC compiler on Windows (only for Visual Studio generators)
if(WIN32 AND CMAKE_GENERATOR MATCHES "Visual Studio")
    set(CMAKE_GENERATOR_TOOLSET "v143" CACHE STRING "Platform Toolset" FORCE)
    set(CMAKE_VS_PLATFORM_TOOLSET "v143" CACHE STRING "Platform Toolset" FORCE)
endif()

project(EncryptedBackupClient LANGUAGES CXX)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Generate compile_commands.json for clang-tidy/clangd
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Output directories
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)

# Find required packages using vcpkg toolchain
set(CMAKE_TOOLCHAIN_FILE "$ENV{USERPROFILE}/vcpkg/scripts/buildsystems/vcpkg.cmake" CACHE STRING "Vcpkg toolchain file")

# Find Boost using CONFIG mode (vcpkg style)
find_package(Boost CONFIG REQUIRED COMPONENTS system)

# Find Crypto++
find_package(cryptopp CONFIG REQUIRED)

message(STATUS "Found Boost: ${Boost_VERSION}")
message(STATUS "Found Crypto++: ${cryptopp_VERSION}")

# Source files
file(GLOB CLIENT_SOURCES
    "client/src/*.cpp"
)

# Add executable
add_executable(client ${CLIENT_SOURCES})

# Include directories
target_include_directories(client PRIVATE
    ${CMAKE_SOURCE_DIR}/client/include
    ${CMAKE_SOURCE_DIR}/client/src
)

# Link libraries
target_link_libraries(client PRIVATE
    Boost::system
    cryptopp::cryptopp
)

# Windows-specific linking
if(WIN32)
    target_link_libraries(client PRIVATE
        ws2_32
        wsock32
        mswsock
    )
endif()

# Compiler-specific settings
if (MSVC)
    # MSVC specific options
    target_compile_options(client PRIVATE
        /W4                 # Warning level 4
        /permissive-        # Disable non-conforming code
        /Zc:__cplusplus     # Enable correct __cplusplus macro
        /Zc:preprocessor    # Enable conforming preprocessor
        /utf-8              # Set source and execution character sets to UTF-8
        /MP                 # Enable multi-processor compilation
    )    # Define macros
    target_compile_definitions(client PRIVATE
        _CRT_SECURE_NO_WARNINGS
        WIN32_LEAN_AND_MEAN
        NOMINMAX
        BOOST_ASIO_NO_WIN32_LEAN_AND_MEAN
        _WIN32_WINNT=0x0601  # Windows 7 or later for Boost.Asio
    )

    # Debug configuration
    target_compile_options(client PRIVATE
        $<$<CONFIG:Debug>:/Od /Zi /RTC1>
    )

    # Release configuration
    target_compile_options(client PRIVATE
        $<$<CONFIG:Release>:/O2 /DNDEBUG>
    )

elseif(CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
    # Clang specific options
    target_compile_options(client PRIVATE
        -Wall -Wextra -Wpedantic
        -Wno-unused-parameter
    )
elseif(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    # GCC specific options
    target_compile_options(client PRIVATE
        -Wall -Wextra -Wpedantic
        -Wno-unused-parameter
    )
endif()

# Find clang-tidy if available
find_program(CLANG_TIDY_EXE NAMES "clang-tidy")
if(CLANG_TIDY_EXE)
    message(STATUS "Found clang-tidy: ${CLANG_TIDY_EXE}")
    set_target_properties(client PROPERTIES
        CXX_CLANG_TIDY "${CLANG_TIDY_EXE};--config-file=${CMAKE_SOURCE_DIR}/.clang-tidy"
    )
else()
    message(STATUS "clang-tidy not found")
endif()

# Custom target for running clang-tidy manually
if(CLANG_TIDY_EXE)
    add_custom_target(clang-tidy
        COMMAND ${CLANG_TIDY_EXE}
        -p ${CMAKE_BINARY_DIR}
        --config-file=${CMAKE_SOURCE_DIR}/.clang-tidy
        ${CLIENT_SOURCES}
        WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
        COMMENT "Running clang-tidy"
    )
endif()

# Find clang-format if available
find_program(CLANG_FORMAT_EXE NAMES "clang-format")
if(CLANG_FORMAT_EXE)
    message(STATUS "Found clang-format: ${CLANG_FORMAT_EXE}")
    add_custom_target(clang-format
        COMMAND ${CLANG_FORMAT_EXE}
        -i
        -style=file
        ${CLIENT_SOURCES}
        WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
        COMMENT "Running clang-format"
    )
endif()
