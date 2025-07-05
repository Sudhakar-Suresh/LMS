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
from app.models.user import Assignment, AssignmentSubmission, Notes
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
    batches = Batch.query.filter(Batch.course_id.in_(course_ids)).all()

    return render_template('instructor/batches.html', batches=batches, courses=instructor_courses)


@instructor.route('/create-batch', methods=['GET', 'POST'])
@login_required
@instructor_required
def create_batch():
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

        # Validate inputs
        if not name or not course_id or not start_date or not end_date:
            flash('Please fill all required fields.', 'danger')
            return redirect(url_for('instructor.create_batch'))

        # Check if course belongs to the instructor
        course = Course.query.get(course_id)
        if not course or course.instructor_id != current_user.id:
            flash('Invalid course selected.', 'danger')
            return redirect(url_for('instructor.create_batch'))

        # Create new batch
        batch = Batch(
            name=name,
            course_id=course_id,
            start_date=start_date,
            end_date=end_date,
            max_students=max_students if max_students else 30,
            description=description
        )

        db.session.add(batch)
        db.session.commit()

        flash('Batch created successfully!', 'success')
        return redirect(url_for('instructor.batches'))

    return render_template('instructor/create_batch.html', courses=instructor_courses)


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

        db.session.commit()

        flash('Batch updated successfully!', 'success')
        return redirect(url_for('instructor.batches'))

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

    # Get all students in the batch
    enrollments = BatchEnrollment.query.filter_by(batch_id=batch_id).all()
    students = []
    for enrollment in enrollments:
        student = User.query.get(enrollment.student_id)
        if student:
            students.append({
                'id': student.id,
                'name': f"{student.first_name} {student.last_name}",
                'email': student.email,
                'enrollment_date': enrollment.enrollment_date
            })

    return render_template('instructor/batch_students.html', batch=batch, students=students)


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

    if request.method == 'POST':
        student_email = request.form.get('student_email')

        # Find student by email
        student = User.query.filter_by(
            email=student_email, role=UserRole.STUDENT).first()

        if not student:
            flash('Student not found with this email.', 'danger')
            return redirect(url_for('instructor.add_student_to_batch', batch_id=batch_id))

        # Check if student is already enrolled in the batch
        existing_enrollment = BatchEnrollment.query.filter_by(
            batch_id=batch_id,
            student_id=student.id
        ).first()

        if existing_enrollment:
            flash('Student is already enrolled in this batch.', 'warning')
            return redirect(url_for('instructor.batch_students', batch_id=batch_id))

        # Check if batch has reached maximum capacity
        current_enrollments = BatchEnrollment.query.filter_by(
            batch_id=batch_id).count()
        if current_enrollments >= batch.max_students:
            flash('Batch has reached maximum capacity.', 'danger')
            return redirect(url_for('instructor.batch_students', batch_id=batch_id))

        # Enroll student in batch
        enrollment = BatchEnrollment(
            batch_id=batch_id,
            student_id=student.id,
            enrollment_date=datetime.utcnow()
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
                enrollment_date=datetime.utcnow()
            )
            db.session.add(course_enrollment)

        db.session.add(enrollment)
        db.session.commit()

        flash(
            f'Student {student.first_name} {student.last_name} added to batch successfully!', 'success')
        return redirect(url_for('instructor.batch_students', batch_id=batch_id))

    return render_template('instructor/add_student_to_batch.html', batch=batch)


# Live Class Management Routes
@instructor.route('/live-classes')
@login_required
@instructor_required
def live_classes():
    # Get all live classes for the instructor
    classes = LiveClass.query.filter_by(instructor_id=current_user.id).all()

    # Group classes by batch
    classes_by_batch = {}
    for cls in classes:
        batch = Batch.query.get(cls.batch_id)
        if batch:
            if batch.id not in classes_by_batch:
                classes_by_batch[batch.id] = {
                    'batch': batch,
                    'classes': []
                }
            classes_by_batch[batch.id]['classes'].append(cls)

    return render_template('instructor/live_classes.html', classes_by_batch=classes_by_batch)


@instructor.route('/create-live-class', methods=['GET', 'POST'])
@login_required
@instructor_required
def create_live_class():
    # Get instructor's batches for the dropdown
    instructor_courses = Course.query.filter_by(
        instructor_id=current_user.id).all()
    course_ids = [course.id for course in instructor_courses]
    batches = Batch.query.filter(Batch.course_id.in_(course_ids)).all()

    if request.method == 'POST':
        title = request.form.get('title')
        batch_id = request.form.get('batch_id')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        platform = request.form.get('platform')
        meeting_link = request.form.get('meeting_link')
        meeting_id = request.form.get('meeting_id')
        meeting_password = request.form.get('meeting_password')
        description = request.form.get('description')
        is_recurring = 'is_recurring' in request.form
        recurrence_pattern = request.form.get(
            'recurrence_pattern') if is_recurring else None

        # Validate inputs
        if not title or not batch_id or not start_time_str or not end_time_str or not platform:
            flash('Please fill all required fields.', 'danger')
            return redirect(url_for('instructor.create_live_class'))

        # Parse datetime strings
        try:
            start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date/time format.', 'danger')
            return redirect(url_for('instructor.create_live_class'))

        # Check if batch belongs to instructor's course
        batch = Batch.query.get(batch_id)
        if not batch or batch.course.instructor_id != current_user.id:
            flash('Invalid batch selected.', 'danger')
            return redirect(url_for('instructor.create_live_class'))

        # Create new live class
        live_class = LiveClass(
            title=title,
            batch_id=batch_id,
            instructor_id=current_user.id,
            start_time=start_time,
            end_time=end_time,
            platform=platform,
            meeting_link=meeting_link,
            meeting_id=meeting_id,
            meeting_password=meeting_password,
            description=description,
            is_recurring=is_recurring,
            recurrence_pattern=recurrence_pattern
        )

        db.session.add(live_class)
        db.session.commit()

        flash('Live class scheduled successfully!', 'success')
        return redirect(url_for('instructor.live_classes'))

    return render_template('instructor/create_live_class.html', batches=batches)


@instructor.route('/edit-live-class/<int:class_id>', methods=['GET', 'POST'])
@login_required
@instructor_required
def edit_live_class(class_id):
    live_class = LiveClass.query.get_or_404(class_id)

    # Check if class belongs to instructor
    if live_class.instructor_id != current_user.id:
        flash('You do not have permission to edit this class.', 'danger')
        return redirect(url_for('instructor.live_classes'))

    # Get instructor's batches for the dropdown
    instructor_courses = Course.query.filter_by(
        instructor_id=current_user.id).all()
    course_ids = [course.id for course in instructor_courses]
    batches = Batch.query.filter(Batch.course_id.in_(course_ids)).all()

    if request.method == 'POST':
        title = request.form.get('title')
        batch_id = request.form.get('batch_id')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        platform = request.form.get('platform')
        meeting_link = request.form.get('meeting_link')
        meeting_id = request.form.get('meeting_id')
        meeting_password = request.form.get('meeting_password')
        description = request.form.get('description')
        is_recurring = 'is_recurring' in request.form
        recurrence_pattern = request.form.get(
            'recurrence_pattern') if is_recurring else None

        # Validate inputs
        if not title or not batch_id or not start_time_str or not end_time_str or not platform:
            flash('Please fill all required fields.', 'danger')
            return redirect(url_for('instructor.edit_live_class', class_id=class_id))

        # Parse datetime strings
        try:
            start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date/time format.', 'danger')
            return redirect(url_for('instructor.edit_live_class', class_id=class_id))

        # Check if batch belongs to instructor's course
        batch = Batch.query.get(batch_id)
        if not batch or batch.course.instructor_id != current_user.id:
            flash('Invalid batch selected.', 'danger')
            return redirect(url_for('instructor.edit_live_class', class_id=class_id))

        # Update live class
        live_class.title = title
        live_class.batch_id = batch_id
        live_class.start_time = start_time
        live_class.end_time = end_time
        live_class.platform = platform
        live_class.meeting_link = meeting_link
        live_class.meeting_id = meeting_id
        live_class.meeting_password = meeting_password
        live_class.description = description
        live_class.is_recurring = is_recurring
        live_class.recurrence_pattern = recurrence_pattern

        db.session.commit()

        flash('Live class updated successfully!', 'success')
        return redirect(url_for('instructor.live_classes'))

    return render_template('instructor/edit_live_class.html', live_class=live_class, batches=batches)


@instructor.route('/live-class/<int:class_id>/attendance', methods=['GET', 'POST'])
@login_required
@instructor_required
def class_attendance(class_id):
    live_class = LiveClass.query.get_or_404(class_id)

    # Check if class belongs to instructor
    if live_class.instructor_id != current_user.id:
        flash('You do not have permission to view this class.', 'danger')
        return redirect(url_for('instructor.live_classes'))

    batch = Batch.query.get(live_class.batch_id)

    # Get all students in the batch
    batch_students = User.query.join(BatchEnrollment).filter(
        BatchEnrollment.batch_id == batch.id).all()

    if request.method == 'POST':
        # Process attendance form
        for student in batch_students:
            status = request.form.get(f'status_{student.id}')
            join_time_str = request.form.get(f'join_time_{student.id}')
            leave_time_str = request.form.get(f'leave_time_{student.id}')

            # Parse times if provided
            join_time = None
            leave_time = None
            duration_minutes = None

            if join_time_str:
                try:
                    join_time = datetime.strptime(join_time_str, '%H:%M')
                    join_time = datetime.combine(
                        live_class.start_time.date(), join_time.time())
                except ValueError:
                    pass

            if leave_time_str:
                try:
                    leave_time = datetime.strptime(leave_time_str, '%H:%M')
                    leave_time = datetime.combine(
                        live_class.start_time.date(), leave_time.time())
                except ValueError:
                    pass

            # Calculate duration if both times are provided
            if join_time and leave_time:
                duration = leave_time - join_time
                duration_minutes = int(duration.total_seconds() / 60)

            # Check if attendance record exists
            attendance = Attendance.query.filter_by(
                class_id=class_id, student_id=student.id).first()

            if attendance:
                # Update existing record
                attendance.status = status
                attendance.join_time = join_time
                attendance.leave_time = leave_time
                attendance.duration_minutes = duration_minutes
            else:
                # Create new record
                attendance = Attendance(
                    class_id=class_id,
                    student_id=student.id,
                    status=status,
                    join_time=join_time,
                    leave_time=leave_time,
                    duration_minutes=duration_minutes
                )
                db.session.add(attendance)

        db.session.commit()
        flash('Attendance recorded successfully!', 'success')
        return redirect(url_for('instructor.class_attendance', class_id=class_id))

    # Get existing attendance records
    attendances = {a.student_id: a for a in Attendance.query.filter_by(
        class_id=class_id).all()}

    return render_template('instructor/class_attendance.html',
                           live_class=live_class,
                           batch=batch,
                           students=batch_students,
                           attendances=attendances)


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
            assignment_id=new_assignment.id,
            due_date=due_date
        )

        db.session.add(grade_item)
        db.session.commit()

        flash('Assignment created successfully!', 'success')
        return redirect(url_for('instructor.assignments'))

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

        flash('Assignment updated successfully!', 'success')
        return redirect(url_for('instructor.assignments'))

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

        submission.points = points
        submission.feedback = feedback
        submission.graded_by_id = current_user.id
        submission.graded_at = datetime.now()

        db.session.commit()

        # Update corresponding grade item
        grade_item = GradeItem.query.filter_by(
            assignment_id=assignment.id).first()
        if grade_item:
            # Check if student grade exists
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
        flash('You do not have permission to edit this batch.', 'danger')
        return redirect(url_for('instructor.batches'))

    if request.method == 'POST':
        student_ids = request.form.getlist('student_ids')

        if not student_ids:
            flash('No students selected.', 'warning')
            return redirect(url_for('instructor.add_students_to_batch', batch_id=batch_id))

        # Check if batch has reached maximum capacity
        current_enrollments = BatchEnrollment.query.filter_by(
            batch_id=batch_id).count()
        remaining_slots = batch.max_students - current_enrollments

        if len(student_ids) > remaining_slots:
            flash(
                f'Batch can only accommodate {remaining_slots} more students.', 'danger')
            return redirect(url_for('instructor.add_students_to_batch', batch_id=batch_id))

        # Enroll students in batch
        for student_id in student_ids:
            # Check if student is already enrolled in the batch
            existing_enrollment = BatchEnrollment.query.filter_by(
                batch_id=batch_id,
                student_id=student_id
            ).first()

            if not existing_enrollment:
                # Enroll student in batch
                enrollment = BatchEnrollment(
                    batch_id=batch_id,
                    student_id=student_id,
                    enrollment_date=datetime.utcnow()
                )

                # Also enroll in course if not already enrolled
                course_enrollment = Enrollment.query.filter_by(
                    student_id=student_id,
                    course_id=batch.course_id
                ).first()

                if not course_enrollment:
                    course_enrollment = Enrollment(
                        student_id=student_id,
                        course_id=batch.course_id,
                        enrollment_date=datetime.utcnow()
                    )
                    db.session.add(course_enrollment)

                db.session.add(enrollment)

        db.session.commit()

        flash('Students added to batch successfully!', 'success')
        return redirect(url_for('instructor.batch_students', batch_id=batch_id))

    # Get all students who are not enrolled in this batch
    enrolled_student_ids = db.session.query(
        BatchEnrollment.student_id).filter_by(batch_id=batch_id).all()
    enrolled_student_ids = [id[0] for id in enrolled_student_ids]

    available_students = User.query.filter(
        User.role == UserRole.STUDENT,
        User.is_active == True,
        ~User.id.in_(enrolled_student_ids) if enrolled_student_ids else True
    ).all()

    return render_template('instructor/add_students_to_batch.html',
                           batch=batch,
                           available_students=available_students)


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
