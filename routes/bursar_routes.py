from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
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
# 4️⃣ ADD PAYMENT (fee_id included, with validation)
# -------------------------------------------------------------
@bursar_routes.route("/bursar/add-payment/<int:pupil_id>", methods=["POST"])
def add_payment(pupil_id):
    pupil = Pupil.query.get_or_404(pupil_id)

    try:
        fee_id = int(request.form.get("fee_id"))
        amount_paid = float(request.form.get("amount_paid"))
        payment_method = request.form.get("payment_method")
        year = request.form.get("year")
        term = request.form.get("term")

        # Check if fee item exists
        fee_item = ClassFeeStructure.query.get_or_404(fee_id)

        # Calculate total already paid for this fee item
        already_paid = sum(p.amount_paid for p in pupil.payments if p.fee_id == fee_id)

        # Prevent adding payment if fully paid
        if already_paid >= fee_item.amount:
            flash(f"The fee item '{fee_item.item_name}' is already fully paid.", "warning")
            return redirect(url_for("bursar_routes.view_pupil_fees_structure", pupil_id=pupil.id))

        # Prevent overpayment
        if already_paid + amount_paid > fee_item.amount:
            flash(f"Payment exceeds required amount for '{fee_item.item_name}'.", "danger")
            return redirect(url_for("bursar_routes.view_pupil_fees_structure", pupil_id=pupil.id))

        payment = Payment(
            pupil_id=pupil.id,
            fee_id=fee_id,
            amount_paid=amount_paid,
            payment_method=payment_method,
            reference=str(fee_id),
            year=int(year) if year else None,
            term=term if term else None
        )

        db.session.add(payment)
        db.session.commit()
        flash(f"Payment of UGX {amount_paid:,.0f} added successfully for {fee_item.item_name} ({term} {year}).", "success")

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


# ---------------------------------------------------------
# 8️⃣ API: ADD PAYMENT (JSON endpoint for AJAX)
# ---------------------------------------------------------
@bursar_routes.route("/bursar/api/add-payment/<int:pupil_id>", methods=["POST"])
def api_add_payment(pupil_id):
    """JSON API endpoint for adding payments via AJAX"""
    pupil = Pupil.query.get_or_404(pupil_id)

    try:
        data = request.get_json()
        fee_id = int(data.get("fee_id"))
        amount_paid = float(data.get("amount_paid"))
        payment_method = data.get("payment_method")
        year = data.get("year")
        term = data.get("term")

        # Check if fee item exists
        fee_item = ClassFeeStructure.query.get_or_404(fee_id)

        # Calculate total already paid for this fee item
        already_paid = sum(p.amount_paid for p in pupil.payments if p.fee_id == fee_id)

        # Prevent adding payment if fully paid
        if already_paid >= fee_item.amount:
            return jsonify({"success": False, "error": f"The fee item '{fee_item.item_name}' is already fully paid."}), 400

        # Prevent overpayment
        if already_paid + amount_paid > fee_item.amount:
            return jsonify({"success": False, "error": f"Payment exceeds required amount for '{fee_item.item_name}'."}), 400

        payment = Payment(
            pupil_id=pupil.id,
            fee_id=fee_id,
            amount_paid=amount_paid,
            payment_method=payment_method,
            reference=str(fee_id),
            year=int(year) if year else None,
            term=term if term else None
        )

        db.session.add(payment)
        db.session.commit()

        # Return updated totals for live refresh
        return jsonify({
            "success": True,
            "message": f"Payment of UGX {amount_paid:,.0f} added successfully",
            "payment": {
                "id": payment.id,
                "fee_name": fee_item.item_name,
                "amount_paid": amount_paid,
                "payment_method": payment_method,
                "payment_date": payment.payment_date.strftime('%Y-%m-%d'),
                "year": payment.year,
                "term": payment.term
            },
            "pupil_totals": {
                "total_paid": sum(p.amount_paid for p in pupil.payments),
                "balance": sum(f.amount for f in pupil.class_fees) - sum(p.amount_paid for p in pupil.payments)
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------
# 9️⃣ INVOICES / BILLING (View all payments for receipts)
# ---------------------------------------------------------
@bursar_routes.route("/bursar/invoices")
def invoices():
    """Display all students with payments for receipt generation"""
    # Get all pupils that have made at least one payment
    pupils_with_payments = db.session.query(Pupil).join(
        Payment, Pupil.id == Payment.pupil_id
    ).distinct().options(
        db.joinedload(Pupil.class_),
        db.joinedload(Pupil.stream),
        db.joinedload(Pupil.payments)
    ).order_by(Pupil.first_name).all()

    # Build invoice data
    invoice_data = []
    for pupil in pupils_with_payments:
        total_required = sum(f.amount for f in pupil.class_fees)
        total_paid = sum(p.amount_paid for p in pupil.payments)
        balance = total_required - total_paid

        invoice_data.append({
            "pupil_id": pupil.id,
            "first_name": pupil.first_name,
            "last_name": pupil.last_name,
            "admission_number": pupil.admission_number,
            "class_name": pupil.class_.name if pupil.class_ else "N/A",
            "stream_name": pupil.stream.name if pupil.stream else "N/A",
            "total_required": total_required,
            "total_paid": total_paid,
            "balance": balance,
            "payments": pupil.payments,
            "fees": pupil.class_fees,
        })

    return render_template("bursar/invoices.html", invoices=invoice_data)


# ---------------------------------------------------------
# 🔟 RECEIPT (Print individual student receipt)
# ---------------------------------------------------------
@bursar_routes.route("/bursar/receipt/<int:pupil_id>")
def student_receipt(pupil_id):
    """Generate printable receipt for a student"""
    from datetime import datetime
    
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
    receipt_date = datetime.now().strftime('%d/%m/%Y %H:%M')
    # Determine cashier name from current_user if available (Flask-Login), otherwise fallback
    cashier_name = 'generated by........'
    bursar_role_name = ''
    # ensure we always have a variable to pass into the template
    current_user_obj = None
    try:
        # import lazily to avoid hard dependency if the project doesn't use Flask-Login
        from flask_login import current_user as _fl_current_user
        current_user_obj = _fl_current_user
        if current_user_obj and getattr(current_user_obj, 'is_authenticated', False):
            # try common attribute names
            if hasattr(current_user_obj, 'name') and current_user_obj.name:
                cashier_name = current_user_obj.name
            elif hasattr(current_user_obj, 'full_name') and current_user_obj.full_name:
                cashier_name = current_user_obj.full_name
            elif hasattr(current_user_obj, 'first_name'):
                # combine first and last if available
                fn = getattr(current_user_obj, 'first_name', '') or ''
                ln = getattr(current_user_obj, 'last_name', '') or ''
                cashier_name = (fn + ' ' + ln).strip() or cashier_name
            # Get role name if available
            if hasattr(current_user_obj, 'role') and current_user_obj.role and hasattr(current_user_obj.role, 'role_name'):
                bursar_role_name = current_user_obj.role.role_name
    except Exception:
        # if flask_login not installed or any other error, keep placeholder and current_user_obj None
        current_user_obj = None
    
    return render_template(
        "bursar/receipt.html",
        pupil=pupil,
        pupil_fees=fees_for_class,
        paid_lookup=paid_lookup,
        payments=payments,
        total_required=total_required,
        total_paid=total_paid,
        balance=balance,
        receipt_date=receipt_date,
        cashier_name=cashier_name,
        bursar_role_name=bursar_role_name,
        current_user=current_user_obj
    )

