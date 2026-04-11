import os

target_files = ['templates/admin_reservations.html', 'templates/room_dashboard.html', 'templates/manage_accounts.html']

for f in target_files:
    if os.path.exists(f):
        print(f"File {f} is available for componentization.")
