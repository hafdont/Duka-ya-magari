from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from enum import Enum
from flask_sqlalchemy import SQLAlchemy
from app import db

class StockStatus(Enum):
    IN_STOCK = "In Stock"
    OUT_OF_STOCK = "Out of Stock"
    LIMITED = "Limited"

class UserRole(Enum):
    ADMIN = 'admin'
    CUSTOMER = 'customer'

class UserStatus(Enum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'

class OrderStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"

class Gender(Enum):
    MALE = 'male'
    FEMALE = 'female'

# Updated Category Enum
class CategoryType(Enum):
    TOOLS_MACHINERY = 'Tools_and_Machinery'
    CAR_PARTS = 'Car_Parts'
    HOUSEHOLD_ITEMS = 'Household_Items'
    COMPUTERS = 'Computers'
    CARS = 'Cars'

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(50), nullable=False)
    category_type = db.Column(db.String(50), nullable=False)

    # Relationship to access all cars in this category
    cars_in_category = db.relationship('Car', back_populates='category', lazy=True)
    
    def __repr__(self):
        return f"<Category {self.category_name}>"

# User model
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    firstname = db.Column(db.String(50), nullable=False)
    lastname = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), default=UserRole.CUSTOMER, nullable=False)
    status = db.Column(db.Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)

    # Address details
    city = db.Column(db.String(50), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    country = db.Column(db.String(50), nullable=True)

    # Contact information
    phone_number = db.Column(db.String(15), nullable=True)

    # User bio or description
    bio = db.Column(db.Text, nullable=True)

    # User Profile image
    profile_picture = db.Column(db.String(255), nullable=True)

    # New fields
    date_of_birth = db.Column(db.Date, nullable=True) 
    gender = db.Column(db.Enum(Gender), nullable=True)  

    # Relationships
    owned_cars = db.relationship('Car', back_populates='seller')
    orders = db.relationship('Order', backref='customer', lazy=True)
    likes = db.relationship('Like', backref='liked_items', lazy=True)
    products = db.relationship('Product', back_populates='user')  # Relationship to products

    def __repr__(self):
        return f"<User {self.username}>"

    def full_name(self):
        return f"{self.firstname} {self.lastname}"

    def is_active(self):
        return self.status == UserStatus.ACTIVE

    # Count methods
    def car_count(self):
        return len(self.owned_cars)

    def order_count(self):
        return len(self.orders)

    def wishlist_count(self):
        return len(self.likes)

class Item(db.Model):
    __tablename__ = 'items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)  # Add the foreign key
    car_id = db.Column(db.Integer, db.ForeignKey('cars.id'), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    total_price = db.Column(db.Numeric(10 , 2), nullable=False)

    car = db.relationship('Car', backref=db.backref('associated_items', lazy=True))
    product = db.relationship('Product', backref=db.backref('associated_items', lazy=True))

    def __repr__(self):
        return f"<Item (Car: {self.car_id}, Product: {self.product_id})>"

# Updated Product model
class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, default=1)
    StockStatus = db.Column(db.Enum(StockStatus), default=StockStatus.IN_STOCK, nullable=False)
    description = db.Column(db.Text, nullable=True)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    category = db.Column(db.Enum(CategoryType), nullable=False)


    # Foreign key to link to the User model
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    specifications = db.relationship('ProductSpecification', backref='product', lazy=True)


    
    # Relationships
    user = db.relationship('User', back_populates='products')

    def __repr__(self):
        return f"<Product {self.name}>"

# ProductSpecification model
class ProductSpecification(db.Model):
    __tablename__ = 'product_specifications'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    key = db.Column(db.String(50), nullable=False)
    value = db.Column(db.String(255), nullable=False)
    brand_name = db.Column(db.String(100), nullable=True)  # Store the brand name directly
    category_name = db.Column(db.String(100), nullable=True)  # Store the category name directly


    # Relationships
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    brand_id = db.Column(db.Integer, db.ForeignKey('brands.id'), nullable=True)
    brand = db.relationship('Brand', backref='products', lazy=True)

    def __repr__(self):
        return f"<Specification {self.key}: {self.value}>"

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Allow nullable user_id
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    order_status = db.Column(db.Enum(OrderStatus), default=OrderStatus.PENDING)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    message = db.Column(db.Text, nullable=True)

    # Guest user fields
    guest_name = db.Column(db.String(100), nullable=True)
    guest_email = db.Column(db.String(100), nullable=True)
    guest_phone = db.Column(db.String(15), nullable=True)

    # Relationships
    user = db.relationship('User', backref='user_orders', lazy=True)


    def __repr__(self):
        return f"<Order {self.id} for User {self.user.username if self.user else self.guest_name}>"

    def get_status_display(self):
        return self.order_status.value

# Image model for storing multiple images for Cars, Users, and potentially Admins
class Image(db.Model):
    __tablename__ = 'images'
    id = db.Column(db.Integer, primary_key=True)
    car_id = db.Column(db.Integer, db.ForeignKey('cars.id'), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    image_path = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    car = db.relationship('Car', backref=db.backref('car_images', lazy=True))
    product = db.relationship('Product', backref=db.backref('product_images', lazy=True))

    def __repr__(self):
        return f"<Image {self.image_path}>"

# Brand model
class Brand(db.Model):
    __tablename__ = 'brands'
    id = db.Column(db.Integer, primary_key=True)
    brand_name = db.Column(db.String(50), nullable=False)
    brand_logo = db.Column(db.String(255), nullable=True)
    category = db.Column(db.Enum(CategoryType), nullable=False)

    def __repr__(self):
        return f"<Brand {self.brand_name}>"

# Category model
class Car(db.Model):
    
    __tablename__ = 'cars'
    id = db.Column(db.Integer, primary_key=True)
    brand_id = db.Column(db.Integer, db.ForeignKey('brands.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)  
    model = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    mileage = db.Column(db.Integer, nullable=False)
    interior_color = db.Column(db.String(30), nullable=False)
    exterior_color = db.Column(db.String(30), nullable=False)
    description = db.Column(db.Text)
    stock = db.Column(db.Integer, default=1)
    StockStatus = db.Column(db.Enum(StockStatus), default=StockStatus.IN_STOCK, nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    condition = db.Column(db.String(20), nullable=False)
    transmission = db.Column(db.String(20), nullable=False)
    fuel_type = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    warranty = db.Column(db.String(100))
    vin = db.Column(db.String(17), unique=True)
    features = db.Column(db.Text)
    status = db.Column(db.String(20), default='available')

    # Relationships
    brand = db.relationship('Brand', backref=db.backref('cars', lazy=True))
    category = db.relationship('Category', back_populates='cars_in_category')
    seller = db.relationship('User', back_populates='owned_cars')

    def __repr__(self):
        return f"<Car {self.model} {self.year}>"

# Payment model
class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(20))
    payment_status = db.Column(db.String(20), default='pending')
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    order = db.relationship('Order', backref=db.backref('payments', lazy=True))
    user = db.relationship('User', backref=db.backref('payments', lazy=True))

    def __repr__(self):
        return f"<Payment {self.id} for Order {self.order_id}>"

# Review model
class Review(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    car_id = db.Column(db.Integer, db.ForeignKey('cars.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # Consider adding a check constraint
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    car = db.relationship('Car', backref=db.backref('reviews', lazy=True))
    user = db.relationship('User', backref=db.backref('reviews', lazy=True))

    def __repr__(self):
        return f"<Review {self.rating} for Car {self.car.model}>"

# Cart model
class Cart(db.Model):
    __tablename__ = 'carts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    car_id = db.Column(db.Integer, db.ForeignKey('cars.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('carts', lazy=True))
    car = db.relationship('Car', backref=db.backref('carts', lazy=True))

    def __repr__(self):
        return f"<Cart {self.id} for User {self.user.username}>"

class Like(db.Model):
    __tablename__ = 'likes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)  # ID of the liked item
    target_type = db.Column(db.String(50), nullable=False)  # 'car', 'review', etc.

    user = db.relationship('User', backref='liked_items')

    def __repr__(self):
        return f"<Like {self.id} for User {self.user.username}>"
