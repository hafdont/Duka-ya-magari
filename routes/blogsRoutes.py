from flask import Blueprint, request, render_template, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
from models import db, Product, ProductSpecification, CategoryType, Blog, StockStatus, User, Image, Category, Brand, Order, Item, OrderStatus, Review
import os
from .user_routes import admin_required
from enum import Enum

blog_bp = Blueprint('blogs', __name__)

# Set upload folder for product images (if applicable)
BLOGS_UPLOAD_FOLDER = os.getenv('BLOGS_UPLOAD_FOLDER', 'uploads/blogs')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@blog_bp.route('/blog/new', methods=['GET', 'POST'])
@admin_required
def create_blog():
    current_user = session.get('user', None)

    if request.method == 'GET':
        return render_template('blogs/newBlog.html', user=current_user)
