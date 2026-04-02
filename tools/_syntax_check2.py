import ast, sys
try:
    with open(r"Q:\Claudework\bridge base\api_server.py", encoding="utf-8") as f:
        src = f.read()
    ast.parse(src)
    print("OK: api_server.py syntax valid")
except SyntaxError as e:
    print(f"SYNTAX ERROR: line {e.lineno} — {e.msg}")
    sys.exit(1)
