from main import *
import pytest
import sys

def test_signup(test_input, capsys):
    signup()
    responses = iter(['Adam', 'EJry', 'Jerry Excel', 'Fts%0421u'])
    test_input.setattr('builtins.input', lambda _: next(responses))

    username = input('Please enter your username: ')
    assert username == "EJry"

    name = input('Please enter your first and last name: ')
    assert name == "Jerry Excel"

    password = input('Enter your password: ')
    assert password == "Fts%0421u"

    captured = capsys.readouterr()
    assert captured.out == "You have successfully signed up! Please log in now."

def test_login(test_input, capsys):
    login()
    responses = iter(['Jerry', 'Fts%0421u'])
    test_input.setattr('builtins.input', lambda _: next(responses))

    username = input('Please enter your username: ')
    assert username == "Jerry"

    password = input('Enter your password: ')
    assert password == "Fts%0421u"

    captured = capsys.readouterr()
    assert captured.out == "Login successful."

def test_follow(test_input, capsys):
    follow()
    test_input.setattr('builtins.input', lambda _: 'Adam')

    username = input('Enter the username of the user to follow: ')
    assert username == 'Adam'

    captured = capsys.readouterr()
    assert captured == "You are now following Adam"
    
def test_list_followers(capsys):
    list_followers()

    captured = capsys.readouterr()
    assert captured == "raunakchhatwal Raunak Chhatwal"