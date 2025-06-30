from app import create_app, db
from app.models.user import User, Course, Enrollment, ParentStudent, UserRole, CourseCategory, CourseTag, Module, Lesson, Topic, Batch, BatchEnrollment, LiveClass, Attendance, Quiz, Question, QuestionOption, QuestionAnswer, Assignment, GradeItem, CertificateTemplate, DiscussionForum, ForumTopic, ForumReply, Announcement, UserProfile, Role, Permission, UserLoginHistory
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta, date


def init_db():
    app = create_app()
    with app.app_context():
        # Drop all tables
        db.drop_all()

        # Create all tables
        db.create_all()

        print("Creating users...")
        # Create admin user
        admin = User(
            username="admin",
            first_name="Admin",
            last_name="User",
            email="admin@example.com",
            password=generate_password_hash("admin123"),
            role=UserRole.ADMIN,
            is_active=True,
            is_email_verified=True
        )

        # Create instructor users
        instructor1 = User(
            username="instructor1",
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password=generate_password_hash("instructor123"),
            role=UserRole.INSTRUCTOR,
            is_active=True,
            is_email_verified=True
        )

        instructor2 = User(
            username="instructor2",
            first_name="Jane",
            last_name="Smith",
            email="jane@example.com",
            password=generate_password_hash("instructor123"),
            role=UserRole.INSTRUCTOR,
            is_active=True,
            is_email_verified=True
        )

        # Create student users
        student1 = User(
            username="student1",
            first_name="Alice",
            last_name="Johnson",
            email="alice@example.com",
            password=generate_password_hash("student123"),
            role=UserRole.STUDENT,
            is_active=True,
            is_email_verified=True
        )

        student2 = User(
            username="student2",
            first_name="Bob",
            last_name="Brown",
            email="bob@example.com",
            password=generate_password_hash("student123"),
            role=UserRole.STUDENT,
            is_active=True,
            is_email_verified=True
        )

        # Create parent user
        parent = User(
            username="parent",
            first_name="Michael",
            last_name="Johnson",
            email="michael@example.com",
            password=generate_password_hash("parent123"),
            role=UserRole.PARENT,
            is_active=True,
            is_email_verified=True
        )

        # Create guest user
        guest = User(
            username="guest",
            first_name="Guest",
            last_name="User",
            email="guest@example.com",
            password=generate_password_hash("guest123"),
            role=UserRole.GUEST,
            is_active=True,
            is_email_verified=True
        )

        # Add all users to the database
        db.session.add(admin)
        db.session.add(instructor1)
        db.session.add(instructor2)
        db.session.add(student1)
        db.session.add(student2)
        db.session.add(parent)
        db.session.add(guest)
        db.session.commit()

        # Create user profiles
        admin_profile = UserProfile(user=admin)
        instructor1_profile = UserProfile(user=instructor1)
        instructor2_profile = UserProfile(user=instructor2)
        student1_profile = UserProfile(user=student1)
        student2_profile = UserProfile(user=student2)
        parent_profile = UserProfile(user=parent)
        guest_profile = UserProfile(user=guest)

        db.session.add_all([admin_profile, instructor1_profile, instructor2_profile,
                            student1_profile, student2_profile, parent_profile, guest_profile])
        db.session.commit()

        # Create parent-student relationship
        parent_student = ParentStudent(
            parent_id=parent.id,
            student_id=student1.id
        )
        db.session.add(parent_student)
        db.session.commit()

        # Create RBAC roles and permissions
        print("Creating roles and permissions...")
        # Create permissions
        view_dashboard = Permission(
            name="view_dashboard", description="Can view dashboard")
        manage_users = Permission(
            name="manage_users", description="Can manage users")
        manage_courses = Permission(
            name="manage_courses", description="Can manage courses")
        view_courses = Permission(
            name="view_courses", description="Can view courses")
        enroll_courses = Permission(
            name="enroll_courses", description="Can enroll in courses")
        create_content = Permission(
            name="create_content", description="Can create course content")
        grade_assignments = Permission(
            name="grade_assignments", description="Can grade assignments")
        submit_assignments = Permission(
            name="submit_assignments", description="Can submit assignments")
        view_grades = Permission(
            name="view_grades", description="Can view grades")
        manage_system = Permission(
            name="manage_system", description="Can manage system settings")

        db.session.add_all([view_dashboard, manage_users, manage_courses, view_courses,
                            enroll_courses, create_content, grade_assignments, submit_assignments,
                            view_grades, manage_system])
        db.session.commit()

        # Create roles
        admin_role = Role(name="admin_role",
                          description="Administrator role with full access")
        instructor_role = Role(name="instructor_role",
                               description="Instructor role")
        student_role = Role(name="student_role", description="Student role")
        parent_role = Role(name="parent_role", description="Parent role")
        guest_role = Role(name="guest_role",
                          description="Guest role with limited access")

        # Assign permissions to roles
        admin_role.permissions = [view_dashboard, manage_users, manage_courses, view_courses,
                                  enroll_courses, create_content, grade_assignments, view_grades, manage_system]

        instructor_role.permissions = [view_dashboard, manage_courses, view_courses, create_content,
                                       grade_assignments, view_grades]

        student_role.permissions = [
            view_dashboard, view_courses, enroll_courses, submit_assignments, view_grades]

        parent_role.permissions = [view_dashboard, view_grades]

        guest_role.permissions = [view_courses]

        db.session.add_all([admin_role, instructor_role,
                           student_role, parent_role, guest_role])
        db.session.commit()

        # Create course categories
        print("Creating course categories...")
        programming_category = CourseCategory(name="Programming")
        web_dev_category = CourseCategory(name="Web Development")
        data_science_category = CourseCategory(name="Data Science")

        db.session.add(programming_category)
        db.session.add(web_dev_category)
        db.session.add(data_science_category)
        db.session.commit()

        # Create course tags
        print("Creating course tags...")
        python_tag = CourseTag(name="Python")
        javascript_tag = CourseTag(name="JavaScript")
        html_tag = CourseTag(name="HTML")
        css_tag = CourseTag(name="CSS")
        data_analysis_tag = CourseTag(name="Data Analysis")

        db.session.add(python_tag)
        db.session.add(javascript_tag)
        db.session.add(html_tag)
        db.session.add(css_tag)
        db.session.add(data_analysis_tag)
        db.session.commit()

        print("Creating courses...")
        # Create courses
        python_course = Course(
            title="Python Programming",
            description="Learn Python programming from scratch",
            instructor_id=instructor1.id,
            is_published=True,
            category_id=programming_category.id
        )
        python_course.tags.append(python_tag)

        web_dev_course = Course(
            title="Web Development Fundamentals",
            description="Learn HTML, CSS, and JavaScript",
            instructor_id=instructor2.id,
            is_published=True,
            category_id=web_dev_category.id
        )
        web_dev_course.tags.append(html_tag)
        web_dev_course.tags.append(css_tag)
        web_dev_course.tags.append(javascript_tag)

        data_science_course = Course(
            title="Introduction to Data Science",
            description="Learn data analysis with Python",
            instructor_id=instructor1.id,
            is_published=False,
            category_id=data_science_category.id
        )
        data_science_course.tags.append(python_tag)
        data_science_course.tags.append(data_analysis_tag)

        # Add courses to the database
        db.session.add(python_course)
        db.session.add(web_dev_course)
        db.session.add(data_science_course)
        db.session.commit()

        # Create enrollments
        print("Creating enrollments...")
        enrollment1 = Enrollment(
            student_id=student1.id,
            course_id=python_course.id,
            enrollment_date=datetime.now()
        )

        enrollment2 = Enrollment(
            student_id=student1.id,
            course_id=web_dev_course.id,
            enrollment_date=datetime.now()
        )

        enrollment3 = Enrollment(
            student_id=student2.id,
            course_id=web_dev_course.id,
            enrollment_date=datetime.now()
        )

        # Add enrollments to the database
        db.session.add(enrollment1)
        db.session.add(enrollment2)
        db.session.add(enrollment3)
        db.session.commit()

        # Create modules for Python course
        print("Creating course content...")
        python_module1 = Module(
            title="Getting Started with Python",
            description="Introduction to Python programming language",
            course_id=python_course.id,
            order=1
        )

        python_module2 = Module(
            title="Data Structures in Python",
            description="Learn about lists, dictionaries, sets, and tuples",
            course_id=python_course.id,
            order=2
        )

        # Add modules to the database
        db.session.add(python_module1)
        db.session.add(python_module2)
        db.session.commit()

        # Create lessons for Python modules
        python_lesson1 = Lesson(
            title="Installing Python",
            module_id=python_module1.id,
            order=1,
            release_days=0
        )

        python_lesson2 = Lesson(
            title="Python Syntax",
            module_id=python_module1.id,
            order=2,
            release_days=1
        )

        python_lesson3 = Lesson(
            title="Lists and Tuples",
            module_id=python_module2.id,
            order=1,
            release_days=3
        )

        # Add lessons to the database
        db.session.add(python_lesson1)
        db.session.add(python_lesson2)
        db.session.add(python_lesson3)
        db.session.commit()

        # Create topics for Python lessons
        python_topic1 = Topic(
            title="Windows Installation",
            content="<p>Steps to install Python on Windows:</p><ol><li>Download the installer from python.org</li><li>Run the installer</li><li>Check 'Add Python to PATH'</li><li>Click Install Now</li></ol>",
            lesson_id=python_lesson1.id,
            order=1
        )

        python_topic2 = Topic(
            title="Mac Installation",
            content="<p>Steps to install Python on Mac:</p><ol><li>Download the installer from python.org</li><li>Run the installer</li><li>Follow the installation wizard</li></ol>",
            lesson_id=python_lesson1.id,
            order=2
        )

        python_topic3 = Topic(
            title="Variables and Data Types",
            content="<p>Python has the following basic data types:</p><ul><li>Integers</li><li>Floats</li><li>Strings</li><li>Booleans</li></ul>",
            lesson_id=python_lesson2.id,
            order=1
        )

        # Add topics to the database
        db.session.add(python_topic1)
        db.session.add(python_topic2)
        db.session.add(python_topic3)
        db.session.commit()

        # Create batches for courses
        print("Creating batches...")
        python_batch = Batch(
            name="Python Morning Batch 2023",
            course_id=python_course.id,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=60),
            max_students=25,
            description="Morning batch for Python Programming course. Classes will be held on weekdays from 9 AM to 11 AM."
        )

        web_dev_batch = Batch(
            name="Web Development Weekend Batch",
            course_id=web_dev_course.id,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=90),
            max_students=20,
            description="Weekend batch for Web Development course. Classes will be held on Saturdays and Sundays from 10 AM to 1 PM."
        )

        db.session.add(python_batch)
        db.session.add(web_dev_batch)
        db.session.commit()

        # Enroll students in batches
        print("Enrolling students in batches...")
        python_batch_enrollment = BatchEnrollment(
            batch_id=python_batch.id,
            student_id=student1.id,
            enrollment_date=datetime.now()
        )

        web_dev_batch_enrollment = BatchEnrollment(
            batch_id=web_dev_batch.id,
            student_id=student2.id,
            enrollment_date=datetime.now()
        )

        db.session.add(python_batch_enrollment)
        db.session.add(web_dev_batch_enrollment)
        db.session.commit()

        # Create live classes
        print("Creating live classes...")
        # Python course classes
        python_class1 = LiveClass(
            title="Introduction to Python Variables and Data Types",
            batch_id=python_batch.id,
            instructor_id=instructor1.id,
            start_time=datetime.now() + timedelta(days=1, hours=10),
            end_time=datetime.now() + timedelta(days=1, hours=12),
            platform="zoom",
            meeting_link="https://zoom.us/j/123456789",
            meeting_id="123456789",
            meeting_password="python123",
            description="In this class, we will cover Python variables, data types, and basic operations."
        )

        python_class2 = LiveClass(
            title="Control Flow in Python",
            batch_id=python_batch.id,
            instructor_id=instructor1.id,
            start_time=datetime.now() + timedelta(days=3, hours=10),
            end_time=datetime.now() + timedelta(days=3, hours=12),
            platform="zoom",
            meeting_link="https://zoom.us/j/123456790",
            meeting_id="123456790",
            meeting_password="python123",
            description="In this class, we will cover if statements, loops, and other control flow mechanisms in Python."
        )

        # Web Development course classes
        web_dev_class1 = LiveClass(
            title="HTML Fundamentals",
            batch_id=web_dev_batch.id,
            instructor_id=instructor2.id,
            start_time=datetime.now() + timedelta(days=5, hours=10),
            end_time=datetime.now() + timedelta(days=5, hours=13),
            platform="google_meet",
            meeting_link="https://meet.google.com/abc-defg-hij",
            description="In this class, we will cover HTML basics, tags, and document structure."
        )

        web_dev_class2 = LiveClass(
            title="CSS Styling",
            batch_id=web_dev_batch.id,
            instructor_id=instructor2.id,
            start_time=datetime.now() + timedelta(days=6, hours=10),
            end_time=datetime.now() + timedelta(days=6, hours=13),
            platform="google_meet",
            meeting_link="https://meet.google.com/xyz-uvwx-yz",
            description="In this class, we will cover CSS selectors, properties, and styling techniques."
        )

        # Add a past class with attendance
        past_class = LiveClass(
            title="Python Setup and Environment",
            batch_id=python_batch.id,
            instructor_id=instructor1.id,
            start_time=datetime.now() - timedelta(days=2, hours=2),
            end_time=datetime.now() - timedelta(days=2),
            platform="zoom",
            meeting_link="https://zoom.us/j/123456788",
            meeting_id="123456788",
            meeting_password="python123",
            description="In this class, we covered Python installation and setting up the development environment."
        )

        db.session.add(python_class1)
        db.session.add(python_class2)
        db.session.add(web_dev_class1)
        db.session.add(web_dev_class2)
        db.session.add(past_class)
        db.session.commit()

        # Add attendance records
        print("Adding attendance records...")
        attendance1 = Attendance(
            class_id=past_class.id,
            student_id=student1.id,
            status="present",
            join_time=past_class.start_time + timedelta(minutes=5),
            leave_time=past_class.end_time - timedelta(minutes=10),
            duration_minutes=110
        )

        db.session.add(attendance1)
        db.session.commit()

        # Create sample quiz
        print("Creating sample quizzes and questions...")
        python_quiz = Quiz(
            title="Python Basics Quiz",
            description="Test your knowledge of Python fundamentals",
            course_id=python_course.id,
            module_id=python_module1.id,
            time_limit_minutes=30,
            passing_score=70.0,
            attempts_allowed=2,
            shuffle_questions=True,
            is_published=True
        )

        web_quiz = Quiz(
            title="HTML & CSS Fundamentals",
            description="Test your knowledge of web development basics",
            course_id=web_dev_course.id,
            time_limit_minutes=20,
            passing_score=60.0,
            attempts_allowed=3,
            is_published=True
        )

        db.session.add(python_quiz)
        db.session.add(web_quiz)
        db.session.commit()

        # Create questions for Python quiz
        q1 = Question(
            quiz_id=python_quiz.id,
            question_text="What is the output of print(2 + 2)?",
            question_type="mcq",
            points=1.0,
            order=1
        )

        q1_options = [
            QuestionOption(question_id=q1.id, option_text="4",
                           is_correct=True, order=1),
            QuestionOption(question_id=q1.id, option_text="2 + 2",
                           is_correct=False, order=2),
            QuestionOption(question_id=q1.id, option_text="22",
                           is_correct=False, order=3),
            QuestionOption(question_id=q1.id, option_text="Error",
                           is_correct=False, order=4)
        ]

        q2 = Question(
            quiz_id=python_quiz.id,
            question_text="Which of these is a valid Python data type?",
            question_type="mcq",
            points=1.0,
            order=2
        )

        q2_options = [
            QuestionOption(question_id=q2.id, option_text="integer",
                           is_correct=False, order=1),
            QuestionOption(question_id=q2.id, option_text="int",
                           is_correct=True, order=2),
            QuestionOption(question_id=q2.id, option_text="number",
                           is_correct=False, order=3),
            QuestionOption(question_id=q2.id, option_text="num",
                           is_correct=False, order=4)
        ]

        q3 = Question(
            quiz_id=python_quiz.id,
            question_text="Python is a dynamically typed language.",
            question_type="true_false",
            points=1.0,
            order=3
        )

        q3_options = [
            QuestionOption(question_id=q3.id, option_text="True",
                           is_correct=True, order=1),
            QuestionOption(question_id=q3.id, option_text="False",
                           is_correct=False, order=2)
        ]

        q4 = Question(
            quiz_id=python_quiz.id,
            question_text="What function is used to get the length of a list?",
            question_type="fill_blank",
            points=2.0,
            order=4
        )

        q4_answer = QuestionAnswer(question_id=q4.id, answer_text="len")

        db.session.add_all([q1, q2, q3, q4])
        db.session.add_all(q1_options + q2_options + q3_options)
        db.session.add(q4_answer)
        db.session.commit()

        # Create sample assignment
        print("Creating sample assignments...")
        python_assignment = Assignment(
            title="Python Variables Exercise",
            description="Create a Python script that demonstrates the use of variables and basic operations.",
            course_id=python_course.id,
            module_id=python_module1.id,
            created_by_id=instructor1.id,
            due_date=datetime.now() + timedelta(days=7),
            max_points=100.0,
            allowed_file_extensions="py,txt",
            max_file_size_mb=5
        )

        web_assignment = Assignment(
            title="Create a Simple Webpage",
            description="Build a simple webpage using HTML and CSS that includes a header, navigation, main content, and footer.",
            course_id=web_dev_course.id,
            created_by_id=instructor2.id,
            due_date=datetime.now() + timedelta(days=10),
            max_points=100.0,
            allowed_file_extensions="html,css,zip",
            max_file_size_mb=10
        )

        db.session.add(python_assignment)
        db.session.add(web_assignment)
        db.session.commit()

        # Create grade items
        print("Creating grade items...")
        python_quiz_grade = GradeItem(
            course_id=python_course.id,
            title="Python Basics Quiz",
            description="Quiz on Python fundamentals",
            item_type="quiz",
            max_points=100.0,
            weight=0.3,
            quiz_id=python_quiz.id
        )

        python_assignment_grade = GradeItem(
            course_id=python_course.id,
            title="Python Variables Exercise",
            description="Assignment on Python variables",
            item_type="assignment",
            max_points=100.0,
            weight=0.7,
            assignment_id=python_assignment.id,
            due_date=python_assignment.due_date
        )

        db.session.add(python_quiz_grade)
        db.session.add(python_assignment_grade)
        db.session.commit()

        # Create certificate template
        print("Creating certificate template...")
        default_template = CertificateTemplate(
            name="Default Certificate",
            description="Standard certificate template",
            template_file="default_certificate.html",
            is_default=True,
            created_by_id=admin.id
        )

        db.session.add(default_template)
        db.session.commit()

        # Create discussion forum
        print("Creating discussion forums...")
        python_forum = DiscussionForum(
            title="Python Course Discussion",
            description="Forum for discussing Python course topics",
            course_id=python_course.id,
            created_by_id=instructor1.id
        )

        general_forum = DiscussionForum(
            title="General Discussion",
            description="Forum for general topics and questions",
            created_by_id=admin.id
        )

        db.session.add(python_forum)
        db.session.add(general_forum)
        db.session.commit()

        # Create forum topics
        python_topic = ForumTopic(
            forum_id=python_forum.id,
            title="Getting Started with Python",
            content="Share your experience with Python installation and setup.",
            created_by_id=instructor1.id,
            is_pinned=True
        )

        db.session.add(python_topic)
        db.session.commit()

        # Create forum replies
        python_reply = ForumReply(
            topic_id=python_topic.id,
            content="I found the Python installation process to be straightforward on Windows 10.",
            created_by_id=student1.id
        )

        instructor_reply = ForumReply(
            topic_id=python_topic.id,
            content="Great to hear! Let me know if you encounter any issues with the setup.",
            created_by_id=instructor1.id,
            parent_id=python_reply.id
        )

        db.session.add(python_reply)
        db.session.add(instructor_reply)
        db.session.commit()

        # Create announcements
        print("Creating announcements...")
        course_announcement = Announcement(
            title="Welcome to Python Programming",
            content="Welcome to the Python Programming course! We'll start with the basics and work our way up to more advanced topics.",
            created_by_id=instructor1.id,
            course_id=python_course.id
        )

        global_announcement = Announcement(
            title="System Maintenance",
            content="The LMS will be undergoing maintenance this weekend. Please expect some downtime.",
            created_by_id=admin.id,
            is_global=True
        )

        db.session.add(course_announcement)
        db.session.add(global_announcement)
        db.session.commit()

        print("Database initialized successfully!")


if __name__ == "__main__":
    init_db()
