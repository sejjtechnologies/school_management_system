import os
from flask import Flask, render_template
from models.user_models import db
from routes.user_routes import user_routes
from routes.admin_routes import admin_routes
from routes.secretary_routes import secretary_routes
from dotenv import load_dotenv   # ✅ Import dotenv

# ✅ Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# ✅ Secret key from environment
app.secret_key = os.getenv("SECRET_KEY", "default_secret")

# ✅ Database configuration from environment
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = (
    os.getenv("SQLALCHEMY_TRACK_MODIFICATIONS", "False") == "True"
)

# ✅ Initialize DB
db.init_app(app)

# ✅ Register Blueprints
app.register_blueprint(user_routes)
app.register_blueprint(admin_routes)
app.register_blueprint(secretary_routes)

@app.route("/")
def index():
    return render_template("index.html")

# ✅ Auto-create tables if missing
with app.app_context():
    db.create_all()

# ✅ Entry point for local testing
if __name__ == "__main__":
    app.run(debug=True)