from flask import Blueprint, render_template, request, redirect, url_for
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from sqlalchemy import extract, func
from collections import Counter
from models.user_models import db
from models.register_pupils import Pupil
from models.class_model import Class
from models.stream_model import Stream

secretary_routes = Blueprint("secretary_routes", __name__)

# Utility: Generate next admission number (HPF001, HPF002, ...)
def generate_admission_number():
    last_pupil = Pupil.query.order_by(Pupil.id.desc()).first()
    if last_pupil and last_pupil.admission_number and last_pupil.admission_number.startswith("HPF"):
        try:
            last_num = int(last_pupil.admission_number.replace("HPF", ""))
            next_num = last_num + 1
        except ValueError:
            next_num = 1
    else:
        next_num = 1
    return f"HPF{str(next_num).zfill(3)}"

# Utility: Generate next receipt number (RCT-001, RCT-002, ...)
def generate_receipt_number():
    last_pupil = Pupil.query.order_by(Pupil.id.desc()).first()
    if last_pupil and last_pupil.receipt_number and last_pupil.receipt_number.startswith("RCT-"):
        try:
            last_num = int(last_pupil.receipt_number.replace("RCT-", ""))
            next_num = last_num + 1
        except ValueError:
            next_num = 1
    else:
        next_num = 1
    return f"RCT-{str(next_num).zfill(3)}"

# Utility: Generate next pupil_id (ID001, ID002, ...)
def generate_pupil_id():
    last_pupil = Pupil.query.order_by(Pupil.id.desc()).first()
    if last_pupil and last_pupil.pupil_id and last_pupil.pupil_id.startswith("ID"):
        try:
            last_num = int(last_pupil.pupil_id.replace("ID", ""))
            next_num = last_num + 1
        except ValueError:
            next_num = 1
    else:
        next_num = 1
    return f"ID{str(next_num).zfill(3)}"

# Utility: Generate roll/index number (H25/001, H25/002, ...)
def generate_roll_number(admission_date: datetime):
    last_pupil = Pupil.query.order_by(Pupil.id.desc()).first()
    if last_pupil and last_pupil.roll_number and last_pupil.roll_number.startswith("H25/"):
        try:
            last_num = int(last_pupil.roll_number.replace("H25/", ""))
            next_num = last_num + 1
        except ValueError:
            next_num = 1
    else:
        next_num = 1
    return f"H25/{str(next_num).zfill(3)}"

# Utility: Save profile image
def save_photo(file, pupil_id):
    if file and file.filename:
        upload_dir = os.path.join("static", "uploads", "pupils")
        os.makedirs(upload_dir, exist_ok=True)

        existing = Pupil.query.filter_by(pupil_id=pupil_id).first()
        if existing and existing.photo:
            try:
                existing_path = existing.photo.lstrip("/")
                if os.path.exists(existing_path):
                    os.remove(existing_path)
            except Exception as e:
                print(f"Warning: Failed to delete old photo: {e}")

        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        final_name = f"{timestamp}_{filename}"
        full_path = os.path.join(upload_dir, final_name)
        file.save(full_path)
        return f"/{full_path}"
    return None

# GET: Dashboard
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
    # Validate required fields
    if not request.form.get("class") or not request.form.get("class").strip():
        flash("Class is required", "error")
        return redirect(url_for("secretary_routes.register_pupil"))
    
    if not request.form.get("stream") or not request.form.get("stream").strip():
        flash("Stream is required", "error")
        return redirect(url_for("secretary_routes.register_pupil"))
    
    admission_date = datetime.strptime(request.form["admission_date"], "%Y-%m-%d").date()
    admission_number = generate_admission_number()
    receipt_number = generate_receipt_number()
    pupil_id = generate_pupil_id()
    roll_number = generate_roll_number(admission_date)
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
        class_id=int(request.form["class"]),
        stream_id=int(request.form["stream"]),
        previous_school=request.form.get("previous_school"),
        roll_number=roll_number,
        photo=photo_path,
        admission_number=admission_number,
        receipt_number=receipt_number,
        enrollment_status=request.form["enrollment_status"],
    )

    db.session.add(pupil)
    db.session.commit()
    return redirect(url_for("secretary_routes.manage_pupils"))

# GET: Manage pupils
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

# GET: Edit pupil
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

# POST: Update pupil
@secretary_routes.route("/edit-pupil/<int:pupil_id>", methods=["POST"])
def update_pupil(pupil_id):
    pupil = Pupil.query.get_or_404(pupil_id)
    
    # Validate required fields
    if not request.form.get("class_id") or not request.form.get("class_id").strip():
        flash("Class is required", "error")
        return redirect(url_for("secretary_routes.edit_pupil", pupil_id=pupil_id))
    
    if not request.form.get("stream_id") or not request.form.get("stream_id").strip():
        flash("Stream is required", "error")
        return redirect(url_for("secretary_routes.edit_pupil", pupil_id=pupil_id))

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
    pupil.class_id = int(request.form["class_id"])
    pupil.stream_id = int(request.form["stream_id"])
    pupil.previous_school = request.form.get("previous_school")
    pupil.enrollment_status = request.form["enrollment_status"]

    pupil.roll_number = generate_roll_number(pupil.admission_date)
    photo_path = save_photo(request.files.get("profile_image"), pupil.pupil_id)
    if photo_path:
        pupil.photo = photo_path

    db.session.commit()
    return redirect(url_for("secretary_routes.manage_pupils"))

# POST: Delete pupil
@secretary_routes.route("/delete-pupil/<int:pupil_id>", methods=["POST"])
def delete_pupil(pupil_id):
    pupil = Pupil.query.get_or_404(pupil_id)
    if pupil.photo:
        try:
            existing_path = pupil.photo.lstrip("/")
            if os.path.exists(existing_path):
                os.remove(existing_path)
        except Exception as e:
            print(f"Warning: Failed to delete photo: {e}")
    db.session.delete(pupil)
    db.session.commit()
    return redirect(url_for("secretary_routes.manage_pupils"))
