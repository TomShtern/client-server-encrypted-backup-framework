"""
Comprehensive app.js repair script - Phase 1: De-bloat whitespace
"""

import re


def debloat_file(filename, output_filename):
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()

    fixed_lines = []
    in_bloated_section = False
    bloat_start = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        leading_ws = len(line) - len(line.lstrip())

        # Check if this line is bloated (>50 spaces indent)
        if leading_ws > 50 and stripped:
            if not in_bloated_section:
                in_bloated_section = True
                bloat_start = i
                print(f"Bloated section starts at line {i + 1}")

            # Determine the "true" indentation level from the content
            # Look for patterns that indicate structure:
            # - 'if (' at various legal depths
            # - 'for (' at various legal depths
            # - method definitions starting with '#' or keywords
            # - 'const/let/var' statements

            # Try to infer correct indentation from content type
            if stripped.startswith("class "):
                correct_indent = 0
            elif stripped.startswith("static ") or stripped.startswith("#"):
                correct_indent = 2  # Method level in class
            elif (
                re.match(r"^(if|for|while|try|switch)\s*\(", stripped)
                or stripped.startswith("} else")
                or stripped.startswith("} catch")
            ):
                correct_indent = 4  # Inside method
            elif (
                stripped.startswith("return ")
                or stripped.startswith("const ")
                or stripped.startswith("let ")
                or stripped.startswith("this.")
            ):
                correct_indent = 4  # Statement level
            else:
                # Default: estimate based on nesting
                # Count depth indicators in the line
                correct_indent = 4 + (stripped.count("{") - stripped.count("}")) * 2
                if correct_indent < 0:
                    correct_indent = 4

            fixed_line = " " * correct_indent + stripped + "\n"
            fixed_lines.append(fixed_line)
        else:
            if in_bloated_section:
                print(
                    f"Bloated section ended at line {i + 1} (lines {bloat_start + 1} to {i})"
                )
                in_bloated_section = False
            fixed_lines.append(line)

    with open(output_filename, "w", encoding="utf-8") as f:
        f.writelines(fixed_lines)

    print(f"\nFixed file written to: {output_filename}")
    print(f"Original size: {sum(len(l) for l in lines)} chars")
    print(f"Fixed size: {sum(len(l) for l in fixed_lines)} chars")


if __name__ == "__main__":
    debloat_file("api_server/web_ui/js/app.js", "api_server/web_ui/js/app_debloated.js")
