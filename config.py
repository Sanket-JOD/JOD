import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///attendance.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Department Configuration
    DEPARTMENT = 'CS Department'
    DIVISIONS = ['A', 'B', 'C', 'D', 'E', 'F']
    SUBJECTS = ['SFT', 'ML', 'ETI', 'MAN', 'CPE', 'MAD']
    STUDENTS_PER_DIVISION = 40
    SESSIONS_PER_DAY = 6
    
    # Attendance Threshold
    LOW_ATTENDANCE_THRESHOLD = 75.0