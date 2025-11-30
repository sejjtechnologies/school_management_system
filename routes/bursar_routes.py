from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.register_pupils import db, Pupil, ClassFeeStructure, Payment
from models.class_model import Class
from models.stream_model import Stream

bursar_routes = Blueprint("bursar_routes", __name__, template_folder="templates/bursar")


# -------------------------------------------------------------
# 1️⃣ Dashboard
# -------------------------------------------------------------
@bursar_routes.route("/bursar/dashboard")
def dashboard():
    return render_template("bursar/dashboard.html")


# -------------------------------------------------------------
# 2️⃣ Student Fees List
# -------------------------------------------------------------
@bursar_routes.route("/bursar/student-fees")
def student_fees():
    pupils = Pupil.query.options(
        db.joinedload(Pupil.class_),
        db.joinedload(Pupil.stream),
        db.joinedload(Pupil.payments)
    ).order_by(Pupil.first_name).all()

    pupil_data = []

    for pupil in pupils:
        fees_for_class = pupil.class_fees
        total_required = sum(f.amount for f in fees_for_class)
        total_paid = sum(p.amount_paid for p in pupil.payments)
        balance = total_required - total_paid

        pupil_data.append({
            "id": pupil.id,
            "first_name": pupil.first_name,
            "last_name": pupil.last_name,
            "admission_number": pupil.admission_number,
            "class_name": pupil.class_.name if pupil.class_ else "N/A",
            "stream_name": pupil.stream.name if pupil.stream else "N/A",
            "total_required": total_required,
            "total_paid": total_paid,
            "balance": balance,
            "payments": pupil.payments,
            "fees": fees_for_class,
        })

    return render_template("bursar/student_fees.html", pupils=pupil_data)


# -------------------------------------------------------------
# 3️⃣ ENTER PAYMENT PAGE (Single pupil payment entry)
# -------------------------------------------------------------
@bursar_routes.route("/bursar/enter-payment/<int:pupil_id>")
def enter_payment_page(pupil_id):
    pupil = Pupil.query.get_or_404(pupil_id)
    return render_template("bursar/enter_pupils_payments.html", pupil=pupil)


# -------------------------------------------------------------
# 4️⃣ ADD PAYMENT (fee_id included)
# -------------------------------------------------------------
@bursar_routes.route("/bursar/add-payment/<int:pupil_id>", methods=["POST"])
def add_payment(pupil_id):
    pupil = Pupil.query.get_or_404(pupil_id)

    try:
        fee_id = int(request.form.get("fee_id"))
        amount_paid = float(request.form.get("amount_paid"))
        payment_method = request.form.get("payment_method")

        payment = Payment(
            pupil_id=pupil.id,
            fee_id=fee_id,                   # ✔ Linked to specific fee item
            amount_paid=amount_paid,
            payment_method=payment_method,
            reference=str(fee_id)            # Optional – keeping for backwards compatibility
        )

        db.session.add(payment)
        db.session.commit()
        flash(f"Payment of UGX {amount_paid:,.0f} added successfully.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error adding payment: {e}", "danger")

    return redirect(url_for("bursar_routes.view_pupil_fees_structure", pupil_id=pupil.id))


# -------------------------------------------------------------
# 5️⃣ EDIT PAYMENT
# -------------------------------------------------------------
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


# -------------------------------------------------------------
# 6️⃣ DELETE PAYMENT
# -------------------------------------------------------------
@bursar_routes.route("/bursar/delete-payment/<int:payment_id>", methods=["POST"])
def delete_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    pupil = payment.pupil

    try:
        db.session.delete(payment)
        db.session.commit()
        flash("Payment deleted.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting payment: {e}", "danger")

    return redirect(url_for("bursar_routes.view_pupil_fees_structure", pupil_id=pupil.id))


# -------------------------------------------------------------
# 7️⃣ VIEW FEES STRUCTURE PER PUPIL
# -------------------------------------------------------------
@bursar_routes.route("/bursar/view-fees/<int:pupil_id>")
def view_pupil_fees_structure(pupil_id):
    pupil = Pupil.query.get_or_404(pupil_id)

    fees_for_class = pupil.class_fees
    payments = pupil.payments

    # Map each fee item → total paid toward that item
    paid_lookup = {
        fee.id: sum(p.amount_paid for p in payments if p.fee_id == fee.id)
        for fee in fees_for_class
    }

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
