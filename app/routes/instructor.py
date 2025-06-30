from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.user import User, UserRole, Course, Enrollment
from functools import wraps

instructor = Blueprint('instructor', __name__, url_prefix='/instructor')

# Instructor required decorator


def instructor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != UserRole.INSTRUCTOR:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


@instructor.route('/dashboard')
@login_required
@instructor_required
def dashboard():
    # Get instructor's courses
    courses = Course.query.filter_by(instructor_id=current_user.id).all()

    # Get student count for each course
    course_stats = []
    for course in courses:
        student_count = Enrollment.query.filter_by(course_id=course.id).count()
        course_stats.append({
            'course': course,
            'student_count': student_count
        })

    return render_template('instructor/dashboard.html', course_stats=course_stats)


@instructor.route('/courses')
@login_required
@instructor_required
def courses():
    courses = Course.query.filter_by(instructor_id=current_user.id).all()
    return render_template('instructor/courses.html', courses=courses)


@instructor.route('/course/<int:course_id>')
@login_required
@instructor_required
def course_details(course_id):
    course = Course.query.get_or_404(course_id)

    # Ensure instructor owns this course
    if course.instructor_id != current_user.id:
        flash('You do not have permission to view this course.', 'danger')
        return redirect(url_for('instructor.courses'))

    # Get enrolled students
    enrollments = Enrollment.query.filter_by(course_id=course_id).all()
    students = []
    for enrollment in enrollments:
        student = User.query.get(enrollment.student_id)
        if student:
            students.append(student)

    return render_template('instructor/course_details.html', course=course, students=students)
