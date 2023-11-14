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
    server_process = sp.Popen('gunicorn --bind 0.0.0.0:8000 server:app --log-file gunicorn.log --log-level DEBUG'.split(' '), stdout=sp.PIPE, stderr=sp.PIPE)
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
        self.jobs = []
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
            'Post a job',
            'List applied jobs',
            'List jobs not yet applied to',
            'Unmark a job',
            'See all job postings',
            'Job search/internship',
            'Go back',
            'InCollege Video',
            'Log out'
        ]}

        self.options_not_covered = [
            'Lookup users',
            'Exit',
            'Create/view/edit profile',
            'See job titles and apply',
            'Mark a job',
            'Delete a job',
            'General',
            'Browse InCollege',
            'Business Solutions',
            'Useful links',
            'Help Center',
            'About',
            'Press',
            'Blog',
            'Careers',
            'Developers',
            'Return',
            'InCollege Important Links',
            'Directories',
            'Go Back'
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
                        new_user['jobs-posted'] = []
                        new_user['jobs-marked'] = []
                        new_user['jobs-applied'] = []
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
                case 'Job search/internship':
                    assert self.menu.mode == 'job search/internship'
                case 'InCollege Important Links':
                    assert self.menu.mode == 'incollege links'
                case 'Post a job':
                    fields = ['title', 'description', 'employer', 'location', 'salary']
                    inputs = [self.get_test_value('job', attr) for attr in fields]
                    inputs[-1] = '$' + str(inputs[-1])

                    yield from iter(inputs)

                    if len(self.jobs) < 10:
                        self.assert_output('Job posting created successfully.')
                        try:
                            new_job = dict([(fields[i], inputs[i]) for i in range(len(fields))])
                        except (ValueError):
                            assert False
                        username = self.users[self.user_session]['username']
                        new_job['deleted'] = False
                        self.user()["jobs-posted"].append(new_job)
                        new_job['username'] = username
                        self.jobs.append(new_job)
                    else:
                        self.assert_output('Limit of ten job postings has been reached.')
                case 'See all job postings':
                    job_postings = [job for job in self.jobs if job["deleted"] == False]
                    if len(job_postings) > 0:
                        out, err = self.capsys.readouterr()
                        output_lines = out.strip().split('\n')[:6*len(job_postings)]
                        expected_lines = [f'title: {job["title"]}' for job in job_postings] + \
                        [f'employer: {job["employer"]}' for job in job_postings] + \
                        [f'description: {job["description"]}' for job in job_postings] + \
                        [f'location: {job["location"]}' for job in job_postings] + \
                        [f'salary: {job["salary"]}' for job in job_postings] + \
                        [f'username: {job["username"]}' for job in job_postings]
                        assert set(output_lines) == set(expected_lines)
                    else:
                        self.assert_output('No job postings found.')
                case 'Delete a job':
                    job_postings = [job for job in self.user()["jobs-posted"] if job["deleted"] == False]
                    if len(job_postings) > 0:
                        out, err = self.capsys.readouterr()
                        print(out)
                        output_lines = out.strip().split('\n')[:len(job_postings)]
                        expected_lines = [f'{i+1}) {job["title"]}' for i, job in enumerate(job_postings)]
                        #print(expected_lines)
                        #print(output_lines)
                        assert set(output_lines[:len(job_postings)]) == set(expected_lines)
                        delete_job = bernoulli(3/4)
                        if delete_job:
                            choice_delete = random.choice(job_postings)
                            for posting in self.jobs:
                                if posting == choice_delete:
                                    posting["deleted"] = True
                                    choice_delete["deleted"] = True
                                    break
                        self.assert_output('Job successfully deleted.')
                            
                    else:
                        self.assert_output('No job postings found from you.')
                case 'List applied jobs':
                    applied_jobs = [job for job in self.user()["jobs-applied"]]
                    if len(applied_jobs) == 0:
                        self.assert_output('No job applications found.')
                    else:
                        expected_lines = []
                        for i, job in applied_jobs:
                            expected_lines.append(f'{i + 1}) {applied_jobs["title"]}')
                        out, err = self.capsys.readouterr()
                        output_lines = out.strip().split('\n')[:len(applied_jobs)]
                        assert set(output_lines) == set(expected_lines)
                case 'List jobs not yet applied to':
                    job_postings = [job for job in self.jobs if job["deleted"] == False]
                    applied_jobs = [job for job in self.users[self.user_session]["jobs-applied"]]
                    unapplied_jobs = []
                    if len(applied_jobs) == len(job_postings):
                        self.assert_output('No remaining job postings found.')
                    else:
                        expected_lines = []
                        for i, title in enumerate([posting['title'] for posting in job_postings if posting['title'] not in applied_jobs]):
                            expected_lines.append(f'{i + 1}) {title}')
                            unapplied_jobs.append(title)
                        out, err = self.capsys.readouterr()
                        output_lines = out.strip().split('\n')[:len(unapplied_jobs)]
                        assert set(output_lines) == set(expected_lines)
                case 'Mark a job':
                    job_postings = [job for job in self.jobs if job["deleted"] == False]
                    jobs_marked = [job for job in self.user()["jobs-marked"]]
                    expected_lines = []
                    jobs_unmarked = []
                    if len(job_postings) == 0:
                        self.assert_output('No job postings found.')
                    else: 
                        for i, posting in enumerate(job_postings):
                            if posting in jobs_marked:
                                expected_lines.append(f'{i + 1}) {posting["title"]} (marked)')
                            else:
                                expected_lines.append(f'{i + 1}) {posting["title"]}')
                                jobs_unmarked.append((i, posting))
                        out, err = self.capsys.readouterr()
                        output_lines = out.strip().split('\n')[:len(job_postings)]
                        assert set(output_lines) == set(expected_lines)
                        if len(jobs_unmarked) > 0:
                            mark_id, mark_choice = random.choice(jobs_unmarked)
                            
                            yield mark_choice
                            self.assert_output('Job successfully marked as saved.',
                                        error_msg=f'Unable to mark job, target: {mark_choice}')
                            self.users[self.user_session]['jobs-marked'].append(mark_id)
                case 'Unmark a job':
                    jobs_marked = [job for job in self.user()["jobs-marked"]]
                    expected_lines = []
                    jobs_unmarked = []
                    if len(jobs_marked) == 0:
                        self.assert_output('No jobs are marked as saved.')
                    else:
                        for i, posting in enumerate(jobs_marked):
                            if posting in jobs_marked:
                                expected_lines.append(f'{i + 1}) {posting["title"]}')
                        out, err = self.capsys.readouterr()
                        output_lines = out.strip().split('\n')[:len(jobs_marked)]
                        assert set(output_lines) == set(expected_lines)
                        if len(jobs_marked) > 0:
                            mark_id, mark_choice = random.choice(jobs_marked)
                            yield mark_choice

                            self.assert_output('Job successfully unmarked.',
                                        error_msg=f'Unable to unmark job.')
                            self.users[self.user_session]['jobs-marked'].remove(mark_id)
                case 'Lookup users':
                    if self.menu.access_token is not None:
                        if len(self.users) > 0:
                            find_user = bernoulli(3/4)
                            if find_user:
                                user = random.choice(self.users)
                                enter_first_name = bernoulli(3/4)
                                if enter_first_name:
                                    first_name = user['firstname']
                                enter_last_name = bernoulli(3/4)
                                if enter_last_name:
                                    last_name = user['lastname']
                                enter_university = bernoulli(3/4)
                                if enter_university:
                                    university = user['university']
                                enter_major = bernoulli(3/4)
                                if enter_major:
                                    major = user['major']

                                if len(first_name) > 0 or len(last_name) > 0 or len(university) > 0 or len(major) > 0:
                                    out, err = self.capsys.readouterr()
                                    valid_users = [user for user in self.users if user["firstname"] == first_name or user["lastname"] == last_name
                                                   or user["university"] == university or user["major"] == major]
                                    print(valid_users)
                                    output_lines = out.strip().split('\n')
                                    assert output_lines[0] == 'Matches:'
                                    assert output_lines[1:len(valid_users)] == {f'{user["username"]} {user["firstname"]} {user["lastname"]}' for user in valid_users}
                                    
                                    assert output_lines[-1] == 'Would you like to connect to any one of the matches displayed above? If so, enter their username. If not, simply press enter'
                                    enter_match = bernoulli(3/4)
                                    if enter_match:
                                        user = random.choice(valid_users)
                                        if i == self.user_session or \
                                        self.user_session in self.users[i]['connection-requests'] or \
                                        i in self.user()['connection-requests'] + self.user()['connections']:
                                            self.assert_output(f'Unable to send {user["username"]} a connection request.')
                                        else:
                                            self.assert_output('Connection request successfully sent.',
                                            error_msg=f'user: {self.user()["username"]}, target: {user}')
                                            self.users[self.user_session]['connection-requests'].append(choice_id)
                                    else:
                                        assert self.menu.mode == 'main'

                        else:
                            assert self.menu.mode == 'main'
                case 'InCollege Video':
                    self.assert_output('Video is now playing')
                case 'Useful links':
                    assert self.menu.mode == 'useful links'
                case 'General':
                    assert self.menu.mode == 'general'
                case 'Browse InCollege':
                    self.assert_output('Under construction')
                case 'Business Solutions':
                    self.assert_output('Under construction')
                case 'Directories':
                    self.assert_output('Under construction')
                case 'Help Center':
                    self.assert_output('We\'re here to help')
                case 'About':
                    self.assert_output('InCollege: Welcome to InCollege, the world\'s largest college student network with many users in many countries and territories worldwide.')
                case 'Press':
                    self.assert_output('InCollege Pressroom: Stay on top of the latest news, updates, and reports.')
                case 'Blog':
                    self.assert_output('Under construction')
                case 'Careers':
                    self.assert_output('Under construction')
                case 'Developers':
                    self.assert_output('Under construction')
                case 'Go back':
                    if self.menu.access_token is None:
                        assert self.menu.mode == 'log-in'
                    else:
                        assert self.menu.mode == 'main'
                case 'Return':
                    assert self.menu.mode == 'useful links'
                case _:
                    raise Exception(f'Not implemented: {options[option]}')

        assert self.menu.mode in ['job search/internship', 'main', 'log-in']
        if self.menu.mode == 'job search/internship':
            yield next(zip(*self.menu.options())).index('Go back') + 1
        if self.menu.mode == 'main':
            yield next(zip(*self.menu.options())).index('Log out') + 1
        if self.menu.mode == 'log-in':
            yield next(zip(*self.menu.options())).index('Exit') + 1
        assert self.menu.mode == 'exited', self.menu.mode
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