# Learning Management System (LMS)

A comprehensive Flask-based Learning Management System with different user roles and dashboards.

## Features

- **User Roles**: Admin, Instructor, Student, Guest, Parent
- **Authentication**: User registration and login functionality
- **Role-Based Dashboards**: Customized dashboards for each user role
- **Course Management**: Create, view, and manage courses
- **SQLite Database**: Lightweight database for storing user and course information
- **Responsive Design**: Built with Bootstrap for a mobile-friendly experience

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: HTML, CSS, JavaScript
- **CSS Framework**: Bootstrap 5
- **Icons**: Font Awesome

## Project Structure

```
LMS/
├── app/
│   ├── models/
│   │   └── user.py
│   ├── routes/
│   │   ├── admin.py
│   │   ├── auth.py
│   │   ├── guest.py
│   │   ├── instructor.py
│   │   ├── main.py
│   │   ├── parent.py
│   │   └── student.py
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css
│   │   ├── js/
│   │   │   └── script.js
│   │   └── img/
│   ├── templates/
│   │   ├── admin/
│   │   │   └── dashboard.html
│   │   ├── auth/
│   │   │   ├── login.html
│   │   │   └── register.html
│   │   ├── guest/
│   │   │   └── dashboard.html
│   │   ├── instructor/
│   │   │   └── dashboard.html
│   │   ├── parent/
│   │   │   └── dashboard.html
│   │   ├── student/
│   │   │   └── dashboard.html
│   │   ├── base.html
│   │   ├── index.html
│   │   └── about.html
│   └── __init__.py
├── app.py
├── config.py
├── init_db.py
├── requirements.txt
└── README.md
```

## Installation

1. Clone the repository:

```
git clone https://github.com/yourusername/LMS.git
cd LMS
```

2. Create a virtual environment and activate it:

```
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```
pip install -r requirements.txt
```

4. Initialize the database with sample data (optional):

```
python init_db.py
```

5. Run the application:

```
python app.py
```

6. Access the application in your browser at `http://localhost:5000`

## Sample Users

If you initialized the database with sample data, you can use the following credentials to log in:

| Role       | Username    | Password      |
| ---------- | ----------- | ------------- |
| Admin      | admin       | admin123      |
| Instructor | instructor1 | instructor123 |
| Instructor | instructor2 | instructor123 |
| Student    | student1    | student123    |
| Student    | student2    | student123    |
| Parent     | parent      | parent123     |
| Guest      | guest       | guest123      |

## Custom User Registration

You can also register your own users with different roles through the registration page.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
