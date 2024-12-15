from flask import Blueprint, request, render_template, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
from models import db, Car, User, CategoryType, StockStatus, Brand, Category, Image, Like, Review
from .admin_routes import admin_required
import os

car_bp = Blueprint('car', __name__)

# Set the upload folder for images
CARS_UPLOAD_FOLDER = os.getenv('CARS_UPLOAD_FOLDER', 'uploads/cars')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_car_data_from_form(form):
    return {
        'brand_id': form.get('brand_id'),
        'category_id': form.get('category_id'),
        'model': form.get('model'),
        'year': form.get('year'),
        'price': form.get('price'),
        'mileage': form.get('mileage'),
        'interior_color': form.get('interior_color'),
        'exterior_color': form.get('exterior_color'),
        'description': form.get('description'),
        'stock': form.get('stock', 1),
        'condition': form.get('condition'),
        'transmission': form.get('transmission'),
        'fuel_type': form.get('fuel_type'),
        'location': form.get('location'),
        'seller_id': session['user']['id'], 
        'warranty': form.get('warranty'),
        'vin': form.get('vin'),
        'features': form.get('features'),
        'status': form.get('status', 'available')
    }

@car_bp.route('/cars/create', methods=['GET', 'POST'])
@admin_required
def create_car():
    current_user = session.get('user', None)

    if request.method == 'GET':
        brands = Brand.query.all()
        categories = Category.query.all()
        return render_template('cars/newCar.html', brands=brands, user=current_user,categories = Category.query.filter_by(category_type=CategoryType.CARS.value).all())

    if request.method == 'POST':
        car_data = get_car_data_from_form(request.form)

        # Check for duplicate VIN
        existing_car = Car.query.filter_by(vin=car_data['vin']).first()
        if existing_car:
            flash("A car with this VIN already exists.", "danger")
            return redirect(url_for('car.create_car'))

        # Handle image upload
        if 'images' in request.files:
            files = request.files.getlist('images')
            print("Files Uploaded:", files)

            if not files or all(file.filename == '' for file in files):
                print("No files selected.")
                flash("Invalid file type or no file selected.", "danger")
                return redirect(url_for('car.create_car'))

            # Save the car data first
            new_car = Car(**car_data)
            db.session.add(new_car)
            db.session.commit()  # Commit to get the new_car.id

            # Process and save each uploaded file
            for file in files:
                if not allowed_file(file.filename):
                    print("Invalid file type for file:", file.filename)
                    flash("Invalid file type for file: {}".format(file.filename), "danger")
                    continue  # Skip invalid files

                filename = secure_filename(file.filename)
                file_path = os.path.join(CARS_UPLOAD_FOLDER, filename)

                # Create directory if it doesn't exist
                os.makedirs(CARS_UPLOAD_FOLDER, exist_ok=True)
                print("Saving file to:", file_path)
                file.save(file_path)
                print("File saved successfully:", filename)

                # Save the image information with the correct car_id
                new_image = Image(car_id=new_car.id, image_path=filename)
                db.session.add(new_image)

            # Commit the images after all are processed
            db.session.commit()
            print("New car and images added to the database:", new_car.id)

            flash("Car created successfully!", "success")
            return redirect(url_for('car.get_cars'))

        print("Image upload required.")
        flash("Image upload required.", "danger")
        return redirect(url_for('car.create_car'))

@car_bp.route('/cars', methods=['GET'])
@admin_required
def get_cars():
    current_user = session.get('user', None)
    cars = Car.query.all()
    users = User.query.all()

    liked_cars = []
    if current_user:
        liked_cars = [like.target_id for like in Like.query.filter_by(user_id=current_user['id'], target_type='car').all()]

    return render_template('cars/carList.html', cars=cars, user=current_user, liked_cars=liked_cars, users=users)

@car_bp.route('/cars/<int:car_id>', methods=['GET'])
def get_car(car_id):
    current_user = session.get('user', None)
    car = Car.query.get_or_404(car_id)
    reviews = Review.query.filter_by(car_id=car_id).all()
    return render_template('cars/car_detail.html', car=car, user=current_user,reviews=reviews )

@car_bp.route('/likes', methods=['POST'])
def toggle_like():
    data = request.get_json()
    target_id = data.get('car_id')  # Ensure the key matches what you send from the frontend
    target_type = data.get('target_type')  
    current_user = session.get('user')  # Get the current user from the session

    if not current_user:
        return jsonify({'success': False, 'message': 'User not logged in'}), 403

    # Check if the like already exists
    existing_like = Like.query.filter_by(user_id=current_user['id'], target_id=target_id, target_type='car').first()

    if existing_like:
        db.session.delete(existing_like)  # Unlike
    else:
        new_like = Like(user_id=current_user['id'], target_id=target_id, target_type='car')  # Like
        db.session.add(new_like)

    db.session.commit()
    return jsonify({'success': True})

# Update a Car
@car_bp.route('/cars/edit/<int:car_id>', methods=['GET', 'POST'])
@admin_required
def update_car(car_id):
    current_user = session.get('user', None)
    car = Car.query.get(car_id)
    if not car:
        flash("Car not found.", "danger")
        return redirect(url_for('car.get_all_cars'))

    if request.method == 'GET':
        brands = Brand.query.all()
        categories = Category.query.all()
        return render_template('cars/updateCar.html', car=car, brands=brands, categories = Category.query.filter_by(category_type=CategoryType.CARS.value).all(),user=current_user)

    if request.method == 'POST':
        car_data = get_car_data_from_form(request.form)

        # Handle image upload
        if 'image' in request.files:
            file = request.files['image']
            if file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(CARS_UPLOAD_FOLDER, filename)

                os.makedirs(CARS_UPLOAD_FOLDER, exist_ok=True)
                file.save(file_path)

                # Update image
                image = Image.query.filter_by(car_id=car.id).first()
                if image:
                    image.image_path = filename
                    db.session.commit()

        # Update car fields
        for key, value in car_data.items():
            setattr(car, key, value)

        db.session.commit()
        flash("Car updated successfully!", "success")
        return redirect(url_for('car.get_all_cars'))
    
@car_bp.route('/cars/delete/<int:car_id>', methods=['POST'])
@admin_required
def delete_car(car_id):
    car = Car.query.get_or_404(car_id)
    db.session.delete(car)
    db.session.commit()
    return redirect(url_for('get_cars'))

