from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.register_pupils import db, Pupil, ClassFeeStructure, Payment
from models.class_model import Class
from models.stream_model import Stream

bursar_routes = Blueprint("bursar_routes", __name__, template_folder="templates/bursar")

# -----------------------------
# 1️⃣ Dashboard
# -----------------------------
@bursar_routes.route("/bursar/dashboard")
def dashboard():
    return render_template("bursar/dashboard.html")

# -----------------------------
# 2️⃣ Student fees list
# -----------------------------
@bursar_routes.route("/bursar/student-fees")
def student_fees():
    pupils = Pupil.query.options(
        db.joinedload(Pupil.class_),
        db.joinedload(Pupil.stream)
    ).order_by(Pupil.first_name).all()

    pupil_data = []

    for pupil in pupils:
        fees_for_class = pupil.class_fees  # ClassFeeStructure items for pupil's class
        total_required = sum(f.amount for f in fees_for_class)
        total_paid = sum(p.amount_paid for p in pupil.payments)
        balance = total_required - total_paid

        pupil_data.append({
            "id": pupil.id,
            "first_name": pupil.first_name,
            "last_name": pupil.last_name,
            "gender": pupil.gender,
            "dob": pupil.dob,
            "admission_number": pupil.admission_number,
            "class_name": pupil.class_.name if pupil.class_ else "N/A",
            "stream_name": pupil.stream.name if pupil.stream else "N/A",
            "total_required": total_required,
            "total_paid": total_paid,
            "balance": balance,
            "payments": pupil.payments,
            "fees": fees_for_class,
        })

    return render_template(
        "bursar/student_fees.html",
        pupils=pupil_data
    )

# -----------------------------
# 3️⃣ Add Payment
# -----------------------------
@bursar_routes.route("/bursar/add-payment/<int:pupil_id>", methods=["POST"])
def add_payment(pupil_id):
    pupil = Pupil.query.get_or_404(pupil_id)
    try:
        fee_id = int(request.form.get("fee_id"))
        amount_paid = float(request.form.get("amount_paid"))
        payment_method = request.form.get("payment_method", "Cash")

        payment = Payment(
            pupil_id=pupil.id,
            amount_paid=amount_paid,
            payment_method=payment_method,
            reference=str(fee_id)  # store fee reference as ID
        )
        db.session.add(payment)
        db.session.commit()

        flash(f"Payment of UGX {amount_paid:,.0f} added successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding payment: {e}", "danger")

    return redirect(url_for("bursar_routes.view_pupil_fees_structure", pupil_id=pupil.id))

# -----------------------------
# 4️⃣ Edit Payment
# -----------------------------
@bursar_routes.route("/bursar/edit-payment/<int:payment_id>", methods=["GET", "POST"])
def edit_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    pupil = payment.pupil

    if request.method == "POST":
        try:
            payment.amount_paid = float(request.form.get("amount_paid"))
            payment.payment_method = request.form.get("payment_method")
            db.session.commit()
            flash("Payment updated successfully.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating payment: {e}", "danger")
        return redirect(url_for("bursar_routes.view_pupil_fees_structure", pupil_id=pupil.id))

    fees_for_class = pupil.class_fees
    return render_template("bursar/edit_payment.html", payment=payment, fees=fees_for_class)

# -----------------------------
# 5️⃣ Delete Payment
# -----------------------------
@bursar_routes.route("/bursar/delete-payment/<int:payment_id>", methods=["POST"])
def delete_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    pupil = payment.pupil

    try:
        db.session.delete(payment)
        db.session.commit()
        flash("Payment deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting payment: {e}", "danger")

    return redirect(url_for("bursar_routes.view_pupil_fees_structure", pupil_id=pupil.id))

# -----------------------------
# 6️⃣ View Full Fees Structure Per Pupil
# -----------------------------
@bursar_routes.route("/bursar/view-fees/<int:pupil_id>")
def view_pupil_fees_structure(pupil_id):
    pupil = Pupil.query.get_or_404(pupil_id)

    fees_for_class = pupil.class_fees
    payments = pupil.payments

    # Map payments to fee items by reference
    paid_lookup = {}
    for fee in fees_for_class:
        paid_lookup[fee.id] = sum(
            p.amount_paid for p in payments if p.reference == str(fee.id)
        )

    total_required = sum(f.amount for f in fees_for_class)
    total_paid = sum(paid_lookup.values())
    balance = total_required - total_paid

    return render_template(
        "bursar/edit_pupil_fees.html",
        pupil=pupil,
        pupil_fees=fees_for_class,
        paid_lookup=paid_lookup,
        total_required=total_required,
        total_paid=total_paid,
        balance=balance
    )
