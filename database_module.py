# Simulated PostgreSQL Database tables for the prototype
MOCK_DATABASE = {
    "plates": {
        "MH 12AB 3456": {"booking_id": "BKG-9901", "user": "Rahul"},
        "TN09BY 9726": {"booking_id": "BKG-9902", "user": "Aneena"}
    },
    "bookings": {
        "BKG-9901": {"slot": "A1", "service": "Fuel", "status": "CONFIRMED"},
        "BKG-9902": {"slot": "B2", "service": "Charging", "status": "CONFIRMED"}
    },
    "payments": {
        "BKG-9901": {"paid": True, "amount": 1500},
        "BKG-9902": {"paid": False, "amount": 800}
    }
}

def check_booking(plate_number):
    """Simulates the Booking Agent's database lookup."""
    print(f"Checking database for plate: {plate_number}...")
    
    # 1. Clean the OCR text (remove spaces and special characters if needed)
    clean_plate = plate_number.replace(" ", "").upper()
    
    # 2. Look up the plate (using original formatting for the mock DB match)
    vehicle_record = MOCK_DATABASE["plates"].get(plate_number)
    
    if not vehicle_record:
        print("❌ No matching vehicle found in database.")
        return None
        
    booking_id = vehicle_record["booking_id"]
    booking_details = MOCK_DATABASE["bookings"].get(booking_id)
    
    print(f"✅ Booking Found! ID: {booking_id} for User: {vehicle_record['user']}")
    return booking_id

def check_payment(booking_id):
    """Simulates the Payment Agent's database lookup."""
    print(f"Checking payment status for Booking ID: {booking_id}...")
    
    payment_record = MOCK_DATABASE["payments"].get(booking_id)
    
    if not payment_record:
        print("❌ Payment record not found.")
        return False
        
    if payment_record["paid"]:
        print(f"✅ Payment Confirmed. Amount: ₹{payment_record['amount']}")
        return True
    else:
        print(f"❌ Payment Pending! Amount Due: ₹{payment_record['amount']}")
        return False

if __name__ == "__main__":
    # Test Case 1: Valid Plate, Paid
    print("--- TEST CASE 1 ---")
    plate_from_ocr = "MH 12AB 3456"
    booking = check_booking(plate_from_ocr)
    if booking:
        check_payment(booking)
        
    print("\n--- TEST CASE 2 ---")
    # Test Case 2: Valid Plate, Not Paid
    plate_from_ocr_2 = "TN09BY 9726"
    booking_2 = check_booking(plate_from_ocr_2)
    if booking_2:
        check_payment(booking_2)