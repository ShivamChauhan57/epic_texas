from main import *
import requests
import pytest
import sys

@pytest.fixture(scope="class")
@pytest.mark.parametrize('user_name, fullname, pw', [('Adam', None, None),
('EJry', 'Jerry Excel', 'Fts%sau'), ('EJry', 'Jerry Excel', 'Fts%0421u')])
def test_signup(monkeypatch, capsys, username, fullname, password):
    test_menu = Menu()
    test_menu.signup()
    responses = iter([username, fullname, password])
    monkeypatch.setattr('builtins.input', lambda _: next(responses))

    captured = capsys.readouterr()
    assert captured.out == 'Username not available!' # Ryan Chick 10/1/2023

    captured = capsys.readouterr()
    assert captured.out == 'Password is not secure, should be at least eight characters and must contain a number.' # Ryan Chick 10/1/2023

    captured = capsys.readouterr()
    assert captured.out == "You have successfully signed up! Please log in now." # Ryan Chick 9/25/2023

@pytest.fixture()
@pytest.mark.parametrize('username, fullname, password', [('EJry', None),
('EJr', 'Fts%0421u'), ('EJry','Fts%0421u')])
def test_login(monkeypatch, capsys, username, password):
    test_menu = Menu()
    test_menu.login()
    responses = iter([username, password])
    monkeypatch.setattr('builtins.input', lambda _: next(responses))

    captured = capsys.readouterr()
    assert captured.out == 'Login unsuccessful.' # Ryan Chick 10/1/2023

    captured = capsys.readouterr()
    assert captured.out == 'Login unsuccessful.' # Ryan Chick 10/1/2023

    captured = capsys.readouterr()
    assert captured.out == "Login successful." # Ryan Chick 9/25/2023

@pytest.fixture()
def test_follow(monkeypatch, capsys):
    test_menu = Menu()
    test_menu.follow()
    monkeypatch.setattr('builtins.input', lambda _: 'Adam')

    captured = capsys.readouterr()
    assert captured == "You are now following Adam" # Ryan Chick 9/25/2023

@pytest.fixture()
def test_list_followers(capsys):
    test_menu = Menu()
    test_menu.list_followers()

    captured = capsys.readouterr()
    assert captured == "raunakchhatwal Raunak Chhatwal" # Ryan Chick 9/25/2023

@pytest.fixture()
def test_discover_users(capsys): 
    test_menu = Menu()
    test_menu.discover_users()

    captured = capsys.readouterr()
    assert captured == "raunakchhatwal Raunak Chhatwal"
    captured = capsys.readouterr()
    assert captured == "david david shermite"
    captured = capsys.readouterr()
    assert captured == "Adam Adam Kelvor"
    captured = capsys.readouterr()
    assert captured == "testuser1 Test User"
    captured = capsys.readouterr()
    assert captured == "Noah10 Noah Diez"
    captured = capsys.readouterr()
    assert captured == "Ejry Jerry Excel" # Ryan Chick 10/1/2023

@pytest.fixture()
@pytest.mark.parametrize('firstname, lastname, output', [('Adam', 'Kelvor', 'Adam Kelvor is a part of the InCollege system.'), 
               ('Karen', 'Stewart', 'Karen Stewart is not yet a part of the InCollege system yet.'), 
               (None, None, 'Unable to lookup whether user is part of the InCollege system')])
def test_lookup_user(monkeypatch, capsys, firstname, lastname, output):
    test_menu = Menu()
    test_menu.lookup_user()

    responses = iter([firstname, lastname])
    monkeypatch.setattr('builtins.input', lambda _: next(responses))

    captured = capsys.readouterr()
    assert captured == output # Ryan Chick 10/1/2023

@pytest.fixture(scope='class')
@pytest.mark.parametrize('title, description, employer, location, salary', [(None, None, None, None, 0), 
               ('Software Engineer', 
                'Can prepare and install solutions by determining and designing system specifications, standards, and programming.', 
                'Malcom Perrson', 'tampa', '$88568')])
def test_post_job(monkeypatch, capsys, title, description, employer, location, salary):
    test_menu = Menu()
    test_menu.post_job()

    responses = iter([title, description, employer, location, salary])
    monkeypatch.setattr('builtins.input', lambda _: next(responses))

    captured = capsys.readouterr()
    assert captured == 'Invalid salary, must be a number which begins with $' # Ryan Chick 10/1/2023

    captured = capsys.readouterr()
    assert captured == 'Job posting created successfully.' # Ryan Chick 10/1/2023

@pytest.fixture()
@pytest.mark.parametrize('title, description, employer, location, salary, username', [
    ('title: Software Engineer', 
     'description: Can prepare and install solutions by determining and designing system specifications, standards, and programming.', 
     'employer: Malcom Perrson', 'location: tampa', 'salary: $88568', 'username: Adam')])
def test_get_job_postings(monkeypatch, capsys, title, description, employer, location, salary, username):
    test_menu = Menu()
    test_menu.get_job_postings()

    captured = capsys.readouterr()
    assert captured == title
    captured = capsys.readouterr()
    assert captured == description
    captured = capsys.readouterr()
    assert captured == employer
    captured = capsys.readouterr()
    assert captured == location
    captured = capsys.readouterr()
    assert captured == salary
    captured = capsys.readouterr()
    assert captured == username # Ryan Chick 10/1/2023