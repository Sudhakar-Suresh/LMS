import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from datetime import datetime
from config import Config

# Initialize SQLAlchemy
db = SQLAlchemy()
login_manager = LoginManager()


def create_app(config_class=Config):
    app = Flask(__name__)

    # Configuration
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
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

    return app
