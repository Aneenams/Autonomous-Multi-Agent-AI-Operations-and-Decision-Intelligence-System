import time
# Import the functions you already built in Steps 2 and 3
from database_module import check_booking, check_payment
from safety_module import read_simulated_sensors, evaluate_safety

def process_vehicle_request(plate_number):
    """
    Executes the core business logic.
    A separate hardware controller would execute the demonstration action if approved.
    """
    print(f"\n{'='*40}")
    print(f"NEW VEHICLE DETECTED: {plate_number}")
    print(f"{'='*40}")

    # 1. Booking & Identity Check
    print("\n[Step 1] Verifying Identity & Booking...")
    booking_id = check_booking(plate_number)
    if not booking_id:
        print(">> OPERATION REJECTED: Unregistered vehicle or no active booking.")
        return False
        
    time.sleep(1) # Simulate processing time

    # 2. Payment Check
    print("\n[Step 2] Verifying Payment Status...")
    is_paid = check_payment(booking_id)
    if not is_paid:
        print(">> OPERATION REJECTED: Payment is pending. Please complete payment.")
        return False

    time.sleep(1)

    # 3. Safety & Operations Check
    print("\n[Step 3] Verifying Site Safety & Equipment...")
    current_sensors = read_simulated_sensors()
    is_safe = evaluate_safety(current_sensors)
    
    if not is_safe:
        print(">> OPERATION REJECTED: Safety hazard detected. System locked.")
        return False

    # 4. Final Approval
    print("\n[Step 4] Final Policy Decision...")
    print(">> OPERATION APPROVED: All checks passed. Triggering hardware controller.")
    return True

if __name__ == "__main__":
    # Test Case A: Valid booking, paid, hopefully safe (random chance of hazard)
    process_vehicle_request("MH 12AB 3456")
    
    time.sleep(2)
    
    # Test Case B: Valid booking, but unpaid
    process_vehicle_request("TN09BY 9726")
    
    time.sleep(2)
    
    # Test Case C: Unknown vehicle
    process_vehicle_request("KL 10 XYZ 0000")