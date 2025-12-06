def dump_depths(filename):
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()

    depth = 0
    in_block_comment = False

    for line_idx, line in enumerate(lines):
        line_num = line_idx + 1

        # Calculate indent
        indent = 0
        for char in line:
            if char == " ":
                indent += 1
            elif char == "\t":
                indent += 4
            else:
                break

        # Calculate depth change
        i = 0
        length = len(line)
        in_string = False
        string_char = ""

        original_depth = depth

        line_change = 0

        while i < length:
            char = line[i]
            if in_block_comment:
                if i + 1 < length and char == "*" and line[i + 1] == "/":
                    in_block_comment = False
                    i += 2
                    continue
                i += 1
                continue
            if not in_string and i + 1 < length and char == "/" and line[i + 1] == "/":
                break
            if not in_string and i + 1 < length and char == "/" and line[i + 1] == "*":
                in_block_comment = True
                i += 2
                continue
            if in_string:
                if char == "\\":
                    i += 2
                    continue
                if char == string_char:
                    in_string = False
                i += 1
                continue
            if char in ['"', "'", "`"]:
                in_string = True
                string_char = char
                i += 1
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            i += 1

        stripped = line.strip()
        if stripped:
            # Expected depth usually correlates with indent (2 spaces per level)
            # App class (level 0 indent) starts at depth 0, ends at depth 1 (body).
            # Inside App (level 2 indent) starts at depth 1.
            # So Expected Indent ~= (Depth - 1) * 2? Or Depth * 2?
            # If line starts with '}', effective depth for indent is depth (before decrement) or after?
            # Usually indent matches the LOWER of start/end depth if closing, or start if opening.

            # Simple check: Print if mismatch seems large
            # Or just print everything
            pass

        # Print transitions that look weird
        # Ignore comments
        if (
            not stripped.startswith("//")
            and not stripped.startswith("*")
            and not stripped.startswith("/*")
        ):
            expected_indent = (original_depth) * 2
            # Adjust expectation: if line starts with }, expected indent is (depth-1)*2
            if stripped.startswith("}"):
                expected_indent = (original_depth - 1) * 2

            # Special case for App class (indent 0, depth 0)
            if "class " in stripped:
                expected_indent = 0

            diff = abs(indent - expected_indent)
            if diff > 4 and line_num > 180:  # Ignore top of file
                print(
                    f"Line {line_num}: Indent={indent}, Depth={original_depth}->{depth}. Content='{stripped}'"
                )


if __name__ == "__main__":
    dump_depths("api_server/web_ui/js/app.js")
