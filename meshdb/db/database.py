from sqlalchemy import create_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from dotenv import load_dotenv
import os


def load_db_string_from_env():
    load_dotenv()  # Load .env file (FIXME: Probably move to somewhere less stupid)
    return "postgresql://{}:{}@{}/{}".format(
        os.getenv("MESHDB_DB_USER"),
        os.getenv("MESHDB_DB_PASSWORD"),
        os.getenv("MESHDB_DB_HOST"),
        os.getenv("MESHDB_DB_NAME"),
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
