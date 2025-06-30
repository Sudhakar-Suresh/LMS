from flask_login import UserMixin
from datetime import datetime
from app import db, login_manager


class UserRole:
    ADMIN = 'admin'
    INSTRUCTOR = 'instructor'
    STUDENT = 'student'
    GUEST = 'guest'
    PARENT = 'parent'


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship with courses (for instructors)
    courses_teaching = db.relationship(
        'Course', backref='instructor', lazy=True)

    # Relationship with enrollments (for students)
    enrollments = db.relationship('Enrollment', backref='student', lazy=True)

    # Relationship for parents - specify foreign keys to avoid ambiguity
    parent_of = db.relationship('ParentStudent',
                                foreign_keys='ParentStudent.parent_id',
                                backref='parent', lazy=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.role}')"


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    instructor_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship with enrollments
    enrollments = db.relationship('Enrollment', backref='course', lazy=True)

    def __repr__(self):
        return f"Course('{self.title}')"


class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey(
        'course.id'), nullable=False)
    enrollment_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"Enrollment(Student ID: {self.student_id}, Course ID: {self.course_id})"


class ParentStudent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    student_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Explicitly define the relationship to avoid ambiguity
    student = db.relationship('User', foreign_keys=[
                              student_id], backref='parent_links')

    def __repr__(self):
        return f"ParentStudent(Parent ID: {self.parent_id}, Student ID: {self.student_id})"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
