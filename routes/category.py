from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db
from models import Category, User, CategoryType
from.user_routes import admin_required

category_bp = Blueprint('category', __name__)

# List Categories
@category_bp.route('/categories', methods=['GET'])
def list_categories():
    current_user = session.get('user', None) 
    categories = Category.query.all()
    return render_template(
        '/Categories/categories.html',
        categories=categories,
        user=current_user,
        cats=CategoryType  # Pass the enum directly to Jinja as 'cats'
    )

# Add Category
@category_bp.route('/categories/add', methods=['POST'])
@admin_required
def add_category():
    current_user = session.get('user', None) 
    category_name = request.form.get('category_name')
    category_type = request.form.get('category_type')

    if not category_name or not category_type:
        flash('Both Category Name and Type are required!', 'danger')
        return redirect(url_for('category.add_category'))


    new_category = Category(category_name=category_name, category_type=category_type)
    db.session.add(new_category)

    try:
        db.session.commit()
        flash('Category added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding category: {e}', 'danger')

    return redirect(url_for('category.list_categories'))


# Edit Category
@category_bp.route('/categories/edit/<int:category_id>', methods=['GET', 'POST'])
@admin_required
def edit_category(category_id):
    """Edit an existing category"""
    current_user = session.get('user', None)
    category = Category.query.get_or_404(category_id)

    if request.method == 'POST':
        category_name = request.form.get('category_name')
        category_type = request.form.get('category_type')

        if not category_name or not category_type:
            flash('Both Category Name and Type are required!', 'danger')
            return redirect(url_for('category.edit_category', category_id=category_id))

        category.category_name = category_name
        category.category_type = category_type

        try:
            db.session.commit()
            flash('Category updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating category: {e}', 'danger')

        return redirect(url_for('category.list_categories'))

    return render_template('/Categories/edit_category.html', category=category, user=current_user)


# Delete Category
@category_bp.route('/categories/delete/<int:category_id>', methods=['POST'])
@admin_required
def delete_category(category_id):
    """Delete an existing category"""
    category = Category.query.get_or_404(category_id)
    db.session.delete(category)

    try:
        db.session.commit()
        flash('Category deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting category: {e}', 'danger')

    return redirect(url_for('category.list_categories'))