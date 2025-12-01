# reset_pupil_data.py

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Date
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import date

# Load .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Setup SQLAlchemy engine and session
engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()

# Define Pupil model for direct DB access
class Pupil(Base):
    __tablename__ = "pupils"

    id = Column(Integer, primary_key=True)
    pupil_id = Column(String, unique=True)
    first_name = Column(String)
    middle_name = Column(String)
    last_name = Column(String)
    roll_number = Column(String)
    admission_number = Column(String)
    receipt_number = Column(String)
    admission_date = Column(Date)

try:
    # Fetch all pupils ordered by id
    pupils = session.query(Pupil).order_by(Pupil.id).all()

    # Reset all required fields
    for idx, pupil in enumerate(pupils, start=1):
        pupil.roll_number = f"H25/{str(idx).zfill(3)}"
        pupil.admission_number = f"HPF{str(idx).zfill(3)}"
        pupil.pupil_id = f"ID{str(idx).zfill(3)}"
        pupil.receipt_number = f"RCT-{str(idx).zfill(3)}"
        pupil.admission_date = date(2025, 12, 1)

    # Commit changes
    session.commit()

    print(f"Successfully updated {len(pupils)} pupils.\n")

    # Print first 10 pupils details
    print("First 10 pupils after updates:")
    for pupil in pupils[:10]:
        print(f"ID: {pupil.pupil_id}, Name: {pupil.first_name} {pupil.middle_name or ''} {pupil.last_name}, "
              f"Roll: {pupil.roll_number}, Admission: {pupil.admission_number}, Receipt: {pupil.receipt_number}, "
              f"Admission Date: {pupil.admission_date}")

except Exception as e:
    session.rollback()
    print(f"Error: {e}")

finally:
    session.close()
