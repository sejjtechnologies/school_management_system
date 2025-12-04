"""
Salary Management Models for Staff (Teachers, Admins, Secretaries, etc.)

This module defines models for:
- RoleSalary: Default salary amount per role
- SalaryPayment: Individual payment records for staff
"""

from datetime import datetime
from decimal import Decimal
from models.user_models import db


class RoleSalary(db.Model):
    """
    Defines the default salary for each role in the school.
    Bursar can override individual user salaries, but this provides a baseline.
    """
    __tablename__ = 'role_salaries'

    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False, unique=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    # Optional min/max range for validation
    min_amount = db.Column(db.Numeric(12, 2), nullable=True)
    max_amount = db.Column(db.Numeric(12, 2), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship back to Role
    role = db.relationship('Role', backref=db.backref('salary_config', uselist=False))

    def __repr__(self):
        return f"<RoleSalary role_id={self.role_id} amount={self.amount}>"


class SalaryPayment(db.Model):
    """
    Records individual salary payment transactions.
    Bursar marks staff as paid for a given period (month or term).
    Supports partial payments, reversals, and audit trail.
    """
    __tablename__ = 'salary_payments'

    id = db.Column(db.Integer, primary_key=True)

    # Staff member being paid
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Denormalized role_id for quick queries
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=True)

    # Payment amount (can be partial if staff receives multiple payments per period)
    amount = db.Column(db.Numeric(12, 2), nullable=False)

    # Bursar who recorded the payment
    paid_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # When the payment was recorded (server timestamp)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)

    # Period tracking - choose one: monthly (month+year) OR term-based (term+year)
    # Monthly: period_month is 1-12
    period_month = db.Column(db.Integer, nullable=True)
    period_year = db.Column(db.Integer, nullable=True)

    # Term-based: term='Term 1' or 'Term 2', year=2025
    term = db.Column(db.String(20), nullable=True)
    year = db.Column(db.Integer, nullable=True)

    # Status: 'paid', 'reversed', 'pending'
    # 'paid' = marked as paid
    # 'reversed' = payment was undone (create a reversal record or mark existing as reversed)
    # 'pending' = recorded but not yet approved (optional; depends on workflow)
    status = db.Column(db.String(20), nullable=False, default='paid')

    # Optional reference number (receipt, check number, etc.)
    reference = db.Column(db.String(100), nullable=True)

    # Optional notes (e.g., advance, partial payment, reason for reversal)
    notes = db.Column(db.Text, nullable=True)

    # Payment method: 'CASH' or 'BANK'
    payment_method = db.Column(db.String(20), nullable=True, default='CASH')

    # Bank name (only used if payment_method='BANK'): 'Centenary', 'Stanbic', 'ABSA', etc.
    bank_name = db.Column(db.String(100), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='salary_payments')
    role = db.relationship('Role', foreign_keys=[role_id])
    paid_by = db.relationship('User', foreign_keys=[paid_by_user_id], backref='payments_recorded')

    def __repr__(self):
        return f"<SalaryPayment user={self.user_id} amount={self.amount} date={self.payment_date} status={self.status}>"

    @property
    def period_display(self):
        """Helper to format the period for display."""
        if self.term and self.year:
            return f"{self.term} {self.year}"
        elif self.period_month and self.period_year:
            month_name = [
                'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
            ][self.period_month - 1]
            return f"{month_name} {self.period_year}"
        return "N/A"
