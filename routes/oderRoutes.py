from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for, flash
from models import db, Order, User, Car, order_car, OrderStatus
from functools import wraps
from sqlalchemy.orm import joinedload
from .carRoutes import get_car

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
    total_price = request.form.get('total_price')
    car_id = request.form.get('car_id')  # Get car_id from the form
    quantity = request.form.get('quantity', 1)  # Default to 1 if not provided
    message = request.form.get('message')  # Message field from the form

    if 'user' in session:
        # Logged-in user scenario
        current_user = session['user']
        new_order = Order(user_id=current_user['id'], total_price=total_price, message=message)
    else:
        # Unauthenticated user scenario (using a contact form)
        guest_name = request.form.get('guest_name')
        guest_email = request.form.get('guest_email')
        guest_phone = request.form.get('guest_phone')

        new_order = Order(user_id=None, total_price=total_price, 
                          guest_name=guest_name, 
                          guest_email=guest_email, 
                          guest_phone=guest_phone,
                          message=message)

    # Add the order to the database
    db.session.add(new_order)
    db.session.commit()

    # Create a record in the association table for the order and car
    order_car_entry = order_car.insert().values(
        order_id=new_order.id,
        car_id=car_id,
        quantity=quantity,
        price=total_price
    )
    db.session.execute(order_car_entry)
    db.session.commit()

    flash("Order created successfully! We will contact you shortly.", "success")
    return redirect(url_for('car.get_car', car_id=car_id))
   


# Read all orders for a user (only for logged-in users)
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
def get_order(order_id):
    if 'user' not in session:
        flash("You must be logged in to access this feature.", "danger")
        return redirect(url_for('user.login'))

    current_user = session['user']  # Access session data only after the check

    order = Order.query.options(joinedload(Order.cars)).get_or_404(order_id)

    if current_user.get('role') != 'admin' and order.user_id != current_user['id']:
        flash("You are not authorized to view this order.", "danger")
        return redirect(url_for('order.get_orders'))

    return render_template('orders/orderDetail.html', order=order, user=current_user)


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
