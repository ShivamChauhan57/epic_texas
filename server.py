from flask import Flask, g, request, jsonify
import json
import sys
import inspect
from pathlib import Path
import jwt
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models import Base, Users
import logging
import argparse
import signal
import os
import psutil

from request_handlers import handlers, authenticated_handlers

def create_session(Session):
    g.session = Session()
    g.session.begin()

def close_session(response):
    if hasattr(g, 'session'):
        g.session.close()
    return response

def authenticate():
    try:
        token = request.headers['Authorization'].strip().split(' ')[1]
        payload = jwt.decode(token, Path('./jwt-key.txt').read_text().strip(), algorithms=['HS256'])
        g.user_id, g.username = payload['user_id'], payload['username']
    except (KeyError, IndexError, jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
        return 'Unauthorized', 401

    if g.session.query(Users).filter(Users.id == g.user_id).one_or_none() is None:
        return 'Unauthorized', 401

def parse():
    parser = argparse.ArgumentParser(description='Server Configuration')
    parser.add_argument(
        '--port', type=int, required=True, help='Port number for the server to listen on'
    )
    parser.add_argument(
        '--db',
        type=str,
        default='users.db',
        help='Path to the SQLite file (default: users.db)',
    )

    return tuple(getattr(parser.parse_args(), arg) for arg in ['port', 'db'])

db_path = os.environ.get('DB_PATH' , 'users.db')
assert os.path.exists(db_path)

app = Flask(__name__)

engine = create_engine(f'sqlite:///{db_path}')
Session = sessionmaker(bind=engine)

app.before_request_funcs = {
    'handlers': [ lambda: create_session(Session) ],
    'authenticated_handlers': [lambda: create_session(Session), authenticate]
}

app.after_request_funcs = {
    'handlers': [ close_session ],
    'authenticated_handlers': [ close_session ]
}

app.register_blueprint(handlers)
app.register_blueprint(authenticated_handlers)

if __name__ == '__main__':
    port, db_path = parse()
    app.run(port=port, threaded=True)
