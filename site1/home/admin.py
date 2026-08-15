# Hotel, RoomPrice, HotelServices, CustomerBookingInfo and ImagesRef are
# deliberately NOT registered here.
#
# Django admin writes straight to the model. It does not run the date and
# room-type validation in ReservationService, and it does not call
# log_booking_update / log_booking_delete, so an edit made through /admin/
# leaves no audit_log row. admin.site.urls is routed at site1/urls.py, so that
# bypass is reachable, not hypothetical.
#
# These models are managed exclusively through /dashboard/. Anything that needs
# a new admin surface belongs there too.
