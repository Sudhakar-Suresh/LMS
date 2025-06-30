from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models.user import User, UserRole

auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            flash('Please check your login details and try again.', 'danger')
            return redirect(url_for('auth.login'))

        login_user(user)

        # Redirect to appropriate dashboard based on user role
        if user.role == UserRole.ADMIN:
            return redirect(url_for('admin.dashboard'))
        elif user.role == UserRole.INSTRUCTOR:
            return redirect(url_for('instructor.dashboard'))
        elif user.role == UserRole.STUDENT:
            return redirect(url_for('student.dashboard'))
        elif user.role == UserRole.PARENT:
            return redirect(url_for('parent.dashboard'))
        else:  # Guest
            return redirect(url_for('guest.dashboard'))

    return render_template('auth/login.html')


@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        role = request.form.get('role', UserRole.STUDENT)  # Default to student

        # Check if user already exists
        user_email = User.query.filter_by(email=email).first()
        user_username = User.query.filter_by(username=username).first()

        if user_email:
            flash('Email already exists.', 'danger')
            return redirect(url_for('auth.register'))

        if user_username:
            flash('Username already exists.', 'danger')
            return redirect(url_for('auth.register'))

        # Create new user
        new_user = User(
            email=email,
            username=username,
            password=generate_password_hash(password, method='sha256'),
            first_name=first_name,
            last_name=last_name,
            role=role
        )

        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! You can now login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))
