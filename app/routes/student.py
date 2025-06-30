from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.user import User, UserRole, Course, Enrollment
from functools import wraps

student = Blueprint('student', __name__, url_prefix='/student')

# Student required decorator


def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != UserRole.STUDENT:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


@student.route('/dashboard')
@login_required
@student_required
def dashboard():
    # Get student's enrollments
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()

    # Get course details
    courses = []
    for enrollment in enrollments:
        course = Course.query.get(enrollment.course_id)
        if course:
            instructor = User.query.get(course.instructor_id)
            courses.append({
                'course': course,
                'instructor': instructor,
                'enrollment_date': enrollment.enrollment_date
            })

    return render_template('student/dashboard.html', courses=courses)


@student.route('/courses')
@login_required
@student_required
def courses():
    # Get all available courses
    all_courses = Course.query.all()

    # Get student's enrolled courses
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    enrolled_course_ids = [enrollment.course_id for enrollment in enrollments]

    return render_template('student/courses.html',
                           all_courses=all_courses,
                           enrolled_course_ids=enrolled_course_ids)


@student.route('/course/<int:course_id>')
@login_required
@student_required
def course_details(course_id):
    course = Course.query.get_or_404(course_id)
    instructor = User.query.get(course.instructor_id)

    # Check if student is enrolled
    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=course_id
    ).first()

    is_enrolled = enrollment is not None

    return render_template('student/course_details.html',
                           course=course,
                           instructor=instructor,
                           is_enrolled=is_enrolled)
