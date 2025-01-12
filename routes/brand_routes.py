# routes/admin_routes.py
import os
from flask import Blueprint, request, render_template, session, redirect, url_for, flash
from werkzeug.utils import secure_filename
from .user_routes import admin_required
from models import User, Brand,CategoryType, Product, Order, Item, ProductSpecification, Car, db
from app import app, db
from sqlalchemy.orm import joinedload
from collections import Counter
from sqlalchemy import func, case
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
        'tools_machinery': Brand.query.filter_by(category='ToolsMachinery').all(),
        'car_parts': Brand.query.filter_by(category='CarParts').all(),
        'household_items': Brand.query.filter_by(category='HouseholdItems').all(),
        'computers': Brand.query.filter_by(category='Computers').all(),
        'cars': Brand.query.filter_by(category='Cars').all(),
    }

   
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
        print(category)

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
@admin_required
def read_brand(brand_id):
    current_user = session.get('user', None)
    brand = Brand.query.get_or_404(brand_id)  # Fetch brand by ID
    
    # Count the number of cars under this brand
    cars_count = Car.query.filter_by(brand_id=brand.id).count()

    # Get the list of cars under this brand
    cars = Car.query.filter_by(brand_id=brand.id).all()

    # Count the number of products under this brand 
    products_count = Product.query.filter_by(brand_id=brand.id).all()

    # Get the list of products under this brand
    products = Product.query.filter_by(brand_id=brand.id).all()

    # Count the number of orders containing products or cars from this brand
    orders_count = db.session.query(Order).join(Item).outerjoin(Product, Item.product_id == Product.id).outerjoin(Car, Item.car_id == Car.id) \
        .filter((Product.brand_id == brand.id) | (Car.brand_id == brand.id)) \
        .distinct(Order.id).count()

    # Get the list of orders containing products or cars from this brand
    orders = db.session.query(Order).join(Item).outerjoin(Product, Item.product_id == Product.id).outerjoin(Car, Item.car_id == Car.id) \
        .filter((Product.brand_id == brand.id) | (Car.brand_id == brand.id)) \
        .distinct(Order.id).all()

    return render_template('Brand/view.html', brand=brand, user=current_user, cars_count=cars_count, products_count=products_count, orders_count=orders_count, cars=cars, products=products, orders=orders)


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
    
@brand_bp.route('/Brand/delete/<int:brand_id>', methods=['POST'])
@admin_required
def delete_brand(brand_id):
    current_user = session.get('user', None)
    brand = Brand.query.get_or_404(brand_id)

    # Ensure that all related cars have their brand_id set to NULL
    cars_to_update = Car.query.filter_by(brand_id=brand.id).all()
    products_to_update = Product.query.filter_by(brand_id=brand_id).all()
    for car in cars_to_update:
        car.brand_id = None

    for product in products_to_update:
        product.brand_id = None

    # Commit the updates to the cars
    db.session.commit()

    # Now, delete the brand
    db.session.delete(brand)
    db.session.commit()

    flash("Brand deleted successfully!", "success")
    return redirect(url_for('brand_bp.view_all_brands'))

@brand_bp.route('/Brands/admin')
@admin_required
def brand_home():
    current_user = session.get('user', None)
    
    try:
        # Get all brands
        brands = Brand.query.all()

        # Query to get orders related to products
        product_orders = db.session.query(
            Product.brand_id,
            Order.order_status,
            func.count(Order.id).label('order_count')
        ).join(
            Item, Item.product_id == Product.id
        ).join(
            Order, Order.id == Item.order_id
        ).group_by(
            Product.brand_id, Order.order_status
        ).all()

        # Query to get orders related to cars
        car_orders = db.session.query(
            Car.brand_id,
            Order.order_status,
            func.count(Order.id).label('order_count')
        ).join(
            Item, Item.car_id == Car.id
        ).join(
            Order, Order.id == Item.order_id
        ).group_by(
            Car.brand_id, Order.order_status
        ).all()

        # Combine product and car order counts
        brand_order_status = {}
        for product_order in product_orders:
            if product_order.brand_id not in brand_order_status:
                brand_order_status[product_order.brand_id] = {}
            brand_order_status[product_order.brand_id][product_order.order_status] = product_order.order_count

        for car_order in car_orders:
            if car_order.brand_id not in brand_order_status:
                brand_order_status[car_order.brand_id] = {}
            brand_order_status[car_order.brand_id][car_order.order_status] = car_order.order_count

        # Filter brands based on low stock of products and cars
        brands_with_low_stock = Brand.query.outerjoin(Product).filter(Product.stock < 5).all()
        brands_with_no_cars = Brand.query.outerjoin(Car).filter(Car.stock == 0).all()

        # Brand statistics (products and cars count)
        brand_stats = []
        for brand in brands:
            brand_products = Product.query.filter_by(brand_id=brand.id).count()
            brand_cars = Car.query.filter_by(brand_id=brand.id).count()
            low_stock_products = Product.query.filter_by(brand_id=brand.id, stock=0).count()
            brand_stats.append({
                'brand_name': brand.brand_name,
                'brand_products': brand_products,
                'brand_cars': brand_cars,
                'low_stock_products': low_stock_products
            })
        
    except Exception as e:
        app.logger.error(f"Error in brand home: {e}")
        return render_template('error.html', message="An error occurred while loading brand data.")

    # Render the template and pass the required data
    return render_template(
        'Brand/brandHome.html', 
        user=current_user,
        brands=brands,
        brands_with_low_stock=brands_with_low_stock, 
        brands_with_no_cars=brands_with_no_cars, 
        brand_stats=brand_stats,
        brand_order_status=brand_order_status
    )
