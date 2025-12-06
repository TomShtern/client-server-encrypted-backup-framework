"""
Phase 2: Restore missing closing braces in app.js
"""


def restore_braces(filename, output_filename):
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()

    fixed_lines = []
    fixes_made = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        prev_stripped = lines[i - 1].strip() if i > 0 else ""

        # Get the indentation of the current line
        current_indent = len(line) - len(line.lstrip())

        # Check if we need to insert a closing brace before this line
        needs_brace = False
        brace_indent = current_indent

        # Pattern 1: "} catch" where previous line doesn't end the block
        if (
            stripped.startswith("} catch")
            or stripped == "} catch (logError) {"
            or stripped == "} catch (toastError) {"
            or "} catch (" in stripped
        ):
            if (
                prev_stripped
                and not prev_stripped.endswith("}")
                and not prev_stripped.endswith("};")
            ):
                needs_brace = True
                brace_indent = current_indent + 2  # One level deeper than the catch

        # Pattern 2: "} else" where previous line doesn't end the block
        elif stripped.startswith("} else"):
            if (
                prev_stripped
                and not prev_stripped.endswith("}")
                and not prev_stripped.endswith("};")
            ):
                needs_brace = True
                brace_indent = current_indent + 2

        # Pattern 3: Static method or private method definition when previous line is a statement
        elif (
            stripped.startswith("static ") or stripped.startswith("#")
        ) and "(" in stripped:
            if (
                prev_stripped
                and not prev_stripped.endswith("}")
                and not prev_stripped.endswith("};")
                and not prev_stripped.endswith("{")
            ):
                # This is a method definition appearing after an unclosed statement
                # Need to close the previous method/block
                needs_brace = True
                brace_indent = current_indent  # Same level as new method

        # Pattern 4: Class-level "}" that should close a class but appears after a statement
        # (For the end of the file)

        if needs_brace:
            # Insert closing brace
            brace_line = " " * brace_indent + "}\n"
            fixed_lines.append(brace_line)
            fixes_made += 1
            print(f"Line {i + 1}: Inserted '}}' before: {stripped[:50]}")

        fixed_lines.append(line)

    # Write fixed file
    with open(output_filename, "w", encoding="utf-8") as f:
        f.writelines(fixed_lines)

    print(f"\nTotal fixes made: {fixes_made}")
    print(f"Output written to: {output_filename}")

    return fixes_made


if __name__ == "__main__":
    # First run on debloated version
    fixes = restore_braces(
        "api_server/web_ui/js/app_debloated.js", "api_server/web_ui/js/app_fixed.js"
    )
    print("\nPhase 2 complete. Now run: node --check api_server/web_ui/js/app_fixed.js")
