# Epics Project README

## Warning
This project is not compatible with native Windows environments and has not been tested on macOS. To run this project, please use either a Linux environment or the Windows Subsystem for Linux (WSL).

## Launching the backend

Follow these steps if you want to run a development backend server on your local machine:

1. Run `pip install -r requirements.txt`.
2. Create `jwt-key.txt` with a secret key in the root directory.
3. Run: `python3 models.py users.db` to create the SQLite database for user data.
4. Launch the backend server using `gunicorn --bind 0.0.0.0:8000 server:app`.
5. Run `python3 main.py http://localhost:8000`.

With your dev backend up and running, you can interact with the application just like you would when connecting to an existing backend. This setup is useful for testing, debugging, and development purposes.

## Using main.py (the CLI frontend)

1. Run `pip install -r requirements.txt`.
2. Run `python3 main.py http://localhost:8000`.
3. If no url provided (i.e. just `python3 main.py` was run), http://raunak.us will be used. Warning: http://raunak.us is often either down or out of date.
4. The application will now interact with the specified backend for requesting and managing user data.
5. Use the available actions such as "Log in", "Sign up", "See profile", "Discover users", etc. to interact with the application.

## End to end testing
1. Run `pip install -r requirements.txt`.
2. Run `pytest -v E2E.py`.
3. Options currently covered: log in, sign up, discover users, exit, send connection requests, view requests, show my network, disconnect from a user, and log out.
