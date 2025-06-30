import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


class Config:
    SECRET_KEY = os.environ.get(
        'SECRET_KEY', 'default-dev-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 'sqlite:///lms.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
