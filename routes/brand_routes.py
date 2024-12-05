# routes/admin_routes.py
import os
from flask import Blueprint, request, render_template, session, redirect, url_for, flash
from werkzeug.utils import secure_filename
from .user_routes import admin_required
from models import User, Brand,CategoryType, db



brand_bp = Blueprint('brand_bp', __name__)

BRAND_UPLOAD_FOLDER = os.getenv('BRAND_UPLOAD_FOLDER', 'uploads/brands')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# View All Brands (Accessible to logged-in users)
@brand_bp.route('/brands', methods=['GET'])
def view_all_brands():
    current_user = session.get('user', None)
    
    # Restrict access if user is not logged in
    if not current_user:
        flash("Please log in to access this page.", "warning")
        return redirect(url_for('user.login'))

    # Query all brands
    all_brands = Brand.query.all()
    
    # Filter brands by category
    brands_by_category = {
        'tools_machinery': Brand.query.filter_by(category='tools_machinery').all(),
        'car_parts': Brand.query.filter_by(category='car_parts').all(),
        'household_items': Brand.query.filter_by(category='household_items').all(),
        'computers': Brand.query.filter_by(category='computers').all(),
        'cars': Brand.query.filter_by(category='cars').all(),
    }

    # Additional grouping logic if needed (optional)
    grouped_brands = {}
    for category in CategoryType:
        grouped_brands[category.name] = [
            brand for brand in all_brands if brand.category == category.name
        ]

    return render_template(
        'Brand/index.html',
        user=current_user,
        all_brands=all_brands,
        brands_by_category=brands_by_category,
        grouped_brands=grouped_brands
    )


# Create a Brand
@brand_bp.route('/brands/create', methods=['GET', 'POST'])
@admin_required
def create_brand():
    current_user = session.get('user', None)
    if request.method == 'GET':
        return render_template('Brand/create.html',user=current_user, cats=CategoryType )

    if request.method == 'POST':
        category = request.form.get('category')
        brand_name = request.form.get('brand_name')
        file = request.files.get('brand_logo')

        # Validate the brand name
        if not brand_name or not category:
            flash("Brand name is required!", "danger")
            return redirect(url_for('brand_bp.create_brand'))

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(BRAND_UPLOAD_FOLDER, filename)
            os.makedirs(BRAND_UPLOAD_FOLDER, exist_ok=True)  # Ensure the folder exists
            
            try:
                file.save(file_path)  # Save the file to the designated folder
                new_brand = Brand(brand_name=brand_name, brand_logo=filename, category=category)  # Store filename only
                db.session.add(new_brand)
                db.session.commit()
                flash("Brand created successfully!", "success")
                return redirect(url_for('brand_bp.view_all_brands'))
            except Exception as e:
                db.session.rollback()
                flash("An error occurred while creating the brand. Please try again.", "danger")
                return redirect(url_for('brand_bp.create_brand'))
        else:
            flash("Invalid file format or no file uploaded!", "danger")
            return redirect(url_for('brand_bp.create_brand'))
        
# Read One Brand
@brand_bp.route('/brand/<int:brand_id>', methods=['GET'])
def read_brand(brand_id):
    current_user = session.get('user', None)
    brand = Brand.query.get_or_404(brand_id)  # Fetch brand by ID
    return render_template('Brand/view.html', brand=brand, user=current_user)

# Update a Brand
@brand_bp.route('/brands/edit/<int:brand_id>', methods=['GET', 'POST'])
@admin_required
def update_brand(brand_id):
    current_user = session.get('user', None)
    brand = Brand.query.get_or_404(brand_id)

    if request.method == 'GET':
        return render_template('Brand/edit.html', brand=brand, user=current_user)

    if request.method == 'POST':
        brand_name = request.form.get('brand_name')
        file = request.files.get('brand_logo')

        # Validate the brand name
        if not brand_name:
            flash("Brand name is required!", "danger")
            return redirect(url_for('brand_bp.update_brand', brand_id=brand.id))

        try:
            brand.brand_name = brand_name
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(BRAND_UPLOAD_FOLDER, filename)
                os.makedirs(BRAND_UPLOAD_FOLDER, exist_ok=True)  # Ensure the folder exists
                file.save(file_path)  # Save the new file
                brand.brand_logo = filename  # Store filename only
            
            db.session.commit()
            flash("Brand updated successfully!", "success")
            return redirect(url_for('brand_bp.view_all_brands'))
        except Exception as e:
            db.session.rollback()
            flash("An error occurred while updating the brand. Please try again.", "danger")
            return redirect(url_for('brand_bp.update_brand', brand_id=brand.id))

    return redirect(url_for('brand_bp.view_all_brands'))  # Fallback return
    
# Delete a Brand
@brand_bp.route('/Brand/delete/<int:brand_id>', methods=['POST'])
@admin_required
def delete_brand(brand_id):
    brand = Brand.query.get_or_404(brand_id)
    db.session.delete(brand)
    db.session.commit()
    flash("Brand deleted successfully!", "success")
    return redirect(url_for('brand_bp.view_all_brands'))