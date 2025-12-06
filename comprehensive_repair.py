"""
COMPREHENSIVE app.js Repair Script
Strategy: The file has every standalone `}` stripped. Structure is broken.
We need to:
1. Detect method/class/function boundaries
2. Calculate expected indent for each line
3. Insert closing braces when indent should decrease
"""
import re

def repair_app_js(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Patterns for detecting structure beginnings
    class_pattern = re.compile(r'^(\s*)class\s+\w+')
    method_pattern = re.compile(r'^(\s*)(static\s+)?(\basync\s+)?(#?\w+)\s*\([^)]*\)\s*\{?\s*$')
    func_pattern = re.compile(r'^(\s*)(async\s+)?function\s+\w+')
    arrow_func = re.compile(r'^(\s*)const\s+\w+\s*=\s*(\([^)]*\)|[^=]+)\s*=>')

    # Track what we're inside
    brace_stack = []  # Stack of (indent_level, type)
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        current_indent = len(line) - len(line.lstrip())

        # Skip empty lines and comments
        if not stripped or stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
            result.append(line)
            i += 1
            continue

        # Detect structure starts
        is_class = bool(class_pattern.match(line))
        is_method = bool(method_pattern.match(stripped)) and '(' in stripped
        is_function = bool(func_pattern.match(line))

        # Key insight: If we're at a method definition but we're deeply indented,
        # we need to close previous structures

        # Expected indents:
        # - Top-level (class declarations, const declarations): 0
        # - Class methods: 2
        # - Inside method: 4+

        expected_indent = 0
        if is_class:
            expected_indent = 0
        elif is_method and not stripped.startswith('static'):
            # Private methods (#name) should be at 2-space indent
            if stripped.startswith('#'):
                expected_indent = 2
            elif 'static ' in stripped:
                expected_indent = 2
            else:
                expected_indent = 2
        elif 'static ' in stripped and ('(' in stripped):
            expected_indent = 2
        elif stripped.startswith('async ') and '(' in stripped:
            # async methods in class
            expected_indent = 2

        # If this line should be at a specific indent but is too deep,
        # we may need to close braces

        # Check for } catch or } else patterns - these need special handling
        if stripped.startswith('} catch') or stripped.startswith('} else') or stripped.startswith('} finally'):
            # The } is closing something, and catch/else/finally opens new block
            # This is likely correct as-is (the } closes the if/try)
            pass

        result.append(line)
        i += 1

    # Write result
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(result)

    print(f"Written to {output_file}")

# This approach is too naive. Let me try a different strategy:
# Build a proper parsing state machine

def analyze_and_suggest(input_file):
    """Analyze the file and suggest specific line-by-line fixes"""
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    suggestions = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())

        # Check for common broken patterns:

        # 1. `} catch` without proper preceding closure
        if '} catch' in stripped:
            prev = lines[i-1].strip() if i > 0 else ''
            if prev and not prev.endswith('}') and not prev.endswith('{'):
                suggestions.append((i+1, "INSERT_BRACE_BEFORE", f"Need '}' before line {i+1}: {stripped[:50]}"))

        # 2. `} else` without proper preceding closure
        if '} else' in stripped:
            prev = lines[i-1].strip() if i > 0 else ''
            if prev and not prev.endswith('}') and not prev.endswith('{'):
                suggestions.append((i+1, "INSERT_BRACE_BEFORE", f"Need '}' before line {i+1}: {stripped[:50]}"))

        # 3. Method/function definition at wrong indent
        if (stripped.startswith('static ') or stripped.startswith('#') or
            stripped.startswith('async ') or stripped.startswith('constructor')):
            if '(' in stripped:
                # This should be at class level (indent 2)
                if indent != 2 and indent != 0:
                    suggestions.append((i+1, "WRONG_INDENT", f"Line {i+1} should be at indent 2, is {indent}: {stripped[:50]}"))

        # 4. Class definition at wrong indent
        if stripped.startswith('class '):
            if indent != 0:
                suggestions.append((i+1, "WRONG_INDENT", f"Line {i+1} class should be at indent 0, is {indent}: {stripped[:50]}"))

    return suggestions

if __name__ == "__main__":
    print("Analyzing app_debloated.js for structural issues...\n")
    suggestions = analyze_and_suggest('api_server/web_ui/js/app_debloated.js')

    print(f"Found {len(suggestions)} potential issues:\n")
    for item in suggestions[:50]:  # Show first 50
        line, issue_type, desc = item
        print(f"  [{issue_type}] {desc}")

    if len(suggestions) > 50:
        print(f"\n  ... and {len(suggestions) - 50} more issues")
