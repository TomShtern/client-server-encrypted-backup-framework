#!/usr/bin/env python3
"""Comprehensive test and demo for utf8_solution functionality.

This script demonstrates and tests all enhanced features of utf8_solution
with and without optional libraries. Run this to verify everything works.
"""

import os
import sys

# Add the project root to the path so we can import utf8_solution
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

import Shared.filesystem.utf8_solution as utf8  # noqa: E402


def demo_basic_functionality():
    """Demonstrate basic UTF-8 functionality."""
    utf8.safe_print("=" * 60)
    utf8.safe_print("🧪 BASIC UTF-8 FUNCTIONALITY")
    utf8.safe_print("=" * 60)

    # Test safe_print with various Unicode characters
    utf8.safe_print("✅ Basic safe_print test")
    utf8.safe_print("🎉 Emojis: 🌍 🚀 ⭐ 💖 🔥 ✨ 🎯 📊")
    utf8.safe_print("📝 Hebrew: שלום עולם")
    utf8.safe_print("🔤 Mixed: Hello שלום World עולם 🌍")

    # Test RTL printing
    utf8.safe_print("\n📐 RTL Processing:")
    utf8.rtl_print("שלום עולם")
    utf8.rtl_print("בדיקה test ✅")
    utf8.rtl_print("Hello שלום World עולם")


def demo_enhanced_features():
    """Demonstrate enhanced features with optional libraries."""
    utf8.safe_print("\n" + "=" * 60)
    utf8.safe_print("🎨 ENHANCED FEATURES DEMO")
    utf8.safe_print("=" * 60)

    # Rich console features
    utf8.safe_print("🎨 Rich Console Output:")
    utf8.safe_print("[bold green]✅ Success message[/bold green]")
    utf8.safe_print("[red]❌ Error message[/red]")
    utf8.safe_print("[blue]ℹ️ Info message[/blue]")
    utf8.safe_print("🎉 [bold]Enhanced[/bold] with [italic]rich[/italic] markup!")

    # Text width and formatting
    utf8.safe_print("\n📏 Text Width & Formatting:")
    test_texts = ["A", "🎉", "שלום", "Hello", "🌍"]
    for text in test_texts:
        width = utf8.get_text_width(text)
        utf8.safe_print(f"   '{text}' → width: {width}")

    # Text alignment
    utf8.safe_print("\n📐 Text Alignment:")
    test_word = "🎉Hello"
    utf8.safe_print(f"Original: '{test_word}'")
    utf8.safe_print(f"Left:     '{utf8.pad_text(test_word, 20, align='left')}'")
    utf8.safe_print(f"Center:   '{utf8.pad_text(test_word, 20, align='center')}'")
    utf8.safe_print(f"Right:    '{utf8.pad_text(test_word, 20, align='right')}'")


def demo_table_formatting():
    """Demonstrate table formatting."""
    utf8.safe_print("\n" + "=" * 60)
    utf8.safe_print("📋 TABLE FORMATTING DEMO")
    utf8.safe_print("=" * 60)

    # Create a demo table
    headers = ["File", "Size", "Status", "Notes"]
    widths = [25, 10, 12, 20]

    # Header row
    header_row = utf8.format_table_row(headers, widths)
    separator = utf8.format_table_row(["-" * w for w in widths], widths)

    utf8.safe_print(header_row)
    utf8.safe_print(separator)

    # Data rows with Unicode content
    test_data = [
        ["config.txt", "1.2 KB", "✅ Ready", "Basic config"],
        ["שלום.doc", "0.8 MB", "🔄 Processing", "Hebrew document"],
        ["emoji_🎉_test.png", "2.1 MB", "❌ Failed", "Image with emoji"],
        [
            "very_long_filename_that_needs_truncation.xlsx",
            "15.7 MB",
            "⏳ Queued",
            "Will be shortened",
        ],
    ]

    for row_data in test_data:
        # Truncate long filenames
        row_data[0] = utf8.truncate_text(row_data[0], widths[0] - 2)
        row = utf8.format_table_row(row_data, widths)
        utf8.safe_print(row)


def demo_framework_integration():
    """Show how this integrates with the framework."""
    utf8.safe_print("\n" + "=" * 60)
    utf8.safe_print("🔧 FRAMEWORK INTEGRATION DEMO")
    utf8.safe_print("=" * 60)

    # Simulate API server startup
    utf8.safe_print("\n🚀 API Server Startup:")
    utf8.safe_print("[green]✅[/green] Environment initialized")
    utf8.safe_print("[blue]🔗[/blue] Flask server starting on port 9090")
    utf8.safe_print("[yellow]⚡[/yellow] C++ client ready")

    # Simulate backup progress
    utf8.safe_print("\n📤 Backup Progress Demo:")

    files = [
        ("document.pdf", "2.3 MB", 100, "✅"),
        ("photos_🎉.zip", "15.7 MB", 75, "🔄"),
        ("הקבצים_שלי.docx", "0.9 MB", 45, "🔄"),
        ("backup_final.tar.gz", "127 MB", 0, "⏳"),
    ]

    # Progress header
    progress_headers = ["Filename", "Size", "Progress", "Status"]
    progress_widths = [30, 10, 15, 8]

    utf8.safe_print(utf8.format_table_row(progress_headers, progress_widths))
    utf8.safe_print(
        utf8.format_table_row(["-" * w for w in progress_widths], progress_widths)
    )

    for filename, size, progress, status in files:
        display_name = utf8.truncate_text(filename, 27)
        progress_bar = "█" * (progress // 10) + "░" * (10 - progress // 10)
        progress_text = f"{progress_bar} {progress}%"

        row_data = [display_name, size, progress_text, status]
        utf8.safe_print(utf8.format_table_row(row_data, progress_widths))


def test_library_status():
    """Test and display library availability."""
    utf8.safe_print("\n" + "=" * 60)
    utf8.safe_print("📦 LIBRARY STATUS TEST")
    utf8.safe_print("=" * 60)

    # Get diagnostics
    diagnosis = utf8.diagnose_utf8_environment()

    # Display basic environment info
    utf8.safe_print("🖥️ Environment:")
    utf8.safe_print(f"   Platform: {diagnosis['platform']}")
    utf8.safe_print(
        f"   UTF-8 Test: {'✅ Pass' if diagnosis['utf8_test'] else '❌ Fail'}"
    )

    # Display library status
    utf8.safe_print("\n📚 Optional Libraries:")
    libraries = diagnosis["optional_libraries"]
    for lib, available in libraries.items():
        status = "✅ Available" if available else "❌ Not installed"
        utf8.safe_print(f"   {lib}: {status}")

    # Display active enhancements
    utf8.safe_print("\n🚀 Active Enhancements:")
    enhancements = diagnosis["enhancements_active"]
    for feature, active in enhancements.items():
        status = "✅ Enhanced" if active else "📦 Basic"
        utf8.safe_print(f"   {feature.replace('_', ' ').title()}: {status}")

    # Test specific features if available
    if "bidi_test" in diagnosis:
        result = diagnosis["bidi_test"]
        utf8.safe_print(
            f"\n🔤 BiDi Test: {'✅ Pass' if result['success'] else '❌ Fail'}"
        )
        if result["success"]:
            utf8.safe_print(f"   Result: '{result['result']}'")

    if "wcwidth_test" in diagnosis:
        result = diagnosis["wcwidth_test"]
        utf8.safe_print(
            f"📏 Width Test: {'✅ Pass' if result['success'] else '❌ Fail'}"
        )
        if result["success"]:
            utf8.safe_print(f"   Width calculation: {result['width']}")


def test_text_processing():
    """Test various text processing features."""
    utf8.safe_print("\n" + "=" * 60)
    utf8.safe_print("📝 TEXT PROCESSING TEST")
    utf8.safe_print("=" * 60)

    # Test BiDi processing
    utf8.safe_print("🔤 Bidirectional Text Processing:")
    test_texts = [
        "שלום עולם",
        "Hello שלום World",
        "בדיקה test 123 ✅",
        "English and זה עברית mixed",
    ]

    for text in test_texts:
        processed = utf8.process_bidirectional_text(text)
        utf8.safe_print(f"   '{text}' → '{processed}'")

    # Test text wrapping
    utf8.safe_print("\n📄 Text Wrapping:")
    long_text = "This is a long paragraph with 🎉 emojis and שלום Hebrew text that needs proper wrapping."

    utf8.safe_print(f"Original: {long_text}")
    utf8.safe_print("Wrapped to 30 characters:")

    wrapped_lines = utf8.wrap_text(long_text, 30, indent="  ", subsequent_indent="    ")
    for line in wrapped_lines:
        utf8.safe_print(f"'{line}'")


def installation_guide():
    """Show installation guidance."""
    utf8.safe_print("\n" + "=" * 60)
    utf8.safe_print("📦 INSTALLATION GUIDE")
    utf8.safe_print("=" * 60)

    diagnosis = utf8.diagnose_utf8_environment()
    libraries = diagnosis["optional_libraries"]

    if missing := [lib for lib, available in libraries.items() if not available]:
        utf8.safe_print("🔧 Some enhancements are missing:")
        for lib in missing:
            utf8.safe_print(f"   ❌ {lib}")

        utf8.safe_print("\n📝 To install missing enhancements:")
        utf8.safe_print("   pip install -r requirements.txt")
        utf8.safe_print("\n   Or install individually:")
        for lib in missing:
            utf8.safe_print(f"   pip install {lib}")
    else:
        utf8.safe_print(
            "🎉 [bold green]Perfect! All enhancements are available![/bold green]"
        )
        utf8.safe_print("✨ You have the full enhanced utf8_solution experience!")

    utf8.safe_print(
        f"\n📊 Enhancement Status: {sum(libraries.values())}/{len(libraries)} active"
    )


def main():
    """Run all demonstrations and tests."""
    utf8.safe_print("🚀 UTF-8 Solution - Comprehensive Test & Demo")
    utf8.safe_print("=" * 60)

    # Ensure initialization
    if utf8.ensure_initialized():
        utf8.safe_print("✅ UTF-8 environment initialized successfully")
    else:
        utf8.safe_print("⚠️ UTF-8 environment initialization had issues")

    # Run all demos
    demo_basic_functionality()
    demo_enhanced_features()
    demo_table_formatting()
    demo_framework_integration()
    test_library_status()
    test_text_processing()
    installation_guide()

    # Final message
    utf8.safe_print("\n" + "=" * 60)
    utf8.safe_print("✅ Test completed successfully!")
    utf8.safe_print("🎯 To use: import Shared.utils.utf8_solution as utf8")
    utf8.safe_print("📚 Docs: Shared/utils/UTF8_SOLUTION.md")
    utf8.safe_print("=" * 60)


if __name__ == "__main__":
    main()
