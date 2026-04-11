import sys

with open('home/views.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_get_block = '''    # Group rooms by floor
    floors = {}
    status_counts = {
        'vacant': 0, 'occupied': 0, 'reserved': 0,
        'clean': 0, 'dirty': 0, 'cleaning_in_progress': 0, 'out_of_order': 0
    }
    
    for room in rooms:
        assignment = assignment_map.get(room.room_id)
        duration = None
        if assignment:
            duration = (assignment.check_out - assignment.check_in).days

        room_data = {
            'room': room,
            'assignment': assignment,
            'duration': duration,
        }
        floors.setdefault(room.floor_number, []).append(room_data)
        
        # Track both types
        status_counts[room.reservation_status] = status_counts.get(room.reservation_status, 0) + 1
        status_counts[room.housekeeping_status] = status_counts.get(room.housekeeping_status, 0) + 1'''

new_get_block = '''    # Group rooms by floor
    floors = {}
    status_counts = {
        'vacant': 0, 'occupied': 0, 'out_of_order': 0, 'reserved': 0,
    }
    for room in rooms:
        assignment = assignment_map.get(room.room_id)
        duration = None
        if assignment:
            duration = (assignment.check_out - assignment.check_in).days

        room_data = {
            'room': room,
            'assignment': assignment,
            'duration': duration,
        }
        floors.setdefault(room.floor_number, []).append(room_data)
        
        # Mapping to old format for UI rendering
        disp_status = room.reservation_status # defaults to vacant/occupied/reserved
        if room.housekeeping_status == 'out_of_order':
            disp_status = 'out_of_order'
        status_counts[disp_status] = status_counts.get(disp_status, 0) + 1'''

if old_get_block in text:
    text = text.replace(old_get_block, new_get_block)
    with open('home/views.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Updated views GET block successfully")
else:
    print("Could not find old_get_block block")

