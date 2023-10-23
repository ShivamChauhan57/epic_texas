from flask import Flask, g, request, jsonify
import json
import sys
import inspect
from pathlib import Path
import jwt
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models import Base, Users

from request_handlers import handlers, authenticated_handlers

engine = create_engine('sqlite:///users.db')
Session = sessionmaker(bind=engine)

def create_session():
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
        print(e)
        return 'Unauthorized', 401

    if g.session.query(Users).filter(Users.id == g.user_id).one_or_none() is None:
        return 'Unauthorized', 401

app = Flask(__name__)

app.before_request_funcs = {
    'handlers': [ create_session ],
    'authenticated_handlers': [ create_session, authenticate ]
}

app.after_request_funcs = {
    'handlers': [ close_session ],
    'authenticated_handlers': [ close_session ]
}

app.register_blueprint(handlers)
app.register_blueprint(authenticated_handlers)

if __name__ == '__main__':
    PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    app.run(port=PORT, threaded=True)
