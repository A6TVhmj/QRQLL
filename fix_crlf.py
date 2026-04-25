#!/usr/bin/env python3
import os
import sys

script_path = r"D:\何旻骏\python_projects\qrqll_mobile\build.sh"

with open(script_path, 'rb') as f:
    content = f.read()

# Fix CRLF
content_fixed = content.replace(b'\r\n', b'\n').replace(b'\r', b'')

with open(script_path, 'wb') as f:
    f.write(content_fixed)

print(f"Fixed CRLF in {script_path}")

# Also fix the copied project
project_script = r"/home/A6TVhmj/qrqll_mobile/build.sh"
if os.path.exists(project_script):
    with open(project_script, 'rb') as f:
        content = f.read().replace(b'\r\n', b'\n').replace(b'\r', b'')
    with open(project_script, 'wb') as f:
        f.write(content)
    print(f"Fixed CRLF in {project_script}")