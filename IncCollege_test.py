import pytest
from InCollege import *



def test_new_user(test_input):
    test_input.setattr('builtins.input', lambda_: 'n')
    user = input("")
    assert user == 'n'

def test_wrong_input():
    assert main() == None

def test_existing_user():
    assert main() == 'e'

def test_home_page_quit():
    with pytest.raises(SystemExit):
        x = 1 / 1


def test_skills():
    assert skills_page == 1