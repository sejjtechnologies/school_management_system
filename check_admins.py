from app import app, db
from models.user_models import User

with app.app_context():
    admins = User.query.filter(User.role.has(role_name="Admin")).all()
    
    if not admins:
        print("? No Admin users found")
    else:
        print("?? All Admin users in the database:\n")
        for admin in admins:
            print(f"ID: {admin.id}, Email: {admin.email}, Role: {admin.role.role_name}")
        
        print(f"\nTotal Admin users: {len(admins)}")
