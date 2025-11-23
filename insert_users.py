import os
from werkzeug.security import generate_password_hash
from models.user_models import db, User, Role
from app import app  # import your Flask app to get db context

# Define default users to insert
default_users = [
    {"first_name": "Admin", "last_name": "User", "email": "admin@example.com", "password": "admin123", "role_id": 1},
    {"first_name": "Teacher", "last_name": "User", "email": "teacher@example.com", "password": "teacher123", "role_id": 2},
    {"first_name": "Secretary", "last_name": "User", "email": "secretary@example.com", "password": "secretary123", "role_id": 3},
    {"first_name": "Head", "last_name": "Teacher", "email": "headteacher@example.com", "password": "head123", "role_id": 4},
    {"first_name": "Parent", "last_name": "User", "email": "parent@example.com", "password": "parent123", "role_id": 5},
    {"first_name": "Bursar", "last_name": "User", "email": "bursar@example.com", "password": "bursar123", "role_id": 6},
]

with app.app_context():
    for u in default_users:
        # Check if user already exists
        existing = User.query.filter_by(email=u["email"]).first()
        if existing:
            print(f"User {u['email']} already exists, skipping.")
            continue

        hashed_pw = generate_password_hash(u["password"])
        new_user = User(
            first_name=u["first_name"],
            last_name=u["last_name"],
            email=u["email"],
            password=hashed_pw,
            role_id=u["role_id"]
        )
        db.session.add(new_user)
        print(f"Inserted {u['email']} with role_id {u['role_id']}")
    db.session.commit()
    print("✅ Seeding complete.")