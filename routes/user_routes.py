from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for, flash
from functools import wraps
from flask_bcrypt import Bcrypt
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from enum import Enum
from models import User, UserRole,  UserStatus, Gender
from app import db, login_manager, google, mail, app
from flask_mail import Message
from flask_login import login_user, logout_user, LoginManager
import logging

# Add logging for Flask-Mail
app.logger.setLevel(logging.DEBUG)


bcrypt = Bcrypt()
user_bp = Blueprint('user', __name__)

load_dotenv()


USER_UPLOAD_FOLDER = os.getenv('USER_UPLOAD_FOLDER', 'uploads/users')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_user_data_from_form(form, current_user=None):
    data = {
        'username': form.get('username'),
        'firstname': form.get('firstname'),
        'lastname': form.get('lastname'),
        'email': form.get('email'),
        'password': form.get('password'),
        'city': form.get('city'),
        'postal_code': form.get('postal_code'),
        'country': form.get('country'),
        'phone_number': form.get('phone_number'),
        'bio': form.get('bio'),
        'date_of_birth': form.get('date_of_birth'),
        'gender': form.get('gender'),
        'status': form.get('status'),
    }

    # Only allow admins to modify the role
    if current_user and current_user['role'] == 'admin':
        data['role'] = form.get('role')
    elif current_user:
        # If not admin, ensure role stays unchanged (don't set it to null)
        data['role'] = current_user['role']
    else:
        # If current_user is None, don't set a role (like in registration)
        data['role'] = 'customer'  # Default to 'customer' role

    return data


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
            session.permanent = True  # Make session permanent to enable timeout
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

# Google OAuth callback route
@user_bp.route('/google_register')
def google_register():
    if not google.authorized:
        return redirect(url_for('user.google_login'))  # Redirect to Google login if not authorized

    # Get the user's info from Google
    google_user = google.get('/plus/v1/people/me')
    user_data = google_user.json()

    # Extract relevant information from Google user data
    user_info = {
        'email': user_data['emails'][0]['value'],
        'username': user_data['displayName'],
        'firstname': user_data['name']['givenName'],
        'lastname': user_data['name']['familyName'],
        'profile_picture': user_data['image']['url'],
    }

    # Check if the user already exists
    existing_user = User.query.filter_by(email=user_info['email']).first()
    if existing_user:
        session['user'] = {
            'id': existing_user.id,
            'username': existing_user.username,
            'firstname': existing_user.firstname,
            'lastname': existing_user.lastname,
            'profile_picture': existing_user.profile_picture,
            'role': existing_user.role.value,
        }
        flash("Logged in successfully with Google!", "success")
        return redirect(url_for('home_bp.index'))

    # Create a new user if they don't exist
    new_user = User(
        username=user_info['username'],
        firstname=user_info['firstname'],
        lastname=user_info['lastname'],
        email=user_info['email'],
        profile_picture=user_info['profile_picture'],
        role=UserRole.CUSTOMER,
    )
    db.session.add(new_user)
    db.session.commit()

    # Log in the newly created user
    session['user'] = {
        'id': new_user.id,
        'username': new_user.username,
        'firstname': new_user.firstname,
        'lastname': new_user.lastname,
        'profile_picture': new_user.profile_picture,
        'role': new_user.role.value,
    }

    flash("User registered and logged in via Google!", "success")
    return redirect(url_for('home_bp.index'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Route to initiate Google login
@user_bp.route('/google_login')
def google_login():
    redirect_uri = url_for('user_bp.google_register', _external=True)
    return google.authorize_redirect(redirect_uri)


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
        user_data = get_user_data_from_form(request.form, current_user)

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

            # Refresh the session if role changes

            if user_data.get('role') != current_user['role']:
                session['user']['role'] = user_data['role']  # Refresh the session's role

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
        users = User.query.filter(User.username.contains(search_query) | User.email.contains(search_query) | User.phone_number.contains(search_query)).all()
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



@user_bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if request.method == 'POST':
        identifier = request.form['identifier']  # This can be either username or email

        # Find the user by either username or email
        user = User.query.filter((User.email == identifier) | (User.username == identifier)).first()

        if user:
            print(user.email)
            # Generate a bcrypt token for the reset link
            reset_token = user.generate_reset_token()  # Token generation logic here
            reset_link = url_for('user.reset_password', token=reset_token, _external=True)
            

            # Set the reset token and expiration in the user record
            user.reset_token = reset_token
            user.reset_token_expiry = datetime.now() + timedelta(minutes=30)  # 30-minute expiry
            db.session.commit()

            try:
                # Create the email message
                msg = Message(
                    subject="Password Reset",
                    recipients=[user.email],  # The recipient email
                    html=render_template(
                        'email/email_template.html',  # Template path
                        message=f"Click the link below to reset your password:\n{reset_link}"
                    )
                )

                # Log before sending email
                app.logger.debug(f"Sending email to: {user.email}")
                # Send the email
                mail.send(msg)

                # Log success
                app.logger.debug(f"Email successfully sent to: {user.email}")

                flash("Password reset link sent! Check your email.", "info")
                return redirect(url_for('user.login'))
            except Exception as e:
                app.logger.error(f"Error sending email: {e}")
                flash("There was an error sending the password reset email. Please try again.", "danger")
                return redirect(url_for('user.reset_password_request'))
            
        flash("No user found with that username or email.", "danger")
        return redirect(url_for('user.reset_password_request'))
            
    return render_template('reset_password_request.html')

@user_bp.route('/reset_password/<path:token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    print(token)

    # Check if the user exists, and the token is valid (i.e., not expired)
    if user and user.reset_token_expiry > datetime.now():
        if request.method == 'POST':
            new_password = request.form['password']

            # Hash the new password using bcrypt
            hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            
            # Update the user's password
            user.password = hashed_password
            user.reset_token = None  # Clear the token after successful reset
            user.reset_token_expiry = None  # Clear the expiry timestamp
            db.session.commit()

            flash("Your password has been reset. Please log in.", "success")
            return redirect(url_for('user.login'))

        return render_template('reset_password.html', token=token)

    flash("The reset link is either invalid or expired.", "danger")
    return redirect(url_for('user.reset_password_request'))
