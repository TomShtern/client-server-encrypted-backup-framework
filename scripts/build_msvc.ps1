# PowerShell script to build the project with MSVC
param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("Debug", "Release")]
    [string]$Configuration = "Debug",
    
    [Parameter(Mandatory=$false)]
    [switch]$Clean,
    
    [Parameter(Mandatory=$false)]
    [switch]$RunClangTidy,
    
    [Parameter(Mandatory=$false)]
    [switch]$RunClangFormat,
    
    [Parameter(Mandatory=$false)]
    [switch]$UseNinja
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Get script directory and project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "Building Encrypted Backup Client with MSVC..." -ForegroundColor Green
Write-Host "Configuration: $Configuration" -ForegroundColor Yellow
Write-Host "Project Root: $ProjectRoot" -ForegroundColor Yellow

# Change to project root
Set-Location $ProjectRoot

# Determine preset name
if ($UseNinja) {
    $PresetName = "msvc-ninja-$($Configuration.ToLower())"
} else {
    $PresetName = "msvc-$($Configuration.ToLower())"
}

Write-Host "Using preset: $PresetName" -ForegroundColor Yellow

# Clean if requested
if ($Clean) {
    Write-Host "Cleaning build directory..." -ForegroundColor Yellow
    $BuildDir = "build/$PresetName"
    if (Test-Path $BuildDir) {
        Remove-Item -Recurse -Force $BuildDir
        Write-Host "Cleaned $BuildDir" -ForegroundColor Green
    }
}

# Configure the project
Write-Host "Configuring project..." -ForegroundColor Yellow
try {
    cmake --preset $PresetName
    if ($LASTEXITCODE -ne 0) {
        throw "CMake configuration failed with exit code $LASTEXITCODE"
    }
    Write-Host "Configuration completed successfully!" -ForegroundColor Green
} catch {
    Write-Error "Configuration failed: $_"
    exit 1
}

# Build the project
Write-Host "Building project..." -ForegroundColor Yellow
try {
    cmake --build --preset $PresetName --config $Configuration
    if ($LASTEXITCODE -ne 0) {
        throw "Build failed with exit code $LASTEXITCODE"
    }
    Write-Host "Build completed successfully!" -ForegroundColor Green
} catch {
    Write-Error "Build failed: $_"
    exit 1
}

# Run clang-format if requested
if ($RunClangFormat) {
    Write-Host "Running clang-format..." -ForegroundColor Yellow
    try {
        cmake --build "build/$PresetName" --target clang-format
        Write-Host "clang-format completed!" -ForegroundColor Green
    } catch {
        Write-Warning "clang-format failed or not available: $_"
    }
}

# Run clang-tidy if requested
if ($RunClangTidy) {
    Write-Host "Running clang-tidy..." -ForegroundColor Yellow
    try {
        cmake --build "build/$PresetName" --target clang-tidy
        Write-Host "clang-tidy completed!" -ForegroundColor Green
    } catch {
        Write-Warning "clang-tidy failed or not available: $_"
    }
}

Write-Host "All operations completed successfully!" -ForegroundColor Green
Write-Host "Executable location: build/$PresetName/bin/client.exe" -ForegroundColor Cyan
