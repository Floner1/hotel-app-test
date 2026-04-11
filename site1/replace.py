import json
with open('templates/room_dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('current_status', 'reservation_status')
text = text.replace('empty_clean', 'vacant')
text = text.replace('empty_dirty', 'vacant')

with open('templates/room_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
