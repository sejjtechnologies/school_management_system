# auto_fix_emails.py

import os
import re
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Load .env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()

# Define Pupil model
class Pupil(Base):
    __tablename__ = "pupils"

    id = Column(Integer, primary_key=True)
    first_name = Column(String)
    middle_name = Column(String)
    last_name = Column(String)
    email = Column(String)


# ---------------------------
# CLEAN CHARACTERS FOR EMAILS
# ---------------------------
def clean_word(word):
    if not word:
        return ""
    return re.sub(r"[^A-Za-z0-9]", "", word).lower()


# ---------------------------
# BUILD SAFE UNIQUE EMAIL
# ---------------------------
def make_unique_email(base_email, used_emails):
    email = base_email.lower()

    if email not in used_emails:
        return email

    # Add numeric suffix if needed
    counter = 2
    name, domain = email.split("@")
    while f"{name}{counter}@{domain}" in used_emails:
        counter += 1

    return f"{name}{counter}@{domain}"


try:
    pupils = session.query(Pupil).order_by(Pupil.id).all()

    # Count occurrences of first names
    firstname_map = {}
    for p in pupils:
        fn = (p.first_name or "").lower()
        firstname_map[fn] = firstname_map.get(fn, 0) + 1

    used_emails = set()
    log_lines = []

    for p in pupils:
        fn = clean_word(p.first_name)
        ln = clean_word(p.last_name)
        mn = clean_word(p.middle_name)

        # Email generation logic
        if firstname_map[p.first_name.lower()] == 1:
            base_email = f"{fn}@gmail.com"
        else:
            if ln:
                base_email = f"{fn}{ln}@gmail.com"
            elif mn:
                base_email = f"{fn}{mn}@gmail.com"
            else:
                base_email = f"{fn}@gmail.com"

        # Ensure uniqueness
        final_email = make_unique_email(base_email, used_emails)
        used_emails.add(final_email)

        # Log old & new
        log_lines.append(
            f"{p.id}: {p.first_name} {p.middle_name or ''} {p.last_name} "
            f"OLD EMAIL: {p.email} -> NEW EMAIL: {final_email}"
        )

        # Update DB
        p.email = final_email

    # Save changes
    session.commit()

    # Write log file
    with open("email_fix_log.txt", "w") as f:
        f.write("\n".join(log_lines))

    print("Emails successfully updated.")
    print("Log saved to email_fix_log.txt.\n")
    print("First 10 updated pupils:")

    for p in pupils[:10]:
        print(f"ID: {p.id}, Name: {p.first_name} {p.middle_name or ''} {p.last_name}, Email: {p.email}")

except Exception as e:
    session.rollback()
    print("Error:", e)

finally:
    session.close()
