#!/usr/bin/env python3
"""Clean up empty marker files that are safe to delete."""
from pathlib import Path

BASE = Path(r"C:\Users\tom7s\Desktopp\Claude_Folder_2\Client_Server_Encrypted_Backup_Framework")

# Files safe to delete (temp/generated files)
files_to_delete = [
    "mcp_temp.json",
    "pyflakes_out.txt",
    "tmp/analytics_base.py",
    # Don't delete AI workspace files (.crush, .kilocode, .trae)
    # Don't delete AGENTS.md etc - user said not to merge AI instructions
    # Don't delete test stubs - might be intentional
]

deleted = []
skipped = []

for rel_path in files_to_delete:
    path = BASE / rel_path
    if path.exists():
        try:
            if path.stat().st_size == 0:
                path.unlink()
                deleted.append(rel_path)
            else:
                skipped.append(f"{rel_path} (not empty)")
        except Exception as e:
            skipped.append(f"{rel_path}: {e}")
    else:
        skipped.append(f"{rel_path} (not found)")

print("=== Empty Marker Files Cleanup ===\n")

print(f"Deleted {len(deleted)} files:")
for d in deleted:
    print(f"  ✓ {d}")

if skipped:
    print(f"\nSkipped {len(skipped)} files:")
    for s in skipped:
        print(f"  - {s}")

print("\nNote: Preserved AI workspace files (.crush, .kilocode, .trae)")
print("Note: Preserved AGENTS.md, QWEN.md, etc (AI instructions)")
print("Note: Preserved test stubs (tests/test_*.py)")
