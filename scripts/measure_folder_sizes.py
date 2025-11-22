#!/usr/bin/env python3
"""Measure actual folder sizes for PROJECT_STRUCTURE_AND_DUPLICATION_REPORT.md verification."""
from pathlib import Path
import json

BASE = Path(r"C:\Users\tom7s\Desktopp\Claude_Folder_2\Client_Server_Encrypted_Backup_Framework")

def measure_folder(folder_path: Path) -> dict:
    """Measure folder size and file count."""
    if not folder_path.exists():
        return {"files": 0, "bytes": 0, "mb": 0}

    total_size = 0
    file_count = 0

    try:
        for item in folder_path.rglob("*"):
            if item.is_file():
                try:
                    total_size += item.stat().st_size
                    file_count += 1
                except (OSError, PermissionError):
                    pass
    except (OSError, PermissionError):
        pass

    return {
        "files": file_count,
        "bytes": total_size,
        "mb": round(total_size / (1024 * 1024), 2)
    }

def format_size(mb: float) -> str:
    """Format size for display."""
    if mb >= 1024:
        return f"{mb/1024:.2f} GB"
    elif mb >= 1:
        return f"{mb:.2f} MB"
    else:
        return f"{int(mb * 1024)} KB"

# Define all folders to measure
folders = {
    # Core Application
    "FletV2": "FletV2",
    "python_server": "python_server",
    "api_server": "api_server",
    "Client": "Client",
    "Shared": "Shared",
    "cpp_api_server": "cpp_api_server",
    "scripts": "scripts",
    "tests": "tests",

    # Documentation
    "docs": "docs",
    "AI-CONTEXT-IMPORTANT": "AI-CONTEXT-IMPORTANT",
    "archive": "archive",

    # AI Workspaces
    ".specstory": ".specstory",
    ".factory": ".factory",
    ".gemini": ".gemini",
    ".serena": ".serena",
    ".qwen": ".qwen",
    ".kilocode": ".kilocode",
    ".roo": ".roo",
    ".trae": ".trae",
    ".crush": ".crush",

    # Runtime & Data
    "logs": "logs",
    "Database": "Database",
    "data": "data",
    "received_files": "received_files",
    "backups": "backups",
    "config": "config",

    # Assets
    "favicon_stuff": "favicon_stuff",
    "ScreenShots": "ScreenShots",
    ".playwright-mcp": ".playwright-mcp",

    # Dev Tools
    ".vscode": ".vscode",
    ".claude": ".claude",
    ".github": ".github",
    ".circleci": ".circleci",

    # Misc
    "tmp": "tmp",
    "stubs": "stubs",
}

results = {}

print("=" * 60)
print("FOLDER SIZE MEASUREMENTS")
print("=" * 60)

# Measure each folder
for name, path in folders.items():
    folder_path = BASE / path
    data = measure_folder(folder_path)
    results[name] = data
    if data["files"] > 0:
        print(f"{name}|{data['files']}|{data['bytes']}|{format_size(data['mb'])}")

# Measure root files
root_files = [f for f in BASE.iterdir() if f.is_file()]
root_size = sum(f.stat().st_size for f in root_files)
root_count = len(root_files)
results["[root]"] = {"files": root_count, "bytes": root_size, "mb": round(root_size / (1024 * 1024), 2)}
print(f"[root]|{root_count}|{root_size}|{format_size(root_size / (1024 * 1024))}")

# Calculate totals
total_files = sum(r["files"] for r in results.values())
total_bytes = sum(r["bytes"] for r in results.values())
total_mb = total_bytes / (1024 * 1024)

print("=" * 60)
print(f"TOTAL|{total_files}|{total_bytes}|{format_size(total_mb)}")

# AI Workspaces total
ai_workspaces = [".specstory", ".factory", ".gemini", ".serena", ".qwen", ".kilocode", ".roo", ".trae", ".crush"]
ai_total_files = sum(results.get(w, {}).get("files", 0) for w in ai_workspaces)
ai_total_bytes = sum(results.get(w, {}).get("bytes", 0) for w in ai_workspaces)
ai_total_mb = ai_total_bytes / (1024 * 1024)
print(f"AI_WORKSPACES_TOTAL|{ai_total_files}|{ai_total_bytes}|{format_size(ai_total_mb)}")

print("=" * 60)
print("\nJSON OUTPUT:")
print(json.dumps(results, indent=2))
