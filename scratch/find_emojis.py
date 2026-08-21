import re
import glob
import sys

emoji_pattern = re.compile(r'[\U00010000-\U0010ffff]', flags=re.UNICODE)

with open('scratch/emojis_out.txt', 'w', encoding='utf-8') as out:
    for f in glob.glob('frontend/*.html'):
        try:
            content = open(f, encoding='utf-8').read()
            emojis = set(emoji_pattern.findall(content))
            if emojis:
                out.write(f"{f}: {emojis}\n")
        except Exception as e:
            out.write(f"Error reading {f}: {e}\n")
