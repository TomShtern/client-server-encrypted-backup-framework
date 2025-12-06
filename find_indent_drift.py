def find_indent_drift(filename):
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line_idx, line in enumerate(lines):
        if line.strip().startswith("#") and line.strip().endswith(") {"):
            # Check indent
            indent = len(line) - len(line.lstrip())
            if indent > 2:
                print(
                    f"Line {line_idx + 1}: Indentation {indent} (Expected 2). Content: {line.strip()}"
                )
                # Print previous few lines to see context
                print("Context:")
                for i in range(max(0, line_idx - 5), line_idx):
                    print(f"  {i + 1}: {lines[i].rstrip()}")
                break


if __name__ == "__main__":
    find_indent_drift("api_server/web_ui/js/app.js")
