#!/usr/bin/env python3
"""
Comprehensive validation script for flet_venv workspace setup
Tests both current folder and workspace file contexts
"""

import json
import os
import sys
from pathlib import Path

# Import UTF-8 solution first
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import Shared.filesystem.utf8_solution

    _ = Shared.filesystem.utf8_solution
    print("[INFO] UTF-8 solution imported successfully")
except ImportError as e:
    print(f"[WARNING] UTF-8 solution not available: {e}")


def validate_python_environment():
    """Validate that we're using the correct Python environment"""
    print("\n" + "=" * 60)
    print("🐍 PYTHON ENVIRONMENT VALIDATION")
    print("=" * 60)

    current_python = Path(sys.executable)
    expected_path = project_root / "flet_venv" / "Scripts" / "python.exe"

    print(f"Current Python: {current_python}")
    print(f"Expected Path:  {expected_path}")

    if "flet_venv" in str(current_python):
        print("✅ CORRECT: Using flet_venv environment")
        env_status = True
    else:
        print("❌ INCORRECT: Not using flet_venv environment")
        env_status = False

    virtual_env = os.environ.get("VIRTUAL_ENV", "Not set")
    print(f"Virtual Environment Variable: {virtual_env}")

    return env_status


def validate_package_imports():
    """Test that all required packages are available"""
    print("\n" + "=" * 60)
    print("📦 PACKAGE IMPORT VALIDATION")
    print("=" * 60)

    packages = [
        "flet",
        "flask",
        "requests",
        "psutil",
        "matplotlib",
        "pydantic",
        "aiofiles",
        "watchdog",
        "loguru",
        "cryptography",
    ]

    success_count = 0
    for package in packages:
        try:
            __import__(package)
            print(f"✅ {package}")
            success_count += 1
        except ImportError as e:
            print(f"❌ {package} - {e}")

    print(f"\nPackage Success Rate: {success_count}/{len(packages)}")
    return success_count == len(packages)


def validate_vscode_configuration():
    """Check VS Code configuration files"""
    print("\n" + "=" * 60)
    print("⚙️ VS CODE CONFIGURATION VALIDATION")
    print("=" * 60)

    # project_root is already defined globally or we can redefine it locally if needed,
    # but since we defined it at top level, we can use it if we pass it or redefine it.
    # To be safe and consistent with local scope:
    project_root = Path(__file__).parent.parent.parent
    vscode_dir = project_root / ".vscode"

    config_files = {
        "settings.json": vscode_dir / "settings.json",
        "launch.json": vscode_dir / "launch.json",
        "python.json": vscode_dir / "python.json",
        "main_workspace": project_root
        / "Client-Server-Backup-Framework.code-workspace",
        "fletv2_workspace": project_root / "FletV2-Workspace.code-workspace",
    }

    all_valid = True
    for name, path in config_files.items():
        if path.exists():
            print(f"✅ {name}: {path}")
            if name.endswith(".json") or name.endswith(".code-workspace"):
                try:
                    with open(path, encoding="utf-8") as f:
                        config = json.load(f)
                        # Check for flet_venv references
                        config_str = json.dumps(config)
                        if "flet_venv" in config_str:
                            print("   ✓ Contains flet_venv references")
                        else:
                            print("   ⚠️ No flet_venv references found")
                except Exception as e:
                    print(f"   ❌ Error reading {name}: {e}")
                    all_valid = False
        else:
            print(f"❌ {name}: Missing - {path}")
            all_valid = False

    return all_valid


def validate_workspace_files():
    """Check workspace files contain correct settings"""
    print("\n" + "=" * 60)
    print("📁 WORKSPACE FILE VALIDATION")
    print("=" * 60)

    project_root = Path(__file__).parent.parent.parent
    workspace_files = [
        project_root / "Client-Server-Backup-Framework.code-workspace",
        project_root / "FletV2-Workspace.code-workspace",
    ]

    all_valid = True
    for workspace_file in workspace_files:
        print(f"\nChecking: {workspace_file.name}")
        if workspace_file.exists():
            try:
                with open(workspace_file, encoding="utf-8") as f:
                    workspace_config = json.load(f)

                # Check settings
                settings = workspace_config.get("settings", {})
                interpreter_path = settings.get("python.defaultInterpreterPath", "")

                if "./flet_venv/Scripts/python.exe" in interpreter_path:
                    print("   ✅ Correct Python interpreter path")
                else:
                    print(f"   ❌ Wrong interpreter path: {interpreter_path}")
                    all_valid = False

                # Check launch configurations
                launch_config = workspace_config.get("launch", {})
                configurations = launch_config.get("configurations", [])

                flet_venv_configs = 0
                for config in configurations:
                    python_path = config.get("python", "")
                    if "flet_venv" in python_path:
                        flet_venv_configs += 1

                print(f"   ✅ {flet_venv_configs} launch configs use flet_venv")

            except Exception as e:
                print(f"   ❌ Error reading workspace file: {e}")
                all_valid = False
        else:
            print(f"   ❌ Workspace file missing: {workspace_file}")
            all_valid = False

    return all_valid


def main():
    """Run comprehensive validation"""
    print("🔍 COMPREHENSIVE FLET_VENV WORKSPACE VALIDATION")
    print("=" * 80)

    results = {
        "python_environment": validate_python_environment(),
        "package_imports": validate_package_imports(),
        "vscode_configuration": validate_vscode_configuration(),
        "workspace_files": validate_workspace_files(),
    }

    print("\n" + "=" * 80)
    print("📊 VALIDATION SUMMARY")
    print("=" * 80)

    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name.replace('_', ' ').title()}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 ALL VALIDATIONS PASSED!")
        print("🚀 flet_venv is properly configured for both workspace contexts")
        print("\nNext Steps:")
        print("1. Close VS Code completely")
        print("2. Open either workspace file:")
        print("   - Client-Server-Backup-Framework.code-workspace (main)")
        print("   - FletV2-Workspace.code-workspace (FletV2 focused)")
        print("3. Verify VS Code status bar shows 'flet_venv' as active interpreter")
    else:
        print("⚠️ SOME VALIDATIONS FAILED")
        print(
            "Review the errors above and ensure all configuration files are properly set"
        )
    print("=" * 80)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
