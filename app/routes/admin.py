from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.user import User, UserRole, Course
from functools import wraps

admin = Blueprint('admin', __name__, url_prefix='/admin')

# Admin required decorator


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


@admin.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Get counts for dashboard
    user_count = User.query.count()
    instructor_count = User.query.filter_by(role=UserRole.INSTRUCTOR).count()
    student_count = User.query.filter_by(role=UserRole.STUDENT).count()
    course_count = Course.query.count()

    return render_template('admin/dashboard.html',
                           user_count=user_count,
                           instructor_count=instructor_count,
                           student_count=student_count,
                           course_count=course_count)


@admin.route('/users')
@login_required
@admin_required
def users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)


@admin.route('/courses')
@login_required
@admin_required
def courses():
    courses = Course.query.all()
    return render_template('admin/courses.html', courses=courses)
