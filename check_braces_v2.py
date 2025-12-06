import re


def check_braces(filename):
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()

    # Remove comments
    content = re.sub(r"//.*", "", content)
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
    # Remove strings (simple approximation)
    content = re.sub(r"'[^']*'", "''", content)
    content = re.sub(r'"[^"]*"', '""', content)
    content = re.sub(r"`[^`]*`", "``", content)

    stack = []
    lines = content.split("\n")
    for i, line in enumerate(lines):
        line_num = i + 1
        for char in line:
            if char == "{":
                stack.append(line_num)
            elif char == "}":
                if not stack:
                    print(f"Extra closing brace at line {line_num}")
                    return
                stack.pop()

    if stack:
        print(f"Unclosed opening brace at line {stack[-1]}")
    else:
        print("Braces are balanced")


check_braces("api_server/web_ui/js/app.js")
