import os
import sys
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Users(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    firstname = Column(String)
    lastname = Column(String)
    university = Column(String)
    major = Column(String)
    passwordHash = Column(String)

class Connections(Base):
    __tablename__ = 'connections'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    connection_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    request_status = Column(String, CheckConstraint("request_status IN ('pending', 'accepted')"))

    __table_args__ = (
        UniqueConstraint('user_id', 'connection_id'),
    )

    user = relationship('Users', foreign_keys=[user_id])
    connection = relationship('Users', foreign_keys=[connection_id])

class JobPostings(Base):
    __tablename__ = 'job_postings'

    id = Column(Integer, primary_key=True)
    title = Column(String)
    description = Column(String)
    employer = Column(String)
    location = Column(String)
    salary = Column(Integer)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))

    user = relationship('Users')

class UserPreferences(Base):
    __tablename__ = 'user_preferences'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True)
    email_notifications_enabled = Column(Boolean)
    sms_notifications_enabled = Column(Boolean)
    targeted_advertising_enabled = Column(Boolean)
    language = Column(String)

    user = relationship('Users')

if __name__ == '__main__':
    if os.path.exists('./users.db'):
        print('./users.db already exists!')
        sys.exit()

    engine = create_engine('sqlite:///users.db')
    Base.metadata.create_all(engine)
    print('./users.db successfully created')