from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models.user import User, UserRole, Course, UserProfile, UserImportHistory, Role, Permission, CourseCategory, Enrollment
from functools import wraps
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
import os
import csv
import pandas as pd
from datetime import datetime
import uuid

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

    # Get recent users
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()

    # Get recent login activity
    recent_logins = db.session.query(User, db.func.max(User.last_login).label('last_login')) \
        .group_by(User.id) \
        .order_by(db.text('last_login DESC')) \
        .limit(5) \
        .all()

    return render_template('admin/dashboard.html',
                           user_count=user_count,
                           instructor_count=instructor_count,
                           student_count=student_count,
                           course_count=course_count,
                           recent_users=recent_users,
                           recent_logins=recent_logins)


@admin.route('/users')
@login_required
@admin_required
def users():
    # Get query parameters for filtering
    role_filter = request.args.get('role', '')
    search_query = request.args.get('q', '')

    # Base query
    query = User.query

    # Apply filters
    if role_filter:
        query = query.filter(User.role == role_filter)

    if search_query:
        search = f"%{search_query}%"
        query = query.filter(
            db.or_(
                User.username.ilike(search),
                User.email.ilike(search),
                User.first_name.ilike(search),
                User.last_name.ilike(search)
            )
        )

    # Get users with pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    users_pagination = query.order_by(
        User.created_at.desc()).paginate(page=page, per_page=per_page)

    return render_template('admin/users.html',
                           users_pagination=users_pagination,
                           role_filter=role_filter,
                           search_query=search_query,
                           roles=UserRole)


@admin.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username')
        email = request.form.get('email')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        role = request.form.get('role')
        password = request.form.get('password')
        is_active = 'is_active' in request.form

        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('admin.create_user'))

        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return redirect(url_for('admin.create_user'))

        # Create new user
        new_user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            password=generate_password_hash(password),
            is_active=is_active,
            is_email_verified=False
        )

        # Create user profile
        profile = UserProfile(user=new_user)

        db.session.add(new_user)
        db.session.add(profile)
        db.session.commit()

        flash(f'User {username} created successfully.', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/create_user.html', roles=UserRole)


@admin.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)

    # Ensure user has a profile
    if not user.profile:
        profile = UserProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()
        user = User.query.get(user_id)  # Refresh user data

    if request.method == 'POST':
        # Update user data
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        user.first_name = request.form.get('first_name')
        user.last_name = request.form.get('last_name')
        user.role = request.form.get('role')
        user.is_active = 'is_active' in request.form

        # Update password if provided
        new_password = request.form.get('password')
        if new_password:
            user.password = generate_password_hash(new_password)

        # Update profile data
        profile = user.profile
        profile.phone_number = request.form.get('phone_number')
        profile.address = request.form.get('address')
        profile.city = request.form.get('city')
        profile.state = request.form.get('state')
        profile.country = request.form.get('country')
        profile.postal_code = request.form.get('postal_code')

        # Handle profile picture upload
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename:
                from app.utils.uploads import save_profile_picture
                filename = save_profile_picture(file)
                if filename:
                    profile.profile_picture = filename

        db.session.commit()
        flash(f'User {user.username} updated successfully.', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/edit_user.html', user=user, roles=UserRole)


@admin.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    # Don't allow deleting self
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.users'))

    username = user.username

    # Delete user
    db.session.delete(user)
    db.session.commit()

    flash(f'User {username} has been deleted.', 'success')
    return redirect(url_for('admin.users'))


@admin.route('/users/bulk-import', methods=['GET', 'POST'])
@login_required
@admin_required
def bulk_import_users():
    if request.method == 'POST':
        # Check if file was uploaded
        if 'file' not in request.files:
            flash('No file uploaded.', 'danger')
            return redirect(request.url)

        file = request.files['file']

        # Check if file was selected
        if file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(request.url)

        # Check file extension
        if not file.filename.endswith(('.csv', '.xlsx')):
            flash('Only CSV and Excel files are allowed.', 'danger')
            return redirect(request.url)

        # Save file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(
            current_app.config['UPLOAD_FOLDER'], 'temp', f"{uuid.uuid4()}_{filename}")
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        file.save(temp_path)

        # Process file
        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(temp_path)
            else:
                df = pd.read_excel(temp_path)

            # Validate required columns
            required_columns = ['username', 'email',
                                'first_name', 'last_name', 'role', 'password']
            missing_columns = [
                col for col in required_columns if col not in df.columns]

            if missing_columns:
                flash(
                    f"Missing required columns: {', '.join(missing_columns)}", 'danger')
                os.remove(temp_path)
                return redirect(request.url)

            # Initialize counters
            total_records = len(df)
            successful_imports = 0
            failed_imports = 0
            error_log = []

            # Process each row
            for index, row in df.iterrows():
                try:
                    # Check if username or email already exists
                    existing_user = User.query.filter(
                        db.or_(
                            User.username == row['username'],
                            User.email == row['email']
                        )
                    ).first()

                    if existing_user:
                        error_log.append(
                            f"Row {index+1}: User with username '{row['username']}' or email '{row['email']}' already exists.")
                        failed_imports += 1
                        continue

                    # Validate role
                    if row['role'] not in [UserRole.ADMIN, UserRole.INSTRUCTOR, UserRole.STUDENT, UserRole.PARENT, UserRole.GUEST]:
                        error_log.append(
                            f"Row {index+1}: Invalid role '{row['role']}'. Must be one of: admin, instructor, student, parent, guest.")
                        failed_imports += 1
                        continue

                    # Create user
                    new_user = User(
                        username=row['username'],
                        email=row['email'],
                        first_name=row['first_name'],
                        last_name=row['last_name'],
                        role=row['role'],
                        password=generate_password_hash(str(row['password'])),
                        is_active=True,
                        is_email_verified=False
                    )

                    # Create profile
                    profile = UserProfile(user=new_user)

                    # Add optional profile fields if present
                    for field in ['phone_number', 'address', 'city', 'state', 'country', 'postal_code']:
                        if field in df.columns and not pd.isna(row[field]):
                            setattr(profile, field, row[field])

                    db.session.add(new_user)
                    db.session.add(profile)
                    successful_imports += 1

                except Exception as e:
                    error_log.append(f"Row {index+1}: {str(e)}")
                    failed_imports += 1

            # Commit changes
            db.session.commit()

            # Create import history record
            import_history = UserImportHistory(
                filename=filename,
                imported_by_id=current_user.id,
                total_records=total_records,
                successful_imports=successful_imports,
                failed_imports=failed_imports,
                error_log='\n'.join(error_log) if error_log else None
            )

            db.session.add(import_history)
            db.session.commit()

            # Clean up
            os.remove(temp_path)

            flash(
                f'Bulk import completed. {successful_imports} users imported successfully, {failed_imports} failed.', 'success')
            return redirect(url_for('admin.import_history'))

        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'danger')
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return redirect(request.url)

    return render_template('admin/bulk_import.html')


@admin.route('/users/import-history')
@login_required
@admin_required
def import_history():
    history = UserImportHistory.query.order_by(
        UserImportHistory.import_date.desc()).all()
    return render_template('admin/import_history.html', history=history)


@admin.route('/users/import-history/<int:history_id>')
@login_required
@admin_required
def import_history_detail(history_id):
    history = UserImportHistory.query.get_or_404(history_id)
    return render_template('admin/import_history_detail.html', history=history)


@admin.route('/courses')
@login_required
@admin_required
def courses():
    # Get query parameters for filtering
    category_filter = request.args.get('category', '')
    instructor_filter = request.args.get('instructor', '')
    search_query = request.args.get('q', '')

    # Base query
    query = Course.query

    # Apply filters
    if category_filter:
        query = query.filter(Course.category_id == category_filter)

    if instructor_filter:
        query = query.filter(Course.instructor_id == instructor_filter)

    if search_query:
        search = f"%{search_query}%"
        query = query.filter(Course.title.ilike(search) |
                             Course.description.ilike(search))

    # Get courses with pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    courses_pagination = query.order_by(
        Course.created_at.desc()).paginate(page=page, per_page=per_page)

    # Get categories and instructors for filter dropdowns
    categories = CourseCategory.query.all()
    instructors = User.query.filter_by(role=UserRole.INSTRUCTOR).all()

    return render_template('admin/courses.html',
                           courses_pagination=courses_pagination,
                           categories=categories,
                           instructors=instructors,
                           category_filter=category_filter,
                           instructor_filter=instructor_filter,
                           search_query=search_query)


@admin.route('/courses/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_course():
    if request.method == 'POST':
        # Get form data
        title = request.form.get('title')
        description = request.form.get('description')
        instructor_id = request.form.get('instructor_id')
        category_id = request.form.get('category_id')
        is_published = 'is_published' in request.form
        is_featured = 'is_featured' in request.form

        # Create new course
        new_course = Course(
            title=title,
            description=description,
            instructor_id=instructor_id,
            category_id=category_id if category_id else None,
            is_published=is_published,
            is_featured=is_featured
        )

        # Handle thumbnail upload
        if 'thumbnail' in request.files:
            file = request.files['thumbnail']
            if file and file.filename:
                from app.utils.uploads import save_course_thumbnail
                filename = save_course_thumbnail(file)
                if filename:
                    new_course.thumbnail = filename

        db.session.add(new_course)
        db.session.commit()

        flash(f'Course "{title}" created successfully.', 'success')
        return redirect(url_for('admin.courses'))

    # Get instructors and categories for dropdowns
    instructors = User.query.filter_by(role=UserRole.INSTRUCTOR).all()
    categories = CourseCategory.query.all()

    return render_template('admin/create_course.html',
                           instructors=instructors,
                           categories=categories)


@admin.route('/courses/<int:course_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)

    if request.method == 'POST':
        # Update course data
        course.title = request.form.get('title')
        course.description = request.form.get('description')
        course.instructor_id = request.form.get('instructor_id')
        course.category_id = request.form.get(
            'category_id') if request.form.get('category_id') else None
        course.is_published = 'is_published' in request.form
        course.is_featured = 'is_featured' in request.form

        # Handle thumbnail upload
        if 'thumbnail' in request.files:
            file = request.files['thumbnail']
            if file and file.filename:
                from app.utils.uploads import save_course_thumbnail
                filename = save_course_thumbnail(file)
                if filename:
                    course.thumbnail = filename

        db.session.commit()
        flash(f'Course "{course.title}" updated successfully.', 'success')
        return redirect(url_for('admin.courses'))

    # Get instructors and categories for dropdowns
    instructors = User.query.filter_by(role=UserRole.INSTRUCTOR).all()
    categories = CourseCategory.query.all()

    return render_template('admin/edit_course.html',
                           course=course,
                           instructors=instructors,
                           categories=categories)


@admin.route('/courses/<int:course_id>/view')
@login_required
@admin_required
def view_course(course_id):
    course = Course.query.get_or_404(course_id)
    enrollment_count = Enrollment.query.filter_by(course_id=course_id).count()
    return render_template('admin/view_course.html',
                           course=course,
                           enrollment_count=enrollment_count)


@admin.route('/courses/<int:course_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    title = course.title

    # Delete course
    db.session.delete(course)
    db.session.commit()

    flash(f'Course "{title}" has been deleted.', 'success')
    return redirect(url_for('admin.courses'))


@admin.route('/categories')
@login_required
@admin_required
def categories():
    categories = CourseCategory.query.all()
    return render_template('admin/categories.html', categories=categories)


@admin.route('/categories/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_category():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')

        # Check if category already exists
        if CourseCategory.query.filter_by(name=name).first():
            flash('Category already exists.', 'danger')
            return redirect(url_for('admin.create_category'))

        # Create category
        category = CourseCategory(name=name, description=description)

        db.session.add(category)
        db.session.commit()

        flash(f'Category "{name}" created successfully.', 'success')
        return redirect(url_for('admin.categories'))

    return render_template('admin/create_category.html')


@admin.route('/categories/edit/<int:category_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_category(category_id):
    category = CourseCategory.query.get_or_404(category_id)

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')

        # Check if another category with the same name exists
        existing_category = CourseCategory.query.filter(
            CourseCategory.name == name,
            CourseCategory.id != category_id
        ).first()

        if existing_category:
            flash('A category with this name already exists.', 'danger')
            return redirect(url_for('admin.edit_category', category_id=category_id))

        # Update category
        category.name = name
        category.description = description

        db.session.commit()
        flash(f'Category "{name}" updated successfully.', 'success')
        return redirect(url_for('admin.categories'))

    return render_template('admin/edit_category.html', category=category)


@admin.route('/categories/delete/<int:category_id>', methods=['POST'])
@login_required
@admin_required
def delete_category(category_id):
    category = CourseCategory.query.get_or_404(category_id)
    name = category.name

    # Update courses with this category to have no category
    for course in category.courses:
        course.category_id = None

    # Delete the category
    db.session.delete(category)
    db.session.commit()

    flash(f'Category "{name}" has been deleted.', 'success')
    return redirect(url_for('admin.categories'))


@admin.route('/system-settings', methods=['GET', 'POST'])
@login_required
@admin_required
def system_settings():
    # Get current settings from database or config
    # This is a placeholder - implement actual settings storage
    settings = {
        'site_name': current_app.config.get('SITE_NAME', 'Learning Management System'),
        'site_description': current_app.config.get('SITE_DESCRIPTION', 'A comprehensive learning platform'),
        'contact_email': current_app.config.get('CONTACT_EMAIL', 'admin@example.com'),
        'items_per_page': current_app.config.get('ITEMS_PER_PAGE', 20),
        'allow_registration': current_app.config.get('ALLOW_REGISTRATION', True),
        'email_verification_required': current_app.config.get('EMAIL_VERIFICATION_REQUIRED', False),
        'maintenance_mode': current_app.config.get('MAINTENANCE_MODE', False),
    }

    if request.method == 'POST':
        # Update settings
        # This is a placeholder - implement actual settings storage
        flash('System settings updated successfully.', 'success')
        return redirect(url_for('admin.system_settings'))

    return render_template('admin/system_settings.html', settings=settings)


@admin.route('/reports')
@login_required
@admin_required
def reports():
    report_type = request.args.get('type', 'users')

    if report_type == 'users':
        # User registration over time - SQLite compatible
        user_counts = db.session.query(
            db.func.strftime('%Y-%m', User.created_at).label('month'),
            db.func.count(User.id).label('count')
        ).group_by('month').order_by('month').all()

        # Users by role
        role_counts = db.session.query(
            User.role,
            db.func.count(User.id).label('count')
        ).group_by(User.role).all()

        return render_template('admin/reports.html',
                               report_type=report_type,
                               user_counts=user_counts,
                               role_counts=role_counts)

    elif report_type == 'courses':
        # Course creation over time - SQLite compatible
        course_counts = db.session.query(
            db.func.strftime('%Y-%m', Course.created_at).label('month'),
            db.func.count(Course.id).label('count')
        ).group_by('month').order_by('month').all()

        # Courses by category
        category_counts = db.session.query(
            CourseCategory.name,
            db.func.count(Course.id).label('count')
        ).join(Course, CourseCategory.id == Course.category_id, isouter=True)\
         .group_by(CourseCategory.name).all()

        return render_template('admin/reports.html',
                               report_type=report_type,
                               course_counts=course_counts,
                               category_counts=category_counts)

    elif report_type == 'enrollments':
        # Enrollments over time - SQLite compatible
        enrollment_counts = db.session.query(
            db.func.strftime(
                '%Y-%m', Enrollment.enrollment_date).label('month'),
            db.func.count(Enrollment.id).label('count')
        ).group_by('month').order_by('month').all()

        # Most popular courses
        popular_courses = db.session.query(
            Course.title,
            db.func.count(Enrollment.id).label('count')
        ).join(Enrollment, Course.id == Enrollment.course_id)\
         .group_by(Course.id).order_by(db.desc('count')).limit(10).all()

        return render_template('admin/reports.html',
                               report_type=report_type,
                               enrollment_counts=enrollment_counts,
                               popular_courses=popular_courses)

    return render_template('admin/reports.html', report_type=report_type)


@admin.route('/roles-permissions')
@login_required
@admin_required
def roles_permissions():
    roles = Role.query.all()
    permissions = Permission.query.all()
    return render_template('admin/roles_permissions.html', roles=roles, permissions=permissions)


@admin.route('/roles/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_role():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        permission_ids = request.form.getlist('permissions')

        # Check if role already exists
        if Role.query.filter_by(name=name).first():
            flash('Role already exists.', 'danger')
            return redirect(url_for('admin.create_role'))

        # Create role
        role = Role(name=name, description=description)

        # Add permissions
        for permission_id in permission_ids:
            permission = Permission.query.get(permission_id)
            if permission:
                role.permissions.append(permission)

        db.session.add(role)
        db.session.commit()

        flash(f'Role {name} created successfully.', 'success')
        return redirect(url_for('admin.roles_permissions'))

    permissions = Permission.query.all()
    return render_template('admin/create_role.html', permissions=permissions)


@admin.route('/permissions/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_permission():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')

        # Check if permission already exists
        if Permission.query.filter_by(name=name).first():
            flash('Permission already exists.', 'danger')
            return redirect(url_for('admin.create_permission'))

        # Create permission
        permission = Permission(name=name, description=description)

        db.session.add(permission)
        db.session.commit()

        flash(f'Permission {name} created successfully.', 'success')
        return redirect(url_for('admin.roles_permissions'))

    return render_template('admin/create_permission.html')

