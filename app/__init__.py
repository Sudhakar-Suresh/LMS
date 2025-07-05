import os
from flask import Flask, json
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from datetime import datetime
from config import Config
from flask_ckeditor import CKEditor

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
ckeditor = CKEditor()


def create_app(config_class=Config):
    app = Flask(__name__)

    # Configuration
    app.config.from_object(config_class)

    # Create upload directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(
        app.config['UPLOAD_FOLDER'], 'thumbnails'), exist_ok=True)
    os.makedirs(os.path.join(
        app.config['UPLOAD_FOLDER'], 'video'), exist_ok=True)
    os.makedirs(os.path.join(
        app.config['UPLOAD_FOLDER'], 'audio'), exist_ok=True)
    os.makedirs(os.path.join(
        app.config['UPLOAD_FOLDER'], 'pdf'), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    ckeditor.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    # Register blueprints
    from app.routes.auth import auth
    from app.routes.admin import admin
    from app.routes.instructor import instructor
    from app.routes.student import student
    from app.routes.guest import guest
    from app.routes.parent import parent
    from app.routes.main import main

    app.register_blueprint(auth)
    app.register_blueprint(admin)
    app.register_blueprint(instructor)
    app.register_blueprint(student)
    app.register_blueprint(guest)
    app.register_blueprint(parent)
    app.register_blueprint(main)

    # Create database tables
    with app.app_context():
        db.create_all()

        # Add current datetime to template context
        @app.context_processor
        def inject_now():
            return {'now': datetime.utcnow()}

            # Add unread messages count for student users
        @app.context_processor
        def inject_unread_messages():
            from flask_login import current_user
            from app.models.user import Message
            from sqlalchemy import inspect

            unread_messages = 0
            if current_user.is_authenticated:
                try:
                    # Check if current_user has role attribute and it's a student
                    if hasattr(current_user, 'role') and current_user.role == 'student':
                        # Check if created_at column exists in Message table
                        inspector = inspect(db.engine)
                        columns = [column['name']
                                   for column in inspector.get_columns('messages')]

                        # Only filter by created_at if the column exists
                        unread_messages = Message.query.filter_by(
                            recipient_id=current_user.id,
                            is_read=False
                        ).count()
                except Exception as e:
                    print(f"Error getting unread messages: {str(e)}")
                    pass
            return {'unread_messages': unread_messages}

        # Add tojson filter
        @app.template_filter('tojson')
        def tojson_filter(obj):
            return json.dumps(obj)

        # Add normalize_path filter
        @app.template_filter('normalize_path')
        def normalize_path_filter(path):
            if path:
                return path.replace('\\', '/')
            return path

    return app
