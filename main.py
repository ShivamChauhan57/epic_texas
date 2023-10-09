from getpass import getpass
import hashlib
import requests
import sys
import json
from pathlib import Path
import os

class InvalidInputError(ValueError):
    def __init__(self, message):
        super().__init__(message)

def get_field(prompt, nullable=False):
    _input = input(f'{prompt}: ').strip()
    if any(c.isspace() for c in _input.strip()):
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
        while True:
            options, actions = tuple(zip(*self.options()))
            print('Available actions:\n{}'.format('\n'.join(f'{i + 1}: {option}' for i, option in enumerate(options))))

            try:
                action = actions[int((input('Enter choice (enter the index): ')).strip()) - 1]
                action()
            except InvalidInputError as e:
                print(e)
            except (ValueError, IndexError):
                print('Invalid response, try again.')

            print()

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
                ('Exit', sys.exit)
            ]
        elif self.mode == 'main':
            if not self.access_token:
                self.change_mode('log-in')
                return self.options()

            if len(self.view_requests()) > 0:
                print('You have pending connection requests to accept or deny.')

            options = [
                ('See profile', self.see_profile),
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
        elif self.mode == 'job search/internship':
            options = [
                ('See job postings', self.get_job_postings),
                ('Post a job', self.post_job),
                ('Return to main menu', lambda: self.change_mode('main')),
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

            if self.access_token == None:
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

            options = [(document, lambda textfile=textfile: print(Path(os.path.join(os.path.dirname(__file__), 'documents', textfile)).read_text().strip()))
                for document, textfile in documents.items()]

            if self.access_token:
                options += [
                    ('Guest Controls', lambda: self.change_mode('guest controls')),
                    ('Languages', lambda: self.change_mode('languages'))
                ]

            options.append(('Go back', lambda: self.change_mode('main' if self.access_token else 'log-in')))
        elif self.mode == 'guest controls':
            self.fetch_user_preferences()
            if any(setting == None for setting in
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
        
    def login(self):
        username = get_field('Please enter your username')
        passwordHash = hashlib.sha256(getpass('Enter your password: ').strip().encode()).hexdigest()

        data = {
            'username': username,
            'passwordHash': passwordHash
        }

        response = requests.post(f'{self.url}/login', data=json.dumps(data), headers={ 'Content-Type': 'application/json' })
        if response.status_code == 200:
            self.access_token = response.json()['token']
            print('Login successful.')
            self.change_mode('main')
        else:
            print('Login unsuccessful.')

    def logout(self):
        self.access_token = None
        self.change_mode('log-in')

    def signup(self):
        def username_exists(username):
            try:
                return any(username == user['username'] for user in requests.get(f'{self.url}/list-users').json())
            except:
                return False    # signing up will be unsuccessful regardless

        def validate_password(password):
            def special(c):
                digit = 0 <= ord(c) - ord('0') < 10
                letter = 0 <= ord(c.lower()) - ord('a') < 26
                return not (digit or letter or c.isspace())

            contains_digit = any(chr(ord('0') + i) in password for i in range(10))
            contains_capital = any(chr(ord('A') + i) in password for i in range(ord('Z') - ord('A') + 1))
            contains_special = any(special(c) for c in password)

            return 8 <= len(password) <= 12 and contains_digit and contains_capital and contains_special

        username = get_field('Please enter your username')
        if username_exists(username):
            print('Username not available!')
            return

        data = { field: get_field(f'Please enter your {field}') for field in ['firstname', 'lastname', 'university', 'major'] }

        password = getpass('Enter your password: ').strip()
        if not validate_password(password):
            print('Password is not secure, should between eight and twelve characters, must contain a digit, a capital letter, and a special character.')
            return

        if getpass('Confirm your password: ').strip() != password:
            print('Passwords don\'t match!')
            return

        data = {
            'username': username,
            **data,
            'passwordHash': hashlib.sha256(password.encode()).hexdigest()
        }

        response = requests.post(f'{self.url}/add-user', data=json.dumps(data), headers={ 'Content-Type': 'application/json' })
        if response.status_code == 200:
            print('You have successfully signed up! Please log in now.')
        else:
            if response.json() == { 'error': 'Limit of ten users has been reached' }:
                print('All permitted accounts have been created, please come back later.')
            else:
                print(response.json())
                print('Sign up unsuccessful. Please try again.')

    def see_profile(self):
        response = requests.get(f'{self.url}/profile', headers={ 'Authorization': f'Bearer {self.access_token}' })
        if response.status_code == 200:
            username, firstname, lastname = tuple(response.json().values())
            print(f'Username: {username}')
            print(f'First name: {firstname}')
            print(f'Last name: {lastname}')
        elif response.status_code == 401:
            print('Error retrieving profile info: permission denied. If you haven\'t logged in yet, please do so. If you have, consider doing so again.')
        else:
            print('Error retrieving profile info.')

    def discover_users(self):
        response = requests.get(f'{self.url}/list-users')
        if response.status_code != 200:
            print('Error retrieving user list')

        if len(users := response.json()):
            for user in users:
                print(' '.join(user.values()))
        else:
            print('No users yet.')

    def lookup_users(self):
        fields = { field: get_field(f'Enter the user\'s {field} (leave empty and press enter to skip)', nullable=True)
            for field in ['firstname', 'lastname', 'university', 'major'] }
        fields = {field: fields[field] for field in fields if fields[field]}
        if len(fields) == 0:
            raise InvalidInputError('You skipped all conditions!')
            return

        response = requests.post(f'{self.url}/lookup-user', data=json.dumps(fields))

        if response.status_code == 200:
            matches = response.json()['matches']
            if len(matches) > 0:
                print(f'Matches:')
                print('\n'.join(' '.join(user.values()) for user in matches))
            else:
                print(f'Nobody matches these criteria.')
                return
        else:
            print('Unable to lookup whether user is part of the InCollege system')
            return

        if not self.access_token:
            return

        request_target = get_field('Would you like to connect to any of the matches? If so, enter their username. If not, simply press enter', nullable=True)
        if request_target == None:
            return
        if not any(user['username'] == request_target for user in matches):
            raise InvalidInputError(f'{request_target} isn\'t one of the matches.')

        self.send_connection_request(request_target)

    def send_connection_request(self, username=None):
        if username == None:
            username = get_field('Enter the username of the person to connect with')

        response = requests.post(f'{self.url}/make-connection-request', data=json.dumps({ 'username': username }),
            headers={ 'Authorization': f'Bearer {self.access_token}' })

        if response.status_code == 200:
            print('Connection request successfully sent.')
        elif response.status_code == 401:
            print(f'Unable to send {username} a connection request: \
permission denied. If you haven\'t logged in yet, please do so. If you have, consider doing so again.')
        else:
            print(f'Unable to send {username} a connection request')

    def view_requests(self):
        response = requests.get(f'{self.url}/pending-requests', headers={ 'Authorization': f'Bearer {self.access_token}' })
        if response.status_code == 200:
            return response.json()
        else:
            return None

    def consider_requests(self):
        connection_requests = self.view_requests()
        if connection_requests == None:
            print('Error retrieving connection requests.')
            return
        elif len(connection_requests) == 0:
            print('You have no connection requests.')
            return

        print('Incoming connection requests:')
        print('\n'.join(' '.join(user.values()) for user in connection_requests))

        users_to_accept = input('Enter the usernames of the users to accept (separated by a space). Leave empty to accept no requests: ').strip().split(' ')
        users_to_deny = input('Enter the usernames of the users to deny (separated by a space). Leave empty to deny no requests: ').strip().split(' ')

        data = {
            'users-to-accept': [{ 'username': username } for username in users_to_accept if username != ''],
            'users-to-deny': [{ 'username': username } for username in users_to_deny if username != '']
        }

        response = requests.post(f'{self.url}/accept-requests', data=json.dumps(data), headers={ 'Authorization': f'Bearer {self.access_token}' })
        if response.status_code == 200:
            accepted, denied, ignored = tuple(response.json()[field] for field in ['accepted', 'denied', 'ignored'])
            if len(accepted):
                print('\n'.join(f'Successfully accepted {user["username"]}\'s request.' for user in accepted))
            if len(denied):
                print('\n'.join(f'Successfully denied {user["username"]}\'s request.' for user in denied))
            if len(ignored):
                print('\n'.join(f'You do not have a connection request from {user["username"]}.' for user in ignored))
        elif response.status_code == 401:
            print('Unable to consider requests: permission denied. If you haven\'t logged in yet, please do so. If you have, consider doing so again.')
        else:
            print('Unable to consider requests.')

    def view_connections(self):
        response = requests.get(f'{self.url}/connections', headers={ 'Authorization': f'Bearer {self.access_token}' })
        if response.status_code == 200:
            connections = response.json()
            if len(connections) > 0:
                print('\n'.join(' '.join(user[field] for field in ['username', 'firstname', 'lastname']) for user in connections))
            else:
                print('You have no connections.')
        elif response.status_code == 401:
            print('Unable to view current connections: permission denied. If you haven\'t logged in yet, please do so. If you have, consider doing so again.')
        else:
            print('Unable to view current connections.')

    def disconnect(self):
        username = get_field('Enter the username of the user to disconnect')
        response = requests.post(f'{self.url}/disconnect', data=json.dumps({ 'username': username }), headers={ 'Authorization': f'Bearer {self.access_token}' })
        if response.status_code == 200:
            print(f'Successfully disconnected from {username}.')
        elif response.status_code == 401:
            print(f'Unable to disconnect from {username}: permission denied. If you haven\'t logged in yet, please do so. If you have, consider doing so again.')
        else:
            print(f'Unable to disconnect from {username}.')

    def post_job(self):
        data = {get_field(f'Enter the {field}') for field in ['title', 'description', 'employer', 'location', 'salary']}
        try:
            assert data['salary'][0] == '$'
            data['salary'] = int(data['salary'][1:])
        except (AssertionError, ValueError):
            print('Invalid salary, must be a number which begins with $')
            return

        response = requests.post(f'{self.url}/post-job', data=json.dumps(data), headers={ 'Authorization': f'Bearer {self.access_token}' })
        if response.status_code == 200:
            print('Job posting created successfully.')
        else:
            if response.json() == { 'error': 'Limit of five job postings has been reached' }:
                print('Limit of five job postings has been reached')
            else:
                print('Error creating job posting.')

    def get_job_postings(self):
        response = requests.get(f'{self.url}/job-postings')
        if response.status_code != 200:
            print('Error fetching job postings.')
            return

        if len(job_postings := response.json()):
            for posting in job_postings:
                posting['salary'] = f'${posting["salary"]}'
                print('\n'.join(f'{key}: {value}' for key, value in posting.items()))
        else:
            print('No job postings found.')

    def fetch_user_preferences(self):
        response = requests.get(f'{self.url}/user-preferences', headers={ 'Authorization': f'Bearer {self.access_token}' })

        if response.status_code == 200:
            self.email_notifications_enabled, self.sms_notifications_enabled, self.targeted_advertising_enabled, self.language = response.json().values()
        else:
            self.email_notifications_enabled = None
            self.sms_notifications_enabled = None
            self.targeted_advertising_enabled = None
            self.language = None

    def set_user_preferences(self, field, value):
        response = requests.post(f'{self.url}/set-user-preferences',
            data=json.dumps({ field: value }),
            headers={ 'Content-Type': 'application/json', 'Authorization': f'Bearer {self.access_token}' })
        if response.status_code == 200:
            print('Successfully updated user preferences.')
        else:
            print(f'Error updating {field} to {value}')

if __name__ == '__main__':
    print(Path('./documents/success-story.txt').read_text().strip() + '\n')

    url = sys.argv[1] if len(sys.argv) > 1 else 'http://raunak.us'
    menu = Menu(url)
    menu.main()
