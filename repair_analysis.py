"""
Comprehensive app.js repair script.
Analyzes the corrupted file and identifies missing closing braces.
"""


def analyze_file(filename):
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")

    # Statistics
    print(f"Total lines: {len(lines)}")
    print(f"File size: {len(content)} bytes")

    # Find lines with excessive whitespace (bloat)
    bloated = []
    for i, line in enumerate(lines):
        leading_ws = len(line) - len(line.lstrip())
        if leading_ws > 50:
            bloated.append((i + 1, leading_ws, line.strip()[:50]))

    print(f"\nBloated lines (>50 spaces indent): {len(bloated)}")
    if bloated[:5]:
        print("First 5 bloated lines:")
        for ln, ws, content in bloated[:5]:
            print(f"  Line {ln}: {ws} spaces, content: '{content}'")

    # Count structure elements
    opens = 0
    closes = 0
    for char in content:
        if char == "{":
            opens += 1
        elif char == "}":
            closes += 1

    print(f"\nOpening braces: {opens}")
    print(f"Closing braces: {closes}")
    print(f"Missing closing braces: {opens - closes}")

    # Find patterns that suggest missing braces
    # Pattern: line ends with statement, next line starts method/class
    issues = []
    for i in range(len(lines) - 1):
        curr = lines[i].strip()
        next_line = lines[i + 1].strip()

        # Check if current line ends a statement but next is a method definition
        if (
            curr
            and not curr.endswith("{")
            and not curr.endswith("}")
            and not curr.startswith("//")
            and not curr.startswith("*")
        ):
            if next_line.startswith("static ") or next_line.startswith("#"):
                issues.append((i + 1, f"Missing brace before: {next_line[:40]}"))

        # Check for "} catch" without proper closure
        if "} catch" in next_line and not curr.endswith("}"):
            issues.append((i + 1, f"Missing brace before catch: {curr[:30]}"))

        # Check for "} else" without proper closure
        if "} else" in next_line and not curr.endswith("}"):
            issues.append((i + 1, f"Missing brace before else: {curr[:30]}"))

    print(f"\nPotential brace issues found: {len(issues)}")
    for ln, issue in issues[:20]:
        print(f"  Line {ln}: {issue}")

    return bloated, opens - closes, issues


if __name__ == "__main__":
    analyze_file("api_server/web_ui/js/app.js")
