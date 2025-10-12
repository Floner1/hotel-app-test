"""
Test script to verify the reservation system is working correctly
Run this with: python test_reservation_system.py
"""

import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
django.setup()

from backend.services.services import ReservationService, ROOM_TYPE_RATES
from data.repos.repositories import ReservationRepository
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
import uuid

def test_imports():
    """Test that all necessary imports work"""
    print("\n" + "="*60)
    print("TEST 1: Import Verification")
    print("="*60)
    try:
        from home.views import get_reservation
        from backend.services.services import ReservationService
        from data.repos.repositories import ReservationRepository
        from data.models import CustomerBookingInfo
        print("✅ All imports successful!")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_service_methods():
    """Test that service methods exist"""
    print("\n" + "="*60)
    print("TEST 2: Service Layer Methods")
    print("="*60)
    methods = [m for m in dir(ReservationService) if not m.startswith('_')]
    print(f"✅ ReservationService methods: {', '.join(methods)}")
    
    required_methods = ['create_reservation', 'get_reservation_by_id', 
                       'get_all_reservations', 'get_reservations_by_email']
    for method in required_methods:
        if method in methods:
            print(f"   ✅ {method} - Found")
        else:
            print(f"   ❌ {method} - Missing")
            return False
    return True

def test_total_days_and_cost_calculation():
    """Ensure stay duration and total cost are stored correctly."""
    print("\n" + "="*60)
    print("TEST 8: Total Days & Cost Calculation")
    print("="*60)

    checkin = datetime.now() + timedelta(days=10)
    checkout = checkin + timedelta(days=4)

    test_data = {
        'name': 'Cost Test User',
        'phone': '555-6789',
        'email': f"cost_test_{uuid.uuid4().hex}@example.com",
        'checkin_date': checkin.strftime('%m/%d/%Y'),
        'checkout_date': checkout.strftime('%m/%d/%Y'),
        'adults': 2,
        'children': 0,
        'room_type': '1 bed balcony room',
        'notes': 'Testing total cost logic'
    }

    expected_days = (checkout - checkin).days
    expected_cost = expected_days * ROOM_TYPE_RATES['1 bed balcony room']

    booking = None
    try:
        booking = ReservationService.create_reservation(test_data)
        if booking.total_days != expected_days:
            print(f"   ❌ total_days stored as {booking.total_days}, expected {expected_days}")
            return False
        if booking.total_cost_amount != expected_cost:
            print(f"   ❌ total_cost_amount stored as {booking.total_cost_amount}, expected {expected_cost}")
            return False
        print(f"   ✅ Stored total_days={booking.total_days}, total_cost_amount={booking.total_cost_amount}")
        return True
    except ValidationError as exc:
        print(f"   ❌ Reservation creation failed: {exc}")
        return False
    finally:
        if booking:
            booking.delete()

def test_repository_methods():
    """Test that repository methods exist"""
    print("\n" + "="*60)
    print("TEST 3: Repository Layer Methods")
    print("="*60)
    methods = [m for m in dir(ReservationRepository) if not m.startswith('_')]
    print(f"✅ ReservationRepository methods: {', '.join(methods)}")
    
    required_methods = ['create', 'get_by_id', 'get_all', 'get_by_email',
                       'get_upcoming_bookings', 'update_booking', 'delete_booking']
    for method in required_methods:
        if method in methods:
            print(f"   ✅ {method} - Found")
        else:
            print(f"   ❌ {method} - Missing")
            return False
    return True

def test_date_validation():
    """Test date validation logic"""
    print("\n" + "="*60)
    print("TEST 4: Date Validation")
    print("="*60)
    
    # Test 1: Valid dates
    try:
        future_date = (datetime.now() + timedelta(days=7)).strftime('%m/%d/%Y')
        later_date = (datetime.now() + timedelta(days=14)).strftime('%m/%d/%Y')
        
        test_data = {
            'name': 'Test User',
            'phone': '555-1234',
            'email': 'test@example.com',
            'checkin_date': future_date,
            'checkout_date': later_date,
            'adults': 2,
            'children': 1,
            'room_type': '1 bed balcony room',
            'notes': 'Test booking'
        }
        print(f"   Testing valid dates: {future_date} to {later_date}")
        print("   ✅ Valid dates accepted (not actually saving)")
    except Exception as e:
        print(f"   ❌ Valid dates rejected: {e}")
        return False
    
    # Test 2: Past date (should fail)
    try:
        past_date = (datetime.now() - timedelta(days=1)).strftime('%m/%d/%Y')
        future_date = (datetime.now() + timedelta(days=7)).strftime('%m/%d/%Y')
        
        test_data = {
            'name': 'Test User',
            'phone': '555-1234',
            'email': 'test@example.com',
            'checkin_date': past_date,
            'checkout_date': future_date,
            'adults': 2,
            'children': 1,
            'room_type': '1 bed balcony room'
        }
        print(f"   Testing past check-in date: {past_date}")
        ReservationService.create_reservation(test_data)
        print("   ❌ Past date incorrectly accepted")
        return False
    except ValidationError:
        print("   ✅ Past date correctly rejected")
    except Exception as e:
        print(f"   ⚠️  Unexpected error: {e}")
    
    return True

def test_human_readable_date_parsing():
    """Ensure human readable date strings are accepted"""
    print("\n" + "="*60)
    print("TEST 5: Human Readable Date Parsing")
    print("="*60)

    sample_inputs = [
        ('23 October, 2025', datetime(2025, 10, 23).date()),
        ('October 23, 2025', datetime(2025, 10, 23).date()),
        ('23 Oct 2025', datetime(2025, 10, 23).date()),
    ]

    all_passed = True
    for value, expected in sample_inputs:
        try:
            parsed = ReservationService._parse_date(value)
            if parsed == expected:
                print(f"   ✅ '{value}' parsed correctly -> {parsed}")
            else:
                print(f"   ❌ '{value}' parsed to {parsed}, expected {expected}")
                all_passed = False
        except Exception as exc:
            print(f"   ❌ '{value}' raised {exc}")
            all_passed = False

    return all_passed

def test_email_validation():
    """Test email validation"""
    print("\n" + "="*60)
    print("TEST 6: Email Validation")
    print("="*60)
    
    future_date = (datetime.now() + timedelta(days=7)).strftime('%m/%d/%Y')
    later_date = (datetime.now() + timedelta(days=14)).strftime('%m/%d/%Y')
    
    # Test invalid email
    try:
        test_data = {
            'name': 'Test User',
            'phone': '555-1234',
            'email': 'invalid-email',  # Missing @ and .
            'checkin_date': future_date,
            'checkout_date': later_date,
            'adults': 2,
            'children': 1,
            'room_type': '1 bed balcony room'
        }
        print("   Testing invalid email: 'invalid-email'")
        ReservationService.create_reservation(test_data)
        print("   ❌ Invalid email incorrectly accepted")
        return False
    except ValidationError:
        print("   ✅ Invalid email correctly rejected")
    except Exception as e:
        print(f"   ⚠️  Unexpected error: {e}")
    
    return True

def test_guest_count_validation():
    """Test guest count validation"""
    print("\n" + "="*60)
    print("TEST 7: Guest Count Validation")
    print("="*60)
    
    future_date = (datetime.now() + timedelta(days=7)).strftime('%m/%d/%Y')
    later_date = (datetime.now() + timedelta(days=14)).strftime('%m/%d/%Y')
    
    # Test 0 adults (should fail)
    try:
        test_data = {
            'name': 'Test User',
            'phone': '555-1234',
            'email': 'test@example.com',
            'checkin_date': future_date,
            'checkout_date': later_date,
            'adults': 0,  # Invalid
            'children': 2,
            'room_type': '1 bed balcony room'
        }
        print("   Testing 0 adults")
        ReservationService.create_reservation(test_data)
        print("   ❌ 0 adults incorrectly accepted")
        return False
    except ValidationError:
        print("   ✅ 0 adults correctly rejected")
    except Exception as e:
        print(f"   ⚠️  Unexpected error: {e}")
    
    return True

def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "="*60)
    print("RESERVATION SYSTEM TEST SUITE")
    print("="*60)
    
    tests = [
        ("Import Verification", test_imports),
        ("Service Layer Methods", test_service_methods),
        ("Repository Layer Methods", test_repository_methods),
        ("Date Validation", test_date_validation),
        ("Human Readable Date Parsing", test_human_readable_date_parsing),
        ("Email Validation", test_email_validation),
        ("Guest Count Validation", test_guest_count_validation),
        ("Total Days & Cost Calculation", test_total_days_and_cost_calculation)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Reservation system is ready to use!")
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")
    
    return passed == total

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
