from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for, flash 
from models import db, Order, User, Car, OrderStatus, Product, Item, CategoryType
from functools import wraps
from sqlalchemy.orm import joinedload
import traceback
from .user_routes import admin_required
from datetime import datetime
from flask_mail import Message
from app import app, mail,requests
import os
from dotenv import load_dotenv
import time, base64

# Load environment variables from the .env file
load_dotenv()
# Access the API_KEY and API_SECRET from the environment
api_key = os.getenv("API_KEY")
api_secret = os.getenv("API_SECRET")

# Define global variables
access_token = None
token_expiry_time = None
order_bp = Blueprint('order', __name__)

# Helper function to ensure user is logged in
def user_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash("You must be logged in to access this feature.", "danger")

            return redirect(url_for('user.login'))
        return f(*args, **kwargs)
    return decorated_function

# Function to recalculate the total price for an order
def update_order_total(order):
    total = sum(item.total_price for item in order.items)
    order.total_price = total
    db.session.commit()

@order_bp.route('/orders', methods=['POST'])
def create_order():
    itemPrice = float(request.form.get('total_price'))
    car_id = request.form.get('car_id')  # Get car_id from the form
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 1))  # Default to 1 if not provided
    message = request.form.get('message')  # Message field from the form

    if 'user' in session:
        # Logged-in user scenario
        current_user = session['user']
        new_order = Order(user_id=current_user['id'], total_price=itemPrice, message=message)
    else:
        # Unauthenticated user scenario (using a contact form)
        guest_name = request.form.get('guest_name')
        guest_email = request.form.get('guest_email')
        guest_phone = request.form.get('guest_phone')

        new_order = Order(user_id=None, total_price=itemPrice, 
                          guest_name=guest_name, 
                          guest_email=guest_email, 
                          guest_phone=guest_phone,
                          message=message)

    # Add the order to the database
    db.session.add(new_order)
    db.session.flush()

    car_id = request.form.get('car_id')
    product_id = request.form.get('product_id')

    if car_id:
        total_item_price = itemPrice * quantity 
        new_item = Item(
            order_id=new_order.id,
            car_id=car_id,
            quantity=quantity,
            price=itemPrice,
            total_price= total_item_price,
        )
    elif product_id:
        total_item_price = itemPrice * quantity
        new_item = Item(
            order_id=new_order.id,
            product_id=product_id,
            quantity=quantity,
            price=itemPrice,
            total_price=total_item_price,
        )
    else:
        flash("No valid item provided for the order.", "error")
        return redirect(url_for('home.index'))

    # Add the item to the database
    db.session.add(new_item)
    db.session.commit()

    flash("Order created successfully! We will contact you shortly.", "success")

    # Send the order notification to the admin
    send_order_notification_to_admin(new_order, new_item)

    # Redirect to the appropriate page based on item type
    if car_id:
        return redirect(url_for('car.get_car', car_id=car_id))
    elif product_id:
        return redirect(url_for('product.get_product', product_id=product_id))

        
@order_bp.route('/orders', methods=['GET'])
@admin_required
def get_orders():
    current_user = session['user']
    # Check if the user is an admin
    if 'user' not in session or session['user'].get('role') != 'admin':
        flash("You must be an admin to access this feature.", "danger")
        return redirect(url_for('user.login'))
    
    # Fetch all orders, optionally filter by status (e.g., pending)
    orders = Order.query.filter(Order.order_status == 'Pending').all()
    all_orders = Order.query.all()
    pending_orders = Order.query.filter_by(order_status='pending').all()
    approved_orders = Order.query.filter_by(order_status='approved').all()
    rejected_orders = Order.query.filter_by(order_status='rejected').all()
    completed_orders = Order.query.filter_by(order_status='completed').all()

    orders_by_status = {
    'pending': Order.query.filter_by(order_status='pending').all(),
    'approved': Order.query.filter_by(order_status='approved').all(),
    'rejected': Order.query.filter_by(order_status='rejected').all(),
    'completed': Order.query.filter_by(order_status='completed').all(),
}

    # You might also want to include logic to differentiate between guest and logged-in user orders here
    guest_orders = [order for order in orders if order.user_id is None]
    user_orders = [order for order in orders if order.user_id is not None]

    return render_template('orders/orderList.html', 
                           guest_orders=guest_orders, 
                           user_orders=user_orders, 
                           user=current_user,                           
                           all_orders=all_orders,
                           pending_orders=pending_orders,
                           approved_orders=approved_orders,
                           rejected_orders=rejected_orders,
                           completed_orders=completed_orders, orders_by_status=orders_by_status)

@order_bp.route('/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    # Check if the user is logged in
    if 'user' not in session:
        flash("You must be logged in to access this feature.", "danger")
        return redirect(url_for('user.login'))

    current_user = session['user']  # Access session data only after the check

    # Fetch the order by its ID
    order = Order.query.get(order_id)

    if order is None:
        flash("Order not found.", "danger")
        return redirect(url_for('order.get_orders'))  # Redirect to the orders list if the order doesn't exist

    # Check if the logged-in user is the one who made the order or if the user is an admin
    if order.user_id != current_user['id'] and current_user['role'] != 'admin':
        flash("You do not have permission to view this order.", "danger")
        return redirect(url_for('home_bp.index'))  # Redirect to home page or appropriate route

    # Query the items associated with the order
    items = Item.query.filter_by(order_id=order_id).all()  # Fetch all items for the order

    return render_template('orders/orderDetail.html', order=order, user=current_user, items=items)

# Endpoint to display details of a specific order
@order_bp.route('/user/orders/<int:order_id>', methods=['GET'])
def order_details(order_id):
    if 'user' not in session:  # Check if the user is logged in
        flash("You must be logged in to view the order details.", "danger")
        return redirect(url_for('user.login'))

    current_user = session['user']
    order = Order.query.get_or_404(order_id)  # Fetch the order by ID

    # Check if the order belongs to the logged-in user
    if order.user_id != current_user['id']:
        flash("You do not have permission to view this order.", "danger")
        return redirect(url_for('user_orders'))

    # Fetch related items in the order
    items = Item.query.filter_by(order_id=order.id).all()

    return render_template('users/order_details.html', order=order, items=items, user=current_user,OrderStatus=OrderStatus)

# Delete an order
@order_bp.route('/orders/<int:order_id>', methods=['DELETE', 'POST'])
@admin_required
def delete_order(order_id):
    current_user = session['user']
    order = Order.query.get_or_404(order_id)
    
    # Delete associated items first
    for item in order.items:
        db.session.delete(item)
    
    db.session.delete(order)
    db.session.commit()
    flash("Order deleted successfully!", "success")


    return redirect(url_for('order.get_orders'))

def check_stock_availability(order):
    """
    Check if stock is sufficient for all products and cars in the order.
    Returns a tuple (is_stock_available, message).
    """
    for item in order.items:  # Assuming `order.items` contains all products/cars in the order
        product_or_car = None

        if item.product_id:  # For product
            product_or_car = Product.query.get(item.product_id)
        elif item.car_id:  # For car
            product_or_car = Car.query.get(item.car_id)

        if product_or_car:
            if item.quantity > product_or_car.stock:  # Check if stock is enough
                return False, f"Not enough stock for {product_or_car.name} (only {product_or_car.stock} left)."
    return True, "Stock is sufficient."

@order_bp.route('/orders/<int:order_id>', methods=['PUT'])
@admin_required
def update_order(order_id):
    current_user = session['user']
    order = Order.query.get_or_404(order_id)
    data = request.get_json()
    new_status = data.get('status')

    if new_status in [status.value for status in OrderStatus]:
        # Update stock levels and check sufficiency
        if new_status in ['approved', 'completed']:
            is_stock_available, message = check_stock_availability(order)

            if not is_stock_available:
                return jsonify({'success': False, 'error': message}), 400

            order.order_status = OrderStatus[new_status.upper()]

            # Update stock for each item in the order
            updated_items = []
            for item in order.items:
                product_or_car = None

                if item.product_id:
                    product_or_car = Product.query.get(item.product_id)
                elif item.car_id:
                    product_or_car = Car.query.get(item.car_id)

                if product_or_car:
                    if new_status == 'completed':
                        product_or_car.stock -= item.quantity
                        db.session.commit()

                    # Check if the stock is sufficient
                    stock_sufficient = product_or_car.stock >= item.quantity
                    updated_items.append({
                        'id': item.id,
                        'stock_sufficient': stock_sufficient
                    })

            db.session.commit()
            # Send email notification about the update
            send_order_update_notification_to_admin(order, 'updated', additional_info=f"Updated status to '{new_status}'.")
            return jsonify({'success': True, 'message': 'Order status updated successfully.', 'items': updated_items})

        else:
            order.order_status = OrderStatus[new_status.upper()]
            db.session.commit()
            return jsonify({'success': True, 'message': 'Order status updated successfully.'})

    else:
        return jsonify({'success': False, 'error': 'Invalid status provided.'}), 400

# Endpoint to display all orders for the logged-in user with status filtering
@order_bp.route('/user/orders', methods=['GET'])
@order_bp.route('/user/orders/<int:user_id>', methods=['GET'])
def user_orders(user_id=None):
    if 'user' not in session:  # Check if the user is logged in
        flash("You must be logged in to view your orders.", "danger")
        return redirect(url_for('user.login'))
    
    current_user = User.query.get(session['user']['id'])  # Fetch the actual logged-in user from the DB

    if user_id:  # If a user_id is provided, check for that specific user's orders
        target_user = User.query.get(user_id)

        if target_user is None:
            flash("User not found.", "danger")
            return redirect(url_for('user.index'))

        # Check if the logged-in user is allowed to view this user's orders
        if session['user']['role'] != 'admin' and current_user.id != target_user.id:
            flash("You are not authorized to view this user's orders.", "danger")
            return redirect(url_for('user.view_profile', user_id=current_user.id))
    else:
        target_user = current_user  # If no user_id is provided, show the logged-in user's orders

    # Fetch orders for the target user
    user_orders = Order.query.filter_by(user_id=target_user.id).all()

    # Fetch orders by status for filtering purposes
    pending_orders = Order.query.filter_by(user_id=target_user.id, order_status='pending').all()
    approved_orders = Order.query.filter_by(user_id=target_user.id, order_status='approved').all()
    rejected_orders = Order.query.filter_by(user_id=target_user.id, order_status='rejected').all()
    completed_orders = Order.query.filter_by(user_id=target_user.id, order_status='completed').all()

    # Organize orders by status
    orders_by_status = {
        'pending': pending_orders,
        'approved': approved_orders,
        'rejected': rejected_orders,
        'completed': completed_orders,
    }

    # Render template with filtered orders and categorized by status
    return render_template('users/user_orders.html',
                           user_orders=user_orders,
                           orders_by_status=orders_by_status,
                           user=target_user)


@order_bp.route('/order/edit/<int:order_id>', methods=['GET', 'POST'])
def edit_order(order_id):
    current_user = session['user']
    order = Order.query.get_or_404(order_id)

    # Permission check
    if order.user_id != current_user['id'] and current_user['role'] != 'admin':
        flash("You do not have permission to view this order.", "danger")
        return redirect(url_for('order.user_orders'))

    # Check if order is still editable (pending status)
    if order.order_status not in [OrderStatus.PENDING]:
        flash("This order is no longer editable.", "danger")
        return redirect(url_for('order.user_orders'))

    if request.method == 'GET':
        order_items = Item.query.filter_by(order_id=order_id).all()
        category_types = CategoryType
        cars = Car.query.all()  # All cars
        return render_template('users/order_edit.html', user=current_user, order=order, order_items=order_items, category_types=category_types, cars=cars)

    if request.method == 'POST':
        # Debug: Print initial total price before updating
        print(f"Initial order total price: {order.total_price}")

        # Handle quantity updates for existing items
        for item in order.items:
            new_quantity = request.form.get(f"quantity_{item.id}")
            if new_quantity:
                new_quantity = int(new_quantity)
                if new_quantity != item.quantity:  # Only update if quantity has changed
                    item.quantity = new_quantity
                    item.total_price = item.price * new_quantity  # Recalculate the total price of the item
                    print(f"Updated item {item.id} - New quantity: {new_quantity}, Total price: {item.total_price}")

        # Handle adding a new product or car to the order
        new_product_id = request.form.get("product")
        new_car_id = request.form.get("car")

        if new_product_id:
            new_product = Product.query.get(new_product_id)
            if new_product:
                new_item = Item(order_id=order.id, product_id=new_product.id, price=new_product.price, total_price=new_product.price)
                db.session.add(new_item)
                print(f"Added new product item - Product ID: {new_product.id}, Price: {new_product.price}, Total price: {new_item.total_price}")

        if new_car_id:
            new_car = Car.query.get(new_car_id)
            if new_car:
                new_item = Item(order_id=order.id, car_id=new_car.id, price=new_car.price, total_price=new_car.price)
                db.session.add(new_item)
                print(f"Added new car item - Car ID: {new_car.id}, Price: {new_car.price}, Total price: {new_item.total_price}")

        # Recalculate total price of the order after adding new items and updating existing items
        update_order_total(order)

        # Debug: Print final total price after updating
        print(f"Updated order total price after adding items: {order.total_price}")

        # Commit the session after adding new items and recalculating the order total
        db.session.commit()
        
        flash("Order updated successfully!", "success")
        send_order_update_notification_to_admin(order, 'updated', additional_info="Order items updated.")
        return redirect(url_for('order.user_orders'))

# New endpoint for updating products by category
@order_bp.route('/order/update_products_by_category', methods=['POST'])
def update_products_by_category():
    category_id = request.form['category_id']
    products = Product.query.filter_by(category=category_id).all()
    product_data = [{'id': product.id, 'name': product.name} for product in products]

    return jsonify({'products': product_data})
    
# Route to remove an item from the order
@order_bp.route('/order/remove_item/<int:item_id>', methods=['POST'])
def remove_item(item_id):
    item = Item.query.get_or_404(item_id)
    order = item.order

    if item:
        db.session.delete(item)
        db.session.commit()
        flash("Item removed successfully!", "success")
    else:
        flash("Item not found.", "danger")

    # Recalculate total price after item removal
    update_order_total(order)

    send_order_update_notification_to_admin(order, 'item_removed', additional_info=f"Item ID {item.id} removed from the order.")

    return redirect(url_for('order.edit_order', order_id=order.id))

def send_order_notification_to_admin(order, item):
    """
    Function to send a notification email to the admin after an order is placed.
    """
    # Prepare the email
    admin_email = app.config['MAIL_USERNAME']  # Admin email from config
    subject = f"New Order Received: #{order.id}"

    # Construct the body of the message based on the type of order
    if order.user_id:  # Logged-in user
        user_info = f"User ID: {order.user_id}\n"
        user_info += f"User Name: {order.user.username}\n"  # Fetching username from related User object
    else:  # Guest user
        user_info = f"Guest Name: {order.guest_name}\nGuest Email: {order.guest_email}\nGuest Phone: {order.guest_phone}\n"

    item_details = f"Item ID: {item.car_id if item.car_id else item.product_id}\n"
    item_details += f"Quantity: {item.quantity}\n"
    item_details += f"Price per Item: ${item.price}\n"
    item_details += f"Total Price: ${item.total_price}\n"

    # Check if it's a car or product order
    if item.car_id:
        item_type = "Car Order"
    else:
        item_type = "Product Order"

    email_body = f"""
    New Order Details:

    Order ID: {order.id}
    {user_info}
    Item Type: {item_type}
    {item_details}

    Message from Customer: {order.message}
    """

    # Send the email
    msg = Message(subject, recipients=[admin_email])
    msg.body = email_body
    mail.send(msg)

def send_order_update_notification_to_admin(order, action_type, additional_info=None):
    """
    Generic function to send email notifications to the admin about changes to an order.
    
    :param order: The Order object that was changed.
    :param action_type: A string describing the type of action (e.g., 'deleted', 'updated', 'item_removed').
    :param additional_info: Any additional information to include in the email (e.g., updated items, status, etc.)
    """
    admin_email = app.config['MAIL_USERNAME']  # Admin email from config
    subject = f"Order #{order.id} {action_type.capitalize()}"

    # Construct the email body based on the action type
    email_body = f"""
    Order #{order.id} has been {action_type}.
    
    Order Details:
    Customer: {order.guest_name if order.user_id is None else 'User ID: ' + str(order.user_id)}
    Status: {order.order_status.name}
    Total Price: ${order.total_price}
    
    {additional_info if additional_info else ''}
    """

    # Send the email
    msg = Message(subject, recipients=[admin_email])
    msg.body = email_body
    mail.send(msg)

def get_mpesa_token():
    global access_token, token_expiry_time

    # If the token is not set or has expired, request a new one
    if not access_token or time.time() > token_expiry_time:
        api_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
        
        # Get the API key and secret from environment variables
        api_key = os.getenv("API_KEY")
        api_secret = os.getenv("API_SECRET")
        
        # Base64 encode the Consumer Key and Secret
        credentials = f"{api_key}:{api_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode('utf-8')
        
        headers = {
            "Authorization": f"Basic {encoded_credentials}"
        }
        
        # Make the GET request to fetch the access token
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            access_token = response.json()['access_token']
            # Set the expiration time (access token typically expires in 1 hour)
            token_expiry_time = time.time() + 3600
            print(f"New token obtained: {access_token}")
        else:
            raise Exception("Failed to obtain access token")

    return access_token


def initiate_payment(phone_number, amount):
    # Get the access token
    token = get_mpesa_token()

    # Endpoint for Lipa Na M-Pesa STK Push
    lipa_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    
    # Get necessary environment variables
    shortcode = os.getenv("LIPA_NA_MPESA_SHORTCODE")
    shortcode_secret = os.getenv("LIPA_NA_MPESA_SHORTCODE_SECRET")
    callback_url = os.getenv("CALLBACK_URL")
    # Generate timestamp
    timestamp = time.strftime("%Y%m%d%H%M%S", time.gmtime())

    # Generate password (shortcode + secret)
    password = base64.b64encode(f"{shortcode}{shortcode_secret}".encode('utf-8')).decode('utf-8')

       # Prepare payload
    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",  # Payment type (could be Paybill or Buy goods)
        "Amount": amount,
        "PartyA": phone_number,  # Customer's phone number (the one making the payment)
        "PartyB": shortcode,  # Your shortcode (merchant)
        "PhoneNumber": phone_number,  # Customer's phone number (for STK Push)
        "CallBackURL": callback_url,  # The callback URL for response
        "AccountReference": "Test1234",  # Reference for the transaction
        "TransactionDesc": "Payment for goods",  # Description of the transaction
    }

    # Set headers for authorization
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Make the POST request to initiate the STK push
    response = requests.post(lipa_url, json=payload, headers=headers)
    
    # Return response from Safaricom API
    return response.json()

@order_bp.route('/order/pay/<int:order_id>', methods=['POST'])
def pay(order_id):
    phone_number = request.form.get('phone_number')
    amount = request.form.get('amount')

        # Convert amount to integer by removing decimals
    try:
        amount = int(float(amount))  # This ensures that the amount is an integer
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid amount format"}), 400
    
    print(phone_number)
    print(amount)
    
    # Call initiate_payment to process the payment
    payment_response = initiate_payment(phone_number, amount)
    
    # Handle the response from the payment API as needed
    return jsonify(payment_response)

