import re

files = [
    'templates/admin_reservations.html', 
    'templates/room_dashboard.html', 
    'templates/manage_accounts.html'
]

for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    head_pattern = r'<!DOCTYPE\s*HTML(?:>|\s.*?>).*?(?=<style>)'

    match = re.search(head_pattern, content, re.IGNORECASE | re.DOTALL)
    if match:
        print(f"Match found in {f}!")
    else:
        print(f"NO match in {f}.")
