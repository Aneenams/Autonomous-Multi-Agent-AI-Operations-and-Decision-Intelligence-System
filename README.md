Autonomous Multi-Agent Smart Fuel Station

An end-to-end, Edge AI-powered smart fuel station system. This project uses Computer Vision (YOLOv8 + EasyOCR) and a Multi-Agent Orchestration Engine (CrewAI/LangGraph + Local Ollama LLMs) to autonomously detect vehicles, correct messy OCR reads, verify payments, and physically unlock fuel pumps via an ESP32 Microcontroller.

🚀 Key Features

Real-Time ANPR (Automatic Number Plate Recognition): Uses YOLOv8 to detect vehicle types (Car, Truck, Bike) and tightly crop license plates, followed by EasyOCR for lightning-fast edge text extraction.

Cognitive Identity Agent (Fuzzy Matching): Intelligently auto-corrects messy real-world OCR reads (e.g., confusing an 8 for a B, or reading a car model badge) by contextually mapping it to the registered database.

Master Orchestrator Policy Engine: A deterministic AI agent that cross-references vehicle identity, payment status, and environmental safety conditions before making a final operational decision.

Hardware IoT Integration: Communicates with a local ESP32 microcontroller over Wi-Fi (/approve, /reject) to physically trigger a relay and unlock the fuel pump.

Live React Command Center: A React-based dashboard displaying live video feeds, bounding boxes, system logs, and AI agent reasoning in real-time.

🛠️ Technology Stack

AI & Vision: YOLOv8, OpenCV, EasyOCR, Ollama (Local Edge AI), CrewAI / LangGraph

Backend: Python, FastAPI, Uvicorn, Python-MySQL Connector

Frontend: React (Vite), React Router, React Bootstrap, Axios

Database: MySQL (Local / Edge deployment)

Hardware: ESP32 Microcontroller, Relay Module, ADXL345 (Vibration/Safety Telemetry)

🧠 Multi-Agent Architecture

Vision Agent: Scans the camera feed, draws bounding boxes, classifies the vehicle type, and extracts raw plate text.

Identity Agent: Takes the messy raw text, filters out noise, corrects standard OCR format errors, and uses fuzzy matching to snap the text to a known user booking.

Safety Agent (Simulated): Pings the ESP32 hardware for vibration/temperature telemetry to ensure the physical pump is safe to activate.

Master Orchestrator: Reviews the outputs of the Identity and Safety agents. If registration is valid, payment is cleared, and safety is nominal, it sends the unlock signal to the hardware.

⚙️ Installation & Setup

1. Prerequisites

Python 3.9+

Node.js 18+

MySQL Server

Ollama (For local Edge AI processing)

2. Database Setup (MySQL)

Create a database named fuel_station and execute the following SQL schema:

CREATE DATABASE fuel_station;
USE fuel_station;

-- Table for registered users and payments
CREATE TABLE bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id VARCHAR(20) UNIQUE,
    plate_number VARCHAR(20) UNIQUE,
    user_name VARCHAR(100),
    is_paid BOOLEAN DEFAULT FALSE,
    vehichle_type VARCHAR(50)
);

-- Table for AI Agent decisions and logging
CREATE TABLE audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    plate_number VARCHAR(20),
    vehicle_type VARCHAR(50),
    registration_status VARCHAR(50),
    payment_status VARCHAR(50),
    safety_status VARCHAR(50),
    decision VARCHAR(50),
    reason TEXT
);


3. Backend Setup (FastAPI & AI)

Open a terminal and navigate to your backend folder.

Create and activate a virtual environment:

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate


Install dependencies:

pip install fastapi uvicorn opencv-python ultralytics easyocr mysql-connector-python requests pydantic


Start the AI Server:

python api.py


The backend will run on http://127.0.0.1:8080

4. Frontend Setup (React Dashboard)

Open a new terminal and navigate to the fuel-dashboard folder.

Install dependencies:

npm install


Start the Vite development server:

npm run dev


The frontend will run on http://localhost:5173

5. Hardware Setup (ESP32)

The backend expects an ESP32 to be on the same local Wi-Fi network at a static IP (e.g., http://192.168.1.82).
The ESP32 should host a simple C++ Web Server with the following endpoints:

GET /approve (Turns the relay HIGH)

GET /reject (Turns the relay LOW)

GET /telemetry (Returns JSON: {"status": "safe", "vibration": 0.05})

🎮 Usage

Open the Customer Portal (/register) to register a new vehicle plate (e.g., DL2CAT4762) and simulate a payment.

Open the Command Center (/admin) on a separate monitor.

Show an image of the registered license plate to your webcam (or point the camera at moving traffic).

Watch the Dashboard as the Vision Agent detects the vehicle, the Orchestrator checks the database, and the system autonomously approves or rejects the fuel pump trigger!

🛡️ License & Acknowledgements

This project was built to demonstrate Edge AI capabilities in physical infrastructure.
Models used include YOLOv8 by Ultralytics and EasyOCR by Jaided AI.
