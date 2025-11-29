from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.register_pupils import db, Pupil, Fee, Payment
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
    pupil_fees = {}

    for pupil in pupils:
        pupil.total_paid_calculated = pupil.total_paid or 0
        pupil.total_fees_calculated = pupil.total_fees or 0
        calculated_balance = (pupil.total_fees or 0) - (pupil.total_paid or 0)
        if pupil.balance != calculated_balance:
            pupil.balance = calculated_balance
            db.session.commit()
        pupil.balance_calculated = pupil.balance

        # Fetch fees assigned to the pupil's class
        fees_for_class = Fee.query.filter_by(class_id=pupil.class_id).all() if pupil.class_ else []
        pupil_fees[pupil.id] = fees_for_class

        pupil_data.append({
            "id": pupil.id,
            "first_name": pupil.first_name,
            "last_name": pupil.last_name,
            "gender": pupil.gender,
            "dob": pupil.dob,
            "admission_number": pupil.admission_number,
            "class_name": pupil.class_.name if pupil.class_ else "N/A",
            "stream_name": pupil.stream.name if pupil.stream else "N/A",
            "total_paid_calculated": pupil.total_paid_calculated,
            "total_fees_calculated": pupil.total_fees_calculated,
            "balance_calculated": pupil.balance_calculated,
            "payments": pupil.payments,
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

        # Update pupil balance
        pupil.balance = (pupil.total_fees or 0) - sum([p.amount_paid for p in pupil.payments])
        db.session.commit()

        flash(f"Payment of UGX {amount_paid:,.0f} added successfully for {pupil.first_name}.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding payment: {e}", "danger")

    return redirect(url_for("bursar_routes.edit_pupil_fees", pupil_id=pupil.id))


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

            pupil.balance = (pupil.total_fees or 0) - sum([p.amount_paid for p in pupil.payments])
            db.session.commit()

            flash(f"Payment updated successfully for {pupil.first_name}.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating payment: {e}", "danger")

        return redirect(url_for("bursar_routes.edit_pupil_fees", pupil_id=pupil.id))

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

        pupil.balance = (pupil.total_fees or 0) - sum([p.amount_paid for p in pupil.payments])
        db.session.commit()

        flash(f"Payment deleted successfully for {pupil.first_name}.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting payment: {e}", "danger")

    return redirect(url_for("bursar_routes.edit_pupil_fees", pupil_id=pupil.id))


# -----------------------------
# 6️⃣ Update all payments for a single pupil
# -----------------------------
@bursar_routes.route("/bursar/update-pupil-payments/<int:pupil_id>", methods=["POST"])
def update_pupil_payments(pupil_id):
    pupil = Pupil.query.get_or_404(pupil_id)
    try:
        for payment in pupil.payments:
            amount_field = f"amount_{payment.id}"
            method_field = f"method_{payment.id}"
            if amount_field in request.form and method_field in request.form:
                payment.amount_paid = float(request.form.get(amount_field, 0))
                payment.payment_method = request.form.get(method_field, "Cash")
        db.session.commit()

        pupil.balance = (pupil.total_fees or 0) - sum([p.amount_paid for p in pupil.payments])
        db.session.commit()

        flash(f"All payments updated successfully for {pupil.first_name}.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating payments: {e}", "danger")

    return redirect(url_for("bursar_routes.edit_pupil_fees", pupil_id=pupil.id))


# -----------------------------
# 7️⃣ Edit/Add payments for a single pupil (auto-load class fees)
# -----------------------------
@bursar_routes.route("/bursar/edit-pupil-fees/<int:pupil_id>", methods=["GET", "POST"])
def edit_pupil_fees(pupil_id):
    pupil = Pupil.query.get_or_404(pupil_id)

    # Fetch class fees for this pupil's class
    class_fee = Fee.query.filter_by(class_id=pupil.class_id).first() if pupil.class_ else None

    if request.method == "POST":
        try:
            tuition = float(request.form.get("tuition_fee", 0))
            activity = float(request.form.get("activity_fee", 0))
            lab = float(request.form.get("lab_fee", 0))
            exam = float(request.form.get("exam_fee", 0))
            other = float(request.form.get("other_fee", 0))

            fees = {
                "Tuition": tuition,
                "Activity": activity,
                "Lab": lab,
                "Exam": exam,
                "Other": other
            }

            for name, amount in fees.items():
                payment = Payment.query.filter_by(pupil_id=pupil.id, fee_name=name).first()
                if payment:
                    payment.amount_paid = amount
                else:
                    payment = Payment(
                        pupil_id=pupil.id,
                        fee_name=name,
                        amount_paid=amount,
                        payment_method="Cash"
                    )
                    db.session.add(payment)

            pupil.balance = (tuition + activity + lab + exam + other) - sum([p.amount_paid for p in pupil.payments])
            db.session.commit()

            flash(f"Fees updated successfully for {pupil.first_name}.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating fees: {e}", "danger")

        return redirect(url_for("bursar_routes.edit_pupil_fees", pupil_id=pupil.id))

    return render_template(
        "bursar/edit_pupil_fees.html",
        pupil=pupil,
        class_fee=class_fee
    )
