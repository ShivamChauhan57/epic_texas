from getpass import getpass
import hashlib
import requests
import sys
import json

class Menu:
    def __init__(self, url):
        self.url = url
        self.access_token = None
        self.mode = 'log-in'

    def main(self):
        while True:
            options, actions = tuple(zip(*self.options()))
            print('Availaible actions:\n{}'.format('\n'.join(f'{i + 1}: {option}' for i, option in enumerate(options))))

            try:
                action = actions[int((input('Enter choice (enter the index): ')).strip()) - 1]
                action()
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
                ('Lookup user', self.lookup_user),
                ('Discover users', self.discover_users),
                ('Useful links', lambda: self.change_mode('useful links')),
                ('InCollege Important Links', lambda: self.change_mode('incollege links')),
                ('Exit', sys.exit)
            ]
        elif self.mode == 'main':
            options = [
                ('See profile', self.see_profile),
                ('Discover users', self.discover_users),
                ('Follow a user', self.follow),
                ('See your followers', self.list_followers),
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
            options = [
                ('Copyright Notice', lambda: print('We\'re here to help')),
                ('About', lambda: print(about_message)),
                ('Accessibility', lambda: print(press_message)),
                ('User Agreement', self.under_construction),
                ('Privacy Policy', self.under_construction),
                ('Cookie Policy', self.under_construction),
                ('Copyright Policy', lambda: self.change_mode('useful links')),
                ('Brand Policy', lambda: self.change_mode('useful links')),
                ('Guest Controls', lambda: self.change_mode('useful links')),
                ('Languages', lambda: self.change_mode('useful links')),
                   
            ]

        return options

    def change_mode(self, new_mode):
        self.mode = new_mode
        if self.options() == None:
            raise Exception(f'Invalid mode: {self.mode}')

    def under_construction(self):
        print('Under construction')
        
    def login(self):
        username = input('Please enter your username: ')
        passwordHash = hashlib.sha256(getpass('Enter your password: ').encode()).hexdigest()

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

        username = input('Please enter your username: ')
        if username_exists(username):
            print('Username not available!')
            return

        fullname = input('Please enter your full name: ').strip().split(' ')
        assert len(fullname) >= 2

        password = getpass('Enter your password: ')
        if not (len(password) >= 8 and any(chr(ord('0') + i) in password for i in range(10))):
            print('Password is not secure, should be at least eight characters and must contain a number.')
            return

        data = {
            'username': username,
            'firstname': fullname[0],
            'lastname': fullname[-1],
            'passwordHash': hashlib.sha256(password.encode()).hexdigest()
        }

        response = requests.post(f'{self.url}/add-user', data=json.dumps(data), headers={ 'Content-Type': 'application/json' })
        if response.status_code == 200:
            print('You have successfully signed up! Please log in now.')
        else:
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
            for user in response.json():
                print(' '.join(user.values()))
        else:
            print('No users yet.')

    def lookup_user(self):
        firstname = input('Enter the user\'s first name: ').strip()
        lastname = input('Enter the user\'s last name: ').strip()

        response = requests.post(f'{self.url}/lookup-user', data=json.dumps({ 'firstname': firstname, 'lastname': lastname }))

        if response.status_code == 200:
            if response.json()['matches']:
                print(f'{firstname} {lastname} is a part of the InCollege system.')
            else:
                print(f'{firstname} {lastname} is not yet a part of the InCollege system yet.')
        else:
            print('Unable to lookup whether user is part of the InCollege system')

    def follow(self):
        user_to_follow = input('Enter the username of the user to follow: ')
        response = requests.post(f'{self.url}/follow', data=json.dumps({ 'username': user_to_follow }), headers={ 'Authorization': f'Bearer {self.access_token}' })

        if response.status_code == 200:
            print(f'You are now following {user_to_follow}')
        elif response.status_code == 401:
            print(f'Unable to follow {user_to_follow}: permission denied. If you haven\'t logged in yet, please do so. If you have, consider doing so again.')
        else:
            print(f'Unable to follow {user_to_follow}.')

    def list_followers(self):
        response = requests.get(f'{self.url}/followers', headers={ 'Authorization': f'Bearer {self.access_token}' })
        if response.status_code == 200:
            if len(users := response.json()):
                for user in users:
                    print(' '.join(user.values()))
            else:
                print('You have no followers')
        elif response.status_code == 401:
            print(f'Error retrieving follower list: permission denied. If you haven\'t logged in yet, please do so. If you have, consider doing so again.')
        else:
            print('Error retrieving follower list')

    def post_job(self):
        data = dict()
        for field in ['title', 'description', 'employer', 'location', 'salary']:
            data[field] = input(f'Enter the {field}: ').strip()
        try:
            assert data['salary'][0] == '$'
            data['salary'] = int(data['salary'][1:])
        except (AssertionError, ValueError):
            print('Invalid salary, must be a number which begins with $')
            return

        response = requests.post(f'{self.url}/post-job', data=json.dumps(data), headers={ 'Content-Type': 'application/json', 'Authorization': f'Bearer {self.access_token}' })
        if response.status_code == 200:
            print('Job posting created successfully.')
        else:
            print('Error creating job posting.')

    def get_job_postings(self):
        response = requests.get(f'{self.url}/job-postings', headers={ 'Authorization': f'Bearer {self.access_token}' })
        if response.status_code != 200:
            print('Error fetching job postings.')
            return

        if len(job_postings := response.json()):
            for posting in job_postings:
                posting['salary'] = f'${posting["salary"]}'
                print('\n'.join(f'{key}: {value}' for key, value in posting.items()))
        else:
            print('No job postings found.')

if __name__ == '__main__':
    print('Here is a student success story from Raunak Chhatwal: I was a struggling student with a 2.069 GPA and no internship, so my hopes were down. Fortunately, with InCollege, I was able to land an entry level position with the mighty Sinaloa cartel in their armed robotics division.\n')

    url = sys.argv[1] if len(sys.argv) > 1 else 'http://raunak.us'
    menu = Menu(url)
    menu.main()
