from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.user import User, UserRole, Course, Enrollment, Batch, BatchEnrollment, LiveClass, Attendance, Quiz, QuizAttempt, Question, QuestionOption, QuizResponse, Assignment, AssignmentSubmission, GradeItem, StudentGrade, Certificate, DiscussionForum, Message
from functools import wraps
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import os

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

    # Get upcoming classes (next 7 days)
    now = datetime.now()
    next_week = now + timedelta(days=7)

    # Get batches the student is enrolled in
    batch_enrollments = BatchEnrollment.query.filter_by(
        student_id=current_user.id).all()
    batch_ids = [be.batch_id for be in batch_enrollments]

    # Get upcoming classes for these batches
    upcoming_classes = LiveClass.query.filter(
        LiveClass.batch_id.in_(batch_ids),
        LiveClass.start_time >= now,
        LiveClass.start_time <= next_week
    ).order_by(LiveClass.start_time).limit(5).all()

    return render_template('student/dashboard.html',
                           courses=courses,
                           upcoming_classes=upcoming_classes)


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

    # Get batches for this course that the student is enrolled in
    batches = []
    if is_enrolled:
        batch_enrollments = BatchEnrollment.query.join(Batch).filter(
            BatchEnrollment.student_id == current_user.id,
            Batch.course_id == course_id
        ).all()

        for be in batch_enrollments:
            batch = Batch.query.get(be.batch_id)
            if batch:
                batches.append(batch)

        # Get upcoming classes for these batches
        now = datetime.now()
        upcoming_classes = []
        for batch in batches:
            classes = LiveClass.query.filter(
                LiveClass.batch_id == batch.id,
                LiveClass.start_time >= now
            ).order_by(LiveClass.start_time).limit(3).all()

            upcoming_classes.extend(classes)
    else:
        upcoming_classes = []

    return render_template('student/course_details.html',
                           course=course,
                           instructor=instructor,
                           is_enrolled=is_enrolled,
                           batches=batches,
                           upcoming_classes=upcoming_classes)


@student.route('/enroll/<int:course_id>', methods=['POST'])
@login_required
@student_required
def enroll_course(course_id):
    # Check if course exists
    course = Course.query.get_or_404(course_id)

    # Check if student is already enrolled
    existing_enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=course_id
    ).first()

    if existing_enrollment:
        flash('You are already enrolled in this course.', 'info')
    else:
        # Create new enrollment
        enrollment = Enrollment(
            student_id=current_user.id,
            course_id=course_id,
            enrollment_date=datetime.now()
        )
        db.session.add(enrollment)
        db.session.commit()
        flash('Successfully enrolled in the course!', 'success')

    return redirect(url_for('student.course_details', course_id=course_id))


@student.route('/calendar')
@login_required
@student_required
def calendar():
    # Get batches the student is enrolled in
    batch_enrollments = BatchEnrollment.query.filter_by(
        student_id=current_user.id).all()
    batch_ids = [be.batch_id for be in batch_enrollments]

    # Get all classes for these batches
    classes = LiveClass.query.filter(LiveClass.batch_id.in_(batch_ids)).all()

    # Format classes for calendar display
    calendar_events = []
    for cls in classes:
        batch = Batch.query.get(cls.batch_id)
        course = Course.query.get(batch.course_id) if batch else None

        if course:
            calendar_events.append({
                'id': cls.id,
                'title': cls.title,
                'start': cls.start_time.strftime('%Y-%m-%dT%H:%M:%S'),
                'end': cls.end_time.strftime('%Y-%m-%dT%H:%M:%S'),
                'course': course.title,
                'batch': batch.name,
                'instructor': f"{cls.instructor.first_name} {cls.instructor.last_name}",
                'platform': cls.platform,
                'url': url_for('student.class_details', class_id=cls.id)
            })

    return render_template('student/calendar.html', calendar_events=calendar_events)


@student.route('/classes')
@login_required
@student_required
def classes():
    # Get batches the student is enrolled in
    batch_enrollments = BatchEnrollment.query.filter_by(
        student_id=current_user.id).all()
    batch_ids = [be.batch_id for be in batch_enrollments]

    # Get all classes for these batches
    now = datetime.now()

    # Upcoming classes
    upcoming_classes = LiveClass.query.filter(
        LiveClass.batch_id.in_(batch_ids),
        LiveClass.start_time >= now
    ).order_by(LiveClass.start_time).all()

    # Past classes
    past_classes = LiveClass.query.filter(
        LiveClass.batch_id.in_(batch_ids),
        LiveClass.start_time < now
    ).order_by(LiveClass.start_time.desc()).all()

    # Get attendance records for past classes
    attendance_records = {}
    for cls in past_classes:
        attendance = Attendance.query.filter_by(
            class_id=cls.id,
            student_id=current_user.id
        ).first()

        if attendance:
            attendance_records[cls.id] = attendance

    return render_template('student/classes.html',
                           upcoming_classes=upcoming_classes,
                           past_classes=past_classes,
                           attendance_records=attendance_records)


@student.route('/class/<int:class_id>')
@login_required
@student_required
def class_details(class_id):
    live_class = LiveClass.query.get_or_404(class_id)

    # Check if student is enrolled in the batch
    batch_enrollment = BatchEnrollment.query.filter_by(
        batch_id=live_class.batch_id,
        student_id=current_user.id
    ).first()

    if not batch_enrollment:
        flash('You are not enrolled in this class.', 'danger')
        return redirect(url_for('student.classes'))

    batch = Batch.query.get(live_class.batch_id)
    course = Course.query.get(batch.course_id) if batch else None
    instructor = User.query.get(live_class.instructor_id)

    # Get attendance if this is a past class
    now = datetime.now()
    is_past = live_class.start_time < now

    attendance = None
    if is_past:
        attendance = Attendance.query.filter_by(
            class_id=class_id,
            student_id=current_user.id
        ).first()

    return render_template('student/class_details.html',
                           live_class=live_class,
                           batch=batch,
                           course=course,
                           instructor=instructor,
                           is_past=is_past,
                           attendance=attendance)


# Quiz Routes
@student.route('/quizzes')
@login_required
@student_required
def quizzes():
    # Get courses the student is enrolled in
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    course_ids = [enrollment.course_id for enrollment in enrollments]

    # Get published quizzes for these courses
    quizzes = Quiz.query.filter(
        Quiz.course_id.in_(course_ids),
        Quiz.is_published == True
    ).order_by(Quiz.created_at.desc()).all()

    # Get attempt information for each quiz
    quiz_data = []
    for quiz in quizzes:
        attempts = QuizAttempt.query.filter_by(
            quiz_id=quiz.id,
            student_id=current_user.id
        ).order_by(QuizAttempt.start_time.desc()).all()

        # Check if student can take this quiz
        can_take = True
        if quiz.attempts_allowed > 0 and len(attempts) >= quiz.attempts_allowed:
            can_take = False

        quiz_data.append({
            'quiz': quiz,
            'course': Course.query.get(quiz.course_id),
            'attempts': attempts,
            'can_take': can_take
        })

    return render_template('student/quizzes.html', quiz_data=quiz_data)


@student.route('/quiz/<int:quiz_id>')
@login_required
@student_required
def quiz_details(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)

    # Check if student is enrolled in the course
    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=quiz.course_id
    ).first()

    if not enrollment:
        flash('You are not enrolled in this course.', 'danger')
        return redirect(url_for('student.quizzes'))

    # Check if quiz is published
    if not quiz.is_published:
        flash('This quiz is not available yet.', 'danger')
        return redirect(url_for('student.quizzes'))

    # Get attempts for this quiz
    attempts = QuizAttempt.query.filter_by(
        quiz_id=quiz.id,
        student_id=current_user.id
    ).order_by(QuizAttempt.start_time.desc()).all()

    # Check if student can take this quiz
    can_take = True
    if quiz.attempts_allowed > 0 and len(attempts) >= quiz.attempts_allowed:
        can_take = False

    course = Course.query.get(quiz.course_id)

    return render_template('student/quiz_details.html',
                           quiz=quiz,
                           course=course,
                           attempts=attempts,
                           can_take=can_take)


@student.route('/quiz/<int:quiz_id>/take', methods=['GET', 'POST'])
@login_required
@student_required
def take_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)

    # Check if student is enrolled in the course
    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=quiz.course_id
    ).first()

    if not enrollment:
        flash('You are not enrolled in this course.', 'danger')
        return redirect(url_for('student.quizzes'))

    # Check if quiz is published
    if not quiz.is_published:
        flash('This quiz is not available yet.', 'danger')
        return redirect(url_for('student.quizzes'))

    # Check if student has reached attempt limit
    attempts = QuizAttempt.query.filter_by(
        quiz_id=quiz.id,
        student_id=current_user.id
    ).all()

    if quiz.attempts_allowed > 0 and len(attempts) >= quiz.attempts_allowed:
        flash('You have reached the maximum number of attempts for this quiz.', 'danger')
        return redirect(url_for('student.quiz_details', quiz_id=quiz_id))

    # Check if there's an ongoing attempt
    ongoing_attempt = QuizAttempt.query.filter_by(
        quiz_id=quiz.id,
        student_id=current_user.id,
        is_completed=False
    ).first()

    if ongoing_attempt:
        # Continue existing attempt
        attempt = ongoing_attempt
    else:
        # Create new attempt
        attempt = QuizAttempt(
            quiz_id=quiz.id,
            student_id=current_user.id,
            start_time=datetime.now()
        )
        db.session.add(attempt)
        db.session.commit()

    if request.method == 'POST':
        # Process quiz submission
        questions = Question.query.filter_by(quiz_id=quiz_id).all()
        total_points = 0
        max_points = 0

        for question in questions:
            max_points += question.points

            # Check if response exists
            response = QuizResponse.query.filter_by(
                attempt_id=attempt.id,
                question_id=question.id
            ).first()

            if not response:
                response = QuizResponse(
                    attempt_id=attempt.id,
                    question_id=question.id
                )
                db.session.add(response)

            # Process response based on question type
            if question.question_type == 'mcq' or question.question_type == 'true_false':
                selected_option_id = request.form.get(
                    f'question_{question.id}')

                if selected_option_id:
                    selected_option = QuestionOption.query.get(
                        selected_option_id)
                    response.selected_option_id = selected_option_id

                    # Auto-grade MCQ and true/false questions
                    response.is_correct = selected_option.is_correct
                    response.points_earned = question.points if selected_option.is_correct else 0

                    # Apply negative marking if applicable
                    if not selected_option.is_correct and question.negative_points > 0:
                        response.points_earned = -question.negative_points
                else:
                    response.is_correct = False
                    response.points_earned = 0

            elif question.question_type == 'fill_blank' or question.question_type == 'short_answer':
                text_response = request.form.get(f'question_{question.id}')
                response.text_response = text_response

                # Auto-grade fill in the blank questions
                if question.question_type == 'fill_blank':
                    correct_answer = QuestionAnswer.query.filter_by(
                        question_id=question.id).first()
                    if correct_answer and text_response and text_response.lower().strip() == correct_answer.answer_text.lower().strip():
                        response.is_correct = True
                        response.points_earned = question.points
                    else:
                        response.is_correct = False
                        response.points_earned = 0
                else:
                    # Short answer questions need manual grading
                    response.is_correct = None
                    response.points_earned = 0

            total_points += response.points_earned

        # Update attempt
        attempt.end_time = datetime.now()
        attempt.score = total_points
        attempt.max_score = max_points
        attempt.percentage = (total_points / max_points *
                              100) if max_points > 0 else 0
        attempt.is_passed = attempt.percentage >= quiz.passing_score
        attempt.is_completed = True

        db.session.commit()

        flash('Quiz submitted successfully!', 'success')
        return redirect(url_for('student.quiz_result', attempt_id=attempt.id))

    # Get questions for the quiz
    questions = Question.query.filter_by(
        quiz_id=quiz_id).order_by(Question.order).all()

    # Shuffle questions if enabled
    if quiz.shuffle_questions:
        import random
        random.shuffle(questions)

    # Get existing responses
    responses = {}
    for response in QuizResponse.query.filter_by(attempt_id=attempt.id).all():
        responses[response.question_id] = response

    return render_template('student/take_quiz.html',
                           quiz=quiz,
                           questions=questions,
                           attempt=attempt,
                           responses=responses)


@student.route('/quiz-result/<int:attempt_id>')
@login_required
@student_required
def quiz_result(attempt_id):
    attempt = QuizAttempt.query.get_or_404(attempt_id)

    # Check if this attempt belongs to the current student
    if attempt.student_id != current_user.id:
        flash('You do not have permission to view this result.', 'danger')
        return redirect(url_for('student.quizzes'))

    quiz = Quiz.query.get(attempt.quiz_id)

    # Get responses with questions
    responses = QuizResponse.query.filter_by(attempt_id=attempt_id).all()

    response_data = {}
    for response in responses:
        question = Question.query.get(response.question_id)
        if question:
            response_data[question.id] = {
                'question': question,
                'response': response,
                'options': question.options if question.question_type in ['mcq', 'true_false'] else [],
                'answer': QuestionAnswer.query.filter_by(question_id=question.id).first() if quiz.show_correct_answers else None
            }

    return render_template('student/quiz_result.html',
                           attempt=attempt,
                           quiz=quiz,
                           response_data=response_data)


# Assignment Routes
@student.route('/assignments')
@login_required
@student_required
def assignments():
    # Get courses the student is enrolled in
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    course_ids = [enrollment.course_id for enrollment in enrollments]

    # Get assignments for these courses
    assignments = Assignment.query.filter(
        Assignment.course_id.in_(course_ids)
    ).order_by(Assignment.due_date.asc()).all()

    # Get submission information for each assignment
    assignment_data = []
    now = datetime.now()

    for assignment in assignments:
        submission = AssignmentSubmission.query.filter_by(
            assignment_id=assignment.id,
            student_id=current_user.id
        ).first()

        # Check status
        status = "Not Submitted"
        if submission:
            if submission.graded_at:
                status = "Graded"
            else:
                status = "Submitted"
        elif assignment.due_date and assignment.due_date < now:
            status = "Overdue"

        assignment_data.append({
            'assignment': assignment,
            'course': Course.query.get(assignment.course_id),
            'submission': submission,
            'status': status
        })

    return render_template('student/assignments.html', assignment_data=assignment_data)


@student.route('/assignment/<int:assignment_id>')
@login_required
@student_required
def assignment_details(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)

    # Check if student is enrolled in the course
    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=assignment.course_id
    ).first()

    if not enrollment:
        flash('You are not enrolled in this course.', 'danger')
        return redirect(url_for('student.assignments'))

    # Get submission if it exists
    submission = AssignmentSubmission.query.filter_by(
        assignment_id=assignment.id,
        student_id=current_user.id
    ).first()

    course = Course.query.get(assignment.course_id)

    # Check if assignment is past due
    now = datetime.now()
    is_past_due = assignment.due_date and assignment.due_date < now

    return render_template('student/assignment_details.html',
                           assignment=assignment,
                           course=course,
                           submission=submission,
                           is_past_due=is_past_due)


@student.route('/assignment/<int:assignment_id>/submit', methods=['GET', 'POST'])
@login_required
@student_required
def submit_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)

    # Check if student is enrolled in the course
    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=assignment.course_id
    ).first()

    if not enrollment:
        flash('You are not enrolled in this course.', 'danger')
        return redirect(url_for('student.assignments'))

    # Check if student has already submitted
    existing_submission = AssignmentSubmission.query.filter_by(
        assignment_id=assignment.id,
        student_id=current_user.id
    ).first()

    if existing_submission:
        flash('You have already submitted this assignment. Please use the edit option instead.', 'info')
        return redirect(url_for('student.assignment_details', assignment_id=assignment_id))

    if request.method == 'POST':
        submission_text = request.form.get('submission_text')

        # Check if file was uploaded
        submission_file = None
        if 'submission_file' in request.files:
            file = request.files['submission_file']
            if file and file.filename:
                # Check file extension
                allowed_extensions = assignment.allowed_file_extensions.split(
                    ',')
                file_ext = file.filename.rsplit(
                    '.', 1)[1].lower() if '.' in file.filename else ''

                if file_ext not in allowed_extensions:
                    flash(
                        f'File type not allowed. Allowed types: {assignment.allowed_file_extensions}', 'danger')
                    return redirect(url_for('student.submit_assignment', assignment_id=assignment_id))

                # Check file size
                if len(file.read()) > assignment.max_file_size_mb * 1024 * 1024:
                    flash(
                        f'File is too large. Maximum size: {assignment.max_file_size_mb}MB', 'danger')
                    return redirect(url_for('student.submit_assignment', assignment_id=assignment_id))

                # Reset file pointer and save
                file.seek(0)
                filename = secure_filename(
                    f"{current_user.id}_{assignment_id}_{file.filename}")
                file_path = os.path.join(
                    current_app.config['UPLOAD_FOLDER'], 'assignments', filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                file.save(file_path)
                submission_file = os.path.join('assignments', filename)

        # Check if past due date
        now = datetime.now()
        is_late = assignment.due_date and assignment.due_date < now

        # Create submission
        submission = AssignmentSubmission(
            assignment_id=assignment.id,
            student_id=current_user.id,
            submission_text=submission_text,
            submission_file=submission_file,
            submitted_at=now,
            is_late=is_late
        )

        db.session.add(submission)
        db.session.commit()

        flash('Assignment submitted successfully!', 'success')
        return redirect(url_for('student.assignment_details', assignment_id=assignment_id))

    return render_template('student/submit_assignment.html',
                           assignment=assignment,
                           course=Course.query.get(assignment.course_id))


@student.route('/assignment/<int:assignment_id>/edit', methods=['GET', 'POST'])
@login_required
@student_required
def edit_assignment_submission(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)

    # Check if student is enrolled in the course
    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=assignment.course_id
    ).first()

    if not enrollment:
        flash('You are not enrolled in this course.', 'danger')
        return redirect(url_for('student.assignments'))

    # Get existing submission
    submission = AssignmentSubmission.query.filter_by(
        assignment_id=assignment.id,
        student_id=current_user.id
    ).first()

    if not submission:
        flash('You have not submitted this assignment yet.', 'info')
        return redirect(url_for('student.submit_assignment', assignment_id=assignment_id))

    # Check if already graded
    if submission.graded_at:
        flash('This submission has already been graded and cannot be edited.', 'warning')
        return redirect(url_for('student.assignment_details', assignment_id=assignment_id))

    if request.method == 'POST':
        submission.submission_text = request.form.get('submission_text')

        # Check if file was uploaded
        if 'submission_file' in request.files:
            file = request.files['submission_file']
            if file and file.filename:
                # Check file extension
                allowed_extensions = assignment.allowed_file_extensions.split(
                    ',')
                file_ext = file.filename.rsplit(
                    '.', 1)[1].lower() if '.' in file.filename else ''

                if file_ext not in allowed_extensions:
                    flash(
                        f'File type not allowed. Allowed types: {assignment.allowed_file_extensions}', 'danger')
                    return redirect(url_for('student.edit_assignment_submission', assignment_id=assignment_id))

                # Check file size
                if len(file.read()) > assignment.max_file_size_mb * 1024 * 1024:
                    flash(
                        f'File is too large. Maximum size: {assignment.max_file_size_mb}MB', 'danger')
                    return redirect(url_for('student.edit_assignment_submission', assignment_id=assignment_id))

                # Reset file pointer and save
                file.seek(0)
                filename = secure_filename(
                    f"{current_user.id}_{assignment_id}_{file.filename}")
                file_path = os.path.join(
                    current_app.config['UPLOAD_FOLDER'], 'assignments', filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                file.save(file_path)

                # Delete old file if it exists
                if submission.submission_file:
                    old_path = os.path.join(
                        current_app.config['UPLOAD_FOLDER'], submission.submission_file)
                    if os.path.exists(old_path):
                        os.remove(old_path)

                submission.submission_file = os.path.join(
                    'assignments', filename)

        # Update submission time
        submission.submitted_at = datetime.now()

        # Check if past due date
        now = datetime.now()
        submission.is_late = assignment.due_date and assignment.due_date < now

        db.session.commit()

        flash('Assignment submission updated successfully!', 'success')
        return redirect(url_for('student.assignment_details', assignment_id=assignment_id))

    return render_template('student/edit_submission.html',
                           assignment=assignment,
                           submission=submission,
                           course=Course.query.get(assignment.course_id))


# Grade Book
@student.route('/grades')
@login_required
@student_required
def grades():
    # Get courses the student is enrolled in
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()

    # Get grades for each course
    course_grades = []

    for enrollment in enrollments:
        course = Course.query.get(enrollment.course_id)
        if course:
            # Get grade items for this course
            grade_items = GradeItem.query.filter_by(course_id=course.id).all()

            # Get student grades for these items
            grades = []
            total_points = 0
            total_possible = 0
            weighted_score = 0
            total_weight = 0

            for item in grade_items:
                student_grade = StudentGrade.query.filter_by(
                    grade_item_id=item.id,
                    student_id=current_user.id
                ).first()

                if student_grade:
                    grade_percentage = (
                        student_grade.points / item.max_points * 100) if item.max_points > 0 else 0
                    grades.append({
                        'item': item,
                        'grade': student_grade,
                        'percentage': grade_percentage
                    })

                    total_points += student_grade.points
                    total_possible += item.max_points
                    weighted_score += grade_percentage * item.weight
                    total_weight += item.weight
                else:
                    grades.append({
                        'item': item,
                        'grade': None,
                        'percentage': 0
                    })

            # Calculate overall grade
            overall_percentage = 0
            if total_possible > 0:
                overall_percentage = total_points / total_possible * 100

            weighted_percentage = 0
            if total_weight > 0:
                weighted_percentage = weighted_score / total_weight

            course_grades.append({
                'course': course,
                'grades': grades,
                'overall_percentage': overall_percentage,
                'weighted_percentage': weighted_percentage
            })

    return render_template('student/grades.html', course_grades=course_grades)


# Certificate Routes
@student.route('/certificates')
@login_required
@student_required
def certificates():
    # Get student's certificates
    certificates = Certificate.query.filter_by(
        student_id=current_user.id).all()

    certificate_data = []
    for cert in certificates:
        course = Course.query.get(cert.course_id)
        if course:
            certificate_data.append({
                'certificate': cert,
                'course': course
            })

    return render_template('student/certificates.html', certificate_data=certificate_data)


@student.route('/certificate/<int:certificate_id>')
@login_required
@student_required
def view_certificate(certificate_id):
    certificate = Certificate.query.get_or_404(certificate_id)

    # Check if this certificate belongs to the current student
    if certificate.student_id != current_user.id:
        flash('You do not have permission to view this certificate.', 'danger')
        return redirect(url_for('student.certificates'))

    course = Course.query.get(certificate.course_id)

    return render_template('student/view_certificate.html',
                           certificate=certificate,
                           course=course)


# Communication Routes
@student.route('/messages')
@login_required
@student_required
def messages():
    # Get received messages
    received_messages = Message.query.filter_by(
        recipient_id=current_user.id
    ).order_by(Message.sent_at.desc()).all()

    # Get sent messages
    sent_messages = Message.query.filter_by(
        sender_id=current_user.id
    ).order_by(Message.sent_at.desc()).all()

    return render_template('student/messages.html',
                           received_messages=received_messages,
                           sent_messages=sent_messages)


@student.route('/send-message', methods=['GET', 'POST'])
@login_required
@student_required
def send_message():
    if request.method == 'POST':
        recipient_id = request.form.get('recipient_id')
        subject = request.form.get('subject')
        content = request.form.get('content')

        # Validate recipient
        recipient = User.query.get(recipient_id)
        if not recipient:
            flash('Invalid recipient.', 'danger')
            return redirect(url_for('student.send_message'))

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
        return redirect(url_for('student.messages'))

    # Get potential recipients (instructors of enrolled courses)
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    course_ids = [enrollment.course_id for enrollment in enrollments]
    courses = Course.query.filter(Course.id.in_(course_ids)).all()

    instructors = []
    for course in courses:
        instructor = User.query.get(course.instructor_id)
        if instructor and instructor not in instructors:
            instructors.append(instructor)

    return render_template('student/send_message.html', instructors=instructors)


@student.route('/message/<int:message_id>')
@login_required
@student_required
def view_message(message_id):
    message = Message.query.get_or_404(message_id)

    # Check if message belongs to current user
    if message.recipient_id != current_user.id and message.sender_id != current_user.id:
        flash('You do not have permission to view this message.', 'danger')
        return redirect(url_for('student.messages'))

    # Mark as read if current user is recipient
    if message.recipient_id == current_user.id and not message.is_read:
        message.is_read = True
        message.read_at = datetime.now()
        db.session.commit()

    sender = User.query.get(message.sender_id)
    recipient = User.query.get(message.recipient_id)

    return render_template('student/view_message.html',
                           message=message,
                           sender=sender,
                           recipient=recipient)


@student.route('/forums')
@login_required
@student_required
def forums():
    # Get forums for courses the student is enrolled in
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    course_ids = [enrollment.course_id for enrollment in enrollments]

    course_forums = DiscussionForum.query.filter(
        DiscussionForum.course_id.in_(course_ids)).all()
    general_forums = DiscussionForum.query.filter(
        DiscussionForum.course_id == None).all()

    return render_template('student/forums.html',
                           course_forums=course_forums,
                           general_forums=general_forums)
