import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base

# Load .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env file!")

# Connect to PostgreSQL
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()

# Define Pupils model (ONLY the fields we need)
class Pupils(Base):
    __tablename__ = "pupils"

    id = Column(Integer, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    class_level = Column("class", String)   # <-- FIXED HERE
    stream = Column(String)


print("Fetching P1 pupils...")

try:
    # Query pupils where class = "P1"
    p1_pupils = session.query(Pupils).filter(Pupils.class_level == "P1").all()

    stream_counts = {}

    for p in p1_pupils:
        stream = p.stream if p.stream else "No Stream"
        stream_counts[stream] = stream_counts.get(stream, 0) + 1

    print("\n=== P1 STREAM COUNTS ===")
    for stream, count in stream_counts.items():
        print(f"{stream}: {count} pupils")

    print(f"\nTOTAL P1 PUPILS: {len(p1_pupils)}")

except Exception as e:
    print("\nError:", e)

finally:
    session.close()
