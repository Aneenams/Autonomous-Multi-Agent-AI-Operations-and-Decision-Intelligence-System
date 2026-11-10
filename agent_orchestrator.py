import mysql.connector
from crewai import Agent, Task, Crew, LLM
from crewai.tools import tool

# 1. Setup Local LLM Connection (Using CrewAI's native LLM handler)
local_llm = LLM(
    model="ollama/llama3.2",
    base_url="http://localhost:11434"
)

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",          
        password="root2003",          
        database="fuel_station"
    )

# --- TOOLS ---

@tool("Verify Booking and Payment Tool")
def verify_booking_and_payment_tool(plate_number: str) -> str:
    """Queries the database to verify if the vehicle has a valid booking and clear payment."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM bookings WHERE plate_number = %s", (plate_number,))
        record = cursor.fetchone()
        
        if not record:
            return f"NO BOOKING FOUND FOR PLATE: {plate_number}."
            
        if record['is_paid'] == 1:
            return f"BOOKING VALID (ID: {record['booking_id']}). PAYMENT STATUS: PAID AND CLEARED."
        else:
            return f"BOOKING VALID (ID: {record['booking_id']}). PAYMENT STATUS: PENDING. PAYMENT REQUIRED."
            
    except Exception as e:
        return f"DATABASE ERROR: {str(e)}"
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

@tool("Check Safety Conditions Simulator")
def check_safety_conditions(dummy_input: str = "") -> str:
    """Simulates reading telemetry from environmental safety sensors."""
    return "SAFETY STATUS: NOMINAL. TEMPERATURE: 28.5C. VIBRATION: 0.05g. NO HAZARDS DETECTED."

# --- DETERMINISTIC POLICY ENGINE ---

def deterministic_policy_engine(booking_valid: bool, payment_cleared: bool, safety_nominal: bool) -> str:
    if not booking_valid:
        return "REJECTED: NO VALID BOOKING"
    if not payment_cleared:
        return "REJECTED: PAYMENT PENDING"
    if not safety_nominal:
        return "REJECTED: SAFETY HAZARD"
    return "APPROVED"

# --- AGENTS AND CREW WORKFLOW ---

# Prevent agents from overthinking by limiting iterations
identity_booking_agent = Agent(
    role='Identity and Booking Agent',
    goal='Verify vehicle identity, check reservations, and confirm payment status.',
    backstory='You are an AI assistant at a smart fuel station responsible for verifying incoming vehicles.',
    verbose=True,
    allow_delegation=False,
    cache=False, 
    max_iter=2,
    tools=[verify_booking_and_payment_tool], 
    llm=local_llm
)

safety_agent = Agent(
    role='Safety Agent',
    goal='Check environmental conditions and flag any safety hazards.',
    backstory='You monitor site safety sensors to ensure operating conditions are secure before any action is approved.',
    verbose=True,
    allow_delegation=False,
    max_iter=3, 
    tools=[check_safety_conditions], 
    llm=local_llm
)

master_orchestrator = Agent(
    role='Master Orchestrator',
    goal='Coordinate operations and provide a final approval or rejection summary.',
    backstory='You oversee the smart fuel station. You review the findings from other agents and make final operational decisions.',
    verbose=True,
    allow_delegation=True,
    max_iter=2,
    llm=local_llm
)

def run_station_workflow(plate_number: str):
    print(f"--- INITIATING WORKFLOW FOR: {plate_number} ---")
    
    auth_task = Task(
        description=f"Use the Verification tool to check booking and payment for plate: {plate_number}",
        expected_output="A summary stating if a booking exists and the exact payment status.",
        agent=identity_booking_agent
    )
    
    safety_task = Task(
        description="Use the Safety tool to check environmental conditions.",
        expected_output="A summary of the safety sensor readings.",
        agent=safety_agent
    )
    
    decision_task = Task(
        description="Review the outputs from the Identity and Safety agents. Summarize the operation status clearly.",
        expected_output="A final summary statement explaining why the operation is approved or rejected.",
        agent=master_orchestrator
    )

    crew = Crew(
        agents=[identity_booking_agent, safety_agent, master_orchestrator],
        tasks=[auth_task, safety_task, decision_task],
        verbose=True
    )
    
    crew_result = crew.kickoff()
    
    identity_output = str(auth_task.output).upper() if auth_task.output else ""
    safety_output = str(safety_task.output).upper() if safety_task.output else ""
    reasoning_summary = str(crew_result).upper()
    
    # Robust Policy Engine Extraction
    booking_found = any(kw in identity_output for kw in ["BKG", "APPROVED", "VALID", "FOUND"])
    payment_cleared = any(kw in identity_output for kw in ["PAID", "CLEARED", "SUCCESS", "CONFIRMED"])
    safety_nominal = "NOMINAL" in safety_output or "NO HAZARDS" in safety_output
    
    final_decision = deterministic_policy_engine(
        booking_valid=booking_found, 
        payment_cleared=payment_cleared, 
        safety_nominal=safety_nominal
    )
    
    final_decision_str = "APPROVED" if final_decision == "APPROVED" else "REJECTED"
    print(f"\n[POLICY ENGINE DECISION]: {final_decision_str}")
    
    try:
        print("Attempting to save record to MySQL database...")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "INSERT INTO audit_logs (plate_number, decision, reason) VALUES (%s, %s, %s)"
        cursor.execute(query, (plate_number, final_decision_str, reasoning_summary))
        conn.commit()
        
        print(f"[SUCCESS] Record for {plate_number} saved to database!")
        
    except mysql.connector.Error as db_err:
        print(f"\n[MYSQL ERROR]: Failed to insert into database. Details: {db_err}")
    except Exception as e:
        print(f"\n[GENERAL ERROR]: Could not save log. Details: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
            print("Database connection closed safely.")