from models.user_models import db
from datetime import date


class Term(db.Model):
    __tablename__ = 'terms'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # e.g., 'Term 1'
    year = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    def __repr__(self):
        return f"<Term {self.name} {self.year}: {self.start_date} -> {self.end_date}>"

    def contains(self, d: date) -> bool:
        """Return True if date d is within the term (inclusive)."""
        return self.start_date <= d <= self.end_date
