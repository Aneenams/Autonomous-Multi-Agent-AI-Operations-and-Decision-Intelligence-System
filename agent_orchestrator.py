from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool
from database_module import check_booking, check_payment

from safety_module import read_simulated_sensors, evaluate_safety # Add this



# Initialize the local LLM using CrewAI's native LLM class
local_llm = LLM(
    model="ollama/llama3.2",
    base_url="http://localhost:11434"
)

# ---------------------------------------------------------
# 1. Define AI Tools (Wrapping your Python functions)
# ---------------------------------------------------------
@tool("Verify Vehicle Booking")
def verify_booking_tool(plate_number: str) -> str:
    """Use this tool to check if a license plate has a valid booking ID."""
    booking_id = check_booking(plate_number)
    if booking_id:
        return f"Booking ID found: {booking_id}"
    return "No active booking found for this plate."

# ... (Keep the rest of your agent and task code exactly the same)

@tool("Verify Payment Status")
def verify_payment_tool(booking_id: str) -> str:
    """Use this tool to check if a booking ID has been paid for."""
    is_paid = check_payment(booking_id)
    if is_paid:
        return "Payment is confirmed."
    return "Payment is pending."


@tool("Verify Site Safety")
def verify_safety_tool() -> str:
    """Use this tool to check current temperature, gas, and vibration sensors for safety hazards."""
    current_sensors = read_simulated_sensors()
    is_safe = evaluate_safety(current_sensors)
    if is_safe:
        return "All safety and equipment conditions are nominal."
    return "SAFETY HAZARD DETECTED. Do not approve operation."

# ---------------------------------------------------------
# 2. Define the Agents
# ---------------------------------------------------------
identity_booking_agent = Agent(
    role='Identity and Booking Agent',
    goal='Verify vehicle identity, check reservations, and confirm payment status.',
    backstory='You are an AI assistant at a smart fuel station responsible for verifying incoming vehicles against the booking and payment database.',
    verbose=True,
    allow_delegation=False,
    tools=[verify_booking_tool, verify_payment_tool],
    llm=local_llm
)

master_orchestrator = Agent(
    role='Master Orchestrator',
    goal='Coordinate operations and provide a final approval or rejection summary.',
    backstory='You oversee the smart fuel station. You review the findings from other agents and make final operational decisions.',
    verbose=True,
    allow_delegation=True,
    llm=local_llm
)

# ---------------------------------------------------------
# 3. Define the Tasks
# ---------------------------------------------------------
vehicle_verification_task = Task(
    description='A vehicle with license plate "MH 12AB 3456" has arrived. Use your tools to find its booking ID and check if the payment is complete.',
    expected_output='A clear statement on whether the vehicle has a valid booking and if the payment is settled.',
    agent=identity_booking_agent
)

final_decision_task = Task(
    description='Review the verification results. If the booking is valid and paid, output "OPERATION APPROVED". Otherwise, output "OPERATION REJECTED" with the reason.',
    expected_output='Final approval status and a brief explanation.',
    agent=master_orchestrator
)

# ---------------------------------------------------------
# 4. Assemble and Run the Crew
# ---------------------------------------------------------
station_crew = Crew(
    agents=[identity_booking_agent, master_orchestrator],
    tasks=[vehicle_verification_task, final_decision_task],
    process=Process.sequential
)

if __name__ == "__main__":
    print("Starting Multi-Agent AI Workflow...")
    result = station_crew.kickoff()
    
    print("\n==============================================")
    print("FINAL AGENTIC OUTPUT:")
    print("==============================================")
    print(result)