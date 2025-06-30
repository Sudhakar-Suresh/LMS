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

    def __repr__(self):
        return f"Topic('{self.title}', Type: {self.content_type})"


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
