Segreta - Echoes of Love
Overview
Segreta is a Flask-based web application with a romantic, cosmic-themed design. The application features user authentication (signup/login) with a poetic, love-themed interface that includes animated starry backgrounds and ethereal visual effects. The project appears to be in early development, focusing on establishing the foundational user management system with an elegant, space-inspired aesthetic.

User Preferences
Preferred communication style: Simple, everyday language.

System Architecture
Frontend Architecture
Template Engine: Jinja2 templates with Flask's render_template system
Styling: Custom CSS with cosmic/romantic theme featuring gradients, animations, and backdrop filters
JavaScript: Vanilla JavaScript for interactive elements including:
Animated starry background using HTML5 Canvas
Form submissions via fetch API for AJAX functionality
Responsive navigation menu toggle
Design Pattern: Traditional server-side rendered pages with client-side enhancements
Backend Architecture
Framework: Flask (Python web framework)
Architecture Pattern: Monolithic application structure
Session Management: Flask's built-in session handling with server-side storage
Password Security: Werkzeug's generate_password_hash and check_password_hash for secure password handling
API Design: RESTful endpoints returning JSON responses for authentication actions
Data Storage
Database: SQLite with SQLAlchemy ORM
Schema Design: Simple User model with:
Primary key (id)
Unique constraints on username and email
Hashed password storage
Migration Strategy: Flask-SQLAlchemy automatic table creation
Authentication System
Method: Username/email and password-based authentication
Password Hashing: Werkzeug's secure hashing algorithms
Session Management: Flask sessions for maintaining login state
Validation: Email format validation and duplicate user checking
Application Structure
Route Organization: All routes defined in main app.py file
Static Assets: Organized in /static directory with subdirectories for CSS and JavaScript
Templates: HTML templates in /templates directory following Flask conventions
Configuration: Direct configuration in app.py with hardcoded values
External Dependencies
Python Packages
Flask 3.0.3: Core web framework
Flask-SQLAlchemy 3.1.1: ORM and database integration
Werkzeug 3.0.3: WSGI utilities and security functions
email-validator 2.0.0: Email format validation
gunicorn 23.0.0: WSGI HTTP server for production deployment
Frontend Dependencies
Google Fonts: Poppins font family for typography
HTML5 Canvas: For animated starry background effects
CSS3: Advanced features like backdrop-filter, gradients, and animations
Database
SQLite: Embedded database for local development and simple deployment
File-based storage: users.db file in application root directory
Development Tools
Local Development: Flask's built-in development server
Production: Gunicorn WSGI server configuration ready