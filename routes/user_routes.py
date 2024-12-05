from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for, flash
from functools import wraps
from flask_bcrypt import Bcrypt
import os
from datetime import datetime
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from enum import Enum
from models import User, UserRole,  UserStatus, Gender
from app import db

load_dotenv()

USER_UPLOAD_FOLDER = os.getenv('USER_UPLOAD_FOLDER', 'uploads/users')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

bcrypt = Bcrypt()
user_bp = Blueprint('user', __name__)

def get_user_data_from_form(form):
    return {
        'username': form.get('username'),
        'firstname': form.get('firstname'),
        'lastname': form.get('lastname'),
        'email': form.get('email'),
        'password': form.get('password'),
        'role': form.get('role'),  # Role field (admin or customer)
        'city': form.get('city'),
        'postal_code': form.get('postal_code'),
        'country': form.get('country'),  # Added country field
        'phone_number': form.get('phone_number'),
        'bio': form.get('bio'),
        'date_of_birth': form.get('date_of_birth'),  # Added date_of_birth field
        'gender': form.get('gender'),  # Added gender field
        'status': form.get('status'),  # Added status field (active/inactive)
    }

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or session['user']['role'] != 'admin':
            flash("Access denied! Admins only.", "danger")
            return redirect(url_for('home_bp.index'))
        return f(*args, **kwargs)
    return decorated_function

# User Login
@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:  # Check if user is already logged in
        flash("You are already logged in!", "info")
        return redirect(url_for('home_bp.index'))  # Redirect to home if logged in

    if request.method == 'GET':
        return render_template('users/login.html')

    if request.method == 'POST':
        data = request.form
        identifier = data.get('identifier')
        password = data.get('password')

        user = User.query.filter((User.email == identifier) | (User.username == identifier)).first()

        if user and bcrypt.check_password_hash(user.password, password):
            session['user'] = {
                'id': user.id,
                'username': user.username,
                'firstname': user.firstname,
                'lastname': user.lastname,
                'profile_picture': user.profile_picture,
                'role': user.role.value,
            }
            flash("Login successful!", "success")
            return redirect(url_for('admin_bp.home') if user.role.value == 'admin' else url_for('home_bp.index'))            

        flash("Invalid credentials!", "danger")
        return redirect(url_for('user.login'))

# User Registration
@user_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('users/register.html')

    if request.method == 'POST':
        user_data = get_user_data_from_form(request.form)

        existing_user = User.query.filter_by(email=user_data['email']).first()
        if existing_user:
            flash("User already exists!", "danger")
            return redirect(url_for('user.register'))

        hashed_password = bcrypt.generate_password_hash(user_data['password']).decode('utf-8')
        new_user = User(
            username=user_data['username'],
            firstname=user_data['firstname'],
            lastname=user_data['lastname'],
            email=user_data['email'],
            password=hashed_password,
            role=UserRole.CUSTOMER  
        )
        db.session.add(new_user)
        db.session.commit()

        flash("User registered successfully!", "success")
        return redirect(url_for('user.login'))

# Edit User Profile
@user_bp.route('/editProfile/<int:user_id>', methods=['GET', 'POST'])
def edit_profile(user_id):
    current_user = session.get('user', None)

    if current_user is None:
        flash("You must be logged in to edit profiles.", "danger")
        return redirect(url_for('user.login'))

    user_to_edit = User.query.get(user_id)

    if user_to_edit is None:
        flash("User not found.", "danger")
        return redirect(url_for('home_bp.index'))

    # Updated Authorization check
    if UserRole(current_user['role'].lower()) != UserRole.ADMIN and current_user['id'] != user_id:
        flash("Unauthorized access! Only admins can edit other users' profiles.", "danger")
        return redirect(url_for('home_bp.index'))

    if request.method == 'GET':
        return render_template('users/userEdit.html', user=user_to_edit, roles=UserRole)

    if request.method == 'POST':
        user_data = get_user_data_from_form(request.form)

        # Handle profile picture upload with validation
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file.filename != '':
                if not allowed_file(file.filename):
                    flash("File type not allowed. Please upload an image file.", "danger")
                    return redirect(url_for('user.edit_profile', user_id=user_to_edit.id))

                filename = secure_filename(file.filename)
                file_path = os.path.join(USER_UPLOAD_FOLDER, filename)

                os.makedirs(USER_UPLOAD_FOLDER, exist_ok=True)

                try:
                    file.save(file_path)  # Save the file
                    user_to_edit.profile_picture = filename  # Store filename in the database
                except Exception as e:
                    flash(f"An error occurred while saving the profile picture: {e}", "danger")
                    return redirect(url_for('user.edit_profile', user_id=user_to_edit.id))

        # Update user fields with validation
        try:
            if user_data.get('username'):
                user_to_edit.username = user_data['username']
            if user_data.get('firstname'):
                user_to_edit.firstname = user_data['firstname']
            if user_data.get('lastname'):
                user_to_edit.lastname = user_data['lastname']
            if user_data.get('email'):
                user_to_edit.email = user_data['email']
            if user_data.get('city'):
                user_to_edit.city = user_data['city']
            if user_data.get('postal_code'):
                user_to_edit.postal_code = user_data['postal_code']
            if user_data.get('phone_number'):
                user_to_edit.phone_number = user_data['phone_number']
            if user_data.get('location'):
                user_to_edit.location = user_data['location']
            if user_data.get('bio'):
                user_to_edit.bio = user_data['bio']
            if user_data.get('date_of_birth'):
                user_to_edit.date_of_birth = datetime.strptime(user_data['date_of_birth'], '%Y-%m-%d')
            if user_data.get('gender'):
                user_to_edit.gender = user_data['gender']
            # Update role only if current user is an admin
            if current_user['role']:
                user_to_edit.role = user_data['role']
            # Commit changes
            db.session.commit()
            flash("Profile updated successfully!", "success")
        except Exception as e:
            db.session.rollback()  # Rollback changes if there's an error
            flash(f"An error occurred while updating the profile: {e}", "danger")
            return redirect(url_for('user.edit_profile', user_id=user_to_edit.id))

        return redirect(url_for('user.view_profile', user_id=user_to_edit.id))

    return redirect(url_for('home_bp.index'))  # Fallback return


# Delete User Profile
@user_bp.route('/delete_profile', methods=['POST'])
@admin_required
def delete_profile():
    current_user = session.get('user', None)
    if current_user:
        user = User.query.get(current_user['id'])

        if user:
            db.session.delete(user)
            db.session.commit()
            session.clear()
            flash("Profile deleted successfully!", "success")
            return redirect(url_for('home_bp.index'))

    flash("Unauthorized action!", "danger")
    return redirect(url_for('home_bp.index'))

# View All Users
@user_bp.route('/users', methods=['GET'])
@admin_required
def view_all_users():
    current_user = session.get('user', None)
    search_query = request.args.get('search')

    if search_query:
        users = User.query.filter(User.username.contains(search_query) | User.email.contains(search_query)).all()
    else:
        users = User.query.all()

    return render_template('users/index.html', users=users, user=current_user)

@user_bp.route('/logout')
def logout():
    session.clear()  # Clear the session
    flash("You have been logged out!", "success")
    return redirect(url_for('home_bp.index'))



# User Profile
@user_bp.route('/viewProfile/<int:user_id>', methods=['GET'])
def view_profile(user_id):
    current_user = session.get('user', None)

    if current_user is None:
        flash("You must be logged in to view profiles.", "danger")
        return redirect(url_for('user.login'))

    user = User.query.get(user_id)

    if user is None:
        flash("User not found.", "danger")
        return redirect(url_for('home_bp.index'))

    # User activity data
    user_orders_count = len(user.orders)
    user_likes_count = len(user.likes)
    user_cars_count = len(user.owned_cars)
    user_reviews_count = len(user.reviews)

    # Pass activity data along with user info
    return render_template('users/userProfile.html', user=user,
                           orders_count=user_orders_count,
                           likes_count=user_likes_count,
                           cars_count=user_cars_count,
                           reviews_count=user_reviews_count)
