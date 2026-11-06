import random
import time

def read_simulated_sensors():
    """Simulates receiving MQTT telemetry from an ESP32 node."""
    # Generating random data to simulate real-world sensor fluctuations
    return {
        "temperature_c": random.uniform(35.0, 60.0),          # Normal < 50.0
        "gas_leak_detected": random.choice([False, False, False, True]), # 25% chance of hazard for testing
        "vibration_g": random.uniform(0.5, 3.0)               # Normal < 2.5
    }

def evaluate_safety(sensor_data):
    """Simulates the Safety Agent and Predictive Agent logic."""
    print("\n--- SAFETY CHECK ---")
    print(f"Current Readings: Temp: {sensor_data['temperature_c']:.1f}°C | "
          f"Vibration: {sensor_data['vibration_g']:.2f}g | "
          f"Gas Leak: {sensor_data['gas_leak_detected']}")
    
    is_safe = True

    if sensor_data["gas_leak_detected"]:
        print("❌ CRITICAL SAFETY HAZARD: Gas leak detected! Immediate halt.")
        is_safe = False
        
    if sensor_data["temperature_c"] > 50.0:
        print("❌ PREDICTIVE WARNING: Equipment overheating. Potential failure risk.")
        is_safe = False
        
    if sensor_data["vibration_g"] > 2.5:
        print("❌ PREDICTIVE WARNING: Abnormal vibration detected. Check motors.")
        is_safe = False
        
    if is_safe:
        print("✅ All safety and equipment conditions are nominal.")
        
    return is_safe

if __name__ == "__main__":
    # Run 3 test cycles to see different random sensor states
    for i in range(1, 4):
        print(f"\n[Test Cycle {i}]")
        current_sensors = read_simulated_sensors()
        evaluate_safety(current_sensors)
        time.sleep(1) # Pause briefly between checks