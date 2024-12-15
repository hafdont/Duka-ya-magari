from flask import Blueprint, request, jsonify, session, redirect, url_for, flash, render_template
from models import Review, User, Car, Product
from app import db

review_bp = Blueprint('review', __name__)

# Add a new review
@review_bp.route('/add_review/<int:car_id>', methods=['POST'])
def add_review():
    current_user = session.get('user')
    if not current_user:
        flash("You must be logged in to add a review.", "danger")
        return redirect(url_for('user.login'))

    data = request.form
    comment = data.get('comment')
    rating = data.get('rating')
    car_id = request.form.get('car_id')  # For car review
    product_id = request.form.get('product_id')  # For product review

    # If reviewing a car
    if car_id:
        car = Car.query.get(car_id)
        if not car:
            flash("Car not found", "danger")
            return redirect(url_for('home.index'))
        
        new_review = Review(user_id=current_user['id'],rating=rating, comment=comment, car_id=car.id)
    
    # If reviewing a product
    elif product_id:
        product = Product.query.get(product_id)
        if not product:
            flash("Product not found", "danger")
            return redirect(url_for('home.index'))
        
        new_review = Review(user_id=current_user['id'],rating=rating, comment=comment, product_id=product.id)

    db.session.add(new_review)
    db.session.commit()
    
    flash("Review added successfully!", "success")
    return redirect(url_for('product.view_product', product_id=product.id) if product_id else url_for('car.view_car', car_id=car.id))

# View all reviews for a car
@review_bp.route('/reviews/<int:car_id>', methods=['GET'])
def view_reviews(car_id):
    reviews = Review.query.filter_by(car_id=car_id).all()
    car = Car.query.get(car_id)
    return render_template('cars/carReviews.html', car=car, reviews=reviews)

# Edit a review
@review_bp.route('/edit_review/<int:review_id>', methods=['GET', 'POST'])
def edit_review(review_id):
    current_user = session.get('user')
    review = Review.query.get(review_id)

    if not review or (review.user_id != current_user['id'] and current_user['role'] != 'admin'):
        flash("Unauthorized access!", "danger")
        return redirect(url_for('car.get_car', car_id=review.car_id))

    if request.method == 'GET':
        return render_template('reviews/editReview.html', review=review)

    if request.method == 'POST':
        data = request.form
        review.comment = data.get('comment')
        review.rating = data.get('rating')
        db.session.commit()
        flash("Review updated successfully!", "success")
        return redirect(url_for('car.get_car', car_id=review.car_id))

# Delete a review
@review_bp.route('/delete_review/<int:review_id>', methods=['POST'])
def delete_review(review_id):
    current_user = session.get('user')
    review = Review.query.get(review_id)

    if not review or (review.user_id != current_user['id'] and current_user['role'] != 'admin'):
        flash("Unauthorized access!", "danger")
        return redirect(url_for('car.get_car', car_id=review.car_id))

    db.session.delete(review)
    db.session.commit()
    flash("Review deleted successfully!", "success")
    return redirect(url_for('car.get_car', car_id=review.car_id))
