from werkzeug.security import generate_password_hash
from models.user_models import db, User, Role
from flask import Flask

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:sejjtechnologies@localhost/school_management'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

default_roles = ["teacher", "bursar", "secretary", "headteacher", "parent"]

with app.app_context():
    for role_name in default_roles:
        role = Role.query.filter_by(role_name=role_name.capitalize()).first()
        if role:
            email = f"{role_name}@gmail.com"
            password = f"{role_name}1"
            existing_user = User.query.filter_by(email=email).first()

            if not existing_user:
                user = User(
                    first_name=role_name.capitalize(),
                    last_name=role_name.capitalize(),
                    email=email,
                    password=generate_password_hash(password),
                    role_id=role.id
                )
                db.session.add(user)
                print(f"✅ Inserted {email} with password '{password}'")
            else:
                print(f"⚠️ {email} already exists")
        else:
            print(f"❌ Role '{role_name}' not found in roles table")

    db.session.commit()
    print("🎉 Default users inserted successfully.")