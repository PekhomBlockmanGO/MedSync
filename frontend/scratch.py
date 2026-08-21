with open('frontend/app.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
depth = 0
start = -1
for i, line in enumerate(lines):
    if 'id="view-emergency"' in line:
        start = i
        depth = 0
    if start != -1:
        depth += line.count('<div') - line.count('</div')
        if depth <= 0 and i > start:
            print('view-emergency ends at line', i+1)
            break
