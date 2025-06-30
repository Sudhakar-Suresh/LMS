from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models.user import User, UserRole, UserLoginHistory, UserProfile
from datetime import datetime

auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        # Changed from email to username
        username = request.form.get('username')
        password = request.form.get('password')
        remember = 'remember' in request.form

        # First try to find by username
        user = User.query.filter_by(username=username).first()

        # If not found by username, try email
        if not user:
            user = User.query.filter_by(email=username).first()

        # Check if user exists and password is correct
        if not user or not check_password_hash(user.password, password):
            # Log failed login attempt
            if user:
                login_history = UserLoginHistory(
                    user_id=user.id,
                    ip_address=request.remote_addr,
                    user_agent=request.user_agent.string,
                    success=False
                )
                db.session.add(login_history)
                db.session.commit()

            flash('Invalid username/email or password. Please try again.', 'danger')
            return redirect(url_for('auth.login'))

        # Check if user is active
        if not user.is_active:
            flash(
                'Your account has been deactivated. Please contact an administrator.', 'danger')
            return redirect(url_for('auth.login'))

        # Update last login time
        user.last_login = datetime.utcnow()

        # Log successful login
        login_history = UserLoginHistory(
            user_id=user.id,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string,
            success=True
        )

        db.session.add(login_history)
        db.session.commit()

        # Login the user
        login_user(user, remember=remember)

        # Store role in session for easy access
        session['user_role'] = user.role

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
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        role = request.form.get('role', UserRole.STUDENT)  # Default to student

        # Validate password match
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.register'))

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
            role=role,
            is_active=True,
            is_email_verified=False
        )

        # Create user profile
        user_profile = UserProfile(user=new_user)

        db.session.add(new_user)
        db.session.add(user_profile)
        db.session.commit()

        flash('Registration successful! You can now login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth.route('/logout')
@login_required
def logout():
    session.pop('user_role', None)
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.index'))


@auth.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    # Ensure user has a profile
    if not current_user.profile:
        profile = UserProfile(user_id=current_user.id)
        db.session.add(profile)
        db.session.commit()

    if request.method == 'POST':
        # Update basic user info
        current_user.first_name = request.form.get('first_name')
        current_user.last_name = request.form.get('last_name')
        current_user.email = request.form.get('email')

        # Update profile information
        profile = current_user.profile
        profile.phone_number = request.form.get('phone_number')
        profile.address = request.form.get('address')
        profile.city = request.form.get('city')
        profile.state = request.form.get('state')
        profile.country = request.form.get('country')
        profile.postal_code = request.form.get('postal_code')
        profile.bio = request.form.get('bio')

        # Handle profile picture upload
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename:
                from app.utils.uploads import save_profile_picture
                filename = save_profile_picture(file)
                profile.profile_picture = filename

        # Role-specific fields
        if current_user.role == UserRole.STUDENT:
            profile.student_id = request.form.get('student_id')
            profile.graduation_year = request.form.get('graduation_year')
            profile.major = request.form.get('major')
        elif current_user.role == UserRole.INSTRUCTOR:
            profile.title = request.form.get('title')
            profile.specialization = request.form.get('specialization')
            profile.experience_years = request.form.get('experience_years')

        # Social media links
        profile.website = request.form.get('website')
        profile.linkedin = request.form.get('linkedin')
        profile.twitter = request.form.get('twitter')
        profile.github = request.form.get('github')

        db.session.commit()
        flash('Your profile has been updated successfully.', 'success')
        return redirect(url_for('auth.profile'))

    return render_template('auth/profile.html')


@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Verify current password
        if not check_password_hash(current_user.password, current_password):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('auth.change_password'))

        # Check if new passwords match
        if new_password != confirm_password:
            flash('New passwords do not match.', 'danger')
            return redirect(url_for('auth.change_password'))

        # Update password
        current_user.password = generate_password_hash(
            new_password, method='sha256')
        db.session.commit()

        flash('Your password has been updated successfully.', 'success')
        return redirect(url_for('auth.profile'))

    return render_template('auth/change_password.html')
