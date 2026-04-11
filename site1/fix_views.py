import sys

with open('home/views.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_post_handler = '''    # Handle status update via POST (staff/admin changes a room's status)
    if request.method == 'POST':
        room_id = request.POST.get('room_id')
        new_reservation_status = request.POST.get('reservation_status')
        new_housekeeping_status = request.POST.get('housekeeping_status')
        
        valid_res_statuses = ['vacant', 'occupied', 'reserved']
        valid_hk_statuses = ['clean', 'dirty', 'cleaning_in_progress', 'out_of_order']
        
        if room_id:
            try:
                room = Room.objects.get(room_id=room_id)
                updated = False
                if new_reservation_status in valid_res_statuses:
                    room.reservation_status = new_reservation_status
                    updated = True
                if new_housekeeping_status in valid_hk_statuses:
                    room.housekeeping_status = new_housekeeping_status
                    updated = True
                
                if updated:
                    room.save()
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return JsonResponse({'status': 'ok'})
                    messages.success(request, f'Room {room.room_code} updated to {room.get_reservation_status_display()} / {room.get_housekeeping_status_display()}.')
            except Room.DoesNotExist:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': 'Room not found.'}, status=404)
                messages.error(request, 'Room not found.')
        return redirect('room_dashboard')'''

new_post_handler = '''    # Handle status update via POST (staff/admin changes a room's status)
    if request.method == 'POST':
        room_id = request.POST.get('room_id')
        new_status = request.POST.get('new_status') # backwards-compatibility
        
        if room_id and new_status:
            try:
                room = Room.objects.get(room_id=room_id)
                if new_status == 'vacant':
                    room.reservation_status = 'vacant'
                    room.housekeeping_status = 'clean'
                elif new_status == 'empty_dirty': # keeping old mappings
                    room.reservation_status = 'vacant'
                    room.housekeeping_status = 'dirty'
                elif new_status == 'occupied':
                    room.reservation_status = 'occupied'
                elif new_status == 'reserved':
                    room.reservation_status = 'reserved'
                elif new_status == 'out_of_order':
                    room.housekeeping_status = 'out_of_order'
                room.save()
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'ok'})
                messages.success(request, f'Room {room.room_code} updated status.')
            except Room.DoesNotExist:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': 'Room not found.'}, status=404)
                messages.error(request, 'Room not found.')
        return redirect('room_dashboard')'''

if old_post_handler in text:
    text = text.replace(old_post_handler, new_post_handler)
    with open('home/views.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Updated views.py successfully")
else:
    print("Could not find old_post_handler block")
