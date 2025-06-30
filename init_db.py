from app import create_app, db
from app.models.user import User, Course, Enrollment, ParentStudent, UserRole, CourseCategory, CourseTag, Module, Lesson, Topic
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta


def init_db():
    app = create_app()
    with app.app_context():
        # Clear existing data
        db.drop_all()
        db.create_all()

        print("Creating sample users...")

        # Create admin user
        admin = User(
            username="admin",
            email="admin@example.com",
            password=generate_password_hash("admin123", method='sha256'),
            first_name="Admin",
            last_name="User",
            role=UserRole.ADMIN
        )
        db.session.add(admin)

        # Create instructor users
        instructor1 = User(
            username="instructor1",
            email="instructor1@example.com",
            password=generate_password_hash("instructor123", method='sha256'),
            first_name="John",
            last_name="Smith",
            role=UserRole.INSTRUCTOR
        )
        db.session.add(instructor1)

        instructor2 = User(
            username="instructor2",
            email="instructor2@example.com",
            password=generate_password_hash("instructor123", method='sha256'),
            first_name="Sarah",
            last_name="Johnson",
            role=UserRole.INSTRUCTOR
        )
        db.session.add(instructor2)

        # Create student users
        student1 = User(
            username="student1",
            email="student1@example.com",
            password=generate_password_hash("student123", method='sha256'),
            first_name="Michael",
            last_name="Brown",
            role=UserRole.STUDENT
        )
        db.session.add(student1)

        student2 = User(
            username="student2",
            email="student2@example.com",
            password=generate_password_hash("student123", method='sha256'),
            first_name="Emily",
            last_name="Davis",
            role=UserRole.STUDENT
        )
        db.session.add(student2)

        # Create parent user
        parent = User(
            username="parent",
            email="parent@example.com",
            password=generate_password_hash("parent123", method='sha256'),
            first_name="Robert",
            last_name="Brown",
            role=UserRole.PARENT
        )
        db.session.add(parent)

        # Create guest user
        guest = User(
            username="guest",
            email="guest@example.com",
            password=generate_password_hash("guest123", method='sha256'),
            first_name="Guest",
            last_name="User",
            role=UserRole.GUEST
        )
        db.session.add(guest)

        # Commit to get IDs
        db.session.commit()

        print("Creating course categories and tags...")

        # Create course categories
        categories = [
            CourseCategory(
                name="Programming", description="Courses related to programming languages and software development"),
            CourseCategory(
                name="Data Science", description="Courses covering data analysis, machine learning, and statistics"),
            CourseCategory(name="Web Development",
                           description="Courses on web technologies, frameworks, and design"),
            CourseCategory(name="Mobile Development",
                           description="Courses focused on mobile app development"),
            CourseCategory(name="Computer Science",
                           description="Theoretical computer science and algorithms")
        ]

        for category in categories:
            db.session.add(category)

        # Create course tags
        tags = [
            CourseTag(name="Beginner"),
            CourseTag(name="Intermediate"),
            CourseTag(name="Advanced"),
            CourseTag(name="Python"),
            CourseTag(name="JavaScript"),
            CourseTag(name="Database"),
            CourseTag(name="Algorithms"),
            CourseTag(name="Frontend"),
            CourseTag(name="Backend"),
            CourseTag(name="Machine Learning")
        ]

        for tag in tags:
            db.session.add(tag)

        # Commit to get IDs
        db.session.commit()

        print("Creating sample courses...")

        # Create courses
        course1 = Course(
            title="Introduction to Programming",
            description="Learn the basics of programming using Python. This course covers variables, data types, control structures, functions, and more.",
            instructor_id=instructor1.id,
            category_id=categories[0].id,  # Programming category
            is_published=True,
            thumbnail="thumbnails/python_intro.jpg"
        )
        # Add tags to course1
        course1.tags.append(tags[0])  # Beginner
        course1.tags.append(tags[3])  # Python
        db.session.add(course1)

        course2 = Course(
            title="Database Systems",
            description="Introduction to database design, SQL, and database management systems. Learn how to create, query, and manage relational databases.",
            instructor_id=instructor1.id,
            category_id=categories[0].id,  # Programming category
            is_published=True,
            thumbnail="thumbnails/database.jpg"
        )
        # Add tags to course2
        course2.tags.append(tags[1])  # Intermediate
        course2.tags.append(tags[5])  # Database
        db.session.add(course2)

        course3 = Course(
            title="Advanced Algorithms",
            description="Study of advanced algorithms and data structures. Topics include graph algorithms, dynamic programming, and complexity analysis.",
            instructor_id=instructor2.id,
            category_id=categories[4].id,  # Computer Science category
            is_published=True,
            thumbnail="thumbnails/algorithms.jpg"
        )
        # Add tags to course3
        course3.tags.append(tags[2])  # Advanced
        course3.tags.append(tags[6])  # Algorithms
        db.session.add(course3)

        # Commit to get IDs
        db.session.commit()

        print("Creating course content (modules, lessons, topics)...")

        # Create modules, lessons, and topics for course1
        module1 = Module(
            title="Getting Started with Python",
            description="Introduction to Python programming language and setup",
            course_id=course1.id,
            order=0
        )
        db.session.add(module1)

        module2 = Module(
            title="Basic Python Concepts",
            description="Learn about variables, data types, and basic operations",
            course_id=course1.id,
            order=1
        )
        db.session.add(module2)

        # Commit to get module IDs
        db.session.commit()

        # Lessons for module1
        lesson1_1 = Lesson(
            title="Introduction to the Course",
            module_id=module1.id,
            order=0
        )
        db.session.add(lesson1_1)

        lesson1_2 = Lesson(
            title="Setting Up Python Environment",
            module_id=module1.id,
            order=1
        )
        db.session.add(lesson1_2)

        # Lessons for module2
        lesson2_1 = Lesson(
            title="Variables and Data Types",
            module_id=module2.id,
            order=0
        )
        db.session.add(lesson2_1)

        lesson2_2 = Lesson(
            title="Basic Operations and Expressions",
            module_id=module2.id,
            order=1
        )
        db.session.add(lesson2_2)

        # Commit to get lesson IDs
        db.session.commit()

        # Topics for lesson1_1
        topic1_1_1 = Topic(
            title="Course Overview",
            content="<h2>Welcome to Introduction to Programming!</h2><p>In this course, you will learn the fundamentals of programming using Python. Python is a versatile and beginner-friendly language that is widely used in various fields including web development, data science, artificial intelligence, and more.</p><p>By the end of this course, you will be able to:</p><ul><li>Write basic Python programs</li><li>Understand core programming concepts</li><li>Solve problems using programming logic</li><li>Create simple applications</li></ul>",
            content_type="text",
            lesson_id=lesson1_1.id,
            order=0
        )
        db.session.add(topic1_1_1)

        topic1_1_2 = Topic(
            title="Why Learn Programming?",
            content="<h2>The Importance of Programming Skills</h2><p>Programming has become an essential skill in today's digital world. Learning to code helps you:</p><ul><li>Develop problem-solving abilities</li><li>Create software solutions</li><li>Automate repetitive tasks</li><li>Analyze and visualize data</li><li>Enhance career opportunities</li></ul><p>Whether you're interested in becoming a professional developer or just want to understand how technology works, programming knowledge is invaluable.</p>",
            content_type="text",
            lesson_id=lesson1_1.id,
            order=1
        )
        db.session.add(topic1_1_2)

        # Topics for lesson1_2
        topic1_2_1 = Topic(
            title="Installing Python",
            content="<h2>Installing Python on Your Computer</h2><p>Before we start coding, you need to install Python on your computer. Follow these steps:</p><ol><li>Go to <a href='https://www.python.org/downloads/' target='_blank'>python.org/downloads</a></li><li>Download the latest version for your operating system</li><li>Run the installer and make sure to check 'Add Python to PATH'</li><li>Verify the installation by opening a command prompt or terminal and typing: <code>python --version</code></li></ol>",
            content_type="text",
            lesson_id=lesson1_2.id,
            order=0
        )
        db.session.add(topic1_2_1)

        # Topics for lesson2_1
        topic2_1_1 = Topic(
            title="Understanding Variables",
            content="<h2>Variables in Python</h2><p>Variables are containers for storing data values. In Python, you don't need to declare a variable's type, and you can change the value stored in a variable during program execution.</p><pre><code># Creating variables\nname = \"John\"\nage = 25\nheight = 1.75\nis_student = True\n\n# Printing variables\nprint(name)\nprint(age)\nprint(height)\nprint(is_student)</code></pre><p>Variables are essential for storing and manipulating data in your programs.</p>",
            content_type="text",
            lesson_id=lesson2_1.id,
            order=0
        )
        db.session.add(topic2_1_1)

        topic2_1_2 = Topic(
            title="Data Types in Python",
            content="<h2>Common Data Types</h2><p>Python has several built-in data types:</p><ul><li><strong>Numeric Types:</strong> int, float, complex</li><li><strong>Text Type:</strong> str</li><li><strong>Boolean Type:</strong> bool</li><li><strong>Sequence Types:</strong> list, tuple, range</li><li><strong>Mapping Type:</strong> dict</li><li><strong>Set Types:</strong> set, frozenset</li></ul><pre><code># Examples of different data types\nint_num = 10\nfloat_num = 10.5\ntext = \"Hello, World!\"\nmy_list = [1, 2, 3, 4]\nmy_dict = {\"name\": \"John\", \"age\": 25}\nmy_set = {1, 2, 3}</code></pre>",
            content_type="text",
            lesson_id=lesson2_1.id,
            order=1
        )
        db.session.add(topic2_1_2)

        print("Creating enrollments...")

        # Create enrollments
        enrollment1 = Enrollment(
            student_id=student1.id,
            course_id=course1.id,
            enrollment_date=datetime.utcnow() - timedelta(days=30)
        )
        db.session.add(enrollment1)

        enrollment2 = Enrollment(
            student_id=student1.id,
            course_id=course2.id,
            enrollment_date=datetime.utcnow() - timedelta(days=15)
        )
        db.session.add(enrollment2)

        enrollment3 = Enrollment(
            student_id=student2.id,
            course_id=course1.id,
            enrollment_date=datetime.utcnow() - timedelta(days=20)
        )
        db.session.add(enrollment3)

        enrollment4 = Enrollment(
            student_id=student2.id,
            course_id=course3.id,
            enrollment_date=datetime.utcnow() - timedelta(days=10)
        )
        db.session.add(enrollment4)

        print("Creating parent-student relationships...")

        # Create parent-student relationship
        parent_student = ParentStudent(
            parent_id=parent.id,
            student_id=student1.id
        )
        db.session.add(parent_student)

        # Commit all changes
        db.session.commit()

        print("Database initialized successfully!")


if __name__ == "__main__":
    init_db()
