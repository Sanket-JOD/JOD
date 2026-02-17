from flask import Flask
from models import db, Staff, Student
from config import Config

def init_database():
    """Initialize database with tables and sample data"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("✓ Database tables created successfully")
        
        # Check if staff already exists
        if not Staff.query.first():
            # Create default staff account
            admin = Staff(
                name='Admin Staff',
                email='admin@cs.dept',
                department='CS Department'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            print("✓ Default staff account created (admin@cs.dept / admin123)")
        
        # Check if students already exist
        if not Student.query.first():
            # Create 240 students (40 per division)
            divisions = Config.DIVISIONS
            students = []
            
            for division in divisions:
                for i in range(1, Config.STUDENTS_PER_DIVISION + 1):
                    roll_no = f"{division}{i:02d}"
                    student = Student(
                        roll_no=roll_no,
                        name=f"Student {roll_no}",
                        division=division
                    )
                    students.append(student)
            
            db.session.bulk_save_objects(students)
            print(f"✓ Created {len(students)} students across {len(divisions)} divisions")
        
        db.session.commit()
        print("✓ Database initialization completed successfully!")
        print("\n" + "="*50)
        print("Login Credentials:")
        print("Email: admin@cs.dept")
        print("Password: admin123")
        print("="*50 + "\n")

if __name__ == '__main__':
    init_database()