from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.user_models import db, User, Role
from werkzeug.security import generate_password_hash

admin_routes = Blueprint("admin_routes", __name__)

@admin_routes.route("/admin/dashboard")
def dashboard():
    return render_template("admin/dashboard.html")

@admin_routes.route("/admin/manage-users")
def manage_users():
    users = User.query.order_by(User.id.asc()).all()
    return render_template("admin/manage_users.html", users=users)

@admin_routes.route("/admin/create-user", methods=["GET", "POST"])
def create_user():
    # ✅ Show all roles except Admin (to prevent creating another Admin via UI)
    roles = Role.query.filter(Role.role_name != "Admin").order_by(Role.role_name.asc()).all()

    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        password = request.form.get("password")
        role_name = request.form.get("role")

        # ✅ Always resolve role_id from roles table
        role = Role.query.filter_by(role_name=role_name).first()
        if not role:
            flash("Invalid role selected.", "danger")
            return render_template("admin/create_user.html", roles=roles)

        # ✅ Unique email check
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already exists. Please use a different email.", "danger")
            return render_template("admin/create_user.html", roles=roles,
                                   first_name=first_name, last_name=last_name, email=email)

        # ✅ Hash password
        hashed_password = generate_password_hash(password)

        # ✅ Create user with correct role_id
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=hashed_password,
            role_id=role.id   # ✅ Always correct mapping
        )
        db.session.add(new_user)
        db.session.commit()

        flash("User created successfully!", "success")
        return redirect(url_for("admin_routes.manage_users"))

    return render_template("admin/create_user.html", roles=roles)

@admin_routes.route("/admin/edit-user/<int:user_id>", methods=["GET", "POST"])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    roles = Role.query.filter(Role.role_name != "Admin").order_by(Role.role_name.asc()).all()

    if request.method == "POST":
        user.first_name = request.form.get("first_name")
        user.last_name = request.form.get("last_name")
        new_email = request.form.get("email")
        role_name = request.form.get("role")
        password = request.form.get("password")

        # ✅ Always resolve role_id from roles table
        role = Role.query.filter_by(role_name=role_name).first()
        if not role:
            flash("Invalid role selected.", "danger")
            return render_template("admin/edit_user.html", user=user, roles=roles)

        # ✅ Unique email check (exclude current user)
        existing_user = User.query.filter(User.email == new_email, User.id != user.id).first()
        if existing_user:
            flash("Email already exists. Please use a different email.", "danger")
            return render_template("admin/edit_user.html", user=user, roles=roles)

        user.email = new_email
        user.role_id = role.id   # ✅ Always correct mapping

        if password:
            user.password = generate_password_hash(password)

        db.session.commit()
        flash("User updated successfully!", "success")
        return redirect(url_for("admin_routes.manage_users"))

    return render_template("admin/edit_user.html", user=user, roles=roles)

@admin_routes.route("/admin/delete-user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash("User deleted successfully!", "success")
    return redirect(url_for("admin_routes.manage_users"))