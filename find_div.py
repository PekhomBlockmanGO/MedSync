import sys
lines = open('frontend/app.html', 'r', encoding='utf-8', errors='replace').readlines()
depth = 0
for i in range(1233, 1834):
    l = lines[i]
    depth += l.count('<div')
    depth -= l.count('</div')
    if depth == 0:
        print(f'view-emergency closes at {i}')
        break
