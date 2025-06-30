from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.user import (User, UserRole, Course, Enrollment, CourseCategory,
                             CourseTag, Module, Lesson, Topic)
from werkzeug.utils import secure_filename
from functools import wraps
import os
import json
from datetime import datetime, timedelta

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
                if file.filename:
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(
                        current_app.config['UPLOAD_FOLDER'], content_type, filename)
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    file.save(file_path)
                    new_topic.file_path = os.path.join(content_type, filename)

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
                if file.filename:
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(
                        current_app.config['UPLOAD_FOLDER'], topic.content_type, filename)
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    file.save(file_path)
                    topic.file_path = os.path.join(
                        topic.content_type, filename)

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
