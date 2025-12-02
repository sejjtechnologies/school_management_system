# auto_fill_middle_email.py

import os
import random
import string
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

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
    email = Column(String, unique=True)

try:
    # Fetch all pupils ordered by id
    pupils = session.query(Pupil).order_by(Pupil.id).all()

    # Track email numbering to ensure uniqueness
    email_counter = 1

    for pupil in pupils:
        # Fill middle_name if empty, None, or string "None"
        if not pupil.middle_name or pupil.middle_name.strip().lower() == "none":
            pupil.middle_name = random.choice(string.ascii_uppercase)

        # Fill email if empty, None, or string "None"
        if not pupil.email or pupil.email.strip().lower() == "none":
            pupil.email = f"student{email_counter}@gmail.com"
            email_counter += 1

    # Commit changes
    session.commit()

    print(f"Successfully updated {len(pupils)} pupils' middle_name and email.\n")

    # Print first 10 pupils after updates
    print("First 10 pupils after updates:")
    for pupil in pupils[:10]:
        print(f"ID: {pupil.pupil_id}, Name: {pupil.first_name} {pupil.middle_name} {pupil.last_name}, Email: {pupil.email}")

except Exception as e:
    session.rollback()
    print(f"Error: {e}")

finally:
    session.close()
