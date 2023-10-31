import subprocess as sp
from pathlib import Path
import os
from unittest.mock import patch
import time
import json
import random
import itertools
import pytest
import psutil

import main

def bernoulli(p):       # bernoulli random variable
    if not (0 <= p <= 1):
        raise ValueError(f'Invalid p: {p}')

    return random.random() < p

@pytest.fixture
def create_db():
    # assert not os.path.exists('./test.db')
    if os.path.exists('./test.db'):
        os.remove('./test.db')

    db_creator_process = sp.run('env python3 models.py test.db'.split(' '), capture_output=True, text=True)
    assert db_creator_process.stdout.strip() == 'test.db successfully created'
    assert os.path.exists('./test.db')
    yield
    # os.remove('./test.db')

@pytest.fixture
def start_server(create_db):
    if os.path.exists('./gunicorn.log'):
        os.remove('./gunicorn.log')

    os.environ['DB_PATH'] = 'test.db'
    server_process = sp.Popen('gunicorn --bind 0.0.0.0:8000 server:app --log-file /home/raunak/misc/repos/epic_texas/gunicorn.log --log-level DEBUG'.split(' '), stdout=sp.PIPE, stderr=sp.PIPE)
    time.sleep(0.5)   # wait for backend to start
    assert main.Menu(url='http://localhost:8000').get('/list-users').json() == []
    yield
    server_process.terminate()

class TestFactory:
    def __init__(self, menu, num_tests, capsys):
        self.menu = menu
        self.num_tests = num_tests
        self.capsys = capsys

        self.test_values_json = json.loads(Path('test-values.json').read_text())
        self.users = []
        self.user_session = None

        self.distribution = {option: 0 for option in [
            'Log in',
            'Sign up',
            'Discover users',
            'Exit',
            'Send connection requests',
            'View requests',
            'Show my network',
            'Disconnect from a user',
            'Log out'
        ]}

        self.options_not_covered = [
            'InCollege Video',
            'Lookup users',
            'Useful links',
            'InCollege Important Links',
            'Exit',
            'Create/view/edit profile',
            'Job search/internship'
        ]

    def get_test_value(self, obj, attr):
        return random.choice(self.test_values_json[obj][attr])

    def assert_output(self, *expected_lines, error_msg=None):
        out, err = self.capsys.readouterr()

        for i, (output_line, line_expected) in enumerate(zip(out.strip().split('\n'), expected_lines)):
            if error_msg is None:
                assert output_line.strip() == line_expected
            else:
                assert output_line.strip() == line_expected, error_msg

        assert err.strip() == ''

    def user(self):
        return self.users[self.user_session]

    def input_generator(self):
        for i in range(self.num_tests):
            _, _ = self.capsys.readouterr()

            options = next(zip(*self.menu.options()))
            available_options = [option for option in options if option not in self.options_not_covered]

            n, m = 3, 6     # number of options in log-in and main mode, respectively
            if self.menu.mode == 'main':
                exit_probability = (n - 1)/(n*(m - 1))
                weights = [(1 - exit_probability)/(len(available_options) - 1)] * (len(available_options) - 1)
                weights.append(exit_probability)
                option = random.choices(available_options, weights=weights)[0]
            else:
                option = random.choice(available_options)
            option = options.index(option)
            with Path('./dbg.txt').open('a') as dbg_file:
                dbg_file.write(f'option to yield: {option + 1}\n')
            yield option + 1

            self.distribution[options[option]] += 1     # to ensure that each option is tested fairly

            # for more clarity on each test case implemented in this match block,
            # please first view the corresponding implementation in main.py
            match options[option]:
                case 'Log in':
                    username_correct = bernoulli(3/4) if len(self.users) > 0 else False
                    if username_correct:
                        user = random.choice(self.users)
                        username = user['username']

                        password_correct = bernoulli(3/4)
                        if password_correct:
                            password = user['password']
                        else:
                            password = self.get_test_value('user', 'password')
                    else:
                        firstname = self.get_test_value('user', 'firstname')
                        lastname = self.get_test_value('user', 'lastname')
                        username = firstname.lower() + lastname.lower() + \
                            str(random.choice(range(10))) + str(random.choice(range(10)))
                        password = self.get_test_value('user', 'password')

                    yield username
                    yield password

                    user_session = None
                    for i, user in enumerate(self.users):
                        if user['username'] == username and user['password'] == password:
                            user_session = i
                            break

                    if user_session is not None:
                        self.assert_output('Login successful.')
                        assert self.menu.access_token is not None
                        assert self.menu.mode == 'main'

                        self.user_session = user_session
                    else:
                        self.assert_output('Login unsuccessful.')
                        assert self.menu.access_token is None
                        assert self.menu.mode == 'log-in'
                case 'Sign up':
                    fields = [
                            ('user', 'firstname'),
                            ('user', 'lastname'),
                            ('profile', 'university'),
                            ('profile', 'major'),
                            ('user', 'password')
                        ]
                    inputs = [(attr, self.get_test_value(obj, attr)) for obj, attr in fields]
                    username = inputs[0][1].lower() + inputs[1][1].lower() + '{:02}'.format(len(self.users))
                    inputs = [('username', username)] + inputs

                    yield from iter([value for attr, value in inputs])
                    yield inputs[-1][1]    # password confirmation

                    if len(self.users) < 10:
                        self.assert_output('You have successfully signed up! Please log in now.')

                        new_user = dict(inputs)
                        new_user['connection-requests'] = []
                        new_user['connections'] = []
                        self.users.append(new_user)
                    else:
                        self.assert_output('All permitted accounts have been created, please come back later.')
                case 'Discover users':
                    if len(self.users):
                        out, err = self.capsys.readouterr()
                        output_lines = out.strip().split('\n')[:len(self.users)]
                        assert set(output_lines) == {f'{user["username"]} {user["firstname"]} {user["lastname"]}' for user in self.users}
                    else:
                        self.assert_output('No users yet.')
                case 'Send connection requests':
                    connect_successfully = bernoulli(3/4)
                    if connect_successfully:
                        choices = []
                        for i in range(len(self.users)):
                            if i == self.user_session or \
                                self.user_session in self.users[i]['connection-requests'] or \
                                i in self.user()['connection-requests'] + self.user()['connections']:
                                continue

                            choices.append((i, self.users[i]['username']))

                        if len(choices) > 0:
                            choice_id, choice = random.choice(choices)

                            yield choice
                            self.assert_output('Connection request successfully sent.',
                                error_msg=f'user: {self.user()["username"]}, target: {choice}')
                            self.users[self.user_session]['connection-requests'].append(choice_id)
                        else:
                            connect_successfully = False

                    if not connect_successfully:
                        choice = random.choice([
                                self.user_session,
                                *self.user()['connection-requests'],
                                *self.user()['connections'],
                                *[i for i, user in enumerate(self.users) if self.user_session in user['connection-requests']]
                            ])
                        username = self.users[choice]['username']
                        yield username
                        self.assert_output(f'Unable to send {username} a connection request.')
                case 'View requests':
                    pending_requests = [user for user in self.users if self.user_session in user['connection-requests']]
                    if len(pending_requests) == 0:
                        self.assert_output('You have no connection requests.')
                        continue

                    out, err = self.capsys.readouterr()
                    output_lines = out.strip().split('\n')
                    assert output_lines[0] == 'Incoming connection requests:'
                    assert set(output_lines[1:]) == {f'{user["username"]} {user["firstname"]} {user["lastname"]}' for user in pending_requests}

                    to_accept = random.choice(range(len(pending_requests)))
                    to_accept = random.choice(list(itertools.combinations(pending_requests, to_accept)))
                    yield ' '.join(user['username'] for user in to_accept)
                    to_deny = [user for user in pending_requests if user not in to_accept]
                    yield ' '.join(user['username'] for user in to_deny)

                    out, err = self.capsys.readouterr()
                    output_lines = out.strip().split('\n')[:len(to_accept) + len(to_deny)]
                    expected_lines = [f'Successfully accepted {user["username"]}\'s request.' for user in to_accept] + \
                        [f'Successfully denied {user["username"]}\'s request.' for user in to_deny]

                    assert set(output_lines) == set(expected_lines)
                    for user in to_accept:
                        user = self.users.index(user)
                        self.users[user]['connection-requests'].remove(self.user_session)
                        self.users[user]['connections'].append(self.user_session)
                        self.user()['connections'].append(user)

                    for user in to_deny:
                        user = self.users.index(user)
                        self.users[user]['connection-requests'].remove(self.user_session)
                case 'Show my network':
                    connections = [self.users[i] for i in self.user()['connections']]
                    if len(connections) == 0:
                        self.assert_output('You have no connections.')
                        continue

                    out, err = self.capsys.readouterr()
                    output_lines = [line.strip()[line.index(' ') + 1:] for line in out.strip().split('\n')[:len(connections)]]
                    assert set(output_lines) == {f'{user["username"]} {user["firstname"]} {user["lastname"]}' for user in connections}

                    choice = random.choice(range(len(output_lines) + 1))
                    if choice == 0:
                        yield ''
                        continue

                    yield choice
                    username = output_lines[choice - 1]
                    username = username[:username.index(' ')]
                    friend = [user for user in connections if user['username'] == username][0]
                    fields = [(field, label) for field, label in [
                            ('username', 'Username'),
                            ('firstname', 'First name'),
                            ('lastname', 'Last name'),
                            ('bio', 'Bio'),
                            ('university', 'University'),
                            ('major', 'Major'),
                            ('years_attended', 'Years attended')
                        ] if field in friend]
                    profile_expected = [f'{label}: {friend[field]}' for field, label in fields]
                    self.assert_output(*profile_expected)
                case 'Disconnect from a user':
                    disconnect_successfully = bernoulli(3/4)
                    if disconnect_successfully:
                        connections = self.user()['connections']
                        if len(connections) == 0:
                            disconnect_successfully = False
                        else:
                            friend = random.choice(connections)
                            username = self.users[friend]['username']

                    if not disconnect_successfully:
                        firstname = self.get_test_value('user', 'firstname')
                        lastname = self.get_test_value('user', 'lastname')
                        username = firstname.lower() + lastname.lower() + \
                            str(random.choice(range(10))) + str(random.choice(range(10)))
                        friend = -1

                    yield username
                    if friend in self.user()['connections']:
                        self.assert_output(f'Successfully disconnected from {username}.')
                        self.users[friend]['connections'].remove(self.user_session)
                        self.users[self.user_session]['connections'].remove(friend)
                    else:
                        self.assert_output(f'Unable to disconnect from {username}.')
                case 'Log out':
                    assert self.menu.access_token is None
                    assert self.menu.mode == 'log-in'
                    self.user_session = None
                case _:
                    raise Exception(f'Not implemented: {options[option]}')

        if self.menu.mode == 'main':
            yield next(zip(*self.menu.options())).index('Log out') + 1

        yield next(zip(*self.menu.options())).index('Exit') + 1

@pytest.mark.usefixtures('start_server')
def test(capsys):
    if os.path.exists('./dbg.txt'):
        os.remove('./dbg.txt')

    menu = main.Menu(url='http://localhost:8000')
    test_factory = TestFactory(menu, 250, capsys)
    input_generator = map(str, test_factory.input_generator())
    with patch('builtins.input', side_effect=input_generator):
        with patch('getpass.getpass', side_effect=input_generator):
            menu.main()

    Path('./dist.txt').write_text(str(test_factory.distribution))

if __name__ == '__main__':
    pytest.main([__file__])