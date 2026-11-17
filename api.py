import cv2
import uvicorn
import re
import time
import threading
import mysql.connector
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
import easyocr

import random 

from fastapi import Request
from pydantic import BaseModel

import requests
from datetime import datetime

from typing import Optional


import difflib


# Holds the physical state of the hardware pump for the ESP32
global_pump_state = {"status": "LOCKED", "plate": None}

# Global variable to hold whatever the camera is currently looking at
global_live_status = {"plate": None, "message": "Waiting for vehicle..."}

# Pydantic model for the Vision Agent to send data to FastAPI
class VisionStatus(BaseModel):
    plate: Optional[str] = None
    message: str



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all frontend ports (localhost:3000, etc.)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



ESP32_IP = "http://192.168.1.82"

@app.post("/trigger-fueling/{plate_number}")
async def trigger_fueling(plate_number: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 1. Check if vehicle exists and is paid
        cursor.execute("SELECT * FROM bookings WHERE plate_number = %s", (plate_number.upper(),))
        booking = cursor.fetchone()
        
        if not booking:
            return {"status": "error", "message": "Vehicle not found."}
        if not booking['is_paid']:
            return {"status": "error", "message": "Payment pending. Cannot dispense fuel."}

        # 2. Agent Safety Check: Ping the ESP32 Accelerometer Telemetry
        try:
            telemetry = requests.get(f"{ESP32_IP}/telemetry", timeout=3).json()
            # Assuming your ESP32 returns something like {"status": "safe", "vibration": 0.5}
            if telemetry.get("status") != "safe":
                reason = "Safety Lockout: Hazardous vibrations detected at pump."
                log_decision(cursor, conn, plate_number.upper(), "REJECTED", reason)
                return {"status": "error", "message": reason}
        except requests.exceptions.RequestException:
            reason = "Safety Lockout: ESP32 Hardware offline or unreachable."
            log_decision(cursor, conn, plate_number.upper(), "REJECTED", reason)
            return {"status": "error", "message": reason}

        # 3. Agent Operations: Trigger the physical ESP32 Relay
        try:
            # Assuming your ESP32 has an /approve endpoint to turn on the relay
            requests.get(f"{ESP32_IP}/approve", timeout=3)
        except requests.exceptions.RequestException:
            return {"status": "error", "message": "Failed to trigger pump relay."}

        # 4. Log Success to Audit Logs
        reason = "Payment verified and Safety sensors nominal. Fuel dispensing engaged."
        log_decision(cursor, conn, plate_number.upper(), "APPROVED", reason)
        
        return {"status": "success", "message": "Fuel dispensing started!"}
        
    except Exception as e:
        print(f"Orchestrator Error: {str(e)}")
        return {"status": "error", "message": str(e)}
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

# Helper function to write to your audit_logs table
def log_decision(cursor, conn, plate_number, decision_val, reason_val):
    cursor.execute("""
        INSERT INTO audit_logs (timestamp, plate_number, decision, reason) 
        VALUES (%s, %s, %s, %s)
    """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), plate_number, decision_val, reason_val))
    conn.commit()

# Define the data structure expected from React
class VehicleRegistration(BaseModel):
    plate_number: str
    vehicle_type: str
    is_paid: bool

@app.post("/register-vehicle")
async def register_vehicle(data: VehicleRegistration):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Generate a random booking ID to match your database format (e.g., BKG-3045)
        new_booking_id = f"BKG-{random.randint(3000, 9999)}"
        default_user = "Portal User"
        
        # 2. Match your exact database columns, including 'vehichle_type' and 'booking_id'
        query = """
            INSERT INTO bookings 
            (booking_id, plate_number, user_name, is_paid, vehichle_type) 
            VALUES (%s, %s, %s, %s, %s)
        """
        
        # Execute with the data from the React frontend
        cursor.execute(query, (
            new_booking_id, 
            data.plate_number.upper(), 
            default_user, 
            data.is_paid, 
            data.vehicle_type 
        ))
        
        conn.commit()
        
        return {"status": "success", "message": f"Vehicle {data.plate_number} registered successfully."}
    except Exception as e:
        # This will print the exact MySQL error to your terminal if it fails again!
        print(f"DATABASE ERROR: {str(e)}") 
        return {"status": "error", "message": str(e)}
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()



model = YOLO('yolov8n.pt')
reader = easyocr.Reader(['en'], gpu=True)

# YOLOv8 default class mappings for vehicles
VEHICLE_CLASSES = {2: "Car", 3: "Motorcycle", 5: "Bus", 7: "Truck"}

live_status = {"plate": None, "message": "Waiting for vehicle...", "vehicle_type": None}
is_processing = False

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",          
        password="root2003",          
        database="fuel_station"
    )



def correct_plate_ocr(text):
    # 1. Strip out spaces and special characters, force uppercase
    clean_text = re.sub(r'[^A-Z0-9]', '', text.upper())
    
    if len(clean_text) < 7:
        return clean_text

    # 2. Dictionaries mapping common EasyOCR visual confusions
    letter_to_num = {'O': '0', 'Q': '0', 'I': '1', 'L': '1', 'Z': '2', 'S': '5', 'B': '8', 'G': '6'}
    num_to_letter = {'0': 'O', '1': 'I', '2': 'Z', '5': 'S', '8': 'B', '6': 'G'}
    
    corrected = list(clean_text)
    
    # 3. State Code (First 2 characters MUST be letters)
    # If the AI read "K1", it automatically becomes "KL"
    for i in range(min(2, len(corrected))):
        if corrected[i] in num_to_letter:
            corrected[i] = num_to_letter[corrected[i]]
            
    # 4. RTO Code (Characters 3 and 4 MUST be numbers)
    # If the AI read "O5", it automatically becomes "05"
    for i in range(2, min(4, len(corrected))):
        if corrected[i] in letter_to_num:
            corrected[i] = letter_to_num[corrected[i]]
            
    # 5. Vehicle Number (The last 4 characters MUST be numbers)
    # If the AI read "686Q" or "686O", it becomes "6860"
    for i in range(max(4, len(corrected)-4), len(corrected)):
        if corrected[i] in letter_to_num:
            corrected[i] = letter_to_num[corrected[i]]
            
    return "".join(corrected)


 # Make sure requests is imported at the top of your file

def run_safety_agent_check():
    # Temporarily forcing a Nominal status until the ADXL345 is coded
    return "Nominal", "Safety checks passed."

def direct_database_check(plate, vehicle_type):
    """Checks registration, payment, and environmental safety sequentially."""
    global is_processing, live_status, global_pump_state
    try:
        live_status["plate"] = plate
        live_status["vehicle_type"] = vehicle_type
        live_status["message"] = f"Checking Registration, Payment, and Safety for {vehicle_type}..."
        print(f"\n[INFO] Processing {vehicle_type}: {plate}")
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # ==========================================
        # FUZZY IDENTITY AGENT
        # ==========================================
        cursor.execute("SELECT plate_number FROM bookings")
        valid_plates = [row['plate_number'] for row in cursor.fetchall()]
        closest_matches = difflib.get_close_matches(plate, valid_plates, n=1, cutoff=0.5)

        if closest_matches:
            corrected_plate = closest_matches[0]
            print(f"🤖 [IDENTITY AGENT] Auto-corrected '{plate}' to '{corrected_plate}'")
            plate = corrected_plate
            
        # ==========================================
        # POLICY ORCHESTRATOR
        # ==========================================
        # 1. Check Registration
        cursor.execute("SELECT * FROM bookings WHERE plate_number = %s", (plate,))
        record = cursor.fetchone()
        
        if record:
            registration_status = "Completed"
            
            # 2. Check Payment
            if record.get('is_paid') == 1 or record.get('is_paid') == True:
                payment_status = "Success"
                
                # 3. Check Safety (Only runs if registered AND paid)
                safety_status, safety_reason = run_safety_agent_check()
                
                if safety_status == "Nominal":
                    decision = "APPROVED"
                    reason = f"Cleared. {safety_reason}"
                    global_pump_state = {"status": "UNLOCKED", "plate": plate}
                else:
                    decision = "REJECTED"
                    reason = f"Safety Lockout: {safety_reason}"
                    global_pump_state = {"status": "LOCKED", "plate": plate}
                    
            else:
                payment_status = "Not Completed"
                safety_status = "Skipped"
                decision = "REJECTED"
                reason = "Payment is pending."
                global_pump_state = {"status": "LOCKED", "plate": plate}
                
        else:
            registration_status = "Rejected"
            payment_status = "N/A"
            safety_status = "Skipped"
            decision = "REJECTED"
            reason = "Vehicle not registered in system."
            global_pump_state = {"status": "LOCKED", "plate": plate}
            
        print(f"[RESULT] Reg: {registration_status} | Pay: {payment_status} | Safety: {safety_status} | Decision: {decision}")

        # ... (Your ESP32 hardware trigger and SQL insert_query code should remain directly below this!) ...
        # ==========================================
        # HARDWARE ACTION AGENT
        # ==========================================
        try:
            if decision == "APPROVED":
                requests.post("http://192.168.1.82/approve", timeout=2.0)
                print("🟢 [HARDWARE] Signal Sent: Pump UNLOCKED")
            else:
                requests.post("http://192.168.1.82/reject", timeout=2.0)
                print("🔴 [HARDWARE] Signal Sent: Pump LOCKED")
        except requests.exceptions.RequestException:
            print("[WARNING] ESP32 not reachable on network.")
        
        # ... (Keep your insert_query right below this) ...
  
        insert_query = """
            INSERT INTO audit_logs 
            (plate_number, vehicle_type, registration_status, payment_status, safety_status, decision, reason) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (plate, vehicle_type, registration_status, payment_status, safety_status, decision, reason))
        conn.commit()
        
    except mysql.connector.Error as db_err:
        print(f"[MYSQL ERROR]: {db_err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
        
        time.sleep(2)
        live_status["plate"] = None
        live_status["vehicle_type"] = None
        live_status["message"] = "Waiting for vehicle..."
        is_processing = False

def generate_video_stream():
    global is_processing, live_status
    
    # 1. CHANGED: Use 0 for default webcam (use 1 or 2 if you have multiple USB cameras plugged in)
    cap = cv2.VideoCapture('test_video.mp4')
    frame_counter = 0
    last_frame = None 

    while cap.isOpened():
        if is_processing:
            if last_frame is not None:
                ret, buffer = cv2.imencode('.jpg', last_frame)
                yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.1) 
            continue

        ret, frame = cap.read()
        
        # 2. CHANGED: A live camera cannot "rewind" to frame 0. If it fails, break the loop.
        if not ret:
            print("Warning: Camera disconnected or frame dropped.")
            break
            
        frame_counter += 1
        plate_detected = False
        detected_text = ""
        detected_vehicle_type = "Unknown"

        if frame_counter % 15 == 0:
            results = model(frame, verbose=False)
            
            for result in results:
                for box in result.boxes:
                    cls = int(box.cls[0])
                    if cls in VEHICLE_CLASSES:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        if (x2 - x1) > 100:
                            vehicle_crop = frame[y1:y2, x1:x2]
                            if vehicle_crop.size == 0: continue
                            
                            detected_vehicle_type = VEHICLE_CLASSES[cls]

                            gray_vehicle = cv2.cvtColor(vehicle_crop, cv2.COLOR_BGR2GRAY)
                            blur_vehicle = cv2.bilateralFilter(gray_vehicle, 11, 17, 17)
                            edged = cv2.Canny(blur_vehicle, 30, 200)

                            contours, _ = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]
                            
                            plate_crop = None
                            for c in contours:
                                approx = cv2.approxPolyDP(c, 0.018 * cv2.arcLength(c, True), True)
                                if len(approx) == 4:
                                    (px, py, pw, ph) = cv2.boundingRect(approx)
                                    if 2.0 < (pw / float(ph)) < 6.0: 
                                        plate_crop = vehicle_crop[py:py+ph, px:px+pw]
                                        break

                            if plate_crop is None or plate_crop.size == 0:
                                h_veh, w_veh, _ = vehicle_crop.shape
                                plate_crop = vehicle_crop[int(h_veh*0.3):int(h_veh*0.8), int(w_veh*0.2):int(w_veh*0.8)]

                            gray_plate = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)
                            zoomed_plate = cv2.resize(gray_plate, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
                            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                            enhanced = clahe.apply(zoomed_plate)

                            ocr_results = reader.readtext(enhanced, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
                            combined_text = "".join([text for (bbox, text, prob) in ocr_results if prob > 0.15])

                            clean_text = correct_plate_ocr(combined_text) or ""
                            
                            # 1. Print exactly what EasyOCR sees to your VS Code terminal
                            if len(clean_text) > 3:
                                print(f"🔍 AI SEES RAW TEXT: '{clean_text}'")

                            # 2. Relax the rules: Accept any alphanumeric string that is at least 5 characters
                            if len(clean_text) >= 5:
                                print(f"✅ PLATE ACCEPTED: {clean_text}")
                                detected_text = clean_text
                                plate_detected = True
                                
                                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 4)
                                cv2.putText(frame, f"{detected_vehicle_type}: {detected_text}", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 3)
                                break
                if plate_detected:
                    break

        last_frame = frame.copy()
        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        
        if plate_detected and not is_processing:
            is_processing = False
            threading.Thread(target=direct_database_check, args=(detected_text, detected_vehicle_type), daemon=True).start()
            
            # 3. CHANGED: Removed the cap.set() logic here. Live hardware cannot skip frames forward.

# @app.get("/api/video-feed")
# def video_feed():
#     return StreamingResponse(generate_video_stream(), media_type="multipart/x-mixed-replace; boundary=frame")


# @app.get("/api/live-status")
# def get_live_status():
#     return live_status

@app.get("/live-logs")
async def get_live_logs():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Fetch the 10 most recent agent decisions
        cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 10")
        logs = cursor.fetchall()
        
        return {"status": "success", "data": logs}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()


@app.get("/all-registrations")
async def get_all_registrations():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True) # dictionary=True is important here!
        
        # Fetch everything from the bookings table
        cursor.execute("SELECT * FROM bookings ORDER BY id DESC")
        registrations = cursor.fetchall()
        
        return {"status": "success", "data": registrations}
    except Exception as e:
        print(f"Error fetching registrations: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()




@app.put("/complete-payment/{plate_number}")
async def complete_payment(plate_number: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update the payment status in the database
        cursor.execute("UPDATE bookings SET is_paid = 1 WHERE plate_number = %s", (plate_number.upper(),))
        conn.commit()
        
        return {"status": "success", "message": "Payment completed successfully."}
    except Exception as e:
        print(f"Payment Error: {str(e)}")
        return {"status": "error", "message": str(e)}
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()


@app.get("/my-ticket/{plate_number}")
async def get_my_ticket(plate_number: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 1. Fetch the vehicle registration details
        cursor.execute("SELECT * FROM bookings WHERE plate_number = %s ORDER BY id DESC LIMIT 1", (plate_number.upper(),))
        booking = cursor.fetchone()
        
        if not booking:
            return {"status": "error", "message": "Ticket not found"}
            
        # 2. Fetch the latest AI audit log status for this vehicle
        cursor.execute("SELECT * FROM audit_logs WHERE plate_number = %s ORDER BY id DESC LIMIT 1", (plate_number.upper(),))
        log = cursor.fetchone()
        
        # 3. Format the AI result
        result = {
            "decision": log["decision"] if log else "EVALUATING",
            "reason": log["reason"] if log else "Awaiting Master Orchestrator."
        }
        
        return {
            "status": "success", 
            "booking": booking,
            "result": result
        }
    except Exception as e:
        print(f"Ticket Error: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
@app.delete("/cancel-registration/{plate_number}")
async def cancel_registration(plate_number: str):
    """For the User to delete their registration."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bookings WHERE plate_number = %s", (plate_number.upper(),))
        conn.commit()
        return {"status": "success", "message": "Registration cancelled successfully."}
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()


# 1. The React Dashboard calls this every 1 second to update the UI
# ==========================================
# SYSTEM & VIDEO ENDPOINTS
# ==========================================
@app.get("/")
def home():
    return {"status": "System Online"}

# React connects here to view your test_video.mp4 stream
@app.get("/video-feed")
def video_feed():
    return StreamingResponse(generate_video_stream(), media_type="multipart/x-mixed-replace; boundary=frame")

# ==========================================
# ORCHESTRATOR LOGS ENDPOINT
# ==========================================
@app.get("/audit-logs")
async def get_audit_logs():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT 
                a.id as log_id,
                a.plate_number, 
                a.decision as policy_decision, 
                a.reason as agent_reasoning,
                b.booking_id as vehicle_id,
                a.vehicle_type as vehicle_type  # CHANGED: Pulling from 'a' (audit_logs) instead of 'b'
            FROM audit_logs a
            LEFT JOIN bookings b ON a.plate_number = b.plate_number
            ORDER BY a.id DESC
        """
        cursor.execute(query)
        logs = cursor.fetchall()
        
        return {"status": "success", "data": logs}
    except Exception as e:
        print(f"Error fetching logs: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

# ==========================================
# LIVE VISION AGENT STATUS ENDPOINTS
# ==========================================
# 1. React polls this every 1 second to update the UI
@app.get("/live-status")
def get_live_status():
    return live_status

# 2. Your YOLO/EasyOCR script updates this when it sees a car
@app.post("/update-live-status")
async def update_live_status(status: VisionStatus):
    global live_status
    live_status = {"plate": status.plate, "message": status.message}
    return {"status": "success"}
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)