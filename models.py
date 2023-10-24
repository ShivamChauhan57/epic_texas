import os
import sys
from sqlalchemy import create_engine, Column, Integer, String, Date, Boolean, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Users(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    firstname = Column(String, nullable=False)
    lastname = Column(String, nullable=False)
    passwordHash = Column(String, nullable=False)

class Profiles(Base):
    __tablename__ = 'profiles'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True)

    bio = Column(String)

    university = Column(String, nullable=False)
    major = Column(String, nullable=False)
    years_attended = Column(Integer)

class Experience(Base):
    __tablename__ = 'experience'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))

    title = Column(String, nullable=False)
    employer = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    location = Column(String)
    description = Column(String)

class Connections(Base):
    __tablename__ = 'connections'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    connection_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    request_status = Column(String, CheckConstraint('request_status IN ("pending", "accepted")'))

    __table_args__ = (
        UniqueConstraint('user_id', 'connection_id'),
    )

class JobPostings(Base):
    __tablename__ = 'job_postings'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))

    title = Column(String, nullable=False)
    description = Column(String)
    employer = Column(String)
    location = Column(String)
    salary = Column(Integer)

class UserPreferences(Base):
    __tablename__ = 'user_preferences'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True)

    email_notifications_enabled = Column(Boolean, nullable=False)
    sms_notifications_enabled = Column(Boolean, nullable=False)
    targeted_advertising_enabled = Column(Boolean, nullable=False)
    language = Column(String, CheckConstraint('language IN ("english", "spanish")'), nullable=False)

if __name__ == '__main__':
    if os.path.exists('./users.db'):
        print('./users.db already exists!')
        sys.exit()

    engine = create_engine('sqlite:///users.db')
    Base.metadata.create_all(engine)
    print('./users.db successfully created')