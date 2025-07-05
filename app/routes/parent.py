from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.user import User, UserRole, Course, Enrollment, ParentStudent
from app.models.user import Assignment, AssignmentSubmission, GradeItem, StudentGrade, Message
from functools import wraps
from datetime import datetime

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


@parent.route('/child/<int:student_id>/assignments')
@login_required
@parent_required
def child_assignments(student_id):
    # Verify this is the parent's child
    parent_student = ParentStudent.query.filter_by(
        parent_id=current_user.id,
        student_id=student_id
    ).first()

    if not parent_student:
        flash('You do not have permission to view this student.', 'danger')
        return redirect(url_for('parent.dashboard'))

    student = User.query.get_or_404(student_id)

    # Get courses the student is enrolled in
    enrollments = Enrollment.query.filter_by(student_id=student_id).all()
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
            student_id=student_id
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

    return render_template('parent/child_assignments.html',
                           student=student,
                           assignment_data=assignment_data)


@parent.route('/child/<int:student_id>/assignment/<int:assignment_id>')
@login_required
@parent_required
def child_assignment_details(student_id, assignment_id):
    # Verify this is the parent's child
    parent_student = ParentStudent.query.filter_by(
        parent_id=current_user.id,
        student_id=student_id
    ).first()

    if not parent_student:
        flash('You do not have permission to view this student.', 'danger')
        return redirect(url_for('parent.dashboard'))

    student = User.query.get_or_404(student_id)
    assignment = Assignment.query.get_or_404(assignment_id)

    # Check if student is enrolled in the course
    enrollment = Enrollment.query.filter_by(
        student_id=student_id,
        course_id=assignment.course_id
    ).first()

    if not enrollment:
        flash('Student is not enrolled in this course.', 'danger')
        return redirect(url_for('parent.child_assignments', student_id=student_id))

    # Get submission if it exists
    submission = AssignmentSubmission.query.filter_by(
        assignment_id=assignment.id,
        student_id=student_id
    ).first()

    course = Course.query.get(assignment.course_id)

    # Check if assignment is past due
    now = datetime.now()
    is_past_due = assignment.due_date and assignment.due_date < now

    return render_template('parent/child_assignment_details.html',
                           student=student,
                           assignment=assignment,
                           course=course,
                           submission=submission,
                           is_past_due=is_past_due)


@parent.route('/child/<int:student_id>/grades')
@login_required
@parent_required
def child_grades(student_id):
    # Verify this is the parent's child
    parent_student = ParentStudent.query.filter_by(
        parent_id=current_user.id,
        student_id=student_id
    ).first()

    if not parent_student:
        flash('You do not have permission to view this student.', 'danger')
        return redirect(url_for('parent.dashboard'))

    student = User.query.get_or_404(student_id)

    # Get courses the student is enrolled in
    enrollments = Enrollment.query.filter_by(student_id=student_id).all()

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
                    student_id=student_id
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

    return render_template('parent/child_grades.html',
                           student=student,
                           course_grades=course_grades)


@parent.route('/child/<int:student_id>/messages')
@login_required
@parent_required
def child_messages(student_id):
    # Verify this is the parent's child
    parent_student = ParentStudent.query.filter_by(
        parent_id=current_user.id,
        student_id=student_id
    ).first()

    if not parent_student:
        flash('You do not have permission to view this student.', 'danger')
        return redirect(url_for('parent.dashboard'))

    student = User.query.get_or_404(student_id)

    # Get received messages
    received_messages = Message.query.filter_by(
        recipient_id=student_id
    ).order_by(Message.sent_at.desc()).all()

    # Get sent messages
    sent_messages = Message.query.filter_by(
        sender_id=student_id
    ).order_by(Message.sent_at.desc()).all()

    return render_template('parent/child_messages.html',
                           student=student,
                           received_messages=received_messages,
                           sent_messages=sent_messages)


@parent.route('/messages')
@login_required
@parent_required
def messages():
    # Get received messages
    received_messages = Message.query.filter_by(
        recipient_id=current_user.id
    ).order_by(Message.sent_at.desc()).all()

    # Get sent messages
    sent_messages = Message.query.filter_by(
        sender_id=current_user.id
    ).order_by(Message.sent_at.desc()).all()

    return render_template('parent/messages.html',
                           received_messages=received_messages,
                           sent_messages=sent_messages)


@parent.route('/send-message', methods=['GET', 'POST'])
@login_required
@parent_required
def send_message():
    if request.method == 'POST':
        recipient_id = request.form.get('recipient_id')
        subject = request.form.get('subject')
        content = request.form.get('content')

        # Validate recipient
        recipient = User.query.get(recipient_id)
        if not recipient:
            flash('Invalid recipient.', 'danger')
            return redirect(url_for('parent.send_message'))

        # Create message
        message = Message(
            sender_id=current_user.id,
            recipient_id=recipient_id,
            subject=subject,
            content=content,
            is_read=False,
            created_at=datetime.now()
        )

        db.session.add(message)
        db.session.commit()

        flash('Message sent successfully!', 'success')
        return redirect(url_for('parent.messages'))

    # Get potential recipients (instructors of children's courses)
    parent_students = ParentStudent.query.filter_by(
        parent_id=current_user.id).all()
    student_ids = [ps.student_id for ps in parent_students]

    enrollments = Enrollment.query.filter(
        Enrollment.student_id.in_(student_ids)).all()
    course_ids = [enrollment.course_id for enrollment in enrollments]
    courses = Course.query.filter(Course.id.in_(course_ids)).all()

    instructors = []
    for course in courses:
        instructor = User.query.get(course.instructor_id)
        if instructor and instructor not in instructors:
            instructors.append(instructor)

    return render_template('parent/send_message.html',
                           instructors=instructors,
                           students=[User.query.get(student_id) for student_id in student_ids])


@parent.route('/message/<int:message_id>')
@login_required
@parent_required
def view_message(message_id):
    message = Message.query.get_or_404(message_id)

    # Check if message belongs to current user
    if message.recipient_id != current_user.id and message.sender_id != current_user.id:
        flash('You do not have permission to view this message.', 'danger')
        return redirect(url_for('parent.messages'))

    # Mark as read if current user is recipient
    if message.recipient_id == current_user.id and not message.is_read:
        message.is_read = True
        message.read_at = datetime.now()
        db.session.commit()

    sender = User.query.get(message.sender_id)
    recipient = User.query.get(message.recipient_id)

    return render_template('parent/view_message.html',
                           message=message,
                           sender=sender,
                           recipient=recipient)


@parent.route('/reply-message/<int:message_id>', methods=['GET', 'POST'])
@login_required
@parent_required
def reply_message(message_id):
    original_message = Message.query.get_or_404(message_id)

    # Check if message belongs to current user
    if original_message.recipient_id != current_user.id and original_message.sender_id != current_user.id:
        flash('You do not have permission to reply to this message.', 'danger')
        return redirect(url_for('parent.messages'))

    # Determine the recipient (the other party in the conversation)
    if original_message.sender_id == current_user.id:
        recipient_id = original_message.recipient_id
    else:
        recipient_id = original_message.sender_id

    other_user = User.query.get(recipient_id)

    if request.method == 'POST':
        subject = request.form.get('subject')
        content = request.form.get('content')

        # Create reply message
        reply = Message(
            sender_id=current_user.id,
            recipient_id=recipient_id,
            subject=subject,
            content=content,
            is_read=False,
            created_at=datetime.now()
        )

        db.session.add(reply)
        db.session.commit()

        flash('Reply sent successfully!', 'success')
        return redirect(url_for('parent.messages'))

    # Prepare reply subject with "Re: " prefix if not already there
    reply_subject = original_message.subject
    if not reply_subject.startswith('Re: '):
        reply_subject = f"Re: {reply_subject}"

    return render_template('parent/reply_message.html',
                           message=original_message,
                           reply_subject=reply_subject,
                           recipient=other_user)
