from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from models import db, Staff, Student, Attendance
from config import Config
from datetime import datetime, date
from sqlalchemy import func, case

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

# Helper function to check if user is logged in
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'staff_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def index():
    if 'staff_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        staff = Staff.query.filter_by(email=email).first()
        
        if staff and staff.check_password(password):
            session['staff_id'] = staff.id
            session['staff_name'] = staff.name
            session['staff_email'] = staff.email
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    # Get total students
    total_students = Student.query.count()
    
    # Get total divisions
    total_divisions = len(Config.DIVISIONS)
    
    # Get today's attendance rate
    today = date.today()
    today_attendance = Attendance.query.filter_by(date=today).all()
    
    if today_attendance:
        present_count = sum(1 for a in today_attendance if a.status == 'Present')
        attendance_rate = (present_count / len(today_attendance)) * 100 if today_attendance else 0
    else:
        attendance_rate = 0
    
    # Get students with low attendance
    low_attendance_students = get_low_attendance_students()
    low_attendance_count = len(low_attendance_students)
    
    return render_template('dashboard.html',
                         total_students=total_students,
                         total_divisions=total_divisions,
                         attendance_rate=round(attendance_rate, 1),
                         low_attendance_count=low_attendance_count,
                         subjects=Config.SUBJECTS,
                         sessions_per_day=Config.SESSIONS_PER_DAY,
                         students_per_division=Config.STUDENTS_PER_DIVISION)


@app.route('/mark-attendance', methods=['GET', 'POST'])
@login_required
def mark_attendance():
    if request.method == 'POST':
        division = request.form.get('division')
        subject = request.form.get('subject')
        attendance_date = request.form.get('date')
        student_statuses = request.form.getlist('status')
        
        # Convert date string to date object
        attendance_date = datetime.strptime(attendance_date, '%Y-%m-%d').date()
        
        # Get all students in the division
        students = Student.query.filter_by(division=division).order_by(Student.roll_no).all()
        
        # Delete existing attendance for this date, division, and subject
        Attendance.query.filter_by(
            date=attendance_date,
            division=division,
            subject=subject
        ).delete()
        
        # Save new attendance
        for idx, student in enumerate(students):
            status = student_statuses[idx] if idx < len(student_statuses) else 'Absent'
            
            attendance = Attendance(
                student_id=student.id,
                date=attendance_date,
                division=division,
                subject=subject,
                status=status,
                marked_by=session['staff_id']
            )
            db.session.add(attendance)
        
        db.session.commit()
        flash(f'Attendance saved successfully for Division {division} - {subject}', 'success')
        return redirect(url_for('mark_attendance'))
    
    # GET request
    divisions = Config.DIVISIONS
    subjects = Config.SUBJECTS
    today = date.today().strftime('%Y-%m-%d')
    
    return render_template('mark_attendance.html',
                         divisions=divisions,
                         subjects=subjects,
                         today=today)


@app.route('/api/get-students/<division>')
@login_required
def get_students(division):
    students = Student.query.filter_by(division=division).order_by(Student.roll_no).all()
    return jsonify([{
        'id': s.id,
        'roll_no': s.roll_no,
        'name': s.name
    } for s in students])


@app.route('/reports')
@login_required
def reports():
    division_filter = request.args.get('division', 'all')
    
    # Get all students
    if division_filter != 'all':
        students = Student.query.filter_by(division=division_filter).order_by(Student.roll_no).all()
    else:
        students = Student.query.order_by(Student.division, Student.roll_no).all()
    
    # Calculate attendance for each student
    student_data = []
    for student in students:
        total_sessions = Attendance.query.filter_by(student_id=student.id).count()
        present_sessions = Attendance.query.filter_by(student_id=student.id, status='Present').count()
        absent_sessions = total_sessions - present_sessions
        
        attendance_percentage = (present_sessions / total_sessions * 100) if total_sessions > 0 else 100
        
        student_data.append({
            'roll_no': student.roll_no,
            'name': student.name,
            'division': student.division,
            'total_sessions': total_sessions,
            'present': present_sessions,
            'absent': absent_sessions,
            'percentage': round(attendance_percentage, 2)
        })
    
    return render_template('reports.html',
                         students=student_data,
                         divisions=Config.DIVISIONS,
                         selected_division=division_filter)


@app.route('/alerts')
@login_required
def alerts():
    low_attendance_students = get_low_attendance_students()
    
    return render_template('alerts.html',
                         students=low_attendance_students,
                         threshold=Config.LOW_ATTENDANCE_THRESHOLD)


def get_low_attendance_students():
    """Helper function to get students with attendance below threshold"""
    students = Student.query.all()
    low_attendance = []
    
    for student in students:
        total_sessions = Attendance.query.filter_by(student_id=student.id).count()
        
        if total_sessions > 0:
            present_sessions = Attendance.query.filter_by(student_id=student.id, status='Present').count()
            attendance_percentage = (present_sessions / total_sessions * 100)
            
            if attendance_percentage < Config.LOW_ATTENDANCE_THRESHOLD:
                # Determine criticality
                if attendance_percentage == 0:
                    criticality = 'Critical'
                elif attendance_percentage < 50:
                    criticality = 'Critical'
                else:
                    criticality = 'High'
                
                low_attendance.append({
                    'roll_no': student.roll_no,
                    'name': student.name,
                    'division': student.division,
                    'percentage': round(attendance_percentage, 2),
                    'criticality': criticality
                })
    
    # Sort by attendance percentage (lowest first)
    low_attendance.sort(key=lambda x: x['percentage'])
    
    return low_attendance


if __name__ == '__main__':
    app.run(debug=True)