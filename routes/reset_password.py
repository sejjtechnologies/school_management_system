# routes/reset_password.py

import os
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from werkzeug.security import generate_password_hash
from models.user_models import db, User
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv

# ✅ Load environment variables
load_dotenv()

reset_password_routes = Blueprint("reset_password_routes", __name__)

@reset_password_routes.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    alert_message = None
    alert_category = None  # 'success' or 'danger'

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip()
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        # ✅ Basic validation
        if not all([first_name, last_name, email, new_password, confirm_password]):
            alert_message = "All fields are required."
            alert_category = "danger"
            return render_template(
                "reset_password.html",
                alert_message=alert_message,
                alert_category=alert_category
            )

        if new_password != confirm_password:
            alert_message = "Passwords do not match."
            alert_category = "danger"
            return render_template(
                "reset_password.html",
                alert_message=alert_message,
                alert_category=alert_category
            )

        try:
            # ✅ Attempt to find user
            user = User.query.filter_by(
                first_name=first_name,
                last_name=last_name,
                email=email
            ).first()

            if not user:
                alert_message = "No user found with the provided details."
                alert_category = "danger"
                return render_template(
                    "reset_password.html",
                    alert_message=alert_message,
                    alert_category=alert_category
                )

            # ✅ Hash the new password and update
            user.password = generate_password_hash(new_password)
            db.session.commit()

            alert_message = "Password has been reset successfully!"
            alert_category = "success"
            return render_template(
                "reset_password.html",
                alert_message=alert_message,
                alert_category=alert_category
            )

        except OperationalError as e:
            db.session.rollback()
            current_app.logger.error(f"OperationalError during reset: {str(e)}")
            alert_message = "Database connection error. Please try again."
            alert_category = "danger"
            return render_template(
                "reset_password.html",
                alert_message=alert_message,
                alert_category=alert_category
            )

    return render_template("reset_password.html")
