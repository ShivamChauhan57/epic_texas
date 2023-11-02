import sys
import os
import json
from pathlib import Path
import getpass
import hashlib
import requests

class InvalidInputError(Exception):
    def __init__(self, message):
        super().__init__(message)

class StatusCodeError(Exception):
    def __init__(self, message):
        super().__init__(message)

def get_field(prompt, whitespace=False, nullable=False):
    _input = input(f'{prompt}: ').strip()
    if not whitespace and any(c.isspace() for c in _input.strip()):
        raise InvalidInputError('Invalid entry, must not contain whitespace.')

    if len(_input) == 0:
        if nullable:
            return None
        else:
            raise InvalidInputError('Cannot pass an empty message to this field.')

    return _input

class Menu:
    def __init__(self, url):
        self.url = url
        self.access_token = None
        self.mode = 'log-in'

        # these values are fetched when user logs in
        self.email_notifications_enabled = None
        self.sms_notifications_enabled = None
        self.targeted_advertising_enabled = None
        self.language = None

    def main(self):
        while self.mode != 'exited':
            if self.mode == 'main':
                if not self.access_token:
                    self.change_mode('log-in')
                    continue

            self.notify()

            options, actions = tuple(zip(*self.options()))
            print('Available actions:\n{}'.format('\n'.join(f'{i + 1}: {option}' for i, option in enumerate(options))))

            try:
                choice = int(input('Enter choice (enter the index): ')) - 1
            except ValueError:
                print('Invalid response, try again.')
                continue

            if not (0 <= choice < len(actions)):
                print(f'Invalid index: {choice}')
                continue

            try:
                actions[choice]()
            except (InvalidInputError, StatusCodeError) as e:
                print(e)

            print()

    # self.options returns a list of label-action pairs
    # it doesn't return a dictionary mapping label to action because order of the entries is going to matter
    def options(self):
        options = None
        if self.mode == 'log-in':
            options = [
                ('InCollege Video', lambda: print('Video is now playing')),
                ('Log in', self.login),
                ('Sign up', self.signup),
                ('Lookup users', self.lookup_users),
                ('Discover users', self.discover_users),
                ('Useful links', lambda: self.change_mode('useful links')),
                ('InCollege Important Links', lambda: self.change_mode('incollege links')),
                ('Exit', lambda: self.change_mode('exited'))
            ]
        elif self.mode == 'main':
            options = [
                ('Create/view/edit profile', lambda: self.change_mode('profile')),
                ('Discover users', self.discover_users),
                ('Lookup users', self.lookup_users),
                ('Send connection requests', self.send_connection_request),
                ('View requests', self.consider_requests),
                ('Show my network', self.view_connections),
                ('Disconnect from a user', self.disconnect),
                ('Job search/internship', lambda: self.change_mode('job search/internship')),
                ('Useful links', lambda: self.change_mode('useful links')),
                ('InCollege Important Links', lambda: self.change_mode('incollege links')),
                ('Log out', self.logout)
            ]
        elif self.mode == 'profile':
            options = [
                ('View/edit profile', self.see_profile),
                ('View/edit job history', self.see_job_history),
                ('Go back', lambda: self.change_mode('main'))
            ]
        elif self.mode == 'job search/internship':
            options = [
                ('See job titles and apply', self.get_job_titles),
                ('See all job postings', self.get_job_postings),
                ('Post a job', self.post_job),
                ('Delete a job', self.delete_job),
                ('List applied jobs', self.applied_jobs),
                ('List jobs not yet applied to', self.not_applied_jobs),
                ('Mark a job', self.mark),
                ('Unmark a job', self.unmark),
                ('Go back', lambda: self.change_mode('main')),
            ]
        elif self.mode == 'useful links':
            options = [
                ('General', lambda: self.change_mode('general')),
                ('Browse InCollege', self.under_construction),
                ('Business Solutions', self.under_construction),
                ('Directories', self.under_construction),
                ('Go back', lambda: self.change_mode('main' if self.access_token else 'log-in'))
            ]
        elif self.mode == 'general':
            about_message = 'InCollege: Welcome to InCollege, the world\'s largest college student network with many users in many countries and territories worldwide.'
            press_message = 'InCollege Pressroom: Stay on top of the latest news, updates, and reports.'

            options = [
                ('Help Center', lambda: print('We\'re here to help')),
                ('About', lambda: print(about_message)),
                ('Press', lambda: print(press_message)),
                ('Blog', self.under_construction),
                ('Careers', self.under_construction),
                ('Developers', self.under_construction),
                ('Go back', lambda: self.change_mode('useful links'))
            ]

            if self.access_token is None:
                options = [('Sign Up', self.signup)] + options
        elif self.mode == 'incollege links':
            documents = {
                'Cookie Policy': 'cookie-policy.txt',
                'Privacy Policy': 'privacy-policy.txt',
                'Copyright Policy': 'copyright-policy.txt',
                'Copyright Notice': 'copyright-notice.txt',
                'About': 'about.txt',
                'Accessibility': 'accessibility.txt',
                'User Agreement': 'user-agreement.txt',
                'Brand Policy': 'brand-policy.txt'
            }

            options = []
            for document, textfile in documents.items():
                def print_content(textfile=textfile):
                    print(Path(os.path.join('documents', textfile)).read_text().strip())

                options.append((document, print_content))

            if self.access_token:
                options += [
                    ('Guest Controls', lambda: self.change_mode('guest controls')),
                    ('Languages', lambda: self.change_mode('languages'))
                ]

            options.append(('Go back', lambda: self.change_mode('main' if self.access_token else 'log-in')))
        elif self.mode == 'guest controls':
            self.fetch_user_preferences()
            if any(setting is None for setting in
                [self.email_notifications_enabled, self.sms_notifications_enabled, self.targeted_advertising_enabled, self.language]):
                print('Error fetching user preferences')
                return [('Go back', lambda: self.change_mode('incollege links'))]

            options = []
            for field, option, value in [
                    ('email_notifications_enabled', 'InCollege Email', self.email_notifications_enabled),
                    ('sms_notifications_enabled', 'SMS', self.sms_notifications_enabled),
                    ('targeted_advertising_enabled', 'Targeted Advertising', self.targeted_advertising_enabled)
                ]:
                options.append((f'Turn {option} {"Off" if value else "On"}',
                    lambda field=field, value=value: self.set_user_preferences(field, not value)))

            options.append(('Go back', lambda: self.change_mode('incollege links')))
        elif self.mode == 'languages':
            options = [
                ('English', lambda: self.set_user_preferences('language', 'english')),
                ('Spanish', lambda: self.set_user_preferences('language', 'spanish')),
                ('Go Back', lambda: self.change_mode('incollege links'))
            ]

        return options

    def change_mode(self, new_mode):
        self.mode = new_mode

    def under_construction(self):
        print('Under construction')

    def get(self, path, error_msg=None, authenticate=False):
        assert path.startswith('/'), f'Invalid path: {path}.'

        headers = { 'Authorization': f'Bearer {self.access_token}' } if authenticate else {}
        response = requests.get(f'{self.url}{path}', headers=headers, timeout=5)
        if error_msg is None:
            return response

        if authenticate and response.status_code == 401:
            if error_msg.endswith('.'):
                error_msg = error_msg[:-1]
            error_msg += ': permission denied. If you haven\'t logged in yet, please do so. If you have, consider doing so again.'

        if response.status_code != 200:
            raise StatusCodeError(error_msg)

        return response.json()

    def post(self, path, data, error_msg=None, authenticate=False):
        assert path.startswith('/'), f'Invalid path: {path}.'

        headers = { 'Authorization': f'Bearer {self.access_token}' } if authenticate else {}
        headers['Content-Type'] = 'application/json'
        response = requests.post(f'{self.url}{path}', data=json.dumps(data), headers=headers, timeout=5)
        if error_msg is None:
            return response

        if authenticate and response.status_code == 401:
            if error_msg.endswith('.'):
                error_msg = error_msg[:-1]
            error_msg += ': permission denied. If you haven\'t logged in yet, please do so. If you have, consider doing so again.'

        if response.status_code != 200:
            raise StatusCodeError(error_msg)

        return response.json()

    def notify(self):
        if self.mode == 'main':
            response = self.get('/pending-requests', authenticate=True)
            if response.status_code == 200 and len(response.json()) > 0:
                print('NOTIFICATION: You have pending connection requests to accept or deny.\n')
        elif self.mode == 'job search/internship':
            response = self.get('/expired-applications', authenticate=True)
            if response.status_code == 200:
                for application in response.json():
                    print(f'NOTIFICATION: You applied to "{application["title"]}", but that job posting has been deleted.\n')

    def login(self):
        username = get_field('Please enter your username')
        password_hash = hashlib.sha256(getpass.getpass('Enter your password: ').strip().encode()).hexdigest()

        self.access_token = self.post('/login', {
            'username': username,
            'passwordHash': password_hash
        }, error_msg='Login unsuccessful.')['token']
        print('Login successful.')
        self.change_mode('main')

    def logout(self):
        self.access_token = None
        self.change_mode('log-in')

    def signup(self):
        def username_exists(username):
            try:
                return any(username == user['username'] for user in self.get('/list-users').json())
            except requests.JSONDecodeError:
                return False    # signing up will be unsuccessful regardless

        def validate_password(password):
            contains_digit = any(chr(ord('0') + i) in password for i in range(10))
            contains_capital = any(chr(ord('A') + i) in password for i in range(ord('Z') - ord('A') + 1))
            contains_special = not all(c.isdigit() or 0 <= ord(c.lower()) - ord('a') < 26 or c.isspace() for c in password)

            return 8 <= len(password) <= 12 and contains_digit and contains_capital and contains_special

        data = {'username': get_field('Please enter your username')}
        if username_exists(data['username']):
            raise InvalidInputError('Username not available!')

        data['firstname'] = get_field('Enter your first name')
        data['lastname'] = get_field('Enter your last name')
        data['university'] = get_field('Enter your university', whitespace=True)
        data['major'] = get_field('Enter your subject major', whitespace=True)

        password = getpass.getpass('Enter your password: ').strip()
        if not validate_password(password):
            raise InvalidInputError('Password is not secure, should between eight and twelve characters, must contain a digit, a capital letter, and a special character.')

        if getpass.getpass('Confirm your password: ').strip() != password:
            print('Passwords don\'t match!')
            return

        data['passwordHash'] = hashlib.sha256(password.encode()).hexdigest()

        response = self.post('/add-user', data)
        if response.status_code == 200:
            print('You have successfully signed up! Please log in now.')
        else:
            if response.json() == { 'error': 'Limit of ten users has been reached' }:
                print('All permitted accounts have been created, please come back later.')
            else:
                print('Sign up unsuccessful. Please try again.')

    def see_profile(self):
        response = self.get('/profile', error_msg='Error retrieving profile info.', authenticate=True)
        labels = [
            ('username', 'username'),
            ('firstname', 'first name'),
            ('lastname', 'last name'),
            ('bio', 'bio'),
            ('university', 'university'),
            ('major', 'major'),
            ('years_attended', 'years attended')
        ]   # this is not a dictionary because order matters here
        for i, (field, label) in enumerate(labels):
            def capitalize(s):
                return s[0].upper() + s[1:]

            if response[field] is None:
                print(f'{i + 1}) {capitalize(label)}: Not yet set.')
            else:
                print(f'{i + 1}) {capitalize(label)}: {response[field]}')

        field_to_edit = input('Would you like to make any changes? If so, enter the index of the field to edit. Otherwise, simply press enter: ')
        if field_to_edit.strip() == '':
            return

        try:
            field_to_edit = labels[int(field_to_edit) - 1][0]
        except (ValueError, IndexError) as e:
            raise InvalidInputError('Invalid response, try again.') from e

        if field_to_edit in next(zip(*labels))[:3]:
            raise InvalidInputError('This field is not editable.')

        new_value = input(f'Enter the {dict(labels)[field_to_edit]}: ')
        if field_to_edit == 'years_attended':
            try:
                new_value = int(new_value)
            except ValueError as e:
                raise InvalidInputError(f'Invalid years_attended: {new_value}') from e

        self.post('/edit-profile', {field_to_edit: new_value},
            error_msg=f'Failed to update {field_to_edit} to new value.', authenticate=True)

        print(f'Successfully updated {field_to_edit}\'s value.')

    def see_job_history(self):
        response = self.get('/job-history', error_msg='Error retrieving job history.', authenticate=True)
        if len(response) == 0:
            job_add = input('Would you like to add a job? If so, enter add. Otherwise, simply press enter: ')

            if job_add == '':
                return

            data = {field: get_field(f'Enter the {field}', whitespace=True, nullable=True) for field in ['title', 'employer', 'start_date', 'end_date', 'location', 'description']}

            response = self.post('/add-job-history', data, authenticate=True)
            if response.status_code == 200:
                print('Successfully added job to history.')
            else:
                if response.json() == { 'error': 'Limit of three jobs has been reached' }:
                    print('Limit of three jobs has been reached.')
                else:
                    print('Error adding job.')
        else:
            labels = [
                ('id', 'id'),
                ('title', 'title'),
                ('employer', 'employer'),
                ('location', 'location'),
                ('start_date', 'start date'),
                ('end_date', 'end date'),
                ('description', 'description')
            ]
            for job in response:
                for i, (field, label) in enumerate(labels):
                    def capitalize(s):
                        return s[0].upper() + s[1]

                    if job[field] is None:
                        print(f'{i + 1}) {capitalize(label)}: Not yet set.')
                    else:
                        print(f'{i + 1}) {capitalize(label)}: {job[field]}')

            modify_job_history = input('Would you like to make any changes? If so, enter add to add a new job, remove to remove a job, edit to edit a job, or press enter to exit: ')

            if modify_job_history == 'add':
                data = {field: get_field(f'Enter the {field}', whitespace=True, nullable=True) for field in ['title', 'employer', 'start_date', 'end_date', 'location', 'description']}

                response = self.post('/add-job-history', data, authenticate=True)
                if response.status_code == 200:
                    print('Successfully added job to history.')
                else:
                    if response.json() == { 'error': 'Limit of three jobs has been reached' }:
                        print('Limit of three jobs has been reached.')
                    else:
                        print('Error adding job.')
                return

            elif modify_job_history == 'remove':
                index = int(input("Enter the index of the job to remove: "))
                self.post('/remove-job-history', {'id': response[index-1]['id'] }, error_msg='Failed to delete job.', authenticate=True)

            elif modify_job_history == 'edit':
                field_to_edit = input('Enter the index of the field to edit: ')

                try:
                    field_to_edit = labels[int(field_to_edit) - 1][0]
                except (ValueError, IndexError) as e:
                    raise InvalidInputError('Invalid response, try again.') from e

                if field_to_edit in next(zip(*labels))[:3]:
                    raise InvalidInputError('This field is not editable.')

                new_value = input(f'Enter the {dict(labels)[field_to_edit]}: ')

                self.post('/edit-job-history', {'id': job['id'], field_to_edit: new_value},
                    error_msg=f'Failed to update {field_to_edit} to new value.', authenticate=True)

                print(f'Successfully updated {field_to_edit}\'s value.')

    def discover_users(self):
        users = self.get('/list-users', error_msg='Error retrieving user list.')
        if len(users):
            for user in users:
                print(f'{user["username"]} {user["firstname"]} {user["lastname"]}')
        else:
            print('No users yet.')

    def lookup_users(self):
        fields = {
            'firstname': get_field('Enter the user\'s first name (leave empty and press enter to skip)', nullable=True),
            'lastname': get_field('Enter the user\'s last name (leave empty and press enter to skip)', nullable=True),
            'university': get_field('Enter the user\'s university name (leave empty and press enter to skip)', whitespace=True, nullable=True),
            'major': get_field('Enter the user\'s subject major (leave empty and press enter to skip)', whitespace=True, nullable=True)
        }
        fields = {field_name: field for field_name, field in fields.items() if field is not None}
        if len(fields) == 0:
            raise InvalidInputError('You skipped all conditions!')

        matches = self.post('/lookup-user', fields, error_msg='Unable to lookup whether user is part of the InCollege system.')['matches']
        if len(matches) > 0:
            print('Matches:')
            print('\n'.join(' '.join(user[field] for field in ['username', 'firstname', 'lastname']) for user in matches))
        else:
            print('Nobody matches these criteria.')
            return

        if not self.access_token:
            return

        request_target = get_field('Would you like to connect to any one of the matches displayed above? If so, enter their username. If not, simply press enter', nullable=True)
        if request_target is None:
            return
        if not any(user['username'] == request_target for user in matches):
            raise InvalidInputError(f'{request_target} isn\'t one of the matches.')

        self.send_connection_request(request_target)

    def send_connection_request(self, username=None):
        if username is None:
            username = get_field('Enter the username of the person to connect with')

        self.post('/make-connection-request', { 'username': username },
            error_msg=f'Unable to send {username} a connection request.', authenticate=True)
        print('Connection request successfully sent.')
        '''response = self.post('/make-connection-request', { 'username': username }, authenticate=True)
        if response.status_code == 200:
            print('Connection request successfully sent.')
        else:
            print(response.json())'''

    def consider_requests(self):
        connection_requests = self.get('/pending-requests', error_msg='You have no connection requests.', authenticate=True)
        if len(connection_requests) == 0:
            print('You have no connection requests.')
            return

        print('Incoming connection requests:')
        for user in connection_requests:
            print(f'{user["username"]} {user["firstname"]} {user["lastname"]}')

        users_to_accept = input('Enter the usernames of the users to accept (separated by a space). Leave empty to accept no requests: ').strip().split(' ')
        users_to_deny = input('Enter the usernames of the users to deny (separated by a space). Leave empty to deny no requests: ').strip().split(' ')

        data = {
            'users-to-accept': [{ 'username': username } for username in users_to_accept if username != ''],
            'users-to-deny': [{ 'username': username } for username in users_to_deny if username != '']
        }

        response = self.post('/accept-requests', data, error_msg='Unable to consider requests.', authenticate=True)
        accepted, denied, ignored = tuple(response[field] for field in ['accepted', 'denied', 'ignored'])
        if len(accepted):
            print('\n'.join(f'Successfully accepted {user["username"]}\'s request.' for user in accepted))
        if len(denied):
            print('\n'.join(f'Successfully denied {user["username"]}\'s request.' for user in denied))
        if len(ignored):
            print('\n'.join(f'You do not have a connection request from {user["username"]}.' for user in ignored))

    def view_connections(self):
        connections = self.get('/connections', error_msg='Unable to view current connections.', authenticate=True)
        if len(connections) == 0:
            print('You have no connections.')
            return

        for i, friend in enumerate(connections):
            print(f'{i + 1}) ' + ' '.join(friend[field] for field in ['username', 'firstname', 'lastname']))

        friend = input('To see a friend\'s profile, enter the his/her index. To skip this, simply press enter: ')
        if friend.strip() == '':
            return

        try:
            friend = connections[int(friend) - 1]
        except (ValueError, IndexError) as e:
            raise InvalidInputError('Invalid response, try again.') from e

        response = self.post('/friend-profile', { 'id': friend['id'] },
            error_msg=f'Unable to view {friend["username"]}\'s profile.', authenticate=True)

        for field, label in [
                ('username', 'Username'),
                ('firstname', 'First name'),
                ('lastname', 'Last name')
            ]:     # this is not a dictionary because order matters here
            print(f'{label}: {friend[field]}')

        for field, label in [
                ('bio', 'Bio'),
                ('university', 'University'),
                ('major', 'Major'),
                ('years_attended', 'Years attended')
            ]:
            if response[field] is not None:
                print(f'{label}: {response[field]}')

    def disconnect(self):
        username = get_field('Enter the username of the user to disconnect')
        self.post('/disconnect', { 'username': username }, error_msg=f'Unable to disconnect from {username}.', authenticate=True)
        print(f'Successfully disconnected from {username}.')

    def post_job(self):
        data = {field: get_field(f'Enter the {field}', whitespace=True) for field in ['title', 'description', 'employer', 'location', 'salary']}
        try:
            assert data['salary'][0] == '$'
            data['salary'] = int(data['salary'][1:])
        except (AssertionError, ValueError) as e:
            raise InvalidInputError('Invalid salary, must be a number which begins with $') from e

        response = self.post('/post-job', data, authenticate=True)
        if response.status_code == 200:
            print('Job posting created successfully.')
        else:
            if response.json() == { 'error': 'Limit of ten job postings has been reached' }:
                print('Limit of ten job postings has been reached.')
            else:
                print('Error creating job posting.')

    def get_job_postings(self):
        job_postings = self.get('/job-postings', error_msg='Error fetching job postings.')

        if len(job_postings) > 0:
            for posting in job_postings:
                posting['salary'] = f'${posting["salary"]}'
                print('\n'.join(f'{label}: {posting[label]}' for label in [
                    'title',
                    'employer',
                    'description',
                    'location',
                    'salary',
                    'username'
                ]))
        else:
            print('No job postings found.')

    def get_job_titles(self):
        job_postings = self.get('/job-postings', error_msg='Error fetching job postings.')
        job_applications = self.get('/applications', error_msg='Error fetching job applications.', authenticate=True)

        if len(job_postings) == 0:
            print('No job postings found.')
            return

        for i, posting in enumerate(job_postings):
            if posting['id'] in [application['job_id'] for application in job_applications]:
                print(f'{i + 1}) {posting["title"]} (applied)')
            else:
                print(f'{i + 1}) {posting["title"]}')

        try:
            choice = job_postings[int(input('Enter the index of a job above to see its entire posting: ')) - 1]
        except (ValueError, IndexError):
            raise InvalidInputError('Invalid response, try again.')

        if choice['id'] in [application['job_id'] for application in job_applications]:
            raise InvalidInputError('You have already applied to this position.')

        print('\n'.join(f'{label}: {posting[label]}' for label in [
                'title',
                'employer',
                'description',
                'location',
                'salary',
                'username'
            ]))

        to_apply = input('Would you like to apply to this job? (Answer either "yes" or "no"): ').strip().lower()
        if to_apply == 'yes':
            graduation_date = get_field('Please enter your graduation date (mm/dd/yyyy)')
            ideal_start_date = get_field('Please enter your ideal starting date (mm/dd/yyyy)')
            cover_letter = get_field('Briefly elaborate on why you are the best fit for this position', whitespace=True)
            self.post('/apply', {
                    'job_id': choice['id'],
                    'graduation_date': graduation_date,
                    'ideal_start_date': ideal_start_date,
                    'cover_letter': cover_letter
                }, error_msg='Unable to apply for the job.', authenticate=True)
            print('Successfully applied for the job.')
        elif to_apply != 'no':
            raise InvalidInputError('Invalid response.')

    def delete_job(self):
        job_postings = self.get('/jobs-posted', error_msg='Error fetching job postings.', authenticate=True)

        if len(job_postings) == 0:
            print('No job postings found from you.')
            return

        for i, posting in enumerate(job_postings):
            print(f'{i + 1}) {posting["title"]}')

        try:
            choice = job_postings[int(input('Enter the index of a job above to delete it: ')) - 1]
        except (ValueError, IndexError):
            raise InvalidInputError('Invalid response, try again.')

        self.post('/delete-job', { 'job_id': choice['id'] }, error_msg='Unable to delete job.', authenticate=True)
        print('Job successfully deleted.')

    def applied_jobs(self):
        applications = self.get('/applications', error_msg='Error fetching job applications.', authenticate=True)

        if len(applications) == 0:
            print('No job applications found.')
            return

        for i, title in enumerate([application['title'] for application in applications]):
            print(f'{i + 1}) {title}')

    def not_applied_jobs(self):
        job_postings = self.get('/job-postings', error_msg='Error fetching job postings.')
        applications = self.get('/applications', error_msg='Error fetching job applications.', authenticate=True)
        applications = [application['job_id'] for application in applications]

        if len(applications) == len(job_postings):
            print('No remaining job postings found.')
            return

        for i, title in enumerate([posting['title'] for posting in job_postings if posting['id'] not in applications]):
            print(f'{i + 1}) {title}')

    def mark(self):
        job_postings = self.get('/job-postings', error_msg='Error fetching job postings.')
        jobs_marked = self.get('/marked', error_msg='Error fetching saved jobs.', authenticate=True)

        if len(job_postings) == 0:
            print('No job postings found.')
            return

        for i, posting in enumerate(job_postings):
            if posting['id'] in jobs_marked:
                print(f'{i + 1}) {posting["title"]} (marked)')
            else:
                print(f'{i + 1}) {posting["title"]}')

        try:
            choice = job_postings[int(input('Enter the index of a job above to see its entire posting: ')) - 1]
        except (ValueError, IndexError):
            raise InvalidInputError('Invalid response, try again.')

        if choice['id'] in jobs_marked:
            raise InvalidInputError('You have already marked this position.')

        self.post('/mark', { 'job_id': choice['id'] }, error_msg='Unable to mark job.', authenticate=True)
        print('Job successfully marked as saved.')

    def unmark(self):
        job_postings = self.get('/job-postings', error_msg='Error fetching job postings.')
        jobs_marked = self.get('/marked', error_msg='Error fetching saved jobs.', authenticate=True)

        if len(jobs_marked) == 0:
            print('No jobs are marked as saved.')
            return

        for i, job_id in enumerate(jobs_marked):
            posting = [posting for posting in job_postings if posting['id'] == job_id][0]
            print(f'{i + 1}) {posting["title"]}')

        try:
            choice = jobs_marked[int(input('Enter the index of a job above to see its entire posting: ')) - 1]
        except (ValueError, IndexError):
            raise InvalidInputError('Invalid response, try again.')

        self.post('/unmark', { 'job_id': choice }, error_msg='Unable to unmark job.', authenticate=True)
        print('Job successfully unmarked.')

    def fetch_user_preferences(self):
        response = self.get('/user-preferences', authenticate=True)

        fields = [
            'email_notifications_enabled',
            'sms_notifications_enabled',
            'targeted_advertising_enabled',
            'language'
        ]
        if response.status_code == 200:
            for field in fields:
                setattr(self, field, response.json()[field])
        else:
            for field in fields:
                setattr(self, field, None)

    def set_user_preferences(self, field, value):
        self.post('/set-user-preferences', { field: value }, error_msg=f'Error updating {field} to {value}', authenticate=True)
        print('Successfully updated user preferences.')

if __name__ == '__main__':
    print(Path('./documents/success-story.txt').read_text().strip() + '\n')

    url = sys.argv[1] if len(sys.argv) > 1 else 'http://raunak.us'
    menu = Menu(url)
    menu.main()
