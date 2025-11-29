from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.register_pupils import db, Pupil, Fee, Payment
from models.class_model import Class  # ✅ Import Class model from its module

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
    # Eager load class relationship to avoid extra queries
    pupils = Pupil.query.options(db.joinedload(Pupil.class_)).order_by(Pupil.first_name).all()

    pupil_data = []
    pupil_fees = {}  # dictionary to hold class fees per pupil

    for pupil in pupils:
        # Convenience properties for totals
        pupil.total_paid_calculated = pupil.total_paid or 0
        pupil.total_fees_calculated = pupil.total_fees or 0
        pupil.balance_calculated = pupil.balance or 0

        # fetch fees assigned to the pupil's class
        if pupil.class_:
            fees_for_class = Fee.query.filter_by(class_id=pupil.class_.id).all()
        else:
            fees_for_class = []

        pupil_fees[pupil.id] = fees_for_class
        pupil_data.append({
            "id": pupil.id,
            "first_name": pupil.first_name,
            "last_name": pupil.last_name,
            "gender": pupil.gender,
            "dob": pupil.dob,
            "admission_number": pupil.admission_number,
            "class_name": pupil.class_.name if pupil.class_ else "N/A",  # Pass class name
            "total_paid_calculated": pupil.total_paid_calculated,
            "total_fees_calculated": pupil.total_fees_calculated,
            "balance_calculated": pupil.balance_calculated,
            "payments": pupil.payments
        })

    return render_template(
        "bursar/student_fees.html",
        pupils=pupil_data,
        pupil_fees=pupil_fees
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
            fee_id=fee_id,
            amount_paid=amount_paid,
            payment_method=payment_method
        )
        db.session.add(payment)
        db.session.commit()

        flash(f"Payment of UGX {amount_paid:,.0f} added successfully for {pupil.first_name}.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding payment: {e}", "danger")

    return redirect(url_for("bursar_routes.student_fees"))


# -----------------------------
# 4️⃣ Edit Payment
# -----------------------------
@bursar_routes.route("/bursar/edit-payment/<int:payment_id>", methods=["GET", "POST"])
def edit_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    pupil = payment.pupil
    if request.method == "POST":
        try:
            payment.fee_id = int(request.form.get("fee_id"))
            payment.amount_paid = float(request.form.get("amount_paid"))
            payment.payment_method = request.form.get("payment_method", "Cash")

            db.session.commit()
            flash(f"Payment updated successfully for {pupil.first_name}.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating payment: {e}", "danger")
        return redirect(url_for("bursar_routes.student_fees"))

    # Fetch fees for pupil's class
    fees_for_class = Fee.query.filter_by(class_id=pupil.class_id).all()
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
        flash(f"Payment deleted successfully for {pupil.first_name}.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting payment: {e}", "danger")

    return redirect(url_for("bursar_routes.student_fees"))
