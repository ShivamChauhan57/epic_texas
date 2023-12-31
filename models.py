import os
import sys
from sqlalchemy import create_engine, Column, Integer, String, Date, DateTime, Boolean, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Users(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    firstname = Column(String, nullable=False)
    lastname = Column(String, nullable=False)
    passwordHash = Column(String, nullable=False)

    tier = Column(String, CheckConstraint('tier IN ("standard", "plus")'), nullable=False)

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

    deleted = Column(Boolean, nullable=False)

class JobApplications(Base):
    __tablename__ = 'job_applications'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    job_id = Column(Integer, ForeignKey('job_postings.id', ondelete='CASCADE'))

    graduation_date = Column(Date, nullable=False)
    ideal_start_date = Column(Date, nullable=False)
    cover_letter = Column(String, nullable=False)
    application_date = Column(Date, nullable=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'job_id'),
    )

class JobsMarked(Base):
    __tablename__ = 'jobs_marked'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    job_id = Column(Integer, ForeignKey('job_postings.id', ondelete='CASCADE'))

    __table_args__ = (
        UniqueConstraint('user_id', 'job_id'),
    )

class UserPreferences(Base):
    __tablename__ = 'user_preferences'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True)

    email_notifications_enabled = Column(Boolean, nullable=False)
    sms_notifications_enabled = Column(Boolean, nullable=False)
    targeted_advertising_enabled = Column(Boolean, nullable=False)
    language = Column(String, CheckConstraint('language IN ("english", "spanish")'), nullable=False)

class Conversations(Base):
    __tablename__ = 'conversations'

    id = Column(Integer, primary_key=True)
    user1 = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    user2 = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))

class Messages(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True)
    sender = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    conversation = Column(Integer, ForeignKey('conversations.id', ondelete='CASCADE'))
    time = Column(DateTime, nullable=False)
    read = Column(Boolean, nullable=False)
    content = Column(String, nullable=False)

class Notifications(Base):
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    menu = Column(String, nullable=False)
    content = Column(String, nullable=False)

if __name__ == '__main__':
    assert len(sys.argv) == 2
    database_name = sys.argv[1]
    if not database_name.endswith('.db'):
        raise Exception(f'Invalid file extension of sqlite database: {database_name}')

    '''if os.path.exists(database_name):
        print(f'./{database_name} already exists!')
        sys.exit()'''

    engine = create_engine(f'sqlite:///{database_name}')
    Base.metadata.create_all(engine)
    print(f'{database_name} successfully created')