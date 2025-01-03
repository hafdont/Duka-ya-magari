from flask import Blueprint, render_template, session, request, flash, redirect, url_for, jsonify
from models import Car, Category, Like,  Product, Brand, Image, CategoryType, ProductSpecification
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Message 
from app import db, app, mail

home_bp = Blueprint('home_bp', __name__)

@home_bp.route('/')
def index():
    current_user = session.get('user')  # Fetch user from session
    categories = Category.query.all()
    brands = Brand.query.all()

    # Limited queries for products    TOOLS_MACHINERY = 'Tools_and_Machinery'
    cars = Car.query.order_by(Car.added_at.desc()).limit(8).all()
    computers = Product.query.filter_by(category=CategoryType.COMPUTERS).order_by(Product.added_at.desc()).limit(8).all()
    tools = Product.query.filter_by(category=CategoryType.TOOLS_MACHINERY).order_by(Product.added_at.desc()).limit(8).all()
    household = Product.query.filter_by(category=CategoryType.HOUSEHOLD_ITEMS).order_by(Product.added_at.desc()).limit(8).all()
    carParts = Product.query.filter_by(category=CategoryType.CAR_PARTS).order_by(Product.added_at.desc()).limit(8).all()
    print(tools,cars)

    liked_items = {}
    if current_user:
        user_id = current_user.get('id')
        liked_items['products'] = [like.product_id for like in Like.query.filter_by(user_id=user_id, target_type='product').all()]

    return render_template(
        'index.html',
        cars=cars,
        computers=computers,
        tools=tools,
        household=household,
        liked_items=liked_items,
        user=current_user,
        categories=categories,
        brands=brands,
        carParts= carParts,

    )


@home_bp.route('/home_cars', methods=['GET'])
def cars():
    current_user = session.get('user')
    
    # Get the filter parameters from the URL query string
    year = request.args.get('year')
    transmission = request.args.get('transmission')
    price_min = request.args.get('price_min')
    price_max = request.args.get('price_max')
    brand = request.args.get('brand')

    liked_items = {}
    if current_user:
        user_id = current_user.get('id')
        liked_items['cars'] = [like.car_id for like in Like.query.filter_by(user_id=user_id, target_type='car').all()]
        liked_items['products'] = [like.product_id for like in Like.query.filter_by(user_id=user_id, target_type='product').all()]

    # Build the query based on the filters
    query = Car.query

    if year:
        query = query.filter(Car.year == year)
    
    if transmission:
        query = query.filter(Car.transmission == transmission)
    
    if price_min:
        query = query.filter(Car.price >= price_min)
    
    if price_max:
        query = query.filter(Car.price <= price_max)
    
    if brand:
        query = query.filter(Car.brand_id == brand)
        
    
    # Execute the query to get the filtered cars
    cars = query.all()

    # Get distinct years and brands for the filter options
    years = db.session.query(Car.year).distinct().all()
    brands = Brand.query.filter_by(category='Cars').all()
    print(tools)

    return render_template('cars.html', 
                           cars=cars, 
                           user=current_user, 
                           years=[year[0] for year in years], 
                           brands=brands, 
                           liked_items=liked_items)

@home_bp.route('/carParts')
def carParts():
    current_user = session.get('user') 
    
    # Get the search query (if any)
    search_query = request.args.get('search', '')
    
    # Get the category filter (if any)
    category_filter = request.args.get('category', '')
    
    # Get price filters (if any)
    price_min = request.args.get('price_min', type=float)
    price_max = request.args.get('price_max', type=float)
    
    # Get brand filter (if any)
    brand_filter = request.args.get('brand', '')
    
    
    # Build the base query for products and brands
    query = Product.query.filter(Product.category == 'Car_Parts') 
    
    # Apply the search filter (search by name only)
    if search_query:
        query = query.filter(Product.name.ilike(f"%{search_query}%"))
    
    # Apply the category filter
    if category_filter:
        query = query.filter(Product.category == category_filter)
    
    # Apply price filters (min and max)
    if price_min is not None:
        query = query.filter(Product.price >= price_min)
    if price_max is not None:
        query = query.filter(Product.price <= price_max)
    
    # Apply the brand filter (if any)
    if brand_filter:
        query = query.filter(Product.brand_id == brand_filter)
    
    # Fetch products based on the filtered query
    products = query.all()

    # Fetch categories related to 'Car_Parts' to display in the filter
    categories = Category.query.filter_by(category_type='Car_Parts').all()
    
    # Fetch distinct brands that are associated with the products in this category
    brand_ids = {product.brand_id for product in products if product.brand_id is not None}
    brands = Brand.query.filter(Brand.id.in_(brand_ids)).all()  # Get the brands associated with these products


    liked_items = {}
    if current_user:
        user_id = current_user.get('id')
        liked_items['products'] = [like.product_id for like in Like.query.filter_by(user_id=user_id, target_type='product').all()]
    
    return render_template('carParts.html', 
                           user=current_user, 
                           products=products, 
                           liked_items=liked_items, 
                           categories=categories, 
                           brands=brands)

@home_bp.route('/tools')
def tools():
    current_user = session.get('user')  
    products = Product.query.filter_by(category=CategoryType.TOOLS_MACHINERY).all()
    print(products)
    return render_template('tools.html',  user=current_user,  products=products)


@home_bp.route('/househldItems')
def househldItems():
    current_user = session.get('user')  
    
    # Get the search query (if any)
    search_query = request.args.get('search', '')
    
    # Get the category filter (if any)
    category_filter = request.args.get('category', '')
    
    # Get price filters (if any)
    price_min = request.args.get('price_min', type=float)
    price_max = request.args.get('price_max', type=float)
    
    # Get brand filter (if any)
    brand_filter = request.args.get('brand', '')
    
    # Build the base query for products
    query = Product.query.filter(Product.category == 'Household_Items')

    # Apply the search filter (search by name only)
    if search_query:
        query = query.filter(Product.name.ilike(f"%{search_query}%"))
    
    # Apply the category filter (if any)
    if category_filter:
        query = query.filter(Product.category == category_filter)
    
    # Apply price filters (min and max)
    if price_min is not None:
        query = query.filter(Product.price >= price_min)
    if price_max is not None:
        query = query.filter(Product.price <= price_max)
    
    # Apply the brand filter (if any)
    if brand_filter:
        query = query.filter(Product.brand_id == brand_filter)
    
    # Fetch products based on the filtered query
    products = query.all()

    # Fetch distinct brands that are associated with the products in this category
    brand_ids = {product.brand_id for product in products if product.brand_id is not None}
    brands = Brand.query.filter(Brand.id.in_(brand_ids)).all()  # Get the brands associated with these products

    # Fetch categories related to 'Household_Items' to display in the filter
    categories = Category.query.filter_by(category_type='Household_Items').all()

    print(brands)


    # Check if the user is logged in and fetch liked items (products liked by the user)
    liked_items = {}
    if current_user:
        user_id = current_user.get('id')
        liked_items['products'] = [like.product_id for like in Like.query.filter_by(user_id=user_id, target_type='product').all()]

    # Render the template with the filtered products, categories, brands, and liked items
    return render_template('households.html', 
                           user=current_user, 
                           products=products, 
                           liked_items=liked_items, 
                           categories=categories, 
                           brands=brands)

@home_bp.route('/computers')
def computers():
    current_user = session.get('user')
    
    
    # Start with filtering products by the 'Computers' category
    query = Product.query.filter(Product.category == 'Computers')
    
    # Handle Search
    search_query = request.args.get('search', '')
    if search_query:
        query = query.filter(Product.name.ilike(f'%{search_query}%'))

    # Handle Category Filter (if specified)
    category_filter = request.args.get('category', '')
    if category_filter:
        query = query.filter(Product.category == category_filter)

    # Handle Price Range Filter
    price_min = request.args.get('price_min', '')
    if price_min:
        query = query.filter(Product.price >= float(price_min))
    
    price_max = request.args.get('price_max', '')
    if price_max:
        query = query.filter(Product.price <= float(price_max))

    # Handle Brand Filter
    brand_filter = request.args.get('brand', '')
    if brand_filter:
        query = query.filter(Product.brand_id == brand_filter)

    # Fetch the filtered products
    products = query.all()
    
    # Fetch categories to display in the filter
    categories = Category.query.filter_by(category_type='Computers').all()
    
    # Fetch distinct brands that are associated with the products in this category
    brand_ids = {product.brand_id for product in products if product.brand_id is not None}
    brands = Brand.query.filter(Brand.id.in_(brand_ids)).all()  # Get the brands associated with these products

    return render_template('computers.html', user=current_user, products=products, categories=categories, brands=brands)

@home_bp.route('/about')
def about():
    current_user = session.get('user')  
    return render_template('about.html',  user=current_user )

@home_bp.route('/send_email', methods=['POST'])
def send_email():
    # Extract form data
    name = request.form.get('name')
    email = request.form.get('email')
    subject = request.form.get('subject')
    message = request.form.get('message')

    # Validate form data
    if not all([name, email, subject, message]):
        return jsonify({"message": "All fields are required"}), 400

    try:
        # Create the email message
        msg = Message(
            subject=subject,
            recipients=[app.config['MAIL_USERNAME']],  # The recipient email
            sender=email,  # User's email as sender
            html=render_template(
                'email/email_template.html',  # Template path
                subject=subject,
                name=name,
                email=email,
                message=message
            )
        )

        # Send the email
        mail.send(msg)
        return jsonify({"message": "Email sent successfully!"}), 200
    except Exception as e:
        app.logger.error(f"Error sending email: {e}")
        return jsonify({"message": "Failed to send email"}), 500
