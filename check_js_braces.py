def check_js_braces(filename):
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()

    stack = []
    in_block_comment = False

    # Simple state machine for parsing
    # We process character by character to handle strings and comments correctly

    for line_idx, line in enumerate(lines):
        line_num = line_idx + 1
        i = 0
        length = len(line)
        in_string = False
        string_char = ""

        while i < length:
            char = line[i]

            # Handle block comments spanning multiple lines
            if in_block_comment:
                if i + 1 < length and char == "*" and line[i + 1] == "/":
                    in_block_comment = False
                    i += 2
                    continue
                i += 1
                continue

            # Handle line comments
            if not in_string and i + 1 < length and char == "/" and line[i + 1] == "/":
                break  # Skip rest of line

            # Handle block comment start
            if not in_string and i + 1 < length and char == "/" and line[i + 1] == "*":
                in_block_comment = True
                i += 2
                continue

            # Handle strings
            if in_string:
                if char == "\\":  # Escape
                    i += 2
                    continue
                if char == string_char:
                    in_string = False
                i += 1
                continue

            # Start string
            if char in ['"', "'", "`"]:
                in_string = True
                string_char = char
                i += 1
                continue

            # Check braces
            if char == "{":
                stack.append((line_num, i + 1))
            elif char == "}":
                if not stack:
                    print(
                        f"ERROR: Extra closing brace '}}' at Line {line_num}, Column {i + 1}"
                    )
                    print(f"Context: {line.strip()}")
                    return
                stack.pop()

            i += 1

    if stack:
        last_brace = stack[-1]
        print(
            f"ERROR: Unclosed opening brace '{{' at Line {last_brace[0]}, Column {last_brace[1]}"
        )


def check_js_braces(filename):
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()

    stack = []
    in_block_comment = False

    # Simple state machine for parsing
    # We process character by character to handle strings and comments correctly

    for line_idx, line in enumerate(lines):
        line_num = line_idx + 1
        i = 0
        length = len(line)
        in_string = False
        string_char = ""

        while i < length:
            char = line[i]

            # Handle block comments spanning multiple lines
            if in_block_comment:
                if i + 1 < length and char == "*" and line[i + 1] == "/":
                    in_block_comment = False
                    i += 2
                    continue
                i += 1
                continue

            # Handle line comments
            if not in_string and i + 1 < length and char == "/" and line[i + 1] == "/":
                break  # Skip rest of line

            # Handle block comment start
            if not in_string and i + 1 < length and char == "/" and line[i + 1] == "*":
                in_block_comment = True
                i += 2
                continue

            # Handle strings
            if in_string:
                if char == "\\":  # Escape
                    i += 2
                    continue
                if char == string_char:
                    in_string = False
                i += 1
                continue

            # Start string
            if char in ['"', "'", "`"]:
                in_string = True
                string_char = char
                i += 1
                continue

            # Check braces
            if char == "{":
                stack.append((line_num, i + 1))
            elif char == "}":
                if not stack:
                    print(
                        f"ERROR: Extra closing brace '}}' at Line {line_num}, Column {i + 1}"
                    )
                    print(f"Context: {line.strip()}")
                    return
                stack.pop()

            i += 1

    if stack:
        print(f"ERROR: {len(stack)} unclosed opening braces:")
        for line_num, col in stack:
            print(f"  Line {line_num}, Column {col}: {lines[line_num - 1].strip()}")
    else:
        print("SUCCESS: Braces are balanced.")


if __name__ == "__main__":
    import sys

    filename = sys.argv[1] if len(sys.argv) > 1 else "api_server/web_ui/js/app.js"
    check_js_braces(filename)
