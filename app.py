from io import BytesIO
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pandas as pd

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- CONFIG ----------------
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///students.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

db = SQLAlchemy(app)

# ---------------- DATABASE MODEL ----------------
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    roll = db.Column(db.String(50), unique=True, nullable=False)
    branch = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == ADMIN_USERNAME and request.form["password"] == ADMIN_PASSWORD:
            session["logged_in"] = True
            flash("Login successful!", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid credentials", "danger")
    return render_template("login.html")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "info")
    return redirect(url_for("login"))

# ---------------- REGISTRATION PAGE ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form["name"].strip()
        roll = request.form["roll"]
        branch = request.form["branch"]
        email = request.form["email"]

        # Name validation: alphabets + space only
        if not name.replace(" ", "").isalpha():
            flash("Name should contain only alphabets", "danger")
            return redirect(url_for("index"))

        if Student.query.filter_by(roll=roll).first():
            flash("Roll number already exists!", "danger")
            return redirect(url_for("index"))

        if Student.query.filter_by(email=email).first():
            flash("Email already exists!", "danger")
            return redirect(url_for("index"))

        student = Student(name=name, roll=roll, branch=branch, email=email)
        db.session.add(student)
        db.session.commit()

        flash("Student registered successfully!", "success")
        return redirect(url_for("index"))

    students = Student.query.all()
    branch_counts = {}
    for s in students:
        branch_counts[s.branch] = branch_counts.get(s.branch, 0) + 1

    return render_template(
        "index.html",
        total_students=len(students),
        branch_counts=branch_counts
    )

# ---------------- VIEW STUDENTS ----------------
@app.route("/students")
def view_students():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    search = request.args.get("search")
    selected_branch = request.args.get("branch")
    filter_type = request.args.get("filter")  # new filter query

    query = Student.query

    if search:
        query = query.filter(Student.name.ilike(f"%{search}%"))
    if selected_branch:
        query = query.filter_by(branch=selected_branch)

    # Apply filter
    if filter_type == "alphabetical_asc":
        students = query.order_by(Student.name.asc()).all()
    elif filter_type == "alphabetical_desc":
        students = query.order_by(Student.name.desc()).all()
    elif filter_type == "date_asc":
        students = query.order_by(Student.created_at.asc()).all()
    elif filter_type == "date_desc":
        students = query.order_by(Student.created_at.desc()).all()
    else:
        students = query.order_by(Student.created_at.desc()).all()

    # Branch counts
    branch_counts = {}
    for s in Student.query.all():
        branch_counts[s.branch] = branch_counts.get(s.branch, 0) + 1

    return render_template(
        "students.html",
        students=students,
        branch_counts=branch_counts,
        selected_branch=selected_branch
    )

# ---------------- EDIT ----------------
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    student = Student.query.get_or_404(id)
    if request.method == "POST":
        name = request.form["name"].strip()
        if not name.replace(" ", "").isalpha():
            flash("Name should contain only alphabets", "danger")
            return redirect(url_for("edit", id=id))
        student.name = name
        student.branch = request.form["branch"]
        student.email = request.form["email"]
        db.session.commit()
        flash("Student updated successfully!", "success")
        return redirect(url_for("view_students"))

    return render_template("edit.html", student=student)

# ---------------- DELETE ----------------
@app.route("/delete/<int:id>")
def delete(id):
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    student = Student.query.get_or_404(id)
    db.session.delete(student)
    db.session.commit()
    flash("Student deleted!", "danger")
    return redirect(url_for("view_students"))

# ---------------- DOWNLOAD ----------------
@app.route("/download")
def download():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    students = Student.query.order_by(Student.name.asc()).all()

    data = [{
        "Name": s.name,
        "Roll": s.roll,
        "Branch": s.branch,
        "Email": s.email,
        "Registered At": s.created_at.strftime("%d-%m-%Y %H:%M:%S")
    } for s in students]

    df = pd.DataFrame(data)
    output = BytesIO()
    df.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="students.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ---------------- RUN ----------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
