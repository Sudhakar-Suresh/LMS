from app import create_app, db
from app.models.user import User, UserProfile, UserRole
from werkzeug.security import generate_password_hash
from datetime import datetime

def init_users():
    app = create_app()
    with app.app_context():
        # Delete existing users
        User.query.delete()
        db.session.commit()
        
        print('Creating users with specified credentials...')
        
        # Create admin user
        admin = User(
            username='admin',
            first_name='Admin',
            last_name='User',
            email='admin@example.com',
            password=generate_password_hash('admin123'),
            role=UserRole.ADMIN,
            is_active=True,
            is_email_verified=True,
            created_at=datetime.utcnow()
        )

        # Create instructor users
        instructor1 = User(
            username='instructor1',
            first_name='John',
            last_name='Doe',
            email='instructor1@example.com',
            password=generate_password_hash('instructor123'),
            role=UserRole.INSTRUCTOR,
            is_active=True,
            is_email_verified=True,
            created_at=datetime.utcnow()
        )

        instructor2 = User(
            username='instructor2',
            first_name='Jane',
            last_name='Smith',
            email='instructor2@example.com',
            password=generate_password_hash('instructor123'),
            role=UserRole.INSTRUCTOR,
            is_active=True,
            is_email_verified=True,
            created_at=datetime.utcnow()
        )

        # Create student users
        student1 = User(
            username='student1',
            first_name='Alice',
            last_name='Johnson',
            email='student1@example.com',
            password=generate_password_hash('student123'),
            role=UserRole.STUDENT,
            is_active=True,
            is_email_verified=True,
            created_at=datetime.utcnow()
        )

        student2 = User(
            username='student2',
            first_name='Bob',
            last_name='Brown',
            email='student2@example.com',
            password=generate_password_hash('student123'),
            role=UserRole.STUDENT,
            is_active=True,
            is_email_verified=True,
            created_at=datetime.utcnow()
        )

        # Create parent user
        parent = User(
            username='parent',
            first_name='Michael',
            last_name='Johnson',
            email='parent@example.com',
            password=generate_password_hash('parent123'),
            role=UserRole.PARENT,
            is_active=True,
            is_email_verified=True,
            created_at=datetime.utcnow()
        )

        # Create guest user
        guest = User(
            username='guest',
            first_name='Guest',
            last_name='User',
            email='guest@example.com',
            password=generate_password_hash('guest123'),
            role=UserRole.GUEST,
            is_active=True,
            is_email_verified=True,
            created_at=datetime.utcnow()
        )

        # Add all users to the database
        db.session.add_all([admin, instructor1, instructor2, student1, student2, parent, guest])
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

        print('Users created successfully with the following credentials:')
        print('Admin: username=admin, password=admin123')
        print('Instructor 1: username=instructor1, password=instructor123')
        print('Instructor 2: username=instructor2, password=instructor123')
        print('Student 1: username=student1, password=student123')
        print('Student 2: username=student2, password=student123')
        print('Parent: username=parent, password=parent123')
        print('Guest: username=guest, password=guest123')

if __name__ == '__main__':
    init_users()
