from models.user_models import db  # ✅ Use shared db

class Class(db.Model):
    __tablename__ = 'classes'
    __table_args__ = {'extend_existing': True}  # ✅ Prevents "already defined" error

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def __repr__(self):
        return f"<Class {self.name}>"
