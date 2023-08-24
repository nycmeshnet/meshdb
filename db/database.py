from sqlalchemy import create_engine
import variables
from sqlalchemy.orm import Session

def create_db_engine():
 return create_engine("postgresql://{}:{}@{}/{}".format(variables.db_user,
                                                             variables.db_password,
                                                             variables.db_host,
                                                             variables.db_name), echo=True)

def executeQuery(statement, db_engine):
    with Session(db_engine) as session:
        return session.execute(statement)