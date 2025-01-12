from flask import Blueprint, jsonify, request, session, flash, redirect, render_template, url_for, session
from app import db,app,mail
from flask_mail import Message
from models import  Car, Product, Cart, Order, Item


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
                cart_item['image'] = url_for('uploaded_file', folder='products', filename=item.product.product_images[0].image_path)
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
            if item.car.car_images:
                cart_item['image'] = url_for('uploaded_file', folder='cars', filename=item.car.car_images[0].image_path) 
            else:
                cart_item['image'] = '/static/img/default_image_path.jpg'  # Path to the default image


        cart_data.append(cart_item)
    return jsonify(cart_data)


@cart_bp.route('/remove_cart_item', methods=['POST'])
def remove_cart_item():
    user_id = session['user']['id'] if 'user' in session else None  # Get user ID from session
    data = request.get_json()  # Parse JSON data from the request
    item_id = data.get('item_id')  # Get item_id from the JSON body
    target_type = data.get('target_type')  # 'car' or 'product'

    print(f"Received data: {data}")
    print(f"User ID: {user_id}, Target Type: {target_type}, Item ID: {item_id}")

    if user_id is None:
        return jsonify({"status": "error", "message": "You need to be logged in to remove items from the cart."}), 401

    if target_type not in ['product', 'car']:
        return jsonify({"status": "error", "message": "Invalid target type. Allowed values are 'product' and 'car'."}), 400

    # Convert item_id to integer (if it's a string)
    try:
        item_id = int(item_id)
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid item_id."}), 400

    print(f"Looking for item_id {item_id} for user_id {user_id} with target_type {target_type}")

    # Fetch the cart item based on user_id, target_type, and the correct id (car_id or product_id)
    if target_type == 'car':
        cart_item = Cart.query.filter_by(user_id=user_id, car_id=item_id).first()
    elif target_type == 'product':
        cart_item = Cart.query.filter_by(user_id=user_id, product_id=item_id).first()

    if cart_item:
        print(f"Found cart_item: {cart_item}")
        db.session.delete(cart_item)  # Remove the item from the cart
        db.session.commit()
        return jsonify({"status": "success", "message": "Item removed from the cart."})
    else:
        print("Item not found in the cart.")
        return jsonify({"status": "error", "message": "Item not found in the cart."}), 404


@cart_bp.route('/clear_cart', methods=['POST'])
def clear_cart():
    # Ensure the user is logged in
    user_id = session.get('user', {}).get('id')
    if not user_id:
        return jsonify({"status": "error", "message": "You need to be logged in to clear your cart."}), 401

    # Clear the user's cart from the database
    Cart.query.filter_by(user_id=user_id).delete()
    db.session.commit()

    # Optionally, clear the cart from session data if using session storage
    # session.pop('cart', None)

    return jsonify({"status": "success", "message": "Your cart has been cleared."})


@cart_bp.route('/checkout_cart', methods=['POST'])
def checkout_cart():
    user_id = session.get('user', {}).get('id')
    data = request.get_json()
    cart_items = data.get('items', [])
    

    if not cart_items:
        return jsonify({"status": "error", "message": "Your cart is empty."}), 400

    # Calculate the total price of the cart
    total_price = 0
    for item in cart_items:
        item_price = float(item['price'])  # Price from the cart
        quantity = item['quantity']
        total_price += item_price * quantity

        # Handle item type (product or car)
        if item['type'] == 'product':
            product = Product.query.get(item['id'])
            if not product:
                return jsonify({"status": "error", "message": "Invalid product item."}), 400
        elif item['type'] == 'car':
            car = Car.query.get(item['id'])
            if not car:
                return jsonify({"status": "error", "message": "Invalid car item."}), 400
        else:
            return jsonify({"status": "error", "message": "Invalid cart item."}), 400

    # Create a new order
    if 'user' in session:
        current_user = session['user']
        new_order = Order(user_id=user_id, total_price=total_price, message=data.get('message'))
        print(f"Created new order with ID: {new_order.id}")  # Debugging: print order ID
        user_name = current_user.get('name')

    # Add the order to the database
    db.session.add(new_order)
    db.session.flush()  # Get the order ID before creating items
   
    # Add each item (product or car) to the order
    for cart_item in cart_items:
        total_item_price = float(cart_item['price']) * cart_item['quantity']
        
        if cart_item['type'] == 'car':
            new_item = Item(
                order_id=new_order.id,
                car_id=cart_item['id'],  # Use 'id' directly for car
                quantity=cart_item['quantity'],
                price=cart_item['price'],
                total_price=total_item_price
            )
        elif cart_item['type'] == 'product':
            new_item = Item(
                order_id=new_order.id,
                product_id=cart_item['id'],  # Use 'id' directly for product
                quantity=cart_item['quantity'],
                price=cart_item['price'],
                total_price=total_item_price
            )
        else:
            flash("Invalid cart item.", "error")
            return redirect(url_for('cart_bp.view_cart'))

        # Add the item to the database
        db.session.add(new_item)
        
    # Commit all changes (create the order and all items)
    db.session.commit()

    # Clear the cart after the order is placed
    Cart.query.filter_by(user_id=user_id).delete()  # Clear cart items from the database
    db.session.commit()  # Commit changes to database

    # Send the order notification to the admin
    send_checkout_notification_to_admin(new_order, cart_items, user_name)
    
    # Return a success response with order ID
    return jsonify({
        "status": "success",
        "message": "Your order has been placed successfully!",
        "order_id": new_order.id  # Send order ID for use in the frontend
    })

def send_checkout_notification_to_admin(order, cart_items, user_name=None):
    """
    Sends an email notification to the admin when an order is placed through the checkout process.
    
    :param order: The Order object that was created.
    :param cart_items: The items in the cart.
    :param user_name: The name of the user placing the order, or None if it's a guest.
    """
    admin_email = app.config['MAIL_USERNAME']  # Admin email from config
    subject = f"New Order #{order.id} Placed"

    # Prepare email body with order and item details
    email_body = f"""
    A new order has been placed:
    
    Order ID: {order.id}
    Customer: {user_name if user_name else 'Guest'}
    Total Price: ${order.total_price}
    
    Items:
    """

    # Add item details to the email
    for item in cart_items:
        item_name = item.get('name', 'Unknown')  # Assuming each cart item has a 'name' field
        item_price = item.get('price', 0)
        item_quantity = item.get('quantity', 0)
        total_item_price = item_price * item_quantity
        email_body += f"\n- {item_name} (x{item_quantity}) - ${total_item_price:.2f}"

    # Send the email
    msg = Message(subject, recipients=[admin_email])
    msg.body = email_body
    mail.send(msg)