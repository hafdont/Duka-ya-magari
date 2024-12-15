from authlib.integrations.flask_client import OAuth
from flask import Flask, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_login import LoginManager
from dotenv import load_dotenv
import os
import pymysql
import base64


# Initialize pymysql
pymysql.install_as_MySQLdb()

# Load environment variables from .env file
load_dotenv()

# Create Flask application
app = Flask(__name__)

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql://{os.getenv('DB_USERNAME')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

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

ALLOWED_FOLDERS = ['users', 'brands', 'cars', 'products']

# Configure JWT
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')  # Load JWT secret from .env
jwt = JWTManager(app)  # Initialize JWTManager


# Initialize SQLAlchemy and Flask-Migrate
db = SQLAlchemy(app)
migrate = Migrate(app, db)
oauth = OAuth(app)  # Initialize OAuth with the app
login_manager = LoginManager(app)  # Initialize LoginManager with the app

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


