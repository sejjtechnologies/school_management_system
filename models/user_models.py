from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(50), unique=True, nullable=False)

    users = db.relationship("User", backref="role", lazy=True)

    def __repr__(self):
        return f"<Role {self.role_name}>"


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.Text, nullable=False)  # hashed with werkzeug
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    
    # Optional: per-user salary override (if None, use role's default salary)
    salary_amount = db.Column(db.Numeric(12, 2), nullable=True)

    def __repr__(self):
        return f"<User {self.email}>"
