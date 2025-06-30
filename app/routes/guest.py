from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.user import User, UserRole, Course
from functools import wraps

guest = Blueprint('guest', __name__, url_prefix='/guest')

# Guest required decorator


def guest_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != UserRole.GUEST:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


@guest.route('/dashboard')
@login_required
@guest_required
def dashboard():
    # Get all available courses for browsing
    courses = Course.query.all()

    # Get instructor information for each course
    course_info = []
    for course in courses:
        instructor = User.query.get(course.instructor_id)
        course_info.append({
            'course': course,
            'instructor': instructor
        })

    return render_template('guest/dashboard.html', course_info=course_info)


@guest.route('/course/<int:course_id>')
@login_required
@guest_required
def course_preview(course_id):
    course = Course.query.get_or_404(course_id)
    instructor = User.query.get(course.instructor_id)

    return render_template('guest/course_preview.html',
                           course=course,
                           instructor=instructor)
