# routes/__init__.py

from flask import Flask
from .user_routes import user_bp
from .home_routes import home_bp
from .carRoutes import car_bp
from .admin_routes import admin_bp
from .brand_routes import brand_bp
from .category import category_bp
from .reviewsRoutes import review_bp
from .oderRoutes import order_bp


def register_routes(app: Flask):
    # Register blueprints here
    app.register_blueprint(user_bp)
    app.register_blueprint(home_bp)
    app.register_blueprint(car_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(brand_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(review_bp)
    app.register_blueprint(order_bp)

    

