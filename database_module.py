from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# Connect to your local PostgreSQL database
# Format: postgresql://username:password@localhost:5432/database_name
DATABASE_URL = "mysql+pymysql://root:root2003@localhost:3306/fuel_station" 
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ---------------------------------------------------------
# 1. Define Database Models
# ---------------------------------------------------------
# ---------------------------------------------------------
# 1. Define Database Models
# ---------------------------------------------------------
class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(String(50), unique=True, index=True)
    plate_number = Column(String(20), unique=True, index=True)
    user_name = Column(String(100))
    is_paid = Column(Boolean, default=False)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    plate_number = Column(String(20), index=True)
    decision = Column(String(50))
    reason = Column(String(255))
    timestamp = Column(DateTime, default=datetime.utcnow)
# Generate tables in PostgreSQL automatically
Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------
# 2. Tool Functions for the AI Orchestrator
# ---------------------------------------------------------
def check_booking(plate_number: str):
    """Searches the database for a matching plate and returns the booking ID."""
    db = SessionLocal()
    # Remove spaces and convert to uppercase for standardized matching
    clean_plate = plate_number.replace(" ", "").upper()
    
    booking = db.query(Booking).filter(Booking.plate_number == clean_plate).first()
    db.close()
    
    if booking:
        return booking.booking_id
    return None

def check_payment(booking_id: str):
    """Checks if a specific booking ID has a completed payment."""
    db = SessionLocal()
    booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
    db.close()
    
    if booking:
        return booking.is_paid
    return False

def log_decision(plate_number: str, decision: str, reason: str):
    """Saves the AI's final policy decision into the Audit Log."""
    db = SessionLocal()
    new_log = AuditLog(plate_number=plate_number, decision=decision, reason=reason)
    db.add(new_log)
    db.commit()
    db.close()