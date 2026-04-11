import re

def process_file(filepath, title_name):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the boundary of <style>
    style_start = content.find('<style>')
    if style_start == -1:
        # Fallback if no style tag
        style_start = content.find('</head>')
        
    style_end = content.find('</style>')
    if style_end != -1:
        css = content[style_start+7:style_end].strip()
    else:
        css = ''

    body_start_match = re.search(r'<body.*?>', content, re.IGNORECASE)
    if body_start_match:
        body_start = body_start_match.end()
        body_content = content[body_start:]
    else:
        body_start = style_end + 8
        body_content = content[body_start:]
        
    body_content = re.sub(r'</body>\s*</html>\s*$', '', body_content, flags=re.IGNORECASE).strip()
    
    # Extract any <script> at the bottom.
    # Usually we want scripts in extra_js block
    script_pattern = r'(<script\b[^>]*>.*?</script>\s*)+$'
    scripts_match = re.search(script_pattern, body_content, flags=re.DOTALL | re.IGNORECASE)
    
    scripts = ''
    if scripts_match:
        scripts = scripts_match.group(0).strip()
        body_content = body_content[:scripts_match.start()].strip()

    new_content = '{% extends "base.html" %}\n{% load static %}\n{% load humanize %}\n\n'
    new_content += f'{{% block title %}}{title_name} | {{{{ hotel.hotel_name }}}}{{% endblock %}}\n\n'
    new_content += '{% block extra_css %}\n<style>\n' + css + '\n</style>\n{% endblock %}\n\n'
    new_content += '{% block content %}\n' + body_content + '\n{% endblock %}\n\n'
    
    if scripts:
        new_content += '{% block extra_js %}\n' + scripts + '\n{% endblock %}\n'
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Processed {filepath}")

process_file('templates/admin_reservations.html', 'Reservations Dashboard')
process_file('templates/room_dashboard.html', 'Room Dashboard')
process_file('templates/manage_accounts.html', 'Manage Accounts')

