from models.user_models import db   # ✅ Use the shared db instance
from models.register_pupils import Pupil   # ✅ Import Pupil explicitly

class Subject(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

class Exam(db.Model):
    __tablename__ = 'exams'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    term = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)

class Mark(db.Model):
    __tablename__ = 'marks'
    id = db.Column(db.Integer, primary_key=True)
    pupil_id = db.Column(db.Integer, db.ForeignKey('pupils.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)

    # ✅ Relationships
    pupil = db.relationship("Pupil", back_populates="marks")
    subject = db.relationship("Subject", backref="marks")
    exam = db.relationship("Exam", backref="marks")

class Report(db.Model):
    __tablename__ = 'reports'
    id = db.Column(db.Integer, primary_key=True)
    pupil_id = db.Column(db.Integer, db.ForeignKey('pupils.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    total_score = db.Column(db.Float, nullable=False)
    average_score = db.Column(db.Float, nullable=False)
    grade = db.Column(db.String(5), nullable=False)
    remarks = db.Column(db.String(255))

    # ✅ Relationships
    pupil = db.relationship("Pupil", back_populates="reports")
    exam = db.relationship("Exam", backref="reports")
