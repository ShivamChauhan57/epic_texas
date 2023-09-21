# My Application README

## Prerequisites

- [Python 3](https://www.python.org/downloads/)
- [SQLite3](https://www.sqlite.org/download.html)

## Setup

1. Create `jwt-key.txt` with a secret key in the root directory.
2. Run: `sqlite3 users.db < users.sql`
3. Launch server: `python3 server.py`
4. Run app: `python3 main.py`

## Important Note

The program will crash if you perform an action that requires you to log in and you haven't logged in. These actions are: get profile, follow a user, see followers. Ensure you log in before attempting any of these actions.