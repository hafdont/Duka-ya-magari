from flask import Blueprint, jsonify, request, session
from app import db
from models import Like, Car, Review, Product, Blog, Review

like_bp = Blueprint('like', __name__)

@like_bp.route('/like', methods=['POST'])
def like():
    data = request.get_json()
    item_id = data.get('item_id')
    item_type = data.get('item_type')
    action = data.get('action')

    current_user = session.get('user')
    if not current_user:
        return jsonify({'error': 'User not logged in'}), 401

    user_id = current_user.get('id')

    # Validate item_type and update the corresponding field
    valid_types = {'car': Car, 'product': Product, 'blog': Blog, 'review': Review}
    if item_type not in valid_types:
        return jsonify({'error': 'Invalid item type'}), 400

    # Determine the foreign key field dynamically
    like_query = Like.query.filter_by(user_id=user_id, target_type=item_type, **{f"{item_type}_id": item_id})
    existing_like = like_query.first()

    try:
        if action == 'like' and not existing_like:
            # Create a new Like instance dynamically
            new_like = Like(user_id=user_id, target_type=item_type, **{f"{item_type}_id": item_id})
            db.session.add(new_like)
        elif action == 'unlike' and existing_like:
            db.session.delete(existing_like)
        else:
            return jsonify({'error': 'Invalid action or like state'}), 400

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

