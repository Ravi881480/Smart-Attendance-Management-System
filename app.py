import os
import re
import sqlite3
import io
import random
from urllib import response
import cv2
import face_recognition
import numpy as np
from datetime import date, datetime, timedelta, timezone
def match(pattern, text):
    return re.search(pattern, text)


from flask import Flask, render_template, request, redirect, url_for, send_file, session, jsonify

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from flask_mail import Mail, Message

try:
    from google import genai
except ImportError:
    genai = None

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if genai and GEMINI_API_KEY else None

# ================= PATH =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

# ================= DATABASE =================
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def log_admin_action(action):
    if not session.get('admin_logged_in'):
        return

    admin_username = session.get('admin_username', 'admin')

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO admin_logs (admin_username, action)
        VALUES (?, ?)
    """, (admin_username, action))
    conn.commit()
    conn.close()

# ================= APP =================
app = Flask(__name__)
app.secret_key = "super-secret-key"  # ✅ REQUIRED FOR SESSION



# ================= FACE DATA =================
KNOWN_FACES = []
KNOWN_IDS = []

def load_faces():
    face_path = os.path.join(BASE_DIR, "faces")

    if not os.path.exists(face_path):
        os.makedirs(face_path)

    for file in os.listdir(face_path):
        img_path = os.path.join(face_path, file)

        img = face_recognition.load_image_file(img_path)
        enc = face_recognition.face_encodings(img)

        if len(enc) > 0:
            KNOWN_FACES.append(enc[0])
            KNOWN_IDS.append(file.split('.')[0])

load_faces()


# ================= MAIL CONFIG =================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'ravi161205@gmail.com'
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")


mail = Mail(app)
otp_store = {}


# ================= HOME =================
@app.route('/')
def home():
    return render_template('login.html')


# ================= STUDENT LOGIN =================
@app.route('/student-login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        uid = request.form['uid']
        password = request.form['password']

        conn = get_db_connection()
        student = conn.execute(
            "SELECT * FROM students WHERE uid=? AND password=?",
            (uid, password)
        ).fetchone()
        conn.close()

        if student:
            return redirect(url_for('student_dashboard', uid=uid))

        return "Invalid UID or Password"

    return render_template('student_login.html')


@app.route("/timetable/<uid>")
def student_timetable(uid):
    timetable = [
        {"day": "Monday", "subject": "Mathematics", "time": "9:00 - 10:00"},
        {"day": "Tuesday", "subject": "Java", "time": "10:00 - 11:00"},
        {"day": "Wednesday", "subject": "DSA", "time": "11:00 - 12:00"},
        {"day": "Thursday", "subject": "OS", "time": "12:00 - 1:00"},
        {"day": "Friday", "subject": "SE", "time": "1:00 - 2:00"},
    ]

    return render_template(
        "student_timetable.html",
        uid=uid,
        timetable=timetable
    )
# ================= STUDENT SIGN UP =================
@app.route('/student-signup', methods=['GET', 'POST'])
def student_signup():
    if request.method == 'POST':
        uid = request.form['uid']
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()

        # Check if UID already exists
        exists = conn.execute(
            "SELECT uid FROM students WHERE uid=?",
            (uid,)
        ).fetchone()

        if exists:
            conn.close()
            return render_template(
                'student_signup.html',
                error="UID already exists. Contact Admin."
            )

        conn.execute(
            "INSERT INTO students (uid, name, email, password) VALUES (?, ?, ?, ?)",
            (uid, name, email, password)
        )
        conn.commit()
        conn.close()

        return redirect(url_for('student_login'))

    return render_template('student_signup.html')


# ================= TEACHER LOGIN =================
@app.route('/teacher-login', methods=['GET', 'POST'])
def teacher_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        teacher = conn.execute(
            "SELECT * FROM teachers WHERE username=? AND password=?",
            (username, password)
        ).fetchone()
        conn.close()

        if teacher:
            session['teacher_logged_in'] = True
            session['teacher_name'] = teacher['name']
            session['teacher_email'] = teacher['email']
            session['teacher_username'] = teacher['username']
            return redirect(url_for('teacher_dashboard'))

        return render_template(
            'teacher_login.html',
            error="Invalid credentials"
        )

    return render_template('teacher_login.html')

# ================= TEACHER SIGN UP =================
@app.route('/teacher-signup', methods=['GET', 'POST'])
def teacher_signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()

        try:
            conn.execute("""
                INSERT INTO teachers (name, email, username, password)
                VALUES (?, ?, ?, ?)
            """, (name, email, username, password))

            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return render_template(
                'teacher_signup.html',
                error="Username or Email already exists"
            )

        conn.close()
        return redirect(url_for('teacher_login'))

    return render_template('teacher_signup.html')


# ================= ADMIN LOGIN =================
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == "admin" and password == "admin@123":
            session['admin_logged_in'] = True
            session['admin_username'] = username

            log_admin_action("Admin logged in")

            return redirect(url_for('admin_dashboard'))

        # ❌ wrong credentials
        return render_template(
            'admin_login.html',
            error="Invalid admin credentials"
        )

    # GET request
    return render_template('admin_login.html')

# ================= ADMIN DASHBOARD =================
@app.route('/admin-dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()

    total_students = conn.execute(
        "SELECT COUNT(*) FROM students"
    ).fetchone()[0]

    total_teachers = conn.execute(
        "SELECT COUNT(*) FROM teachers"
    ).fetchone()[0]

    total_records = conn.execute(
        "SELECT COUNT(*) FROM daily_attendance"
    ).fetchone()[0]

    conn.close()

    return render_template(
        'admin_dashboard.html',
        total_students=total_students,
        total_teachers=total_teachers,
        total_records=total_records
    )

@app.route('/admin/profile', methods=['GET', 'POST'])
def admin_profile():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    message = None

    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']

        # simple static admin password check (as per your system)
        if current_password != "admin@123":
            message = "❌ Current password is incorrect"
        else:
            # update admin password (static version)
            # for now we just show success
            message = "✅ Password updated successfully"

    return render_template(
        'admin_profile.html',
        admin_name="System Administrator",
        admin_username="admin",
        message=message
    )

# ================= ADMIN VIEW STUDENTS =================
@app.route('/admin/students')
def admin_students():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    students = conn.execute(
        "SELECT uid, name, email FROM students"
    ).fetchall()
    conn.close()

    return render_template('admin_students.html', students=students)

# ================= ADMIN ADD STUDENT =================
@app.route('/admin/add-student', methods=['GET', 'POST'])
def admin_add_student():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        uid = request.form['uid']
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO students (uid, name, email, password) VALUES (?, ?, ?, ?)",
            (uid, name, email, password)
        )
        conn.commit()
        log_admin_action(f"Added student: {uid}")
        conn.close()

        return redirect(url_for('admin_students'))

    return render_template('admin_add_student.html')

# ================= ADMIN EDIT STUDENT =================
@app.route('/admin/edit-student/<uid>', methods=['GET', 'POST'])
def admin_edit_student(uid):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()

    student = conn.execute(
        "SELECT * FROM students WHERE uid=?",
        (uid,)
    ).fetchone()

    if not student:
        conn.close()
        return "Student not found"

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        conn.execute("""
            UPDATE students
            SET name=?, email=?, password=?
            WHERE uid=?
        """, (name, email, password, uid))

        conn.commit()
        conn.close()

        return redirect(url_for('admin_students'))

    conn.close()
    return render_template(
        'admin_edit_student.html',
        student=student
    )
# ================= ADMIN ADD TEACHER =================
@app.route('/admin/add-teacher', methods=['GET', 'POST'])
def admin_add_teacher():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
    
        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO teachers (name, email, username, password) VALUES (?, ?, ?, ?)",
                (name, email, username, password)
            )
            conn.commit()
            log_admin_action(f"Added teacher: {username}")
        except sqlite3.IntegrityError:

            conn.close()
    return render_template(
        'admin_add_teacher.html',
        error="Email or Username already exists"
    )
# ================= ADMIN VIEW TEACHERS =================
@app.route('/admin/teachers')
def admin_teachers():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    teachers = conn.execute(
        "SELECT id, name, email, username FROM teachers"
    ).fetchall()
    conn.close()

    return render_template(
        'admin_teachers.html',
        teachers=teachers
    )


# =========================================================
# ================= TEACHER DASHBOARD =====================
# =========================================================
@app.route('/teacher-dashboard')
def teacher_dashboard():
    if not session.get('teacher_logged_in'):
        return redirect(url_for('teacher_login'))

    selected_class = request.args.get("class")  # e.g. 715-A
    today = date.today().strftime("%Y-%m-%d")

    conn = get_db_connection()

    teacher_username = session.get("teacher_username")

    classes = conn.execute("""
    SELECT DISTINCT class
    FROM teacher_timetable
    WHERE teacher_username = ?
    ORDER BY class
    """, (teacher_username,)).fetchall()

    classes = [c["class"] for c in classes]


    if selected_class:
        present = conn.execute("""
            SELECT COUNT(*) FROM daily_attendance
            WHERE date=? AND status='Present' AND class=?
        """, (today, selected_class)).fetchone()[0]

        absent = conn.execute("""
            SELECT COUNT(*) FROM daily_attendance
            WHERE date=? AND status='Absent' AND class=?
        """, (today, selected_class)).fetchone()[0]

        late = conn.execute("""
            SELECT COUNT(*) FROM daily_attendance
            WHERE date=? AND status='Late' AND class=?
        """, (today, selected_class)).fetchone()[0]

        trend = conn.execute("""
            SELECT date, COUNT(*) AS count
            FROM daily_attendance
            WHERE status='Present' AND class=?
            GROUP BY date
            ORDER BY date DESC
            LIMIT 7
        """, (selected_class,)).fetchall()
    else:
        present = absent = late = 0
        trend = []

    conn.close()

    total = present + absent + late
    rate = round((present / total) * 100, 2) if total else 0

    trend_dates = [r["date"] for r in reversed(trend)]
    trend_counts = [r["count"] for r in reversed(trend)]

    return render_template(
        "teacher_dashboard.html",
        classes=classes,
        selected_class=selected_class,
        present=present,
        absent=absent,
        late=late,
        rate=rate,
        trend_dates=trend_dates,
        trend_counts=trend_counts
    )




# =========================================================
# ================= MARK ATTENDANCE =======================
# =========================================================
@app.route('/teacher/mark-attendance', methods=['GET', 'POST'])
def mark_attendance():
    if 'teacher_logged_in' not in session:
        return redirect(url_for('teacher_login'))

    conn = get_db_connection()

    # ✅ GET values FIRST (for both GET & POST)
    subject = request.args.get('subject') or request.form.get('subject')
    class_name = request.args.get('class') or request.form.get('class')
    date_val = request.form.get('date') or date.today().strftime("%Y-%m-%d")

    # Fetch students
    class_no, section = class_name.split("-")

    students = conn.execute("""
    SELECT s.uid, s.name
    FROM students s
    JOIN student_class sc
    ON s.uid = sc.student_uid
    WHERE sc.class = ?
    AND sc.section = ?
    ORDER BY s.uid
     """, (class_no, section)).fetchall()

    # ================= POST =================
    if request.method == 'POST':

        # 🔍 Smart validation
        existing = conn.execute("""
            SELECT COUNT(*) FROM daily_attendance
            WHERE subject = ?
              AND class = ?
              AND date = ?
        """, (subject, class_name, date_val)).fetchone()[0]

        if existing > 0:
            conn.close()
            return render_template(
                'mark_attendance.html',
                students=students,
                selected_subject=subject,
                selected_class=class_name,
                selected_date=date_val,
                error="⚠ Attendance already marked for this subject and class today."
            )

        # ✅ Insert attendance
        for s in students:
            status = request.form.get(s['uid'], 'Absent')
            conn.execute("""
                INSERT INTO daily_attendance
                (student_uid, subject, class, date, status)
                VALUES (?, ?, ?, ?, ?)
            """, (s['uid'], subject, class_name, date_val, status))

        conn.commit()
        conn.close()

        return redirect(url_for('teacher_dashboard'))

    # ================= GET =================
    conn.close()
    return render_template(
        'mark_attendance.html',
        students=students,
        selected_subject=subject,
        selected_class=class_name,
        selected_date=date_val
    )

# =========================================================
# ===== a ============ ATTENDANCE HISTORY ====================
# =========================================================
@app.route('/teacher/history')
def attendance_history():
    conn = get_db_connection()
    records = conn.execute("""
        SELECT * FROM daily_attendance
        ORDER BY date DESC
    """).fetchall()
    conn.close()

    return render_template('attendance_history.html', records=records)

@app.route('/teacher/edit-attendance/<int:id>', methods=['GET', 'POST'])
def edit_attendance(id):

    if not session.get('teacher_logged_in'):
        return redirect(url_for('teacher_login'))

    conn = get_db_connection()

    record = conn.execute(
        "SELECT * FROM daily_attendance WHERE id=?",
        (id,)
    ).fetchone()

    if not record:
        conn.close()
        return "Record not found"

    #  DATE RESTRICTION (3 days)
    record_date = datetime.strptime(record['date'], "%Y-%m-%d")
    today = datetime.today()

    diff = (today - record_date).days

    if diff > 3:
        conn.close()
        return "❌ You can only edit attendance within 3 days"

    # ================= UPDATE =================
    if request.method == 'POST':
        new_status = request.form['status']

        conn.execute("""
            UPDATE daily_attendance
            SET status=?
            WHERE id=?
        """, (new_status, id))

        conn.commit()
        conn.close()

        return redirect(url_for('attendance_history'))

    conn.close()
    return render_template('edit_attendance.html', record=record)

# ================= VIEW ALL STUDENTS =====================
@app.route('/teacher/students')
def teacher_students():
    if not session.get('teacher_logged_in'):
        return redirect(url_for('teacher_login'))

    class_q = request.args.get("class")  # 715-A

    conn = get_db_connection()

    if class_q:
        class_no, section = class_q.split("-")
        students = conn.execute("""
            SELECT s.uid, s.name, s.email
            FROM students s
            JOIN student_class sc ON s.uid = sc.student_uid
            WHERE sc.class=? AND sc.section=?
            ORDER BY s.uid
        """, (class_no, section)).fetchall()
    else:
        students = []

    classes = conn.execute("""
        SELECT DISTINCT class || '-' || section AS cls
        FROM student_class
        ORDER BY cls
    """).fetchall()
    classes = [c["cls"] for c in classes]

    conn.close()

    return render_template(
        "teacher_students.html",
        students=students,
        classes=classes,
        selected_class=class_q
    )


# =========================================================
# ================= LOW ATTENDANCE STUDENTS ===============
# =========================================================
@app.route('/teacher/low-attendance')
def low_attendance_students():
    conn = get_db_connection()
    students = conn.execute("""
    SELECT
        s.uid,
        s.name,
        ROUND(
            SUM(CASE WHEN d.status='Present' THEN 1 ELSE 0 END) * 100.0
            / COUNT(*),
            2
        ) AS percentage
    FROM students s
    JOIN daily_attendance d ON s.uid = d.student_uid
    GROUP BY s.uid
    HAVING percentage < 75
    """).fetchall()
    conn.close()

    return render_template(
        'low_attendance.html',
        students=students
    )
# ================= CLASS ATTENDANCE REPORT =================
@app.route('/teacher/class-report')
def class_attendance_report():
    conn = get_db_connection()

    data = conn.execute("""
        SELECT 
            class,
            COUNT(*) AS total_students,
            SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) AS present_count
        FROM daily_attendance
        GROUP BY class
    """).fetchall()

    conn.close()

    return render_template(
        'class_report.html',
        data=data
    )
# ================= SUBJECT ATTENDANCE REPORT =================
@app.route('/teacher/subject-report')
def subject_attendance_report():
    conn = get_db_connection()

    data = conn.execute("""
        SELECT 
            subject,
            COUNT(*) AS total_students,
            SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) AS present_count
        FROM daily_attendance
        GROUP BY subject
    """).fetchall()

    conn.close()

    return render_template(
        'subject_report.html',
        data=data
    )


# ================= FORGOT PASSWORD =================
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        uid = request.form['uid']
        email = request.form['email']

        conn = get_db_connection()
        student = conn.execute(
            "SELECT * FROM students WHERE uid=? AND email=?",
            (uid, email)
        ).fetchone()
        conn.close()

        if not student:
            return render_template(
                'forgot_password.html',
                error="Invalid UID or Email"
            )

        otp = random.randint(100000, 999999)
        otp_store[uid] = otp

        msg = Message(
            "Smart Attendance – Password Reset OTP",
            sender=app.config['MAIL_USERNAME'],
            recipients=[email]
        )
        msg.body = f"Your OTP is: {otp}"

        mail.send(msg)

        return redirect(url_for('reset_password', uid=uid))

    return render_template('forgot_password.html')


# ================= RESET PASSWORD =================
@app.route('/reset-password/<uid>', methods=['GET', 'POST'])
def reset_password(uid):
    if request.method == 'POST':
        otp_entered = request.form['otp']
        new_password = request.form['new_password']

        if uid not in otp_store:
            return render_template(
                'reset_password.html',
                error="OTP expired. Try again."
            )

        if str(otp_store[uid]) != otp_entered:
            return render_template(
                'reset_password.html',
                error="Invalid OTP"
            )

        conn = get_db_connection()
        conn.execute(
            "UPDATE students SET password=? WHERE uid=?",
            (new_password, uid)
        )
        conn.commit()
        conn.close()

        otp_store.pop(uid)
        return redirect(url_for('student_login'))

    return render_template('reset_password.html')


# ================= STUDENT DASHBOARD =====================
@app.route('/student-dashboard/<uid>')
def student_dashboard(uid):
    conn = get_db_connection()

    student = conn.execute(
        "SELECT * FROM students WHERE uid=?",
        (uid,)
    ).fetchone()

    attendance_rows = conn.execute("""
    SELECT
        subject,
        COUNT(*) AS total_classes,
        SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) AS attended_classes
    FROM daily_attendance
    WHERE student_uid=?
    GROUP BY subject
    """, (uid,)).fetchall()

    conn.close()

    attendance = [dict(r) for r in attendance_rows]
    total_classes = sum(r['total_classes'] for r in attendance)
    total_attended = sum(r['attended_classes'] for r in attendance)

    percent = round((total_attended / total_classes) * 100, 2) if total_classes else 0

    status = "Eligible" if percent >= 75 else "Not Eligible"
    status_class = "status-good" if percent >= 75 else "status-bad"

    return render_template(
        'student_dashboard.html',
        student=student,
        attendance=attendance,
        total_classes=total_classes,
        total_attended=total_attended,
        overall_percentage=percent,
        eligibility_status=status,
        status_class=status_class
    )
# ================= STUDENT PERFORMANCE TABLE =================
@app.route('/teacher/students-performance')
def students_performance():
    conn = get_db_connection()

    students = conn.execute("""
        SELECT
            s.uid,
            s.name,
            ROUND(
                SUM(CASE WHEN d.status='Present' THEN 1 ELSE 0 END) * 100.0
                / COUNT(*),
                2
            ) AS percentage
        FROM students s
        JOIN daily_attendance d
        ON s.uid = d.student_uid
        GROUP BY s.uid
        ORDER BY percentage DESC
    """).fetchall()

    conn.close()

    return render_template(
        'students_performance.html',
        students=students
    )
# ================= STUDENT REPORTS PAGE =================
@app.route('/reports/<uid>')
def reports_page(uid):
    return redirect(url_for('download_report', uid=uid))


# ================= PDF REPORT DOWNLOAD =================
@app.route('/download-report/<uid>')
def download_report(uid):
    conn = get_db_connection()

    student = conn.execute(
        "SELECT * FROM students WHERE uid=?",
        (uid,)
    ).fetchone()

    attendance = conn.execute("""
    SELECT
        subject,
        COUNT(*) AS total_classes,
        SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) AS attended_classes
    FROM daily_attendance
    WHERE student_uid=?
    GROUP BY subject
    """, (uid,)).fetchall()

    conn.close()

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, y, "Attendance Report")
    y -= 30

    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, y, f"Student UID: {student['uid']}")
    y -= 20
    pdf.drawString(50, y, f"Student Name: {student['name']}")
    y -= 30

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(50, y, "Subject")
    pdf.drawString(250, y, "Total")
    pdf.drawString(330, y, "Attended")
    pdf.drawString(430, y, "%")
    y -= 15

    pdf.setFont("Helvetica", 11)

    total_classes = 0
    total_attended = 0

    for row in attendance:
        percent = (row["attended_classes"] / row["total_classes"]) * 100

        pdf.drawString(50, y, row["subject"])
        pdf.drawString(250, y, str(row["total_classes"]))
        pdf.drawString(330, y, str(row["attended_classes"]))
        pdf.drawString(430, y, f"{percent:.1f}%")

        total_classes += row["total_classes"]
        total_attended += row["attended_classes"]
        y -= 18

    overall = (total_attended / total_classes) * 100 if total_classes else 0

    y -= 20
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, f"Overall Attendance: {overall:.2f}%")

    status = "ELIGIBLE" if overall >= 75 else "NOT ELIGIBLE"
    y -= 20
    pdf.drawString(50, y, f"Eligibility Status: {status}")

    pdf.showPage()
    pdf.save()

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"Attendance_Report_{uid}.pdf",
        mimetype='application/pdf'
    )
# ================= FACE LOGIN =================
@app.route('/student-face-login')
def student_face_login():

    cam = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
    if not cam.isOpened():
        return "Camera access failed"

    frame = None

    # Warm up camera & capture multiple frames
    for _ in range(10):
        ret, temp = cam.read()
        if ret:
            frame = temp

    cam.release()

    if frame is None:
        return "Failed to capture image"

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    faces = face_recognition.face_locations(rgb)
    encodings = face_recognition.face_encodings(rgb, faces)

    if not encodings:
        return "No face detected. Try again."

    for encoding in encodings:
        matches = face_recognition.compare_faces(
            KNOWN_FACES, encoding, tolerance=0.5
        )

        if True in matches:
            uid = KNOWN_IDS[matches.index(True)]
            return redirect(url_for('student_dashboard', uid=uid))

    return "Face not recognized"

# ================= ADMIN DELETE STUDENT =================
@app.route('/admin/delete-student/<uid>')
def admin_delete_student(uid):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    conn.execute("DELETE FROM students WHERE uid=?", (uid,))
    conn.commit()
    log_admin_action(f"Deleted student: {uid}")
    conn.close()

    return redirect(url_for('admin_students'))
# ================= ADMIN DELETE TEACHER =================
@app.route('/admin/delete-teacher/<int:id>')
def admin_delete_teacher(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    conn.execute("DELETE FROM teachers WHERE id=?", (id,))
    conn.commit()
    log_admin_action(f"Deleted teacher with ID: {id}")
    conn.close()

    return redirect(url_for('admin_teachers'))

@app.route('/admin/add-teacher-timetable', methods=['GET', 'POST'])
def admin_add_teacher_timetable():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()

    teachers = conn.execute(
        "SELECT username, name FROM teachers"
    ).fetchall()

    if request.method == 'POST':
        teacher_username = request.form['teacher_username']
        day = request.form['day']
        subject = request.form['subject']
        class_name = request.form['class']
        start_time = request.form['start_time']
        end_time = request.form['end_time']

        conn.execute("""
            INSERT INTO teacher_timetable
            (teacher_username, day, subject, class, start_time, end_time)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (teacher_username, day, subject, class_name, start_time, end_time))

        conn.commit()
        conn.close()
        return redirect('/admin/teacher-timetable')

    conn.close()
    return render_template(
        'admin_add_teacher_timetable.html',
        teachers=teachers
    )


# ================= LOGOUT (ALL ROLES) =================
@app.route("/ai-chat", methods=["POST"])
def ai_chat():
    data = request.get_json()
    user_message = data.get("message", "").lower()
    uid = data.get("uid")

    if not uid:
        return jsonify({"reply": "Student not identified."})

    # ================= REGEX PATTERNS (ONLY ONCE ✅) =================
    attendance_pattern = r"(attendance|percentage|percent|my attendance|overall)"
    total_attended_pattern = r"(total.*(attend|present)|how many present)"
    total_classes_pattern = r"(total classes|how many classes|classes)"
    eligibility_pattern = r"(eligible|eligibility|can i sit)"
    highest_pattern = r"(highest|best|maximum|top)"
    weakest_pattern = r"(lowest|weak|minimum|poor)"
    future_miss_pattern = r"(miss|skip|bunk).*(\d+)"
    future_attend_pattern = r"(attend).*(\d+)"
    subject_pattern = r"(maths|mathematics|java|os|operating system|software engineering|se|data analytics|dsa)"

    conn = get_db_connection()

    rows = conn.execute("""
        SELECT
            subject,
            COUNT(*) AS total_classes,
            SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) AS attended_classes
        FROM daily_attendance
        WHERE student_uid=?
        GROUP BY subject
    """, (uid,)).fetchall()

    conn.close()

    if not rows:
        return jsonify({"reply": "No attendance data found."})

    attendance = [dict(r) for r in rows]

    total_classes = sum(r["total_classes"] for r in attendance)
    total_attended = sum(r["attended_classes"] for r in attendance)

    overall = round((total_attended / total_classes) * 100, 2) if total_classes else 0
    eligible = "Eligible" if overall >= 75 else "Not Eligible"

    # ================= FORMULA =================
    if "formula" in user_message or "calculate" in user_message:
        return jsonify({"reply": "(attended / total) × 100"})

    # ================= SUBJECT FUTURE =================
    subject_match = re.search(subject_pattern, user_message)
    number_match = re.search(r"(\d+)", user_message)

    if subject_match and number_match:
        subject_map = {
            "maths": "Mathematics",
            "mathematics": "Mathematics",
            "java": "Java",
            "os": "Operating System",
            "operating system": "Operating System",
            "software engineering": "Software Engineering",
            "se": "Software Engineering",
            "data analytics": "Data Analytics",
            "dsa": "Data Structure and Algorithm"
        }

        subject = subject_map.get(subject_match.group(1))
        count = int(number_match.group(1))

        s = next((x for x in attendance if x["subject"].lower() == subject.lower()), None)
        if not s:
            return jsonify({"reply": f"No data for {subject}."})

        total = s["total_classes"]
        attended = s["attended_classes"]

        if "miss" in user_message or "bunk" in user_message:
            new_percent = round((attended / (total + count)) * 100, 2)
        else:
            new_percent = round(((attended + count) / (total + count)) * 100, 2)

        status = "Eligible" if new_percent >= 75 else "Not Eligible"

        return jsonify({"reply": f"{subject}: {new_percent}% → {status}"})

    # ================= OVERALL FUTURE =================
    miss_match = re.search(future_miss_pattern, user_message)
    if miss_match:
        n = int(miss_match.group(2))
        new_percent = round((total_attended / (total_classes + n)) * 100, 2)
        return jsonify({"reply": f"After missing {n}: {new_percent}% → Not Eligible"})

    attend_match = re.search(future_attend_pattern, user_message)
    if attend_match:
        n = int(attend_match.group(2))
        new_percent = round(((total_attended + n) / (total_classes + n)) * 100, 2)
        return jsonify({"reply": f"After attending {n}: {new_percent}% → Eligible"})
    # ================= SMART QUESTIONS (MOVE UP 🔥) =================
    if "java" in user_message:
        s = next((x for x in attendance if x["subject"].lower() == "java"), None)
    if s:
        percent = round((s["attended_classes"] / s["total_classes"]) * 100, 2)
        return jsonify({
            "reply": f"Your Java attendance is {percent}%"
        })

    if "my attendance" in user_message:
        return jsonify({
        "reply": f"Your overall attendance is {overall}% → {eligible}"
    })

    # ================= BASIC =================
    if match(total_classes_pattern, user_message):
        return jsonify({"reply": f"Total classes: {total_classes}"})

    if match(total_attended_pattern, user_message):
        return jsonify({"reply": f"Total attended: {total_attended}"})

    if match(eligibility_pattern, user_message):
        return jsonify({"reply": f"Eligibility: {eligible}"})

    if match(highest_pattern, user_message):
        s = max(attendance, key=lambda x: x["attended_classes"] / x["total_classes"])
        percent = round((s["attended_classes"] / s["total_classes"]) * 100, 2)
        return jsonify({"reply": f"Highest: {s['subject']} ({percent}%)"})

    if match(weakest_pattern, user_message):
        s = min(attendance, key=lambda x: x["attended_classes"] / x["total_classes"])
        percent = round((s["attended_classes"] / s["total_classes"]) * 100, 2)
        return jsonify({"reply": f"Weakest: {s['subject']} ({percent}%)"})

    if match(attendance_pattern, user_message):
        return jsonify({"reply": f"Overall: {overall}% → {eligible}"})

    if "improve" in user_message or "focus" in user_message:
        weak = min(attendance, key=lambda x: x["attended_classes"] / x["total_classes"])
        percent = round((weak["attended_classes"] / weak["total_classes"]) * 100, 2)
        return jsonify({
            "reply": f"Focus on {weak['subject']} ({percent}%). Attend more classes."
        })
    # ================= GEMINI FALLBACK =================
    if client is None:
        return jsonify({"reply": "AI service unavailable"})

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_message
        )
        return jsonify({"reply": response.text})

    except Exception as e:
        print("AI ERROR:", e)
        return jsonify({"reply": "AI service unavailable"})



@app.route("/gemini-test")
def gemini_test():
    if client is None:
        return "Gemini client is not configured", 503

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Say hello in one sentence"
    )
    return response.text
@app.route('/teacher/timetable')
def teacher_timetable():
    if not session.get('teacher_logged_in'):
        return redirect(url_for('teacher_login'))

    teacher_username = session.get('teacher_username')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT day, subject, class, start_time, end_time
        FROM teacher_timetable
        WHERE teacher_username = ?
        ORDER BY
          CASE day
            WHEN 'Monday' THEN 1
            WHEN 'Tuesday' THEN 2
            WHEN 'Wednesday' THEN 3
            WHEN 'Thursday' THEN 4
            WHEN 'Friday' THEN 5
          END,
          start_time
    """, (teacher_username,))

    rows = cursor.fetchall()
    conn.close()

    timetable = []
    for r in rows:
        timetable.append({
            "day": r["day"],
            "subject": r["subject"],
            "class": r["class"],
            "start_time": r["start_time"],
            "end_time": r["end_time"],
        })

    today = datetime.now().strftime("%A")  # Monday, Tuesday…
    
    now = datetime.now()

    return render_template(
    "teacher_timetable.html",
    timetable=timetable,
    today=today,
    now_time=now.strftime("%H:%M"),
    now_ts=now.timestamp()
)




@app.route('/admin/teacher-timetable')
def admin_teacher_timetable():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()

    teachers = conn.execute("""
        SELECT username, name FROM teachers
    """).fetchall()

    timetable = conn.execute("""
        SELECT tt.*, t.name
        FROM teacher_timetable tt
        JOIN teachers t
        ON tt.teacher_username = t.username
        ORDER BY t.name, tt.day, tt.start_time
    """).fetchall()

    conn.close()

    return render_template(
        'admin_teacher_timetable.html',
        teachers=teachers,
        timetable=timetable
    )
@app.route('/admin/add-timetable', methods=['POST'])
def admin_add_timetable():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    teacher_username = request.form['teacher_username']
    day = request.form['day']
    subject = request.form['subject']
    class_name = request.form['class']
    start_time = request.form['start_time']
    end_time = request.form['end_time']

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO teacher_timetable
        (teacher_username, day, subject, class, start_time, end_time)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (teacher_username, day, subject, class_name, start_time, end_time))

    conn.commit()
    log_admin_action(f"Added timetable for {teacher_username} ({class_name})")
    conn.close()

    return redirect(url_for('admin_teacher_timetable'))

@app.route('/admin/edit-timetable/<int:id>', methods=['GET', 'POST'])
def admin_edit_timetable(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()

    timetable = conn.execute("""
        SELECT * FROM teacher_timetable WHERE id = ?
    """, (id,)).fetchone()

    if not timetable:
        conn.close()
        return "Timetable entry not found"

    if request.method == 'POST':
        day = request.form['day']
        subject = request.form['subject']
        class_name = request.form['class']
        start_time = request.form['start_time']
        end_time = request.form['end_time']

        conn.execute("""
            UPDATE teacher_timetable
            SET day=?, subject=?, class=?, start_time=?, end_time=?
            WHERE id=?
        """, (day, subject, class_name, start_time, end_time, id))

        conn.commit()
        log_admin_action(f"Updated timetable ID: {id}")
        conn.close()
        return redirect(url_for('admin_teacher_timetable'))

    conn.close()
    return render_template(
        'admin_edit_teacher_timetable.html',
        timetable=timetable
    )

@app.route('/admin/logs')
def admin_logs():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    rows = conn.execute("""
        SELECT * FROM admin_logs
        ORDER BY timestamp DESC
    """).fetchall()
    conn.close()

    ist = timezone(timedelta(hours=5, minutes=30))
    logs = []

    for r in rows:
        utc_time = datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S")
        utc_time = utc_time.replace(tzinfo=timezone.utc)
        ist_time = utc_time.astimezone(ist)

        logs.append({
            "id": r["id"],
            "admin_username": r["admin_username"],
            "action": r["action"],
            "timestamp": ist_time.strftime("%Y-%m-%d %H:%M:%S")
        })

    return render_template("admin_logs.html", logs=logs)

@app.route('/attendance/<uid>')
def student_attendance(uid):
    conn = get_db_connection()

    student = conn.execute(
        "SELECT * FROM students WHERE uid=?",
        (uid,)
    ).fetchone()

    attendance_rows = conn.execute("""
    SELECT
        subject,
        COUNT(*) AS total_classes,
        SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) AS attended_classes
    FROM daily_attendance
    WHERE student_uid=?
    GROUP BY subject
    """, (uid,)).fetchall()

    conn.close()

    attendance = [dict(r) for r in attendance_rows]

    data = []
    total_delivered = 0
    total_attended = 0

    for row in attendance:
        total = row["total_classes"]
        attended = row["attended_classes"]
        percent = round((attended / total) * 100, 2) if total else 0

        total_delivered += total
        total_attended += attended

        data.append({
            "subject": row["subject"],
            "total": total,
            "attended": attended,
            "percentage": percent
        })

    overall_percentage = round(
        (total_attended / total_delivered) * 100, 2
    ) if total_delivered else 0

    return render_template(
        "student_attendance.html",
        student=student,
        attendance=data,
        overall_percentage=overall_percentage
    )



# ================= LOGOUT (ALL ROLES) =================
@app.route('/logout')
def logout():
    if session.get('admin_logged_in'):
        log_admin_action("Admin logged out")

    session.clear()
    return redirect(url_for('home'))

# ================= RUN =================
if __name__ == '__main__':
    app.run(debug=False, use_reloader=False)
