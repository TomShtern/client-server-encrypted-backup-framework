def check_braces(filename):
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()

    stack = []
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
