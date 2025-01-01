from flask_dance.contrib.google import make_google_blueprint, google
from flask import Flask, send_from_directory, abort, session, request, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_login import LoginManager, login_user
from dotenv import load_dotenv
import os
import pymysql
import base64
import logging 
from logging.handlers import RotatingFileHandler
from datetime import datetime
from flask_apscheduler import APScheduler
from flask_mail import Mail, Message
import smtplib
from datetime import timedelta


# Initialize pymysql
pymysql.install_as_MySQLdb()

# Load environment variables from .env file
load_dotenv()

# Create Flask application
app = Flask(__name__)


if not app.debug: 
    app.config['SQLALCHEMY_ECHO'] = True
    log_file_path = os.getenv('LOG_FILE_PATH', 'logs/user_actions.log')
    handler = RotatingFileHandler(log_file_path, maxBytes=10000, backupCount=3)
    handler.setLevel(logging.INFO) 
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)


# Set up Flask-Mail configuration for sending emails
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
mail = Mail(app)

# In your Flask app setup (typically app.py)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=6)
app.config['SESSION_PERMANENT'] = True


# Log error details to email (optional)
def send_error_email(error_message):
    try:
        recipient = os.getenv('ERROR_LOG_EMAIL_RECIPIENT', 'admin@nasimgeneralmarchants.co.ke ')
        subject = 'Application Error Notification'
        msg = Message(subject, sender=app.config['MAIL_USERNAME'], recipients=[recipient])
        msg.body = f"An error occurred: {error_message}"
        mail.send(msg)
        app.logger.info("Error email sent successfully.")
    except Exception as e:
        app.logger.error(f"Failed to send error email: {e}")

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql://{os.getenv('DB_USERNAME')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize SQLAlchemy and Flask-Migrate
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)  # Initialize LoginManager with the app

# Set up Google OAuth with Flask-Dance
google_bp = make_google_blueprint(client_id=os.getenv('GOOGLE_CLIENT_ID'),
                                  client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
                                  redirect_to='google_register')
app.register_blueprint(google_bp, url_prefix='/google_login')


# Set up the scheduler for email logs
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

# Define the function that emails the log file
def send_log_email():
    try:
        with open(os.getenv('LOG_FILE_PATH', 'logs/user_actions.log'), 'r') as file:
            log_content = file.read()

        recipient = os.getenv('LOG_EMAIL_RECIPIENT', 'admin@nasimgeneralmarchants.co.ke ')
        subject = os.getenv('LOG_EMAIL_SUBJECT', 'Daily Log File from CarsPalace')

        msg = Message(subject, sender=app.config['MAIL_USERNAME'], recipients=[recipient])
        msg.body = log_content
        mail.send(msg)

        app.logger.info("Log file emailed successfully.")

    except Exception as e:
        app.logger.error(f"Failed to send email: {e}")

# Schedule the task to run every 24 hours
scheduler.add_job(id='send_log_email', func=send_log_email, trigger='interval', hours=24)

@app.before_request
def log_request():
    # Log every request before it is processed
    if 'user' in session:
        user_id = session['user'].get('id')
        username = session['user'].get('username')
        app.logger.info(f"User {username} (ID: {user_id}) made a request to {request.url} at {datetime.now()}.")
    else:
        app.logger.info(f"Anonymous user made a request to {request.url} at {datetime.now()}.")

@app.after_request
def log_response(response):
    # Log after a response is sent
    if response.status_code == 200:
        app.logger.info(f"Request to {request.url} completed successfully.")
    else:
        app.logger.error(f"Request to {request.url} failed with status code {response.status_code}.")
    
    return response


# Load environment variables
USER_UPLOAD_FOLDER = os.getenv('USER_UPLOAD_FOLDER', 'uploads/users')
BRAND_UPLOAD_FOLDER = os.getenv('BRAND_UPLOAD_FOLDER', 'uploads/brands')
CARS_UPLOAD_FOLDER = os.getenv('CARS_UPLOAD_FOLDER', 'uploads/cars')
PRODUCTS_UPLOAD_FOLDER = os.getenv('PRODUCTS_UPLOAD_FOLDER', 'uploads/products')
BLOGS_UPLOAD_FOLDER = os.getenv('BLOGS_UPLOAD_FOLDER', 'uploads/blogs')

# Ensure the upload folders exist
os.makedirs(USER_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(BRAND_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CARS_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PRODUCTS_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(BLOGS_UPLOAD_FOLDER, exist_ok=True)

ALLOWED_FOLDERS = ['users', 'brands', 'cars', 'products', 'blogs']

# Configure JWT
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')  # Load JWT secret from .env
jwt = JWTManager(app)  # Initialize JWTManager


# Define the base64 encoding filter
def b64encode(data):
    return base64.b64encode(data).decode('utf-8')

# Register the filter with Jinja2
app.jinja_env.filters['b64encode'] = b64encode

# Import models after initializing db
from models import Brand, Category, Car, Image, User, Cart, Order, Review, Payment, Like, Product

# Create a function to create tables if they don't exist
def create_tables():
    with app.app_context():
        db.create_all()

# Import and register routes
from routes import register_routes  
register_routes(app)

@app.route('/uploads/<folder>/<filename>')
def uploaded_file(folder, filename):
    # Validate folder name
    if folder not in ALLOWED_FOLDERS:
        abort(404)  # Invalid folder

    # Determine the upload folder based on the provided folder parameter
    if folder == 'users':
        upload_folder = USER_UPLOAD_FOLDER
    elif folder == 'brands':
        upload_folder = BRAND_UPLOAD_FOLDER
    elif folder == 'cars':
        upload_folder = CARS_UPLOAD_FOLDER
    elif folder == 'products':
        upload_folder = PRODUCTS_UPLOAD_FOLDER
    elif folder == 'blogs':
        upload_folder = BLOGS_UPLOAD_FOLDER

    try:
        return send_from_directory(os.path.join(app.root_path, 'uploads', folder), filename)
    except FileNotFoundError:
        abort(404)  # Return a 404 error if the file is not found


# Run the application
if __name__ == '__main__':
    app.run(debug=True)
    # Print all URL routes
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule}")

    create_tables() 
    print("done creating tables and staff") 
    # Call this to create the tables


