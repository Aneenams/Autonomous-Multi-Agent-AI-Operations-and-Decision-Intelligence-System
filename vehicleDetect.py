import cv2
from ultralytics import YOLO
import easyocr
import re
import ollama


def zoom_and_clean_plate(frame, x1, y1, x2, y2):
    # 1. CROP: Extract just the number plate from the full camera frame
    plate_crop = frame[int(y1):int(y2), int(x1):int(x2)]
    
    # 2. ZOOM: Upscale the image by 2.5x using CUBIC interpolation
    zoomed_plate = cv2.resize(plate_crop, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    
    # 3. CLEAN: Convert to grayscale and apply binary thresholding to make characters pop
    gray = cv2.cvtColor(zoomed_plate, cv2.COLOR_BGR2GRAY)
    _, binary_plate = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    return binary_plate

def correct_plate_ocr(raw_plate_text):
    # Strip out any spaces, dashes, or special characters
    clean_plate = re.sub(r'[^A-Z0-9]', '', raw_plate_text.upper())
    
    if len(clean_plate) != 10:
        return clean_plate # Return as-is if it doesn't match standard 10-char format
        
    corrected_plate = list(clean_plate)
    
    # Dictionaries for common mix-ups
    num_to_letter = {'0': 'O', '1': 'I', '2': 'Z', '5': 'S', '8': 'B'}
    letter_to_num = {'O': '0', 'Q': '0', 'D': '0', 'I': '1', 'Z': '2', 'S': '5', 'B': '8'}
    
    # Define which indexes MUST be letters, and which MUST be numbers
    letter_indexes = [0, 1, 4, 5]
    number_indexes = [2, 3, 6, 7, 8, 9]
    
    for i in range(10):
        char = corrected_plate[i]
        
        if i in letter_indexes and char in num_to_letter:
            corrected_plate[i] = num_to_letter[char]
            
        elif i in number_indexes and char in letter_to_num:
            corrected_plate[i] = letter_to_num[char]
            
    return "".join(corrected_plate)



COLOR_GREEN = (0, 255, 0)   # APPROVED (All checks passed)
COLOR_RED = (0, 0, 255)     # REJECTED (Unregistered)
COLOR_BLUE = (255, 0, 0)    # PENDING (Safe, but payment pending)

def draw_status_box(frame, x1, y1, x2, y2, plate_text, status):
    # Determine color based on backend status
    if status == "APPROVED":
        box_color = COLOR_GREEN
        label = f"{plate_text} - READY FOR FUEL"
    elif status == "PENDING_PAYMENT":
        box_color = COLOR_BLUE
        label = f"{plate_text} - PENDING PAYMENT"
    else:
        box_color = COLOR_RED
        label = f"{plate_text} - UNREGISTERED/REJECTED"

    # Draw the vehicle bounding box
    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), box_color, 3)
    
    # Draw a background rectangle for the text to make it readable
    (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
    cv2.rectangle(frame, (int(x1), int(y1) - 30), (int(x1) + w, int(y1)), box_color, -1)
    
    # Overlay the text
    cv2.putText(frame, label, (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    return frame


def detect_and_read_plate_live():
    # Load YOLO model for vehicle detection
    model = YOLO('yolov8n.pt') 
    
    # Initialize EasyOCR reader
    print("Loading OCR Model... This might take a moment.")
    reader = easyocr.Reader(['en'], gpu=False) 
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open live camera.")
        return None, "Unknown"

    print("Live feed started.")
    print("-> Press 's' to SCAN the detected vehicle for a number plate.")
    print("-> Press 'q' to QUIT.")

    detected_plate = None
    detected_vehicle_type = "Unknown"

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Detect vehicles (2=car, 3=motorcycle, 5=bus, 7=truck)
        results = model(frame, classes=[2, 3, 5, 7], verbose=False)
        annotated_frame = results[0].plot()

        cv2.imshow("Vision & Identity Module", annotated_frame)

        key = cv2.waitKey(1) & 0xFF
        
        # Quit manually
        if key == ord('q'):
            break
            
        # Scan for number plate when 's' is pressed
        elif key == ord('s'):
            print("\nScanning frame for text...")
            
            # --- VEHICLE TYPE FIX ---
            # We grab the full boxes object so we can extract the class ID (vehicle type)
            boxes = results[0].boxes 
            
            if len(boxes) == 0:
                print("No vehicles detected to scan.")
            
            # Loop through detected vehicles, grabbing both coordinates and class index
            for i, box in enumerate(boxes.xyxy.cpu().numpy()):
                x1, y1, x2, y2 = map(int, box)
                
                # Extract the YOLO class ID and map it to the string name (e.g., "Car", "Truck")
                cls_id = int(boxes.cls[i].item())
                current_vehicle_type = model.names[cls_id].capitalize()
                
                # 1. APPLY DIGITAL ZOOM & CLEANING
                processed_plate = zoom_and_clean_plate(frame, x1, y1, x2, y2)
                
                # Check if crop is valid before running OCR
                if processed_plate.size != 0:
                    # Feed the zoomed, high-contrast image to EasyOCR
                    ocr_results = reader.readtext(processed_plate)
                    
                    if not ocr_results:
                        print(f"-> {current_vehicle_type} detected, but NO TEXT found. Try moving closer.")
                    else:
                        for (bbox, text, prob) in ocr_results:
                            print(f"-> Raw EasyOCR sees: '{text}' (Confidence: {prob:.2f})")
                            
                            # Accept if confidence is greater than 30%
                            if prob > 0.3:
                                # 2. APPLY COGNITIVE IDENTITY AGENT (OLLAMA)
                                # Instead of the old positional python script, we ask the LLM to fix it!
                                detected_plate = run_identity_agent(text)
                                detected_vehicle_type = current_vehicle_type
                                break 
                
                if detected_plate:
                    break

        # If a plate was successfully detected, break the live camera loop
        if detected_plate:
            break

    # Safely close the camera window
    cap.release()
    cv2.destroyAllWindows()
    
    # Return BOTH the AI-corrected plate and the vehicle type!
    return detected_plate, detected_vehicle_type

# Testing block
if __name__ == "__main__":
    plate, v_type = detect_and_read_plate_live()
    if plate:
        print(f"\nSUCCESS: Sending Plate '{plate}' and Type '{v_type}' to the AI Orchestrator...")
