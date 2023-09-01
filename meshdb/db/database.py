import os

from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker

db = SQLAlchemy()


def load_db_string_from_env():
    load_dotenv()  # Load .env file (FIXME: Probably move to somewhere less stupid)
    return "postgresql://{}:{}@{}/{}".format(
        os.getenv("DB_USER"),
        os.getenv("DB_PASSWORD"),
        os.getenv("DB_HOST"),
        os.getenv("DB_NAME"),
    )


def create_db_engine():
    print("Creating engine...")
    return create_engine(
        load_db_string_from_env(),
        echo=True,
    )


def executeQuery(statement, db_engine):
    with Session(db_engine) as session:
        return session.execute(statement)
