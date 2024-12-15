from flask import Blueprint, request, render_template, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
from models import db, Product, ProductSpecification, CategoryType, StockStatus, User, Image, Category, Brand, Order, Item, OrderStatus, Review
import os
from .user_routes import admin_required
from enum import Enum

product_bp = Blueprint('product', __name__)

# Set upload folder for product images (if applicable)
PRODUCTS_UPLOAD_FOLDER = os.getenv('PRODUCTS_UPLOAD_FOLDER', 'uploads/products')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@product_bp.route('/products/create', methods=['GET', 'POST'])
@admin_required
def create_product():
    current_user = session.get('user', None)

    if request.method == 'GET':
        categories = CategoryType
        return render_template(
            'products/new_product.html',
            categories=categories,
            user=current_user
        )

    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        price = request.form.get('price')
        stock = request.form.get('stock', 1)  # Default stock to 1
        description = request.form.get('description')
        category = request.form.get('category')

        # Validate form fields
        if not name or not price:
            flash("Name, Price are required fields.", "danger")
            return redirect(url_for('product.create_product'))

        # Save product data first
        try:
            new_product = Product(
                name=name,
                price=price,
                stock=stock,
                description=description,
                category=CategoryType[category],
                user_id=current_user.get('id') if current_user else None
            )
            db.session.add(new_product)
            db.session.commit()  # Commit to generate the product ID
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating product: {str(e)}", "danger")
            return redirect(url_for('product.create_product'))

        # Handle image uploads
        if 'images' in request.files:
            files = request.files.getlist('images')
            print("Files Uploaded:", [file.filename for file in files])

            if not files or all(file.filename == '' for file in files):
                print("No valid files selected.")
                flash("Please upload at least one valid image.", "danger")
                db.session.rollback()  # Roll back product creation if no images
                return redirect(url_for('product.create_product'))

            # Process and save each image
            for file in files:
                if not allowed_file(file.filename):
                    print(f"Invalid file type for: {file.filename}")
                    flash(f"Invalid file type: {file.filename}", "danger")
                    continue  # Skip invalid files

                filename = secure_filename(file.filename)
                file_path = os.path.join(PRODUCTS_UPLOAD_FOLDER, filename)

                # Create directory if it doesn't exist
                os.makedirs(PRODUCTS_UPLOAD_FOLDER, exist_ok=True)
                print(f"Saving file to: {file_path}")
                file.save(file_path)

                # Save image record in the database
                new_image = Image(product_id=new_product.id, image_path=filename)
                db.session.add(new_image)

            # Commit all images
            db.session.commit()
            print(f"Product and images saved successfully: {new_product.id}")
            flash("Product created successfully!", "success")
            return redirect(url_for('product.get_products'))

        # No images uploaded
        print("No images uploaded.")
        flash("At least one image is required.", "danger")
        db.session.rollback()  # Roll back product creation if no images
        return redirect(url_for('product.create_product'))

    # Fallback in case of unhandled scenarios
    flash("An unexpected error occurred.", "danger")
    return redirect(url_for('product.create_product'))

@product_bp.route('/products', methods=['GET'])
def get_products():
    current_user = session.get('user', None)
    products = Product.query.all()
    return render_template('products/product_list.html', products=products, user=current_user)


@product_bp.route('/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    current_user = session.get('user', None)
    product = Product.query.get_or_404(product_id)
    specifications = ProductSpecification.query.filter_by(product_id=product.id).all()
    reviews = Review.query.filter_by(product_id=product.id).all()

    category_type_enum = product.category  # Enum member, not value
    categories = Category.query.filter_by(category_type=category_type_enum.value).all()
    brands = Brand.query.filter_by(category=category_type_enum.value).all()

    # Fetch orders associated with the product (via Item model)
    orders_with_product = (
        Order.query.join(Item)
        .filter(Item.product_id == product.id)
        .all()
    )

        # Fetch completed orders associated with the product
    completed_orders_with_product = (
        Order.query.join(Item)
        .filter(
            Item.product_id == product.id,
            Order.order_status == OrderStatus.COMPLETED
        )
        .all()
    )

    # Fetch all categories for dropdowns
    categories_for_dropdown = Category.query.all()

    return render_template(
        'products/product_detail.html',
        product=product,
        specifications=specifications,
        user=current_user,
        categories=categories,
        brands=brands,
        orders_with_product=orders_with_product,  # Include related orders for the product
        categories_for_dropdown=categories_for_dropdown,
        completed_orders_with_product=completed_orders_with_product,
        reviews=reviews
    )

@product_bp.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
def update_product(product_id):
    product = Product.query.get_or_404(product_id)

    if request.method == 'GET':
        categories = [cat.value for cat in CategoryType]
        specifications = ProductSpecification.query.filter_by(product_id=product.id).all()
        return render_template('products/edit_product.html', product=product, categories=categories, specifications=specifications)
    
    if request.method == 'POST':
        product.name = request.form.get('name')
        product.price = request.form.get('price')
        product.stock = request.form.get('stock', 1)
        product.StockStatus = request.form.get('stock_status')
        product.category = request.form.get('category')
        product.description = request.form.get('description')
        db.session.commit()

        # Update specifications
        specs = request.form.getlist('specifications[]')
        for spec in specs:
            key, value = spec.split(':')
            existing_spec = ProductSpecification.query.filter_by(product_id=product.id, key=key.strip()).first()
            if existing_spec:
                existing_spec.value = value.strip()
            else:
                new_spec = ProductSpecification(product_id=product.id, key=key.strip(), value=value.strip())
                db.session.add(new_spec)
        
        db.session.commit()
        flash("Product updated successfully!", "success")
        return redirect(url_for('product.get_product', product_id=product.id))

@product_bp.route('/products/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    ProductSpecification.query.filter_by(product_id=product.id).delete()  # Delete related specifications
    db.session.delete(product)
    db.session.commit()
    flash("Product deleted successfully!", "success")
    return redirect(url_for('product.get_products'))

@product_bp.route('/products/<int:product_id>/add-specifications', methods=['POST'])
def add_specifications(product_id):
    product = Product.query.get_or_404(product_id)

    # Get form data
    brand_id = request.form.get('brand')
    category_id = request.form.get('category')
    spec_keys = request.form.getlist('spec_key[]')
    spec_values = request.form.getlist('spec_value[]')

    # Save specifications
    for key, value in zip(spec_keys, spec_values):
        specification = ProductSpecification(
            product_id=product.id,
            key=key,
            value=value,
            brand_id=brand_id,
            category_id=category_id
        )
        db.session.add(specification)

    db.session.commit()
    flash('Specifications added successfully!', 'success')
    return redirect(url_for('product.get_product', product_id=product.id))