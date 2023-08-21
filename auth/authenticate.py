from sqlalchemy import create_engine
import variables
from db.database import create_db_engine, executeQuery
from auth.token import authToken
from sqlalchemy import select

db_engine = create_db_engine()

def get_userrole(token):
    stmt = (
        select(authToken.role).where(authToken.token == token)
    )
    result = executeQuery(stmt, db_engine)
    return result.one()[0]