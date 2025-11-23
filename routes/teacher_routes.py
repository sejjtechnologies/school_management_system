from flask import Blueprint, render_template

teacher_routes = Blueprint("teacher_routes", __name__)

@teacher_routes.route("/teacher/dashboard")
def dashboard():
    return render_template("teacher/dashboard.html")