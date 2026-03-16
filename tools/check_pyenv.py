import os, sys
print("Python:", sys.executable)
print("Version:", sys.version)
print("PYTHONHOME:", os.environ.get("PYTHONHOME", "(not set)"))
print("PYTHONPATH:", os.environ.get("PYTHONPATH", "(not set)"))
print("PATH (Python-related):")
for p in os.environ.get("PATH","").split(";"):
    if "python" in p.lower() or "Python" in p:
        print(" ", p)

print("\nPackages:")
try:
    import anthropic; print("  anthropic:", anthropic.__version__)
except: print("  anthropic: MISSING")
try:
    import google.genai; print("  google.genai: OK")
except: print("  google.genai: MISSING")
try:
    import selenium; print("  selenium:", selenium.__version__)
except: print("  selenium: MISSING")
try:
    import PIL; print("  Pillow:", PIL.__version__)
except: print("  Pillow: MISSING")
try:
    import keyring; print("  keyring: OK")
except: print("  keyring: MISSING")
try:
    import json_repair; print("  json_repair: OK")
except: print("  json_repair: MISSING")
try:
    import pyperclip; print("  pyperclip: OK")
except: print("  pyperclip: MISSING")
