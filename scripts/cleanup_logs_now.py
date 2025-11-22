#!/usr/bin/env python3
"""One-time log cleanup script - keeps only the last 2 log files."""
from pathlib import Path

logs_dir = Path(__file__).parent.parent / "logs"

# Get all log files sorted by modification time (newest first)
log_files = sorted(logs_dir.glob("*.log"), key=lambda f: f.stat().st_mtime, reverse=True)

# Calculate before stats
before_count = len(log_files)
before_size = sum(f.stat().st_size for f in log_files)

# Keep only the last 2
files_to_keep = log_files[:2]
files_to_delete = log_files[2:]

# Delete old files
deleted_count = 0
deleted_size = 0
for f in files_to_delete:
    deleted_size += f.stat().st_size
    f.unlink()
    deleted_count += 1

# After stats
remaining_files = list(logs_dir.glob("*.log"))
after_count = len(remaining_files)
after_size = sum(f.stat().st_size for f in remaining_files)

# Output results
print(f"BEFORE_SIZE_BYTES:{before_size}")
print(f"BEFORE_COUNT:{before_count}")
print(f"DELETED_COUNT:{deleted_count}")
print(f"DELETED_SIZE_BYTES:{deleted_size}")
print(f"AFTER_SIZE_BYTES:{after_size}")
print(f"AFTER_COUNT:{after_count}")
print(f"SAVED_MB:{deleted_size / (1024*1024):.2f}")
print("KEPT_FILES:")
for f in sorted(remaining_files, key=lambda x: x.stat().st_mtime, reverse=True):
    print(f"  - {f.name} ({f.stat().st_size / 1024:.2f} KB)")
