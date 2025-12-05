from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

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
    
    # ✅ Track active session for Admin role (single-device login restriction)
    active_session_id = db.Column(db.String(255), nullable=True, unique=True)

    admin_sessions = db.relationship("AdminSession", backref="user", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"


class AdminSession(db.Model):
    """Track active admin sessions to enforce single-device login for Admin role."""
    __tablename__ = "admin_sessions"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    session_id = db.Column(db.String(255), nullable=False, unique=True, index=True)
    ip_address = db.Column(db.String(45), nullable=True)  # Support IPv4 and IPv6
    user_agent = db.Column(db.Text, nullable=True)
    login_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<AdminSession user_id={self.user_id} session_id={self.session_id[:8]}... active={self.is_active}>"
