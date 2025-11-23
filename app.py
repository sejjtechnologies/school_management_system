from flask import Flask, render_template
from models.user_models import db
from routes.user_routes import user_routes
from routes.admin_routes import admin_routes
from routes.secretary_routes import secretary_routes  # ✅ Newly added

# ✅ Direct model imports for table creation
from models.register_pupils import Pupil
from models.class_model import Class
from models.stream_model import Stream

app = Flask(__name__)
app.secret_key = "your_secret_key"

# ✅ Hardcoded Neon PostgreSQL connection string
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "postgresql://neondb_owner:npg_sCrqa7J6oxGg@ep-snowy-voice-afsxk5rn-pooler.c-2.us-west-2.aws.neon.tech/neondb"
    "?sslmode=require&channel_binding=require"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

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