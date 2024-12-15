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

def get_blog_data_from_form(form_data):
    return {
        'title': form_data['title'],
        'content': form_data['content'],
        'user_id': session['user']['id'], 
    }

@blog_bp.route('/blog/new', methods=['GET', 'POST'])
@admin_required
def create_blog():
    current_user = session.get('user', None)
    tinymce_api_key = os.getenv('TINYMCE_API_KEY')

    if request.method == 'GET':
        return render_template('blogs/newBlog.html', user=current_user,TINYMCE_API_KEY=tinymce_api_key)

    if request.method == 'POST':
        # Extract form data
        blog_data = get_blog_data_from_form(request.form)  # Assuming you have a helper function to get form data
        
        # Handle saving blog post data
        new_blog = Blog(**blog_data)
        db.session.add(new_blog)
        db.session.commit()  # Commit to get the new_blog.id
        
        # Handle image upload
        if 'images' in request.files:
            files = request.files.getlist('images')
            print("Files Uploaded:", files)

            if not files or all(file.filename == '' for file in files):
                print("No files selected.")
                flash("No images selected or invalid file type.", "danger")
                return redirect(url_for('blog.create_blog'))

            # Process and save each uploaded image
            for file in files:
                if not allowed_file(file.filename):  # Assuming `allowed_file` is a function to check valid file types
                    print(f"Invalid file type for file: {file.filename}")
                    flash(f"Invalid file type for file: {file.filename}", "danger")
                    continue  # Skip invalid files

                # Secure the filename and save the file
                filename = secure_filename(file.filename)
                file_path = os.path.join(BLOGS_UPLOAD_FOLDER, filename)  # Assuming BLOGS_UPLOAD_FOLDER is configured in your settings

                # Create directory if it doesn't exist
                os.makedirs(BLOGS_UPLOAD_FOLDER, exist_ok=True)
                print(f"Saving file to: {file_path}")
                file.save(file_path)
                print(f"File saved successfully: {filename}")

                # Save the image with reference to the new blog
                new_image = Image(blog_id=new_blog.id, image_path=filename)
                db.session.add(new_image)

            # Commit the images after all are processed
            db.session.commit()
            print(f"New blog and images added to the database: {new_blog.id}")

            # After successful blog creation
            flash("Blog created successfully!", "success")
            return redirect(url_for('blog.get_blogs'))  # Redirect to the list of blogs or the new blog view

        # If no image upload, show an error message
        print("Image upload required.")
        flash("Image upload required.", "danger")
        return redirect(url_for('blog.create_blog'))

@blog_bp.route('/blogs')
def get_blogs():
    current_user = session.get('user', None)
    # Query the database to fetch all blogs
    blogs = Blog.query.all()
    # Render the blogs page with the fetched blogs
    return render_template('blogs/blogs.html', blogs=blogs, user=current_user)

@blog_bp.route('/blog/<int:blog_id>')
def view_blog(blog_id):
    current_user = session.get('user', None)
    # Fetch the specific blog by ID
    blog = Blog.query.get_or_404(blog_id)
    # Render a template to display the full blog content
    return render_template('blogs/view_blog.html', blog=blog, user=current_user,)