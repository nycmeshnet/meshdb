import os

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker

db = SQLAlchemy()


def executeQuery(statement, db_engine):
    with Session(db_engine) as session:
        return session.execute(statement)
