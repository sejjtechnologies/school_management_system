from flask import Blueprint, render_template

parent_routes = Blueprint("parent_routes", __name__)

@parent_routes.route("/parent/dashboard")
def dashboard():
    return render_template("parent/dashboard.html")