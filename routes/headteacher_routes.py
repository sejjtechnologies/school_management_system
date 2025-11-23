from flask import Blueprint, render_template

headteacher_routes = Blueprint("headteacher_routes", __name__)

@headteacher_routes.route("/headteacher/dashboard")
def dashboard():
    return render_template("headteacher/dashboard.html")