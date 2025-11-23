from flask import Blueprint, request, redirect, render_template, flash, session, url_for
from werkzeug.security import check_password_hash
from models.user_models import db, User, Role

user_routes = Blueprint("user_routes", __name__)

@user_routes.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        remember = request.form.get("remember") == "on"

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["role"] = user.role.role_name
            session.permanent = remember

            role = user.role.role_name.lower()

            return redirect(url_for(f"user_routes.{role}_dashboard"))
        else:
            flash("Invalid email or password.", "danger")
            return redirect(url_for("user_routes.login"))

    return render_template("index.html")

@user_routes.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("user_routes.login"))

# Dashboard routes for each role
@user_routes.route("/admin/dashboard")
def admin_dashboard():
    return render_template("admin/dashboard.html")

@user_routes.route("/teacher/dashboard")
def teacher_dashboard():
    return render_template("teacher/dashboard.html")

@user_routes.route("/secretary/dashboard")
def secretary_dashboard():
    return render_template("secretary/dashboard.html")

@user_routes.route("/headteacher/dashboard")
def headteacher_dashboard():
    return render_template("headteacher/dashboard.html")

@user_routes.route("/parent/dashboard")
def parent_dashboard():
    return render_template("parent/dashboard.html")

@user_routes.route("/bursar/dashboard")
def bursar_dashboard():
    return render_template("bursar/dashboard.html")