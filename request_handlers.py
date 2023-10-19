import datetime
from pathlib import Path
import time
import jwt
import sqlite3
from sqlalchemy.orm import joinedload
from models import Users, Connections, JobPostings, UserPreferences

def list_users(session):
    labels = ['username', 'firstname', 'lastname']
    users = session.query(*[getattr(Users, label) for label in labels]).all()
    
    return [{label: user._asdict()[label] for label in labels} for user in users], 200

def lookup_user(session, data):
    fields = ['firstname', 'lastname', 'university', 'major']
    if any(field not in fields for field in data):
        return {'error': 'Invalid fields.'}, 400
    fields = list(data.keys())

    labels = ['username', 'firstname', 'lastname']
    query = session.query(*[getattr(Users, label) for label in labels])
    for field in fields:
        query = query.filter(getattr(Users, field) == data[field])
    matches = query.all()

    return { 'matches': [{label: user._asdict()[label] for label in labels} for user in matches] }, 200

def log_in(session, data):
    try:
        username, passwordHash = tuple(data[label] for label in ['username', 'passwordHash'])
    except KeyError:
        return {'error': 'Missing data, both username and password are required.'}, 400

    user = session.query(Users.id, Users.username, Users.passwordHash) \
        .filter(Users.username == username).one_or_none()

    if user is None:
        return {'error': 'Invalid username or password.'}, 400

    user_id, retrieved_username, retrieved_passwordHash = user
    if retrieved_passwordHash != passwordHash:
        return {'error': 'Invalid username or password.'}, 400

    # The user is authenticated successfully, create and return a JWT token
    jwt_key = Path('./jwt-key.txt').read_text().strip()
    payload = {
        'user_id': user_id,
        'username': retrieved_username,
        'exp': time.time() + (24 * 60 * 60)  # 24 hours from now
    }
    token = jwt.encode(payload, jwt_key, algorithm='HS256')

    return {'token': token}, 200

def add_user(session, data):
    fields = ['username', 'firstname', 'lastname', 'university', 'major', 'passwordHash']
    if set(data.keys()) != set(fields):
        return {'error': 'Invalid fields.'}, 400

    if session.query(Users).count() >= 10:
        return {'error': 'Limit of ten users has been reached'}, 400

    session.add(Users(**{field: data[field] for field in fields}))

    try:
        session.commit()
        user_id = new_user.id
    except IntegrityError:
        session.rollback()
        return {'error': 'The username you chose has already been taken.'}, 400

    session.add(UserPreferences(user_id=user_id, email_notifications_enabled=True,
        sms_notifications_enabled=True, targeted_advertising_enabled=True, language='english'))
    session.commit()

    return { 'success': 'User successfully added' }, 200

def get_profile(session, user):
    user_id = user[0]

    labels = ['username', 'firstname', 'lastname']
    profile = session.query(*[getattr(Users, label) for label in labels]) \
        .filter(Users.id == user_id).one_or_none()

    if profile is None:
        return {'error': 'User not found'}, 404

    return {label: profile._asdict()[label] for label in labels}, 200

def make_connection_request(session, data, user):
    target_username = data.get('username')
    if target_username == None:
        return {'error': 'Missing username.'}, 400

    if user[1] == target_username:
        return {'error': 'You cannot connect with yourself.'}, 400

    target = session.query(Users.id).filter(Users.username == target_username).one_or_none()
    if target is None:
        return {'error': 'User not found.'}, 404

    user_id = user[0]

    existing_connections = session.query(Connections).filter(
            ((Connections.user_id == user_id) & (Connections.connection_id == target.id))
            | ((Connections.user_id == target.id) & (Connections.connection_id == user_id))
        ).count()
    if existing_connections > 0:
        return {'error':
            'Either you are already following each other or one of you has an open connection request to the other.'
        }, 400

    session.add(Connections(user_id=user_id, connection_id=target.id, request_status="pending"))
    session.commit()

    return {'message': f'Connections request sent to {target_username}'}, 200

def pending_requests(session, user):
    user_id = user[0]
    
    pending_connection_requests = session.query(Users.username, Users.firstname, Users.lastname) \
        .join(Connections, Users.id == Connections.user_id) \
        .filter(Connections.connection_id == user_id, Connections.request_status == "pending") \
        .all()

    return [
        {label: request_sender._asdict()[label] for label in ['username', 'firstname', 'lastname']}
        for request_sender in pending_connection_requests
    ], 200

def accept_requests(session, data, user):
    users_to_accept = data.get('users-to-accept', [])
    users_to_deny = data.get('users-to-deny', [])

    user_id = user[0]

    accepted, denied, ignored = [], [], []

    for username in users_to_accept + users_to_deny:
        username = username['username']

        connection_request = session.query(Connections) \
            .join(Users, Connections.user_id == Users.id) \
            .filter((Users.username == username) &
                (Connections.connection_id == user_id) &
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

    return { 'accepted': accepted, 'denied': denied, 'ignored': ignored }, 200

def connections(session, user):
    user_id = user[0]

    connections = (
        session.query(Users.username, Users.firstname, Users.lastname)
        .join(Connections, ((Users.id == Connections.user_id) & (Connections.connection_id == user_id)) |
            ((Users.id == Connections.connection_id) & (Connections.user_id == user_id)))
        .filter(Connections.request_status == 'accepted')
        .all()
    )

    return [
        {label: connection._asdict()[label] for label in ['username', 'firstname', 'lastname']}
        for connection in connections
    ], 200

def disconnect(session, data, user):
    user_id = user[0]
    
    username_to_disconnect = data.get('username')
    if username_to_disconnect == None:
        return { 'error': 'FORMAT: { \'username\': username }'}, 400

    connection = session.query(Connections) \
        .join(Users, Connections.user_id == Users.id) \
        .filter((Users.username == username_to_disconnect) & \
            ((Connections.user_id == user_id) | (Connections.connection_id == user_id))) \
        .one_or_none()

    if connection is None:
        return {'error': f'you are not connected with {username_to_disconnect}.'}, 400

    session.delete(connection)
    session.commit()
    return {'success': f'successfully disconnected from {username_to_disconnect}'}, 200

def post_job(session, data, user):
    fields = ['title', 'description', 'employer', 'location', 'salary']
    if set(data.keys()) != set(fields):
        return {'error': 'Missing data, all fields are required.'}, 400

    if session.query(JobPostings).count() >= 5:
        return { 'error': 'Limit of five job postings has been reached' }, 400

    user_id = user[0]
    session.add(JobPostings(**{field: data[field] for field in fields}, user_id=user_id))
    session.commit()

    return {'message': 'Job posting created successfully.'}, 200

def get_job_postings(session):
    fields = ['title', 'description', 'employer', 'location', 'salary']
    postings = session.query(*[getattr(JobPostings, field) for field in fields], Users.username) \
        .join(Users, JobPostings.user_id == Users.id).all()

    return [{field: posting[i] for i, field in
        enumerate(['title', 'description', 'employer', 'location', 'salary', 'username'])}
        for posting in postings], 200

def get_user_preferences(session, user):
    user_id = user[0]

    label = [
        'email_notifications_enabled',
        'sms_notifications_enabled',
        'targeted_advertising_enabled',
        'language'
    ]
    preferences = session.query(*[getattr(UserPreferences, label) for label in labels]) \
        .filter(UserPreferences.user_id == user_id).one_or_none()

    if preferences is None:
        return {'error': 'Preferences not found'}, 404

    return {label: getattr(preferences, label) for label in labels}, 200

def set_user_preferences(session, data, user):
    user_id = user[0]

    if len(data) != 1:
        return {'error': 'FORMAT: { field: value }'}, 400
    field, value = list(data.items())[0]
    if field not in ['email_notifications_enabled',
        'sms_notifications_enabled',
        'targeted_advertising_enabled',
        'language']:
        return {'error': f'Invalid field: {field}'}

    preferences = session.query(UserPreferences) \
        .filter(UserPreferences.user_id == user_id).one_or_none()
    setattr(preferences, field, value)
    session.commit()

    return {'message': 'Preferences updated successfully.'}, 200

get_requests = {
    '/list-users': list_users,
    '/profile': get_profile,
    '/pending-requests': pending_requests,
    '/connections': connections,
    '/job-postings': get_job_postings,
    '/user-preferences': get_user_preferences
}

post_requests = {
    '/lookup-user': lookup_user,
    '/login': log_in,
    '/add-user': add_user,
    '/make-connection-request': make_connection_request,
    '/accept-requests': accept_requests,
    '/disconnect': disconnect,
    '/post-job': post_job,
    '/set-user-preferences': set_user_preferences
}