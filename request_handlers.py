from flask import request, g, jsonify, Blueprint
from datetime import date, datetime
from pathlib import Path
import time
import jwt
import sqlite3
from sqlalchemy import func, literal_column, case
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from models import Users, Profiles, Experience, Connections, JobPostings, JobApplications, JobsMarked, UserPreferences, Conversations, Messages, Notifications

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
    query = g.session.query(*[getattr(Users, label) for label in labels]) \
        .join(Profiles, Users.id == Profiles.user_id)
    for field in fields:
        if field in ['firstname', 'lastname']:
            query = query.filter(getattr(Users, field) == data[field])
        elif field in ['university', 'major']:
            query = query.filter(getattr(Profiles, field) == data[field])

    matches = query.all()

    return jsonify({'matches': [{label: user._asdict()[label] for label in labels} for user in matches]}), 200

@handlers.route('/login', methods=['POST'])
def log_in():
    try:
        username, passwordHash = tuple(request.get_json()[label] for label in ['username', 'passwordHash'])
    except KeyError:
        return jsonify({'error': 'Missing data, both username and password are required.'}), 400

    user = g.session.query(Users.id, Users.username, Users.passwordHash) \
        .filter(Users.username == username) \
        .one_or_none()

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

    fields = ['username', 'firstname', 'lastname', 'passwordHash', 'tier', 'university', 'major']
    if set(data.keys()) != set(fields) or data['tier'] not in ['standard', 'plus']:
        return jsonify({'error': 'Invalid fields.'}), 400

    if session.query(Users).count() >= 10:
        return jsonify({'error': 'Limit of ten users has been reached'}), 400

    for field_to_capitalize in fields[-2:]:
        if data[field_to_capitalize].strip() == '':
            return jsonify({'error': f'Invalid {field_to_capitalize}.'}), 400
        data[field_to_capitalize] = ' '.join(word[0].upper() + word[1:]
            for word in data[field_to_capitalize].strip().split(' '))

    new_user = Users(**{field: data[field] for field in fields[:-2]})
    session.add(new_user)
    try:
        session.flush()     # this synchronizes the session with the above change without committing it
    except IntegrityError:
        return jsonify({'error': 'The username you chose has already been taken.'}), 400

    session.add(Profiles(user_id=new_user.id, **{field: data[field] for field in fields[-2:]}))
    session.add(UserPreferences(user_id=new_user.id, email_notifications_enabled=True,
        sms_notifications_enabled=True, targeted_advertising_enabled=True, language='english'))
    
    for user in session.query(Users.id).all():
        if user.id == new_user.id:
            continue

        session.add(Notifications(user_id=user.id, menu='main', content=f'{data["firstname"]} {data["lastname"]} has joined InCollege.'))
    session.commit()

    return jsonify({'success': 'User successfully added'}), 200

@authenticated_handlers.route('/profile', methods=['GET'])
def get_profile():
    labels = ['username', 'firstname', 'lastname', 'tier', 'bio', 'university', 'major', 'years_attended']
    profile = g.session.query(*[getattr(Users if i < 4 else Profiles, label) for i, label in enumerate(labels)]) \
        .join(Profiles, Users.id == Profiles.user_id) \
        .filter(Users.id == g.user_id) \
        .one_or_none()

    return jsonify({label: profile._asdict()[label] for label in labels}), 200

@authenticated_handlers.route('/friend-profile', methods=['POST'])
def get_friend_profile():
    friend_id = request.get_json().get('id')
    if friend_id is None:
        return jsonify({'error': 'FORMAT: { "id": friend_id }'}), 400

    labels = ['bio', 'university', 'major', 'years_attended']
    profile = g.session.query(*[getattr(Profiles, label) for label in labels]) \
        .join(Connections, ((Profiles.user_id == Connections.user_id) & (Connections.connection_id == g.user_id)) |
            ((Profiles.user_id == Connections.connection_id) & (Connections.user_id == g.user_id))) \
        .filter(Profiles.user_id == friend_id) \
        .one_or_none()

    if friend_id is None:
        return jsonify({'error': f'You are not connected to the user with id {friend_id}.'}), 400

    return jsonify({label: profile._asdict()[label] for label in labels}), 200

@authenticated_handlers.route('/edit-profile', methods=['POST'])
def edit_profile():
    data = request.get_json()

    if len(data) != 1:
        return jsonify({'error': 'FORMAT: { field: value }'}), 400
    field, value = list(data.items())[0]
    match field:
        case 'bio':
            pass
        case 'university' | 'major':
            if value.strip() == '':
                return jsonify({'error': f'Invalid {field}.'}), 400
            value = ' '.join(word[0].upper() + word[1:] for word in value.strip().split(' '))
        case 'years_attended':
            if not isinstance(data[field], int):
                return jsonify({'error': f'Invalid years_attended: {value}'}), 400
        case _:
            return jsonify({'error': f'Invalid field: {field}'}), 400

    profile = g.session.query(Profiles) \
        .filter(Profiles.user_id == g.user_id) \
        .one_or_none()

    setattr(profile, field, value)
    g.session.commit()

    return jsonify({'message': 'Successfully editted profile.'}), 200

@authenticated_handlers.route('/job-history', methods=['GET'])
def get_job_history():
    labels = ['id', 'title', 'employer', 'start_date', 'end_date', 'location', 'description']
    job_history = g.session.query(*[getattr(Experience, label) for label in labels]) \
        .filter(Experience.user_id == g.user_id) \
        .all()

    return jsonify([{label: job._asdict()[label] for label in labels} for job in job_history]), 200

@authenticated_handlers.route('/add-job-history', methods=['POST'])
def add_job_history():
    session = g.session
    data = request.get_json()

    if session.query(Experience).filter(Experience.user_id == g.user_id).count() >= 3:
        return jsonify({'error': 'Limit of three jobs has been reached' }), 400

    labels = ['title', 'employer', 'start_date', 'end_date', 'location', 'description']     # the first four fields are required
    invalid_field_specified = any(field not in labels for field in data.keys())
    required_fields_specified = all(field in data.keys() for field in labels[:4])
    if invalid_field_specified or not required_fields_specified:
        return jsonify({'error': 'Invalid fields.'}), 400

    for date_label in ['start_date', 'end_date']:
        try:
            data[date_label] = datetime.strptime(data[date_label], '%m/%d/%Y').date()
        except ValueError:
            return jsonify({'error': f'Invalid {date_label}: {data[date_label]}'}), 400

    session.add(Experience(user_id=g.user_id, **data))
    session.commit()

    return jsonify({'message': 'Successfully added job history'}), 200

@authenticated_handlers.route('/edit-job-history', methods=['POST'])
def edit_job_history():
    data = request.get_json()

    if len(data) != 2 or 'id' not in data:
        return jsonify({'error': 'FORMAT: { "id": id, field: value }'}), 400
    job_id = data['id']
    field = [field for field in data.keys() if field != 'id'][0]
    if field not in ['title', 'employer', 'start_date', 'end_date', 'location', 'description']:
        return jsonify({'error': f'Invalid field: {field}'}), 400
    if field in ['start_date', 'end_date']:
        try:
            data[field] = datetime.strptime(data[field], '%m/%d/%Y').date()
        except ValueError:
            return jsonify({'error': f'Invalid {field}: {data[field]}'}), 400

    job = g.session.query(Experience) \
        .filter((Experience.user_id == g.user_id) & (Experience.id == job_id)) \
        .one_or_none()

    if job is None:
        return jsonify({'error': f'Invalid job id.'}), 400

    setattr(job, field, data[field])
    g.session.commit()

    return jsonify({'message': 'Successfully editted job history'}), 200

@authenticated_handlers.route('/remove-job-history', methods=['POST'])
def remove_job_history():
    session = g.session
    data = request.get_json()

    if len(data) != 1 or 'id' not in data:
        return jsonify({'error': 'FORMAT: { "id": id }'}), 400

    job = session.query(Experience) \
        .filter((Experience.user_id == g.user_id) & (Experience.id == data['id'])) \
        .one_or_none()

    if job is None:
        return jsonify({'error': f'Invalid job id.'}), 400

    session.delete(job)
    session.commit()

    return jsonify({'message': 'Successfully removed job.'}), 200

@authenticated_handlers.route('/make-connection-request', methods=['POST'])
def make_connection_request():
    session = g.session
    data = request.get_json()

    target_username = data.get('username')
    if target_username == None:
        return jsonify({'error': 'Missing username.'}), 400

    if g.username == target_username:
        return jsonify({'error': 'You cannot connect with yourself.'}), 400

    target = session.query(Users.id) \
        .filter(Users.username == target_username) \
        .one_or_none()
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
    labels = ['id', 'username', 'firstname', 'lastname']
    connections = g.session.query(*[getattr(Users, label) for label in labels]) \
        .join(Connections, ((Users.id == Connections.user_id) & (Connections.connection_id == g.user_id)) |
            ((Users.id == Connections.connection_id) & (Connections.user_id == g.user_id))) \
        .filter(Connections.request_status == 'accepted') \
        .all()

    return jsonify([{label:
        connection._asdict()[label] for label in labels}
        for connection in connections
    ]), 200

@authenticated_handlers.route('/disconnect', methods=['POST'])
def disconnect():
    session = g.session
    
    username_to_disconnect = request.get_json().get('username')
    if username_to_disconnect == None:
        return jsonify({ 'error': 'FORMAT: { \'username\': username }'}), 400

    connection = session.query(Connections) \
        .join(Users, (Connections.user_id == Users.id) | (Connections.connection_id == Users.id)) \
        .filter((Users.username == username_to_disconnect) & \
            ((Connections.user_id == g.user_id) | (Connections.connection_id == g.user_id)) & \
            (Connections.request_status == 'accepted')) \
        .one_or_none()

    if connection is None:
        return jsonify({'error': f'you are not connected with {username_to_disconnect}.'}), 400

    session.delete(connection)
    session.commit()
    return jsonify({'success': f'successfully disconnected from {username_to_disconnect}'}), 200

@authenticated_handlers.route('/post-job', methods=['POST'])
def post_job():
    session = g.session
    data = request.get_json()

    fields = ['title', 'description', 'employer', 'location', 'salary']
    if set(data.keys()) != set(fields):
        return jsonify({'error': 'Missing data, all fields are required.'}), 400

    if session.query(JobPostings).count() >= 10:
        return jsonify({'error': 'Limit of ten job postings has been reached' }), 400

    session.add(JobPostings(**{field: data[field] for field in fields}, user_id=g.user_id, deleted=False))
    for user in session.query(Users.id).all():
        if user.id == g.user_id:
            continue

        session.add(Notifications(user_id=user.id, menu='main', content=f'A new job "{data["title"]}" has been posted'))
        session.add(Notifications(user_id=user.id, menu='job search/internship', content=f'A new job "{data["title"]}" has been posted'))
    session.commit()

    return jsonify({'message': 'Job posting created successfully.'}), 200

@handlers.route('/job-postings', methods=['GET'])
def get_job_postings():
    fields = ['id', 'title', 'description', 'employer', 'location', 'salary']
    postings = g.session.query(*[getattr(JobPostings, field) for field in fields], Users.username) \
        .filter(JobPostings.deleted == False) \
        .join(Users, JobPostings.user_id == Users.id).all()

    return jsonify([{field: posting[i] for i, field in
        enumerate(fields + ['username'])}
        for posting in postings]), 200

@authenticated_handlers.route('/jobs-posted', methods=['GET'])
def get_jobs_posted():
    fields = ['id', 'title', 'description', 'employer', 'location', 'salary']
    postings = g.session.query(*[getattr(JobPostings, field) for field in fields]) \
        .filter((JobPostings.deleted == False) & (JobPostings.user_id == g.user_id)) \
        .all()

    return jsonify([{field: posting[i] for i, field in enumerate(fields)}
        for posting in postings]), 200

@authenticated_handlers.route('/delete-job', methods=['POST'])
def delete_job():
    session = g.session
    data = request.get_json()

    if list(data.keys()) != ['job_id']:
        return jsonify({'error': 'FORMAT: { "job_id": job_id }'}), 400
    else:
        job_id = data['job_id']

    job_to_delete = session.query(JobPostings) \
        .filter((JobPostings.id == job_id) & (JobPostings.user_id == g.user_id)) \
        .one_or_none()
    if job_to_delete is None:
        return jsonify({'error': 'Job either does not exist or was not posted by you.' }), 404

    job_to_delete.deleted = True
    session.commit()

    return jsonify({'message': 'Job posting deleted successfully.'}), 200

@authenticated_handlers.route('/user-preferences', methods=['GET'])
def get_user_preferences():
    labels = [
        'email_notifications_enabled',
        'sms_notifications_enabled',
        'targeted_advertising_enabled',
        'language'
    ]
    preferences = g.session.query(*[getattr(UserPreferences, label) for label in labels]) \
        .filter(UserPreferences.user_id == g.user_id) \
        .one_or_none()

    if preferences is None:
        return jsonify({'error': 'Preferences not found'}), 404

    return jsonify({label: getattr(preferences, label) for label in labels}), 200

@authenticated_handlers.route('/set-user-preferences', methods=['POST'])
def set_user_preferences():
    session = g.session
    data = request.get_json()

    if len(data) != 1:
        return jsonify({'error': 'FORMAT: { field: value }'}), 400
    field, value = list(data.items())[0]
    if field not in [
            'email_notifications_enabled',
            'sms_notifications_enabled',
            'targeted_advertising_enabled',
            'language'
        ]:
        return jsonify({'error': f'Invalid field: {field}'}), 400

    if not ((field == 'language' and value in ['english', 'spanish']) or isinstance(value, bool)):
        return jsonify({'error': f'Invalid {field}.'}), 400

    preferences = session.query(UserPreferences) \
        .filter(UserPreferences.user_id == g.user_id) \
        .one_or_none()
    setattr(preferences, field, value)
    session.commit()

    return jsonify({'message': 'Preferences updated successfully.'}), 200

@authenticated_handlers.route('/apply', methods=['POST'])
def apply():
    session = g.session
    data = request.get_json()

    labels = ['job_id', 'graduation_date', 'ideal_start_date', 'cover_letter']
    if set(labels) != set(data.keys()):
        return jsonify({'error': 'Invalid fields.'}), 400

    for date_label in ['graduation_date', 'ideal_start_date']:
        try:
            data[date_label] = datetime.strptime(data[date_label], '%m/%d/%Y').date()
        except ValueError:
            return jsonify({'error': f'Invalid {date_label}: {data[date_label]}'}), 400

    if session.query(JobPostings).filter(
            (JobPostings.id == data['job_id']) & \
            (JobPostings.user_id != g.user_id)) \
        .one_or_none() is None:
        return jsonify({'error': f'Either job doesn\'t exist or you are its poster.'}), 404

    if session.query(JobApplications).filter(
            (JobApplications.user_id == g.user_id) & \
            (JobApplications.job_id == data['job_id'])) \
        .count() > 0:
        return jsonify({'error': f'You have already applied to this job.'}), 400

    session.add(JobApplications(user_id=g.user_id, **data, application_date=date.today()))
    session.commit()

    return jsonify({'message': 'Successfully applied to job'}), 200

@authenticated_handlers.route('/applications', methods=['GET'])
def applications():
    session = g.session

    job_applications = session.query(JobApplications.job_id, JobApplications.application_date, JobPostings.title) \
        .join(JobPostings, JobApplications.job_id == JobPostings.id) \
        .filter((JobPostings.deleted == False) & (JobApplications.user_id == g.user_id)) \
        .all()

    return jsonify([{
            'job_id': application.job_id,
            'title': application.title,
            'application-date': str(application.application_date)
        } for application in job_applications]), 200

@authenticated_handlers.route('/expired-applications', methods=['GET'])
def expired_applications():
    session = g.session

    job_applications = session.query(JobPostings.id, JobPostings.title) \
        .join(JobApplications, JobPostings.id == JobApplications.job_id) \
        .filter((JobPostings.deleted == True) & (JobApplications.user_id == g.user_id)) \
        .all()

    job_applications_to_delete = session.query(JobApplications) \
        .join(JobPostings, JobApplications.job_id == JobPostings.id) \
        .filter((JobPostings.deleted == True) & (JobApplications.user_id == g.user_id)) \
        .all()

    for application in job_applications_to_delete:
        session.delete(application)

    session.commit()

    return jsonify([{
            'job_id': application.id,
            'title': application.title
        } for application in job_applications]), 200

@authenticated_handlers.route('/mark', methods=['POST'])
def mark():
    session = g.session
    data = request.get_json()

    if list(data.keys()) != ['job_id']:
        return jsonify({'error': 'FORMAT: { "job_id": job_id }'}), 400

    if session.query(JobPostings).filter(JobPostings.id == data['job_id']).one_or_none() is None:
        return jsonify({'error': f'Job doesn\'t exist.'}), 404

    session.add(JobsMarked(user_id=g.user_id, job_id=data['job_id']))
    session.commit()

    return jsonify({'message': 'Job marked successfully.'}), 200

@authenticated_handlers.route('/marked', methods=['GET'])
def marked():
    session = g.session

    jobs_marked = session.query(JobsMarked.job_id).filter(JobsMarked.user_id == g.user_id).all()

    return jsonify([job.job_id for job in jobs_marked]), 200

@authenticated_handlers.route('/unmark', methods=['POST'])
def unmark():
    session = g.session
    data = request.get_json()

    if list(data.keys()) != ['job_id']:
        return jsonify({'error': 'FORMAT: { "job_id": job_id }'}), 400

    job_mark = session.query(JobsMarked).filter( \
            (JobsMarked.user_id == g.user_id) & \
            (JobsMarked.job_id == data['job_id']) \
        ).one_or_none()
    if job_mark is None:
        return jsonify({'error': f'Job isn\'t marked.'}), 404

    session.delete(job_mark)
    session.commit()

    return jsonify({'message': 'Job unmarked successfully.'}), 200

@authenticated_handlers.route('/unread-messages', methods=['GET'])
def unread_messages():
    session = g.session

    num_unread_attr = func.sum(
            case(((Messages.read==False) & \
                (Messages.sender != g.user_id), 1), else_=0)
        ).label('num_unread')       # only count when 
    conversations = session.query(Users.username, Users.firstname, Users.lastname,
            Conversations.id, num_unread_attr) \
        .join(Conversations, (Users.id == Conversations.user1) | (Users.id == Conversations.user2)) \
        .join(Messages, Conversations.id == Messages.conversation) \
        .filter(Users.id != g.user_id,
            (Conversations.user1 == g.user_id) | (Conversations.user2 == g.user_id)) \
        .group_by(Users.username, Users.firstname, Users.lastname, Conversations.id) \
        .all()

    return jsonify([{
        'username': conversation.username,
        'firstname': conversation.firstname,
        'lastname': conversation.lastname,
        'num_unread': conversation.num_unread,
    } for conversation in conversations]), 200

@authenticated_handlers.route('/messages', methods=['POST'])
def _messages():
    session = g.session
    data = request.get_json()

    if list(data.keys()) != ['username']:
        return jsonify({'error': 'FORMAT: { "username": username }'}), 400

    target_user = session.query(Users.id) \
        .filter(Users.username == data['username']) \
        .one_or_none()

    if target_user is None:
        return jsonify({'error': f'{data["username"]} not found.'}), 404
    else:
        target_user_id = target_user.id

    conversation = session.query(Conversations) \
        .filter(((Conversations.user1 == g.user_id) & (Conversations.user2 == target_user_id)) | \
            ((Conversations.user1 == target_user_id) & (Conversations.user2 == g.user_id))) \
        .one_or_none()

    if conversation is None:
        return jsonify({'error': 'Conversation not found.'}), 404

    messages = session.query(Messages.time, Messages.content, Messages.read,
            Users.firstname) \
        .join(Users, Messages.sender == Users.id) \
        .filter(Messages.conversation == conversation.id) \
        .all()

    messages_to_read = session.query(Messages) \
        .filter(Messages.conversation == conversation.id, Messages.sender != g.user_id) \
        .all()

    for message in messages_to_read:
        message.read = True

    session.commit()

    return jsonify([{
        'time': message.time,
        'content': message.content,
        'read': message.read,
        'firstname': message.firstname
    } for message in messages]), 200

@authenticated_handlers.route('/message', methods=['POST'])
def message():
    session = g.session
    data = request.get_json()

    if list(data.keys()) != ['username', 'content']:
        return jsonify({'error': 'FORMAT: { "username": username }'}), 400

    target_user = session.query(Users.id) \
        .filter(Users.username == data['username']) \
        .one_or_none()

    if target_user is None:
        return jsonify({'error': f'{data["username"]} not found.'}), 404
    else:
        target_user_id = target_user.id

    conversation = session.query(Conversations.id) \
        .filter(((Conversations.user1 == g.user_id) & (Conversations.user2 == target_user_id)) | \
            ((Conversations.user1 == target_user_id) & (Conversations.user2 == g.user_id))) \
        .one_or_none()

    if conversation is None:
        return jsonify({'error': 'Conversation does not exist.'}), 404

    session.add(Messages(time=datetime.now(), conversation=conversation.id, content=data['content'], read=False, sender=g.user_id))
    session.commit()
    return jsonify({'success': f'Successfully messaged {data["username"]}.'}), 200

@authenticated_handlers.route('/start-conversation', methods=['POST'])
def start_conversation():
    session = g.session
    data = request.get_json()

    if list(data.keys()) != ['username', 'content']:
        return jsonify({'error': 'FORMAT: { "username": username, "content": content }'}), 400

    if g.username == data['username']:
        return jsonify({'error': 'You cannot DM yourself.'}), 400

    target_user = session.query(Users.id) \
        .filter(Users.username == data['username']) \
        .one_or_none()

    if target_user is None:
        return jsonify({'error': f'{data["username"]} not found.'}), 404
    else:
        target_user_id = target_user.id

    conversation = session.query(Conversations.id) \
        .filter(((Conversations.user1 == g.user_id) & (Conversations.user2 == target_user_id)) | \
            ((Conversations.user1 == target_user_id) & (Conversations.user2 == g.user_id))) \
        .one_or_none()

    if conversation is not None:
        return jsonify({'error': 'Conversation already exists.'}), 400

    connection = session.query(Connections) \
        .filter(((Connections.user_id == g.user_id) & (Connections.connection_id == target_user_id)) | \
            ((Connections.user_id == target_user_id) & (Connections.connection_id == g.user_id))) \
        .one_or_none()
    tier = session.query(Users.tier).filter(Users.id == g.user_id).one_or_none()
    if connection is None and tier.tier == 'standard':
        return jsonify({'error': 'I\'m sorry, you are not friends with that person.'}), 400

    session.add(Conversations(user1=g.user_id, user2=target_user_id))
    session.flush()
    conversation = session.query(Conversations.id) \
        .filter(((Conversations.user1 == g.user_id) & (Conversations.user2 == target_user_id)) | \
            ((Conversations.user1 == target_user_id) & (Conversations.user2 == g.user_id))) \
        .one_or_none()

    assert conversation is not None

    session.add(Messages(time=datetime.now(), conversation=conversation.id, content=data['content'], read=False, sender=g.user_id))

    session.commit()
    return jsonify({'success': f'Successfully messaged {data["username"]}.'}), 200

@authenticated_handlers.route('/delete-conversation', methods=['POST'])
def delete_conversation():
    session = g.session
    data = request.get_json()

    if list(data.keys()) != ['username']:
        return jsonify({'error': 'FORMAT: { "username": username }'}), 400

    target_user = session.query(Users.id) \
        .filter(Users.username == data['username']) \
        .one_or_none()

    if target_user is None:
        return jsonify({'error': f'{data["username"]} not found.'}), 404
    else:
        target_user_id = target_user.id

    conversation = session.query(Conversations) \
        .filter(((Conversations.user1 == g.user_id) & (Conversations.user2 == target_user_id)) | \
            ((Conversations.user1 == target_user_id) & (Conversations.user2 == g.user_id))) \
        .one_or_none()

    if conversation is None:
        return jsonify({'error': 'Conversation does not exist.'}), 400

    for message in session.query(Messages).filter(Messages.conversation == conversation.id).all():
        session.delete(message)

    session.delete(conversation)
    session.commit()
    return jsonify({'success': f'Successfully messaged {data["username"]}.'}), 200

@authenticated_handlers.route('/notifications', methods=['POST'])
def _notifications():
    session = g.session
    data = request.get_json()

    if list(data.keys()) != ['menu']:
        return jsonify({'error': 'FORMAT: { "menu": menu }'}), 400

    notifications = session.query(Notifications) \
        .filter(Notifications.user_id == g.user_id, Notifications.menu == data['menu']) \
        .all()
    response = jsonify([{'content': notification.content} for notification in notifications])

    if len(notifications) > 0:
        for notification in notifications:
            session.delete(notification)
        session.commit()

    return response, 200

@handlers.route('/error', methods=['GET'])
def error():
    assert False
