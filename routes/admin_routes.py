# routes/admin_routes.py
from flask import Blueprint, render_template, session, request, jsonify
from .user_routes import admin_required
from models import User, UserStatus, Product, Car
from sqlalchemy import func
from datetime import datetime, timedelta

admin_bp = Blueprint('admin_bp', __name__)

@admin_bp.route('/home')
@admin_required
def home():
    current_user = session.get('user')

    # Get the current date to filter based on month
    current_date = datetime.now()

    # Define the time period options (monthly, quarterly, etc.)
    period = request.args.get('period', 'monthly')  # Default to 'monthly'

    if period == 'monthly':
        # Fetch monthly new user counts (same as before)
        months = []
        for i in range(6):
            # Calculate the correct month
            month = current_date.month - (5 - i)  # This gives us the last 6 months
            
            # If month goes below 1 (January), adjust the year
            if month <= 0:
                month += 12
                year = current_date.year - 1
            else:
                year = current_date.year

            # Create a date representing the first day of the month
            months.append(datetime(year, month, 1))

        user_counts = []
        for month in months:
            # Start of the month and end of the month
            start_of_month = month.replace(day=1)
            if month.month == 12:
                end_of_month = month.replace(year=month.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_of_month = (month.replace(month=month.month + 1, day=1) - timedelta(days=1))

            # Count users who registered within the month range
            user_count = User.query.filter(User.created_at >= start_of_month, User.created_at <= end_of_month).count()
            user_counts.append(user_count)

        # Prepare the data to pass to the template
        user_growth_data = {
            'months': [month.strftime('%B %Y') for month in months],
            'user_counts': user_counts
        }

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(user_growth_data)
    
    # User Status Breakdown Calculation
    active_count = User.query.filter(User.status == UserStatus.ACTIVE).count()
    inactive_count = User.query.filter(User.status == UserStatus.INACTIVE).count()

        # Quick Stats Data
    total_users = User.query.count()
    total_active_users = active_count
    total_inactive_users = inactive_count

        # Formatting the total user count to show "k" or "m"
    total_users_formatted = f"{total_users:,}"
    if total_users >= 1000000:
        total_users_formatted = f"{total_users / 1000000:.1f}M"
    elif total_users >= 1000:
        total_users_formatted = f"{total_users / 1000:.1f}K"

    # Product Stock Data
    low_stock_threshold = 5  # You can change this threshold as needed
    low_stock_products = Product.query.filter(Product.stock <= low_stock_threshold).all()
    out_of_stock_products = Product.query.filter(Product.stock == 0).count()
    total_products = Product.query.count()
    total_cars = Car.query.count()


    # Prepare the data for the Pie chart (User Status Breakdown)
    user_status_data = {
        'labels': ['Active', 'Inactive'],
        'data': [active_count, inactive_count],
    }

    product_stock_data = {
        'low_stock_products': low_stock_products,
        'out_of_stock_products': out_of_stock_products,
        'total_products': total_products,
    }


    return render_template('Admin/home.html', 
                           user=current_user, 
                           user_growth_data=user_growth_data, 
                           user_status_data=user_status_data,
                           total_users=total_users_formatted,
                           total_active_users=total_active_users,
                           total_inactive_users=total_inactive_users,
                           product_stock_data=product_stock_data,
                           period=period,
                           total_cars=total_cars)

