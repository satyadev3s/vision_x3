from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import uuid

app = Flask(__name__)
CORS(app)

# ================= CONFIG =================
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:spacegp_infinite1@localhost/mydatabase'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

db = SQLAlchemy(app)

# ================= MODELS =================
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    age = db.Column(db.Integer, nullable=False)
    schoolname = db.Column(db.String(50), nullable=False)
    classofstudy = db.Column(db.String(30), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "age": self.age,
            "schoolname": self.schoolname,
            "classofstudy": self.classofstudy,
            "score": self.score
        }

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    schoolname = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(100), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "schoolname": self.schoolname
        }

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(50), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    teacher_name = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "subject": self.subject,
            "teacher_name": self.teacher_name,
            "date": self.timestamp.strftime("%Y-%m-%d %H:%M"),
            "url": f"http://localhost:5000/uploads/{self.filename}"
        }

with app.app_context():
    db.create_all()

# ================= STUDENT SIGNUP =================
@app.route("/TeacherSignup", methods=["POST"])
def teacher_signup():
    data = request.get_json()

    required = ["name", "email", "schoolname", "password"]
    if not all(k in data for k in required):
        return jsonify({"error": "Missing fields"}), 400

    if Teacher.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already exists"}), 400

    teacher = Teacher(
        name=data["name"],
        email=data["email"],
        schoolname=data["schoolname"],
        password=data["password"]
    )

    db.session.add(teacher)
    db.session.commit()

    return jsonify({"message": "Signup successful"}), 201

@app.route("/Signup", methods=["POST"])
def signup_student():
    data = request.get_json()
    required = ["name", "age", "schoolname", "classofstudy", "password"]

    if not data or not all(k in data for k in required):
        return jsonify({"error": "Missing fields"}), 400

    if Student.query.filter_by(name=data["name"]).first():
        return jsonify({"error": "Username already exists"}), 400

    student = Student(
        name=data["name"],
        age=int(data["age"]),
        schoolname=data["schoolname"],
        classofstudy=data["classofstudy"],
        password=data["password"]
    )

    db.session.add(student)
    db.session.commit()

    return jsonify({"message": "Signup successful", "student": student.to_dict()}), 201

# ================= STUDENT LOGIN =================
@app.route("/Login", methods=["POST"])
def login_student():
    data = request.get_json()

    student = Student.query.filter_by(name=data.get("identifier")).first()
    if not student or student.password != data.get("password"):
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({"message": "Login successful", "student": student.to_dict()}), 200

# ================= TEACHER LOGIN =================
@app.route("/TeacherLogin", methods=["POST"])
def login_teacher():
    data = request.get_json()

    teacher = Teacher.query.filter_by(email=data.get("email")).first()
    if not teacher or teacher.password != data.get("password"):
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({"message": "Login successful", "teacher": teacher.to_dict()}), 200

# ================= ASSIGN WORK =================
from datetime import datetime
import  uuid

import re
from werkzeug.utils import secure_filename

@app.route("/assign_work", methods=["POST"])
def assign_work():
    try:
        print("=== ASSIGN_WORK DEBUG ===")
        print("FORM DATA:", dict(request.form))
        print("FILES:", list(request.files.keys()))
        
        subject = request.form.get("subject", "").strip()
        teacher_name = request.form.get("teacher_name", "Unknown Teacher").strip()
        
        print(f"SUBJECT RECEIVED: '{subject}'")
        print(f"TEACHER NAME: '{teacher_name}'")

        if not subject:
            return jsonify({"error": "Subject missing"}), 400

        if "assignment_file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["assignment_file"]
        if not file or file.filename == "":
            return jsonify({"error": "Empty file"}), 400

        # Simple Windows-friendly file validation
        original_filename = file.filename
        filename = secure_filename(original_filename)
        
        # Check extension (matches your frontend accept attribute)
        allowed_extensions = ['.pdf', '.doc', '.docx', '.png', '.jpg']
        file_ext = os.path.splitext(filename.lower())[1]
        if file_ext not in allowed_extensions:
            return jsonify({"error": f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"}), 400

        # Size limit (10MB)
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)     # Reset to start
        if file_size > 10 * 1024 * 1024:
            return jsonify({"error": "File too large (max 10MB)"}), 400

        print(f"FILE: {filename} ({file_size} bytes)")

        # Save with unique name
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        unique_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
        file.save(filepath)

        assignment = Assignment(
            subject=subject,
            filename=unique_filename,
            teacher_name=teacher_name,
            timestamp=datetime.utcnow()
        )

        db.session.add(assignment)
        db.session.commit()

        print("✅ SUCCESS:", assignment.id)
        return jsonify({
            "message": "Assignment uploaded successfully",
            "assignment": assignment.to_dict()
        }), 201

    except Exception as e:
        print("❌ ERROR:", str(e))
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ================= GET ASSIGNMENTS (STUDENTS) =================
@app.route("/assignments", methods=["GET"])
def get_assignments():
    works = Assignment.query.order_by(Assignment.timestamp.desc()).all()
    return jsonify([w.to_dict() for w in works]), 200

# ================= FILE SERVE =================
@app.route("/uploads/<filename>")
def serve_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# ================= SCORE UPDATE =================
@app.route("/scoreupdate", methods=["POST"])
def update_score():
    data = request.get_json()
    student = Student.query.filter_by(name=data.get("name")).first()

    if not student:
        return jsonify({"error": "User not found"}), 404

    student.score += int(data.get("score", 0))
    db.session.commit()

    return jsonify({"message": "Score updated", "student": student.to_dict()}), 200

# ================= LEADERBOARD =================
@app.route("/leaderboard", methods=["GET"])
def leaderboard():
    students = Student.query.order_by(Student.score.desc()).all()
    return jsonify([s.to_dict() for s in students]), 200

# ================= PROFILE UPDATE =================
@app.route("/profilesupdate", methods=["POST"])
def update_profile():
    data = request.get_json()
    student = Student.query.filter_by(name=data.get("name")).first()

    if not student:
        return jsonify({"error": "User not found"}), 404

    for field in ["age", "schoolname", "classofstudy", "password"]:
        if field in data:
            setattr(student, field, data[field])

    db.session.commit()
    return jsonify({"message": "Profile updated", "student": student.to_dict()}), 200

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
