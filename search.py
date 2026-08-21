import sys
lines = open('frontend/app.html', 'r', encoding='utf-8', errors='replace').readlines()
for i, l in enumerate(lines):
    if 'id="view-' in l:
        print(f'{i}: {l.strip()}')
