import os
import sqlite3
import random

# ================= DATABASE PATH =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

# ================= DATABASE CONNECTION =================
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# ================= TABLES =================

# STUDENTS
cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    uid TEXT PRIMARY KEY,
    name TEXT,
    email TEXT,
    password TEXT
)
""")

# SUBJECT-WISE ATTENDANCE (FOR STUDENT DASHBOARD)
cursor.execute("""
CREATE TABLE IF NOT EXISTS attendance (
    uid TEXT,
    subject TEXT,
    total_classes INTEGER,
    attended_classes INTEGER
)
""")

# DAILY ATTENDANCE (FOR TEACHER DASHBOARD)
cursor.execute("""
CREATE TABLE IF NOT EXISTS daily_attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_uid TEXT,
    subject TEXT,
    class TEXT,
    date TEXT,
    status TEXT
)
""")

# ================= CLEAR OLD DATA =================
cursor.execute("DELETE FROM attendance")
cursor.execute("DELETE FROM daily_attendance")
cursor.execute("DELETE FROM students")

# ================= STUDENTS =================
students = [
    ("24BCS10101", "Aarav", "ravisheokand161205@gmail.com", "1234"),
    ("24BCS10102", "Vivaan", "vivaan@gmail.com", "1234"),
    ("24BCS10103", "Aditya", "aditya@gmail.com", "1234"),
    ("24BCS10104", "Krishna", "krishna@gmail.com", "1234"),
    ("24BCS10105", "Rohan", "rohan@gmail.com", "1234"),
    ("24BCS10106", "Arjun", "arjun@gmail.com", "1234"),
    ("24BCS10107", "Kunal", "kunal@gmail.com", "1234"),
    ("24BCS10108", "Sahil", "sahil@gmail.com", "1234"),
    ("24BCS10109", "Ankit", "ankit@gmail.com", "1234"),
    ("24BCS10110", "Manish", "manish@gmail.com", "1234"),
    ("24BCS10111", "Rahul", "rahul@gmail.com", "1234"),
    ("24BCS10112", "Nikhil", "nikhil@gmail.com", "1234"),
    ("24BCS10113", "Ravi", "ravi161205@gmail.com", "1234"),
    ("24BCS10114", "Amit", "amit@gmail.com", "1234"),
    ("24BCS10115", "Suresh", "suresh@gmail.com", "1234"),
    ("24BCS10116", "Deepak", "deepak@gmail.com", "1234"),
    ("24BCS10117", "Vikas", "vikas@gmail.com", "1234"),
    ("24BCS10118", "Harsh", "harsh@gmail.com", "1234"),
    ("24BCS10119", "Yash", "yash@gmail.com", "1234"),
    ("24BCS10120", "Mohit", "mohit@gmail.com", "1234"),
    ("24BCS10121", "Puneet", "puneet@gmail.com", "1234"),
    ("24BCS10122", "Aakash", "aakash@gmail.com", "1234"),
    ("24BCS10123", "Dev", "dev@gmail.com", "1234"),
    ("24BCS10124", "Ishaan", "ishaan@gmail.com", "1234"),
    ("24BCS10125", "Rajat", "rajat@gmail.com", "1234"),
    ("24BCS10126", "Abhishek", "abhishek@gmail.com", "1234"),
    ("24BCS10127", "Shubham", "shubham@gmail.com", "1234"),
    ("24BCS10128", "Pranav", "pranav@gmail.com", "1234"),
    ("24BCS10129", "Siddharth", "siddharth@gmail.com", "1234"),
    ("24BCS10130", "Varun", "varun@gmail.com", "1234"),
    ("24BCS10040", "Sukhraj Singh", "sukhraj0027@gmail.com", "1234")
]

cursor.executemany(
    "INSERT INTO students VALUES (?, ?, ?, ?)",
    students
)

# ================= SUBJECTS =================
subjects = [
    ("Mathematics", 30),
    ("Java", 40),
    ("Data Structure and Algorithm", 45),
    ("Operating System", 35),
    ("Software Engineering", 32),
    ("Data Analytics", 28)
]

# ================= SUBJECT-WISE ATTENDANCE =================
for uid, _, _, _ in students:

    performance = random.choices(
        ["excellent", "good", "average", "low"],
        weights=[2, 4, 3, 1]
    )[0]

    for subject, total in subjects:
        if performance == "excellent":
            attended = random.randint(int(total * 0.85), total)
        elif performance == "good":
            attended = random.randint(int(total * 0.75), int(total * 0.85))
        elif performance == "average":
            attended = random.randint(int(total * 0.6), int(total * 0.75))
        else:
            attended = random.randint(int(total * 0.45), int(total * 0.6))

        cursor.execute(
            "INSERT INTO attendance VALUES (?, ?, ?, ?)",
            (uid, subject, total, attended)
        )

# ================= SAVE =================
conn.commit()
conn.close()

print("✅ Database seeded successfully with students, subject attendance & daily attendance support")
