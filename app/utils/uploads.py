import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app
from PIL import Image

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    'image': {'png', 'jpg', 'jpeg', 'gif'},
    'document': {'pdf', 'doc', 'docx', 'txt', 'rtf', 'odt'},
    'spreadsheet': {'xls', 'xlsx', 'csv'},
    'presentation': {'ppt', 'pptx'},
    'video': {'mp4', 'webm', 'avi', 'mov'},
    'audio': {'mp3', 'wav', 'ogg'}
}


def allowed_file(filename, file_type='image'):
    """Check if the file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower(
           ) in ALLOWED_EXTENSIONS.get(file_type, set())


def generate_unique_filename(filename):
    """Generate a unique filename to prevent overwriting"""
    unique_id = uuid.uuid4().hex
    _, extension = os.path.splitext(filename)
    return f"{unique_id}{extension}"


def save_profile_picture(file):
    """Save a profile picture with resizing"""
    if not file or not allowed_file(file.filename, 'image'):
        return None

    # Create profile pictures directory if it doesn't exist
    profile_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'profile')
    os.makedirs(profile_dir, exist_ok=True)

    # Generate a secure filename
    original_filename = secure_filename(file.filename)
    unique_filename = generate_unique_filename(original_filename)
    file_path = os.path.join(profile_dir, unique_filename)

    # Save and resize the image
    try:
        # Save the original file temporarily
        file.save(file_path)

        # Open the image and resize it
        with Image.open(file_path) as img:
            # Resize to a standard profile picture size (e.g., 300x300)
            img = img.resize((300, 300), Image.LANCZOS)

            # Save the resized image
            img.save(file_path)

        return unique_filename
    except Exception as e:
        print(f"Error saving profile picture: {e}")
        # If there was an error, try to remove the file if it exists
        if os.path.exists(file_path):
            os.remove(file_path)
        return None


def save_course_thumbnail(file):
    """Save a course thumbnail with resizing"""
    if not file or not allowed_file(file.filename, 'image'):
        return None

    # Create thumbnails directory if it doesn't exist
    thumbnail_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'thumbnails')
    os.makedirs(thumbnail_dir, exist_ok=True)

    # Generate a secure filename
    original_filename = secure_filename(file.filename)
    unique_filename = generate_unique_filename(original_filename)
    file_path = os.path.join(thumbnail_dir, unique_filename)

    # Save and resize the image
    try:
        # Save the original file temporarily
        file.save(file_path)

        # Open the image and resize it
        with Image.open(file_path) as img:
            # Resize to a standard thumbnail size (e.g., 800x450 for 16:9 aspect ratio)
            img = img.resize((800, 450), Image.LANCZOS)

            # Save the resized image
            img.save(file_path)

        return unique_filename
    except Exception as e:
        print(f"Error saving course thumbnail: {e}")
        # If there was an error, try to remove the file if it exists
        if os.path.exists(file_path):
            os.remove(file_path)
        return None


def save_file(file, directory, allowed_types=None):
    """Save a file to the specified directory"""
    if not file:
        return None

    if allowed_types and not allowed_file(file.filename, allowed_types):
        return None

    # Create directory if it doesn't exist
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], directory)
    os.makedirs(upload_dir, exist_ok=True)

    # Generate a secure filename
    original_filename = secure_filename(file.filename)
    unique_filename = generate_unique_filename(original_filename)
    file_path = os.path.join(upload_dir, unique_filename)

    try:
        file.save(file_path)
        return unique_filename
    except Exception as e:
        print(f"Error saving file: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
        return None
