import re
import os

html_file = 'frontend/app.html'

with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace CoreFour with MedSync
content = content.replace('CoreFour', 'MedSync')

# Regex to find the SVG logo block
svg_pattern = re.compile(r'<svg class="([^"]*)"[^>]*>\s*<polygon points="12 2 22 22 2 22"></polygon>\s*<polyline points="2 12 22 12"></polyline>\s*<line x1="12" y1="2" x2="12" y2="22"></line>\s*</svg>', re.DOTALL)

# See how many we find before replacing
matches = svg_pattern.findall(content)
print(f"Found {len(matches)} SVG logos to replace.")

# Replace SVG with img tag
content, num_subs = svg_pattern.subn(r'<img src="logo.png" class="\1 object-contain" alt="MedSync Logo">', content)
print(f"Replaced {num_subs} SVG logos.")

with open(html_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Modifications saved.")
