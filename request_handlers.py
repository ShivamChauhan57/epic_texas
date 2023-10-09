import datetime
from pathlib import Path
import time
import jwt
import sqlite3

def list_users(conn):
    cursor = conn.cursor()
    cursor.execute('SELECT username, firstname, lastname FROM users')
    users = cursor.fetchall()

    return [{label: user[i] for i, label in enumerate(['username', 'firstname', 'lastname'])} for user in users], 200

def lookup_user(conn, data):
    fields = ['firstname', 'lastname', 'university', 'major']
    if any(field not in fields for field in data):
        return {'error': 'Invalid fields.'}, 400
    fields = list(data.keys())

    cursor = conn.cursor()
    cursor.execute('SELECT username, firstname, lastname FROM users WHERE ' + ' AND '.join(f'{field}=?' for field in fields),
        tuple(data[field] for field in fields))
    matches = cursor.fetchall()

    return { 'matches': [{
            field: user[i] for i, field in enumerate(['username', 'firstname', 'lastname'])
        } for user in matches] }, 200

def log_in(conn, data):
    try:
        username, passwordHash = tuple(data[label] for label in ['username', 'passwordHash'])
    except KeyError:
        return {'error': 'Missing data, both username and password are required.'}, 400

    cursor = conn.cursor()
    cursor.execute('SELECT id, username, passwordHash FROM users WHERE username=?', (username,))
    user = cursor.fetchone()

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

def add_user(conn, data):
    fields = ['username', 'firstname', 'lastname', 'university', 'major', 'passwordHash']
    if set(data.keys()) != set(fields):
        return {'error': 'Invalid fields.'}, 400

    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    num_users = cursor.fetchone()[0]
    if num_users >= 10:
        return { 'error': 'Limit of ten users has been reached' }, 400

    try:
        cursor.execute(f'INSERT INTO users ({", ".join(fields)}) VALUES ({", ".join("?"*len(fields))})',
                tuple(data[field] for field in fields))
        conn.commit()

        # Retrieve the new user's id
        user_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        # This error will be raised if the username is not unique
        return {'error': 'The username you chose has already been taken.'}, 400

    cursor.execute('''INSERT INTO user_preferences
        (user_id, email_notifications_enabled, sms_notifications_enabled, targeted_advertising_enabled, language)
        VALUES (?, ?, ?, ?, ?)''', (user_id, True, True, True, 'english'))
    conn.commit()

    return { 'success': 'User successfully added' }, 200

def get_profile(conn, user):
    user_id = user[0]

    cursor = conn.cursor()
    cursor.execute('SELECT username, firstname, lastname FROM users WHERE id = ?', (user_id,))
    profile = cursor.fetchone()

    return {label: profile[i] for i, label in enumerate(['username', 'firstname', 'lastname'])}, 200

def make_connection_request(conn, data, user):
    target_username = data.get('username')
    if target_username == None:
        return {'error': 'Missing username.'}, 400

    if user[1] == target_username:
        return {'error': 'You cannot connect with yourself.'}, 400

    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE username=?', (target_username,))
    target = cursor.fetchone()
    if not target:
        return {'error': 'User not found.'}, 404

    target_id = target[0]
    user_id = user[0]

    cursor.execute('''SELECT COUNT(*) FROM connections
        WHERE (user_id = ? AND connection_id = ?)
        OR (user_id = ? AND connection_id = ?)''', (user_id, target_id, target_id, user_id))
    matches = cursor.fetchone()[0]
    if matches > 0:
        return { 'error': 'Either you are already following each other or one of you has an open connection request to the other.' }, 400

    cursor.execute('INSERT INTO connections (user_id, connection_id, request_status) VALUES (?, ?, "pending")', (user_id, target_id))
    conn.commit()

    return {'message': f'Connection request sent to {target_username}'}, 200

def pending_requests(conn, user):
    user_id = user[0]
    
    cursor = conn.cursor()
    cursor.execute('''SELECT u.username, u.firstname, u.lastname
        FROM users u JOIN connections c ON u.id = c.user_id
        WHERE c.connection_id = ? AND c.request_status = "pending"''', (user_id,))
    pending_connection_requests = cursor.fetchall()

    return [{label: request_sender[i] for i, label in
        enumerate(['username', 'firstname', 'lastname'])} for request_sender in pending_connection_requests], 200

def accept_requests(conn, data, user):
    users_to_accept = data.get('users-to-accept', [])
    users_to_deny = data.get('users-to-deny', [])

    user_id = user[0]

    accepted, denied, ignored = [], [], []

    cursor = conn.cursor()
    conn.execute('BEGIN TRANSACTION')
    try:
        for username in users_to_accept + users_to_deny:
            username = username['username']

            cursor.execute('''SELECT u.id
                FROM connections c JOIN users u ON c.user_id = u.id
                WHERE u.username = ? AND c.connection_id = ? AND c.request_status = "pending"''',
                (username, user_id))
            request_sender_id = cursor.fetchone()
            if request_sender_id == None:
                ignored.append({ 'username': username })
                continue
            else:
                request_sender_id = request_sender_id[0]

            if username in [user['username'] for user in users_to_accept]:
                cursor.execute('''UPDATE connections SET request_status = "accepted"
                    WHERE user_id = ? AND connection_id = ?''', (request_sender_id, user_id))
                accepted.append({ 'username': username })
            elif username in [user['username'] for user in users_to_deny]:
                cursor.execute('''DELETE FROM connections
                    WHERE user_id = ? AND connection_id = ?''', (request_sender_id, user_id))
                denied.append({ 'username': username })
            else:
                raise Exception('There is a bug in this part of code.')

        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
    except Exception as e:
        conn.rollback()
        raise e

    return { 'accepted': accepted, 'denied': denied, 'ignored': ignored }, 200

def connections(conn, user):
    user_id = user[0]
    
    cursor = conn.cursor()
    cursor.execute('''SELECT u.username, u.firstname, u.lastname
        FROM users u JOIN connections c ON (
            (u.id = c.user_id AND c.connection_id = ?)
            OR (u.id = c.connection_id AND c.user_id = ?)
        ) WHERE c.request_status = "accepted"''', (user_id, user_id))
    pending_connection_requests = cursor.fetchall()

    return [{label: request_sender[i] for i, label in
        enumerate(['username', 'firstname', 'lastname'])} for request_sender in pending_connection_requests], 200

def disconnect(conn, data, user):
    user_id = user[0]
    
    username_to_disconnect = data.get('username')
    if username_to_disconnect == None:
        return { 'error': 'FORMAT: { \'username\': username }'}, 400

    cursor = conn.cursor()
    cursor.execute('''SELECT u.id
        FROM connections c JOIN users u ON c.user_id = u.id
        WHERE (c.user_id = ? OR c.connection_id = ?)
        AND u.username = ? AND c.request_status = "accepted"''',
        (user_id, user_id, username_to_disconnect))
    connection_id = cursor.fetchall()
    if len(connection_id) == 0:
        return { 'error': f'you are not connected with {username_to_disconnect}.' }, 400
    else:
        connection_id = connection_id[0][0]
        print(connection_id)

    cursor.execute('''DELETE FROM connections
        WHERE user_id = ? AND connection_id = ?''', (connection_id, user_id))
    return { 'success': f'successfully disconnected from {username_to_disconnect}' }, 200

def post_job(conn, data, user):
    try:
        title, description, employer, location, salary = tuple(data[label] for label in ['title', 'description', 'employer', 'location', 'salary'])
    except KeyError:
        return {'error': 'Missing data, all fields are required.'}, 400

    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM job_postings')
    num_job_postings = cursor.fetchone()[0]
    if num_job_postings >= 5:
        return { 'error': 'Limit of five job postings has been reached' }, 400

    user_id = user[0]
    cursor.execute('INSERT INTO job_postings (title, description, employer, location, salary, user_id) VALUES (?, ?, ?, ?, ?, ?)',
        (title, description, employer, location, salary, user_id))
    conn.commit()

    return {'message': 'Job posting created successfully.'}, 200

def get_job_postings(conn):
    cursor = conn.cursor()
    cursor.execute("""SELECT jp.title, jp.description, jp.employer, jp.location, jp.salary, u.username
                        FROM job_postings AS jp JOIN users AS u
                        WHERE jp.user_id = u.id""")
    postings = cursor.fetchall()

    return [{field: posting[i] for i, field in enumerate(['title', 'description', 'employer', 'location', 'salary', 'username'])} for posting in postings], 200

def get_user_preferences(conn, user):
    user_id = user[0]

    cursor = conn.cursor()
    cursor.execute('SELECT email_notifications_enabled, sms_notifications_enabled, targeted_advertising_enabled, language FROM user_preferences WHERE user_id = ?', (user_id,))
    preferences = cursor.fetchone()

    if preferences is None:
        return {'error': 'Preferences not found'}, 404

    return {label: preferences[i] for i, label in enumerate(['email_notifications_enabled', 'sms_notifications_enabled', 'targeted_advertising_enabled', 'language'])}, 200

def set_user_preferences(conn, data, user):
    user_id = user[0]

    if len(data) != 1:
        return {'error': 'FORMAT: { field: value }'}, 400
    field, value = list(data.items())[0]
    if field not in ['email_notifications_enabled',
        'sms_notifications_enabled',
        'targeted_advertising_enabled',
        'language']:
        return {'error': f'Invalid field: {field}'}

    cursor = conn.cursor()
    cursor.execute(f'UPDATE user_preferences SET {field} = ? WHERE user_id = ?', (value, user_id))
    conn.commit()

    if cursor.rowcount == 0:
        return {'error': 'Failed to update preferences.'}, 500

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