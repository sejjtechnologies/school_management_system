from datetime import datetime
from models.register_pupils import db


class ExpenseItem(db.Model):
    __tablename__ = 'expense_items'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<ExpenseItem {self.name}>"


class ExpenseRecord(db.Model):
    __tablename__ = 'expense_records'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('expense_items.id'), nullable=True)
    item = db.relationship('ExpenseItem', backref='expenses')
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=True)
    description = db.Column(db.Text, nullable=True)
    spent_by = db.Column(db.String(150), nullable=True)  # name of staff who recorded or paid
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    term = db.Column(db.String(50), nullable=True)
    year = db.Column(db.Integer, nullable=True)

    def __repr__(self):
        return f"<ExpenseRecord {self.id} {self.amount}>"
