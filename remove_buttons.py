import sys

with open('frontend/app.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Delete lines 1309 to 1339 (0-indexed, which corresponds to lines 1310 to 1340)
del lines[1309:1340]

with open('frontend/app.html', 'w', encoding='utf-8') as f:
    f.writelines(lines)
