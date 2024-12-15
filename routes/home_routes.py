from flask import Blueprint, render_template, session, request, flash, redirect, url_for, jsonify, make_response
from models import Car, Category, Like,  Product, Brand, Image
from flask_sqlalchemy import SQLAlchemy
from app import db

home_bp = Blueprint('home_bp', __name__)

@home_bp.route('/')
def index():
    current_user = session.get('user')  # Fetch user from session
    categories = Category.query.all()
    brands = Brand.query.all()

    # Limited queries for products
    cars = Car.query.order_by(Car.added_at.desc()).limit(8).all()
    computers = Product.query.filter_by(category='Computers').order_by(Product.added_at.desc()).limit(8).all()
    tools = Product.query.filter_by(category='Tools_and_Machinery').order_by(Product.added_at.desc()).limit(8).all()
    household = Product.query.filter_by(category='Household_Items').order_by(Product.added_at.desc()).limit(8).all()
    carParts = Product.query.filter_by(category='Car_Parts').order_by(Product.added_at.desc()).limit(8).all()

    liked_items = {}
    if current_user:
        user_id = current_user.get('id')
        liked_items['cars'] = [like.car_id for like in Like.query.filter_by(user_id=user_id, target_type='car').all()]
        liked_items['products'] = [like.target_id for like in Like.query.filter_by(user_id=user_id, target_type='product').all()]

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
        carParts= carParts
    )

# Additional route to handle AJAX pagination requests
@home_bp.route('/paginate/<category>')
def paginate_category(category):
    page = request.args.get('page', 1, type=int)
    
    category_queries = {
        'cars': Car.query.order_by(Car.added_at.desc()),
        'computers': Product.query.filter_by(category='Computers').order_by(Product.added_at.desc()),
        'tools': Product.query.filter_by(category='Tools_and_Machinery').order_by(Product.added_at.desc()),
        'household': Product.query.filter_by(category='Household_Items').order_by(Product.added_at.desc()),
    }
    
    if category not in category_queries:
        return jsonify({'error': 'Invalid category'}), 400
    
    paginated_items = category_queries[category].paginate(page=page, per_page=8)
    return render_template(f'partials/{category}_list.html', paginated_items=paginated_items)






@home_bp.route('/cars', methods=['GET'])
def cars():
    current_user = session.get('user')
    
    # Get the filter parameters from the URL query string
    year = request.args.get('year')
    transmission = request.args.get('transmission')
    price_min = request.args.get('price_min')
    price_max = request.args.get('price_max')
    brand = request.args.get('brand')

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

    return render_template('cars.html', 
                           cars=cars, 
                           user=current_user, 
                           years=[year[0] for year in years], 
                           brands=brands)


@home_bp.route('/carParts')
def carParts():
    current_user = session.get('user') 
    products = Product.query.filter_by(category='Car_Parts').all()
    return render_template('carParts.html',  user=current_user, products=products)

@home_bp.route('/tools')
def tools():
    current_user = session.get('user')  
    products = Product.query.filter_by(category='Tools_and_Machinery').all()
    return render_template('tools.html',  user=current_user,  products=products)


@home_bp.route('/househldItems')
def househldItems():
    current_user = session.get('user')  
    products = Product.query.filter_by(category='Household_Items').all()
    return render_template('households.html',  user=current_user, products=products)

@home_bp.route('/computers')
def computers():
    current_user = session.get('user')  
    products = Product.query.filter_by(category='Computers').all()
    return render_template('computers.html',  user=current_user, products=products )