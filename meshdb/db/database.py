import os
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import Engine, Executable, Result, create_engine
from sqlalchemy.orm import Session


def load_db_string_from_env() -> str:
    load_dotenv()  # Load .env file (FIXME: Probably move to somewhere less stupid)
    return "postgresql://{}:{}@{}/{}".format(
        os.getenv("DB_USER"),
        os.getenv("DB_PASSWORD"),
        os.getenv("DB_HOST"),
        os.getenv("DB_NAME"),
    )


def create_db_engine() -> Engine:
    print("Creating engine...")
    return create_engine(
        load_db_string_from_env(),
        echo=True,
    )


def executeQuery(statement: Executable, db_engine: Engine) -> Result[Any]:
    with Session(db_engine) as session:
        return session.execute(statement)
