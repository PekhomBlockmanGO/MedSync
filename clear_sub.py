import sys

file_path = "frontend/app.html"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

with open(file_path, "w", encoding="utf-8") as f:
    for i, line in enumerate(lines, start=1):
        if 1376 <= i <= 1474:
            continue
        f.write(line)
