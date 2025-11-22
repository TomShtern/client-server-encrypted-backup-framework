#!/usr/bin/env python3
"""Consolidate scattered Flet documentation to /docs/flet/"""
import shutil
from pathlib import Path

BASE = Path(r"C:\Users\tom7s\Desktopp\Claude_Folder_2\Client_Server_Encrypted_Backup_Framework")
FLET_DOCS_DIR = BASE / "docs" / "flet"

# Create target directory
FLET_DOCS_DIR.mkdir(parents=True, exist_ok=True)

# Files to move (source -> keep original name or rename)
files_to_move = [
    # From AI-CONTEXT-IMPORTANT
    ("AI-CONTEXT-IMPORTANT/Flet_0.28.3_Handbook_for_Agents.md", None),
    ("AI-CONTEXT-IMPORTANT/Flet_0.28.3_Supplemental_Guide.md", None),
    ("AI-CONTEXT-IMPORTANT/flet_docs.md", None),
    ("AI-CONTEXT-IMPORTANT/Controls_Reference_flet.md", None),
    ("AI-CONTEXT-IMPORTANT/AppBar_flet.md", None),
    ("AI-CONTEXT-IMPORTANT/MenuBar_flet.md", None),
    ("AI-CONTEXT-IMPORTANT/Navigation_Drawer_flet.md", None),
    ("AI-CONTEXT-IMPORTANT/Flet_Web_Hot_Reload.md", None),
    ("AI-CONTEXT-IMPORTANT/FletV2_Analysis_01.10.2025.md", None),
    ("AI-CONTEXT-IMPORTANT/Flet_Integration_Plan_to_fully_Operational_01102025.md", None),
    # Skip Badge_flet.md - it's empty (0 bytes)

    # From root level
    ("The_Real_Flet_M3_Anti_Patterns_Fix_Plan.md", None),
    ("material_3_in_flet_implementation_guide.md", None),
    ("FLET_0.28.3_ERROR_REFERENCE.md", None),
    ("FLETV2_INTEGRATION_IMPLEMENTATION_SUMMARY.md", None),
    ("FLETV2_INTEGRATION_PLAN.md", None),
    ("FLET_V2_PERFORMANCE_OPTIMIZATION_PLAN.md", None),
    ("flet_skill_trigger_analysis.md", None),
]

moved = []
skipped = []
errors = []

for src_rel, new_name in files_to_move:
    src = BASE / src_rel
    if not src.exists():
        skipped.append(f"{src_rel} (not found)")
        continue

    # Skip empty files
    if src.stat().st_size == 0:
        skipped.append(f"{src_rel} (empty file)")
        continue

    target_name = new_name or src.name
    target = FLET_DOCS_DIR / target_name

    try:
        shutil.move(str(src), str(target))
        moved.append(f"{src_rel} -> docs/flet/{target_name}")
    except Exception as e:
        errors.append(f"{src_rel}: {e}")

print("=== Flet Documentation Consolidation ===\n")

print(f"Moved {len(moved)} files:")
for m in moved:
    print(f"  ✓ {m}")

if skipped:
    print(f"\nSkipped {len(skipped)} files:")
    for s in skipped:
        print(f"  - {s}")

if errors:
    print(f"\nErrors ({len(errors)}):")
    for e in errors:
        print(f"  ✗ {e}")

# Create an index file
index_content = """# Flet Documentation Index

This folder consolidates all Flet 0.28.3 documentation for the CyberBackup 3.0 project.

## Core References
- [Flet_0.28.3_Handbook_for_Agents.md](Flet_0.28.3_Handbook_for_Agents.md) - Primary agent guide
- [Flet_0.28.3_Supplemental_Guide.md](Flet_0.28.3_Supplemental_Guide.md) - Additional patterns
- [flet_docs.md](flet_docs.md) - General Flet documentation
- [Controls_Reference_flet.md](Controls_Reference_flet.md) - Control catalog

## Component Documentation
- [AppBar_flet.md](AppBar_flet.md) - AppBar component
- [MenuBar_flet.md](MenuBar_flet.md) - MenuBar component
- [Navigation_Drawer_flet.md](Navigation_Drawer_flet.md) - Navigation drawer

## Implementation Guides
- [material_3_in_flet_implementation_guide.md](material_3_in_flet_implementation_guide.md) - M3 theming
- [The_Real_Flet_M3_Anti_Patterns_Fix_Plan.md](The_Real_Flet_M3_Anti_Patterns_Fix_Plan.md) - Anti-patterns
- [FLET_0.28.3_ERROR_REFERENCE.md](FLET_0.28.3_ERROR_REFERENCE.md) - Common errors

## Project-Specific
- [FLETV2_INTEGRATION_PLAN.md](FLETV2_INTEGRATION_PLAN.md) - Integration plan
- [FLETV2_INTEGRATION_IMPLEMENTATION_SUMMARY.md](FLETV2_INTEGRATION_IMPLEMENTATION_SUMMARY.md) - Implementation summary
- [FLET_V2_PERFORMANCE_OPTIMIZATION_PLAN.md](FLET_V2_PERFORMANCE_OPTIMIZATION_PLAN.md) - Performance
- [FletV2_Analysis_01.10.2025.md](FletV2_Analysis_01.10.2025.md) - Analysis report

## Additional Resources
- [Flet_Web_Hot_Reload.md](Flet_Web_Hot_Reload.md) - Hot reload guide
- [Flet_Integration_Plan_to_fully_Operational_01102025.md](Flet_Integration_Plan_to_fully_Operational_01102025.md) - Full operation plan
- [flet_skill_trigger_analysis.md](flet_skill_trigger_analysis.md) - Skill triggers

## Note
Additional Flet documentation remains in:
- `FletV2/important_docs/` - Module-specific docs
- `archive/documentation/Flet_Documentation_From_Context7_&_web/` - Archived tutorials

*Consolidated: 2025-11-18*
"""

index_path = FLET_DOCS_DIR / "README.md"
index_path.write_text(index_content, encoding='utf-8')
print("\nCreated index: docs/flet/README.md")
