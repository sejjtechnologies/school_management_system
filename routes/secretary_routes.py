from flask import Blueprint, render_template, request, redirect, url_for
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from sqlalchemy import extract   # ✅ Import extract for year filtering
from collections import Counter   # ✅ For class counts
from models.user_models import db
from models.register_pupils import Pupil
from models.class_model import Class
from models.stream_model import Stream

secretary_routes = Blueprint("secretary_routes", __name__)

# Utility: Generate next admission number
def generate_admission_number():
    year = datetime.now().year
    count = Pupil.query.filter(extract("year", Pupil.admission_date) == year).count() + 1
    return f"Sh/sy/{year}/{str(count).zfill(3)}"

# Utility: Generate next receipt number
def generate_receipt_number():
    count = Pupil.query.count() + 1
    return f"receip{str(count).zfill(3)}"

# Utility: Generate next pupil_id (ID001, ID002, ...)
def generate_pupil_id():
    last_pupil = Pupil.query.order_by(Pupil.id.desc()).first()
    if last_pupil and last_pupil.pupil_id and last_pupil.pupil_id.startswith("ID"):
        try:
            last_num = int(last_pupil.pupil_id.replace("ID", ""))
            next_num = last_num + 1
        except ValueError:
            next_num = last_pupil.id + 1
    else:
        next_num = 1
    return f"ID{str(next_num).zfill(3)}"

# Utility: Generate roll/index number (SYY/001, SYY/002...)
def generate_roll_number(admission_date: datetime):
    year_suffix = admission_date.strftime("%y")  # last two digits of year
    month = admission_date.month

    # Count pupils registered in the same month/year
    count = Pupil.query.filter(
        extract("year", Pupil.admission_date) == admission_date.year,
        extract("month", Pupil.admission_date) == month
    ).count() + 1

    return f"S{year_suffix}/{str(count).zfill(3)}"

# Utility: Save profile image
def save_photo(file, pupil_id):
    if file and file.filename:
        upload_dir = os.path.join("static", "uploads", "pupils")
        os.makedirs(upload_dir, exist_ok=True)

        # Delete existing photo if any
        existing = Pupil.query.filter_by(pupil_id=pupil_id).first()
        if existing and existing.photo:
            try:
                existing_path = existing.photo.lstrip("/")
                if os.path.exists(existing_path):
                    os.remove(existing_path)
            except Exception as e:
                print(f"Warning: Failed to delete old photo: {e}")

        # Save new photo
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        final_name = f"{timestamp}_{filename}"
        full_path = os.path.join(upload_dir, final_name)
        file.save(full_path)
        return f"/{full_path}"
    return None

# ✅ GET: Dashboard page
@secretary_routes.route("/dashboard", methods=["GET"])
def dashboard():
    return render_template("secretary/dashboard.html")

# GET: Show registration form
@secretary_routes.route("/register-pupil", methods=["GET"])
def register_pupil():
    classes = Class.query.all()
    streams = Stream.query.all()
    return render_template(
        "secretary/register_pupil.html", classes=classes, streams=streams
    )

# POST: Handle registration
@secretary_routes.route("/register-pupil", methods=["POST"])
def submit_pupil():
    admission_date = datetime.strptime(request.form["admission_date"], "%Y-%m-%d").date()
    admission_number = generate_admission_number()
    receipt_number = generate_receipt_number()
    pupil_id = generate_pupil_id()   # ✅ Auto-generate pupil_id
    roll_number = generate_roll_number(admission_date)  # ✅ Auto-generate roll number
    photo_path = save_photo(request.files.get("profile_image"), pupil_id)

    pupil = Pupil(
        pupil_id=pupil_id,
        admission_date=admission_date,
        first_name=request.form["first_name"],
        middle_name=request.form.get("middle_name"),
        last_name=request.form["last_name"],
        gender=request.form["gender"],
        dob=datetime.strptime(request.form["dob"], "%Y-%m-%d").date(),
        nationality=request.form["nationality"],
        place_of_birth=request.form.get("place_of_birth"),
        home_address=request.form["address"],
        phone=request.form["phone"],
        email=request.form.get("email"),
        emergency_contact=request.form["emergency_contact"],
        emergency_phone=request.form["emergency_phone"],
        guardian_name=request.form["guardian_name"],
        guardian_relationship=request.form["relationship"],
        guardian_occupation=request.form.get("guardian_occupation"),
        guardian_phone=request.form["guardian_phone"],
        guardian_address=request.form.get("guardian_address"),
        class_id=request.form["class"],
        stream_id=request.form.get("stream"),
        previous_school=request.form.get("previous_school"),
        roll_number=roll_number,  # ✅ Auto-assigned roll number
        photo=photo_path,
        admission_number=admission_number,
        receipt_number=receipt_number,
        enrollment_status=request.form["enrollment_status"],
    )

    db.session.add(pupil)
    db.session.commit()

    return redirect(url_for("secretary_routes.manage_pupils"))

# GET: Manage pupils page
@secretary_routes.route("/manage-pupils", methods=["GET"])
def manage_pupils():
    pupils = Pupil.query.order_by(Pupil.admission_date.desc()).all()
    class_counts = Counter([p.class_.name if p.class_ else "Unassigned" for p in pupils])
    total_pupils = len(pupils)

    return render_template(
        "secretary/manage_pupils.html",
        pupils=pupils,
        class_counts=class_counts,
        total_pupils=total_pupils
    )
    # ✅ GET: Edit pupil form
@secretary_routes.route("/edit-pupil/<int:pupil_id>", methods=["GET"])
def edit_pupil(pupil_id):
    pupil = Pupil.query.get_or_404(pupil_id)
    classes = Class.query.all()
    streams = Stream.query.all()
    return render_template(
        "secretary/edit_pupil.html",
        pupil=pupil,
        classes=classes,
        streams=streams
    )

# ✅ POST: Update pupil details (all fields)
@secretary_routes.route("/edit-pupil/<int:pupil_id>", methods=["POST"])
def update_pupil(pupil_id):
    pupil = Pupil.query.get_or_404(pupil_id)

    # Update all fields
    pupil.admission_number = request.form.get("admission_number")
    pupil.receipt_number = request.form.get("receipt_number")
    pupil.admission_date = datetime.strptime(request.form["admission_date"], "%Y-%m-%d").date()
    pupil.first_name = request.form["first_name"]
    pupil.middle_name = request.form.get("middle_name")
    pupil.last_name = request.form["last_name"]
    pupil.gender = request.form["gender"]
    pupil.dob = datetime.strptime(request.form["dob"], "%Y-%m-%d").date()
    pupil.nationality = request.form["nationality"]
    pupil.place_of_birth = request.form.get("place_of_birth")
    pupil.home_address = request.form["home_address"]
    pupil.phone = request.form["phone"]
    pupil.email = request.form.get("email")
    pupil.emergency_contact = request.form["emergency_contact"]
    pupil.emergency_phone = request.form["emergency_phone"]
    pupil.guardian_name = request.form["guardian_name"]
    pupil.guardian_relationship = request.form["guardian_relationship"]
    pupil.guardian_occupation = request.form.get("guardian_occupation")
    pupil.guardian_phone = request.form["guardian_phone"]
    pupil.guardian_address = request.form.get("guardian_address")
    pupil.class_id = request.form["class_id"]
    pupil.stream_id = request.form["stream_id"]
    pupil.previous_school = request.form.get("previous_school")
    pupil.enrollment_status = request.form["enrollment_status"]

    # ✅ Roll number should not be manually edited — regenerate if admission_date changes
    pupil.roll_number = generate_roll_number(pupil.admission_date)

    # ✅ Handle profile image update
    photo_path = save_photo(request.files.get("profile_image"), pupil.pupil_id)
    if photo_path:
        pupil.photo = photo_path

    db.session.commit()
    return redirect(url_for("secretary_routes.manage_pupils"))

# ✅ DELETE: Remove pupil
@secretary_routes.route("/delete-pupil/<int:pupil_id>", methods=["POST"])
def delete_pupil(pupil_id):
    pupil = Pupil.query.get_or_404(pupil_id)

    # Delete photo file if exists
    if pupil.photo:
        try:
            existing_path = pupil.photo.lstrip("/")
            if os.path.exists(existing_path):
                os.remove(existing_path)
        except Exception as e:
            print(f"Warning: Failed to delete photo: {e}")

    # ✅ Remove pupil record from database
    db.session.delete(pupil)
    db.session.commit()

    return redirect(url_for("secretary_routes.manage_pupils"))