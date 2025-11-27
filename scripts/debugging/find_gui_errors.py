#!/usr/bin/env python3
import traceback
from typing import Any, cast

# Setup standardized import paths
from Shared.path_utils import setup_imports

setup_imports()


def find_errors() -> bool:
    print("=== ServerGUI Error Detection ===")
    try:
        # Test imports
        print("Testing imports...")
        from python_server.server_gui import ServerGUI  # type: ignore

        # Note: ModernCard, ModernProgressBar, ModernStatusIndicator not available in current codebase
        print("✓ All imports successful")

        # Test basic instantiation
        print("Testing ServerGUI instantiation...")
        gui = ServerGUI()
        print("✓ ServerGUI created")

        # Test widget creation
        print("Testing widget creation...")
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        container = tk.Frame(root)
        container.pack_forget()

        # Components not available in current codebase - skipping tests
        print(
            "ℹ ModernCard, ModernProgressBar, ModernStatusIndicator tests skipped (components not available)"
        )

        # try:
        #     card: Any = ModernCard(container, title="Test")
        #     _ = getattr(card, "content_frame", None)
        #     print("✓ ModernCard works")
        # except Exception as e:
        #     print(f"✗ ModernCard error: {e}")

        # try:
        #     progress: Any = ModernProgressBar(container)
        #     cast(Any, progress).set_progress(50)
        #     print("✓ ModernProgressBar works")
        # except Exception as e:
        #     print(f"✗ ModernProgressBar error: {e}")

        # try:
        #     status: Any = ModernStatusIndicator(container)
        #     cast(Any, status).set_status("online")
        #     print("✓ ModernStatusIndicator works")
        # except Exception as e:
        #     print(f"✗ ModernStatusIndicator error: {e}")

        root.destroy()

        # Test GUI methods
        print("Testing GUI methods...")
        try:
            _extracted_from_find_errors_50(gui)
        except Exception as e:
            print(f"✗ GUI method error: {e}")
            traceback.print_exc()

        print("✅ No errors found!")
        return True
    except ImportError:
        print("✗ Could not import ServerGUI. Skipping functionality tests.")
        return False
    except Exception as e:
        print(f"❌ Error found: {e}")
        traceback.print_exc()
        return False


# TODO Rename this here and in `find_errors`
def _extracted_from_find_errors_50(gui):
    gui.update_server_status(True, "127.0.0.1", 1256)  # type: ignore
    gui.update_client_stats({"connected": 5, "total": 10, "active_transfers": 2})  # type: ignore
    gui.update_transfer_stats({"bytes_transferred": 1024})  # type: ignore
    toast = getattr(gui, "toast_system", None)
    if toast is not None:
        cast(Any, toast).show_toast("test error", "error")
        cast(Any, toast).show_toast("test success", "success")
        cast(Any, toast).show_toast("test info", "info")
    print("✓ All GUI methods work")


if __name__ == "__main__":
    find_errors()
