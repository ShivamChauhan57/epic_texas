from getpass import getpass
import hashlib
import requests
import sys
from pathlib import Path
import json

url = 'http://localhost:8000'

def login():
    username = input('Please enter your username: ')
    passwordHash = hashlib.sha256(getpass('Enter your password: ').encode()).hexdigest()

    data = {
        'username': username,
        'passwordHash': passwordHash
    }

    response = requests.post(f'{url}/login', data=json.dumps(data), headers={ 'Content-Type': 'application/json' })
    if response.status_code == 200:
        Path('jwt-token.txt').write_text(response.json()['token'])
        print('Login successful.')
    else:
        print('Login unsuccessful.')

def signup():
    def username_exists(username):
        try:
            return any(username == user['username'] for user in requests.get(f'{url}/list-users').json())
        except:
            return False    # signing up will be unsuccessful regardless

    username = input('Please enter your username: ')
    if username_exists(username):
        print('Username not available!')
        return

    fullname = input('Please enter your first and last name: ').strip().split(' ')

    password = getpass('Enter your password: ')
    if len(password) < 8:
        print(f'Password is not secure: {validation_result}')
        return

    data = {
        'username': username,
        'firstname': fullname[0],
        'lastname': fullname[-1],
        'passwordHash': hashlib.sha256(password.encode()).hexdigest()
    }

    response = requests.post(f'{url}/add-user', data=json.dumps(data), headers={ 'Content-Type': 'application/json' })
    if response.status_code == 200:
        print('You have successfully signed up! Please log in now.')
    else:
        print('Sign up unsuccessful. Please try again.')

def see_profile():
    response = requests.get(f'{url}/profile', headers={ 'Authorization': f'Bearer {Path("./jwt-token.txt").read_text().strip()}' })
    if response.status_code == 200:
        username, firstname, lastname = tuple(response.json().values())
        print(f'Username: {username}')
        print(f'First name: {firstname}')
        print(f'Last name: {lastname}')
    else:
        print('Error retrieving profile info.')

def discover_users():
    response = requests.get(f'{url}/list-users')
    if response.status_code == 200:
        for user in response.json():
            print(' '.join(user.values()))
    else:
        print('Error retrieving user list')

def follow():
    user_to_follow = input('Enter the username of the user to follow: ')
    response = requests.post(f'{url}/follow', data=json.dumps({ 'username': user_to_follow }), headers={ 'Authorization': f'Bearer {Path("./jwt-token.txt").read_text().strip()}' })

    if response.status_code == 200:
        print(f'You are now following {user_to_follow}')
    else:
        print(f'Unable to follow {user_to_follow}.')
        print(response.json())

def list_followers():
    response = requests.get(f'{url}/followers', headers={ 'Authorization': f'Bearer {Path("./jwt-token.txt").read_text().strip()}' })
    if response.status_code == 200:
        for user in response.json():
            print(' '.join(user.values()))
    else:
        print('Error retrieving follower list')

if __name__ == '__main__':
    actions = {
        'Log in': login,
        'Sign up': signup,
        'See profile': see_profile,
        'Discover users': discover_users,
        'Follow a user': follow,
        'See your followers': list_followers,
        'Exit the shell': sys.exit
    }
    
    while True:
        print('Availaible actions:\n{}'.format('\n'.join(actions.keys())))
        actions[(input('Enter choice: ')).strip()]()

    
