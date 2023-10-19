from flask import request, g, jsonify, Blueprint
import datetime
from pathlib import Path
import time
import jwt
import sqlite3
from sqlalchemy.orm import joinedload
from models import Users, Connections, JobPostings, UserPreferences

handlers = Blueprint('handlers', __name__)
authenticated_handlers = Blueprint('authenticated_handlers', __name__)

@handlers.route('/list-users', methods=['GET'])
def list_users():
    labels = ['username', 'firstname', 'lastname']
    users = g.session.query(*[getattr(Users, label) for label in labels]).all()
    
    return jsonify([{label: user._asdict()[label] for label in labels} for user in users]), 200

@handlers.route('/lookup-user', methods=['POST'])
def lookup_user():
    data = request.get_json()

    fields = ['firstname', 'lastname', 'university', 'major']
    if any(field not in fields for field in data):
        return jsonify({'error': 'Invalid fields.'}), 400
    fields = list(data.keys())

    labels = ['username', 'firstname', 'lastname']
    query = g.session.query(*[getattr(Users, label) for label in labels])
    for field in fields:
        query = query.filter(getattr(Users, field) == data[field])
    matches = query.all()

    return jsonify({'matches': [{label: user._asdict()[label] for label in labels} for user in matches]}), 200

@handlers.route('/login', methods=['POST'])
def log_in():
    try:
        username, passwordHash = tuple(request.get_json()[label] for label in ['username', 'passwordHash'])
    except KeyError:
        return jsonify({'error': 'Missing data, both username and password are required.'}), 400

    user = g.session.query(Users.id, Users.username, Users.passwordHash) \
        .filter(Users.username == username).one_or_none()

    if user is None:
        return jsonify({'error': 'Invalid username or password.'}), 400

    user_id, retrieved_username, retrieved_passwordHash = user
    if retrieved_passwordHash != passwordHash:
        return jsonify({'error': 'Invalid username or password.'}), 400

    # The user is authenticated successfully, create and return a JWT token
    jwt_key = Path('./jwt-key.txt').read_text().strip()
    payload = {
        'user_id': user_id,
        'username': retrieved_username,
        'exp': time.time() + (24 * 60 * 60)  # 24 hours from now
    }
    token = jwt.encode(payload, jwt_key, algorithm='HS256')

    return jsonify({'token': token}), 200

@handlers.route('/add-user', methods=['POST'])
def add_user():
    session = g.session
    data = request.get_json()

    fields = ['username', 'firstname', 'lastname', 'university', 'major', 'passwordHash']
    if set(data.keys()) != set(fields):
        return jsonify({'error': 'Invalid fields.'}), 400

    if session.query(Users).count() >= 10:
        return jsonify({'error': 'Limit of ten users has been reached'}), 400

    session.add(Users(**{field: data[field] for field in fields}))

    try:
        session.commit()
        user_id = new_user.id
    except IntegrityError:
        session.rollback()
        return jsonify({'error': 'The username you chose has already been taken.'}), 400

    session.add(UserPreferences(user_id=user_id, email_notifications_enabled=True,
        sms_notifications_enabled=True, targeted_advertising_enabled=True, language='english'))
    session.commit()

    return jsonify({'success': 'User successfully added'}), 200

@authenticated_handlers.route('/profile', methods=['GET'])
def get_profile():
    labels = ['username', 'firstname', 'lastname']
    profile = g.session.query(*[getattr(Users, label) for label in labels]) \
        .filter(Users.id == g.user_id).one_or_none()

    if profile is None:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({label: profile._asdict()[label] for label in labels}), 200

@authenticated_handlers.route('/make-connection-request', methods=['POST'])
def make_connection_request():
    session = g.session
    data = request.get_json()

    target_username = data.get('username')
    if target_username == None:
        return jsonify({'error': 'Missing username.'}), 400

    if g.username == target_username:
        return jsonify({'error': 'You cannot connect with yourself.'}), 400

    target = session.query(Users.id).filter(Users.username == target_username).one_or_none()
    if target is None:
        return jsonify({'error': 'User not found.'}), 404

    existing_connections = session.query(Connections).filter(
            ((Connections.user_id == g.user_id) & (Connections.connection_id == target.id))
            | ((Connections.user_id == target.id) & (Connections.connection_id == g.user_id))
        ).count()
    if existing_connections > 0:
        return jsonify({'error':
            'Either you are already following each other or one of you has an open connection request to the other.'
        }), 400

    session.add(Connections(user_id=g.user_id, connection_id=target.id, request_status="pending"))
    session.commit()

    return jsonify({'message': f'Connections request sent to {target_username}'}), 200

@authenticated_handlers.route('/pending-requests', methods=['GET'])
def pending_requests():
    pending_connection_requests = g.session.query(Users.username, Users.firstname, Users.lastname) \
        .join(Connections, Users.id == Connections.user_id) \
        .filter(Connections.connection_id == g.user_id, Connections.request_status == "pending") \
        .all()

    return jsonify([
        {label: request_sender._asdict()[label] for label in ['username', 'firstname', 'lastname']}
        for request_sender in pending_connection_requests
    ]), 200

@authenticated_handlers.route('/accept-requests', methods=['POST'])
def accept_requests():
    session = g.session
    data = request.get_json()

    users_to_accept = data.get('users-to-accept', [])
    users_to_deny = data.get('users-to-deny', [])

    accepted, denied, ignored = [], [], []

    for username in users_to_accept + users_to_deny:
        username = username['username']

        connection_request = session.query(Connections) \
            .join(Users, Connections.user_id == Users.id) \
            .filter((Users.username == username) &
                (Connections.connection_id == g.user_id) &
                (Connections.request_status == 'pending')) \
            .one_or_none()
        
        if connection_request is None:
            ignored.append({ 'username': username })
            continue

        if username in [user['username'] for user in users_to_accept]:
            connection_request.request_status = 'accepted'
            accepted.append({ 'username': username })
        elif username in [user['username'] for user in users_to_deny]:
            session.delete(connection_request)
            denied.append({ 'username': username })
        else:
            raise Exception('There is a bug in this part of code.')

    session.commit()

    return jsonify({ 'accepted': accepted, 'denied': denied, 'ignored': ignored }), 200

@authenticated_handlers.route('/connections', methods=['GET'])
def connections():
    connections = \
        g.session.query(Users.username, Users.firstname, Users.lastname) \
        .join(Connections, ((Users.id == Connections.user_id) & (Connections.connection_id == g.user_id)) |
            ((Users.id == Connections.connection_id) & (Connections.user_id == g.user_id))) \
        .filter(Connections.request_status == 'accepted') \
        .all()

    return jsonify([{label:
        connection._asdict()[label] for label in ['username', 'firstname', 'lastname']}
        for connection in connections
    ]), 200

@authenticated_handlers.route('/disconnect', methods=['POST'])
def disconnect():
    session = g.session
    
    username_to_disconnect = request.get_json().get('username')
    if username_to_disconnect == None:
        return jsonify({ 'error': 'FORMAT: { \'username\': username }'}), 400

    connection = session.query(Connections) \
        .join(Users, Connections.user_id == Users.id) \
        .filter((Users.username == username_to_disconnect) & \
            ((Connections.user_id == g.user_id) | (Connections.connection_id == g.user_id))) \
        .one_or_none()

    if connection is None:
        return jsonify({'error': f'you are not connected with {username_to_disconnect}.'}), 400

    session.delete(connection)
    session.commit()
    return jsonify({'success': f'successfully disconnected from {username_to_disconnect}'}), 200

@authenticated_handlers.route('/disconnect', methods=['POST'])
def post_job():
    session = g.session
    data = request.get_json()

    fields = ['title', 'description', 'employer', 'location', 'salary']
    if set(data.keys()) != set(fields):
        return jsonify({'error': 'Missing data, all fields are required.'}), 400

    if session.query(JobPostings).count() >= 5:
        return jsonify({'error': 'Limit of five job postings has been reached' }), 400

    user_id = user[0]
    session.add(JobPostings(**{field: data[field] for field in fields}, user_id=g.user_id))
    session.commit()

    return jsonify({'message': 'Job posting created successfully.'}), 200

@handlers.route('/job-postings', methods=['GET'])
def get_job_postings():
    fields = ['title', 'description', 'employer', 'location', 'salary']
    postings = g.session.query(*[getattr(JobPostings, field) for field in fields], Users.username) \
        .join(Users, JobPostings.user_id == Users.id).all()

    return jsonify([{field: posting[i] for i, field in
        enumerate(['title', 'description', 'employer', 'location', 'salary', 'username'])}
        for posting in postings]), 200

@authenticated_handlers.route('/user-preferences', methods=['GET'])
def get_user_preferences():
    label = [
        'email_notifications_enabled',
        'sms_notifications_enabled',
        'targeted_advertising_enabled',
        'language'
    ]
    preferences = g.session.query(*[getattr(UserPreferences, label) for label in labels]) \
        .filter(UserPreferences.user_id == g.user_id).one_or_none()

    if preferences is None:
        return jsonify({'error': 'Preferences not found'}), 404

    return jsonify({label: getattr(preferences, label) for label in labels}), 200

@authenticated_handlers.route('/set-user-preferences', methods=['POST'])
def set_user_preferences():
    session = g.session
    data = request.get_data()

    if len(data) != 1:
        return jsonify({'error': 'FORMAT: { field: value }'}), 400
    field, value = list(data.items())[0]
    if field not in ['email_notifications_enabled',
        'sms_notifications_enabled',
        'targeted_advertising_enabled',
        'language']:
        return jsonify({'error': f'Invalid field: {field}'})

    preferences = session.query(UserPreferences) \
        .filter(UserPreferences.user_id == g.user_id).one_or_none()
    setattr(preferences, field, value)
    session.commit()

    return jsonify({'message': 'Preferences updated successfully.'}), 200
