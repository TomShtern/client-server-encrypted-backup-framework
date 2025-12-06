def analyze_braces(filename):
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()

    depth = 0
    in_block_comment = False

    print(f"Analyzing {filename}...")

    for line_idx, line in enumerate(lines):
        line_num = line_idx + 1
        original_depth = depth

        i = 0
        length = len(line)
        in_string = False
        string_char = ""

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
            and not stripped.startswith("while")
            and not stripped.startswith("switch")
            and not stripped.startswith("catch")
            and not stripped.startswith("try")
            and "function" not in stripped
            and "=>" not in stripped
        ):
            if original_depth != 1:
                print(
                    f"SUSPICIOUS METHOD START at Line {line_num}: Content='{stripped}' | Depth: {original_depth} -> {depth}"
                )

    print(f"Final Depth: {depth}")


if __name__ == "__main__":
    analyze_braces("api_server/web_ui/js/app.js")
