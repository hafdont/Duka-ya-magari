from flask import Blueprint, request, render_template, redirect, url_for, flash, session, jsonify, abort
from werkzeug.utils import secure_filename
from models import db, Blog, Image, Category, Brand, Order, Item, OrderStatus, Review, Like, Comment, User, BlogView
import os
from .user_routes import admin_required
from enum import Enum
from datetime import datetime, timedelta


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
        blog_data = get_blog_data_from_form(request.form)  
        
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
                if not allowed_file(file.filename):  
                    print(f"Invalid file type for file: {file.filename}")
                    flash(f"Invalid file type for file: {file.filename}", "danger")
                    continue  # Skip invalid files

                # Secure the filename and save the file
                filename = secure_filename(file.filename)
                file_path = os.path.join(BLOGS_UPLOAD_FOLDER, filename) 
                
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
            return redirect(url_for('blogs.get_blogs'))  # Redirect to the list of blogs or the new blog view

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

@blog_bp.route('/blog/<int:blog_id>', methods=['GET', 'POST'])
def view_blog(blog_id):
    current_user = session.get('user', None)

    try:
        blog = Blog.query.get_or_404(blog_id)
        blog.view_count = (blog.view_count or 0) + 1  # Handle None value
        db.session.commit()

        # Record the user view in BlogView (if the user is logged in)
        if current_user:
            user_id = current_user.get('id')
            new_view = BlogView(blog_id=blog_id, user_id=user_id)
        else:
            new_view = BlogView(blog_id=blog_id)

        db.session.add(new_view)
        db.session.commit()

    except Exception as e:
        db.session.rollback()  # Rollback on any database error
        print(f"Database error: {e}") # Log the error for debugging
        abort(500) # Or handle the error differently

    # Handle comment submission (rest of your existing code)
    if request.method == 'POST' and 'comment' in request.form:
        comment_content = request.form['comment']
        if not current_user:
            flash("Kindly log in to comment.")
            return redirect(url_for('user.login'))

        if comment_content:
            user_id = current_user.id if isinstance(current_user, User) else current_user.get('id')
            new_comment = Comment(content=comment_content, user_id=user_id, blog_id=blog_id)
            db.session.add(new_comment)
            db.session.commit()
            return redirect(url_for('blogs.view_blog', blog_id=blog.id)) # Redirect to avoid resubmission on refresh


    comments = Comment.query.filter_by(blog_id=blog_id).all()
    blog_likes_count = Like.query.filter_by(blog_id=blog_id, target_type='blog').count()

    liked_items = {}
    if current_user:
        user_id = current_user.get('id')
        liked_items['blog'] = [like.blog_id for like in Like.query.filter_by(user_id=user_id, target_type='blog').all()]
        liked_items['comment'] = [like.comment_id for like in Like.query.filter_by(user_id=user_id, target_type='comment').all()]

    comments_likes_count = {
        comment.id: Like.query.filter_by(comment_id=comment.id, target_type='comment').count()
        for comment in comments
    }

    return render_template(
        'blogs/view_blog.html',
        blog=blog,
        user=current_user,
        comments=comments,
        blog_likes_count=blog_likes_count,
        comments_likes_count=comments_likes_count,
        liked_items=liked_items
    )

@blog_bp.route('/blog/edit/<int:blog_id>', methods=['GET', 'POST'])
@admin_required
def edit_blog(blog_id):
    current_user = session.get('user', None)
    blog = Blog.query.get_or_404(blog_id)

    if request.method == 'POST':
        # Update blog title and content
        blog.title = request.form['title']
        blog.content = request.form['content']

        # Handle image uploads (multiple images)
        if 'images' in request.files:
            files = request.files.getlist('images')
            for file in files:
                if file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(BLOGS_UPLOAD_FOLDER, filename)
                    os.makedirs(BLOGS_UPLOAD_FOLDER, exist_ok=True)
                    file.save(file_path)

                    # Save new image in the database
                    new_image = Image(blog_id=blog.id, image_path=filename)
                    db.session.add(new_image)

        # Handle image deletions (if any)
        image_ids_to_delete = request.form.getlist('delete_images')
        if image_ids_to_delete:
            for image_id in image_ids_to_delete:
                image = Image.query.get(image_id)  # Find the image by ID
                if image:
                    # Delete image file from the server
                    os.remove(os.path.join(BLOGS_UPLOAD_FOLDER, image.image_path))  # Delete the image file
                    db.session.delete(image)  # Remove image from the database

        # Commit the changes to the database
        db.session.commit()

        flash('Blog updated successfully!', 'success')
        return redirect(url_for('blogs.view_blog', blog_id=blog.id))  # Redirect to the updated blog page

    # Render the form with the current blog data
    return render_template('blogs/edit_blog.html', blog=blog, user=current_user)