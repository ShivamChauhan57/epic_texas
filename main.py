from getpass import getpass
import hashlib
import requests
import sys
from pathlib import Path
import json

def authorization_header():
    if Path("./jwt-token.txt").exists():
        return { 'Authorization': f'Bearer {Path("./jwt-token.txt").read_text().strip()}' }
    else:
        return dict()

url = None

def playvideo():
    print('\n\nVideo is now playing\n')
    
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
    if not (len(password) >= 8 and any(chr(ord('0') + i) in password for i in range(10))):
        print('Password is not secure, should be at least eight characters and must contain a number.')
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
    response = requests.get(f'{url}/profile', headers=authorization_header())
    if response.status_code == 200:
        username, firstname, lastname = tuple(response.json().values())
        print(f'Username: {username}')
        print(f'First name: {firstname}')
        print(f'Last name: {lastname}')
    elif response.status_code == 401:
        print('Error retrieving profile info: permission denied. If you haven\'t logged in yet, please do so. If you have, consider doing so again.')
    else:
        print('Error retrieving profile info.')

def discover_users():
    response = requests.get(f'{url}/list-users')
    if response.status_code == 200:
        for user in response.json():
            print(' '.join(user.values()))
    else:
        print('Error retrieving user list')

def lookup_user():
    firstname = input('Enter the user\'s first name: ').strip()
    lastname = input('Enter the user\'s last name: ').strip()

    response = requests.post(f'{url}/lookup-user', data=json.dumps({ 'firstname': firstname, 'lastname': lastname }))

    if response.status_code == 200:
        if response.json()['matches']:
            print(f'{firstname} {lastname} is a part of the InCollege system.')
        else:
            print(f'{firstname} {lastname} is not yet a part of the InCollege system yet.')
    else:
        print('Unable to lookup whether user is part of the InCollege system')

def follow():
    user_to_follow = input('Enter the username of the user to follow: ')
    response = requests.post(f'{url}/follow', data=json.dumps({ 'username': user_to_follow }), headers=authorization_header())

    if response.status_code == 200:
        print(f'You are now following {user_to_follow}')
    elif response.status_code == 401:
        print(f'Unable to follow {user_to_follow}: permission denied. If you haven\'t logged in yet, please do so. If you have, consider doing so again.')
    else:
        print(f'Unable to follow {user_to_follow}.')

def list_followers():
    response = requests.get(f'{url}/followers', headers=authorization_header())
    if response.status_code == 200:
        for user in response.json():
            print(' '.join(user.values()))
    elif response.status_code == 401:
        print(f'Error retrieving follower list: permission denied. If you haven\'t logged in yet, please do so. If you have, consider doing so again.')
    else:
        print('Error retrieving follower list')

if __name__ == '__main__':
    url = input('Please enter the backend URL <example: http://raunak.us>: ')

    print('Here is a student success story from Raunak Chhatwal: I was a struggling student with a 2.069 GPA and no internship, so my hopes were down. Fortunately, with InCollege, I was able to land an entry level position with the mighty Sinaloa cartel in their armed robotics division.\n')

    actions = {
        '\nInCollege Video\n': playvideo,
        'Log in': login,
        'Sign up': signup,
        'See profile': see_profile,
        'Discover users': discover_users,
        'Lookup user': lookup_user,
        'Follow a user': follow,
        'See your followers': list_followers,
        'Exit the shell': sys.exit
    }
    
    while True:
        print('Availaible actions:\n{}'.format('\n'.join(actions.keys())))
        actions[(input('Enter choice: ')).strip()]()
        print()

    
