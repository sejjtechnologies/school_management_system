from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.register_pupils import db, Pupil, Fee, Payment

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
    pupils = Pupil.query.order_by(Pupil.first_name).all()
    fees = Fee.query.order_by(Fee.name).all()

    # Calculate total fees for each pupil
    pupil_data = []
    for pupil in pupils:
        total_paid = pupil.total_paid
        total_fees = pupil.total_fees
        balance = pupil.balance
        pupil.total_paid_calculated = total_paid
        pupil.total_fees_calculated = total_fees
        pupil.balance_calculated = balance
        pupil_data.append(pupil)

    return render_template("bursar/student_fees.html", pupils=pupil_data, fees=fees)

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

    fees = Fee.query.order_by(Fee.name).all()
    return render_template("bursar/edit_payment.html", payment=payment, fees=fees)

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
