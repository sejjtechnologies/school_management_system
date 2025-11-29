from app import app, db
from models.user_models import User
from models.user_models import Role  # assuming Role is in the same file

EMAIL_TO_UPDATE = "sejjtechnologies@gmail.com"

with app.app_context():
    user = User.query.filter_by(email=EMAIL_TO_UPDATE).first()
    if not user:
        print("❌ User not found")
    else:
        print(f"Found user: {user.email} (Old role: {user.role})")

        # Get the Role object for Admin
        admin_role = Role.query.filter_by(role_name="Admin").first()
        if not admin_role:
            print("❌ Admin role not found in roles table")
        else:
            user.role = admin_role
            db.session.commit()
            print(f"✅ Role updated to: {user.role.role_name}")
