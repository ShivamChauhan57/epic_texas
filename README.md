# My Application README

## Prerequisites

- [Python 3](https://www.python.org/downloads/)
- [SQLite3](https://www.sqlite.org/download.html) (only needed for running a dev backend)

## Using main.py with an existing backend

1. Run `python3 main.py <backend url>`.
2. If no url provided (i.e. just `python3 main.py` was run), http://raunak.us will be used.
3. The application will now interact with the specified backend for requesting and managing user data.
4. Use the available actions such as "Log in", "Sign up", "See profile", "Discover users", etc. to interact with the application.

## Launching a dev backend

Follow these steps if you want to run a development backend server on your local machine:

1. Create `jwt-key.txt` with a secret key in the root directory.
2. Run: `sqlite3 users.db < users.sql` to create the SQLite database for user data.
3. Launch the backend server using `python3 server.py`. You can specify the port number as a command line argument (e.g., `python3 server.py 8000`) or use the default port 8000.
4. Run `python3 main.py http://localhost:PORT`, replacing "PORT" with the port number you used in step 3.

With your dev backend up and running, you can interact with the application just like you would when connecting to an existing backend. This setup is useful for testing, debugging, and development purposes.