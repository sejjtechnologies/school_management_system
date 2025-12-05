from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
import json
import os
from pathlib import Path
from datetime import datetime
from decimal import Decimal
import uuid
from models.register_pupils import db, Pupil, ClassFeeStructure, Payment
from models.class_model import Class
from models.stream_model import Stream
from models.user_models import User, Role
from models.expenses_model import ExpenseItem, ExpenseRecord
from models.salary_models import RoleSalary, SalaryPayment
from sqlalchemy import func, and_, desc

bursar_routes = Blueprint("bursar_routes", __name__, template_folder="templates/bursar")


# -------------------------------------------------------------
# 1️⃣ Dashboard
# -------------------------------------------------------------
@bursar_routes.route("/dashboard")
def dashboard():
    return render_template("bursar/dashboard.html")


# -------------------------------------------------------------
# 2️⃣ Student Fees List
# -------------------------------------------------------------
@bursar_routes.route("/student-fees")
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
@bursar_routes.route("/enter-payment/<int:pupil_id>")
def enter_payment_page(pupil_id):
    pupil = Pupil.query.get_or_404(pupil_id)
    return render_template("bursar/enter_pupils_payments.html", pupil=pupil)


# -------------------------------------------------------------
# 4️⃣ ADD PAYMENT (fee_id included, with validation)
# -------------------------------------------------------------
@bursar_routes.route("/add-payment/<int:pupil_id>", methods=["POST"])
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

        # Debug log the saved payment for easier traceability in server logs
        try:
            from flask import current_app
            current_app.logger.debug(
                "salary_payment saved: id=%s user_id=%s reference=%s paid_by_user_id=%s payment_date=%s",
                payment.id, payment.user_id, payment.reference, payment.paid_by_user_id, payment.payment_date.isoformat() if payment.payment_date else None
            )
        except Exception:
            pass
        flash(f"Payment of UGX {amount_paid:,.0f} added successfully for {fee_item.item_name} ({term} {year}).", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error adding payment: {e}", "danger")

    return redirect(url_for("bursar_routes.view_pupil_fees_structure", pupil_id=pupil.id))


# -------------------------------------------------------------
# 5️⃣ EDIT PAYMENT
# -------------------------------------------------------------
@bursar_routes.route("/edit-payment/<int:payment_id>", methods=["GET", "POST"])
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
@bursar_routes.route("/delete-payment/<int:payment_id>", methods=["POST"])
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
@bursar_routes.route("/view-fees/<int:pupil_id>")
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
@bursar_routes.route("/api/add-payment/<int:pupil_id>", methods=["POST"])
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
@bursar_routes.route("/invoices")
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
# Staff salary: mark-paid endpoint (AJAX)
# If the recorder is a Secretary, backend will auto-generate reference and notes
# ---------------------------------------------------------
@bursar_routes.route('/staff/<int:user_id>/mark-paid', methods=['POST'])
def mark_staff_paid_bursar(user_id):
    """Mark a staff member as paid for a period. Accepts JSON payload.

    Recorder (logged-in bursar) is identified via session["user_id"] (not Flask-Login).
    """
    try:
        data = request.get_json(force=True, silent=True) or request.form

        # Resolve amount - prefer provided, otherwise fallback to role default
        raw_amount = data.get('amount') if isinstance(data, dict) else data.get('amount')
        if raw_amount is None or raw_amount == '':
            # Try to determine salary from RoleSalary / User override
            user = User.query.get(user_id)
            if not user:
                return jsonify({'success': False, 'error': 'User not found'}), 404
            # Use per-user override if present
            if getattr(user, 'salary_amount', None):
                amount = Decimal(user.salary_amount)
            else:
                # Lookup role salary
                role_salary = None
                if user.role_id:
                    role_salary = RoleSalary.query.filter_by(role_id=user.role_id).first()
                amount = Decimal(role_salary.amount) if role_salary else Decimal('0.00')
        else:
            amount = Decimal(str(raw_amount))

        period_month = data.get('period_month') or None
        period_year = data.get('period_year') or None
        reference = data.get('reference') if isinstance(data, dict) else data.get('reference')
        notes = data.get('notes') if isinstance(data, dict) else data.get('notes')
        payment_method = data.get('payment_method', 'CASH') if isinstance(data, dict) else data.get('payment_method', 'CASH')
        bank_name = data.get('bank_name') if isinstance(data, dict) else data.get('bank_name')

        # Check for duplicate payment (same user, same month/year, status='paid')
        if period_month and period_year:
            existing_payment = SalaryPayment.query.filter_by(
                user_id=user_id,
                period_month=int(period_month),
                period_year=int(period_year),
                status='paid'
            ).first()
            if existing_payment:
                return jsonify({
                    'success': False,
                    'error': f'This staff member has already been marked as paid for {period_month}/{period_year}. Cannot process duplicate payment.'
                }), 400

        # Determine recorder (paid_by) — get from session (this app uses session-based auth, not Flask-Login)
        paid_by_user_id = None
        paid_by_name = None
        try:
            from flask import session
            # Check session for user_id (this app's auth method)
            session_user_id = session.get('user_id')
            if session_user_id:
                paid_by_user_id = session_user_id
                # Fetch the user record to get the name
                db_user = db.session.query(User).get(paid_by_user_id)
                if db_user:
                    paid_by_name = f"{db_user.first_name} {db_user.last_name}".strip()
                    print(f"[DEBUG] Got recorder from session: id={paid_by_user_id}, name={paid_by_name}")
                else:
                    print(f"[DEBUG] Session user_id={session_user_id} but user not found in DB")
            else:
                print(f"[DEBUG] No user_id in session")
        except Exception as e:
            print(f"[DEBUG] Exception resolving recorder from session: {e}")
            try:
                from flask import current_app
                current_app.logger.warning(f"mark_staff_paid_bursar: failed to resolve session user: {str(e)}")
            except:
                pass

        # Use already-resolved paid_by_name; fallback to session role name if needed
        recorder_name = paid_by_name or 'System'
        if not recorder_name or recorder_name == 'System':
            try:
                from flask import session
                # Could add session["role"] here if we want role-based fallback, but we have the name already
                pass
            except Exception:
                pass

        # ALWAYS generate a server-side unique reference and standardized notes
        try:
            gen_ts = datetime.utcnow()
            generated_ref = f"PAY-{gen_ts.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
            # Build notes with period information when available
            period_text = ''
            if period_month and period_year:
                period_text = f"Period: {int(period_month)}/{int(period_year)}"
            elif (period_year and data.get('term')):
                period_text = f"Term: {data.get('term')} {period_year}"
            notes_prefix = f"Recorded by {recorder_name} on {gen_ts.strftime('%Y-%m-%d %H:%M:%S')} UTC" + (f" ({period_text})" if period_text else '')
            # Combine server notes with any client-supplied notes for audit
            combined_notes = notes_prefix + (f" | user_notes: {notes}" if notes else '')

            # Overwrite reference and notes — backend authoritative
            reference = generated_ref
            notes = combined_notes
        except Exception:
            # If generation fails, fall back to whatever was provided (or None)
            pass

        # Create SalaryPayment record
        # Ensure we always have a reference (generate one if not provided)
        if not reference:
            reference = f"PAY-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"

        payment = SalaryPayment(
            user_id=user_id,
            role_id=(User.query.get(user_id).role_id if User.query.get(user_id) else None),
            amount=amount,
            paid_by_user_id=paid_by_user_id,
            payment_date=datetime.utcnow(),
            period_month=int(period_month) if period_month else None,
            period_year=int(period_year) if period_year else None,
            status='paid',
            reference=reference,
            notes=notes,
            payment_method=payment_method if payment_method in ['CASH', 'BANK'] else 'CASH',
            bank_name=bank_name if payment_method == 'BANK' else None
        )

        db.session.add(payment)
        db.session.commit()

        # Fetch the user to get their updated status
        user = User.query.get(user_id)

        # Use already-resolved paid_by_name from above (or re-fetch if needed)
        if not paid_by_name and payment.paid_by_user_id:
            try:
                pb = User.query.get(payment.paid_by_user_id)
                if pb:
                    paid_by_name = f"{pb.first_name} {pb.last_name}".strip()
            except Exception:
                pass

        # Return detailed payment info for immediate template update
        # Ensure paid_by_name is populated from the recorder_name if needed
        final_paid_by_name = paid_by_name or recorder_name
        return jsonify({
            'success': True,
            'message': f'✓ {user.first_name} {user.last_name} marked as paid',
            'payment_id': payment.id,
            'payment': {
                'id': payment.id,
                'user_id': payment.user_id,
                'amount': float(payment.amount),
                'payment_method': payment.payment_method,
                'bank_name': payment.bank_name,
                'reference': payment.reference,
                'notes': payment.notes,
                'status': payment.status,
                'period_month': payment.period_month,
                'period_year': payment.period_year,
                'payment_date': payment.payment_date.isoformat() if payment.payment_date else None,
                'paid_by_user_id': payment.paid_by_user_id,
                'paid_by_name': final_paid_by_name
            },
            'staff_update': {
                'user_id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'salary_amount': float(user.salary_amount) if user.salary_amount else 0.0,
                'is_paid': True,
                'payment_method': payment.payment_method,
                'bank_name': payment.bank_name
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------------------------------------------------------
# 🔟 RECEIPT (Print individual student receipt)
# ---------------------------------------------------------
@bursar_routes.route("/receipt/<int:pupil_id>")
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
            # Prefer the authoritative DB record for the logged-in user (ensures role relationship exists)
            try:
                # current_user should expose an id or email to lookup the full User record
                user_rec = None
                if hasattr(current_user_obj, 'id') and current_user_obj.id:
                    user_rec = db.session.query(User).filter_by(id=current_user_obj.id).first()
                elif hasattr(current_user_obj, 'email') and current_user_obj.email:
                    user_rec = db.session.query(User).filter_by(email=current_user_obj.email).first()

                if user_rec:
                    cashier_name = f"{user_rec.first_name} {user_rec.last_name}".strip()
                    if getattr(user_rec, 'role', None) and getattr(user_rec.role, 'role_name', None):
                        bursar_role_name = user_rec.role.role_name
                else:
                    # Fallback to attributes available on the current_user proxy
                    if hasattr(current_user_obj, 'name') and current_user_obj.name:
                        cashier_name = current_user_obj.name
                    elif hasattr(current_user_obj, 'full_name') and current_user_obj.full_name:
                        cashier_name = current_user_obj.full_name
                    elif hasattr(current_user_obj, 'first_name'):
                        fn = getattr(current_user_obj, 'first_name', '') or ''
                        ln = getattr(current_user_obj, 'last_name', '') or ''
                        cashier_name = (fn + ' ' + ln).strip() or cashier_name
                    if hasattr(current_user_obj, 'role') and current_user_obj.role and hasattr(current_user_obj.role, 'role_name'):
                        bursar_role_name = current_user_obj.role.role_name
            except Exception:
                # If DB lookup fails for any reason, fall back to current_user attributes
                if hasattr(current_user_obj, 'name') and current_user_obj.name:
                    cashier_name = current_user_obj.name
                elif hasattr(current_user_obj, 'full_name') and current_user_obj.full_name:
                    cashier_name = current_user_obj.full_name
                elif hasattr(current_user_obj, 'first_name'):
                    fn = getattr(current_user_obj, 'first_name', '') or ''
                    ln = getattr(current_user_obj, 'last_name', '') or ''
                    cashier_name = (fn + ' ' + ln).strip() or cashier_name
                if hasattr(current_user_obj, 'role') and current_user_obj.role and hasattr(current_user_obj.role, 'role_name'):
                    bursar_role_name = current_user_obj.role.role_name
    except Exception:
        # if flask_login not installed or any other error, keep placeholder and current_user_obj None
        current_user_obj = None
    # Log the cashier details so we can debug missing/placeholder cashier name issues
    try:
        from flask import current_app
        current_app.logger.debug(
            "student_receipt render: pupil_id=%s, cashier_name=%s, bursar_role_name=%s, current_user_present=%s",
            pupil_id, repr(cashier_name), repr(bursar_role_name), bool(current_user_obj)
        )
    except Exception:
        # Logging should never break receipt generation; ignore errors
        pass

    # Attempt to recover cashier info from the most recent saved receipt metadata for this pupil
    try:
        receipts_dir = Path(__file__).resolve().parents[1] / 'receipts'
        receipts_dir.mkdir(parents=True, exist_ok=True)

        # If cashier_name is the placeholder or empty, try to read the latest saved meta for this pupil
        if (not cashier_name) or (cashier_name.strip() == 'generated by........') or (not bursar_role_name):
            # find files matching receipt_{pupil.id}_*.json
            pattern = f"receipt_{pupil.id}_*.json"
            candidates = sorted(receipts_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
            if candidates:
                try:
                    with open(candidates[0], 'r', encoding='utf-8') as f:
                        prev = json.load(f)
                        prev_cashier = prev.get('cashier_name')
                        prev_role = prev.get('bursar_role_name')
                        if prev_cashier and prev_cashier.strip():
                            cashier_name = prev_cashier
                        if prev_role and prev_role.strip():
                            bursar_role_name = prev_role
                except Exception:
                    # ignore malformed files
                    pass

        # Now persist the (possibly updated) metadata for this render
        receipt_meta = {
            'pupil_id': pupil.id,
            'pupil_name': f"{pupil.first_name} {pupil.last_name}",
            'receipt_date': receipt_date,
            'cashier_name': cashier_name,
            'bursar_role_name': bursar_role_name,
            'total_required': total_required,
            'total_paid': total_paid,
            'balance': balance
        }
        safe_ts = receipt_date.replace('/', '-').replace(':', '-')
        meta_path = receipts_dir / f"receipt_{pupil.id}_{safe_ts}.json"
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(receipt_meta, f, ensure_ascii=False, indent=2)
    except Exception:
        # Do not let persistence errors prevent rendering the receipt
        pass
    # If still missing cashier info, try to pick a bursar from the DB as a reasonable fallback
    try:
        if (not cashier_name) or (cashier_name.strip() == 'generated by........'):
            # find any user whose role_name contains 'bursar' (case-insensitive)
            bursar_user = db.session.query(User).join(Role).filter(func.lower(Role.role_name).like('%bursar%')).first()
            if bursar_user:
                cashier_name = f"{bursar_user.first_name} {bursar_user.last_name}".strip()
                bursar_role_name = bursar_user.role.role_name if bursar_user.role and getattr(bursar_user.role, 'role_name', None) else bursar_role_name
    except Exception:
        # ignore DB errors and keep existing values
        pass

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
    )


# ---------------------------------------------------------
# Expenses / Disbursements
# ---------------------------------------------------------
from sqlalchemy.orm import joinedload


@bursar_routes.route('/expenses')
def expenses():
    """List all expenses and show totals for a selected term/year."""
    term = request.args.get('term')
    year = request.args.get('year')
    date_str = request.args.get('date')

    query = db.session.query(ExpenseRecord).options(joinedload(ExpenseRecord.item)).order_by(ExpenseRecord.payment_date.desc())
    if term:
        query = query.filter(ExpenseRecord.term == term)
    if year:
        try:
            y = int(year)
            query = query.filter(ExpenseRecord.year == y)
        except Exception:
            pass
    # optional exact date filter (YYYY-MM-DD)
    if date_str:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(date_str).date()
            query = query.filter(func.date(ExpenseRecord.payment_date) == dt)
        except Exception:
            # ignore parse errors
            pass

    records = query.all()

    # Totals: total money spent and number of expense records, and count of unique items
    total_spent = sum(float(r.amount) for r in records) if records else 0.0
    total_count = len(records)
    unique_items = len({r.item_id for r in records if r.item_id})

    items = ExpenseItem.query.order_by(ExpenseItem.name).all()
    return render_template('bursar/expenses.html', records=records, items=items, total_spent=total_spent, total_count=total_count, unique_items=unique_items, selected_term=term, selected_year=year, selected_date=date_str)


@bursar_routes.route('/expenses/add', methods=['GET', 'POST'])
def add_expense():
    items = ExpenseItem.query.order_by(ExpenseItem.name).all()
    # Support showing a success CTA after adding an expense
    added = request.args.get('added')
    added_term = request.args.get('term')
    added_year = request.args.get('year')
    added_date = request.args.get('date')

    if request.method == 'POST':
        try:
            item_id = request.form.get('item_id') or None
            if item_id:
                item_id = int(item_id)
            amount = float(request.form.get('amount') or 0)
            quantity = request.form.get('quantity')
            qty_val = int(quantity) if quantity else None
            description = request.form.get('description')
            spent_by = request.form.get('spent_by')
            term = request.form.get('term')
            year = request.form.get('year')
            year_val = int(year) if year else None
            payment_date_str = request.form.get('payment_date')
            # create record
            rec = ExpenseRecord(item_id=item_id, amount=amount, description=description, spent_by=spent_by, term=term, year=year_val)
            # set quantity if model supports it
            if qty_val is not None and hasattr(rec, 'quantity'):
                rec.quantity = qty_val
            # set payment_date if provided and the model supports it
            if payment_date_str:
                try:
                    from datetime import datetime
                    # expecting YYYY-MM-DD from input[type=date]
                    rec.payment_date = datetime.fromisoformat(payment_date_str)
                except Exception:
                    # ignore parse errors and keep default
                    pass

            db.session.add(rec)
            db.session.commit()
            flash('Expense recorded successfully.', 'success')
            # Redirect back to add form but include a CTA to view the expenses filtered by submitted term/year/date
            safe_date = payment_date_str or ''
            return redirect(url_for('bursar_routes.add_expense', added=1, term=term or '', year=year or '', date=safe_date))
        except Exception as e:
            db.session.rollback()
            flash(f'Error recording expense: {e}', 'danger')

    # Auto-fill 'recorded by' with logged-in bursar name when available
    bursar_name = ''
    try:
        from flask_login import current_user as _fl_current_user
        if _fl_current_user and getattr(_fl_current_user, 'is_authenticated', False):
            user_rec = None
            try:
                if hasattr(_fl_current_user, 'id') and _fl_current_user.id:
                    user_rec = db.session.query(User).filter_by(id=_fl_current_user.id).first()
                elif hasattr(_fl_current_user, 'email') and _fl_current_user.email:
                    user_rec = db.session.query(User).filter_by(email=_fl_current_user.email).first()
            except Exception:
                user_rec = None

            if user_rec:
                bursar_name = f"{user_rec.first_name} {user_rec.last_name}".strip()
            else:
                # fallback to attributes on current_user proxy
                bursar_name = getattr(_fl_current_user, 'name', '') or getattr(_fl_current_user, 'full_name', '') or ((getattr(_fl_current_user, 'first_name', '') or '') + ' ' + (getattr(_fl_current_user, 'last_name', '') or '')).strip()
    except Exception:
        bursar_name = ''

    # final DB fallback: any user with role containing 'bursar'
    if not bursar_name:
        try:
            buser = db.session.query(User).join(Role).filter(func.lower(Role.role_name).like('%bursar%')).first()
            if buser:
                bursar_name = f"{buser.first_name} {buser.last_name}".strip()
        except Exception:
            pass

    return render_template('bursar/add_expense.html', items=items, added=added, added_term=added_term, added_year=added_year, added_date=added_date, bursar_name=bursar_name)


# ---------------------------------------------------------
# INLINE EDIT: Update expense fields via AJAX
# ---------------------------------------------------------
@bursar_routes.route('/expense/<int:expense_id>/update', methods=['POST'])
def update_expense(expense_id):
    """Update expense fields (amount, quantity, date, term, year) via inline editing (AJAX endpoint)."""
    try:
        rec = ExpenseRecord.query.get_or_404(expense_id)
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        # Update amount if provided
        if 'amount' in data:
            new_amount = float(data.get('amount'))
            if new_amount <= 0:
                return jsonify({'success': False, 'error': 'Amount must be greater than 0'}), 400
            rec.amount = new_amount

        # Update quantity if provided
        if 'quantity' in data:
            qty = data.get('quantity')
            if qty:
                rec.quantity = int(qty)
            else:
                rec.quantity = None

        # Update date if provided
        if 'date' in data:
            date_str = data.get('date')
            if date_str:
                try:
                    from datetime import datetime
                    rec.payment_date = datetime.fromisoformat(date_str)
                except Exception as e:
                    return jsonify({'success': False, 'error': f'Invalid date format: {str(e)}'}), 400

        # Update term if provided
        if 'term' in data:
            rec.term = data.get('term') or None

        # Update year if provided
        if 'year' in data:
            year = data.get('year')
            if year:
                try:
                    rec.year = int(year)
                except Exception:
                    return jsonify({'success': False, 'error': 'Invalid year'}), 400
            else:
                rec.year = None

        db.session.commit()

        # calculate quick totals so client can refresh authoritative totals
        try:
            total_spent = float(db.session.query(func.coalesce(func.sum(ExpenseRecord.amount), 0)).scalar() or 0)
        except Exception:
            total_spent = float(sum(r.amount for r in ExpenseRecord.query.all()))
        try:
            total_count = db.session.query(func.count(ExpenseRecord.id)).scalar() or 0
        except Exception:
            total_count = len(ExpenseRecord.query.all())

        return jsonify({
            'success': True,
            'message': 'Expense updated successfully',
            'id': rec.id,
            'item_name': rec.item.name if rec.item else (rec.description[:200] if rec.description else ''),
            'spent_by': rec.spent_by,
            'data': {
                'amount': float(rec.amount),
                'quantity': rec.quantity,
                'date': rec.payment_date.strftime('%Y-%m-%d') if rec.payment_date else '',
                'term': rec.term,
                'year': rec.year
            },
            'totals': {
                'total_spent': total_spent,
                'total_count': int(total_count)
            }
        }), 200

    except ValueError as e:
        return jsonify({'success': False, 'error': f'Invalid value: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500



# ---------------------------------------------------------
# DELETE: remove an expense record (AJAX)
# ---------------------------------------------------------
@bursar_routes.route('/expense/<int:expense_id>/delete', methods=['POST'])
def delete_expense(expense_id):
    try:
        rec = ExpenseRecord.query.get_or_404(expense_id)
        db.session.delete(rec)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Expense deleted', 'id': expense_id}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# =================================================================
# STAFF SALARY MANAGEMENT
# =================================================================

# ---------------------------------------------------------
# GET: Manage Staff Salaries Page
# ---------------------------------------------------------
@bursar_routes.route('/manage-staff-salaries')
def manage_staff_salaries():
    """
    Display all staff grouped by role with salary information and payment status.
    Allows filtering by role and period (month/year or term/year).
    """
    # Get all roles that have users (non-empty staff) — EXCLUDE 'Parent' role
    roles = db.session.query(Role).join(User, Role.id == User.role_id).filter(
        Role.role_name != 'Parent'
    ).distinct().order_by(Role.role_name).all()

    # Get current month/year as default period
    today = datetime.utcnow()
    current_month = request.args.get('month', today.month, type=int)
    current_year = request.args.get('year', today.year, type=int)
    selected_role_id = request.args.get('role_id', None, type=int)
    filter_status = request.args.get('status', 'all')  # 'all', 'paid', 'unpaid'

    # Base query: all staff users with salary-eligible roles — EXCLUDE 'Parent' role
    query = db.session.query(User).join(Role, User.role_id == Role.id).filter(
        Role.role_name != 'Parent'
    )

    if selected_role_id:
        query = query.filter(User.role_id == selected_role_id)

    staff_users = query.order_by(User.first_name, User.last_name).all()

    # Build staff with payment status for the selected period
    staff_data = []
    for user in staff_users:
        # Get salary amount (per-user override or role default)
        salary_amount = user.salary_amount
        if salary_amount is None and user.role and user.role.salary_config:
            salary_amount = user.role.salary_config.amount

        # Check if paid for this period
        payment = SalaryPayment.query.filter(
            SalaryPayment.user_id == user.id,
            SalaryPayment.period_month == current_month,
            SalaryPayment.period_year == current_year,
            SalaryPayment.status == 'paid'
        ).first()

        is_paid = bool(payment)

        # Apply status filter
        if filter_status == 'paid' and not is_paid:
            continue
        elif filter_status == 'unpaid' and is_paid:
            continue

        staff_data.append({
            'id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'role': user.role.role_name,
            'salary_amount': float(salary_amount) if salary_amount else 0.0,
            'is_paid': is_paid,
            'last_payment': payment,
            'last_payment_reference': (payment.reference if payment and getattr(payment, 'reference', None) else (f"PAY-{payment.payment_date.strftime('%Y%m%d%H%M%S')}-{payment.id}" if payment and getattr(payment, 'payment_date', None) and getattr(payment, 'id', None) else None)),
            'payment_method': payment.payment_method if payment else None,
            'bank_name': payment.bank_name if payment else None,
        })

    # Compute overall stats for the selected period (ignore filters) — EXCLUDE 'Parent' role
    all_staff = db.session.query(User).join(Role, User.role_id == Role.id).filter(
        Role.role_name != 'Parent'
    ).order_by(User.first_name, User.last_name).all()
    total_staff_all = len(all_staff)
    paid_count_all = 0
    for u in all_staff:
        p = SalaryPayment.query.filter(
            SalaryPayment.user_id == u.id,
            SalaryPayment.period_month == current_month,
            SalaryPayment.period_year == current_year,
            SalaryPayment.status == 'paid'
        ).first()
        if p:
            paid_count_all += 1
    unpaid_count_all = total_staff_all - paid_count_all

    # Also update the session-based resolver in the manage_staff_salaries endpoint for consistency
    current_bursar_full_name = ''
    try:
        from flask import session
        session_user_id = session.get('user_id')
        if session_user_id:
            db_user = db.session.query(User).get(session_user_id)
            if db_user:
                current_bursar_full_name = f"{db_user.first_name} {db_user.last_name}".strip()
    except Exception:
        current_bursar_full_name = ''

    return render_template('bursar/manage_staff_salaries.html',
                          staff=staff_data,
                          roles=roles,
                          selected_role_id=selected_role_id,
                          current_month=current_month,
                          current_year=current_year,
                          filter_status=filter_status,
                          total_staff_all=total_staff_all,
                          paid_count_all=paid_count_all,
                          unpaid_count_all=unpaid_count_all,
                          current_bursar_full_name=current_bursar_full_name)


# ---------------------------------------------------------
# GET: Staff salary payment history (for a user)
# ---------------------------------------------------------
@bursar_routes.route('/staff/<int:user_id>/salary-history')
def staff_salary_history(user_id):
    """Get payment history for a specific staff member."""
    user = User.query.get_or_404(user_id)
    payments = SalaryPayment.query.filter_by(user_id=user_id).order_by(desc(SalaryPayment.payment_date)).all()

    history = []
    for p in payments:
        # resolve payer name if possible
        paid_by_name = None
        try:
            if getattr(p, 'paid_by_user_id', None):
                pb = User.query.get(p.paid_by_user_id)
                if pb:
                    paid_by_name = f"{pb.first_name} {pb.last_name}".strip()
        except Exception:
            paid_by_name = None

        # Provide display values when DB fields are missing (non-destructive)
        display_ref = p.reference if p.reference else (f"PAY-{p.payment_date.strftime('%Y%m%d%H%M%S')}-{p.id}" if p.payment_date and p.id else None)
        display_paid_by = paid_by_name
        if not display_paid_by:
            # fallback to logged-in user's name if available
            try:
                from flask_login import current_user as _cu
                if _cu and getattr(_cu, 'is_authenticated', False):
                    fn = getattr(_cu, 'first_name', None) or getattr(_cu, 'name', None) or ''
                    ln = getattr(_cu, 'last_name', None) or ''
                    cand = (fn + ' ' + ln).strip()
                    if cand:
                        display_paid_by = cand
            except Exception:
                pass

        history.append({
            'id': p.id,
            'amount': float(p.amount),
            'payment_date': p.payment_date.isoformat() if p.payment_date else None,
            'period': p.period_display,
            'status': p.status,
            'reference': p.reference,
            'reference_display': display_ref,
            'notes': p.notes,
            'payment_method': p.payment_method,
            'bank_name': p.bank_name,
            'paid_by_name': display_paid_by,
        })

    return jsonify({
        'success': True,
        'user': f"{user.first_name} {user.last_name}",
        'email': user.email,
        'role': user.role.role_name,
        'history': history
    })


# ---------------------------------------------------------
# POST: Mark staff as unpaid / reverse payment
# ---------------------------------------------------------
@bursar_routes.route('/staff/<int:user_id>/mark-unpaid', methods=['POST'])
def mark_staff_unpaid(user_id):
    """
    Reverse/delete a salary payment record for a staff member.
    Expects JSON: { payment_id } - if not provided, reverses the most recent paid payment for the period
    """
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json() or {}
        payment_id_raw = data.get('payment_id')

        payment = None
        try:
            payment_id = int(payment_id_raw) if payment_id_raw is not None and payment_id_raw != '' else None
        except (ValueError, TypeError):
            payment_id = None

        # If no payment_id provided, find the most recent paid payment for this user
        if not payment_id:
            payment = SalaryPayment.query.filter_by(
                user_id=user_id,
                status='paid'
            ).order_by(
                SalaryPayment.period_year.desc(),
                SalaryPayment.period_month.desc()
            ).first()

            if not payment:
                return jsonify({'success': False, 'error': 'No paid payment found to reverse'}), 400
        else:
            payment = SalaryPayment.query.get_or_404(payment_id)

        # Verify payment belongs to this user
        if payment.user_id != user_id:
            return jsonify({'success': False, 'error': 'Payment does not belong to this user'}), 403

        # Mark as reversed (audit trail) instead of deleting
        payment.status = 'reversed'
        payment.notes = (payment.notes or '') + '\n[Reversed by bursar]'
        payment.updated_at = datetime.utcnow()

        db.session.commit()

        # Return detailed info for immediate template update
        return jsonify({
            'success': True,
            'message': f"✓ Payment reversed for {user.first_name} {user.last_name}",
            'payment_id': payment.id,
            'payment': {
                'id': payment.id,
                'status': payment.status,
                'notes': payment.notes,
                'updated_at': payment.updated_at.isoformat() if payment.updated_at else None
            },
            'staff_update': {
                'user_id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_paid': False,
                'salary_amount': float(user.salary_amount) if user.salary_amount else 0.0
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------------------------------------------------------
# GET: Salary report (paid/unpaid summary by role and period)
# ---------------------------------------------------------
@bursar_routes.route('/salary-report')
def salary_report():
    """
    Generate a summary report of salary payments by role and period.
    Query parameters: month, year, role_id
    """
    month = request.args.get('month', datetime.utcnow().month, type=int)
    year = request.args.get('year', datetime.utcnow().year, type=int)
    role_id = request.args.get('role_id', None, type=int)

    # Query payments for the period
    query = SalaryPayment.query.filter(
        SalaryPayment.period_month == month,
        SalaryPayment.period_year == year,
        SalaryPayment.status == 'paid'
    )

    if role_id:
        query = query.filter(SalaryPayment.role_id == role_id)

    payments = query.all()

    # Aggregate by role
    by_role = {}
    total_paid = Decimal('0')

    for p in payments:
        role_name = p.role.role_name if p.role else 'Unknown'
        if role_name not in by_role:
            by_role[role_name] = {'count': 0, 'total': Decimal('0')}
        by_role[role_name]['count'] += 1
        by_role[role_name]['total'] += p.amount
        total_paid += p.amount

    # Convert to list for JSON
    report_data = [
        {'role': role, 'count': stats['count'], 'total': float(stats['total'])}
        for role, stats in by_role.items()
    ]

    return jsonify({
        'success': True,
        'period': f"{month}/{year}",
        'total_paid': float(total_paid),
        'payment_count': len(payments),
        'by_role': report_data,
    })


@bursar_routes.route('/salary-payments/backfill-missing', methods=['POST'])
def backfill_missing_salary_metadata():
    """Admin utility: backfill missing references and notes for existing SalaryPayment rows.

    Behavior:
    - For each SalaryPayment with empty or NULL `reference`, generate a server-side unique reference and append a backfill note.
    - If the current_user is authenticated, set `paid_by_user_id` for rows where it's missing to the current_user id (marking who performed the backfill).

    This endpoint is intentionally destructive (writes to DB). Only run it once after reviewing the preview response.
    """
    try:
        from flask_login import current_user as _cu
        actor_id = None
        actor_name = 'System'
        if _cu and getattr(_cu, 'is_authenticated', False) and getattr(_cu, 'id', None):
            actor_id = _cu.id
            actor_name = getattr(_cu, 'first_name', '') + ' ' + getattr(_cu, 'last_name', '')

        # Find payments missing reference or notes
        candidates = SalaryPayment.query.filter((SalaryPayment.reference == None) | (SalaryPayment.reference == '')).all()
        updated = 0
        for p in candidates:
            try:
                gen_ts = datetime.utcnow()
                new_ref = f"PAY-{gen_ts.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
                p.reference = new_ref
                # append a note stating this was backfilled
                backfill_note = f"[Backfilled by {actor_name} on {gen_ts.strftime('%Y-%m-%d %H:%M:%S')} UTC]"
                if p.notes:
                    p.notes = p.notes + '\n' + backfill_note
                else:
                    p.notes = backfill_note
                # set paid_by_user_id to actor if missing
                if not p.paid_by_user_id and actor_id:
                    p.paid_by_user_id = actor_id
                updated += 1
            except Exception:
                # skip problematic record
                continue

        db.session.commit()
        return jsonify({'success': True, 'updated_count': updated, 'message': f'Backfilled {updated} payments.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500





