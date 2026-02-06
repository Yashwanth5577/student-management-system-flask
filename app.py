from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pandas as pd

app = Flask(__name__)
app.secret_key = "secret123"

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///students.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Admin credentials
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

# ---------------- INDEX / REGISTER ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    # ---------- REGISTER STUDENT ----------
    if request.method == "POST":
        name = request.form["name"]
        roll = request.form["roll"]
        branch = request.form["branch"]
        email = request.form["email"]

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

    # ---------- FILTER & SEARCH ----------
    search = request.args.get("search")
    selected_branch = request.args.get("branch")

    query = Student.query

    if search:
        query = query.filter(Student.name.ilike(f"%{search}%"))

    if selected_branch:
        query = query.filter_by(branch=selected_branch)

    students = query.order_by(Student.created_at.desc()).all()

    # ---------- BRANCH COUNTS (ALL STUDENTS) ----------
    all_students = Student.query.all()
    branch_counts = {}
    for s in all_students:
        branch_counts[s.branch] = branch_counts.get(s.branch, 0) + 1

    return render_template(
        "index.html",
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
        student.name = request.form["name"]
        student.branch = request.form["branch"]
        student.email = request.form["email"]
        db.session.commit()
        flash("Student updated successfully!", "success")
        return redirect(url_for("index"))

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
    return redirect(url_for("index"))

# ---------------- DOWNLOAD EXCEL ----------------
@app.route("/download")
def download():
    students = Student.query.order_by(Student.created_at.desc()).all()

    data = [{
        "Name": s.name,
        "Roll": s.roll,
        "Branch": s.branch,
        "Email": s.email,
        "Registered At": s.created_at.strftime("%d-%m-%Y %H:%M:%S")
    } for s in students]

    df = pd.DataFrame(data)
    file = "students.xlsx"
    df.to_excel(file, index=False)

    return send_file(file, as_attachment=True)

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

# ---------------- RUN ----------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
