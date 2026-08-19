with open('frontend/app.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, l in enumerate(lines):
    if 'id="view-subscription"' in l:
        print("".join(lines[i:i+30]))
        break
