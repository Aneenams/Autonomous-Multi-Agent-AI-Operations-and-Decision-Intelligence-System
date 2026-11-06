import easyocr
from pydantic import BaseModel, ValidationError

class VehicleIdentity(BaseModel):
    plate_number: str
    confidence_score: float
    requires_human_review: bool
    review_image_path: str = ""

# Initialize the OCR reader once (supports English and numbers)
reader = easyocr.Reader(['en'])

import cv2

def extract_number_plate(cropped_plate_image_path: str, threshold: float = 0.80) -> VehicleIdentity:
    # 1. Read the image using OpenCV
    img = cv2.imread(cropped_plate_image_path)
    
    # 2. Convert to Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 3. Apply Gaussian Blur to remove the internal textures/noise
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # 4. Apply Binary Thresholding to make it purely black and white
    _, binary = cv2.threshold(blur, 100, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 5. Pass the preprocessed image array directly to EasyOCR instead of the file path
    results = reader.readtext(binary, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
    
    if not results:
        return VehicleIdentity(
            plate_number="UNKNOWN",
            confidence_score=0.0,
            requires_human_review=True,
            review_image_path=cropped_plate_image_path
        )
    
    best_text = ""
    best_confidence = 0.0
    
    # Loop through ALL detected text
    for (bbox, text, confidence) in results:
        clean_text = ''.join(e for e in text if e.isalnum()).upper()
        
        if len(clean_text) > len(best_text):
            best_text = clean_text
            best_confidence = confidence
    
    needs_review = best_confidence < threshold
    
    return VehicleIdentity(
        plate_number=best_text,
        confidence_score=float(best_confidence),
        requires_human_review=needs_review,
        review_image_path=cropped_plate_image_path if needs_review else ""
    )

def process_vehicle_arrival(image_path: str):
    # Extract identity
    identity = extract_number_plate(image_path)
    
    # Route based on confidence
    if identity.requires_human_review:
        print(f"Alert: Plate {identity.plate_number} read with low confidence ({identity.confidence_score}).")
        return {"status": "pending_human_review"}
    
    # Proceed to Database Verification
    print(f"Success: Proceeding to database lookup for {identity.plate_number}")
    # call verify_booking(identity.plate_number)

# --- TEST BLOCK ---
if __name__ == "__main__":
    # Ensure you have an image named 'plate.jpg' in the same folder before running this
    print("Testing extraction...")
    result = extract_number_plate('number_plate.jpe')
    print(result)