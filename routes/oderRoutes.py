from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for, flash
from models import db, Order, User, Car, OrderStatus, Product, Item
from functools import wraps
from sqlalchemy.orm import joinedload
import traceback
from .user_routes import admin_required

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

    # Redirect to the appropriate page based on item type
    if car_id:
        return redirect(url_for('car.get_car', car_id=car_id))
    elif product_id:
        return redirect(url_for('product.get_product', product_id=product_id))
   

@order_bp.route('/orders', methods=['GET'])
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
@admin_required
def get_order(order_id):
    if 'user' not in session:
        flash("You must be logged in to access this feature.", "danger")
        return redirect(url_for('user.login'))

    current_user = session['user']  # Access session data only after the check
    order = Order.query.get(order_id)  # Fetch a single order by its ID

    if order is None:
        flash("Order not found.", "danger")
        return redirect(url_for('order.get_orders'))  # Redirect to the orders list if the order doesn't exist

    # Query the items associated with the order
    items = Item.query.filter_by(order_id=order_id).all()  # Fetch all items for the order

    return render_template('orders/orderDetail.html', order=order, user=current_user, items=items)


# Update an order (e.g., change status)
@order_bp.route('/orders/<int:order_id>', methods=['PUT'])
@user_required
def update_order(order_id):
    current_user = session['user']
    order = Order.query.get_or_404(order_id)
    data = request.get_json()  # Get JSON data from the request
    new_status = data.get('status')

    if new_status in [status.value for status in OrderStatus]:
        order.order_status = OrderStatus[new_status.upper()]
        db.session.commit()
        flash("Oder status Changes successfully.", "success")
        return jsonify({'success': True, 'message': 'Order status updated successfully.'})
    else:
        return jsonify({'success': False, 'error': 'Invalid status provided.'}), 400


# Delete an order
@order_bp.route('/orders/<int:order_id>', methods=['DELETE'])
@user_required
def delete_order(order_id):
    current_user = session['user']
    order = Order.query.get_or_404(order_id)

    if order.user_id != current_user['id']:
        flash("You are not authorized to delete this order.", "danger")
        return redirect(url_for('order.get_orders'))

    db.session.delete(order)
    db.session.commit()
    flash("Order deleted successfully!", "success")
    return jsonify({'success': True}), 204
