import os
import shutil

# Map emojis to Phosphor Icons
emoji_map = {
    '🔄': '<i class="ph ph-arrows-clockwise"></i>',
    '🔍': '<i class="ph ph-magnifying-glass"></i>',
    '📄': '<i class="ph ph-file-text"></i>',
    '👥': '<i class="ph ph-users"></i>',
    '🗺': '<i class="ph ph-map-trifold"></i>',
    '📶': '<i class="ph ph-cell-signal-full"></i>',
    '🚨': '<i class="ph ph-warning-circle"></i>', # ph-siren exists too, warning is safe
    '📥': '<i class="ph ph-inbox"></i>',
    '📅': '<i class="ph ph-calendar-blank"></i>',
    '🩺': '<i class="ph ph-stethoscope"></i>',
    '🚀': '<i class="ph ph-rocket-launch"></i>',
    '🤝': '<i class="ph ph-handshake"></i>',
    '🚪': '<i class="ph ph-door-open"></i>',
    '📴': '<i class="ph ph-device-mobile-slash"></i>',
    '🆘': '<i class="ph ph-lifebuoy"></i>',
    '🧭': '<i class="ph ph-compass"></i>',
    '🚑': '<i class="ph ph-ambulance"></i>',
    '📍': '<i class="ph ph-map-pin"></i>',
    '🎉': '<i class="ph ph-confetti"></i>',
    '💎': '<i class="ph ph-diamond"></i>',
    '👁': '<i class="ph ph-eye"></i>',
    '🗑': '<i class="ph ph-trash"></i>',
    '📡': '<i class="ph ph-broadcast"></i>',
    '🏥': '<i class="ph ph-hospital"></i>',
    '📝': '<i class="ph ph-notepad"></i>',
    '👋': '<i class="ph ph-hand-waving"></i>',
    '📞': '<i class="ph ph-phone"></i>',
    '📸': '<i class="ph ph-camera"></i>',
    '🏠': '<i class="ph ph-house"></i>',
    '📭': '<i class="ph ph-envelope-open"></i>',
    '📦': '<i class="ph ph-package"></i>',
    '💊': '<i class="ph ph-pill"></i>'
}

html_file = 'frontend/app.html'
backup_file = 'frontend/app.html.bak'

if not os.path.exists(backup_file):
    shutil.copy(html_file, backup_file)

with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Add Phosphor script if not present
if '@phosphor-icons/web' not in content:
    head_close = '</head>'
    script_tag = '    <!-- Phosphor Icons -->\n    <script src="https://unpkg.com/@phosphor-icons/web"></script>\n</head>'
    content = content.replace(head_close, script_tag)

# Replace all emojis
for emoji, icon_html in emoji_map.items():
    content = content.replace(emoji, icon_html)

with open(html_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Replacement complete.")
