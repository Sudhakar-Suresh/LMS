from flask_login import UserMixin
from datetime import datetime
from app import db, login_manager


class UserRole:
    ADMIN = 'admin'
    INSTRUCTOR = 'instructor'
    STUDENT = 'student'
    GUEST = 'guest'
    PARENT = 'parent'


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    is_email_verified = db.Column(db.Boolean, default=False)

    # Profile relationship
    profile = db.relationship(
        'UserProfile', backref='user', uselist=False, cascade='all, delete-orphan')

    # Relationship with courses (for instructors)
    courses_teaching = db.relationship(
        'Course', backref='instructor', lazy=True)

    # Relationship with enrollments (for students)
    enrollments = db.relationship('Enrollment', backref='student', lazy=True)

    # Relationship for parents - specify foreign keys to avoid ambiguity
    parent_of = db.relationship('ParentStudent',
                                foreign_keys='ParentStudent.parent_id',
                                backref='parent', lazy=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.role}')"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"


class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Personal information
    date_of_birth = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)

    # Profile picture
    profile_picture = db.Column(db.String(255), nullable=True)

    # Bio/About
    bio = db.Column(db.Text, nullable=True)

    # Social media links
    website = db.Column(db.String(255), nullable=True)
    linkedin = db.Column(db.String(255), nullable=True)
    twitter = db.Column(db.String(255), nullable=True)
    github = db.Column(db.String(255), nullable=True)

    # Additional fields for students
    student_id = db.Column(db.String(50), nullable=True)
    graduation_year = db.Column(db.Integer, nullable=True)
    major = db.Column(db.String(100), nullable=True)

    # Additional fields for instructors
    # e.g., Professor, Dr., etc.
    title = db.Column(db.String(100), nullable=True)
    specialization = db.Column(db.String(255), nullable=True)
    experience_years = db.Column(db.Integer, nullable=True)

    def __repr__(self):
        return f"UserProfile(User ID: {self.user_id})"


# Permission model for RBAC
class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=True)

    # Many-to-many relationship with roles
    roles = db.relationship(
        'Role', secondary='role_permissions', back_populates='permissions')

    def __repr__(self):
        return f"Permission('{self.name}')"


# Role model for RBAC
class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=True)

    # Many-to-many relationship with permissions
    permissions = db.relationship(
        'Permission', secondary='role_permissions', back_populates='roles')

    def __repr__(self):
        return f"Role('{self.name}')"


# Association table for roles and permissions
role_permissions = db.Table('role_permissions',
                            db.Column('role_id', db.Integer, db.ForeignKey(
                                'role.id'), primary_key=True),
                            db.Column('permission_id', db.Integer, db.ForeignKey(
                                'permission.id'), primary_key=True)
                            )


# User login history for security tracking
class UserLoginHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    login_time = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    success = db.Column(db.Boolean, default=True)

    # Relationship with user
    user = db.relationship('User')

    def __repr__(self):
        return f"UserLoginHistory(User ID: {self.user_id}, Time: {self.login_time})"


# Import history for bulk user imports
class UserImportHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    imported_by_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    import_date = db.Column(db.DateTime, default=datetime.utcnow)
    total_records = db.Column(db.Integer, default=0)
    successful_imports = db.Column(db.Integer, default=0)
    failed_imports = db.Column(db.Integer, default=0)
    error_log = db.Column(db.Text, nullable=True)

    # Relationship with user
    imported_by = db.relationship('User')

    def __repr__(self):
        return f"UserImportHistory('{self.filename}', {self.import_date})"


# Course Category model
class CourseCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)

    # Relationship with courses
    courses = db.relationship('Course', backref='category', lazy=True)

    def __repr__(self):
        return f"CourseCategory('{self.name}')"


# Course Tag model
class CourseTag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=False, unique=True)

    # Many-to-many relationship with courses
    courses = db.relationship(
        'Course', secondary='course_tags', backref=db.backref('tags', lazy='dynamic'))

    def __repr__(self):
        return f"CourseTag('{self.name}')"


# Association table for course tags (many-to-many)
course_tags = db.Table('course_tags',
                       db.Column('course_id', db.Integer, db.ForeignKey(
                           'course.id'), primary_key=True),
                       db.Column('tag_id', db.Integer, db.ForeignKey(
                           'course_tag.id'), primary_key=True)
                       )


# Association table for course prerequisites (many-to-many)
course_prerequisites = db.Table('course_prerequisites',
                                db.Column('course_id', db.Integer, db.ForeignKey(
                                    'course.id'), primary_key=True),
                                db.Column('prerequisite_id', db.Integer,
                                          db.ForeignKey('course.id'), primary_key=True)
                                )


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    instructor_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    category_id = db.Column(db.Integer, db.ForeignKey(
        'course_category.id'), nullable=True)
    thumbnail = db.Column(db.String(255), nullable=True)
    is_published = db.Column(db.Boolean, default=False)
    is_featured = db.Column(db.Boolean, default=False)

    # Drip content settings
    enable_drip = db.Column(db.Boolean, default=False)
    drip_interval_days = db.Column(
        db.Integer, default=0)  # 0 means no interval

    # Relationships
    enrollments = db.relationship('Enrollment', backref='course', lazy=True)
    modules = db.relationship(
        'Module', backref='course', lazy=True, order_by='Module.order')

    # Prerequisites (self-referential many-to-many)
    prerequisites = db.relationship(
        'Course', secondary=course_prerequisites,
        primaryjoin=(course_prerequisites.c.course_id == id),
        secondaryjoin=(course_prerequisites.c.prerequisite_id == id),
        backref=db.backref('required_for', lazy='dynamic'),
        lazy='dynamic'
    )

    def __repr__(self):
        return f"Course('{self.title}')"

    def clone(self, new_title=None):
        """Create a copy of this course with all its modules, lessons and topics"""
        new_course = Course(
            title=new_title or f"Copy of {self.title}",
            description=self.description,
            instructor_id=self.instructor_id,
            category_id=self.category_id,
            thumbnail=self.thumbnail,
            is_published=False,  # Always start as unpublished
            is_featured=False,
            enable_drip=self.enable_drip,
            drip_interval_days=self.drip_interval_days
        )
        db.session.add(new_course)
        db.session.flush()  # Get ID without committing

        # Clone modules
        for module in self.modules:
            new_module = Module(
                title=module.title,
                description=module.description,
                course_id=new_course.id,
                order=module.order
            )
            db.session.add(new_module)
            db.session.flush()

            # Clone lessons
            for lesson in module.lessons:
                new_lesson = Lesson(
                    title=lesson.title,
                    module_id=new_module.id,
                    order=lesson.order,
                    release_days=lesson.release_days
                )
                db.session.add(new_lesson)
                db.session.flush()

                # Clone topics
                for topic in lesson.topics:
                    new_topic = Topic(
                        title=topic.title,
                        content=topic.content,
                        content_type=topic.content_type,
                        lesson_id=new_lesson.id,
                        order=topic.order
                    )
                    db.session.add(new_topic)

        # Add same tags
        for tag in self.tags:
            new_course.tags.append(tag)

        return new_course


class Module(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    course_id = db.Column(db.Integer, db.ForeignKey(
        'course.id'), nullable=False)
    order = db.Column(db.Integer, nullable=False, default=0)

    # Relationship with lessons
    lessons = db.relationship(
        'Lesson', backref='module', lazy=True, order_by='Lesson.order')

    def __repr__(self):
        return f"Module('{self.title}', Course ID: {self.course_id})"


class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey(
        'module.id'), nullable=False)
    order = db.Column(db.Integer, nullable=False, default=0)
    # Days after enrollment for drip release
    release_days = db.Column(db.Integer, default=0)

    # Relationship with topics
    topics = db.relationship('Topic', backref='lesson',
                             lazy=True, order_by='Topic.order')

    def __repr__(self):
        return f"Lesson('{self.title}', Module ID: {self.module_id})"


class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=True)
    # text, video, audio, pdf
    content_type = db.Column(db.String(20), nullable=False, default='text')
    file_path = db.Column(db.String(255), nullable=True)  # For uploaded files
    lesson_id = db.Column(db.Integer, db.ForeignKey(
        'lesson.id'), nullable=False)
    order = db.Column(db.Integer, nullable=False, default=0)

    # Relationship with subcontent
    subcontent = db.relationship('SubContent', backref='topic',
                                 lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"Topic('{self.title}', Type: {self.content_type})"


class SubContent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=True)
    # text, pdf
    content_type = db.Column(db.String(20), nullable=False, default='text')
    file_path = db.Column(db.String(255), nullable=True)  # For uploaded files
    topic_id = db.Column(db.Integer, db.ForeignKey(
        'topic.id'), nullable=False)
    order = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return f"SubContent('{self.title}', Type: {self.content_type})"


class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey(
        'course.id'), nullable=False)
    enrollment_date = db.Column(db.DateTime, default=datetime.utcnow)

    # Track progress
    last_accessed_topic_id = db.Column(
        db.Integer, db.ForeignKey('topic.id'), nullable=True)
    completion_percentage = db.Column(db.Float, default=0.0)

    def __repr__(self):
        return f"Enrollment(Student ID: {self.student_id}, Course ID: {self.course_id})"


class ParentStudent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    student_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Explicitly define the relationship to avoid ambiguity
    student = db.relationship('User', foreign_keys=[
                              student_id], backref='parent_links')

    def __repr__(self):
        return f"ParentStudent(Parent ID: {self.parent_id}, Student ID: {self.student_id})"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Class and Batch Management Models
class Batch(db.Model):
    __tablename__ = 'batches'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey(
        'course.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    max_students = db.Column(db.Integer, default=30)
    description = db.Column(db.Text)

    # Relationships
    course = db.relationship(
        'Course', backref=db.backref('batches', lazy=True))
    students = db.relationship('User', secondary='batch_enrollments')
    classes = db.relationship('LiveClass', backref='batch', lazy=True)

    def __repr__(self):
        return f'<Batch {self.name}>'


class BatchEnrollment(db.Model):
    __tablename__ = 'batch_enrollments'
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey(
        'batches.id'), nullable=False)
    student_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    enrollment_date = db.Column(db.DateTime, default=datetime.utcnow)

    # Unique constraint to prevent duplicate enrollments
    __table_args__ = (db.UniqueConstraint(
        'batch_id', 'student_id', name='uq_batch_enrollment'),)

    def __repr__(self):
        return f'<BatchEnrollment {self.batch_id}-{self.student_id}>'


class LiveClass(db.Model):
    __tablename__ = 'live_classes'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey(
        'batches.id'), nullable=False)
    instructor_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    meeting_link = db.Column(db.String(255))
    meeting_id = db.Column(db.String(100))
    meeting_password = db.Column(db.String(100))
    # 'zoom', 'google_meet', etc.
    platform = db.Column(db.String(20), default='zoom')
    description = db.Column(db.Text)
    is_recurring = db.Column(db.Boolean, default=False)
    # 'daily', 'weekly', 'monthly'
    recurrence_pattern = db.Column(db.String(50))

    # Relationships
    instructor = db.relationship('User', backref='classes_teaching')
    attendances = db.relationship(
        'Attendance', backref='live_class', lazy=True)

    def __repr__(self):
        return f'<LiveClass {self.title}>'


class Attendance(db.Model):
    __tablename__ = 'attendances'
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey(
        'live_classes.id'), nullable=False)
    student_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    # 'present', 'absent', 'late'
    status = db.Column(db.String(20), default='present')
    join_time = db.Column(db.DateTime)
    leave_time = db.Column(db.DateTime)
    duration_minutes = db.Column(db.Integer)

    # Relationships
    student = db.relationship('User', backref='attendances')

    # Unique constraint to prevent duplicate attendance records
    __table_args__ = (db.UniqueConstraint(
        'class_id', 'student_id', name='uq_class_attendance'),)

    def __repr__(self):
        return f'<Attendance {self.class_id}-{self.student_id}>'


# Quiz and Assessment Models
class Quiz(db.Model):
    __tablename__ = 'quizzes'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    course_id = db.Column(db.Integer, db.ForeignKey(
        'course.id'), nullable=False)
    module_id = db.Column(
        db.Integer, db.ForeignKey('module.id'), nullable=True)
    time_limit_minutes = db.Column(
        db.Integer, default=0)  # 0 means no time limit
    passing_score = db.Column(db.Float, default=60.0)
    attempts_allowed = db.Column(db.Integer, default=1)  # -1 means unlimited
    shuffle_questions = db.Column(db.Boolean, default=False)
    show_correct_answers = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_published = db.Column(db.Boolean, default=False)

    # Relationships
    course = db.relationship(
        'Course', backref=db.backref('quizzes', lazy=True))
    module = db.relationship(
        'Module', backref=db.backref('quizzes', lazy=True))
    questions = db.relationship(
        'Question', backref='quiz', lazy=True, cascade='all, delete-orphan')
    attempts = db.relationship(
        'QuizAttempt', backref='quiz', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Quiz {self.title}>'


class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey(
        'quizzes.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    # 'mcq', 'true_false', 'fill_blank', 'short_answer'
    question_type = db.Column(db.String(20), nullable=False)
    points = db.Column(db.Float, default=1.0)
    negative_points = db.Column(db.Float, default=0.0)  # For negative marking
    order = db.Column(db.Integer, default=0)
    explanation = db.Column(db.Text)  # Explanation for the correct answer

    # Relationships
    options = db.relationship(
        'QuestionOption', backref='question', lazy=True, cascade='all, delete-orphan')
    answers = db.relationship(
        'QuestionAnswer', backref='question', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Question {self.id}: {self.question_text[:20]}...>'


class QuestionOption(db.Model):
    __tablename__ = 'question_options'
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey(
        'questions.id'), nullable=False)
    option_text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<QuestionOption {self.id}: {self.option_text[:20]}...>'


class QuestionAnswer(db.Model):
    __tablename__ = 'question_answers'
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey(
        'questions.id'), nullable=False)
    answer_text = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<QuestionAnswer {self.id}: {self.answer_text[:20]}...>'


class QuizAttempt(db.Model):
    __tablename__ = 'quiz_attempts'
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey(
        'quizzes.id'), nullable=False)
    student_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    score = db.Column(db.Float, default=0.0)
    max_score = db.Column(db.Float, default=0.0)
    percentage = db.Column(db.Float, default=0.0)
    is_passed = db.Column(db.Boolean, default=False)
    is_completed = db.Column(db.Boolean, default=False)

    # Relationships
    student = db.relationship('User', backref='quiz_attempts')
    responses = db.relationship(
        'QuizResponse', backref='attempt', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<QuizAttempt {self.id} by Student {self.student_id}>'


class QuizResponse(db.Model):
    __tablename__ = 'quiz_responses'
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey(
        'quiz_attempts.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey(
        'questions.id'), nullable=False)
    selected_option_id = db.Column(db.Integer, db.ForeignKey(
        'question_options.id'), nullable=True)
    text_response = db.Column(db.Text, nullable=True)
    is_correct = db.Column(db.Boolean, default=False)
    points_earned = db.Column(db.Float, default=0.0)
    instructor_feedback = db.Column(db.Text, nullable=True)

    # Relationships
    question = db.relationship('Question')
    selected_option = db.relationship(
        'QuestionOption', foreign_keys=[selected_option_id])

    def __repr__(self):
        return f'<QuizResponse {self.id} for Question {self.question_id}>'


# Grading and Certificate Models
class GradeItem(db.Model):
    __tablename__ = 'grade_items'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey(
        'course.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    # 'quiz', 'assignment', 'exam', 'project', etc.
    item_type = db.Column(db.String(20), nullable=False)
    max_points = db.Column(db.Float, default=100.0)
    # Weight in final grade calculation
    weight = db.Column(db.Float, default=1.0)
    due_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign keys to specific items
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey(
        'assignments.id'), nullable=True)

    # Relationships
    course = db.relationship(
        'Course', backref=db.backref('grade_items', lazy=True))
    student_grades = db.relationship(
        'StudentGrade', backref='grade_item', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<GradeItem {self.title}>'


class StudentGrade(db.Model):
    __tablename__ = 'student_grades'
    id = db.Column(db.Integer, primary_key=True)
    grade_item_id = db.Column(db.Integer, db.ForeignKey(
        'grade_items.id'), nullable=False)
    student_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    points = db.Column(db.Float, default=0.0)
    feedback = db.Column(db.Text)
    graded_by_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=True)
    graded_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    student = db.relationship('User', foreign_keys=[
                              student_id], backref='grades')
    graded_by = db.relationship('User', foreign_keys=[graded_by_id])

    # Unique constraint to prevent duplicate grades
    __table_args__ = (db.UniqueConstraint(
        'grade_item_id', 'student_id', name='uq_student_grade'),)

    def __repr__(self):
        return f'<StudentGrade {self.id} for Student {self.student_id}>'


class Certificate(db.Model):
    __tablename__ = 'certificates'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey(
        'course.id'), nullable=False)
    issue_date = db.Column(db.DateTime, default=datetime.utcnow)
    certificate_number = db.Column(db.String(50), unique=True)
    template_id = db.Column(db.Integer, db.ForeignKey(
        'certificate_templates.id'), nullable=True)
    file_path = db.Column(db.String(255), nullable=True)

    # Relationships
    student = db.relationship('User', backref='certificates')
    course = db.relationship('Course', backref='certificates')
    template = db.relationship('CertificateTemplate')

    def __repr__(self):
        return f'<Certificate {self.certificate_number}>'


class CertificateTemplate(db.Model):
    __tablename__ = 'certificate_templates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    template_file = db.Column(db.String(255))
    is_default = db.Column(db.Boolean, default=False)
    created_by_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    created_by = db.relationship('User')

    def __repr__(self):
        return f'<CertificateTemplate {self.name}>'


# Communication Models
class Announcement(db.Model):
    __tablename__ = 'announcements'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_by_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    course_id = db.Column(
        db.Integer, db.ForeignKey('course.id'), nullable=True)
    batch_id = db.Column(db.Integer, db.ForeignKey(
        'batches.id'), nullable=True)
    # If true, visible to all users
    is_global = db.Column(db.Boolean, default=False)

    # Relationships
    created_by = db.relationship('User', backref='announcements')
    course = db.relationship('Course', backref='announcements')
    batch = db.relationship('Batch', backref='announcements')

    def __repr__(self):
        return f'<Announcement {self.title}>'


class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(100), nullable=True)
    content = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime, nullable=True)
    is_read = db.Column(db.Boolean, default=False)

    # Relationships
    sender = db.relationship('User', foreign_keys=[
                             sender_id], backref='sent_messages')
    recipient = db.relationship(
        'User', foreign_keys=[recipient_id], backref='received_messages')

    def __repr__(self):
        return f'<Message {self.id} from {self.sender_id} to {self.recipient_id}>'


class DiscussionForum(db.Model):
    __tablename__ = 'discussion_forums'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    course_id = db.Column(
        db.Integer, db.ForeignKey('course.id'), nullable=True)
    created_by_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    course = db.relationship('Course', backref='forums')
    created_by = db.relationship('User')
    topics = db.relationship(
        'ForumTopic', backref='forum', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<DiscussionForum {self.title}>'


class ForumTopic(db.Model):
    __tablename__ = 'forum_topics'
    id = db.Column(db.Integer, primary_key=True)
    forum_id = db.Column(db.Integer, db.ForeignKey(
        'discussion_forums.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_by_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_pinned = db.Column(db.Boolean, default=False)
    is_locked = db.Column(db.Boolean, default=False)

    # Relationships
    created_by = db.relationship('User', backref='forum_topics')
    replies = db.relationship(
        'ForumReply', backref='topic', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ForumTopic {self.title}>'


class ForumReply(db.Model):
    __tablename__ = 'forum_replies'
    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey(
        'forum_topics.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_by_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    parent_id = db.Column(db.Integer, db.ForeignKey(
        'forum_replies.id'), nullable=True)

    # Relationships
    created_by = db.relationship('User', backref='forum_replies')
    parent = db.relationship('ForumReply', remote_side=[id], backref='replies')

    def __repr__(self):
        return f'<ForumReply {self.id}>'


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    notification_type = db.Column(
        db.String(20), nullable=False)  # 'email', 'sms', 'in_app'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime, nullable=True)
    is_read = db.Column(db.Boolean, default=False)

    # Relationships
    user = db.relationship('User', backref='notifications')

    def __repr__(self):
        return f'<Notification {self.id} for User {self.user_id}>'


# Assignment Models
class Assignment(db.Model):
    __tablename__ = 'assignments'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey(
        'course.id'), nullable=False)
    module_id = db.Column(
        db.Integer, db.ForeignKey('module.id'), nullable=True)
    created_by_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=True)
    max_points = db.Column(db.Float, default=100.0)
    allowed_file_extensions = db.Column(
        db.String(255), default='pdf,doc,docx,zip')
    max_file_size_mb = db.Column(db.Integer, default=10)
    plagiarism_check = db.Column(db.Boolean, default=False)

    # Relationships
    course = db.relationship('Course', backref='assignments')
    module = db.relationship('Module', backref='assignments')
    created_by = db.relationship('User', backref='created_assignments')
    submissions = db.relationship(
        'AssignmentSubmission', backref='assignment', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Assignment {self.title}>'


class AssignmentSubmission(db.Model):
    __tablename__ = 'assignment_submissions'
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey(
        'assignments.id'), nullable=False)
    student_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    submission_text = db.Column(db.Text, nullable=True)
    submission_file = db.Column(db.String(255), nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_late = db.Column(db.Boolean, default=False)
    points = db.Column(db.Float, nullable=True)
    feedback = db.Column(db.Text, nullable=True)
    graded_by_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=True)
    graded_at = db.Column(db.DateTime, nullable=True)
    # Percentage of plagiarism detected
    plagiarism_score = db.Column(db.Float, nullable=True)

    # Relationships
    student = db.relationship('User', foreign_keys=[
                              student_id], backref='assignment_submissions')
    graded_by = db.relationship('User', foreign_keys=[graded_by_id])

    # Unique constraint to prevent duplicate submissions
    __table_args__ = (db.UniqueConstraint(
        'assignment_id', 'student_id', name='uq_assignment_submission'),)

    def __repr__(self):
        return f'<AssignmentSubmission {self.id} by Student {self.student_id}>'


# Notes model for instructor to publish notes
class Notes(db.Model):
    __tablename__ = 'notes'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    file_path = db.Column(db.String(255), nullable=True)  # For uploaded files
    course_id = db.Column(db.Integer, db.ForeignKey(
        'course.id'), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey(
        'batches.id'), nullable=True)
    instructor_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_published = db.Column(db.Boolean, default=False)

    # Relationships
    course = db.relationship('Course', backref=db.backref('notes', lazy=True))
    batch = db.relationship('Batch', backref=db.backref('notes', lazy=True))
    instructor = db.relationship(
        'User', backref=db.backref('published_notes', lazy=True))

    def __repr__(self):
        return f'<Notes {self.title} for Course {self.course_id}>'
