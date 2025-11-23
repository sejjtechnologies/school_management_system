from flask import Blueprint, request, redirect, render_template, flash, session, url_for, jsonify
from werkzeug.security import check_password_hash
from models.user_models import db, User, Role
import os

user_routes = Blueprint("user_routes", __name__)

@user_routes.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        remember = request.form.get("remember") == "on"

        user = User.query.filter_by(email=email).first()

        # ✅ Debug print to terminal
        print("Login attempt:", email,
              "User found:", user,
              "Password check:", check_password_hash(user.password, password) if user else None,
              "Role:", user.role.role_name if user else None)

        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["role"] = user.role.role_name
            session.permanent = remember

            role = user.role.role_name.lower()

            # ✅ Lock Admin accounts: always route to Admin dashboard
            if role == "admin":
                return redirect(url_for("user_routes.admin_dashboard"))

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

# ✅ Debugging route to test login manually
@user_routes.route("/debug-login", methods=["POST"])
def debug_login():
    email = request.form.get("email")
    password = request.form.get("password")

    user = User.query.filter_by(email=email).first()
    password_ok = check_password_hash(user.password, password) if user else None
    role = user.role.role_name if user else None

    # Print to terminal
    print("DEBUG /debug-login:", email, password, "User:", user, "Password OK:", password_ok, "Role:", role)

    return jsonify({
        "email": email,
        "user_found": bool(user),
        "password_ok": password_ok,
        "role": role
    })

# ✅ Debugging route to list all users
@user_routes.route("/debug-users")
def debug_users():
    users = User.query.all()
    output = []
    for u in users:
        output.append({
            "id": u.id,
            "email": u.email,
            "role": u.role.role_name if u.role else None
        })
    print("DEBUG /debug-users:", output)  # ✅ prints to terminal
    return jsonify({"users": output})

# ✅ Debugging route to show which DB URL is being used
@user_routes.route("/debug-db")
def debug_db():
    db_url = os.getenv("DATABASE_URL")
    print("DEBUG /debug-db: DATABASE_URL =", db_url)
    return jsonify({"DATABASE_URL": db_url})

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