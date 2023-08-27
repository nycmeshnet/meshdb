from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os


def create_db_engine():
    load_dotenv()  # Load .env file (FIXME: Probably move to somewhere less stupid)
    return create_engine(
        "postgresql://{}:{}@{}/{}".format(
            os.getenv("MESHDB_DB_USER"),
            os.getenv("MESHDB_DB_PASSWORD"),
            os.getenv("MESHDB_DB_HOST"),
            os.getenv("MESHDB_DB_NAME"),
        ),
        echo=True,
    )


def executeQuery(statement, db_engine):
    with Session(db_engine) as session:
        return session.execute(statement)
