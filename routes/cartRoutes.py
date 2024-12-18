from flask import Blueprint, jsonify, request, session, flash, redirect, render_template, url_for, session
from app import db
from models import  Car, Product, Cart, User,Image

cart_bp = Blueprint('cart', __name__)

@cart_bp.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    user_id = session['user']['id'] if 'user' in session else None  # Check if the user is logged in
    item_id = request.form['item_id']
    target_type = request.form['target_type']  # 'car' or 'product'
    quantity = int(request.form.get('quantity', 1))  # Default quantity is 1 if not specified
    
    if user_id is None:
        flash("You need to be logged in to add items to the cart.", "error")
        return redirect(url_for('user.login'))  # Redirect to login if user is not logged in
    
    # Check if the item is a car or product and create the cart entry
    if target_type == 'car':
        car = Car.query.get(item_id)
        if not car:
            flash("Car not found.", "error")
            return jsonify({"status": "error", "message": "Car not found."})
    
        # Check if the car already exists in the cart
        existing_item = Cart.query.filter_by(user_id=user_id, car_id=item_id).first()
        if existing_item:
            existing_item.quantity += quantity  # Update quantity if the item already exists in the cart
            db.session.commit()
            return jsonify({"status": "success", "message": "Car is already in the cart. Quantity updated."})

        # Add to cart for the car
        cart_item = Cart(user_id=user_id, car_id=item_id, quantity=quantity, target_type=target_type)

    elif target_type == 'product':
        product = Product.query.get(item_id)
        if not product:
            flash("Product not found.", "error")
            return redirect(url_for('home_bp.index'))

        # Check if the product already exists in the cart
        existing_item = Cart.query.filter_by(user_id=user_id, product_id=item_id).first()
        if existing_item:
            existing_item.quantity += quantity  # Update quantity if the item already exists in the cart
            db.session.commit()
            return jsonify({"status": "success", "message": "Product is already in the cart. Quantity updated."})

        # Add to cart for the product
        cart_item = Cart(user_id=user_id, product_id=item_id, quantity=quantity, target_type=target_type)
        
    else:
        flash("Invalid item type.", "error")
        return redirect(url_for('home_bp.index'))

    db.session.add(cart_item)
    db.session.commit()
    return jsonify({"status": "success", "message": "Item added to the cart."})

@cart_bp.route('/view_cart', methods=['GET'])
def view_cart():
    user_id = session['user']['id'] if 'user' in session else None  # Check if the user is logged in

    if user_id is None:
        flash("You need to be logged in to add items to the cart.", "error")
        return redirect(url_for('user.login'))  # Redirect to login if user is not logged in
    

    cart_items = Cart.query.filter_by(user_id=user_id).all()
    cart_data = []
    
    for item in cart_items:
        cart_item = {}
        if item.product:
            cart_item['type'] = 'product'
            cart_item['name'] = item.product.name
            cart_item['price'] = item.product.price
            cart_item['quantity'] = item.quantity
            cart_item['total'] = item.quantity * item.product.price
            cart_item['id'] = item.product.id
            # Get the first image for the product
            if item.product.product_images:
                cart_item['image'] = item.product.product_images[0].image_path
            else:
                cart_item['image'] = '/static/img/default_image_path.jpg'  # Path to the default image

        elif item.car:
            cart_item['type'] = 'car'
            cart_item['name'] = item.car.model
            cart_item['price'] = item.car.price
            cart_item['quantity'] = item.quantity
            cart_item['total'] = item.quantity * item.car.price
            cart_item['id'] = item.car.id
            # Get the first image for the car
            if item.product.product_images:
                cart_item['image'] = item.car.car_images[0].image_path
            else:
                cart_item['image'] = '/static/img/default_image_path.jpg'  # Path to the default image


        cart_data.append(cart_item)
    return jsonify(cart_data)

@cart_bp.route('/remove_cart_item', methods=['POST'])
def remove_cart_item():
    user_id = session['user']['id'] if 'user' in session else None  # Get user ID from session

    if user_id is None:
        return jsonify({"status": "error", "message": "You need to be logged in to remove items from the cart."}), 401
    
    item_data = request.get_json()
    item_id = item_data.get('item_id')
    
    # Check if the item exists in the user's cart
    cart_item = Cart.query.filter_by(user_id=user_id, id=item_id).first()
    if cart_item:
        db.session.delete(cart_item)  # Remove the item from the cart
        db.session.commit()
        return jsonify({"status": "success", "message": "Item removed from the cart."})
    else:
        return jsonify({"status": "error", "message": "Item not found in the cart."}), 404

