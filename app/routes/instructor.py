import os
import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, send_from_directory
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from app import db
from app.models.user import User, UserRole, Course, CourseCategory, Module, Lesson, Topic, SubContent, CourseTag
from app.models.user import Batch, BatchEnrollment, LiveClass, Attendance, Enrollment
from app.models.user import Quiz, Question, QuestionOption, QuestionAnswer, QuizAttempt, QuizResponse
from app.models.user import Assignment, AssignmentSubmission, GradeItem, StudentGrade, Notes, Message
from app.utils.uploads import allowed_file, save_file, save_course_thumbnail, normalize_path

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


# Course Management Routes

@instructor.route('/create-course', methods=['GET', 'POST'])
@login_required
@instructor_required
def create_course():
    categories = CourseCategory.query.all()
    tags = CourseTag.query.all()

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category_id = request.form.get('category_id')

        # Create new course
        new_course = Course(
            title=title,
            description=description,
            instructor_id=current_user.id,
            category_id=category_id if category_id else None
        )

        # Handle tags
        tag_ids = request.form.getlist('tags')
        for tag_id in tag_ids:
            tag = CourseTag.query.get(tag_id)
            if tag:
                new_course.tags.append(tag)

        # Handle thumbnail upload
        if 'thumbnail' in request.files:
            thumbnail = request.files['thumbnail']
            if thumbnail.filename:
                filename = secure_filename(thumbnail.filename)
                thumbnail_path = os.path.join(
                    current_app.config['UPLOAD_FOLDER'], 'thumbnails', filename)
                os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)
                thumbnail.save(thumbnail_path)
                new_course.thumbnail = os.path.join('thumbnails', filename)

        # Handle drip content settings
        enable_drip = 'enable_drip' in request.form
        drip_interval = request.form.get('drip_interval', 0)
        new_course.enable_drip = enable_drip
        new_course.drip_interval_days = int(
            drip_interval) if drip_interval else 0

        db.session.add(new_course)
        db.session.commit()

        flash('Course created successfully!', 'success')
        return redirect(url_for('instructor.edit_course', course_id=new_course.id))

    return render_template('instructor/create_course.html', categories=categories, tags=tags)


@instructor.route('/edit-course/<int:course_id>', methods=['GET', 'POST'])
@login_required
@instructor_required
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)

    # Ensure instructor owns this course
    if course.instructor_id != current_user.id:
        flash('You do not have permission to edit this course.', 'danger')
        return redirect(url_for('instructor.courses'))

    categories = CourseCategory.query.all()
    tags = CourseTag.query.all()
    all_courses = Course.query.filter(Course.id != course_id,
                                      Course.instructor_id == current_user.id).all()

    if request.method == 'POST':
        course.title = request.form.get('title')
        course.description = request.form.get('description')
        course.category_id = request.form.get('category_id') or None

        # Handle tags
        course.tags = []
        tag_ids = request.form.getlist('tags')
        for tag_id in tag_ids:
            tag = CourseTag.query.get(tag_id)
            if tag:
                course.tags.append(tag)

        # Handle thumbnail upload
        if 'thumbnail' in request.files:
            thumbnail = request.files['thumbnail']
            if thumbnail.filename:
                filename = secure_filename(thumbnail.filename)
                thumbnail_path = os.path.join(
                    current_app.config['UPLOAD_FOLDER'], 'thumbnails', filename)
                os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)
                thumbnail.save(thumbnail_path)
                course.thumbnail = os.path.join('thumbnails', filename)

        # Handle drip content settings
        course.enable_drip = 'enable_drip' in request.form
        drip_interval = request.form.get('drip_interval', 0)
        course.drip_interval_days = int(drip_interval) if drip_interval else 0

        # Handle prerequisites
        course.prerequisites = []
        prereq_ids = request.form.getlist('prerequisites')
        for prereq_id in prereq_ids:
            prereq = Course.query.get(prereq_id)
            if prereq:
                course.prerequisites.append(prereq)

        # Handle publish status
        if 'is_published' in request.form:
            course.is_published = True
        else:
            course.is_published = False

        if 'is_featured' in request.form:
            course.is_featured = True
        else:
            course.is_featured = False

        db.session.commit()
        flash('Course updated successfully!', 'success')
        return redirect(url_for('instructor.course_curriculum', course_id=course.id))

    return render_template('instructor/edit_course.html',
                           course=course,
                           categories=categories,
                           tags=tags,
                           all_courses=all_courses)


@instructor.route('/course/<int:course_id>/curriculum', methods=['GET'])
@login_required
@instructor_required
def course_curriculum(course_id):
    course = Course.query.get_or_404(course_id)

    # Ensure instructor owns this course
    if course.instructor_id != current_user.id:
        flash('You do not have permission to view this course.', 'danger')
        return redirect(url_for('instructor.courses'))

    return render_template('instructor/course_curriculum.html', course=course)


@instructor.route('/course/<int:course_id>/module/create', methods=['GET', 'POST'])
@login_required
@instructor_required
def create_module(course_id):
    course = Course.query.get_or_404(course_id)

    # Ensure instructor owns this course
    if course.instructor_id != current_user.id:
        flash('You do not have permission to edit this course.', 'danger')
        return redirect(url_for('instructor.courses'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')

        # Get the highest order number and add 1
        highest_order = db.session.query(db.func.max(Module.order)).filter_by(
            course_id=course_id).scalar() or -1
        new_order = highest_order + 1

        new_module = Module(
            title=title,
            description=description,
            course_id=course_id,
            order=new_order
        )

        db.session.add(new_module)
        db.session.commit()

        flash('Module created successfully!', 'success')
        return redirect(url_for('instructor.course_curriculum', course_id=course_id))

    return render_template('instructor/create_module.html', course=course)


@instructor.route('/module/<int:module_id>/edit', methods=['GET', 'POST'])
@login_required
@instructor_required
def edit_module(module_id):
    module = Module.query.get_or_404(module_id)
    course = Course.query.get_or_404(module.course_id)

    # Ensure instructor owns this course
    if course.instructor_id != current_user.id:
        flash('You do not have permission to edit this module.', 'danger')
        return redirect(url_for('instructor.courses'))

    if request.method == 'POST':
        module.title = request.form.get('title')
        module.description = request.form.get('description')

        db.session.commit()
        flash('Module updated successfully!', 'success')
        return redirect(url_for('instructor.course_curriculum', course_id=course.id))

    return render_template('instructor/edit_module.html', module=module, course=course)


@instructor.route('/module/<int:module_id>/lesson/create', methods=['GET', 'POST'])
@login_required
@instructor_required
def create_lesson(module_id):
    module = Module.query.get_or_404(module_id)
    course = Course.query.get_or_404(module.course_id)

    # Ensure instructor owns this course
    if course.instructor_id != current_user.id:
        flash('You do not have permission to edit this course.', 'danger')
        return redirect(url_for('instructor.courses'))

    if request.method == 'POST':
        title = request.form.get('title')
        release_days = request.form.get('release_days', 0)

        # Get the highest order number and add 1
        highest_order = db.session.query(db.func.max(Lesson.order)).filter_by(
            module_id=module_id).scalar() or -1
        new_order = highest_order + 1

        new_lesson = Lesson(
            title=title,
            module_id=module_id,
            order=new_order,
            release_days=int(release_days) if release_days else 0
        )

        db.session.add(new_lesson)
        db.session.commit()

        flash('Lesson created successfully!', 'success')
        return redirect(url_for('instructor.course_curriculum', course_id=course.id))

    return render_template('instructor/create_lesson.html', module=module, course=course)


@instructor.route('/lesson/<int:lesson_id>/edit', methods=['GET', 'POST'])
@login_required
@instructor_required
def edit_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    module = Module.query.get_or_404(lesson.module_id)
    course = Course.query.get_or_404(module.course_id)

    # Ensure instructor owns this course
    if course.instructor_id != current_user.id:
        flash('You do not have permission to edit this lesson.', 'danger')
        return redirect(url_for('instructor.courses'))

    if request.method == 'POST':
        lesson.title = request.form.get('title')
        release_days = request.form.get('release_days', 0)
        lesson.release_days = int(release_days) if release_days else 0

        db.session.commit()
        flash('Lesson updated successfully!', 'success')
        return redirect(url_for('instructor.course_curriculum', course_id=course.id))

    return render_template('instructor/edit_lesson.html', lesson=lesson, module=module, course=course)


@instructor.route('/lesson/<int:lesson_id>/topic/create', methods=['GET', 'POST'])
@login_required
@instructor_required
def create_topic(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    module = Module.query.get_or_404(lesson.module_id)
    course = Course.query.get_or_404(module.course_id)

    # Ensure instructor owns this course
    if course.instructor_id != current_user.id:
        flash('You do not have permission to edit this course.', 'danger')
        return redirect(url_for('instructor.courses'))

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        content_type = request.form.get('content_type')

        # Get the highest order number and add 1
        highest_order = db.session.query(db.func.max(Topic.order)).filter_by(
            lesson_id=lesson_id).scalar() or -1
        new_order = highest_order + 1

        new_topic = Topic(
            title=title,
            content=content,
            content_type=content_type,
            lesson_id=lesson_id,
            order=new_order
        )

        # Handle file upload for video, audio, pdf
        if content_type in ['video', 'audio', 'pdf']:
            if 'file' in request.files:
                file = request.files['file']
                if file and file.filename:
                    # Use the utility function to save file with unique name
                    unique_filename = save_file(file, content_type)
                    if unique_filename:
                        new_topic.file_path = os.path.join(
                            content_type, unique_filename)

        db.session.add(new_topic)
        db.session.commit()

        flash('Topic created successfully!', 'success')
        return redirect(url_for('instructor.course_curriculum', course_id=course.id))

    return render_template('instructor/create_topic.html',
                           lesson=lesson,
                           module=module,
                           course=course)


@instructor.route('/topic/<int:topic_id>/edit', methods=['GET', 'POST'])
@login_required
@instructor_required
def edit_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    lesson = Lesson.query.get_or_404(topic.lesson_id)
    module = Module.query.get_or_404(lesson.module_id)
    course = Course.query.get_or_404(module.course_id)

    # Ensure instructor owns this course
    if course.instructor_id != current_user.id:
        flash('You do not have permission to edit this topic.', 'danger')
        return redirect(url_for('instructor.courses'))

    if request.method == 'POST':
        topic.title = request.form.get('title')
        topic.content = request.form.get('content')
        content_type = request.form.get('content_type')

        # Only update content type if it's the same category (file vs text)
        if (topic.content_type == 'text' and content_type == 'text') or \
           (topic.content_type in ['video', 'audio', 'pdf'] and content_type in ['video', 'audio', 'pdf']):
            topic.content_type = content_type

        # Handle file upload for video, audio, pdf
        if topic.content_type in ['video', 'audio', 'pdf']:
            if 'file' in request.files:
                file = request.files['file']
                if file and file.filename:
                    # Delete old file if exists
                    if topic.file_path:
                        old_file_path = os.path.join(
                            current_app.config['UPLOAD_FOLDER'], topic.file_path)
                        if os.path.exists(old_file_path):
                            os.remove(old_file_path)

                    # Use the utility function to save file with unique name
                    unique_filename = save_file(file, topic.content_type)
                    if unique_filename:
                        topic.file_path = os.path.join(
                            topic.content_type, unique_filename)

        db.session.commit()
        flash('Topic updated successfully!', 'success')
        return redirect(url_for('instructor.course_curriculum', course_id=course.id))

    return render_template('instructor/edit_topic.html',
                           topic=topic,
                           lesson=lesson,
                           module=module,
                           course=course)


@instructor.route('/course/<int:course_id>/clone', methods=['POST'])
@login_required
@instructor_required
def clone_course(course_id):
    course = Course.query.get_or_404(course_id)

    # Ensure instructor owns this course
    if course.instructor_id != current_user.id:
        flash('You do not have permission to clone this course.', 'danger')
        return redirect(url_for('instructor.courses'))

    new_title = request.form.get('new_title', f"Copy of {course.title}")

    # Clone the course and all its content
    new_course = course.clone(new_title)

    db.session.commit()
    flash(f'Course cloned successfully as "{new_course.title}"!', 'success')
    return redirect(url_for('instructor.edit_course', course_id=new_course.id))


# AJAX routes for reordering curriculum items
@instructor.route('/api/modules/reorder', methods=['POST'])
@login_required
@instructor_required
def reorder_modules():
    data = request.json
    course_id = data.get('course_id')
    module_order = data.get('module_order')  # List of module IDs in new order

    course = Course.query.get_or_404(course_id)
    if course.instructor_id != current_user.id:
        return jsonify({'success': False, 'error': 'Permission denied'}), 403

    for i, module_id in enumerate(module_order):
        module = Module.query.get(module_id)
        if module and module.course_id == course.id:
            module.order = i

    db.session.commit()
    return jsonify({'success': True})


@instructor.route('/api/lessons/reorder', methods=['POST'])
@login_required
@instructor_required
def reorder_lessons():
    data = request.json
    module_id = data.get('module_id')
    lesson_order = data.get('lesson_order')  # List of lesson IDs in new order

    module = Module.query.get_or_404(module_id)
    course = Course.query.get(module.course_id)

    if course.instructor_id != current_user.id:
        return jsonify({'success': False, 'error': 'Permission denied'}), 403

    for i, lesson_id in enumerate(lesson_order):
        lesson = Lesson.query.get(lesson_id)
        if lesson and lesson.module_id == module.id:
            lesson.order = i

    db.session.commit()
    return jsonify({'success': True})


@instructor.route('/api/topics/reorder', methods=['POST'])
@login_required
@instructor_required
def reorder_topics():
    data = request.json
    lesson_id = data.get('lesson_id')
    topic_order = data.get('topic_order')  # List of topic IDs in new order

    lesson = Lesson.query.get_or_404(lesson_id)
    module = Module.query.get(lesson.module_id)
    course = Course.query.get(module.course_id)

    if course.instructor_id != current_user.id:
        return jsonify({'success': False, 'error': 'Permission denied'}), 403

    for i, topic_id in enumerate(topic_order):
        topic = Topic.query.get(topic_id)
        if topic and topic.lesson_id == lesson.id:
            topic.order = i

    db.session.commit()
    return jsonify({'success': True})


# Category and Tag Management
@instructor.route('/categories', methods=['GET'])
@login_required
@instructor_required
def categories():
    categories = CourseCategory.query.all()
    return render_template('instructor/categories.html', categories=categories)


@instructor.route('/add-category', methods=['POST'])
@login_required
@instructor_required
def add_category():
    name = request.form.get('name')
    description = request.form.get('description')

    # Check if category already exists
    existing_category = CourseCategory.query.filter_by(name=name).first()
    if existing_category:
        flash('A category with this name already exists.', 'danger')
        return redirect(url_for('instructor.categories'))

    new_category = CourseCategory(name=name, description=description)
    db.session.add(new_category)
    db.session.commit()

    flash('Category added successfully!', 'success')
    return redirect(url_for('instructor.categories'))


@instructor.route('/edit-category', methods=['POST'])
@login_required
@instructor_required
def edit_category():
    category_id = request.form.get('id')
    name = request.form.get('name')
    description = request.form.get('description')

    category = CourseCategory.query.get_or_404(category_id)

    # Check if another category with the same name exists
    if name != category.name:
        existing_category = CourseCategory.query.filter_by(name=name).first()
        if existing_category:
            flash('A category with this name already exists.', 'danger')
            return redirect(url_for('instructor.categories'))

    category.name = name
    category.description = description
    db.session.commit()

    flash('Category updated successfully!', 'success')
    return redirect(url_for('instructor.categories'))


@instructor.route('/delete-category', methods=['POST'])
@login_required
@instructor_required
def delete_category():
    category_id = request.form.get('id')
    category = CourseCategory.query.get_or_404(category_id)

    # Update all courses that use this category
    for course in category.courses:
        course.category_id = None

    db.session.delete(category)
    db.session.commit()

    flash('Category deleted successfully!', 'success')
    return redirect(url_for('instructor.categories'))


@instructor.route('/tags', methods=['GET'])
@login_required
@instructor_required
def tags():
    tags = CourseTag.query.all()
    return render_template('instructor/tags.html', tags=tags)


@instructor.route('/add-tag', methods=['POST'])
@login_required
@instructor_required
def add_tag():
    name = request.form.get('name')

    # Check if tag already exists
    existing_tag = CourseTag.query.filter_by(name=name).first()
    if existing_tag:
        flash('A tag with this name already exists.', 'danger')
        return redirect(url_for('instructor.tags'))

    new_tag = CourseTag(name=name)
    db.session.add(new_tag)
    db.session.commit()

    flash('Tag added successfully!', 'success')
    return redirect(url_for('instructor.tags'))


@instructor.route('/edit-tag', methods=['POST'])
@login_required
@instructor_required
def edit_tag():
    tag_id = request.form.get('id')
    name = request.form.get('name')

    tag = CourseTag.query.get_or_404(tag_id)

    # Check if another tag with the same name exists
    if name != tag.name:
        existing_tag = CourseTag.query.filter_by(name=name).first()
        if existing_tag:
            flash('A tag with this name already exists.', 'danger')
            return redirect(url_for('instructor.tags'))

    tag.name = name
    db.session.commit()

    flash('Tag updated successfully!', 'success')
    return redirect(url_for('instructor.tags'))


@instructor.route('/delete-tag', methods=['POST'])
@login_required
@instructor_required
def delete_tag():
    tag_id = request.form.get('id')
    tag = CourseTag.query.get_or_404(tag_id)

    # Remove this tag from all courses
    for course in tag.courses:
        course.tags.remove(tag)

    db.session.delete(tag)
    db.session.commit()

    flash('Tag deleted successfully!', 'success')
    return redirect(url_for('instructor.tags'))


# File upload handler for CKEditor
@instructor.route('/upload', methods=['POST'])
@login_required
@instructor_required
def upload_file():
    if 'upload' in request.files:
        file = request.files['upload']
        if file.filename:
            filename = secure_filename(file.filename)
            file_path = os.path.join(
                current_app.config['UPLOAD_FOLDER'], 'editor', filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            file.save(file_path)

            # Return the URL to CKEditor
            url = url_for('static', filename=f'uploads/editor/{filename}')
            return jsonify({'url': url, 'uploaded': 1, 'fileName': filename})

    return jsonify({'uploaded': 0, 'error': {'message': 'Upload failed'}})


# Batch Management Routes
@instructor.route('/batches')
@login_required
@instructor_required
def batches():
    # Get all batches for the instructor's courses
    instructor_courses = Course.query.filter_by(
        instructor_id=current_user.id).all()
    course_ids = [course.id for course in instructor_courses]

    batches = Batch.query.filter(Batch.course_id.in_(
        course_ids)).order_by(Batch.start_date.desc()).all()

    return render_template('instructor/batches.html', batches=batches, courses=instructor_courses, datetime=datetime)


@instructor.route('/create-batch', methods=['GET', 'POST'])
@login_required
@instructor_required
def create_batch():
    # Get instructor's courses for the dropdown
    courses = Course.query.filter_by(instructor_id=current_user.id).all()

    if not courses:
        flash('You need to create a course first before creating a batch.', 'warning')
        return redirect(url_for('instructor.courses'))

    if request.method == 'POST':
        name = request.form['name']
        course_id = request.form['course_id']
        start_date = datetime.strptime(
            request.form['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(
            request.form['end_date'], '%Y-%m-%d').date()
        max_students = request.form['max_students']
        description = request.form['description']
        is_active = 'is_active' in request.form

        # Validate course belongs to instructor
        course = Course.query.get(course_id)
        if not course or course.instructor_id != current_user.id:
            flash('Invalid course selected.', 'danger')
            return redirect(url_for('instructor.create_batch'))

        # Validate dates
        if end_date < start_date:
            flash('End date cannot be before start date.', 'danger')
            return redirect(url_for('instructor.create_batch'))

        # Create batch
        batch = Batch(
            name=name,
            course_id=course_id,
            start_date=start_date,
            end_date=end_date,
            max_students=max_students,
            description=description,
            is_active=is_active
        )

        db.session.add(batch)
        db.session.commit()

        flash('Batch created successfully.', 'success')
        return redirect(url_for('instructor.batch_students', batch_id=batch.id))

    return render_template('instructor/create_batch.html', courses=courses)


@instructor.route('/edit-batch/<int:batch_id>', methods=['GET', 'POST'])
@login_required
@instructor_required
def edit_batch(batch_id):
    batch = Batch.query.get_or_404(batch_id)

    # Check if batch belongs to instructor's course
    course = Course.query.get(batch.course_id)
    if not course or course.instructor_id != current_user.id:
        flash('You do not have permission to edit this batch.', 'danger')
        return redirect(url_for('instructor.batches'))

    # Get instructor's courses for the dropdown
    instructor_courses = Course.query.filter_by(
        instructor_id=current_user.id).all()

    if request.method == 'POST':
        name = request.form.get('name')
        course_id = request.form.get('course_id')
        start_date = datetime.strptime(
            request.form.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(
            request.form.get('end_date'), '%Y-%m-%d').date()
        max_students = request.form.get('max_students')
        description = request.form.get('description')
        is_active = 'is_active' in request.form

        # Validate inputs
        if not name or not course_id or not start_date or not end_date:
            flash('Please fill all required fields.', 'danger')
            return redirect(url_for('instructor.edit_batch', batch_id=batch_id))

        # Check if course belongs to the instructor
        course = Course.query.get(course_id)
        if not course or course.instructor_id != current_user.id:
            flash('Invalid course selected.', 'danger')
            return redirect(url_for('instructor.edit_batch', batch_id=batch_id))

        # Update batch
        batch.name = name
        batch.course_id = course_id
        batch.start_date = start_date
        batch.end_date = end_date
        batch.max_students = max_students if max_students else 30
        batch.description = description
        batch.is_active = is_active

        db.session.commit()

        flash('Batch updated successfully!', 'success')
        return redirect(url_for('instructor.batch_students', batch_id=batch.id))

    return render_template('instructor/edit_batch.html', batch=batch, courses=instructor_courses)


@instructor.route('/batch/<int:batch_id>/students')
@login_required
@instructor_required
def batch_students(batch_id):
    batch = Batch.query.get_or_404(batch_id)

    # Check if batch belongs to instructor's course
    course = Course.query.get(batch.course_id)
    if not course or course.instructor_id != current_user.id:
        flash('You do not have permission to view this batch.', 'danger')
        return redirect(url_for('instructor.batches'))

    # Get enrolled students
    enrollments = BatchEnrollment.query.filter_by(batch_id=batch_id).all()
    students = []
    for enrollment in enrollments:
        student = User.query.get(enrollment.student_id)
        if student:
            students.append(student)

    return render_template('instructor/batch_students.html',
                           batch=batch,
                           students=students,
                           datetime=datetime,
                           timedelta=timedelta,
                           BatchEnrollment=BatchEnrollment)


@instructor.route('/batch/<int:batch_id>/add-student', methods=['GET', 'POST'])
@login_required
@instructor_required
def add_student_to_batch(batch_id):
    batch = Batch.query.get_or_404(batch_id)

    # Check if batch belongs to instructor's course
    course = Course.query.get(batch.course_id)
    if not course or course.instructor_id != current_user.id:
        flash('You do not have permission to edit this batch.', 'danger')
        return redirect(url_for('instructor.batches'))

    # Get current enrollment count
    current_enrollments = BatchEnrollment.query.filter_by(
        batch_id=batch_id).count()

    # Check if batch has reached maximum capacity
    if batch.max_students > 0 and current_enrollments >= batch.max_students:
        flash('Batch has reached maximum capacity. Remove some students or increase capacity.', 'warning')
        return redirect(url_for('instructor.batch_students', batch_id=batch_id))

    if request.method == 'POST':
        search_term = request.form.get('student_search')

        if search_term:
            # Search by email (exact match) or name (partial match)
            students = User.query.filter(
                User.role == UserRole.STUDENT,  # Student role
                db.or_(
                    User.email == search_term,
                    db.func.lower(User.first_name + ' ' +
                                  User.last_name).contains(search_term.lower())
                )
            ).all()

            if not students:
                flash('No students found with this email or name.', 'warning')
                return render_template('instructor/add_student_to_batch.html',
                                       batch=batch,
                                       search_term=search_term,
                                       search_performed=True,
                                       found_students=[],
                                       enrolled_count=current_enrollments)

            # Filter out students already enrolled in this batch
            enrolled_ids = [e.student_id for e in BatchEnrollment.query.filter_by(
                batch_id=batch_id).all()]
            available_students = [
                s for s in students if s.id not in enrolled_ids]

            if not available_students:
                flash('All found students are already enrolled in this batch.', 'info')
                return render_template('instructor/add_student_to_batch.html',
                                       batch=batch,
                                       search_term=search_term,
                                       search_performed=True,
                                       found_students=[],
                                       enrolled_count=current_enrollments)

            return render_template('instructor/add_student_to_batch.html',
                                   batch=batch,
                                   search_term=search_term,
                                   search_performed=True,
                                   found_students=available_students,
                                   enrolled_count=current_enrollments)

        # If student_id is provided, it means the user selected a student from search results
        student_id = request.form.get('student_id')
        if student_id:
            student = User.query.get(student_id)

            if not student or student.role != UserRole.STUDENT:  # Verify it's a student
                flash('Invalid student selected.', 'danger')
                return redirect(url_for('instructor.add_student_to_batch', batch_id=batch_id))

            # Check if student is already enrolled in the batch
            existing_enrollment = BatchEnrollment.query.filter_by(
                batch_id=batch_id,
                student_id=student.id
            ).first()

            if existing_enrollment:
                flash('Student is already enrolled in this batch.', 'warning')
                return redirect(url_for('instructor.batch_students', batch_id=batch_id))

            # Enroll student in batch
            enrollment = BatchEnrollment(
                batch_id=batch_id,
                student_id=student.id,
                enrollment_date=datetime.utcnow().date()
            )

            # Also enroll in course if not already enrolled
            course_enrollment = Enrollment.query.filter_by(
                student_id=student.id,
                course_id=batch.course_id
            ).first()

            if not course_enrollment:
                course_enrollment = Enrollment(
                    student_id=student.id,
                    course_id=batch.course_id,
                    enrollment_date=datetime.utcnow().date()
                )
                db.session.add(course_enrollment)

            db.session.add(enrollment)
            db.session.commit()

            flash(
                f'Student {student.first_name} {student.last_name} added to batch successfully!', 'success')
            return redirect(url_for('instructor.batch_students', batch_id=batch_id))

    return render_template('instructor/add_student_to_batch.html',
                           batch=batch,
                           search_performed=False,
                           enrolled_count=current_enrollments)


@instructor.route('/batch/<int:batch_id>/remove-student', methods=['POST'])
@login_required
@instructor_required
def remove_student_from_batch(batch_id):
    batch = Batch.query.get_or_404(batch_id)

    # Check if batch belongs to instructor's course
    course = Course.query.get(batch.course_id)
    if not course or course.instructor_id != current_user.id:
        flash('You do not have permission to remove students from this batch.', 'danger')
        return redirect(url_for('instructor.batches'))

    student_id = request.form.get('student_id')
    if not student_id:
        flash('No student specified.', 'danger')
        return redirect(url_for('instructor.batch_students', batch_id=batch_id))

    # Find the enrollment
    enrollment = BatchEnrollment.query.filter_by(
        batch_id=batch_id, student_id=student_id).first()

    if not enrollment:
        flash('Student is not enrolled in this batch.', 'warning')
        return redirect(url_for('instructor.batch_students', batch_id=batch_id))

    # Get student info for the flash message
    student = User.query.get(student_id)
    student_name = f"{student.first_name} {student.last_name}" if student else "Student"

    # Remove the enrollment
    db.session.delete(enrollment)
    db.session.commit()

    flash(f'{student_name} has been removed from the batch.', 'success')
    return redirect(url_for('instructor.batch_students', batch_id=batch_id))


# Live Class Management Routes
@instructor.route('/live-classes')
@login_required
@instructor_required
def live_classes():
    # Get all live classes for the instructor
    instructor_courses = Course.query.filter_by(
        instructor_id=current_user.id).all()
    course_ids = [course.id for course in instructor_courses]

    batches = Batch.query.filter(Batch.course_id.in_(course_ids)).all()
    batch_ids = [batch.id for batch in batches]

    live_classes = LiveClass.query.filter(
        LiveClass.batch_id.in_(batch_ids)).all()

    # Organize classes by batch
    classes_by_batch = {}
    for live_class in live_classes:
        batch = Batch.query.get(live_class.batch_id)
        if batch.name not in classes_by_batch:
            classes_by_batch[batch.name] = []
        classes_by_batch[batch.name].append(live_class)

    return render_template('instructor/live_classes.html', classes_by_batch=classes_by_batch, datetime=datetime, timedelta=timedelta)


@instructor.route('/create-live-class', methods=['GET', 'POST'])
@login_required
@instructor_required
def create_live_class():
    # Get all batches for instructor's courses
    instructor_courses = Course.query.filter_by(
        instructor_id=current_user.id).all()
    course_ids = [course.id for course in instructor_courses]
    batches = Batch.query.filter(Batch.course_id.in_(course_ids)).all()

    if not batches:
        flash('You need to create a batch first before scheduling a live class.', 'warning')
        return redirect(url_for('instructor.batches'))

    # Get batch_id from query parameter if provided
    selected_batch_id = request.args.get('batch_id', type=int)
    selected_batch = None
    if selected_batch_id:
        selected_batch = Batch.query.get(selected_batch_id)
        # Verify the batch belongs to the instructor
        if selected_batch and selected_batch.course.instructor_id != current_user.id:
            selected_batch = None

    if request.method == 'POST':
        title = request.form['title']
        batch_id = request.form['batch_id']
        scheduled_date = request.form['scheduled_date']
        scheduled_time = request.form['scheduled_time']
        duration_minutes = int(request.form['duration_minutes'])
        meeting_link = request.form['meeting_link']
        description = request.form['description']
        is_recorded = 'is_recorded' in request.form

        # Combine date and time
        scheduled_datetime = datetime.strptime(
            f"{scheduled_date} {scheduled_time}", "%Y-%m-%d %H:%M")

        # Calculate end time based on duration
        end_time = scheduled_datetime + timedelta(minutes=duration_minutes)

        # Create new live class
        live_class = LiveClass(
            title=title,
            batch_id=batch_id,
            instructor_id=current_user.id,
            start_time=scheduled_datetime,
            end_time=end_time,
            meeting_link=meeting_link,
            description=description,
            is_recurring=False
        )

        db.session.add(live_class)
        db.session.commit()

        if 'send_notification' in request.form:
            # TODO: Send notification to students
            pass

        flash('Live class scheduled successfully.', 'success')
        return redirect(url_for('instructor.batch_students', batch_id=batch_id))

    today = datetime.now().date()
    return render_template('instructor/create_live_class.html',
                           batches=batches,
                           today=today,
                           selected_batch=selected_batch)


@instructor.route('/live-class/<int:class_id>/edit', methods=['GET', 'POST'])
@login_required
@instructor_required
def edit_live_class(class_id):
    live_class = LiveClass.query.get_or_404(class_id)

    # Check if instructor has access to this class
    batch = Batch.query.get(live_class.batch_id)
    if not batch:
        flash('Batch not found.', 'danger')
        return redirect(url_for('instructor.live_classes'))

    course = Course.query.get(batch.course_id)
    if not course or course.instructor_id != current_user.id:
        flash('You do not have permission to edit this class.', 'danger')
        return redirect(url_for('instructor.live_classes'))

    # Get all batches for instructor's courses
    instructor_courses = Course.query.filter_by(
        instructor_id=current_user.id).all()
    course_ids = [course.id for course in instructor_courses]
    batches = Batch.query.filter(Batch.course_id.in_(course_ids)).all()

    if request.method == 'POST':
        title = request.form['title']
        batch_id = request.form['batch_id']
        scheduled_date = request.form['scheduled_date']
        scheduled_time = request.form['scheduled_time']
        duration_minutes = int(request.form['duration_minutes'])
        meeting_link = request.form['meeting_link']
        description = request.form['description']
        is_recorded = 'is_recorded' in request.form
        send_notification = 'send_notification' in request.form

        # Combine date and time
        scheduled_datetime = datetime.strptime(
            f"{scheduled_date} {scheduled_time}", "%Y-%m-%d %H:%M")

        # Calculate end time based on duration
        end_time = scheduled_datetime + timedelta(minutes=duration_minutes)

        # Update class
        live_class.title = title
        live_class.batch_id = batch_id
        live_class.start_time = scheduled_datetime
        live_class.end_time = end_time
        live_class.meeting_link = meeting_link
        live_class.description = description

        db.session.commit()

        if send_notification:
            # TODO: Send notification to students
            pass

        flash('Live class updated successfully.', 'success')
        return redirect(url_for('instructor.batch_students', batch_id=batch_id))

    return render_template('instructor/edit_live_class.html',
                           live_class=live_class,
                           batches=batches,
                           scheduled_date=live_class.start_time.strftime(
                               '%Y-%m-%d'),
                           scheduled_time=live_class.start_time.strftime(
                               '%H:%M'),
                           duration_minutes=int(
                               (live_class.end_time - live_class.start_time).total_seconds() / 60),
                           now=datetime.now)


@instructor.route('/live-class/<int:class_id>/attendance', methods=['GET', 'POST'])
@login_required
@instructor_required
def class_attendance(class_id):
    live_class = LiveClass.query.get_or_404(class_id)

    # Check if instructor has access to this class
    batch = Batch.query.get(live_class.batch_id)
    if not batch:
        flash('Batch not found.', 'danger')
        return redirect(url_for('instructor.live_classes'))

    course = Course.query.get(batch.course_id)
    if not course or course.instructor_id != current_user.id:
        flash('You do not have permission to manage this class.', 'danger')
        return redirect(url_for('instructor.live_classes'))

    # Get all students enrolled in the batch
    enrollments = BatchEnrollment.query.filter_by(batch_id=batch.id).all()
    students = []
    for enrollment in enrollments:
        student = User.query.get(enrollment.student_id)
        if student:
            # Check if attendance record exists for this student and class
            attendance = Attendance.query.filter_by(
                student_id=student.id,
                live_class_id=class_id
            ).first()

            students.append({
                'id': student.id,
                'name': f"{student.first_name} {student.last_name}",
                'email': student.email,
                'present': attendance.present if attendance else False,
                'has_record': attendance is not None
            })

    if request.method == 'POST':
        # Get present student IDs from form
        present_ids = request.form.getlist('present_students')

        # Convert to integers
        present_ids = [int(id) for id in present_ids]

        # Update attendance records
        for student in students:
            student_id = student['id']

            # Check if attendance record exists
            attendance = Attendance.query.filter_by(
                student_id=student_id,
                live_class_id=class_id
            ).first()

            is_present = student_id in present_ids

            if attendance:
                # Update existing record
                attendance.present = is_present
            else:
                # Create new record
                attendance = Attendance(
                    student_id=student_id,
                    live_class_id=class_id,
                    present=is_present,
                    marked_by=current_user.id,
                    marked_at=datetime.utcnow()
                )
                db.session.add(attendance)

        db.session.commit()
        flash('Attendance has been saved successfully.', 'success')
        return redirect(url_for('instructor.batch_students', batch_id=batch.id))

    return render_template('instructor/class_attendance.html',
                           live_class=live_class,
                           batch=batch,
                           students=students,
                           now=datetime.now)


# Quiz and Assessment Routes
@instructor.route('/quizzes')
@login_required
@instructor_required
def quizzes():
    # Get all quizzes for courses taught by this instructor
    instructor_courses = Course.query.filter_by(
        instructor_id=current_user.id).all()
    course_ids = [course.id for course in instructor_courses]

    quizzes = Quiz.query.filter(Quiz.course_id.in_(
        course_ids)).order_by(Quiz.created_at.desc()).all()

    return render_template('instructor/quizzes.html', quizzes=quizzes, courses=instructor_courses)


@instructor.route('/create-quiz', methods=['GET', 'POST'])
@login_required
@instructor_required
def create_quiz():
    # Get instructor's courses for the dropdown
    instructor_courses = Course.query.filter_by(
        instructor_id=current_user.id).all()

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        course_id = request.form.get('course_id')
        module_id = request.form.get('module_id') or None
        time_limit = request.form.get('time_limit') or 0
        passing_score = request.form.get('passing_score') or 60
        attempts_allowed = request.form.get('attempts_allowed') or 1
        shuffle_questions = 'shuffle_questions' in request.form
        show_correct_answers = 'show_correct_answers' in request.form

        # Create new quiz
        new_quiz = Quiz(
            title=title,
            description=description,
            course_id=course_id,
            module_id=module_id,
            time_limit_minutes=time_limit,
            passing_score=passing_score,
            attempts_allowed=attempts_allowed,
            shuffle_questions=shuffle_questions,
            show_correct_answers=show_correct_answers,
            is_published=False
        )

        db.session.add(new_quiz)
        db.session.commit()

        flash('Quiz created successfully! Now add questions to your quiz.', 'success')
        return redirect(url_for('instructor.edit_quiz', quiz_id=new_quiz.id))

    return render_template('instructor/create_quiz.html', courses=instructor_courses)


@instructor.route('/edit-quiz/<int:quiz_id>', methods=['GET', 'POST'])
@login_required
@instructor_required
def edit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)

    # Check if instructor owns this quiz's course
    if quiz.course.instructor_id != current_user.id:
        flash('You do not have permission to edit this quiz.', 'danger')
        return redirect(url_for('instructor.quizzes'))

    instructor_courses = Course.query.filter_by(
        instructor_id=current_user.id).all()

    if request.method == 'POST':
        quiz.title = request.form.get('title')
        quiz.description = request.form.get('description')
        quiz.course_id = request.form.get('course_id')
        quiz.module_id = request.form.get('module_id') or None
        quiz.time_limit_minutes = request.form.get('time_limit') or 0
        quiz.passing_score = request.form.get('passing_score') or 60
        quiz.attempts_allowed = request.form.get('attempts_allowed') or 1
        quiz.shuffle_questions = 'shuffle_questions' in request.form
        quiz.show_correct_answers = 'show_correct_answers' in request.form
        quiz.is_published = 'is_published' in request.form

        db.session.commit()
        flash('Quiz updated successfully!', 'success')
        return redirect(url_for('instructor.quiz_questions', quiz_id=quiz.id))

    # Get modules for the selected course
    modules = Module.query.filter_by(course_id=quiz.course_id).all()

    return render_template('instructor/edit_quiz.html',
                           quiz=quiz,
                           courses=instructor_courses,
                           modules=modules)


@instructor.route('/quiz/<int:quiz_id>/questions', methods=['GET'])
@login_required
@instructor_required
def quiz_questions(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)

    # Check if instructor owns this quiz's course
    if quiz.course.instructor_id != current_user.id:
        flash('You do not have permission to view this quiz.', 'danger')
        return redirect(url_for('instructor.quizzes'))

    questions = Question.query.filter_by(
        quiz_id=quiz_id).order_by(Question.order).all()

    return render_template('instructor/quiz_questions.html',
                           quiz=quiz,
                           questions=questions)


@instructor.route('/quiz/<int:quiz_id>/add-question', methods=['GET', 'POST'])
@login_required
@instructor_required
def add_question(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)

    # Check if instructor owns this quiz's course
    if quiz.course.instructor_id != current_user.id:
        flash('You do not have permission to edit this quiz.', 'danger')
        return redirect(url_for('instructor.quizzes'))

    if request.method == 'POST':
        question_text = request.form.get('question_text')
        question_type = request.form.get('question_type')
        points = request.form.get('points') or 1.0
        negative_points = request.form.get('negative_points') or 0.0
        explanation = request.form.get('explanation')

        # Get the highest order value
        last_question = Question.query.filter_by(
            quiz_id=quiz_id).order_by(Question.order.desc()).first()
        order = (last_question.order + 1) if last_question else 1

        # Create new question
        new_question = Question(
            quiz_id=quiz_id,
            question_text=question_text,
            question_type=question_type,
            points=points,
            negative_points=negative_points,
            explanation=explanation,
            order=order
        )

        db.session.add(new_question)
        db.session.commit()

        # Handle options/answers based on question type
        if question_type == 'mcq' or question_type == 'true_false':
            option_count = int(request.form.get('option_count', 0))
            for i in range(1, option_count + 1):
                option_text = request.form.get(f'option_{i}')
                is_correct = f'correct_option_{i}' in request.form

                if option_text:
                    option = QuestionOption(
                        question_id=new_question.id,
                        option_text=option_text,
                        is_correct=is_correct,
                        order=i
                    )
                    db.session.add(option)

        elif question_type == 'fill_blank' or question_type == 'short_answer':
            answer_text = request.form.get('answer_text')
            if answer_text:
                answer = QuestionAnswer(
                    question_id=new_question.id,
                    answer_text=answer_text
                )
                db.session.add(answer)

        db.session.commit()
        flash('Question added successfully!', 'success')
        return redirect(url_for('instructor.quiz_questions', quiz_id=quiz_id))

    return render_template('instructor/add_question.html', quiz=quiz)


@instructor.route('/question/<int:question_id>/edit', methods=['GET', 'POST'])
@login_required
@instructor_required
def edit_question(question_id):
    question = Question.query.get_or_404(question_id)
    quiz = Quiz.query.get(question.quiz_id)

    # Check if instructor owns this quiz's course
    if quiz.course.instructor_id != current_user.id:
        flash('You do not have permission to edit this question.', 'danger')
        return redirect(url_for('instructor.quizzes'))

    if request.method == 'POST':
        question.question_text = request.form.get('question_text')
        question.points = request.form.get('points') or 1.0
        question.negative_points = request.form.get('negative_points') or 0.0
        question.explanation = request.form.get('explanation')

        # Handle options/answers based on question type
        if question.question_type == 'mcq' or question.question_type == 'true_false':
            # Delete existing options
            QuestionOption.query.filter_by(question_id=question.id).delete()

            option_count = int(request.form.get('option_count', 0))
            for i in range(1, option_count + 1):
                option_text = request.form.get(f'option_{i}')
                is_correct = f'correct_option_{i}' in request.form

                if option_text:
                    option = QuestionOption(
                        question_id=question.id,
                        option_text=option_text,
                        is_correct=is_correct,
                        order=i
                    )
                    db.session.add(option)

        elif question.question_type == 'fill_blank' or question.question_type == 'short_answer':
            # Delete existing answers
            QuestionAnswer.query.filter_by(question_id=question.id).delete()

            answer_text = request.form.get('answer_text')
            if answer_text:
                answer = QuestionAnswer(
                    question_id=question.id,
                    answer_text=answer_text
                )
                db.session.add(answer)

        db.session.commit()
        flash('Question updated successfully!', 'success')
        return redirect(url_for('instructor.quiz_questions', quiz_id=question.quiz_id))

    return render_template('instructor/edit_question.html',
                           question=question,
                           quiz=quiz,
                           options=question.options,
                           answer=QuestionAnswer.query.filter_by(question_id=question.id).first())


@instructor.route('/question/<int:question_id>/delete', methods=['POST'])
@login_required
@instructor_required
def delete_question(question_id):
    question = Question.query.get_or_404(question_id)
    quiz = Quiz.query.get(question.quiz_id)

    # Check if instructor owns this quiz's course
    if quiz.course.instructor_id != current_user.id:
        flash('You do not have permission to delete this question.', 'danger')
        return redirect(url_for('instructor.quizzes'))

    quiz_id = question.quiz_id

    # Delete the question (cascade will delete options and answers)
    db.session.delete(question)
    db.session.commit()

    flash('Question deleted successfully!', 'success')
    return redirect(url_for('instructor.quiz_questions', quiz_id=quiz_id))


@instructor.route('/quiz/<int:quiz_id>/results')
@login_required
@instructor_required
def quiz_results(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)

    # Check if instructor owns this quiz's course
    if quiz.course.instructor_id != current_user.id:
        flash('You do not have permission to view these results.', 'danger')
        return redirect(url_for('instructor.quizzes'))

    # Get all attempts for this quiz
    attempts = QuizAttempt.query.filter_by(quiz_id=quiz_id).order_by(
        QuizAttempt.start_time.desc()).all()

    # Group attempts by student
    student_attempts = {}
    for attempt in attempts:
        student = User.query.get(attempt.student_id)
        if student:
            if student.id not in student_attempts:
                student_attempts[student.id] = {
                    'student': student,
                    'attempts': []
                }
            student_attempts[student.id]['attempts'].append(attempt)

    return render_template('instructor/quiz_results.html',
                           quiz=quiz,
                           student_attempts=student_attempts)


@instructor.route('/quiz-attempt/<int:attempt_id>/review')
@login_required
@instructor_required
def review_quiz_attempt(attempt_id):
    attempt = QuizAttempt.query.get_or_404(attempt_id)
    quiz = Quiz.query.get(attempt.quiz_id)

    # Check if instructor owns this quiz's course
    if quiz.course.instructor_id != current_user.id:
        flash('You do not have permission to review this attempt.', 'danger')
        return redirect(url_for('instructor.quizzes'))

    # Get student info
    student = User.query.get(attempt.student_id)

    # Get all responses for this attempt with questions
    responses = QuizResponse.query.filter_by(attempt_id=attempt_id).all()

    # Organize responses by question
    response_data = {}
    for response in responses:
        question = Question.query.get(response.question_id)
        if question:
            response_data[question.id] = {
                'question': question,
                'response': response,
                'options': question.options if question.question_type in ['mcq', 'true_false'] else [],
                'answer': QuestionAnswer.query.filter_by(question_id=question.id).first()
            }

    return render_template('instructor/review_quiz_attempt.html',
                           attempt=attempt,
                           quiz=quiz,
                           student=student,
                           response_data=response_data)


@instructor.route('/quiz-response/<int:response_id>/grade', methods=['POST'])
@login_required
@instructor_required
def grade_quiz_response(response_id):
    response = QuizResponse.query.get_or_404(response_id)
    attempt = QuizAttempt.query.get(response.attempt_id)
    quiz = Quiz.query.get(attempt.quiz_id)

    # Check if instructor owns this quiz's course
    if quiz.course.instructor_id != current_user.id:
        flash('You do not have permission to grade this response.', 'danger')
        return redirect(url_for('instructor.quizzes'))

    # Update the response with instructor feedback and score
    is_correct = 'is_correct' in request.form
    points_earned = float(request.form.get('points_earned') or 0)
    instructor_feedback = request.form.get('instructor_feedback')

    response.is_correct = is_correct
    response.points_earned = points_earned
    response.instructor_feedback = instructor_feedback

    db.session.commit()

    # Recalculate the overall quiz score
    total_points = 0
    max_points = 0

    for resp in QuizResponse.query.filter_by(attempt_id=attempt.id).all():
        question = Question.query.get(resp.question_id)
        if question:
            total_points += resp.points_earned
            max_points += question.points

    attempt.score = total_points
    attempt.max_score = max_points
    attempt.percentage = (total_points / max_points *
                          100) if max_points > 0 else 0
    attempt.is_passed = attempt.percentage >= quiz.passing_score

    db.session.commit()

    flash('Response graded successfully!', 'success')
    return redirect(url_for('instructor.review_quiz_attempt', attempt_id=attempt.id))


# Assignment Routes
@instructor.route('/assignments')
@login_required
@instructor_required
def assignments():
    # Get all assignments for courses taught by this instructor
    instructor_courses = Course.query.filter_by(
        instructor_id=current_user.id).all()
    course_ids = [course.id for course in instructor_courses]

    assignments = Assignment.query.filter(Assignment.course_id.in_(
        course_ids)).order_by(Assignment.created_at.desc()).all()

    return render_template('instructor/assignments.html', assignments=assignments, courses=instructor_courses)


@instructor.route('/create-assignment', methods=['GET', 'POST'])
@login_required
@instructor_required
def create_assignment():
    # Get instructor's courses for the dropdown
    instructor_courses = Course.query.filter_by(
        instructor_id=current_user.id).all()

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        course_id = request.form.get('course_id')
        module_id = request.form.get('module_id') or None
        due_date_str = request.form.get('due_date')
        max_points = request.form.get('max_points') or 100
        allowed_extensions = request.form.get(
            'allowed_extensions') or 'pdf,doc,docx,zip'
        max_file_size = request.form.get('max_file_size') or 10
        plagiarism_check = 'plagiarism_check' in request.form

        # Parse due date
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid date format. Please use the date picker.', 'danger')
                return redirect(url_for('instructor.create_assignment'))

        # Create new assignment
        new_assignment = Assignment(
            title=title,
            description=description,
            course_id=course_id,
            module_id=module_id,
            created_by_id=current_user.id,
            due_date=due_date,
            max_points=max_points,
            allowed_file_extensions=allowed_extensions,
            max_file_size_mb=max_file_size,
            plagiarism_check=plagiarism_check
        )

        db.session.add(new_assignment)
        db.session.commit()

        # Create grade item for this assignment
        grade_item = GradeItem(
            course_id=course_id,
            title=title,
            description=f"Assignment: {title}",
            item_type='assignment',
            max_points=max_points,
            weight=1.0,  # Default weight
            assignment_id=new_assignment.id,
            due_date=due_date
        )

        db.session.add(grade_item)
        db.session.commit()

        flash('Assignment created successfully!', 'success')
        return redirect(url_for('instructor.assignment_submissions', assignment_id=new_assignment.id))

    return render_template('instructor/create_assignment.html', courses=instructor_courses)


@instructor.route('/edit-assignment/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
@instructor_required
def edit_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)

    # Check if instructor owns this assignment
    if assignment.created_by_id != current_user.id:
        flash('You do not have permission to edit this assignment.', 'danger')
        return redirect(url_for('instructor.assignments'))

    instructor_courses = Course.query.filter_by(
        instructor_id=current_user.id).all()

    if request.method == 'POST':
        assignment.title = request.form.get('title')
        assignment.description = request.form.get('description')
        assignment.course_id = request.form.get('course_id')
        assignment.module_id = request.form.get('module_id') or None
        due_date_str = request.form.get('due_date')
        assignment.max_points = request.form.get('max_points') or 100
        assignment.allowed_file_extensions = request.form.get(
            'allowed_extensions') or 'pdf,doc,docx,zip'
        assignment.max_file_size_mb = request.form.get('max_file_size') or 10
        assignment.plagiarism_check = 'plagiarism_check' in request.form

        # Parse due date
        if due_date_str:
            try:
                assignment.due_date = datetime.strptime(
                    due_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid date format. Please use the date picker.', 'danger')
                return redirect(url_for('instructor.edit_assignment', assignment_id=assignment_id))
        else:
            assignment.due_date = None

        db.session.commit()

        # Update corresponding grade item
        grade_item = GradeItem.query.filter_by(
            assignment_id=assignment_id).first()
        if grade_item:
            grade_item.title = assignment.title
            grade_item.description = f"Assignment: {assignment.title}"
            grade_item.course_id = assignment.course_id
            grade_item.max_points = assignment.max_points
            grade_item.due_date = assignment.due_date
            db.session.commit()
        else:
            # Create grade item if it doesn't exist
            grade_item = GradeItem(
                course_id=assignment.course_id,
                title=assignment.title,
                description=f"Assignment: {assignment.title}",
                item_type='assignment',
                max_points=assignment.max_points,
                weight=1.0,  # Default weight
                assignment_id=assignment_id,
                due_date=assignment.due_date
            )
            db.session.add(grade_item)
            db.session.commit()

        flash('Assignment updated successfully!', 'success')
        return redirect(url_for('instructor.assignment_submissions', assignment_id=assignment.id))

    # Get modules for the selected course
    modules = Module.query.filter_by(course_id=assignment.course_id).all()

    return render_template('instructor/edit_assignment.html',
                           assignment=assignment,
                           courses=instructor_courses,
                           modules=modules)


@instructor.route('/assignment/<int:assignment_id>/submissions')
@login_required
@instructor_required
def assignment_submissions(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)

    # Check if instructor owns this assignment
    if assignment.created_by_id != current_user.id:
        flash('You do not have permission to view these submissions.', 'danger')
        return redirect(url_for('instructor.assignments'))

    # Get all submissions for this assignment
    submissions = AssignmentSubmission.query.filter_by(
        assignment_id=assignment_id).order_by(AssignmentSubmission.submitted_at.desc()).all()

    # Get student info for each submission
    submission_data = []
    for submission in submissions:
        student = User.query.get(submission.student_id)
        if student:
            submission_data.append({
                'submission': submission,
                'student': student
            })

    return render_template('instructor/assignment_submissions.html',
                           assignment=assignment,
                           submission_data=submission_data)


@instructor.route('/submission/<int:submission_id>/grade', methods=['GET', 'POST'])
@login_required
@instructor_required
def grade_submission(submission_id):
    submission = AssignmentSubmission.query.get_or_404(submission_id)
    assignment = Assignment.query.get(submission.assignment_id)

    # Check if instructor owns this assignment
    if assignment.created_by_id != current_user.id:
        flash('You do not have permission to grade this submission.', 'danger')
        return redirect(url_for('instructor.assignments'))

    student = User.query.get(submission.student_id)

    if request.method == 'POST':
        points = request.form.get('points')
        feedback = request.form.get('feedback')

        # Update submission
        submission.points = points
        submission.feedback = feedback
        submission.graded_by_id = current_user.id
        submission.graded_at = datetime.now()
        db.session.commit()

        # Update or create corresponding grade item
        grade_item = GradeItem.query.filter_by(
            assignment_id=assignment.id).first()

        if not grade_item:
            # Create grade item if it doesn't exist
            grade_item = GradeItem(
                course_id=assignment.course_id,
                title=assignment.title,
                description=f"Assignment: {assignment.title}",
                item_type='assignment',
                max_points=assignment.max_points,
                weight=1.0,  # Default weight
                assignment_id=assignment.id,
                due_date=assignment.due_date
            )
            db.session.add(grade_item)
            db.session.commit()

        # Update or create student grade
        student_grade = StudentGrade.query.filter_by(
            grade_item_id=grade_item.id,
            student_id=student.id
        ).first()

        if student_grade:
            student_grade.points = points
            student_grade.feedback = feedback
            student_grade.graded_by_id = current_user.id
            student_grade.graded_at = datetime.now()
        else:
            student_grade = StudentGrade(
                grade_item_id=grade_item.id,
                student_id=student.id,
                points=points,
                feedback=feedback,
                graded_by_id=current_user.id,
                graded_at=datetime.now()
            )
            db.session.add(student_grade)

        db.session.commit()

        # Send notification to student
        message = Message(
            sender_id=current_user.id,
            recipient_id=student.id,
            subject=f"Assignment Graded: {assignment.title}",
            content=f"Your submission for '{assignment.title}' has been graded.\n\nGrade: {points}/{assignment.max_points}\n\nFeedback: {feedback}",
            is_read=False,
            created_at=datetime.now()
        )
        db.session.add(message)
        db.session.commit()

        flash('Submission graded successfully!', 'success')
        return redirect(url_for('instructor.assignment_submissions', assignment_id=assignment.id))

    return render_template('instructor/grade_submission.html',
                           submission=submission,
                           assignment=assignment,
                           student=student)


# Notes Management Routes
@instructor.route('/notes')
@login_required
@instructor_required
def notes():
    # Get all notes for the instructor's courses
    instructor_courses = Course.query.filter_by(
        instructor_id=current_user.id).all()
    course_ids = [course.id for course in instructor_courses]

    notes_list = Notes.query.filter(
        Notes.course_id.in_(course_ids),
        Notes.instructor_id == current_user.id
    ).order_by(Notes.created_at.desc()).all()

    return render_template('instructor/notes.html',
                           notes=notes_list,
                           courses=instructor_courses)


@instructor.route('/create-note', methods=['GET', 'POST'])
@login_required
@instructor_required
def create_note():
    # Get instructor's courses for the dropdown
    instructor_courses = Course.query.filter_by(
        instructor_id=current_user.id).all()

    # Get instructor's batches for the dropdown
    course_ids = [course.id for course in instructor_courses]
    batches = Batch.query.filter(Batch.course_id.in_(course_ids)).all()

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        course_id = request.form.get('course_id')
        batch_id = request.form.get('batch_id') or None
        is_published = 'is_published' in request.form

        # Validate inputs
        if not title or not content or not course_id:
            flash('Please fill all required fields.', 'danger')
            return redirect(url_for('instructor.create_note'))

        # Check if course belongs to the instructor
        course = Course.query.get(course_id)
        if not course or course.instructor_id != current_user.id:
            flash('Invalid course selected.', 'danger')
            return redirect(url_for('instructor.create_note'))

        # Check if batch belongs to the course
        if batch_id:
            batch = Batch.query.get(batch_id)
            if not batch or batch.course_id != int(course_id):
                flash('Invalid batch selected.', 'danger')
                return redirect(url_for('instructor.create_note'))

        # Handle file upload if present
        file_path = None
        if 'note_file' in request.files:
            file = request.files['note_file']
            if file and file.filename != '' and allowed_file(file.filename, 'document'):
                unique_filename = save_file(file, 'pdf')
                if unique_filename:
                    file_path = os.path.join('pdf', unique_filename)

        # Create new note
        note = Notes(
            title=title,
            content=content,
            file_path=file_path,
            course_id=course_id,
            batch_id=batch_id,
            instructor_id=current_user.id,
            is_published=is_published
        )

        db.session.add(note)
        db.session.commit()

        flash('Note created successfully!', 'success')
        return redirect(url_for('instructor.notes'))

    return render_template('instructor/create_note.html',
                           courses=instructor_courses,
                           batches=batches)


@instructor.route('/edit-note/<int:note_id>', methods=['GET', 'POST'])
@login_required
@instructor_required
def edit_note(note_id):
    note = Notes.query.get_or_404(note_id)

    # Check if note belongs to the instructor
    if note.instructor_id != current_user.id:
        flash('You do not have permission to edit this note.', 'danger')
        return redirect(url_for('instructor.notes'))

    # Get instructor's courses for the dropdown
    instructor_courses = Course.query.filter_by(
        instructor_id=current_user.id).all()

    # Get instructor's batches for the dropdown
    course_ids = [course.id for course in instructor_courses]
    batches = Batch.query.filter(Batch.course_id.in_(course_ids)).all()

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        course_id = request.form.get('course_id')
        batch_id = request.form.get('batch_id') or None
        is_published = 'is_published' in request.form

        # Validate inputs
        if not title or not content or not course_id:
            flash('Please fill all required fields.', 'danger')
            return redirect(url_for('instructor.edit_note', note_id=note_id))

        # Check if course belongs to the instructor
        course = Course.query.get(course_id)
        if not course or course.instructor_id != current_user.id:
            flash('Invalid course selected.', 'danger')
            return redirect(url_for('instructor.edit_note', note_id=note_id))

        # Check if batch belongs to the course
        if batch_id:
            batch = Batch.query.get(batch_id)
            if not batch or batch.course_id != int(course_id):
                flash('Invalid batch selected.', 'danger')
                return redirect(url_for('instructor.edit_note', note_id=note_id))

        # Handle file upload if present
        if 'note_file' in request.files:
            file = request.files['note_file']
            if file and file.filename != '' and allowed_file(file.filename, 'document'):
                # Delete old file if exists
                if note.file_path:
                    old_file_path = os.path.join(
                        current_app.config['UPLOAD_FOLDER'], note.file_path)
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)

                unique_filename = save_file(file, 'pdf')
                if unique_filename:
                    note.file_path = os.path.join('pdf', unique_filename)

        # Update note
        note.title = title
        note.content = content
        note.course_id = course_id
        note.batch_id = batch_id
        note.is_published = is_published
        note.updated_at = datetime.utcnow()

        db.session.commit()

        flash('Note updated successfully!', 'success')
        return redirect(url_for('instructor.notes'))

    return render_template('instructor/edit_note.html',
                           note=note,
                           courses=instructor_courses,
                           batches=batches)


@instructor.route('/delete-note/<int:note_id>', methods=['POST'])
@login_required
@instructor_required
def delete_note(note_id):
    note = Notes.query.get_or_404(note_id)

    # Check if note belongs to the instructor
    if note.instructor_id != current_user.id:
        flash('You do not have permission to delete this note.', 'danger')
        return redirect(url_for('instructor.notes'))

    # Delete file if exists
    if note.file_path:
        file_path = os.path.join('app/static/uploads/', note.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)

    db.session.delete(note)
    db.session.commit()

    flash('Note deleted successfully!', 'success')
    return redirect(url_for('instructor.notes'))


@instructor.route('/batch/<int:batch_id>/add-students', methods=['GET', 'POST'])
@login_required
@instructor_required
def add_students_to_batch(batch_id):
    batch = Batch.query.get_or_404(batch_id)

    # Check if batch belongs to instructor's course
    course = Course.query.get(batch.course_id)
    if not course or course.instructor_id != current_user.id:
        flash('You do not have permission to add students to this batch.', 'danger')
        return redirect(url_for('instructor.batches'))

    # Get currently enrolled students
    enrolled_students = User.query.join(BatchEnrollment).filter(
        BatchEnrollment.batch_id == batch_id).all()
    enrolled_ids = [student.id for student in enrolled_students]
    enrolled_count = len(enrolled_ids)

    # Get all students who are not enrolled in this batch
    search_term = request.args.get('search', '')

    if search_term:
        # Filter students by search term
        available_students = User.query.filter(
            User.role == UserRole.STUDENT,  # Student role
            ~User.id.in_(enrolled_ids) if enrolled_ids else True,
            db.or_(
                User.email.contains(search_term),
                db.func.lower(User.first_name + ' ' +
                              User.last_name).contains(search_term.lower())
            )
        ).all()
    else:
        # Get all unenrolled students
        available_students = User.query.filter(
            User.role == UserRole.STUDENT,  # Student role
            ~User.id.in_(enrolled_ids) if enrolled_ids else True
        ).all()

    # Add enrolled courses count to each student
    for student in available_students:
        student.enrolled_courses_count = BatchEnrollment.query.filter_by(
            student_id=student.id).count()

    if request.method == 'POST':
        student_ids = request.form.getlist('student_ids[]')

        if not student_ids:
            flash('No students selected.', 'warning')
            return redirect(url_for('instructor.add_students_to_batch', batch_id=batch_id))

        # Check if adding these students would exceed batch capacity
        if batch.max_students > 0 and enrolled_count + len(student_ids) > batch.max_students:
            flash(
                f'Cannot add {len(student_ids)} students. Batch capacity would be exceeded. Only {batch.max_students - enrolled_count} slots available.', 'danger')
            return redirect(url_for('instructor.add_students_to_batch', batch_id=batch_id))

        # Add students to batch
        enrollment_date = datetime.now().date()
        added_count = 0
        already_enrolled = 0

        for student_id in student_ids:
            # Check if student is already enrolled
            existing_enrollment = BatchEnrollment.query.filter_by(
                batch_id=batch_id, student_id=int(student_id)).first()

            if not existing_enrollment:
                enrollment = BatchEnrollment(
                    batch_id=batch_id,
                    student_id=int(student_id),
                    enrollment_date=enrollment_date
                )
                db.session.add(enrollment)
                added_count += 1

                # Also enroll in course if not already enrolled
                course_enrollment = Enrollment.query.filter_by(
                    student_id=int(student_id),
                    course_id=batch.course_id
                ).first()

                if not course_enrollment:
                    course_enrollment = Enrollment(
                        student_id=int(student_id),
                        course_id=batch.course_id,
                        enrollment_date=enrollment_date
                    )
                    db.session.add(course_enrollment)
            else:
                already_enrolled += 1

        db.session.commit()

        if added_count > 0:
            flash(
                f'Successfully added {added_count} students to the batch.', 'success')

        if already_enrolled > 0:
            flash(
                f'{already_enrolled} students were already enrolled and skipped.', 'info')

        return redirect(url_for('instructor.batch_students', batch_id=batch_id))

    return render_template('instructor/add_students_to_batch.html',
                           batch=batch,
                           available_students=available_students,
                           enrolled_count=enrolled_count,
                           search_term=search_term)


@instructor.route('/course/<int:course_id>/subcontent/create', methods=['GET', 'POST'])
@login_required
@instructor_required
def create_subcontent(course_id):
    course = Course.query.get_or_404(course_id)

    # Ensure instructor owns this course
    if course.instructor_id != current_user.id:
        flash('You do not have permission to edit this course.', 'danger')
        return redirect(url_for('instructor.courses'))

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        content_type = request.form.get('content_type')

        # Get the highest order number and add 1
        highest_order = db.session.query(db.func.max(SubContent.order)).filter_by(
            course_id=course_id).scalar() or -1
        new_order = highest_order + 1

        new_subcontent = SubContent(
            title=title,
            content=content,
            content_type=content_type,
            course_id=course_id,
            order=new_order
        )

        db.session.add(new_subcontent)
        db.session.commit()

        flash('Subcontent created successfully!', 'success')
        return redirect(url_for('instructor.course_curriculum', course_id=course_id))

    return render_template('instructor/create_subcontent.html', course=course)


@instructor.route('/subcontent/<int:subcontent_id>/edit', methods=['GET', 'POST'])
@login_required
@instructor_required
def edit_subcontent(subcontent_id):
    subcontent = SubContent.query.get_or_404(subcontent_id)
    course = Course.query.get_or_404(subcontent.course_id)

    # Ensure instructor owns this course
    if course.instructor_id != current_user.id:
        flash('You do not have permission to edit this subcontent.', 'danger')
        return redirect(url_for('instructor.courses'))

    if request.method == 'POST':
        subcontent.title = request.form.get('title')
        subcontent.content = request.form.get('content')
        content_type = request.form.get('content_type')

        # Only update content type if it's the same category (file vs text)
        if (subcontent.content_type == 'text' and content_type == 'text') or \
           (subcontent.content_type in ['video', 'audio', 'pdf'] and content_type in ['video', 'audio', 'pdf']):
            subcontent.content_type = content_type

        # Handle file upload for video, audio, pdf
        if subcontent.content_type in ['video', 'audio', 'pdf']:
            if 'file' in request.files:
                file = request.files['file']
                if file and file.filename:
                    # Delete old file if exists
                    if subcontent.file_path:
                        old_file_path = os.path.join(
                            current_app.config['UPLOAD_FOLDER'], subcontent.file_path)
                        if os.path.exists(old_file_path):
                            os.remove(old_file_path)

                    # Use the utility function to save file with unique name
                    unique_filename = save_file(file, subcontent.content_type)
                    if unique_filename:
                        subcontent.file_path = os.path.join(
                            subcontent.content_type, unique_filename)

        db.session.commit()
        flash('Subcontent updated successfully!', 'success')
        return redirect(url_for('instructor.course_curriculum', course_id=course.id))

    return render_template('instructor/edit_subcontent.html',
                           subcontent=subcontent,
                           course=course)


@instructor.route('/subcontent/<int:subcontent_id>/delete', methods=['POST'])
@login_required
@instructor_required
def delete_subcontent(subcontent_id):
    subcontent = SubContent.query.get_or_404(subcontent_id)

    # Check if subcontent belongs to the instructor
    if subcontent.course.instructor_id != current_user.id:
        flash('You do not have permission to delete this subcontent.', 'danger')
        return redirect(url_for('instructor.courses'))

    # Delete file if exists
    if subcontent.file_path:
        file_path = os.path.join(
            current_app.config['UPLOAD_FOLDER'], subcontent.file_path.replace('\\', '/'))
        if os.path.exists(file_path):
            os.remove(file_path)

    db.session.delete(subcontent)
    db.session.commit()

    flash('Subcontent deleted successfully!', 'success')
    return redirect(url_for('instructor.course_curriculum', course_id=subcontent.course_id))


@instructor.route('/topic/<int:topic_id>/add-subcontent', methods=['GET', 'POST'])
@login_required
@instructor_required
def add_subcontent(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    lesson = Lesson.query.get_or_404(topic.lesson_id)
    module = Module.query.get_or_404(lesson.module_id)
    course = Course.query.get_or_404(module.course_id)

    # Ensure instructor owns this course
    if course.instructor_id != current_user.id:
        flash('You do not have permission to edit this topic.', 'danger')
        return redirect(url_for('instructor.courses'))

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        content_type = request.form.get('content_type')

        # Get the highest order number and add 1
        highest_order = db.session.query(db.func.max(SubContent.order)).filter_by(
            topic_id=topic_id).scalar() or -1
        new_order = highest_order + 1

        new_subcontent = SubContent(
            title=title,
            content=content,
            content_type=content_type,
            topic_id=topic_id,
            order=new_order
        )

        # Handle file upload for pdf
        if content_type == 'pdf':
            if 'file' in request.files:
                file = request.files['file']
                if file and file.filename:
                    # Use the utility function to save file with unique name
                    unique_filename = save_file(file, 'pdf')
                    if unique_filename:
                        # Ensure forward slashes are used for file paths
                        file_path = normalize_path('pdf/' + unique_filename)
                        new_subcontent.file_path = file_path

        db.session.add(new_subcontent)
        db.session.commit()

        flash('Resource added successfully!', 'success')
        return redirect(url_for('instructor.edit_topic', topic_id=topic_id))

    return render_template('instructor/create_subcontent.html',
                           topic=topic,
                           lesson=lesson,
                           module=module,
                           course=course)


@instructor.route('/subcontent/<int:subcontent_id>/edit', methods=['GET', 'POST'])
@login_required
@instructor_required
def edit_subcontent_item(subcontent_id):
    subcontent = SubContent.query.get_or_404(subcontent_id)
    topic = Topic.query.get_or_404(subcontent.topic_id)
    lesson = Lesson.query.get_or_404(topic.lesson_id)
    module = Module.query.get_or_404(lesson.module_id)
    course = Course.query.get_or_404(module.course_id)

    # Ensure instructor owns this course
    if course.instructor_id != current_user.id:
        flash('You do not have permission to edit this subcontent.', 'danger')
        return redirect(url_for('instructor.courses'))

    if request.method == 'POST':
        subcontent.title = request.form.get('title')
        subcontent.content = request.form.get('content')
        content_type = request.form.get('content_type')

        # Only update content type if it's the same category (file vs text)
        if (subcontent.content_type == 'text' and content_type == 'text') or \
           (subcontent.content_type == 'pdf' and content_type == 'pdf'):
            subcontent.content_type = content_type

        # Handle file upload for pdf
        if subcontent.content_type == 'pdf':
            if 'file' in request.files:
                file = request.files['file']
                if file and file.filename:
                    # Delete old file if exists
                    if subcontent.file_path:
                        old_file_path = os.path.join(
                            current_app.config['UPLOAD_FOLDER'], normalize_path(subcontent.file_path))
                        if os.path.exists(old_file_path):
                            os.remove(old_file_path)

                    # Use the utility function to save file with unique name
                    unique_filename = save_file(file, 'pdf')
                    if unique_filename:
                        # Ensure forward slashes are used for file paths
                        file_path = normalize_path('pdf/' + unique_filename)
                        subcontent.file_path = file_path

        db.session.commit()
        flash('Resource updated successfully!', 'success')
        return redirect(url_for('instructor.edit_topic', topic_id=topic.id))

    return render_template('instructor/edit_subcontent.html',
                           subcontent=subcontent,
                           topic=topic,
                           lesson=lesson,
                           module=module,
                           course=course)


@instructor.route('/subcontent/<int:subcontent_id>/delete', methods=['POST'])
@login_required
@instructor_required
def delete_subcontent_item(subcontent_id):
    subcontent = SubContent.query.get_or_404(subcontent_id)
    topic = Topic.query.get_or_404(subcontent.topic_id)
    lesson = Lesson.query.get_or_404(topic.lesson_id)
    module = Module.query.get_or_404(lesson.module_id)
    course = Course.query.get_or_404(module.course_id)

    # Check if subcontent belongs to the instructor
    if course.instructor_id != current_user.id:
        flash('You do not have permission to delete this subcontent.', 'danger')
        return redirect(url_for('instructor.courses'))

    # Delete file if exists
    if subcontent.file_path:
        file_path = os.path.join(
            current_app.config['UPLOAD_FOLDER'], subcontent.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)

    db.session.delete(subcontent)
    db.session.commit()

    flash('Subcontent deleted successfully!', 'success')
    return redirect(url_for('instructor.edit_topic', topic_id=topic.id))


# Message Routes
@instructor.route('/messages')
@login_required
@instructor_required
def messages():
    # Get received messages
    received_messages = Message.query.filter_by(
        recipient_id=current_user.id
    ).order_by(Message.sent_at.desc()).all()

    # Get sent messages
    sent_messages = Message.query.filter_by(
        sender_id=current_user.id
    ).order_by(Message.sent_at.desc()).all()

    return render_template('instructor/messages.html',
                           received_messages=received_messages,
                           sent_messages=sent_messages)


@instructor.route('/send-message', methods=['GET', 'POST'])
@login_required
@instructor_required
def send_message():
    if request.method == 'POST':
        recipient_id = request.form.get('recipient_id')
        subject = request.form.get('subject')
        content = request.form.get('content')

        # Validate recipient
        recipient = User.query.get(recipient_id)
        if not recipient:
            flash('Invalid recipient.', 'danger')
            return redirect(url_for('instructor.send_message'))

        # Create message
        message = Message(
            sender_id=current_user.id,
            recipient_id=recipient_id,
            subject=subject,
            content=content
        )

        db.session.add(message)
        db.session.commit()

        flash('Message sent successfully!', 'success')
        return redirect(url_for('instructor.messages'))

    # Get potential recipients (students enrolled in instructor's courses)
    instructor_courses = Course.query.filter_by(
        instructor_id=current_user.id).all()
    course_ids = [course.id for course in instructor_courses]

    enrollments = Enrollment.query.filter(
        Enrollment.course_id.in_(course_ids)).all()
    students = []
    for enrollment in enrollments:
        student = User.query.get(enrollment.student_id)
        if student and student not in students:
            students.append(student)

    return render_template('instructor/send_message.html', students=students)


@instructor.route('/message/<int:message_id>')
@login_required
@instructor_required
def view_message(message_id):
    message = Message.query.get_or_404(message_id)

    # Check if message belongs to current user
    if message.recipient_id != current_user.id and message.sender_id != current_user.id:
        flash('You do not have permission to view this message.', 'danger')
        return redirect(url_for('instructor.messages'))

    # Mark as read if current user is recipient
    if message.recipient_id == current_user.id and not message.is_read:
        message.is_read = True
        db.session.commit()

    # Get sender and recipient info
    sender = User.query.get(message.sender_id)
    recipient = User.query.get(message.recipient_id)

    return render_template('instructor/view_message.html',
                           message=message,
                           sender=sender,
                           recipient=recipient)


@instructor.route('/reply-message/<int:message_id>', methods=['GET', 'POST'])
@login_required
@instructor_required
def reply_message(message_id):
    original_message = Message.query.get_or_404(message_id)

    # Check if message belongs to current user
    if original_message.recipient_id != current_user.id and original_message.sender_id != current_user.id:
        flash('You do not have permission to reply to this message.', 'danger')
        return redirect(url_for('instructor.messages'))

    if request.method == 'POST':
        content = request.form.get('content')

        # Determine recipient (the other party in the conversation)
        recipient_id = original_message.sender_id if original_message.recipient_id == current_user.id else original_message.recipient_id

        # Create reply message
        subject = f"Re: {original_message.subject}"
        reply = Message(
            sender_id=current_user.id,
            recipient_id=recipient_id,
            subject=subject,
            content=content,
            parent_message_id=message_id
        )

        db.session.add(reply)
        db.session.commit()

        flash('Reply sent successfully!', 'success')
        return redirect(url_for('instructor.messages'))

    # Get the other party's info
    if original_message.sender_id == current_user.id:
        other_user = User.query.get(original_message.recipient_id)
    else:
        other_user = User.query.get(original_message.sender_id)

    return render_template('instructor/reply_message.html',
                           original_message=original_message,
                           other_user=other_user)


@instructor.route('/api/course/<int:course_id>/modules', methods=['GET'])
@login_required
@instructor_required
def get_course_modules(course_id):
    """API endpoint to get modules for a specific course"""
    course = Course.query.get_or_404(course_id)

    # Check if instructor owns this course
    if course.instructor_id != current_user.id:
        return jsonify({'error': 'You do not have permission to access this course'}), 403

    modules = Module.query.filter_by(
        course_id=course_id).order_by(Module.order).all()
    modules_data = [{'id': module.id, 'title': module.title}
                    for module in modules]

    return jsonify({'modules': modules_data})


@instructor.route('/course/<int:course_id>/add-student', methods=['POST'])
@login_required
@instructor_required
def add_student_to_course(course_id):
    course = Course.query.get_or_404(course_id)

    # Ensure instructor owns this course
    if course.instructor_id != current_user.id:
        flash('You do not have permission to modify this course.', 'danger')
        return redirect(url_for('instructor.courses'))

    student_email = request.form.get('student_email')

    # Find student by email
    student = User.query.filter_by(
        email=student_email, role=UserRole.STUDENT).first()

    if not student:
        flash('Student not found with this email.', 'danger')
        return redirect(url_for('instructor.course_details', course_id=course_id))

    # Check if student is already enrolled in the course
    existing_enrollment = Enrollment.query.filter_by(
        student_id=student.id,
        course_id=course_id
    ).first()

    if existing_enrollment:
        flash('Student is already enrolled in this course.', 'warning')
        return redirect(url_for('instructor.course_details', course_id=course_id))

    # Enroll student in course
    enrollment = Enrollment(
        student_id=student.id,
        course_id=course_id,
        enrollment_date=datetime.utcnow()
    )
    db.session.add(enrollment)
    db.session.commit()

    flash(
        f'Student {student.first_name} {student.last_name} added to course successfully!', 'success')
    return redirect(url_for('instructor.course_details', course_id=course_id))


@instructor.route('/course/<int:course_id>/remove-student', methods=['POST'])
@login_required
@instructor_required
def remove_student_from_course(course_id):
    course = Course.query.get_or_404(course_id)

    # Ensure instructor owns this course
    if course.instructor_id != current_user.id:
        flash('You do not have permission to modify this course.', 'danger')
        return redirect(url_for('instructor.courses'))

    student_id = request.form.get('student_id')

    if not student_id:
        flash('Student ID is required.', 'danger')
        return redirect(url_for('instructor.course_details', course_id=course_id))

    # Find enrollment
    enrollment = Enrollment.query.filter_by(
        student_id=student_id,
        course_id=course_id
    ).first()

    if not enrollment:
        flash('Student is not enrolled in this course.', 'warning')
        return redirect(url_for('instructor.course_details', course_id=course_id))

    # Remove student from any batches in this course
    batch_enrollments = BatchEnrollment.query.join(Batch).filter(
        BatchEnrollment.student_id == student_id,
        Batch.course_id == course_id
    ).all()

    for batch_enrollment in batch_enrollments:
        db.session.delete(batch_enrollment)

    # Delete enrollment
    db.session.delete(enrollment)
    db.session.commit()

    flash('Student removed from course successfully!', 'success')
    return redirect(url_for('instructor.course_details', course_id=course_id))


@instructor.route('/live-class/<int:class_id>/cancel', methods=['POST'])
@login_required
@instructor_required
def cancel_live_class(class_id):
    live_class = LiveClass.query.get_or_404(class_id)

    # Check if instructor has access to this class
    batch = Batch.query.get(live_class.batch_id)
    if not batch:
        flash('Batch not found.', 'danger')
        return redirect(url_for('instructor.live_classes'))

    course = Course.query.get(batch.course_id)
    if not course or course.instructor_id != current_user.id:
        flash('You do not have permission to cancel this class.', 'danger')
        return redirect(url_for('instructor.live_classes'))

    # Store batch_id before deleting the class
    batch_id = live_class.batch_id

    # Delete the class
    db.session.delete(live_class)
    db.session.commit()

    flash('Live class has been cancelled successfully.', 'success')
    return redirect(url_for('instructor.batch_students', batch_id=batch_id))
