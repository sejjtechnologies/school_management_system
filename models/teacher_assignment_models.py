from models.user_models import db, User
from models.class_model import Class
from models.stream_model import Stream

class TeacherAssignment(db.Model):
    __tablename__ = "teacher_assignments"
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    stream_id = db.Column(db.Integer, db.ForeignKey("streams.id"), nullable=False)

    teacher = db.relationship("User", backref="teacher_assignments", lazy=True)
    class_ = db.relationship("Class", backref="teacher_assignments", lazy=True)
    stream = db.relationship("Stream", backref="teacher_assignments", lazy=True)

    def __repr__(self):
        return f"<TeacherAssignment Teacher={self.teacher_id} Class={self.class_id} Stream={self.stream_id}>"