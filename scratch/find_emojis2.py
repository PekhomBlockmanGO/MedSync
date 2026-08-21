import re
import glob
import sys
import os

emoji_pattern = re.compile(r'[\U00010000-\U0010ffff]', flags=re.UNICODE)

with open('scratch/emojis_out2.txt', 'w', encoding='utf-8') as out:
    for root, dirs, files in os.walk('.'):
        if '.git' in root or '.gemini' in root or 'scratch' in root or '__pycache__' in root:
            continue
        for name in files:
            if name.endswith(('.html', '.py', '.js', '.json')):
                f = os.path.join(root, name)
                try:
                    with open(f, 'r', encoding='utf-8') as infile:
                        content = infile.read()
                        emojis = set(emoji_pattern.findall(content))
                        if emojis:
                            out.write(f"{f}: {emojis}\n")
                except Exception as e:
                    out.write(f"Error reading {f}: {e}\n")
