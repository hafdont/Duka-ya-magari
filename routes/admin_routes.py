# routes/admin_routes.py
from flask import Blueprint, render_template, session
from .user_routes import admin_required
from models import User  # Ensure this import is correct

admin_bp = Blueprint('admin_bp', __name__)

@admin_bp.route('/home')
@admin_required
def home():
    current_user = session.get('user')  # Fetch user from the database
    return render_template('/Admin/home.html', user=current_user)  # Pass user to the template
