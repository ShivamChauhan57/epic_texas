import datetime
from pathlib import Path
import time
import jwt

def list_users(conn):
    cursor = conn.cursor()
    cursor.execute('SELECT username, firstname, lastname FROM users')
    users = cursor.fetchall()

    return [{label: user[i] for i, label in enumerate(['username', 'firstname', 'lastname'])} for user in users], 200

def lookup_user(conn, data):
    try:
        firstname, lastname = tuple(data[label] for label in ['firstname', 'lastname'])
    except KeyError:
        return {'error': 'Missing data.'}, 400

    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users WHERE firstname=? AND lastname=?', (firstname, lastname))
    matches = cursor.fetchone()[0]
    
    return { 'matches': matches }, 200

def log_in(conn, data):
    try:
        username, passwordHash = tuple(data[label] for label in ['username', 'passwordHash'])
    except KeyError:
        return {'error': 'Missing data, both username and password are required.'}, 400

    cursor = conn.cursor()
    cursor.execute("SELECT id, username, passwordHash FROM users WHERE username=?", (username,))
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
    try:
        username, firstname, lastname, passwordHash = tuple(data[label] for label in ['username', 'firstname', 'lastname', 'passwordHash'])
    except KeyError:
        return {'error': 'Missing data, all fields are required.'}, 400

    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, firstname, lastname, passwordHash) VALUES (?, ?, ?, ?)",
                    (username, firstname, lastname, passwordHash))
        conn.commit()
        
        # Retrieve the new user's id
        user_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        # This error will be raised if the username is not unique
        return {'error': 'The username you chose has already been taken.'}, 400

    response = {'id': user_id, 'username': username, 'firstname': firstname, 'lastname': lastname}

    return response, 200

def get_profile(conn, user):
    user_id = user[0]

    cursor = conn.cursor()
    cursor.execute('SELECT username, firstname, lastname FROM users WHERE id = ?', (user_id,))
    profile = cursor.fetchone()

    return {label: profile[i] for i, label in enumerate(['username', 'firstname', 'lastname'])}, 200

def follow(conn, data, user):
    target_username = data.get('username')

    if not target_username:
        return {'error': 'Missing username.'}, 400

    if user[1] == target_username:
        return {'error': 'You cannot follow yourself.'}, 400

    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username=?", (target_username,))
    target = cursor.fetchone()

    if not target:
        return {'error': 'User not found.'}, 404

    target_id = target[0]
    user_id = user[0]
    
    try:
        cursor.execute("INSERT INTO followers (user_id, follower_id) VALUES (?, ?)", (target_id, user_id))
        conn.commit()
    except sqlite3.IntegrityError:
        return {'error': 'You are already following this user.'}, 400

    return {'message': f'You are now following {target_username}'}, 200

def get_followers(conn, user):
    user_id = user[0] # get the user_id from the authenticated user tuple
    
    cursor = conn.cursor()
    cursor.execute("SELECT u.username, u.firstname, u.lastname FROM users u JOIN followers f ON u.id = f.follower_id WHERE f.user_id = ?", (user_id,))
    followers = cursor.fetchall()

    # return [follower[0] for follower in followers], 200
    return [{label: follower[i] for i, label in enumerate(['username', 'firstname', 'lastname'])} for follower in followers], 200

def post_job(conn, data, user):
    try:
        title, description, employer, location, salary = tuple(data[label] for label in ['title', 'description', 'employer', 'location', 'salary'])
    except KeyError:
        return {'error': 'Missing data, all fields are required.'}, 400

    user_id = user[0]
    cursor = conn.cursor()
    cursor.execute("INSERT INTO job_postings (title, description, employer, location, salary, user_id) VALUES (?, ?, ?, ?, ?, ?)", (title, description, employer, location, salary, user_id))
    conn.commit()

    return {'message': 'Job posting created successfully.'}, 200

def get_job_postings(conn, user):
    cursor = conn.cursor()
    cursor.execute("""SELECT jp.title, jp.description, jp.employer, jp.location, jp.salary, u.username
                        FROM job_postings AS jp JOIN users AS u
                        WHERE jp.user_id = u.id""")
    postings = cursor.fetchall()

    return [{field: posting[i] for i, field in enumerate(['title', 'description', 'employer', 'location', 'salary', 'username'])} for posting in postings], 200

get_requests = {
    '/list-users': list_users,
    '/profile': get_profile,
    '/followers': get_followers,
    '/job-postings': get_job_postings
}

post_requests = {
    '/lookup-user': lookup_user,
    '/login': log_in,
    '/add-user': add_user,
    '/follow': follow,
    '/post-job': post_job
}