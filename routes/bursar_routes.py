from flask import Blueprint, render_template

bursar_routes = Blueprint("bursar_routes", __name__)

@bursar_routes.route("/bursar/dashboard")
def dashboard():
    return render_template("bursar/dashboard.html")