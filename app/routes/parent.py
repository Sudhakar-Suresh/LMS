from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.user import User, UserRole, Course, Enrollment, ParentStudent
from functools import wraps

parent = Blueprint('parent', __name__, url_prefix='/parent')

# Parent required decorator


def parent_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != UserRole.PARENT:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


@parent.route('/dashboard')
@login_required
@parent_required
def dashboard():
    # Get parent's children
    parent_students = ParentStudent.query.filter_by(
        parent_id=current_user.id).all()

    children = []
    for ps in parent_students:
        student = User.query.get(ps.student_id)
        if student:
            # Get student's enrollments
            enrollments = Enrollment.query.filter_by(
                student_id=student.id).all()
            enrolled_courses = []

            for enrollment in enrollments:
                course = Course.query.get(enrollment.course_id)
                if course:
                    enrolled_courses.append(course)

            children.append({
                'student': student,
                'courses': enrolled_courses
            })

    return render_template('parent/dashboard.html', children=children)


@parent.route('/child/<int:student_id>')
@login_required
@parent_required
def child_details(student_id):
    # Verify this is the parent's child
    parent_student = ParentStudent.query.filter_by(
        parent_id=current_user.id,
        student_id=student_id
    ).first()

    if not parent_student:
        flash('You do not have permission to view this student.', 'danger')
        return redirect(url_for('parent.dashboard'))

    student = User.query.get_or_404(student_id)

    # Get student's enrollments
    enrollments = Enrollment.query.filter_by(student_id=student_id).all()
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

    return render_template('parent/child_details.html',
                           student=student,
                           courses=courses)
