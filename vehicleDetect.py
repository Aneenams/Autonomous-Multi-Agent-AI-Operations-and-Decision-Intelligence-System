import cv2
from ultralytics import YOLO
import easyocr

def detect_and_read_plate_live():
    # Load YOLO model for vehicle detection
    model = YOLO('yolov8n.pt') 
    
    # Initialize EasyOCR reader (loads into memory once)
    print("Loading OCR Model... This might take a moment.")
    reader = easyocr.Reader(['en'], gpu=False) 
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open live camera.")
        return

    print("Live feed started.")
    print("-> Press 's' to SCAN the detected vehicle for a number plate.")
    print("-> Press 'q' to QUIT.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Detect vehicles
        results = model(frame, classes=[2, 3, 5, 7], verbose=False)
        annotated_frame = results[0].plot()

        cv2.imshow("Vision & Identity Module", annotated_frame)

        key = cv2.waitKey(1) & 0xFF
        
        # Quit
        if key == ord('q'):
            break
            
        # Scan for number plate when 's' is pressed
        elif key == ord('s'):
            print("\nScanning frame for text...")
            boxes = results[0].boxes.xyxy.cpu().numpy() # Get bounding box coordinates
            
            if len(boxes) == 0:
                print("No vehicles detected to scan.")
            
            for box in boxes:
                x1, y1, x2, y2 = map(int, box)
                
                # Crop the vehicle from the original frame
                vehicle_crop = frame[y1:y2, x1:x2]
                
                # Check if crop is valid before running OCR
                if vehicle_crop.size != 0:
                    # Run OCR on the cropped vehicle image
                    ocr_results = reader.readtext(vehicle_crop)
                    
                    if not ocr_results:
                        print("No text found on this vehicle.")
                    else:
                        for (bbox, text, prob) in ocr_results:
                            # Filter out low-confidence reads
                            if prob > 0.3:
                                print(f"Detected Plate/Text: {text} (Confidence: {prob:.2f})")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    detect_and_read_plate_live()