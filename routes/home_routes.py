from flask import Blueprint, render_template, session, request, flash, redirect, url_for
from models import Car, Category, Like,  Product
from flask_sqlalchemy import SQLAlchemy
from app import db

home_bp = Blueprint('home_bp', __name__)

@home_bp.route('/')
def index():
    current_user = session.get('user')  # Fetch user from session
    categories = Category.query.all()

    # Get filter parameters
    selected_year = request.args.get('year', '')
    selected_price = request.args.get('price', '')
    selected_mileage = request.args.get('mileage', '')
    selected_model = request.args.get('model', '')
    selected_category = request.args.get('category', '')
    selected_brand = request.args.get('brand', '')

    # Pagination setup
    page = request.args.get('page', 1, type=int)
    per_page = 20  # Only show 20 cars per page

    # Start with base query
    query = Car.query.order_by(Car.added_at.desc())

    # Apply filters
    if selected_year:
        query = query.filter(Car.year == selected_year)
    if selected_price:
        try:
            selected_price = float(selected_price)
            query = query.filter(Car.price <= selected_price)
        except ValueError:
            pass
    if selected_mileage:
        try:
            selected_mileage = int(selected_mileage)
            query = query.filter(Car.mileage <= selected_mileage)
        except ValueError:
            pass
    if selected_model:
        query = query.filter(Car.model.ilike(f'%{selected_model}%'))
    if selected_category:
        query = query.filter(Car.category_id == int(selected_category))
    if selected_brand:
        query = query.filter(Car.brand.ilike(f'%{selected_brand}%'))

    # Get filtered cars with pagination
    cars_paginated = query.paginate(page=page, per_page=per_page)

    liked_cars = []
    if current_user:
        user_id = current_user.get('id')
        liked_cars = [like.target_id for like in Like.query.filter_by(user_id=user_id, target_type='car').all()]

    return render_template(
        'index.html',
        cars=cars_paginated.items,
        pagination=cars_paginated,
        user=current_user,
        liked_cars=liked_cars,
        categories=categories,
        selected_year=selected_year,
        selected_price=selected_price,
        selected_mileage=selected_mileage,
        selected_model=selected_model,
        selected_category=selected_category,
        selected_brand=selected_brand
    )

@home_bp.route('/cars')
def cars():
    current_user = session.get('user')  # Fetch user from session
    cars = Car.query.all()
    return render_template('cars.html', cars=cars, user=current_user)

@home_bp.route('/carParts')
def carParts():
    current_user = session.get('user')  # Fetch user from session
    products = Product.query.filter_by(category='Car_Parts').all()
    return render_template('carParts.html',  user=current_user, products=products)

@home_bp.route('/tools')
def tools():
    current_user = session.get('user')  # Fetch user from session
    products = Product.query.filter_by(category='Tools_and_Machinery').all()
    return render_template('tools.html',  user=current_user,  products=products)


@home_bp.route('/househldItems')
def househldItems():
    current_user = session.get('user')  # Fetch user from session
    products = Product.query.filter_by(category='Household_Items').all()
    return render_template('households.html',  user=current_user, products=products)

@home_bp.route('/computers')
def computers():
    current_user = session.get('user')  # Fetch user from session
    products = Product.query.filter_by(category='Computers').all()
    return render_template('computers.html',  user=current_user, products=products )