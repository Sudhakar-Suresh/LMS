from app import create_app, db
from app.models.user import User, Course, Enrollment, ParentStudent, UserRole
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta


def init_db():
    app = create_app()
    with app.app_context():
        # Clear existing data
        db.drop_all()
        db.create_all()

        print("Creating sample users...")

        # Create admin user
        admin = User(
            username="admin",
            email="admin@example.com",
            password=generate_password_hash("admin123", method='sha256'),
            first_name="Admin",
            last_name="User",
            role=UserRole.ADMIN
        )
        db.session.add(admin)

        # Create instructor users
        instructor1 = User(
            username="instructor1",
            email="instructor1@example.com",
            password=generate_password_hash("instructor123", method='sha256'),
            first_name="John",
            last_name="Smith",
            role=UserRole.INSTRUCTOR
        )
        db.session.add(instructor1)

        instructor2 = User(
            username="instructor2",
            email="instructor2@example.com",
            password=generate_password_hash("instructor123", method='sha256'),
            first_name="Sarah",
            last_name="Johnson",
            role=UserRole.INSTRUCTOR
        )
        db.session.add(instructor2)

        # Create student users
        student1 = User(
            username="student1",
            email="student1@example.com",
            password=generate_password_hash("student123", method='sha256'),
            first_name="Michael",
            last_name="Brown",
            role=UserRole.STUDENT
        )
        db.session.add(student1)

        student2 = User(
            username="student2",
            email="student2@example.com",
            password=generate_password_hash("student123", method='sha256'),
            first_name="Emily",
            last_name="Davis",
            role=UserRole.STUDENT
        )
        db.session.add(student2)

        # Create parent user
        parent = User(
            username="parent",
            email="parent@example.com",
            password=generate_password_hash("parent123", method='sha256'),
            first_name="Robert",
            last_name="Brown",
            role=UserRole.PARENT
        )
        db.session.add(parent)

        # Create guest user
        guest = User(
            username="guest",
            email="guest@example.com",
            password=generate_password_hash("guest123", method='sha256'),
            first_name="Guest",
            last_name="User",
            role=UserRole.GUEST
        )
        db.session.add(guest)

        # Commit to get IDs
        db.session.commit()

        print("Creating sample courses...")

        # Create courses
        course1 = Course(
            title="Introduction to Programming",
            description="Learn the basics of programming using Python. This course covers variables, data types, control structures, functions, and more.",
            instructor_id=instructor1.id
        )
        db.session.add(course1)

        course2 = Course(
            title="Database Systems",
            description="Introduction to database design, SQL, and database management systems. Learn how to create, query, and manage relational databases.",
            instructor_id=instructor1.id
        )
        db.session.add(course2)

        course3 = Course(
            title="Advanced Algorithms",
            description="Study of advanced algorithms and data structures. Topics include graph algorithms, dynamic programming, and complexity analysis.",
            instructor_id=instructor2.id
        )
        db.session.add(course3)

        # Commit to get IDs
        db.session.commit()

        print("Creating enrollments...")

        # Create enrollments
        enrollment1 = Enrollment(
            student_id=student1.id,
            course_id=course1.id,
            enrollment_date=datetime.utcnow() - timedelta(days=30)
        )
        db.session.add(enrollment1)

        enrollment2 = Enrollment(
            student_id=student1.id,
            course_id=course2.id,
            enrollment_date=datetime.utcnow() - timedelta(days=15)
        )
        db.session.add(enrollment2)

        enrollment3 = Enrollment(
            student_id=student2.id,
            course_id=course1.id,
            enrollment_date=datetime.utcnow() - timedelta(days=20)
        )
        db.session.add(enrollment3)

        enrollment4 = Enrollment(
            student_id=student2.id,
            course_id=course3.id,
            enrollment_date=datetime.utcnow() - timedelta(days=10)
        )
        db.session.add(enrollment4)

        print("Creating parent-student relationships...")

        # Create parent-student relationship
        parent_student = ParentStudent(
            parent_id=parent.id,
            student_id=student1.id
        )
        db.session.add(parent_student)

        # Commit all changes
        db.session.commit()

        print("Database initialized successfully!")


if __name__ == "__main__":
    init_db()
