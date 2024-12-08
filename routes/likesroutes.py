from flask import Blueprint, jsonify, request, session
from app import db
from models import Like, Car, Review

like_bp = Blueprint('like', __name__)

@like_bp.route('/like', methods=['POST'])
def toggle_like():
    # Ensure the user is logged in via session
    current_user_id = session.get('user', {}).get('id')
    if not current_user_id:
        return jsonify({'error': 'User not logged in'}), 401

    target_id = request.json.get('target_id')
    action = request.json.get('action')  # "like" or "unlike"

    if not car_id:
        return jsonify({'error': 'Car ID is required'}), 400

    if action == 'like':
        # Check if the user already liked this car
        existing_like = Like.query.filter_by(user_id=current_user_id, target_id=car_id, target_type='car').first()
        if existing_like:
            return jsonify({'error': 'Already liked'}), 400  # Prevent duplicate likes
        
        like = Like(user_id=current_user_id, target_id=car_id, target_type='car')
        db.session.add(like)
        message = 'Liked'
        
    elif action == 'unlike':
        like = Like.query.filter_by(user_id=current_user_id, target_id=car_id, target_type='car').first()
        if like:
            db.session.delete(like)
            message = 'Unliked'
        else:
            return jsonify({'error': 'Like not found'}), 404
            
    else:
        return jsonify({'error': 'Invalid action'}), 400

    db.session.commit()
    return jsonify({'message': message}), 200

