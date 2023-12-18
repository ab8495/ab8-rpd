from curses import echo
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# import logging
# logging.basicConfig()
# logger = logging.getLogger('sqlalchemy.engine')
# logger.setLevel(logging.INFO)

# The base directory should be two levels up from the current file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Get the DATABASE_URL environment variable, which is empty if it doesn't exist
DATABASE_URL = os.getenv("DATABASE_URL", "")

# If the DATABASE_URL environment variable is not set, use sqlite
if DATABASE_URL == "" or DATABASE_URL is None:
    print("Using sqlite database")
    SQLITE_DATABASE_URL = 'sqlite:///' + os.path.join(BASE_DIR, 'db.sqlite3')
    engine = create_engine(SQLITE_DATABASE_URL, connect_args={"check_same_thread": False})
# If the DATABASE_URL environment variable is set, use postgres
else:
    engine = create_engine(DATABASE_URL)

# Create a session factory
Session = sessionmaker(bind=engine)

# Create a base class for models
Base = declarative_base()

@staticmethod
def create_database_tables():
    """ Conditionally create database tables if they don't already exist """
    # Prevents unnecessary sql statements from being executed if the tables already exist
    if not engine.dialect.has_table(engine, "player_history"):
        Base.metadata.create_all(engine)
